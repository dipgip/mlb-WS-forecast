"""Smoke test: the dashboard runs end to end on the committed outputs, and the
what-if simulator recomputes odds. Uses Streamlit's headless AppTest (no server).
"""
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "dashboard/app.py")


class TestDashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.at = AppTest.from_file(APP, default_timeout=120).run()

    def test_renders_without_errors(self):
        self.assertEqual([e.value for e in self.at.exception], [])
        self.assertEqual([e.value for e in self.at.error], [])
        self.assertTrue(self.at.title[0].value.startswith("⚾ The pick:"))

    def test_simulator_recomputes(self):
        def sim(at):
            return {m.label: float(m.value.rstrip("%")) for m in at.metric if "vs now" in str(m.proto.delta)}
        before = sim(self.at)
        at = AppTest.from_file(APP, default_timeout=120).run()
        # move the trailing team of a series that's still going to 4 wins
        series = {}
        for s in at.select_slider:
            if s.key and s.key.startswith(("alcs-", "nlcs-")):
                series.setdefault(s.key.split("-")[0], []).append(s)
        live = next((v for v in series.values() if max(s.value for s in v) < 4), None)
        if live:
            key = min(live, key=lambda s: s.value).key
            at.select_slider(key=key).set_value(4).run()
        else:
            # both LCS decided: change a model setting instead
            lam = next(s for s in at.select_slider if s.label.startswith("Shrinkage"))
            lam.set_value(20).run()
        after = sim(at)
        self.assertNotEqual(before, after)
        self.assertAlmostEqual(sum(after.values()), 100.0, delta=0.5)


if __name__ == "__main__":
    unittest.main()
