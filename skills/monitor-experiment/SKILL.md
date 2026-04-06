---
name: monitor-experiment
description: Monitor running experiments, check progress, collect results. Use when user says "check results", "is it done", "monitor", or wants experiment output.
argument-hint: [run-id or server-alias]
allowed-tools: Bash(ssh *), Bash(echo *), Read, Write, Edit
---

# Monitor Experiment Results

Monitor: $ARGUMENTS

## Workflow

### Step 1: Check What's Running

Prefer `run_id`-based monitoring over raw session-name monitoring.

1. Read `exp/runs/*/run.json` and identify the most relevant run(s)
2. Resolve `session_name`, `host`, `log_path`, and `result_path`
3. If the user passed only a host/server alias, list the most recent run manifests first

**SSH server:**
```bash
ssh <server> "tmux ls"
```

**Vast.ai instance** (read `ssh_host`, `ssh_port` from `vast-instances.json`):
```bash
ssh -p <PORT> root@<HOST> "tmux ls"
```

Also check vast.ai instance status:
```bash
vastai show instances
```

**Modal** (when `gpu: modal` in CLAUDE.md):
```bash
modal app list         # List running/recent apps
modal app logs <app>   # Stream logs from a running app
```
Modal apps auto-terminate when done — if it's not in the list, it already finished. Check results via `modal volume ls <volume>` or local output.

### Step 2: Collect Output From Each Run

For each active run, capture recent output from the `tmux` pane first, then fall back to the log file:

**SSH server:**
```bash
ssh <server> "tmux capture-pane -t <session_name> -p | tail -50"
```

**Vast.ai instance:**
```bash
ssh -p <PORT> root@<HOST> "tmux capture-pane -t <session_name> -p | tail -50"
```

If pane capture fails, inspect the persisted log:

```bash
tail -50 exp/logs/<run_id>.log
ssh <server> "tail -50 <remote_workdir>/exp/logs/<run_id>.log"
```

### Step 3: Check for JSON Result Files
```bash
ls -lt exp/results/*.json 2>/dev/null | head -20
ssh <server> "ls -lt <remote_workdir>/exp/results/*.json 2>/dev/null | head -20"
```

If JSON results exist, fetch and parse them:
```bash
cat exp/results/<run_id>.json
ssh <server> "cat <remote_workdir>/exp/results/<run_id>.json"
```

Also inspect `exp/runs/<run_id>/run.json` to determine:

- launcher (`tmux`)
- session name
- status
- launch command
- host / remote workdir
- log path / result path

### Step 3.5: Pull W&B Metrics (when `wandb: true` in CLAUDE.md)

**Skip this step entirely if `wandb` is not set or is `false` in CLAUDE.md.**

Pull training curves and metrics from Weights & Biases via Python API:

```bash
# List recent runs in the project
ssh <server> "python3 -c \"
import wandb
api = wandb.Api()
runs = api.runs('<entity>/<project>', per_page=10)
for r in runs:
    print(f'{r.id}  {r.state}  {r.name}  {r.summary.get(\"eval/loss\", \"N/A\")}')
\""

# Pull specific metrics from a run (last 50 steps)
ssh <server> "python3 -c \"
import wandb, json
api = wandb.Api()
run = api.run('<entity>/<project>/<run_id>')
history = list(run.scan_history(keys=['train/loss', 'eval/loss', 'eval/ppl', 'train/lr'], page_size=50))
print(json.dumps(history[-10:], indent=2))
\""

# Pull run summary (final metrics)
ssh <server> "python3 -c \"
import wandb, json
api = wandb.Api()
run = api.run('<entity>/<project>/<run_id>')
print(json.dumps(dict(run.summary), indent=2, default=str))
\""
```

**What to extract:**
- **Training loss curve** — is it converging? diverging? plateauing?
- **Eval metrics** — loss, PPL, accuracy at latest checkpoint
- **Learning rate** — is the schedule behaving as expected?
- **GPU memory** — any OOM risk?
- **Run status** — running / finished / crashed?

**W&B dashboard link** (include in summary for user):
```
https://wandb.ai/<entity>/<project>/runs/<run_id>
```

> This gives the auto-review-loop richer signal than just pane output — training dynamics, loss curves, and metric trends over time.

### Step 4: Summarize Results

Present results in a comparison table:
```
| Experiment | Metric | Delta vs Baseline | Status |
|-----------|--------|-------------------|--------|
| Baseline  | X.XX   | —                 | done   |
| Method A  | X.XX   | +Y.Y              | done   |
```

### Step 5: Interpret
- Compare against known baselines
- Flag unexpected results (negative delta, NaN, divergence)
- Suggest next steps based on findings

### Step 6: Feishu Notification (if configured)

After results are collected, check `~/.claude/feishu.json`:
- Send `experiment_done` notification: results summary table, delta vs baseline
- If config absent or mode `"off"`: skip entirely (no-op)

## Key Rules
- Always show raw numbers before interpretation
- Compare against the correct baseline (same config)
- Prefer `run_id` + `run.json` over guessing session names
- Note if experiments are still running (check `tmux` session, progress bars, iteration counts)
- If results look wrong, check training logs for errors before concluding
- **Vast.ai cost awareness**: When monitoring vast.ai instances, report the running cost (hours * $/hr from `vast-instances.json`). If all experiments on an instance are done, remind the user to run `/vast-gpu destroy <instance_id>` to stop billing
- **Modal cost awareness**: Modal auto-scales to zero — no idle billing. When reporting results from Modal runs, note the actual execution time and estimated cost (time * $/hr from the GPU tier used). No cleanup action needed
