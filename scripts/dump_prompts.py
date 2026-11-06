#!/usr/bin/env python3
"""Write the verbatim task prompts of a LIBERO suite (what the policies receive) to JSON.

Run in the vla.cpp LIBERO venv:  scripts/dump_prompts.py [suite] [out.json]
"""
import json, os, sys
from libero.libero import benchmark

suite = sys.argv[1] if len(sys.argv) > 1 else "libero_object"
out = sys.argv[2] if len(sys.argv) > 2 else f"results/prompts/{suite}.json"
s = benchmark.get_benchmark_dict()[suite]()
rows = [{"task_id": i, "name": s.get_task(i).name, "prompt": s.get_task(i).language} for i in range(s.n_tasks)]
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({"suite": suite, "tasks": rows}, open(out, "w"), indent=2)
print(f"wrote {out}")
