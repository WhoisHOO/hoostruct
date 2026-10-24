import json
import tempfile
import unittest
from pathlib import Path

from hoostruct.integrity import verify_chain
from hoostruct.pipeline import run
from hoostruct.retention import RetentionAction
from hoostruct.sampling import FixedIntervalSampler
from hoostruct.storage import get_sink


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        # the mock engine never decodes, so any file works as a source
        self.src = Path(self.tmp.name) / "fake.bin"
        self.src.write_bytes(b"\x00" * 1024)
        self.out = str(Path(self.tmp.name) / "out")

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, **kwargs):
        return run(
            str(self.src),
            sink=get_sink("jsonl", self.out),
            sampler=FixedIntervalSampler(10.0),
            **kwargs,
        )

    def test_mock_refine_writes_records_and_manifest(self):
        m = self._run()
        self.assertGreaterEqual(m.record_count, 1)
        self.assertEqual(len(m.source.source_id), 64)

        records_file = Path(m.records_path)
        self.assertTrue(records_file.exists())
        dicts = [json.loads(l) for l in records_file.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(dicts), m.record_count)
        self.assertEqual(dicts[-1]["record_hash"], m.chain_head)

        manifest_file = records_file.with_name(
            records_file.name.replace(".records.jsonl", ".manifest.json")
        )
        self.assertTrue(manifest_file.exists())

    def test_chain_verifies_and_detects_tampering(self):
        m = self._run()
        records_file = Path(m.records_path)
        dicts = [json.loads(l) for l in records_file.read_text(encoding="utf-8").splitlines()]

        n, errors = verify_chain(dicts)
        self.assertEqual(n, m.record_count)
        self.assertEqual(errors, [])

        dicts[0]["payload"]["note"] = "tampered value"
        _, errors = verify_chain(dicts)
        self.assertTrue(errors)

    def test_default_retention_keeps_source(self):
        self._run()
        self.assertTrue(self.src.exists())

    def test_delete_source_after_manifest(self):
        m = self._run(retention=RetentionAction.DELETE)
        self.assertFalse(self.src.exists())
        self.assertEqual(m.retention_action, "delete")
        self.assertTrue(Path(m.records_path).exists())


if __name__ == "__main__":
    unittest.main()
