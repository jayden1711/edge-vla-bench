"""X-VLA through eetmie's TensorRT split-engine runtime, behind the LeRobotTorchClient interface.

Credit: github.com/eetmie/jetson-orin-nano-vla (MIT), pinned in PLAN.md. That repo only benchmarks with
synthetic observations; this client is the missing LIBERO bridge. Only model execution differs from the
upstream-PyTorch reference: the checkpoint's own lerobot pre/post-processors (tokenizer, state
normalization, unnormalization) are reused unchanged, so accuracy differences come from the engines.

Needs one interpreter with tensorrt (eetmie's runtime), lerobot (processors), torch and LIBERO.
The bundle must be exported from `lerobot/xvla-libero` (2 views) with eetmie's `./export.sh`.
"""
import sys
from collections import deque
from pathlib import Path


class XvlaTrtClient:
    def __init__(self, eetmie_root, bundle, cache_dir, repo_id, revision, n_action_steps, seed=0):
        import numpy as np
        import torch
        from huggingface_hub import snapshot_download
        from lerobot.configs.policies import PreTrainedConfig
        from lerobot.policies.factory import make_pre_post_processors

        sys.path.insert(0, str(Path(eetmie_root).resolve()))
        from bench.backends.trt_split_xvla import TrtSplitXVLABackend

        self.np, self.torch = np, torch
        self.backend = TrtSplitXVLABackend(Path(bundle), cache_dir)
        self.backend.load()  # builds/loads engines, fails closed on fixture parity
        self.bd = self.backend.bundle
        if self.bd.valid_views != 2:
            raise ValueError(f"bundle has {self.bd.valid_views} valid views; xvla-libero needs 2")
        if n_action_steps > self.bd.chunk_size:
            raise ValueError(f"n_action_steps {n_action_steps} > chunk_size {self.bd.chunk_size}")

        path = snapshot_download(repo_id, revision=revision)
        cfg = PreTrainedConfig.from_pretrained(path)
        cfg.device = "cpu"  # processors only; the model runs in TensorRT
        self.pre, self.post = make_pre_post_processors(
            cfg, pretrained_path=path,
            preprocessor_overrides={"device_processor": {"device": "cpu"}},
        )
        self.n_action_steps = n_action_steps
        self._rng = np.random.default_rng(seed)
        self._action_queue = deque(maxlen=n_action_steps)
        self.last_timings_ms = {}

    def reset(self):
        self._action_queue.clear()

    def _views(self, batch):
        torch = self.torch
        keys = sorted(k for k in batch if k.startswith("observation.images."))
        if len(keys) != self.bd.valid_views:
            raise ValueError(f"got image keys {keys}, bundle expects {self.bd.valid_views} views")
        out = []
        for k in keys:
            x = batch[k].float()
            if x.dim() == 5:  # (B, N, C, H, W)
                x = x[:, 0]
            if x.shape[-2:] != (224, 224):  # square LIBERO frames: plain resize, no padding needed
                x = torch.nn.functional.interpolate(x, size=(224, 224), mode="bilinear", align_corners=False)
            out.append(x[0].numpy())
        return self.np.stack(out)

    def get_action(self, obs):
        np, torch = self.np, self.torch
        if not self._action_queue:
            batch = {k: v for k, v in obs.items() if k != "_batched_tensors"}
            batch = self.pre(batch)
            pv = self._views(batch)
            ids = batch["observation.language.tokens"].cpu().numpy().astype(np.int64).reshape(1, -1)
            proprio = np.zeros((1, self.bd.state_dim), np.float32)
            state = batch["observation.state"].float().cpu().numpy().ravel()[: self.bd.state_dim]
            proprio[0, : len(state)] = state
            x1 = self._rng.standard_normal((1, self.bd.chunk_size, self.bd.action_dim)).astype(np.float32)
            from bench.vendor.xvla_trt import infer
            t = {}
            chunk = infer(self.bd, self.backend.engines.run, pv, ids, proprio, x1, timings=t)
            self.last_timings_ms = t
            acts = torch.from_numpy(np.asarray(chunk[0][: self.n_action_steps], np.float32))
            for a in acts:
                self._action_queue.append(self.post(a[None])[0].cpu().numpy())
        return self._action_queue.popleft()
