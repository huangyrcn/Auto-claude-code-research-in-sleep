#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "run"


def build_run_id(slug: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"r{timestamp}-{slug}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create exp/run manifest artifacts for ARIS tmux experiments.",
    )
    parser.add_argument("--project-root", default=".", help="Project root. Defaults to cwd.")
    parser.add_argument("--slug", required=True, help="Short slug for the run id.")
    parser.add_argument("--command", required=True, help="Exact experiment command to run.")
    parser.add_argument("--gpu-mode", default="local", help="local | remote | vast")
    parser.add_argument("--host", default="", help="SSH host or vast endpoint label.")
    parser.add_argument("--remote-root", default="", help="Remote root directory.")
    parser.add_argument("--remote-workdir", default="", help="Explicit remote workdir override.")
    parser.add_argument("--session-prefix", default="aris", help="Tmux session prefix.")
    parser.add_argument("--runs-dir", default="exp/runs", help="Run manifest directory.")
    parser.add_argument("--logs-dir", default="exp/logs", help="Log directory.")
    parser.add_argument("--results-dir", default="exp/results", help="Result directory.")
    parser.add_argument("--activation-cmd", default="", help="Optional shell snippet before command.")
    parser.add_argument("--status", default="launching", help="Initial manifest status.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    project_root = Path(args.project_root).resolve()
    project_name = project_root.name
    slug = slugify(args.slug)
    run_id = build_run_id(slug)
    session_name = f"{args.session_prefix}-{run_id}"

    runs_dir = Path(args.runs_dir)
    logs_dir = Path(args.logs_dir)
    results_dir = Path(args.results_dir)
    run_dir = project_root / runs_dir / run_id
    log_path = (logs_dir / f"{run_id}.log").as_posix()
    result_path = (results_dir / f"{run_id}.json").as_posix()

    remote_workdir = args.remote_workdir
    if not remote_workdir and args.remote_root:
        remote_workdir = f"{args.remote_root.rstrip('/')}/{project_name}"
    if not remote_workdir and args.gpu_mode == "vast":
        remote_workdir = "/workspace/project"

    run_dir.mkdir(parents=True, exist_ok=True)
    (project_root / logs_dir).mkdir(parents=True, exist_ok=True)
    (project_root / results_dir).mkdir(parents=True, exist_ok=True)

    launch_path = run_dir / "launch.sh"
    launch_lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        f"export ARIS_RUN_ID={run_id}",
        f"export ARIS_SESSION_NAME={session_name}",
        f"export ARIS_LOG_PATH={log_path}",
        f"export ARIS_RESULT_PATH={result_path}",
        "",
        f"mkdir -p {logs_dir.as_posix()} {results_dir.as_posix()}",
    ]
    if args.activation_cmd:
        launch_lines.extend(["", args.activation_cmd])
    launch_lines.extend(
        [
            "",
            f"{args.command} 2>&1 | tee {log_path}",
            "",
        ]
    )
    launch_path.write_text("\n".join(launch_lines))
    launch_path.chmod(0o755)

    manifest = {
        "run_id": run_id,
        "slug": slug,
        "session_name": session_name,
        "launcher": "tmux",
        "gpu_mode": args.gpu_mode,
        "host": args.host or None,
        "remote_root": args.remote_root or None,
        "remote_workdir": remote_workdir or None,
        "runs_dir": runs_dir.as_posix(),
        "log_path": log_path,
        "result_path": result_path,
        "command": args.command,
        "activation_cmd": args.activation_cmd or None,
        "status": args.status,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    manifest_path = run_dir / "run.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
