"""Integrity of the forecast record (forecasts/).

These run in CI on every push, so an edited, deleted or backdated snapshot
fails loudly. Git history and tags on GitHub are the external clock.
"""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FC = ROOT / "forecasts"
sys.path.insert(0, str(ROOT / "src"))

import snapshot as S  # noqa: E402


def manifest():
    entries = {}
    for line in (FC / "MANIFEST.sha256").read_text().splitlines():
        digest, name = line.split("  ", 1)
        entries[name] = digest
    return entries


class TestForecastRecord(unittest.TestCase):
    def test_every_snapshot_matches_its_manifest_hash(self):
        m = manifest()
        for name, digest in m.items():
            body = (FC / name).read_bytes()
            self.assertEqual(hashlib.sha256(body).hexdigest(), digest, f"{name} was modified after it was recorded")

    def test_no_unregistered_or_missing_snapshots(self):
        files = {p.name for p in FC.glob("*.json")} | {f"games/{p.name}" for p in (FC / "games").glob("*.json")}
        self.assertEqual(files, set(manifest()), "snapshot files and MANIFEST.sha256 disagree")

    def test_live_snapshots_are_pregame_and_retrospectives_are_not(self):
        for p in FC.glob("*.json"):
            s = json.loads(p.read_text())
            self.assertIn(s["kind"], ("live", "retrospective"))
            if s["kind"] == "retrospective":
                self.assertFalse(s["pregame_verified"], p.name)
            elif s["pregame_verified"]:
                first = min(g["first_pitch_utc"] for g in s["next_games"])
                self.assertLess(s["created_at_utc"], first, p.name)

    def test_probabilities_are_coherent(self):
        for p in FC.glob("*.json"):
            s = json.loads(p.read_text())
            self.assertAlmostEqual(sum(v["title"] for v in s["odds"].values()), 1.0, places=6, msg=p.name)
            self.assertAlmostEqual(sum(v["pennant"] for v in s["odds"].values()), 2.0, places=6, msg=p.name)

    def test_game_forecasts_are_pregame_and_valid(self):
        for p in (FC / "games").glob("*.json"):
            g = json.loads(p.read_text())
            self.assertTrue(g["pregame_verified"], p.name)
            self.assertLess(g["created_at_utc"], g["first_pitch_utc"], p.name)
            self.assertAlmostEqual(g["p_home_win"] + g["p_away_win"], 1.0, places=9)

    def test_writer_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = S.FC
            S.FC = Path(tmp)
            try:
                snap = {"snapshot_id": "x", "kind": "live", "model_version": "t", "created_at_utc": "2026-01-01T00:00:00Z",
                        "information": {"games_through": "2026-01-01"}, "state_key": "s", "pregame_verified": False,
                        "odds": {"A": {"title": 1.0, "pennant": 1.0}}}
                S.write(snap)
                with self.assertRaises(FileExistsError):
                    S.write(snap)
            finally:
                S.FC = old


if __name__ == "__main__":
    unittest.main()
