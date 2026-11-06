#!/usr/bin/env python3
"""Capture the fixed benchmark setup of the machine it runs on, as JSON.

Runs unprivileged on the Jetson (Orin Nano) or on the NUC (x86 + NVIDIA dGPU).
Every result file embeds this output under "setup". Run-specific fields
(runtime, precision, chunk length, cameras, resolution, ...) are passed in
with --run key=value and stored under "run".

Usage:
  python3 capture_setup.py --run runtime=vla.cpp --run runtime_commit=c93ca0a \
      --run precision=fp16 --run batch=1 --run chunk=50 --run executed_actions=4 \
      --run cameras=2 --run resolution=512 > setup.json
"""
import argparse, datetime, glob, json, os, platform, re, shutil, socket, subprocess


def sh(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception as e:  # noqa: BLE001
        return f"ERROR: {e}"


def read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except Exception:  # noqa: BLE001
        return None


# L4T -> JetPack, from NVIDIA's release notes (extend as needed)
L4T_TO_JETPACK = {"36.3.0": "6.0", "36.4.0": "6.1", "36.4.3": "6.2", "36.4.4": "6.2.1",
                  "36.4.7": "6.2.1", "36.5.0": "6.2.2"}


def jetson():
    rel = read("/etc/nv_tegra_release") or ""
    m = re.search(r"R(\d+) \(release\), REVISION: ([\d.]+)", rel)
    l4t = f"{m.group(1)}.{m.group(2)}" if m else None
    if l4t and l4t.count(".") == 1:
        l4t += ".0"
    core = sh("dpkg-query -W -f='${Version}' nvidia-l4t-core 2>/dev/null")
    jp_pkg = sh("dpkg-query -W -f='${Version}' nvidia-jetpack 2>/dev/null")

    cpus = {}
    for c in sorted(glob.glob("/sys/devices/system/cpu/cpu[0-9]*")):
        f = c + "/cpufreq/"
        if os.path.exists(f):
            cpus[os.path.basename(c)] = {k: read(f + "scaling_" + k) for k in ("cur_freq", "min_freq", "max_freq", "governor")}
            cpus[os.path.basename(c)]["online"] = read(c + "/online") or "1"
    devfreq = {}
    for d in glob.glob("/sys/class/devfreq/*"):
        devfreq[os.path.basename(d)] = {k: read(f"{d}/{k}") for k in ("cur_freq", "min_freq", "max_freq", "governor")}
    gpu = devfreq.get("17000000.gpu", {})
    cpu0 = cpus.get("cpu0", {})
    # jetson_clocks pins min==max; reading its state directly needs root, so infer it.
    clocks_pinned = bool(gpu) and gpu.get("min_freq") == gpu.get("max_freq") and cpu0.get("min_freq") == cpu0.get("max_freq")
    emc = read("/sys/kernel/debug/bpmp/debug/clk/emc/rate")  # root only; None otherwise

    return {
        "device_model": (read("/proc/device-tree/model") or "").rstrip("\x00"),
        "l4t": l4t, "l4t_core_pkg": core,
        "jetpack": jp_pkg or L4T_TO_JETPACK.get(l4t, "unknown (map L4T manually)"),
        "jetpack_source": "nvidia-jetpack pkg" if jp_pkg else "inferred from L4T",
        "power_mode": sh("nvpmodel -q 2>/dev/null | head -1").replace("NV Power Mode: ", ""),
        "jetson_clocks_inferred": clocks_pinned,
        "cpu_freq": cpus, "devfreq": devfreq,
        "emc_rate_hz": emc,
        "cuda": sh("ls -d /usr/local/cuda-* 2>/dev/null | xargs -n1 basename | tr '\\n' ' '"),
        "tensorrt": sh("dpkg-query -W -f='${Version}' tensorrt 2>/dev/null"),
        "cudnn": sh("dpkg-query -W -f='${Version}' libcudnn9-cuda-12 2>/dev/null"),
        "swap": sh("swapon --show --noheadings --bytes"),
        "zram": sh("ls /sys/block | grep zram | tr '\\n' ' '"),
    }


def nuc():
    q = "name,memory.total,driver_version,power.limit,clocks.max.sm,clocks.max.mem,persistence_mode"
    return {
        "gpu": sh(f"nvidia-smi --query-gpu={q} --format=csv,noheader"),
        "cuda_driver": sh("nvidia-smi | grep -o 'CUDA Version: [0-9.]*'"),
        "nvcc": sh("nvcc --version 2>/dev/null | tail -1"),
        "gpu_compute_procs": sh("nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader"),
        "cpu": sh("lscpu | grep 'Model name' | sed 's/.*: *//'"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", default=[], help="key=value run-specific setting")
    a = ap.parse_args()
    run = dict(kv.split("=", 1) for kv in a.run)

    is_jetson = os.path.exists("/etc/nv_tegra_release")
    mem = {l.split(":")[0]: l.split(":")[1].strip() for l in (read("/proc/meminfo") or "").splitlines()[:6]}
    top = sh("ps -eo pid,user,rss,pcpu,comm --sort=-rss | head -15")
    out = {
        "schema": "edge-vla-bench/setup/v1",
        "captured_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "host": socket.gethostname(),
        "role": "jetson" if is_jetson else "reference_host",
        "os": sh("lsb_release -ds") or platform.platform(),
        "kernel": platform.release(),
        "python": platform.python_version(),
        "meminfo": mem,
        "loadavg": read("/proc/loadavg"),
        "top_processes_by_rss": top.splitlines(),
        "platform": jetson() if is_jetson else nuc(),
        "run": run,
    }
    # Required run fields from the brief; flag anything missing rather than guessing.
    required = ["runtime", "runtime_version", "precision", "batch", "chunk", "executed_actions",
                "resolution", "cameras", "warmup_excluded"]
    out["missing_run_fields"] = [k for k in required if k not in run]
    if shutil.which("tegrastats") is None and is_jetson:
        out["warning"] = "tegrastats not on PATH"
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
