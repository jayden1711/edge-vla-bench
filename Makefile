# One command per published artifact. Outputs go to git-ignored results/.
# Run from the repo root. Experiments (GPU/sim) are listed in CRITIQUES.md and PLAN.md, not run here.
PY ?= python3
LIBERO_PY ?= runtimes/vla.cpp/eval/sim/libero/libero_uv/.venv/bin/python
CALIB ?= results/jetson/smolvla_calib/20261106T182439Z
REF   ?= results/nuc/smolvla_fp16_ref/20261106T080842Z

.PHONY: table attempts prompts calib-analysis calib-row ref-row all

# results/TABLE.md: every row.json, with runtime/format/power mode/clocks/seed per row
table:
	$(PY) scripts/summarize.py table results/ > results/TABLE.md.tmp
	mv results/TABLE.md.tmp results/TABLE.md

# results/ATTEMPTS.md: every run dir including partial and failed ones
attempts:
	$(PY) scripts/summarize.py attempts results > results/ATTEMPTS.md.tmp
	mv results/ATTEMPTS.md.tmp results/ATTEMPTS.md

# verbatim LIBERO-Object prompts (CPU only; run through sim-run on the NUC)
prompts:
	MUJOCO_GL=egl ~/projects/bin/sim-run $(LIBERO_PY) scripts/dump_prompts.py libero_object results/prompts/libero_object.json

# per-task successes, Wilson intervals, latency spread, calibration row vs fp16 reference
calib-analysis:
	$(PY) scripts/analyze.py $(CALIB) --ref $(REF) --out results/analysis/smolvla_calib_vs_fp16ref.json

# recompute row.json files from the run dirs (reference successes passed explicitly)
calib-row:
	ref=$$($(PY) -c "import json;print(json.load(open('$(REF)/client/eval_summary.json'))['successes'])") && \
	$(PY) scripts/summarize.py row $(CALIB) --model SmolVLA --params 450M --precision "GGUF as shipped" --reference-successes "$$ref"
ref-row:
	$(PY) scripts/summarize.py row $(REF) --model SmolVLA --params 450M --precision "fp16 (PyTorch ref)"

all: ref-row calib-row table attempts calib-analysis
