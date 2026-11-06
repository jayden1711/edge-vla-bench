#!/usr/bin/env python3
"""LIBERO episode loop against a running vla-server, with per-request timing.

Same loop and measurement boundary as vla.cpp's eval/client/run_sim_client_direct.py
(v0.4.0): wall time of adapter.get_action() per env step, which includes observation
preprocessing and ZMQ transport. Averaged per step, that is vla.cpp's
"ms per executed action". On top of that we log, for every step, whether it issued a
server request (action queue empty) so p50/p95 per request can be computed.

Differences from upstream, on purpose:
- Episodes aborted by the env count as failures (denominator stays n_episodes), matching
  the paper's "incomplete episodes count as failures". Upstream summary.txt drops them.
- No videos unless --videos (video encoding competes for the Nano's CPU).
- One process runs all task ids, so warm-up is handled once: the first --warmup
  requests are timed but flagged warmup=true and excluded from latency stats.

Run inside vla.cpp's LIBERO venv:
  python scripts/libero_eval.py --vla-root runtimes/vla.cpp --arch smolvla \
      --n-action-steps 4 --task-ids 0-9 --n-episodes 20 --out results/.../run
"""
import argparse, json, sys, time
from pathlib import Path


def parse_ids(s):
    out = []
    for part in s.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b) + 1)) if b else [int(a)]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vla-root", required=True, help="vla.cpp checkout (for eval/client and eval/sim)")
    ap.add_argument("--arch", required=True)
    ap.add_argument("--task", default="libero_object")
    ap.add_argument("--task-ids", default="0-9")
    ap.add_argument("--n-episodes", type=int, default=20, help="per task id")
    ap.add_argument("--n-action-steps", type=int, required=True)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--vla-addr", default="tcp://localhost:5555")
    ap.add_argument("--image-size", type=int, default=None)
    ap.add_argument("--tokenizer", default=None)
    ap.add_argument("--stats-json", default=None)
    ap.add_argument("--warmup", type=int, default=3, help="requests excluded from latency stats")
    ap.add_argument("--videos", action="store_true")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    eval_dir = Path(a.vla_root).resolve() / "eval"
    sys.path.insert(0, str(eval_dir))
    import gymnasium as gym
    import sim.libero  # noqa: F401  registers envs
    from client.vla_cpp_client import VlaCppClient
    from client.adapters import LeRobotPipelineAdapter, Evo1PipelineAdapter

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    import inspect
    sig = inspect.signature(VlaCppClient.__init__).parameters
    kw = dict(arch=a.arch, n_action_steps=a.n_action_steps, tokenizer_name=a.tokenizer,
              image_size=a.image_size, stats_json=a.stats_json)
    kw["vla_addr" if "vla_addr" in sig else "addr"] = a.vla_addr
    inner = VlaCppClient(**{k: v for k, v in kw.items() if k in sig})
    adapter = Evo1PipelineAdapter(client=inner) if a.arch == "evo1" else LeRobotPipelineAdapter(client=inner)

    steps_f = open(out / "steps.jsonl", "w")
    episodes, n_req = [], 0
    t_start = time.time()
    for task_id in parse_ids(a.task_ids):
        env = gym.make(f"{a.task}/task_{task_id}", seed=a.seed, video_fps=30,
                       output_video_dir=(out / "videos" / f"task_{task_id}") if a.videos else None,
                       video_view_mode="multi-view")
        for ep in range(a.n_episodes):
            adapter.reset()
            obs, info = env.reset()
            step, aborted, success = 0, False, 0
            while True:
                is_req = len(inner._action_queue) == 0
                t0 = time.perf_counter()
                action = adapter.get_action(obs)
                dt = (time.perf_counter() - t0) * 1000
                if is_req:
                    n_req += 1
                steps_f.write(json.dumps({"task": task_id, "ep": ep, "step": step, "ms": round(dt, 3),
                                          "req": is_req, "warmup": is_req and n_req <= a.warmup}) + "\n")
                try:
                    obs, reward, done, truncated, info = env.step(action)
                except ValueError as e:
                    if "terminated episode" not in str(e):
                        raise
                    aborted = True
                    break
                step += 1
                if done or truncated:
                    success = int(bool(info.get("is_success", 0)))
                    break
            episodes.append({"task": task_id, "ep": ep, "success": 0 if aborted else success,
                             "steps": step, "aborted": int(aborted)})
            print(f"task {task_id} ep {ep}: success={episodes[-1]['success']} steps={step}"
                  f"{' ABORTED' if aborted else ''}", flush=True)
        env.close()
    steps_f.close()

    with open(out / "episodes.jsonl", "w") as f:
        f.writelines(json.dumps(e) + "\n" for e in episodes)
    summary = {
        "arch": a.arch, "task": a.task, "task_ids": a.task_ids, "n_episodes_per_task": a.n_episodes,
        "n_action_steps": a.n_action_steps, "seed": a.seed, "warmup_requests_excluded": a.warmup,
        "episodes": len(episodes), "successes": sum(e["success"] for e in episodes),
        "aborted": sum(e["aborted"] for e in episodes), "wall_s": round(time.time() - t_start, 1),
    }
    (out / "eval_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
