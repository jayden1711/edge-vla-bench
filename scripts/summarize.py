#!/usr/bin/env python3
"""Turn one run directory (from run_row.sh) into a result row JSON, and/or render the table.

  python3 scripts/summarize.py row <run_dir> --model SmolVLA --params 450M --precision "fp16 (GGUF)" \
      [--fits yes] [--reference-successes N]          -> writes <run_dir>/row.json
  python3 scripts/summarize.py table results/          -> prints markdown table of all row.json
"""
import argparse, glob, json, re, statistics
from pathlib import Path


def pct(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * p / 100
    f, c = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def tegra_peak_ram(path):
    peak = None
    for line in open(path) if Path(path).exists() else []:
        m = re.search(r"RAM (\d+)/(\d+)MB", line)
        if m:
            peak = max(peak or 0, int(m.group(1)))
    return peak


def provenance(setup, ev):
    """Fields every row must carry: runtime/format as used, power mode, clocks, seed, date."""
    p, run = setup.get("platform", {}), setup.get("run", {})
    cpu = [int(c["cur_freq"]) for c in p.get("cpu_freq", {}).values() if c.get("cur_freq")]
    gpu = (p.get("devfreq", {}).get("17000000.gpu") or {})
    mhz = lambda v: round(int(v) / 1e6) if v else None
    return {
        "runtime": run.get("runtime"), "runtime_version": run.get("runtime_version"),
        "format": run.get("precision") or run.get("model_file"),
        "model_ref": run.get("policy") or run.get("model_file"), "model_sha256": run.get("model_sha256"),
        "seed": ev.get("seed"), "role": setup.get("role"), "captured_utc": setup.get("captured_utc"),
        "jetpack": p.get("jetpack"), "power_mode": p.get("power_mode"),
        "cpu_mhz_cur": round(statistics.mean(cpu) / 1000) if cpu else None,
        "gpu_mhz_cur": mhz(gpu.get("cur_freq")), "gpu_mhz_min": mhz(gpu.get("min_freq")),
        "gpu_mhz_max": mhz(gpu.get("max_freq")), "emc_rate_hz": p.get("emc_rate_hz"),
    }


def row(a):
    d = Path(a.run_dir)
    steps = [json.loads(l) for l in open(d / "client" / "steps.jsonl")]
    ev = json.load(open(d / "client" / "eval_summary.json"))
    setup = json.load(open(d / "setup.json"))
    S = ev["n_action_steps"]
    req = [s["ms"] for s in steps if s["req"] and not s["warmup"]]
    all_steps = [s["ms"] for s in steps if not s["warmup"]]
    # vla.cpp boundary: mean over env steps of get_action() wall time (preproc + transport incl.)
    ms_per_action = statistics.mean(all_steps)
    rss = None
    p = d / "server_peak_rss.txt"
    if p.exists():
        rss = round(int(re.search(r"(\d+)", p.read_text()).group(1)) / 1024)
    succ, n = ev["successes"], ev["episodes"]
    r = {
        "model": a.model, "params": a.params, "precision": a.precision, "fits": a.fits,
        "sim_location": setup["run"].get("sim_location"),
        "peak_rss_mib": rss, "peak_system_ram_mib": tegra_peak_ram(d / "tegrastats.log"),
        "p50_ms_per_request": round(pct(req, 50), 1), "p95_ms_per_request": round(pct(req, 95), 1),
        "n_requests_timed": len(req),
        "ms_per_executed_action": round(ms_per_action, 2),
        "ms_per_executed_action_from_p50": round(pct(req, 50) / S, 2),
        "hz": round(1000 / ms_per_action, 1),
        "executed_actions_per_request": S,
        "successes": succ, "episodes": n, "success_rate": round(succ / n, 3), "aborted": ev["aborted"],
        "reference_successes": a.reference_successes,
        "success_delta_pp": (round(100 * (succ - a.reference_successes) / n, 1)
                             if a.reference_successes is not None else None),
        "run_dir": str(d), "setup": setup,
    }
    r.update(provenance(setup, ev))
    (d / "row.json").write_text(json.dumps(r, indent=2))
    print(json.dumps({k: v for k, v in r.items() if k != "setup"}, indent=2))


COLS = ["model", "params", "runtime", "format", "role", "power_mode", "cpu_mhz_cur", "gpu_mhz_cur", "emc_rate_hz",
        "fits", "peak_rss_mib", "p50_ms_per_request", "p95_ms_per_request",
        "ms_per_executed_action", "hz", "success_rate", "success_delta_pp", "sim_location", "seed", "captured_utc",
        "model_ref", "model_sha256", "run_dir"]
LATENCY_COLS = ("p50_ms_per_request", "p95_ms_per_request", "ms_per_executed_action", "hz")

DISCLOSURE = ("Disclosure: the author was an NVIDIA intern until Nov 13, 2026 and founded Quatern. "
              "The Jetson rows run on NVIDIA hardware and software. All accuracy numbers are LIBERO-Object "
              "SIMULATION results, not real-robot results. Runtime and format are listed as used, "
              "not tuned per model; see CRITIQUES.md.")


def table(a):
    # scratch/trash dirs (leading "_") hold copies; reading them duplicated rows
    paths = [p for p in sorted(glob.glob(f"{a.root}/**/row.json", recursive=True))
             if not any(part.startswith("_") for part in Path(p).relative_to(a.root).parts)]
    rows = [json.load(open(p)) for p in paths]
    print("| " + " | ".join(COLS) + " |\n|" + "---|" * len(COLS))
    for r in rows:
        # NUC is shared with other workloads, so only Jetson latency is reported
        blank = LATENCY_COLS if r.get("role") != "jetson" else ()
        print("| " + " | ".join("" if (r.get(c) is None or c in blank) else str(r.get(c)) for c in COLS) + " |")
    print("\n" + DISCLOSURE)
    print("Rows with empty runtime/power_mode were summarized before provenance fields existed; "
          "rerun `summarize.py row` on their run dir.")


def attempts(a):
    """List every run dir under root (complete, partial, failed): nothing is left out of the record."""
    print("| run_dir | has_setup | has_eval_summary | episodes | successes | has_row |\n|---|---|---|---|---|---|")
    for s in sorted(glob.glob(f"{a.root}/*/*/*/setup.json")):
        d = Path(s).parent
        ev = d / "client" / "eval_summary.json"
        e = json.load(open(ev)) if ev.exists() else {}
        print(f"| {d} | yes | {'yes' if e else 'no'} | {e.get('episodes', '')} | {e.get('successes', '')} | "
              f"{'yes' if (d / 'row.json').exists() else 'no'} |")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("row"); p.add_argument("run_dir"); p.add_argument("--model", required=True)
    p.add_argument("--params", required=True); p.add_argument("--precision", required=True)
    p.add_argument("--fits", default="yes"); p.add_argument("--reference-successes", type=int)
    t = sub.add_parser("table"); t.add_argument("root")
    t2 = sub.add_parser("attempts"); t2.add_argument("root")
    a = ap.parse_args()
    {"row": row, "table": table, "attempts": attempts}[a.cmd](a)
