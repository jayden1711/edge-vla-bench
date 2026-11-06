#!/usr/bin/env bash
# Run one benchmark row on the Jetson: capture setup, start vla-server, log tegrastats,
# run the LIBERO client (locally or point it at a remote sim), record server peak RSS.
#
# Usage (on the Jetson, from the repo root):
#   scripts/run_row.sh <row_name> <gguf_path> <arch> <n_action_steps> [extra run=k=v ...]
# Env:
#   SIM=local|remote   local (default): client runs here. remote: only the server runs here,
#                      bound to 0.0.0.0, and you start scripts/libero_eval.py on the NUC
#                      pointing at tcp://<jetson>:$PORT; this script waits for DONE_FILE.
#   TASK_IDS (0-9) N_EPISODES (20) PORT (5555) SERVER_ARGS ("") VLA_ROOT (runtimes/vla.cpp)
set -euo pipefail
ROW="$1"; GGUF="$2"; ARCH="$3"; S="$4"; shift 4
REPO="$(cd "$(dirname "$0")/.." && pwd)"
VLA_ROOT="${VLA_ROOT:-$REPO/runtimes/vla.cpp}"
SIM="${SIM:-local}"; TASK_IDS="${TASK_IDS:-0-9}"; N_EPISODES="${N_EPISODES:-20}"; PORT="${PORT:-5555}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$REPO/results/jetson/$ROW/$STAMP"; mkdir -p "$OUT"

RUNTIME_COMMIT="$(git -C "$VLA_ROOT" rev-parse HEAD)"
python3 "$REPO/scripts/capture_setup.py" \
  --run runtime=vla.cpp --run runtime_version="$RUNTIME_COMMIT" \
  --run model_file="$(basename "$GGUF")" --run model_sha256="$(sha256sum "$GGUF" | cut -c1-16)" \
  --run arch="$ARCH" --run batch=1 --run executed_actions="$S" \
  --run sim_location="$SIM" --run task=libero_object --run task_ids="$TASK_IDS" \
  --run n_episodes_per_task="$N_EPISODES" --run warmup_excluded=3 \
  --run server_args="${SERVER_ARGS:-}" "$@" > "$OUT/setup.json"

tegrastats --interval 500 --logfile "$OUT/tegrastats.log" & TS_PID=$!
BIND="tcp://127.0.0.1:$PORT"; [ "$SIM" = remote ] && BIND="tcp://0.0.0.0:$PORT"
# shellcheck disable=SC2086
"$VLA_ROOT/build/bin/vla-server" --bind "$BIND" ${SERVER_ARGS:-} "$GGUF" > "$OUT/server.log" 2>&1 & SRV=$!
cleanup() { kill "$SRV" "$TS_PID" 2>/dev/null || true; }
trap cleanup EXIT

# poll peak RSS while the server lives (VmHWM is the kernel's high-water mark of RSS)
( while kill -0 "$SRV" 2>/dev/null; do grep VmHWM /proc/$SRV/status 2>/dev/null > "$OUT/server_vmhwm.txt.tmp" && mv "$OUT/server_vmhwm.txt.tmp" "$OUT/server_vmhwm.txt"; sleep 1; done ) &

for i in $(seq 1 600); do grep -qiE "listening|ready|bound" "$OUT/server.log" && break; kill -0 "$SRV" || { echo "server died"; tail "$OUT/server.log"; exit 1; }; sleep 1; done

if [ "$SIM" = local ]; then
  # shellcheck disable=SC1091
  source "$VLA_ROOT/eval/sim/libero/libero_uv/.venv/bin/activate"
  MUJOCO_GL=egl python -I "$REPO/scripts/libero_eval.py" --vla-root "$VLA_ROOT" --arch "$ARCH" \
    --n-action-steps "$S" --task-ids "$TASK_IDS" --n-episodes "$N_EPISODES" \
    --vla-addr "tcp://127.0.0.1:$PORT" --out "$OUT/client" 2>&1 | tee "$OUT/client.log"
else
  echo "server up on $BIND; run the client on the NUC with --out <dir>, then: touch $OUT/DONE"
  while [ ! -f "$OUT/DONE" ]; do sleep 5; done
fi
cp "$OUT/server_vmhwm.txt" "$OUT/server_peak_rss.txt" 2>/dev/null || true
echo "results in $OUT"
