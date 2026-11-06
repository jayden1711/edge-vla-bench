# HANDOFF (2026-11-06)
Status: SmolVLA Jetson calibration row and NUC fp16 reference both done (local results); CRITIQUES.md, analysis/attempts/prompts scripts and Makefile added; X-VLA bridge still untested (GPU lock busy)
Next: organizer reviews branch day-1106 and pushes; X-VLA bridge test when the GPU lock frees; then X-VLA and Evo-1 rows, seed repeats; owner confirms the [verify] items
Updated: 2026-11-06 (daytime run 2, branch day-1106, not pushed)

First stop point (calibration row + SmolVLA, X-VLA, Evo-1 rows): calibration and SmolVLA done; X-VLA and Evo-1 not yet.
The Jetson steps listed under older decisions below were done by the organizer (rows are in results/jetson/).

## Decisions taken (day-1106, criticism-proofing run)
- **Branch**: the earlier session left empty worktrees `critiques` and `day-1106` under `.claude/worktrees/` (no commits).
  Used the existing `day-1106` one; both branches are at main's commit. `critiques` is unused.
- **CRITIQUES.md** written (20 items, no result numbers). Calibration row copied by the organizer is analyzed in
  `results/analysis/smolvla_calib_vs_fp16ref.json` (local). `make all` regenerates rows, TABLE.md, ATTEMPTS.md, analysis.
- **X-VLA bridge test not run**: gpu-run lock held by robot-framing-test (Qwen server) all session. Blocked, nothing started.
- **Conservative choices**: other prior work from the owner's list (MIT post, PicoGPT, Hirundo/CrowdStrike/Booz Allen,
  RoboStriker, URMA/MetaMorph, Text2Robot) judged not relevant to this repo and not cited (flagged in CRITIQUES.md item 2
  for the owner); unverifiable arXiv ids marked [verify]; the "$249" price claim in PLAN.md replaced by a [verify] note.
- **Harness changes**: `run_row.sh` now stores the full model sha256 and writes `setup_end.json`; `summarize.py` rows carry
  runtime, format, power mode, clocks, seed, date and the table prints the disclosure; new `attempts` subcommand.
  Existing Jetson row keeps the 16-hex sha prefix and has no `setup_end.json`.
- **Mistake noted**: one no-op inline python heredoc was run by accident (prints a string, no effect).
- Not done: seed repeats, GGUF-vs-PyTorch action comparison, remote-sim latency comparison (need GPU/Jetson; listed as [B] in CRITIQUES.md).

## Decisions taken (day-1106, resumed session)
- **X-VLA checkpoint**: `lerobot/xvla-libero` @ 8e6aeef01f634f5d3b5be4340328f19cc2c25a65 (owner decision);
  PLAN.md and THIRD_PARTY.md updated (reason: the LIBERO processors target it; Apache-2.0).
- **Jetson ssh denied again**: the permission layer refused `ssh jetson ...`. Per the organizer's note I did not
  work around it; nothing was run on the Jetson. Run these from the NUC (repo root = this worktree or main after merge):
  1. `rsync -a --exclude .git --exclude runtimes/ --exclude weights/ --exclude results/ ./ jetson:edge-vla-bench/`
  2. smoke: `ssh jetson 'cd ~/edge-vla-bench && TASK_IDS=0 N_EPISODES=2 scripts/run_row.sh smoke ~/edge-vla-bench/weights/smolvla-libero-gguf/smolvla-libero.gguf smolvla 4 --run precision=as-shipped --run chunk=50 --run cameras=2 --run resolution=512'`
  3. calibration: same with `ROW=smolvla_calib` (10 tasks x 20 episodes), then copy the run dir back into
     `results/jetson/` and compare with vla.cpp Table III as in step 3 below.
  Anything needing sudo on the Jetson (cuDSS for the torch wheel, `jetson_clocks --show`) is still listed under
  "In progress" and "Open decisions"; do not run it unattended.
- **GPU/sim cap**: gpu-run lock held by the Qwen server (llama-server, ~10 GiB) and 4 sim-run processes were
  already running, so no GPU or sim job was started (no X-VLA reference run, no stub test of the bridge).
- **eetmie LIBERO bridge written, untested**: `scripts/xvla_trt_client.py` + `--backend xvla-trt` in
  `scripts/libero_eval.py` (`--eetmie-root --bundle --trt-cache --policy --revision`). The client reuses
  lerobot's checkpoint pre/post-processors on CPU and replaces only model execution with eetmie's
  `bench.vendor.xvla_trt.infer` (noise x1 drawn from a seeded generator, gripper sigmoid inside `infer`).
  Runtime cloned to `runtimes/eetmie-jetson-vla` at 6aa4a151 (ignored). Known open points to verify first:
  (a) the bundle must be exported from `lerobot/xvla-libero` on the NUC (`./export.sh lerobot/xvla-libero`, 2 views),
  (b) that eetmie's `infer` output is in the same space the checkpoint post-processor expects (compare the first
  chunk with the PyTorch reference), (c) one interpreter needs tensorrt + lerobot + LIBERO together, which the
  Jetson envs don't provide yet. Fallback stays upstream PyTorch fp16.
- **Evo-1 reference**: still skipped (see overnight decisions).

## Decisions taken (day-1106, daytime run)
- **Owner decisions recorded**: vla.cpp rows are "as shipped" (PLAN.md "Precision labels"). X-VLA uses
  eetmie's TensorRT export if the license allows: `gh api repos/eetmie/jetson-orin-nano-vla/license` says MIT, so
  it is allowed. Credited in THIRD_PARTY.md (pinned 6aa4a151), row label "TensorRT export by eetmie", PLAN.md updated.
  Its repo doesn't drive LIBERO, so a LIBERO bridge is still to write; fallback is upstream PyTorch fp16.
- **Jetson ssh**: `ssh -o BatchMode=yes -o ConnectTimeout=5 jetson true` was blocked by this session's
  permission layer (command denied, not a connection result), so I don't know whether it works. Nothing was done on
  the Jetson; steps 1-3 below are still open.
- **GPU busy**: robot-framing-test's server holds the gpu-run lock (non-preemptible, hours), so no GPU job ran.
  The X-VLA NUC reference run is not done.
- **X-VLA LIBERO wiring (NUC)**: `scripts/libero_eval.py --arch xvla --backend lerobot` now mirrors lerobot's own
  eval pipeline: raw env obs, `preprocess_observation`, lerobot's X-VLA env pre-processor (20-d state from eef pose,
  image flip, ImageNet norm, domain id), then the checkpoint processors and policy in the client, then rot6d to
  axis-angle for the 7-d action. Checked on a real LIBERO env with a stub (CPU, via sim-run): state (1,20), images
  (1,3,256,256), domain_id, 7-d action out. The policy itself has not been run through it yet.
  Run it with `scripts/run_reference.sh xvla_fp16_ref xvla lerobot/xvla-libero 8e6aeef01f634f5d3b5be4340328f19cc2c25a65 <S>`
  under `gpu-run --need-mib 4096 -- sim-run ...` once the GPU is free. The checkpoint question is settled (lerobot/xvla-libero, owner decision).

## Decisions taken overnight
- **Jetson unreachable**: `ssh jetson` fails with "Could not resolve hostname" from the NUC. There is no
  ~/.ssh/config on this machine and the Jetson isn't in `tailscale status`. Steps 1-3 (rsync, smoke,
  calibration) and the Jetson venv fix were not attempted. Nothing was changed on the Jetson.
- **SmolVLA fp16 reference rerun and completed** (full 10 tasks x 20 episodes) under
  `results/nuc/smolvla_fp16_ref/20261106T080842Z/` (local, git-ignored; `row.json` made with summarize.py).
  Ran as `gpu-run --need-mib 4096 -- sim-run scripts/run_reference.sh ...`, run locally on the NUC (no ssh).
  The earlier PARTIAL dir is kept. Compare against the Jetson calibration row once that exists.
- **Evo-1 reference skipped**: lerobot 0.4.3 has no Evo-1 policy (policies: groot, pi0, pi05, pi0_fast, wall_x,
  xvla, smolvla). It needs the MINT-SJTU/Evo-1 code, its own deps and a new adapter, and its HF weights have
  no license field. Conservative choice: not started.
- **X-VLA smoke on the NUC attempted and not usable yet**: `lerobot/xvla-libero` is
  8e6aeef01f634f5d3b5be4340328f19cc2c25a65 (apache-2.0; PLAN.md lists `2toINF/X-VLA-Libero` @ 129e7146, so
  the checkpoint to use needs deciding). The model loads and runs, but outputs 20-dim actions and the env
  expects 7 (`AssertionError ... expected 7, got 20`). lerobot ships `make_xvla_libero_pre_post_processors()`
  (envs/factory.py) that does rot6d to axis-angle and builds the 20-d state from the raw eef pose. Our
  LeRobotTorchClient uses the checkpoint's own processors on the vla.cpp adapter's observations, which lack
  that. Fix: feed raw LIBERO obs through lerobot's env processors. I didn't guess a conversion, because a
  wrong one would give misleading accuracy. Smoke dir: `results/nuc/xvla_smoke/` (failed, local).
- **Verified**: vla-server prints "vla-server: bound to ... ready." with stdout unbuffered/line-buffered
  (src/serving/server.cpp:323), so `run_row.sh`'s ready grep works. `tegrastats` without sudo is still
  unchecked (Jetson).
- The gpu-run lock was briefly held by walk-anything (preemptible); it yielded as designed.

## Done
- Repo skeleton, PLAN.md (prior art, protocol, columns, model and tool licenses and commits), README.
- `scripts/capture_setup.py`: fixed-setup capture. Tested on the Jetson and the NUC.
- `scripts/libero_eval.py`: the vla.cpp v0.4.0 LIBERO loop, plus per-request timing, aborted
  episodes counted as failures, and a `--backend lerobot` path for upstream PyTorch policies.
- `scripts/run_row.sh` (Jetson row runner), `scripts/run_reference.sh` (NUC fp16 reference),
  `scripts/summarize.py` (run dir to row.json, and the markdown table), `scripts/setup_reference_env.sh`.
- Jetson (`ssh jetson`): vla.cpp v0.4.0 (f7e0f7f) **built** with CUDA, sm_87, at
  `~/edge-vla-bench/runtimes/vla.cpp/build/vla-server`. Its LIBERO venv was set up by vla.cpp's
  `setup_libero.sh`, which finished; that venv has not been smoke-tested on the Jetson yet.
  GGUFs downloaded (full size verified) to `~/edge-vla-bench/weights/{smolvla,evo1}-libero-gguf/`
  (outside git).
- NUC (`ssh nuc-admin`): vla.cpp checkout and LIBERO venv. `runtimes/ref_uv` venv (torch 2.14.1/cu130,
  lerobot 0.4.3) works on the RTX 5080. A smoke test of the SmolVLA fp16 reference ran (result in results/, local).

## In progress / stopped
- SmolVLA fp16 reference on the NUC: done (see Decisions taken overnight). The 20261106T062710Z dir is the
  old PARTIAL run.
- **Jetson PyTorch venv (`runtimes/ref_uv`, for X-VLA): failed.** The JP6 torch 2.11.0 wheel from
  the Jetson AI Lab index needs `libcudss.so.0`, which isn't installed. Fix: install cuDSS
  (needs sudo), or pin an older wheel (torch 2.8.0 / torchvision 0.23 from the same index).
  Then rerun `bash scripts/setup_reference_env.sh` on the Jetson.

## Next steps (in order)
1. Sync the repo to the Jetson: `rsync -a --exclude .git --exclude runtimes/ --exclude weights/ ./ jetson:edge-vla-bench/`
2. Smoke test (1 task, 2 episodes):
   `ssh jetson 'cd ~/edge-vla-bench && TASK_IDS=0 N_EPISODES=2 scripts/run_row.sh smoke ~/edge-vla-bench/weights/smolvla-libero-gguf/smolvla-libero.gguf smolvla 4 --run precision=as-shipped --run chunk=50 --run cameras=2 --run resolution=512'`
   Check the server's ready line. `run_row.sh` waits for "listening|ready|bound" in server.log,
   which isn't verified against vla-server's actual output. Also check that `tegrastats` runs without sudo.
3. Calibration: the same command with `ROW=smolvla_calib`, all 10 tasks x 20 episodes. Then
   `python3 scripts/summarize.py row <run_dir> --model SmolVLA --params 450M --precision "GGUF as shipped"`.
   Compare with vla.cpp Table III: 141.81 ms/action, 176/200, 2031 MiB. If latency differs by more
   than ~15% or successes by more than ~10, investigate before going on. Known differences: JetPack
   6.2.1 vs their 6.2.2, our clocks are pinned, and the Table III commit is unknown.
4. (SmolVLA fp16 reference done.) Evo-1 (vla.cpp, S=8 per Table III) and its
   reference (`MINT-SJTU/Evo1_LIBERO` @ 3ddc6c9c; the lerobot backend may not support Evo-1, check).
5. X-VLA: fix the Jetson torch venv, then `libero_eval.py --backend lerobot --policy lerobot/xvla-libero
   --revision 8e6aeef0...`. Check that the vla.cpp LIBERO adapter's observation and action format
   suits X-VLA. It may need lerobot's own LIBERO processors.
6. Fill `results/TABLE.md` with `scripts/summarize.py table results/`, report to the owner, and stop.
   7B rows wait for the owner's go-ahead.

## Open decisions for the owner
- Resolved 2026-11-06: precision label ("as shipped"), X-VLA runtime (eetmie TensorRT, MIT).
- Optional: run `sudo jetson_clocks --show` once so the EMC clock goes on record. The scripts can't
  read it without sudo.

## Uncommitted
Day-1106 work is committed on branch day-1106 (local, not pushed). Weights, runtimes/ and venvs are git-ignored on purpose.

## Note on the NUC
At capture time the NUC was also running Quatern processes (user `quatern`, several python3 at
high CPU). That doesn't change reference accuracy, but NUC latency numbers aren't clean. Only
Jetson latency goes in the table.
