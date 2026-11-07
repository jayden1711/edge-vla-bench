"""Wrappers must exit non-zero when the inner job crashed or left incomplete output. CPU only, no GPU, no models.

Run: python3 -m unittest discover -s tests -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = ("run_row.sh", "run_reference.sh", "capture_setup.py", "check_eval_output.py")

FAKE_PYTHON = """#!/usr/bin/env bash
# fake `python`: `-c` prints a version; `-I` is the evaluator (exit code and output chosen by env)
out=""; prev=""
for a in "$@"; do [ "$prev" = "--out" ] && out="$a"; prev="$a"; done
case " $* " in
  *" -c "*) echo fake ;;
  *" -I "*)
    if [ "${FAKE_WRITE_SUMMARY:-0}" = 1 ]; then
      mkdir -p "$out"; echo '{}' > "$out/steps.jsonl"; echo '{}' > "$out/episodes.jsonl"
      echo '{"episodes": 1, "successes": 0, "aborted": 0}' > "$out/eval_summary.json"
    fi
    exit "${FAKE_PY_RC:-0}" ;;
esac
"""
FAKE_SERVER = "#!/usr/bin/env bash\n[ \"${FAKE_SERVER_EXIT:-0}\" = 1 ] && exit 3\necho listening\nexec sleep 30\n"
FAKE_TEGRA = "#!/usr/bin/env bash\necho tegra > \"$4\"\nexec sleep 30\n"


def write(path, text, mode=0o755):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(mode)


class CheckEvalOutput(unittest.TestCase):
    def run_check(self, d, ids="0-1", n=2):
        return subprocess.run([sys.executable, str(REPO / "scripts/check_eval_output.py"), str(d), ids, str(n)],
                              capture_output=True, text=True)

    def test_missing_summary_fails(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(self.run_check(t).returncode, 1)

    def test_incomplete_and_complete(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            (d / "steps.jsonl").write_text("{}\n")
            (d / "episodes.jsonl").write_text("{}\n" * 3)
            (d / "eval_summary.json").write_text(json.dumps({"episodes": 3, "aborted": 0}))
            self.assertEqual(self.run_check(d).returncode, 1)  # 3 of 4
            (d / "episodes.jsonl").write_text("{}\n" * 4)
            (d / "eval_summary.json").write_text(json.dumps({"episodes": 4, "aborted": 0}))
            self.assertEqual(self.run_check(d).returncode, 0)


class WrapperExitCodes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "scripts").mkdir()
        for s in SCRIPTS:
            shutil.copy(REPO / "scripts" / s, self.root / "scripts" / s)
        vla = self.root / "vla"
        subprocess.run(["git", "init", "-q", str(vla)], check=True)
        subprocess.run(["git", "-C", str(vla), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q",
                        "--allow-empty", "-m", "x"], check=True)
        write(vla / "build/vla-server", FAKE_SERVER)
        write(vla / "eval/sim/libero/libero_uv/.venv/bin/activate", "", 0o644)
        write(self.root / "runtimes/ref_uv/.venv/bin/activate", "", 0o644)
        write(self.root / "fakebin/python", FAKE_PYTHON)
        write(self.root / "fakebin/tegrastats", FAKE_TEGRA)
        (self.root / "model.gguf").write_text("x")
        self.env = dict(os.environ, PATH=f"{self.root / 'fakebin'}:{os.environ['PATH']}", VLA_ROOT=str(vla),
                        TASK_IDS="0", N_EPISODES="1")

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, name, args, **env):
        return subprocess.run(["bash", str(self.root / "scripts" / name), *args], env={**self.env, **env},
                              capture_output=True, text=True, timeout=120)

    def row(self, **env):
        return self.run_script("run_row.sh", ["row", str(self.root / "model.gguf"), "evo1", "1"], **env)

    def ref(self, **env):
        return self.run_script("run_reference.sh", ["row", "evo1", "pol", "rev", "1"], **env)

    def test_row_ok(self):
        r = self.row(FAKE_WRITE_SUMMARY="1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_row_server_dies(self):
        self.assertNotEqual(self.row(FAKE_SERVER_EXIT="1").returncode, 0)

    def test_row_client_crash(self):
        self.assertNotEqual(self.row(FAKE_PY_RC="3").returncode, 0)

    def test_row_client_exit0_without_output(self):
        r = self.row()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("eval_summary.json", r.stdout + r.stderr)

    def test_reference_ok(self):
        r = self.ref(FAKE_WRITE_SUMMARY="1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_reference_client_crash(self):
        self.assertNotEqual(self.ref(FAKE_PY_RC="3").returncode, 0)

    def test_reference_exit0_without_output(self):
        self.assertNotEqual(self.ref().returncode, 0)


if __name__ == "__main__":
    unittest.main()
