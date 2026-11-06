#!/usr/bin/env bash
# venv for upstream PyTorch policies (lerobot backend of libero_eval.py) in the same LIBERO
# wrapper as the vla.cpp runs. Used on the NUC for fp16 reference runs, and on the Jetson for
# models vla.cpp doesn't support (X-VLA). vla.cpp's LIBERO venv pins torch 2.5.1 (cu124), which
# has no sm_120 kernels for the RTX 5080 and no CUDA build for the Jetson.
set -euxo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
VLA_ROOT="${VLA_ROOT:-$REPO/runtimes/vla.cpp}"
LIBERO_REPO="$VLA_ROOT/eval/sim/libero/LIBERO"
ENV="$REPO/runtimes/ref_uv/.venv"
export PATH="$HOME/.local/bin:$PATH" CMAKE_POLICY_VERSION_MINIMUM=3.5
uv venv "$ENV" --python 3.10
# shellcheck disable=SC1091
source "$ENV/bin/activate"
uv pip install --requirements "$LIBERO_REPO/requirements.txt"
uv pip install -e "$LIBERO_REPO" --config-settings editable_mode=compat
uv pip install lerobot==0.4.3
uv pip install pydantic av tianshou==0.5.1 tyro pandas dm_tree einops==0.8.1 albumentations==1.4.18 zmq \
  transformers==4.51.3 msgpack==1.1.0 msgpack-numpy==0.4.8 gymnasium==0.29.1 pandas==2.0.3 pyarrow==12.0.1 \
  diffusers==0.30.1 numpy==1.26.4 mujoco==2.3.2 num2words
# last, so nothing above downgrades it.
if [ -f /etc/nv_tegra_release ]; then   # Jetson, JetPack 6 / CUDA 12.6 wheels from NVIDIA's Jetson AI Lab index
  uv pip install --reinstall torch==2.11.0 torchvision==0.26.0 --index-url https://pypi.jetson-ai-lab.io/jp6/cu126/+simple
else                                    # NUC: the version lerobot 0.4.3 resolves to; ships sm_120 kernels
  uv pip install --reinstall torch==2.14.1 torchvision==0.29.2
fi
uv pip install numpy==1.26.4  # torch reinstall pulls numpy 2; LIBERO stack needs 1.x
python -c "import torch; x=torch.randn(8,8,device='cuda'); print(torch.__version__, (x@x).sum().item())"
