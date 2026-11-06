# edge-vla-bench: Claude rules

**Read `~/projects/NUC_RULES.md` first.** It covers Quatern priority, sim-run/gpu-run, the results policy and publishing.

Robot VLA models on an 8 GB Jetson Orin Nano: what fits, how fast, how accurate. Plan: PLAN.md. State: HANDOFF.md.

- **Public repo, Apache-2.0.** Code, configs and docs only. Every run dir, setup.json, log, row and table stays in
  git-ignored `results/` until the owner approves publishing. README/PLAN/HANDOFF quote no numbers of ours
  (published third-party numbers we calibrate against are fine).
- **No weights or converted artifacts in git, ever** (GGUF, safetensors, ONNX, engines). Runtimes are cloned
  at pinned commits by scripts into `runtimes/` (ignored). Every model and tool is listed with revision and
  license in THIRD_PARTY.md and PLAN.md.
- **Machines:**
  - NUC: fp16 reference runs. Always use `~/projects/bin/gpu-run --need-mib <N> --label edge-vla-bench -- ...`;
    the LIBERO sim side goes through `sim-run`.
  - Jetson (`ssh jetson`): deploy target. Rsync code there with
    `rsync -a --exclude .git --exclude runtimes/ --exclude weights/ --exclude results/ ./ jetson:edge-vla-bench/`.
    Don't edit on the Jetson. Copy results back into `results/jetson/`.
- 7B rows (OpenVLA-OFT, OmniVLA) are blocked until the owner says go.
