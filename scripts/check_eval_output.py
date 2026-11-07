#!/usr/bin/env python3
"""Exit non-zero unless a libero_eval.py output dir is complete.

Usage: check_eval_output.py <client_dir> <task_ids> <n_episodes_per_task>
Complete = eval_summary.json parses, its episode count is len(task_ids) * n_episodes, and steps.jsonl / episodes.jsonl
are non-empty with matching episode rows. Aborted episodes are already recorded as failures by libero_eval.py; they are
reported on stderr but do not fail the check.
"""
import json
import sys
from pathlib import Path


def parse_ids(s):
    out = []
    for part in s.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b) + 1)) if b else [int(a)]
    return out


def check(client_dir, task_ids, n_episodes):
    d = Path(client_dir)
    want = len(parse_ids(task_ids)) * int(n_episodes)
    summary = d / "eval_summary.json"
    if not summary.is_file():
        return f"missing {summary} (evaluator did not finish)"
    try:
        ev = json.loads(summary.read_text())
    except ValueError as e:
        return f"unreadable {summary}: {e}"
    if ev.get("episodes") != want:
        return f"{summary}: episodes={ev.get('episodes')} expected {want}"
    for name in ("steps.jsonl", "episodes.jsonl"):
        p = d / name
        if not p.is_file() or p.stat().st_size == 0:
            return f"missing or empty {p}"
    n_rows = sum(1 for line in (d / "episodes.jsonl").read_text().splitlines() if line.strip())
    if n_rows != want:
        return f"{d / 'episodes.jsonl'}: {n_rows} rows expected {want}"
    if ev.get("aborted"):
        print(f"warning: {ev['aborted']} of {want} episodes aborted (counted as failures)", file=sys.stderr)
    return None


if __name__ == "__main__":
    err = check(*sys.argv[1:4])
    if err:
        print(f"check_eval_output: FAIL: {err}", file=sys.stderr)
        sys.exit(1)
    print(f"check_eval_output: OK ({sys.argv[1]})")
