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
        key = next(s.key for s in at.select_slider if s.key.startswith("nlcs-") and s.value == 0)
        at.select_slider(key=key).set_value(4).run()
        after = sim(at)
        self.assertNotEqual(before, after)
        self.assertAlmostEqual(sum(after.values()), 100.0, delta=0.5)


if __name__ == "__main__":
    unittest.main()
