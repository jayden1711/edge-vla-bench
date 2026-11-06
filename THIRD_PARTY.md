# Third-party models, runtimes and tools

None of these are committed or redistributed here. Scripts fetch them at the pinned revision into git-ignored
`runtimes/` / `weights/`. PLAN.md has the full model table and status; keep both in sync.

## Models
| Model | Checkpoint (HF id @ revision) | License | Notes |
|---|---|---|---|
| SmolVLA (450M) | `vrfai/smolvla-libero-gguf` @ 349851cd (GGUF of `HuggingFaceVLA/smolvla_libero` @ 6721902b) | Apache-2.0 | calibration row; fp16 reference uses the upstream checkpoint |
| X-VLA (0.9B) | `2toINF/X-VLA-Libero` @ 129e7146; code github.com/2toinf/X-VLA @ 6c4ecfb8 | Apache-2.0 | |
| Evo-1 | `vrfai/evo1-libero-gguf` @ c76eb353 (GGUF of `MINT-SJTU/Evo1_LIBERO` @ 3ddc6c9c); code github.com/MINT-SJTU/Evo-1 @ 5fd14b01 | GGUF repo Apache-2.0; code MIT; upstream HF weights: no license field, **to confirm** | |
| X-VLA TensorRT export | github.com/eetmie/jetson-orin-nano-vla @ 6aa4a151d11c6116037985bd37080210032e57b7 (ONNX/TensorRT export scripts, credit: eetmie) | MIT (LICENSE checked via GitHub API 2026-11-06) | row label "TensorRT export by eetmie"; fetched into `runtimes/`, engines never committed |
| pi0, pi0.5, BitVLA, OpenVLA-OFT, OmniVLA | TBD | TBD | fill in before use; 7B rows blocked until owner says go |

## Runtimes and tools
| Tool | Version / commit | License |
|---|---|---|
| vla.cpp (github.com/VinRobotics/vla.cpp) | v0.4.0 = f7e0f7f89f290a4a6f231f9a83bc2237a61e425e | Apache-2.0 |
| llama.cpp / ggml (pinned by vla.cpp CMake) | ggml 0.25.3 @ 4da633776 | MIT |
| LIBERO | cloned by vla.cpp `setup_libero.sh`; commit to record | MIT |
| lerobot | 0.4.3 | Apache-2.0 |
| MuJoCo | 2.3.2 | Apache-2.0 |
| PyTorch (reference venv) | NUC 2.14.1; Jetson 2.11.0 (Jetson AI Lab JP6 index) | BSD-3-Clause |
| uv | Jetson 0.12.10, NUC 0.13.7 | Apache-2.0 / MIT |
