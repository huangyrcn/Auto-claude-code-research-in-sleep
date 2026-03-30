---
name: "run-experiment"
description: "Deploy and run ML experiments on local or remote GPU servers. Use when user says \"run experiment\", \"deploy to server\", \"\u8dd1\u5b9e\u9a8c\", or needs to launch training jobs."
---

# Run Experiment

Deploy and run ML experiment: $ARGUMENTS

## Workflow

### Step 1: Detect Environment And Runtime Contract

Read the project's `AGENTS.md` to determine the experiment environment and runtime contract:

- **Local GPU**: Look for local CUDA/MPS setup info
- **Remote server**: Look for SSH alias, conda env, and remote root
- **Launcher** (`launcher: tmux`): Treat `tmux` as the canonical launcher
- **Session prefix** (`session_prefix: aris`): Default session name prefix
- **Runs directory** (`runs_dir: exp/runs`): Default run manifest directory
- **Logs directory** (`logs_dir: exp/logs`): Default log directory
- **Results directory** (`results_dir: exp/results`): Default structured result directory

If no server info is found in `AGENTS.md`, ask the user.

### Step 2: Pre-flight Check

Check GPU availability on the target machine:

**Remote:**
```bash
ssh <server> nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv,noheader
```

**Local:**
```bash
nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv,noheader
# or for Mac MPS:
python -c "import torch; print('MPS available:', torch.backends.mps.is_available())"
```

Free GPU = memory.used < 500 MiB.

### Step 3: Sync Code (Remote Only)

Check the project's `AGENTS.md` for a `code_sync` setting. If not specified, default to `rsync`.

#### Option A: rsync (default)

Only sync necessary files — NOT data, checkpoints, or large files:
```bash
rsync -avz --include='*.py' --exclude='*' <local_src>/ <server>:<remote_workdir>/
```

#### Option B: git (when `code_sync: git` is set in AGENTS.md)

Push local changes to remote repo, then pull on the server:
```bash
# 1. Push from local
git add -A && git commit -m "sync: experiment deployment" && git push

# 2. Pull on server
ssh <server> "cd <remote_workdir> && git pull"
```

Benefits: version-tracked, multi-server sync with one push, no rsync include/exclude rules needed.

### Step 3.5: W&B Integration (when `wandb: true` in AGENTS.md)

**Skip this step entirely if `wandb` is not set or is `false` in AGENTS.md.**

Before deploying, ensure the experiment scripts have W&B logging:

1. **Check if wandb is already in the script** — look for `import wandb` or `wandb.init`. If present, skip to Step 4.

2. **If not present, add W&B logging** to the training script:
   ```python
   import wandb
   wandb.init(project=WANDB_PROJECT, name=EXP_NAME, config={...hyperparams...})

   # Inside training loop:
   wandb.log({"train/loss": loss, "train/lr": lr, "step": step})

   # After eval:
   wandb.log({"eval/loss": eval_loss, "eval/ppl": ppl, "eval/accuracy": acc})

   # At end:
   wandb.finish()
   ```

3. **Metrics to log** (add whichever apply to the experiment):
   - `train/loss` — training loss per step
   - `train/lr` — learning rate
   - `eval/loss`, `eval/ppl`, `eval/accuracy` — eval metrics per epoch
   - `gpu/memory_used` — GPU memory (via `torch.cuda.max_memory_allocated()`)
   - `speed/samples_per_sec` — throughput
   - Any custom metrics the experiment already computes

4. **Verify wandb login on the target machine:**
   ```bash
   ssh <server> "wandb status"  # should show logged in
   # If not logged in:
   ssh <server> "wandb login <WANDB_API_KEY>"
   ```

> The W&B project name and API key come from `AGENTS.md` (see example below). The experiment name is auto-generated from the script name + timestamp.

### Step 3.2: Reserve Run Handles

Before deployment, create:

- `exp/runs/<run_id>/launch.sh`
- `exp/runs/<run_id>/run.json`
- `exp/logs/<run_id>.log`
- `exp/results/<run_id>.json`

Set `session_name = aris-<run_id>` unless `session_prefix` overrides it.

### Step 4: Deploy

#### Remote (via SSH + tmux)

For each experiment, create a dedicated `tmux` session with GPU binding:
```bash
ssh <server> "mkdir -p <remote_workdir>/exp/runs/<run_id> <remote_workdir>/exp/logs <remote_workdir>/exp/results && \
  tmux new-session -d -s <session_name> '\
  cd <remote_workdir> && \
  bash exp/runs/<run_id>/launch.sh'"
```

#### Local

```bash
# Linux with CUDA
tmux new-session -d -s <session_name> '\
  cd <project_root> && \
  bash exp/runs/<run_id>/launch.sh'

# Mac with MPS (PyTorch uses MPS automatically)
tmux new-session -d -s <session_name> '\
  cd <project_root> && \
  bash exp/runs/<run_id>/launch.sh'
```

For local long-running jobs, use `run_in_background: true` to keep the conversation responsive.

### Step 5: Verify Launch

**Remote:**
```bash
ssh <server> "tmux ls"
```

**Local:**
Check process is running and GPU is allocated.

### Step 6: Feishu Notification (if configured)

After deployment is verified, check `~/.codex/feishu.json`:
- Send `experiment_done` notification: which experiments launched, which GPUs, estimated time
- If config absent or mode `"off"`: skip entirely (no-op)

## Key Rules

- ALWAYS check GPU availability first — never blindly assign GPUs
- Each experiment gets its own `tmux` session + GPU binding
- Every launch should reserve a `run_id`, `run.json`, log path, and result path
- Use `tee` to save logs to `exp/logs/<run_id>.log`
- Run deployment commands with `run_in_background: true` to keep conversation responsive
- Report back: which GPU, which `tmux` session, which `run_id`, what command, estimated time
- If multiple experiments, launch them in parallel on different GPUs

## AGENTS.md Example

Users should add their server info to their project's `AGENTS.md`:

```markdown
## Remote Server
- launcher: tmux
- SSH: `ssh my-gpu-server`
- GPU: 4x A100 (80GB each)
- Conda: `eval "$(/opt/conda/bin/conda shell.bash hook)" && conda activate research`
- remote_root: `/home/user/experiments`
- code_sync: rsync          # default. Or set to "git" for git push/pull workflow
- session_prefix: aris
- runs_dir: exp/runs
- logs_dir: exp/logs
- results_dir: exp/results
- wandb: false              # set to "true" to auto-add W&B logging to experiment scripts
- wandb_project: my-project # W&B project name (required if wandb: true)
- wandb_entity: my-team     # W&B team/user (optional, uses default if omitted)

## Local Environment
- launcher: tmux
- Mac MPS / Linux CUDA
- Conda env: `ml` (Python 3.10 + PyTorch)
```

> **W&B setup**: Run `wandb login` on your server once (or set `WANDB_API_KEY` env var). The skill reads project/entity from `AGENTS.md` and adds `wandb.init()` + `wandb.log()` to your training scripts automatically. Dashboard: `https://wandb.ai/<entity>/<project>`.
