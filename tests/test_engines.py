import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from synth import make_synthetic_video

from hoostruct.engines import get_engine
from hoostruct.ingest import ingest
from hoostruct.sampling import FixedIntervalSampler

FAKE_VLM_RESPONSE = {
    "message": {"content": json.dumps({"summary": "test scene", "events": []})}
}


class EngineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.src = str(Path(cls.tmp.name) / "synthetic.avi")
        # motion during 0-3s, still during 3-6s
        make_synthetic_video(cls.src, seconds=6.0, fps=10, moving_until=3.0)
        cls.source = ingest(cls.src)
        cls.windows = list(FixedIntervalSampler(2.0).windows(cls.src, cls.source.duration_s))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_ingest_fallback_fills_meta(self):
        self.assertAlmostEqual(self.source.duration_s, 6.0, delta=0.5)
        self.assertAlmostEqual(self.source.fps, 10.0, delta=0.5)
        self.assertEqual(self.source.width, 160)
        self.assertEqual(self.source.kind, "video")

    def test_motion_distinguishes_active_and_static(self):
        engine = get_engine("motion", sample_fps=5.0)
        records = list(engine.extract(self.source, iter(self.windows)))
        self.assertEqual(len(records), 3)
        self.assertTrue(all(r.event_type == "motion.activity" for r in records))
        active, static = records[0].payload, records[2].payload
        self.assertGreater(active["activity_mean"], static["activity_mean"])
        self.assertGreater(active["activity_mean"], 0.005)
        self.assertLess(static["activity_mean"], 0.005)

    def test_vlm_with_mocked_server(self):
        engine = get_engine("vlm", model="fake", frames_per_window=1)
        with mock.patch("hoostruct.engines.vlm._post_json", return_value=FAKE_VLM_RESPONSE) as post:
            records = list(engine.extract(self.source, iter(self.windows)))
        self.assertEqual(len(records), 3)
        self.assertEqual(records[0].event_type, "vlm.observation")
        self.assertEqual(records[0].payload["summary"], "test scene")
        self.assertEqual(records[0].engine_version, "fake")
        sent = post.call_args_list[0].args[1]
        self.assertEqual(len(sent["messages"][0]["images"]), 1)
        self.assertEqual(sent["format"]["type"], "object")

    def test_gated_sends_only_active_windows_to_vlm(self):
        engine = get_engine(
            "motion+vlm", gate_threshold=0.005, sample_fps=5.0, model="fake", frames_per_window=1
        )
        with mock.patch("hoostruct.engines.vlm._post_json", return_value=FAKE_VLM_RESPONSE):
            records = list(engine.extract(self.source, iter(self.windows)))
        motion = [r for r in records if r.event_type == "motion.activity"]
        vlm = [r for r in records if r.event_type == "vlm.observation"]
        self.assertEqual(len(motion), 3)
        self.assertGreaterEqual(len(vlm), 1)
        self.assertLess(len(vlm), 3)
        # the still window (4-6s) must not reach the VLM
        self.assertNotIn(4.0, [r.t_start for r in vlm])


if __name__ == "__main__":
    unittest.main()
