#!/usr/bin/env bash
# fp16 reference run on the NUC: upstream PyTorch checkpoint, same LIBERO wrapper/seed/episodes.
# Usage: scripts/run_reference.sh <row_name> <arch> <hf_repo> <revision> <n_action_steps> [dtype]
set -euo pipefail
ROW="$1"; ARCH="$2"; POLICY="$3"; REV="$4"; S="$5"; DTYPE="${6:-float16}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
VLA_ROOT="${VLA_ROOT:-$REPO/runtimes/vla.cpp}"
TASK_IDS="${TASK_IDS:-0-9}"; N_EPISODES="${N_EPISODES:-20}"
OUT="$REPO/results/nuc/$ROW/$(date -u +%Y%m%dT%H%M%SZ)"; mkdir -p "$OUT"
# shellcheck disable=SC1091
source "$REPO/runtimes/ref_uv/.venv/bin/activate"
python3 "$REPO/scripts/capture_setup.py" --run runtime=lerobot --run runtime_version="$(python -c 'import importlib.metadata as m;print("lerobot "+m.version("lerobot")+", torch "+m.version("torch"))')" \
  --run policy="$POLICY@$REV" --run precision="$DTYPE (weights) + autocast" --run batch=1 \
  --run executed_actions="$S" --run arch="$ARCH" --run sim_location=local --run task=libero_object \
  --run task_ids="$TASK_IDS" --run n_episodes_per_task="$N_EPISODES" --run warmup_excluded=3 \
  --run vla_cpp_eval_commit="$(git -C "$VLA_ROOT" rev-parse HEAD)" > "$OUT/setup.json"
MUJOCO_GL=egl python -I "$REPO/scripts/libero_eval.py" --vla-root "$VLA_ROOT" --arch "$ARCH" --backend lerobot \
  --policy "$POLICY" --revision "$REV" --dtype "$DTYPE" --n-action-steps "$S" \
  --task-ids "$TASK_IDS" --n-episodes "$N_EPISODES" --out "$OUT/client" > "$OUT/client.log" 2>&1
python3 "$REPO/scripts/check_eval_output.py" "$OUT/client" "$TASK_IDS" "$N_EPISODES"
echo "results in $OUT"
