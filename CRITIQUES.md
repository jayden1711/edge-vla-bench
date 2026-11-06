# CRITIQUES: what a skeptical expert would say, and our answer

Every item gets exactly one answer type: **[A]** already addressed (with a pointer), **[B]** an experiment that would
address it (marked *run* if it was cheap and run, *not run* with the reason), or **[C]** a limitation we state up front.
This file contains no result numbers. Numbers live in git-ignored `results/` and every one regenerates with
`make all` (see the Makefile) from the run directories.

All accuracy numbers in this project are **LIBERO-Object simulation** results. None are real-robot results.

## Disclosure (repeated next to every Jetson result)

The author was an NVIDIA intern until Nov 13, 2026 and founded Quatern. The Jetson Orin Nano, JetPack, CUDA and
TensorRT are NVIDIA products. `scripts/summarize.py table` prints this disclosure under every table.
## Prior-work and framing

**1. "vla.cpp already did this."** [A]
vla.cpp (VinRobotics, arXiv 2606.08094, github.com/VinRobotics/vla.cpp, Apache-2.0) is the runtime, the eval loop and
the column definitions we start from. We do not claim first. The `scripts/libero_eval.py` loop is vla.cpp's v0.4.0 loop
plus timing and abort handling (see its header). What this repo adds, and nothing more is claimed:
(a) an independent reproduction of vla.cpp's SmolVLA Orin Nano row on a second unit with a fixed, recorded setup
(`results/jetson/smolvla_calib/`, `results/analysis/smolvla_calib_vs_fp16ref.json`);
(b) a same-seed fp16 PyTorch reference run on a different machine for each row, with the success difference and its
confidence interval (`scripts/analyze.py`);
(c) per-row recording of runtime, format as used, power mode, clocks, seed, date, and machine state before and
after the run (`setup.json`, `setup_end.json`, `row.json`);
(d) raw per-request timings kept, so spreads and not only means can be shown (`client/steps.jsonl`);
(e) planned and not yet done: models vla.cpp does not run (X-VLA via a third party's TensorRT export, see item 15;
7B-class rows, blocked). Until those exist, (a)-(d) are the whole contribution.
Where our numbers differ from vla.cpp's Table III we report the difference as measured and do not explain it away
(known differences are listed in PLAN.md "Calibration" and in items 9 and 10).

**2. "Other related work is missing."** [C]
README and PLAN cite what is relevant to a Jetson VLA benchmark: vla.cpp, eetmie/jetson-orin-nano-vla, arXiv
2604.24447, LIBERO, lerobot and the model papers. The owner's wider reading list (MIT weight-space post, PicoGPT,
Hirundo / CrowdStrike / Booz Allen, RoboStriker, URMA / MetaMorph, Text2Robot) was judged not relevant to this repo's
scope (edge inference of existing VLAs) and is not cited here; the owner should confirm this [verify]. Citations
that could not be checked without web access are marked [verify] in README/PLAN.

## Fairness of the comparison

**3. "You didn't optimize each model fairly."** [A] + [C]
We do not try to. Every row is labeled with the runtime and format *as used* (columns `runtime`, `format`,
`model_ref`, `model_sha256` in `results/TABLE.md`): vla.cpp GGUFs "as shipped" (PLAN.md, "Precision labels"),
upstream PyTorch fp16 for references, a third party's TensorRT export where used. No per-model tuning of batch,
threads, quantization, or flags beyond the runtime's defaults (`server_args` is recorded and was empty for the
calibration row). Consequence stated up front: **rows are not a ranking of models or of runtimes.** A model that is
slow or inaccurate here may be better served by a runtime or quantization we did not try. [C]

**4. "Different runtimes/precisions make the table apples-to-oranges."** [C]
Yes, and the table says so per row. The accuracy delta is always against the same model's fp16 PyTorch reference, so
the comparison that is meaningful is *as-shipped edge row vs its own reference*, not row vs row.

**5. "Power mode and clocks were not controlled, or not fully."** [A] + [C]
Power mode, CPU and GPU clocks (current/min/max/governor) are captured by `scripts/capture_setup.py` for every row
and surfaced in `results/TABLE.md` (`power_mode`, `cpu_mhz_cur`, `gpu_mhz_cur`). The calibration row pins clocks, whereas
vla.cpp's docs say theirs were not changed. [C] Not recorded: the EMC (memory) clock, because reading it needs root
(`emc_rate_hz` is empty); a `sudo jetson_clocks --show` by the owner would close this. Thermal throttling is not
summarized; `tegrastats.log` in each run dir has the temperatures and can be inspected.

**6. "NVIDIA bias."** [A] + [C]
Disclosure above. Mitigations in the design: published third-party numbers are quoted only as calibration targets;
we publish rows that look bad for the hardware too (all rows go in `results/ATTEMPTS.md`, none dropped); the
reference machine is an NVIDIA GPU as well, so the NUC does **not** serve as an NVIDIA-independent check. [C] No
non-NVIDIA edge hardware is tested; we make no claims about other boards.

**7. "Quatern conflict."** [C]
The author founded Quatern. Nothing in this repo depends on Quatern. The NUC is shared with Quatern workloads
(Quatern has priority on it), so NUC timings can be contaminated; for that reason only Jetson latency goes into the
table (the NUC reference is used for accuracy). `setup.json` records load average and top processes at start;
see item 13 for the limits of that.

## Statistics and evidence strength

**8. "One run, one seed, 200 episodes: differences are noise."** [A] + [B]
`scripts/analyze.py` writes per-task successes and Wilson 95% intervals and the interval of the difference between a
row and its reference (`results/analysis/smolvla_calib_vs_fp16ref.json`). Claims in any post are limited to what the
interval supports; a difference inside the interval is described as "no detectable difference", never as parity.
[B] Not run: repeat each row with other seeds (a few more full runs per row). Jetson runs need the organizer's
Jetson session; NUC reference repeats need the GPU lock (held by another project's server during this session).
Until then run-to-run variance is unknown and every row is a single run with seed 42.

**9. "Latency is not comparable to vla.cpp's."** [A] + [C]
We use the same definition (client-side time per request incl. preprocessing and transport, divided by executed
actions; sim step time excluded), documented in PLAN.md "Definitions", and report p50, p95, p99, max, and the spread
of per-episode means (`analyze.py`) next to the mean-based column. Differences that remain: JetPack 6.2.1 vs their
6.2.2, the vla.cpp commit behind their Table III is not stated (we use v0.4.0, f7e0f7f), pinned clocks.
[C] The LIBERO sim runs on the same Jetson as the server (`sim_location=local`), so rendering contends for CPU/GPU/memory
with the policy, as in vla.cpp's setup. `run_row.sh` has a remote-sim mode (`SIM=remote`) that would remove this;
a comparison local vs remote is [B] *not run* (needs the Jetson).

**10. "Memory numbers: RSS is not what unified memory costs."** [A] + [C]
We log both the server's peak RSS (VmHWM, close to vla.cpp's ru_maxrss) and the peak system RAM from `tegrastats`, and
`setup.json` records swap/zram state. [C] On the Nano's unified memory neither is a precise GPU-allocation figure,
and zram was in use by the system when the calibration ran. "Fits" means "completed the run without OOM on this
configuration", not a headroom guarantee. Any difference from vla.cpp's published RSS is reported as measured;
we have not determined its cause.

**11. "LIBERO-Object is easy/saturated and it's simulation."** [C]
Stated everywhere. Success on LIBERO-Object says little about real-robot performance or other suites; we make no
real-robot claim and no claim about LIBERO-Spatial/Goal/10 until run.

**12. "The GGUF conversion may differ from the original model."** [A] + [B]
Accuracy against the same-seed reference of the upstream checkpoint (`HuggingFaceVLA/smolvla_libero` @ 6721902b, the
checkpoint the GGUF was converted from per its model card [verify]) is the end-to-end check
(`success_delta_pp`, with interval). [B] *Not run*: an action-level comparison of the two on fixed observations would
separate conversion error from sampling/seed effects; it needs the GPU (busy) and a small script.
The GGUFs are third-party conversions (`vrfai/*`); hashes are recorded. Existing rows store only a 16-hex prefix of
the sha256 (fixed in `run_row.sh` for new rows; the full hash can be recomputed from the file on the Jetson).

**13. "How do we know nothing else was running on the Jetson?"** [A] + [C]
`setup.json` records load average and top processes by RSS at start; `run_row.sh` now also writes `setup_end.json` at
the end (not present for the calibration row, which predates it). `tegrastats.log` runs throughout. [C] That is evidence,
not proof of isolation; the organizer ran the Jetson row, and background services (jtop, dockerd, tailscaled) were
present at start.

**14. "Seeds: is the seed actually varying episodes?"** [C]
All runs use `--seed 42`, passed to the env at creation as in vla.cpp's loop; successive `env.reset()` calls then
give the episode initial states. We have not verified how LIBERO seeds those resets across runs, so we do not claim
that different seeds give independent samples. [B] *Not run*: a seed sweep (see item 8) would show it.

## X-VLA and later rows

**15. "The X-VLA TensorRT row is untested."** [C]
Correct. `scripts/xvla_trt_client.py` (eetmie TensorRT export, MIT, pinned 6aa4a151) has not been run. The first test
on the NUC needs the GPU lock, which another project's server held for this whole session, so it was not attempted. No
X-VLA claim will be made before it runs and its first action chunk is compared with the PyTorch reference.
Fallback is upstream PyTorch fp16, labeled as such.

**16. "Credit/licensing."** [A]
Every model and tool with revision and license is in THIRD_PARTY.md and PLAN.md. No weights, GGUFs, ONNX or engines
are in git (`.gitignore`). Open item: Evo-1's upstream HF weights have no license field; not used until confirmed.

**17. "Your 7B claims."** [C]
No 7B row exists or is claimed; they are blocked until the owner says go. PLAN.md's wording about price and
the 7B angle is a plan, not a finding.

## Reproducibility and honesty of reporting

**18. "Can I reproduce every number with one command?"** [A] + [C]
`make all` recomputes `row.json`, `results/TABLE.md`, `results/ATTEMPTS.md` and the analysis file from the run dirs;
`make prompts` writes the verbatim prompts (`results/prompts/libero_object.json`). Producing the run dirs themselves
is one command per row: `scripts/run_row.sh` (Jetson) and `scripts/run_reference.sh` (NUC); exact invocations are in
HANDOFF.md. [C] The run dirs are only local until the owner approves publishing; a reader cannot regenerate a
number without them, which is why they are to be published with the post.

**19. "Cherry-picked runs."** [A]
Every run directory, including partial and failed ones (a stopped NUC reference run, a failed X-VLA smoke, a 2-episode
Jetson smoke), is listed by `make attempts` in `results/ATTEMPTS.md`. Rows use the complete run only; no run was
discarded for its result.

**20. "Prompts and isolation proofs."** [A]
Prompts verbatim: `results/prompts/libero_object.json` (from LIBERO's task definitions). Adapter-level formatting
(tokenization, state normalization) is vla.cpp/lerobot code at the pinned commits, not edited by us. Isolation:
`setup.json`, `setup_end.json`, `tegrastats.log`, `server.log`, `client.log` per run dir.
