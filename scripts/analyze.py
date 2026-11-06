#!/usr/bin/env python3
"""Per-task success, Wilson 95% intervals and latency spread for one or two run dirs.

  scripts/analyze.py <run_dir> [--ref <run_dir>] [--out results/analysis/<name>.json]
Reads client/episodes.jsonl and client/steps.jsonl of the run dir(s); writes nothing else.
"""
import argparse, json, math, statistics
from collections import defaultdict
from pathlib import Path


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


def pct(xs, p):
    xs = sorted(xs)
    k = (len(xs) - 1) * p / 100
    f, c = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def load(d):
    d = Path(d)
    eps = [json.loads(l) for l in open(d / "client" / "episodes.jsonl")]
    steps = [json.loads(l) for l in open(d / "client" / "steps.jsonl")]
    per = defaultdict(lambda: [0, 0])
    for e in eps:
        per[e["task"]][0] += e["success"]
        per[e["task"]][1] += 1
    k, n = sum(v[0] for v in per.values()), sum(v[1] for v in per.values())
    req = [s["ms"] for s in steps if s["req"] and not s["warmup"]]
    per_ep = defaultdict(list)
    for s in steps:
        if s["req"] and not s["warmup"]:
            per_ep[(s["task"], s["ep"])].append(s["ms"])
    ep_means = [statistics.mean(v) for v in per_ep.values()]
    return {
        "run_dir": str(d), "successes": k, "episodes": n, "wilson95": wilson(k, n),
        "per_task": {str(t): {"successes": v[0], "episodes": v[1], "wilson95": wilson(*v)}
                     for t, v in sorted(per.items())},
        "request_ms": {"min": round(min(req), 1), "p50": round(pct(req, 50), 1), "p95": round(pct(req, 95), 1),
                       "p99": round(pct(req, 99), 1), "max": round(max(req), 1), "n": len(req)},
        "episode_mean_request_ms": {"min": round(min(ep_means), 1), "p50": round(pct(ep_means, 50), 1),
                                    "max": round(max(ep_means), 1)},
        "episodes_hitting_500_step_limit": sum(1 for e in eps if e["steps"] >= 500),
    }


def two_prop_diff(a, b):
    p1, p2 = a["successes"] / a["episodes"], b["successes"] / b["episodes"]
    se = math.sqrt(p1 * (1 - p1) / a["episodes"] + p2 * (1 - p2) / b["episodes"])
    return {"diff_pp": round(100 * (p1 - p2), 1),
            "ci95_pp": [round(100 * (p1 - p2 - 1.96 * se), 1), round(100 * (p1 - p2 + 1.96 * se), 1)]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--ref")
    ap.add_argument("--out")
    a = ap.parse_args()
    res = {"run": load(a.run_dir)}
    if a.ref:
        res["ref"] = load(a.ref)
        res["run_minus_ref"] = two_prop_diff(res["run"], res["ref"])
    txt = json.dumps(res, indent=2)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(txt)
    print(txt)
