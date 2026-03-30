---
name: run-experiment
description: Deploy and run ML experiments on local or remote GPU servers. Use when user says "run experiment", "deploy to server", "跑实验", or needs to launch training jobs.
argument-hint: [experiment-description]
allowed-tools: Bash(*), Read, Grep, Glob, Edit, Write, Agent
---

# Run Experiment

Deploy and run ML experiment: $ARGUMENTS

## Workflow

### Step 1: Detect Environment And Runtime Contract

Read the project's `CLAUDE.md` to determine both the experiment environment and the runtime contract:

- **Local GPU** (`gpu: local`): Look for local CUDA/MPS setup info
- **Remote server** (`gpu: remote`): Look for SSH alias, conda env, and remote root
- **Vast.ai** (`gpu: vast`): Check for `vast-instances.json` at project root — if a running instance exists, use that instance. Also check `CLAUDE.md` for a `## Vast.ai` section.
- **Launcher** (`launcher: tmux`): Treat `tmux` as the default and canonical launcher
- **Session prefix** (`session_prefix: aris`): Default session name prefix
- **Runs directory** (`runs_dir: exp/runs`): Default run manifest directory
- **Logs directory** (`logs_dir: exp/logs`): Default log directory
- **Results directory** (`results_dir: exp/results`): Default structured result directory

Derive these runtime values before launching anything:

- `project_name` = current project directory name
- `remote_workdir` = `<remote_root>/<project_name>/` for remote SSH servers
- `run_id` = `rYYYYMMDD-HHMMSS-<slug>`
- `session_name` = `<session_prefix>-<run_id>`

For every launched experiment, reserve these artifacts:

- `exp/runs/<run_id>/launch.sh`
- `exp/runs/<run_id>/run.json`
- `exp/logs/<run_id>.log`
- `exp/results/<run_id>.json`

**Vast.ai detection priority:**
1. If `CLAUDE.md` has `gpu: vast` or a `## Vast.ai` section:
   - If `vast-instances.json` exists and has a running instance → use that instance
   - If no running instance → call `/vast-gpu provision` which analyzes the task, presents cost-optimized GPU options, and rents the user's choice
2. If no server info is found in `CLAUDE.md`, ask the user.

### Step 2: Pre-flight Check

Check GPU availability on the target machine:

**Remote (SSH):**
```bash
ssh <server> nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv,noheader
```

**Remote (Vast.ai):**
```bash
ssh -p <PORT> root@<HOST> nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv,noheader
```
(Read `ssh_host` and `ssh_port` from `vast-instances.json`, or run `vastai ssh-url <INSTANCE_ID>` which returns `ssh://root@HOST:PORT`)

**Local:**
```bash
nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv,noheader
# or for Mac MPS:
python -c "import torch; print('MPS available:', torch.backends.mps.is_available())"
```

Free GPU = memory.used < 500 MiB.

### Step 3: Sync Code (Remote Only)

Check the project's `CLAUDE.md` for a `code_sync` setting. If not specified, default to `rsync`.

#### Option A: rsync (default)

Only sync necessary files — NOT data, checkpoints, or large files:
```bash
rsync -avz --include='*.py' --exclude='*' <local_src>/ <server>:<remote_workdir>/
```

#### Option B: git (when `code_sync: git` is set in CLAUDE.md)

Push local changes to remote repo, then pull on the server:
```bash
# 1. Push from local
git add -A && git commit -m "sync: experiment deployment" && git push

# 2. Pull on server
ssh <server> "cd <remote_workdir> && git pull"
```

Benefits: version-tracked, multi-server sync with one push, no rsync include/exclude rules needed.

#### Option C: Vast.ai instance

Sync code to the vast.ai instance (always rsync, code dir is `/workspace/project/`):
```bash
rsync -avz -e "ssh -p <PORT>" \
  --include='*.py' --include='*.yaml' --include='*.yml' --include='*.json' \
  --include='*.txt' --include='*.sh' --include='*/' \
  --exclude='*.pt' --exclude='*.pth' --exclude='*.ckpt' \
  --exclude='__pycache__' --exclude='.git' --exclude='data/' \
  --exclude='wandb/' --exclude='outputs/' \
  ./ root@<HOST>:/workspace/project/
```

If `requirements.txt` exists, install dependencies:
```bash
scp -P <PORT> requirements.txt root@<HOST>:/workspace/
ssh -p <PORT> root@<HOST> "pip install -q -r /workspace/requirements.txt"
```

### Step 3.2: Reserve Run Handles

Before deployment, create the runtime manifest for each experiment:

1. Generate a `run_id`
2. Create `exp/runs/<run_id>/launch.sh`
3. Create `exp/runs/<run_id>/run.json`
4. Ensure `exp/logs/` and `exp/results/` exist
5. Compute `session_name = aris-<run_id>` unless `session_prefix` overrides it

`run.json` should capture at least:

```json
{
  "run_id": "r20260330-153000-main",
  "session_name": "aris-r20260330-153000-main",
  "launcher": "tmux",
  "gpu_mode": "remote",
  "host": "my-gpu-server",
  "remote_workdir": "/home/user/project-name",
  "log_path": "exp/logs/r20260330-153000-main.log",
  "result_path": "exp/results/r20260330-153000-main.json",
  "status": "launching"
}
```

`launch.sh` should contain the exact activation + run command and write logs to `exp/logs/<run_id>.log`. If the experiment already emits structured metrics, point them to `exp/results/<run_id>.json`.

### Step 3.5: W&B Integration (when `wandb: true` in CLAUDE.md)

**Skip this step entirely if `wandb` is not set or is `false` in CLAUDE.md.**

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

> The W&B project name and API key come from `CLAUDE.md` (see example below). The experiment name is auto-generated from the script name + timestamp.

### Step 4: Deploy

#### Remote (via SSH + tmux)

For each experiment, create a dedicated `tmux` session with GPU binding:
```bash
ssh <server> "mkdir -p <remote_workdir>/exp/runs/<run_id> <remote_workdir>/exp/logs <remote_workdir>/exp/results && \
  tmux new-session -d -s <session_name> '\
  cd <remote_workdir> && \
  bash exp/runs/<run_id>/launch.sh'"
```

The `launch.sh` script should handle environment activation and include the final command, for example:

```bash
eval "$(<conda_path>/conda shell.bash hook)"
conda activate <env>
CUDA_VISIBLE_DEVICES=<gpu_id> python <script> <args> 2>&1 | tee exp/logs/<run_id>.log
```

#### Vast.ai instance

No conda needed — the Docker image has the environment. Use `/workspace/project/` as working dir:
```bash
ssh -p <PORT> root@<HOST> "mkdir -p /workspace/project/exp/runs/<run_id> /workspace/project/exp/logs /workspace/project/exp/results && \
  tmux new-session -d -s <session_name> '\
  cd /workspace/project && \
  bash exp/runs/<run_id>/launch.sh'"
```

After launching, update the `experiment` field in `vast-instances.json` for this instance.

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

For short local sanity checks you may run the command directly, but the canonical long-running path is still `tmux + run_id + exp/`.

### Step 5: Verify Launch

**Remote (SSH):**
```bash
ssh <server> "tmux ls"
```

**Remote (Vast.ai):**
```bash
ssh -p <PORT> root@<HOST> "tmux ls"
```

**Local:**
Check the `tmux` session exists, then verify GPU allocation and recent log lines:

```bash
tmux ls
tail -50 exp/logs/<run_id>.log
```

### Step 6: Feishu Notification (if configured)

After deployment is verified, check `~/.claude/feishu.json`:
- Send `experiment_done` notification: which experiments launched, which GPUs, estimated time
- If config absent or mode `"off"`: skip entirely (no-op)

### Step 7: Auto-Destroy Vast.ai Instance (when `gpu: vast` and `auto_destroy: true`)

**Skip this step if not using vast.ai or `auto_destroy` is `false`.**

After the experiment completes (detected via `/monitor-experiment` or tmux session ending):

1. **Download results** from the instance:
   ```bash
   rsync -avz -e "ssh -p <PORT>" root@<HOST>:/workspace/project/exp/results/ ./exp/results/
   ```

2. **Download logs**:
   ```bash
   rsync -avz -e "ssh -p <PORT>" root@<HOST>:/workspace/project/exp/logs/ ./exp/logs/
   ```

3. **Destroy the instance** to stop billing:
   ```bash
   vastai destroy instance <INSTANCE_ID>
   ```

4. **Update `vast-instances.json`** — mark status as `destroyed`.

5. **Report cost**:
   ```
   Vast.ai instance <ID> auto-destroyed.
   - Duration: ~X.X hours
   - Estimated cost: ~$X.XX
   - Results saved to: ./exp/results/
```

> This ensures users are never billed for idle instances. When `auto_destroy: true` (the default), the full lifecycle is automatic: rent → setup → run → collect → destroy.

## Key Rules

- ALWAYS check GPU availability first — never blindly assign GPUs
- Each experiment gets its own `tmux` session + GPU binding
- Every launch must have a `run_id`, `run.json`, `launch.sh`, log file, and result path
- Use `tee` to save logs to `exp/logs/<run_id>.log`
- Run deployment commands with `run_in_background: true` to keep conversation responsive
- Report back: which GPU, which `tmux` session, which `run_id`, what command, estimated time
- If multiple experiments, launch them in parallel on different GPUs
- **Vast.ai cost awareness**: When using `gpu: vast`, always report the running cost. If `auto_destroy: true`, destroy the instance as soon as all experiments on it complete

## CLAUDE.md Example

Users should add their server info to their project's `CLAUDE.md`:

```markdown
## Remote Server
- gpu: remote               # use pre-configured SSH server
- launcher: tmux            # canonical launcher for all experiments
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

## Vast.ai
- gpu: vast                  # rent on-demand GPU from vast.ai
- launcher: tmux             # canonical launcher inside the rented instance
- auto_destroy: true         # auto-destroy after experiment completes (default: true)
- max_budget: 5.00           # optional: max total $ to spend per experiment

## Local Environment
- gpu: local                 # use local GPU
- launcher: tmux             # long-running jobs still use tmux locally
- Mac MPS / Linux CUDA
- Conda env: `ml` (Python 3.10 + PyTorch)
```

> **Vast.ai setup**: Run `pip install vastai && vastai set api-key YOUR_KEY`. Upload your SSH public key at https://cloud.vast.ai/manage-keys/. Set `gpu: vast` in your `CLAUDE.md` — `/run-experiment` will automatically rent an instance, run the experiment, and destroy it when done.

> **W&B setup**: Run `wandb login` on your server once (or set `WANDB_API_KEY` env var). The skill reads project/entity from CLAUDE.md and adds `wandb.init()` + `wandb.log()` to your training scripts automatically. Dashboard: `https://wandb.ai/<entity>/<project>`.
