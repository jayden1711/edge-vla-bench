# CRITIQUES: what a skeptical expert would say, and our answer

Every item gets exactly one answer type: **[A]** already addressed (with a pointer), **[B]** an experiment that would
address it (marked *run* if it was cheap and run, *not run* with the reason), or **[C]** a limitation we state up front.
This file contains no result numbers. Numbers live in git-ignored `results/` and every one regenerates with
`make all` (see the Makefile) from the run directories.

All accuracy numbers in this project are **LIBERO-Object simulation** results. None are real-robot results.

## Prior-work and framing

**1. "vla.cpp already did this."** [A]
vla.cpp (VinRobotics, arXiv 2606.08094, github.com/VinRobotics/vla.cpp, Apache-2.0) is the runtime, the eval loop and
the column definitions we start from. We do not claim first. The `scripts/libero_eval.py` loop is vla.cpp's v0.4.0 loop
plus timing and abort handling (see its header). What this repo adds, and nothing more is claimed:
(a) a re-run of vla.cpp's SmolVLA Orin Nano configuration on our own unit (whether it is a different physical unit
from theirs is not known [verify]) with a fixed, recorded setup (`results/jetson/smolvla_calib/`,
`results/analysis/smolvla_calib_vs_fp16ref.json`). Partial reproduction only: success count and latency land
inside the tolerance set in PLAN.md "Calibration", peak RSS does not match the Table III figure (see reviewer pass R3);
(b) an fp16 PyTorch reference run on a different machine for each row (same env seed and the same fixed LIBERO
initial states; the policy's sampling noise is not seeded, see item 14), with the success difference and its
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
calibration row). Note that vla.cpp's own Jetson doc (`docs/benchmark/jetson-orin-nano.md`) lists a faster
per-model flag set (for SmolVLA, flash-attn and a different matmul precision) with a large latency and memory
effect, so "defaults" are not vla.cpp's best case; see reviewer pass R3. Consequence stated up front: **rows are not a ranking of models or of runtimes.** A model that is
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
Mitigations in the design: published third-party numbers are quoted only as calibration targets;
we publish rows that look bad for the hardware too (all rows go in `results/ATTEMPTS.md`, none dropped); the
reference machine is an NVIDIA GPU as well, so the NUC does **not** serve as an NVIDIA-independent check. [C] No
non-NVIDIA edge hardware is tested; we make no claims about other boards.

**7. "Quatern conflict."** [C]
Nothing in this repo depends on Quatern. The NUC is shared with Quatern workloads
(Quatern has priority on it), so NUC timings can be contaminated; for that reason only Jetson latency goes into the
table (the NUC reference is used for accuracy). This was not true of the first generated table (NUC latency columns
were filled); `summarize.py table` now blanks latency columns for non-Jetson rows. `setup.json` records load average and top processes at start;
see item 13 for the limits of that.

## Statistics and evidence strength

**8. "One run, one seed, 200 episodes: differences are noise."** [A] + [B]
`scripts/analyze.py` writes per-task successes and Wilson 95% intervals and the interval of the difference between a
row and its reference (`results/analysis/smolvla_calib_vs_fp16ref.json`). Claims in any post are limited to what the
interval supports; a difference inside the interval is described as "no detectable difference", never as parity.
[B] Not run: repeat each row (a few more full runs per row; seeds do not change initial states, see item 14).
Jetson runs need the organizer's Jetson session; NUC reference repeats need the GPU lock (held by other projects'
jobs, and machine load was above the NUC_RULES limit, during both sessions). Every row is a single full run. The only
repeat evidence is the stopped partial NUC reference run vs the full one (reviewer pass R2).

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
Accuracy against the reference run (same env seed and initial states) of the upstream checkpoint (`HuggingFaceVLA/smolvla_libero` @ 6721902b, the
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
No. (Corrected in the reviewer pass; the earlier text said this was unverified.) In vla.cpp's LIBERO wrapper
(`runtimes/vla.cpp/eval/sim/libero/libero_env.py`, `reset`) episode *i* of a task starts from LIBERO's fixed
init state *i*; `--seed 42` only seeds the simulator's own RNG. So every run, whatever the seed, evaluates the same
first 20 of LIBERO's initial states per task, and a "seed sweep" would not draw new initial conditions. Policy sampling
noise (flow-matching noise) is not seeded by `libero_eval.py` (no `torch.manual_seed`; vla.cpp's server draws its own),
so reruns are not bit-reproducible. The `seed` column therefore means "env seed argument", nothing more. [C] Real
repeats need a different mechanism (other init-state indices, or several unseeded repeats); see reviewer pass R2.

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

## Reviewer pass (2026-11-06)

Fresh review by a session that had not seen the work. Evidence for every statement below is in the git-ignored
`results/analysis/reviewer_pass_2026-11-06.txt` (made by `results/_scratch/reviewer_checks.py`, CPU only); this file
quotes no result numbers. No GPU or sim job was run: the GPU lock was held by another project and machine load was
above the NUC_RULES limit of 16.

### What I changed in this file (factual errors)
- Item 1(a): "independent reproduction on a second unit" overstated. Unit identity is unknown [verify] and RSS is not
  reproduced. Reworded to "partial reproduction".
- Item 1(b), 12: "same-seed" reference changed to "same env seed and initial states" (see R1).
- Item 14: said seeding was unverified; it is verifiable and the answer is that the seed does not choose episodes. Rewritten.
- Item 7: claimed only Jetson latency is in the table; the generated table had NUC latency filled. Code fixed, text says so.
- Item 8: GPU-lock reason updated; pointer to the only repeat evidence (R2).
- Item 3: added that vla.cpp's own doc has a faster per-model flag set than the defaults we ran (R3).
- Item 3 also said `model_ref` / `model_sha256` are columns of `results/TABLE.md`; they were only in `row.json`. Added to the table.

### Code fixes made (scripts/summarize.py)
- `table` read `row.json` copies under `results/_scratch/` and printed the Jetson row twice. It now skips any path
  component starting with `_`.
- `table` blanks latency columns for non-Jetson rows (NUC shared with Quatern and other jobs).
- Added `model_ref`, `model_sha256` columns.

### 1. Claim-by-claim trace
| Claim (repo or a likely post) | Traces to results? | One command? | Exceeds evidence? |
|---|---|---|---|
| Calibration row reproduces vla.cpp Table III | success and latency yes (within PLAN tolerance); RSS no | `make all` needs the run dirs | "reproduces" is too strong; say "within tolerance on two of three columns" |
| Edge row vs fp16 reference accuracy difference | yes, `smolvla_calib_vs_fp16ref.json` and the paired check | `make calib-analysis` | A difference inside the CI must read "no detectable difference". The paired comparison (McNemar) gives the same reading |
| "Same seed" reference | env seed yes, but it picks nothing (R1) | n/a | Fails: wording removed |
| Latency "ms per executed action" | yes, recomputed from `steps.jsonl` | `make calib-row` | It is a mean over env steps (includes the steps where no request is made), amortized over a 4-action chunk. It is not the time the robot waits (the per-request p50 is). Any post must show both |
| Jetson was otherwise idle | `setup.json` start only (no `setup_end.json` for this run) | n/a | Evidence, not proof (item 13) |
| "Pinned clocks" | `setup.json` clocks min = max | n/a | The reference config of vla.cpp left clocks unchanged; ours is the faster config for the hardware (R4) |
| Prior-work ids | vla.cpp id 2606.08094 confirmed offline in its README; the other arXiv ids [verify] | n/a | fine |
| "7B rows" / "$249" | none exist | n/a | PLAN's angle is a plan only |
| Row "fits" | `fits` is a CLI default ("yes"), set by hand; not derived from the run | n/a | Means "run completed", already stated in item 10; but the column is not computed |
| Reproducible with one command | run dirs are local only | `make all` + `run_row.sh` | A reader cannot rerun until the run dirs are published |
Failures: the "reproduces" wording, the "same seed" wording, the NUC-latency-in-table claim (fixed), and the `fits` column being manual.

### 2. Existing entries: is the answer true, is the classification honest
- 1 A: true after the 1(a)/(b) edits. Header of `libero_eval.py` does state the differences from upstream; it also
  differs by running all tasks in one process, which the item omits (harmless).
- 2 C: classification fine; the judgement of the omitted references is in R5.
- 3 A+C: true. Was missing the flag-set point (R3). The vague label "as-shipped" hides that the dtype is a runtime
  default (R3).
- 4 C: honest.
- 5 A+C: true (`emc_rate_hz` empty confirmed). Clocks are pinned at the maximum, see R4.
- 6 A+C: true; add the clock-pinning and unit-ownership points (R4, R6).
- 7 C: honest after fix.
- 8 A+B: the statistical outputs exist. Classification now A+B(not run)+C because repeats cannot vary the initial states (item 14).
- 9 A+C: true; added R3/R4 caveats on what differs from vla.cpp.
- 10 A+C: true. The RSS gap to Table III has a probable cause (flags, R3), still unproven.
- 11, 13 C: honest. 13: the organizer, not the author, ran the Jetson row; noted.
- 12 A+B: true; the 16-hex hash prefix confirmed in `row.json`.
- 14: was wrong (fixed).
- 15, 16, 17 C/A: true (X-VLA bridge untested; no 7B row exists). Evo-1 has no lerobot policy, so it cannot get a
  reference by the PLAN protocol (R7), which the item list did not say.
- 18 A+C: true once the duplicate-row bug was fixed (it broke `make table`).
- 19 A: true for run dirs (ATTEMPTS lists all five). It cannot list attempts that left no run dir (the failed Jetson
  PyTorch venv, build trials); HANDOFF.md carries those. Say "every run directory", not "every attempt".
- 20 A: true; but see R8 on the reference's observation path.

### 3. Missing criticisms and answers
**R1. "Your seed does nothing / the reference is not 'same-seed'."** Fixed in item 14. [C] Experiment would be a
different set of init-state indices (the wrapper has `episode_index`), or unseeded repeats: *not run*, needs GPU/Jetson time.

**R2. "Run-to-run noise at 200 episodes is unknown."** [A] partial evidence + [B]. The earlier stopped NUC run used the
identical configuration as the full NUC run. On the episodes it finished, a noticeable fraction of individual outcomes
flipped between the two runs and the step counts almost never matched, so single-episode outcomes are noisy even on one
machine. The fraction of per-episode discordance between the Jetson row and the NUC reference is of the same size as
that same-machine repeat flip rate; the exact McNemar test on the 200 paired episodes shows no detectable difference and
the paired interval comfortably spans zero. Reading: the edge row and the reference are indistinguishable at this
sample size and noise level. It is not evidence they are equal. [B] *Not run*: full repeats (GPU lock busy, load high).
A Jetson 2-episode smoke run also disagreed with the same two episodes in the calibration run on one episode.

**R3. "You did not optimize each model fairly; what runtime/format/flags?"** [A] + [C]. Owner-required.
Rows are labeled with runtime, commit, format and `server_args` (empty = defaults). Three things the label alone does
not say, found in `server.log` and vla.cpp's docs: (i) with defaults the server keeps tower weights in bf16 and widens
the LM matmul weights to f32 (`--mm-prec` default), so "as-shipped" is not a low-bit format; the `format` column should
carry that and currently does not. (ii) vla.cpp's own Jetson doc lists a faster flag set for SmolVLA with a large
latency and RSS improvement over defaults; we ran defaults, so our row is neither vla.cpp's fastest nor necessarily
the config behind its Table III. (iii) Our peak RSS sits next to that doc's default-flags figure and above the Table III
figure, which suggests Table III used non-default flags [verify]; this is a hypothesis. Action: record the full server
command and the three dtype lines from `server.log` in `setup.json` for new rows (not done), and run the
flag-set row as a separate labeled row if the Jetson is available. Limitation stated: rows are not a ranking.

**R4. "NVIDIA bias; hardware advantages."** [C] Owner-required; extends item 6. Added points: clocks are pinned at the mode's maximum while the vla.cpp doc
we calibrate against did not change them, which favors the hardware; the NUC reference is NVIDIA too; the CUDA
GGUF runtime is the vendor-friendly path, and no non-NVIDIA edge board is tested. Whether the Jetson was NVIDIA-provided or personally owned is not recorded [verify]; state it.

**R5. Omitted references (owner asked for a judgement).** Mostly right, with one correction. I cannot open any of
them offline and I do not state what the MIT post, PicoGPT, Hirundo / CrowdStrike / Booz Allen items contain
[verify]. RoboStriker, URMA / MetaMorph and Text2Robot are, by title, about locomotion, cross-embodiment or robot design,
not edge inference of existing VLAs: leaving them out of README/PLAN is right. The other group appears tied to
compression/weight-space methods, which matter for the blocked 7B "one row per compression method" plan, so "not
relevant" is wrong for those as a blanket statement: they should be cited or explicitly dismissed before any 7B/compression
row or post. PLAN.md now carries that as a to-do. The owner's own OmniVLA workshop paper is cited as the recipe source in
PLAN; as a self-citation it should be labeled so in any post.

**R6. "The numbers are one person's, one unit, one day."** [C] Single Jetson unit, single day, run by the organizer, no
independent replication. Say so.

**R7. "Reference protocol does not hold for every model."** [C] PLAN says every model gets a PyTorch fp16 reference, but
lerobot 0.4.3 has no Evo-1 policy, so an Evo-1 row can only be compared to Evo-1's own upstream code (not started) or
have no reference. Also the reference pipeline for the X-VLA row uses lerobot's processors, the edge row will not.
Rows without a same-pipeline reference must be labeled as such.

**R8. "Your reference is not upstream's pipeline."** [C] The fp16 reference feeds the vla.cpp adapter's observations
(resize/format) into lerobot's pre/post-processors, so both rows share the adapter; the comparison isolates the
policy backend, not the full upstream eval pipeline. We did not compare the reference to published upstream LIBERO-Object
numbers [verify]. Any post should not call it "the original model's accuracy".

**R9. "ms/action and Hz hide the blocking latency."** [A]+[C] Each request blocks for roughly the p50 request time
(in the table), then several actions run from the queue. Hz here is amortized and is not a control rate. Show the p50
request time and chunk size next to Hz in any post. The p95/p99 spread is very narrow, consistent with fixed clocks and
a deterministic kernel path; it also means the latency spread of a pinned-clock row says nothing about default-clock behavior.

**R10. "Thermal throttling / power."** [C] `tegrastats.log` shows the CPU clock constant throughout and junction
temperature in a moderate range, with no downward drift of latency across the run (checked by quarter), so no
throttling is evidenced; GPU clock was not sampled in tegrastats. No power or energy claim is made though VDD_IN is
logged; do not make one without a proper power measurement.

**R11. "Ground truth for peak memory and sim co-location."** [C] The server and the sim share memory; system RAM peak
is high relative to 8 GB in the local-sim setup, so "fits" next to a simulator is not "fits on a robot". The remote-sim
comparison is not run (item 9).

**R12. "Table III commit and versions differ."** [C] They use a branch commit and a different llama.cpp build and
JetPack 6.2.2; ours is the v0.4.0 tag, JetPack 6.2.1. Not reconciled; listed so a reader does not assume identical software.

### 4. Required checks
- Medians and spreads: the table carries p50, p95, and the analysis p99/max and per-episode mean spread. Accuracy
  has Wilson intervals per task. OK for the one row that exists, but it is one run with no repeats (R2).
- No cherry-picking: all five run dirs are listed in `ATTEMPTS.md`; the only complete rows use the complete runs.
- Simulation stated plainly: README top, PLAN, table footer, this file. OK.
- Prior work: vla.cpp, eetmie, 2604.24447 cited; vla.cpp id confirmed offline, the others marked [verify]. OK.
- Neutral wording: no superlatives found in README/PLAN/CRITIQUES. "Pi0 / BitVLA later" etc. are plans.
- No numbers in tracked files: checked README, PLAN, CRITIQUES, HANDOFF (only third-party Table III targets, allowed).
