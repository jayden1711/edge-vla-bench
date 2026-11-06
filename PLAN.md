# edge-vla-bench: plan

Benchmark of robot VLA models on an 8 GB Jetson Orin Nano: what fits, how fast, how accurate.

Rules: the repo stays private until the owner says otherwise. No model weights or converted
artifacts are committed or redistributed (`.gitignore` blocks them). Only scripts, configs and
results go in the repo. Nothing gets posted publicly without the owner's go-ahead.

## Prior art (we do not claim "first")

| Work | What it covers | Relation to us |
|---|---|---|
| vla.cpp, arXiv 2606.08094 (v2, 21 Sep 2026), github.com/VinRobotics/vla.cpp, Apache-2.0 | llama.cpp-based runtime. Table III gives Orin Nano rows for SmolVLA, BitVLA, Evo-1, GR00T-N1.5, pi0; GR00T-N1.6/1.7 OOM | Our calibration target. We use their columns so rows compare directly |
| eetmie/jetson-orin-nano-vla | Split ONNX + TensorRT exports of SmolVLA and X-VLA for the 8 GB Nano | Alternative runtime path for SmolVLA/X-VLA |
| arXiv 2604.24447 | Cross-hardware VLA leaderboard, no Orin Nano | Context only |

Our angle: 7B-class models on the $249 board, plus models others skipped.

## Hardware

| Role | Machine | Access |
|---|---|---|
| Device under test | Jetson Orin Nano 8 GB devkit (Super), hostname `jayden-desktop` | `ssh jetson` (Tailscale) |
| Reference / simulator / conversions | NUC, RTX 5080 **Laptop** GPU 16 GB, Ubuntu 24.04.5, driver 595.99.02 | `ssh nuc-admin` |

Nothing else runs on the Jetson during benchmarks. `capture_setup.py` records the top processes by
RSS and the load average in every result file so this can be checked after the fact.

## Fixed setup (recorded in every result file by `scripts/capture_setup.py`)

Machine side (captured automatically): device model, L4T and JetPack, power mode, CPU and GPU
clocks (cur/min/max/governor), inferred jetson_clocks state, EMC rate (root only), CUDA,
TensorRT, cuDNN, swap/zram, OS, kernel, memory, load average, top processes.

Run side (passed with `--run key=value`, missing ones are flagged in `missing_run_fields`):
runtime, runtime_version (commit), precision, batch (always 1), chunk (actions produced per
request), executed_actions (actions executed per request), resolution, cameras, warmup_excluded,
sim_location (`local` or `remote-nuc`).

Current Jetson state (2026-11-06): L4T R36.4.7 (JetPack 6.2.1), MAXN_SUPER, CPU 1.728 GHz and
GPU 1.02 GHz pinned (min = max, so jetson_clocks appears active), CUDA 12.6, TensorRT 10.3.0.30.

## Columns

Model, params, precision/method, fits (yes / OOM / needs remote sim), peak RSS (MiB),
p50 and p95 ms per request, ms per executed action, Hz, success rate, success delta vs fp16
reference on the NUC.

Definitions (matching vla.cpp Table III):
- ms per executed action = client-side inference time per request, including preprocessing and
  transport, divided by executed actions per request S. Excludes time spent stepping the sim.
- Hz = 1000 / (ms per executed action).
- Peak RSS = peak process RSS of the policy server (getrusage ru_maxrss, as in vla.cpp's Nano doc).
  We also log peak system used memory from tegrastats, because on the Nano's unified memory
  process RSS can miss some GPU allocations.
- Warm-up requests are excluded (first episode's first 3 requests at minimum).

## Accuracy protocol

- Manipulation models: LIBERO-Object, 10 tasks x 20 episodes = 200 episodes, as in vla.cpp
  Table III (their `eval/run_libero.sh`, seed 42 default). Incomplete episodes count as failures.
  The sim runs on the Jetson when it fits next to the model; otherwise it runs on the NUC and only
  the policy runs on the Jetson over the network. Each row says which (`sim_location`).
- Navigation models (OmniVLA): LIBERO doesn't apply. They use the eval from the owner's workshop
  paper and go in a separate section of the table.
- Every model gets an fp16 reference run on the NUC with the upstream PyTorch checkpoint, same
  suite, episodes and seed. Each Jetson row reports its success delta against that.

## Calibration

Before anything new: reproduce vla.cpp's SmolVLA Nano row.

| Source | S | ms / executed action | successes / 200 | peak RSS (MiB) |
|---|---|---|---|---|
| vla.cpp Table III, Orin Nano | 4 | 141.81 | 176 | 2031 |

Known differences we start with: their Nano docs list JetPack 6.2.2 (L4T R36.5); ours is 6.2.1
(L4T R36.4.7). Their jetson_clocks state was "not changed"; ours is pinned. The vla.cpp commit for
Table III is not stated; we use the v0.4.0 tag (closest release after paper v2).
If our numbers differ by more than ~15% latency or ~10 successes, find out why before continuing.

## Models

First stop point: calibration row + three as-is models. 7B rows do not start until the owner says so.

| # | Model | Row(s) | Checkpoint (HF id @ revision) | License | Status |
|---|---|---|---|---|---|
| 1 | SmolVLA (450M) | fp16 as-is (vla.cpp) | `vrfai/smolvla-libero-gguf` @ 349851cd (GGUF of `HuggingFaceVLA/smolvla_libero` @ 6721902b) | Apache-2.0 | calibration, in progress |
| 2 | X-VLA (0.9B) | fp16 as-is | `2toINF/X-VLA-Libero` @ 129e7146; code github.com/2toinf/X-VLA @ 6c4ecfb8 | Apache-2.0 | todo; runtime TBD (not in vla.cpp) |
| 3 | Evo-1 | fp16 as-is (vla.cpp) | `vrfai/evo1-libero-gguf` @ c76eb353 (GGUF of `MINT-SJTU/Evo1_LIBERO` @ 3ddc6c9c); code github.com/MINT-SJTU/Evo-1 @ 5fd14b01 | GGUF repo: Apache-2.0; upstream code: MIT; upstream HF weights: no license field, to confirm | todo |
| 4 | pi0 | standard int8 / as published | TBD | TBD | later |
| 5 | pi0.5 | standard int8 / as published | TBD | TBD | later |
| 6 | BitVLA | as published (1.58-bit) | TBD | TBD | later |
| 7 | OpenVLA-OFT (7B) | generic 4-bit; plus one row per compression method | TBD | TBD | **blocked until owner says go** |
| 8 | OmniVLA (7B, nav) | generic 4-bit; plus one row per compression method | TBD | TBD | **blocked until owner says go** |
| - | MolmoAct-7B | optional later | | | |
| - | GR00T | skipped; cite vla.cpp's numbers | | | |

7B rows: the owner's OmniVLA recipe (CoRL 2026 workshop paper) is a reference, not a
requirement. Each compression method is its own row with a clear name, and the generic 4-bit
baseline row always sits next to it so any gain is measurable.

## Tools (license and commit)

| Tool | Where | Version / commit | License |
|---|---|---|---|
| vla.cpp | Jetson + NUC | v0.4.0 = f7e0f7f89f290a4a6f231f9a83bc2237a61e425e | Apache-2.0 |
| llama.cpp (fetched and pinned by vla.cpp CMake) | Jetson | ggml 0.25.3 @ 4da633776 (as reported by configure) | MIT |
| LIBERO | Jetson + NUC | cloned by vla.cpp `setup_libero.sh`; commit to record | MIT |
| lerobot (sim client deps) | Jetson + NUC | 0.4.3 | Apache-2.0 |
| MuJoCo | Jetson + NUC | 2.3.2 | Apache-2.0 |
| uv | Jetson 0.12.10, NUC 0.13.7 | | Apache-2.0 / MIT |

## Open issues

1. **The GitHub repo `jayden1711/edge-vla-bench` is currently PUBLIC** (empty, created
   2026-11-06). Nothing has been pushed. It must be made private before the first push.
2. `sudo` on the Jetson needs a password, so EMC clock and the jetson_clocks state can only be
   inferred, not read. Fine for now; the owner may want to record `sudo jetson_clocks --show` once.
3. X-VLA is not supported by vla.cpp; pick a runtime (upstream PyTorch fp16 or the
   eetmie TensorRT export) and say which in its row.
