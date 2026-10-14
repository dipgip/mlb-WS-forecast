"""Both report builders must run end to end on the committed data.

The 2026-10-14 scheduled refresh crashed in report/build_md.py on the first
unplayed game in the record (a NaN result), after every model test had passed.
This builds both reports into a temp folder (REPORT_OUT) so report bugs fail
in CI, not in the middle of a refresh.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestReportBuilds(unittest.TestCase):
    def test_html_and_markdown_reports_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, REPORT_OUT=tmp, MPLBACKEND="Agg")
            for script in ("report/build.py", "report/build_md.py"):
                r = subprocess.run([sys.executable, script], cwd=ROOT, env=env, capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, f"{script} failed:\n{r.stderr[-2000:]}")
            data = json.loads((Path(tmp) / "data.json").read_text())  # strict JSON: NaN would fail to parse
            for g in data["record"]["games"]:
                self.assertTrue(g["winner"] is None or isinstance(g["winner"], str), g)
            md = (Path(tmp) / "REPORT.md").read_text()
            self.assertIn("## The forecast record", md)
            self.assertIn("/*__DATA__*/", (ROOT / "report/template.html").read_text())
            self.assertNotIn("/*__DATA__*/null", (Path(tmp) / "index.html").read_text())


if __name__ == "__main__":
    unittest.main()
