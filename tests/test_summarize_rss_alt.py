"""summarize.py: optional second memory number from rss_alt.json (row + table), absent by default."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUMMARIZE = ROOT / "scripts" / "summarize.py"


def make_run(d: Path):
    (d / "client").mkdir(parents=True)
    steps = [{"ms": 500.0, "req": True, "warmup": False}] + [{"ms": 1.0, "req": False, "warmup": False}] * 3
    (d / "client" / "steps.jsonl").write_text("".join(json.dumps(s) + "\n" for s in steps))
    (d / "client" / "eval_summary.json").write_text(json.dumps(
        {"n_action_steps": 4, "successes": 9, "episodes": 10, "aborted": 0, "seed": 42}))
    (d / "setup.json").write_text(json.dumps({"role": "jetson", "run": {"sim_location": "local"}, "platform": {}}))
    (d / "server_peak_rss.txt").write_text("VmHWM:\t 2561444 kB\n")


def run(*args):
    return subprocess.run([sys.executable, str(SUMMARIZE), *args], capture_output=True, text=True, check=True).stdout


class RssAlt(unittest.TestCase):
    def test_without_sidecar_the_row_has_no_alt_field(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "jetson" / "row1" / "20260101T000000Z"
            make_run(d)
            run("row", str(d), "--model", "M", "--params", "1M", "--precision", "p")
            r = json.loads((d / "row.json").read_text())
            self.assertEqual(r["peak_rss_mib"], 2501)
            self.assertNotIn("peak_rss_mib_mmprec_default", r)

    def test_sidecar_adds_the_column_and_the_note(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "jetson" / "row1" / "20260101T000000Z"
            make_run(d)
            (d / "rss_alt.json").write_text(json.dumps({"peak_rss_mib_mmprec_default": 1743, "note": "2 episodes only"}))
            run("row", str(d), "--model", "M", "--params", "1M", "--precision", "p")
            r = json.loads((d / "row.json").read_text())
            self.assertEqual(r["peak_rss_mib"], 2501)
            self.assertEqual(r["peak_rss_mib_mmprec_default"], 1743)
            out = run("table", t)
            header = out.splitlines()[0].split(" | ")
            line = [l for l in out.splitlines() if l.startswith("| M |")][0].split(" | ")
            i = header.index("peak_rss_mib_mmprec_default")
            self.assertEqual(line[i], "1743")
            self.assertEqual(line[header.index("peak_rss_mib")], "2501")
            self.assertIn("2 episodes only", out)


if __name__ == "__main__":
    unittest.main()
