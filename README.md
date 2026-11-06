# edge-vla-bench

Robot VLA models on an 8 GB Jetson Orin Nano (Super devkit): what fits, how fast, how accurate.
Columns follow vla.cpp (arXiv 2606.08094) Table III so rows compare directly. Scope, protocol,
prior art, and the license and commit of every model and tool are in [PLAN.md](PLAN.md).

This repo holds scripts, configs and results only. It contains no model weights.

## Layout

```
scripts/capture_setup.py   fixed-setup capture (JetPack/L4T, power mode, clocks, runtime, ...) -> JSON
scripts/run_row.sh         one row on the Jetson: setup capture, vla-server, tegrastats, LIBERO client, peak RSS
scripts/libero_eval.py     LIBERO loop with per-request timing (vla.cpp client boundary)
scripts/summarize.py       run dir -> row.json; all row.json -> markdown table
results/jetson/<row>/<utc>/  one directory per run (setup.json, steps.jsonl, episodes.jsonl, row.json, logs)
results/nuc/<row>/<utc>/     fp16 reference runs
runtimes/                  third-party runtimes, cloned at pinned commits (git-ignored)
```

## Results

See [results/TABLE.md](results/TABLE.md).
