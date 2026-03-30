---
name: "monitor-experiment"
description: "Monitor running experiments, check progress, collect results. Use when user says \"check results\", \"is it done\", \"monitor\", or wants experiment output."
---

# Monitor Experiment Results

Monitor: $ARGUMENTS

## Workflow

### Step 1: Check What's Running

Prefer `run_id`-based monitoring over raw session-name monitoring.

1. Read `exp/runs/*/run.json`
2. Resolve `session_name`, `log_path`, and `result_path`
3. If the user passed only a host/server alias, list the most recent runs first

```bash
ssh <server> "tmux ls"
```

### Step 2: Collect Output From Each Run

For each active run, capture the recent `tmux` pane output first, then fall back to the persisted log:

```bash
ssh <server> "tmux capture-pane -t <session_name> -p | tail -50"
```

If pane capture fails, check:

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

After results are collected, check `~/.codex/feishu.json`:
- Send `experiment_done` notification: results summary table, delta vs baseline
- If config absent or mode `"off"`: skip entirely (no-op)

## Key Rules
- Always show raw numbers before interpretation
- Compare against the correct baseline (same config)
- Prefer `run_id` + `run.json` over guessing raw session names
- Note if experiments are still running (check `tmux` session, progress bars, iteration counts)
- If results look wrong, check training logs for errors before concluding
