# HANDOFF (2026-11-06)
Status: Harness built; SmolVLA fp16 reference done on NUC (local); Jetson unreachable overnight; X-VLA needs LIBERO processor wiring
Next: Fix `jetson` ssh access from the NUC, then rsync, smoke test, SmolVLA calibration row
Updated: 2026-11-06 (overnight run)

Session stopped at the owner's request. No benchmark rows exist yet. The first stop point
(calibration row + SmolVLA, X-VLA, Evo-1 rows) is **not** reached.

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
- Precision label for the vla.cpp rows: the GGUFs are "as shipped" (vla.cpp's own dtype choice,
  `--weight-dtype` defaults to bf16 in its eval script). Is that fine as the "fp16 as-is" row, or
  should we force fp16?
- X-VLA runtime: upstream PyTorch fp16 on the Jetson (current plan) or eetmie's TensorRT export.
  eetmie's repo is benchmark-only (no LIBERO driving) and was measured on JetPack 7.2.1.
- Optional: run `sudo jetson_clocks --show` once so the EMC clock goes on record. The scripts can't
  read it without sudo.

## Uncommitted
Nothing is uncommitted in this repo. Weights, runtimes/ and venvs are git-ignored on purpose.

## Note on the NUC
At capture time the NUC was also running Quatern processes (user `quatern`, several python3 at
high CPU). That doesn't change reference accuracy, but NUC latency numbers aren't clean. Only
Jetson latency goes in the table.
