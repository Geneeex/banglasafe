"""Dataset JSONL files stay UTF-8 when the platform default is not UTF-8."""

import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import httpx

from banglasafe import dataset


class DatasetEncodingTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        real_open = io.open

        def open_with_cp1252(file, mode="r", buffering=-1, encoding=None, *args, **kwargs):
            # Pathlib may resolve an omitted encoding to the "locale" sentinel.
            if "b" not in mode and encoding in (None, "locale"):
                encoding = "cp1252"
            return real_open(file, mode, buffering, encoding, *args, **kwargs)

        legacy_encoding = patch("io.open", open_with_cp1252)
        legacy_encoding.start()
        self.addCleanup(legacy_encoding.stop)

    def test_append_jsonl_writes_utf8(self):
        path = self.directory / "results" / "responses.jsonl"
        record = {"response_id": "model-1", "response": "বাংলা উত্তর"}

        dataset.append_jsonl(path, record)

        expected = (json.dumps(record, ensure_ascii=False) + os.linesep).encode("utf-8")
        self.assertEqual(path.read_bytes(), expected)

    def test_read_jsonl_reads_utf8(self):
        path = self.directory / "prompts.jsonl"
        record = {"prompt_id": "bm-A-BN-1", "prompt": "বাংলা প্রশ্ন"}
        path.write_bytes((json.dumps(record, ensure_ascii=False) + "\n\n").encode("utf-8"))

        self.assertEqual(dataset.read_jsonl(path), [record])

    def test_load_done_reads_utf8(self):
        path = self.directory / "responses.jsonl"
        records = [
            {"response_id": "উত্তর-১", "response": "বাংলা উত্তর"},
            {"response_id": "উত্তর-২", "error": "retry this response"},
        ]
        payload = "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n"
        path.write_bytes(payload.encode("utf-8"))

        self.assertEqual(dataset.load_done(path), {"উত্তর-১"})

    def test_fetch_prompts_writes_utf8_and_reuses_cache(self):
        record = {"prompt_id": "bm-A-BN-1", "prompt": "বাংলা প্রশ্ন"}
        payload = json.dumps(record, ensure_ascii=False) + "\n"
        revision = "test-revision"
        url = dataset.FILE_URL.format(repo=dataset.HF_DATASET, rev=revision)
        response = httpx.Response(200, text=payload, request=httpx.Request("GET", url))
        get = Mock(return_value=response)
        cache = self.directory / "cache"

        with patch.object(dataset.httpx, "get", get), patch.object(dataset, "CACHE_DIR", cache):
            self.assertEqual(dataset.fetch_prompts(revision), [record])
            expected = payload.replace("\n", os.linesep).encode("utf-8")
            self.assertEqual((cache / f"prompts-{revision}.jsonl").read_bytes(), expected)
            self.assertEqual(dataset.fetch_prompts(revision), [record])

        get.assert_called_once_with(url, follow_redirects=True, timeout=60.0)


if __name__ == "__main__":
    unittest.main()
