from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hb_knowledge_app.hb_knowledge.local_index import LocalIndex, LocalIndexError, tokenize


class LocalIndexTest(unittest.TestCase):
    def test_chinese_and_equipment_tokens_retrieve_real_rows(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "index.jsonl"
            rows = [
                {
                    "dataset_id": "m607b-first-corpus",
                    "document_id": "K-C01",
                    "title": "过滤洗涤干燥机维护规程",
                    "version": "2.0",
                    "status_note": "现行有效性待核",
                    "section": "第 4 页 · 文本块 1",
                    "page_number": 4,
                    "chunk_id": "chunk-1",
                    "excerpt": "M607B 过滤洗涤干燥机应执行日常维护和月度维护。",
                },
                {
                    "dataset_id": "m607b-first-corpus",
                    "document_id": "K-C03",
                    "title": "公用工程清单",
                    "version": None,
                    "status_note": "设备适用性待核",
                    "section": "第 1 页 · 文本块 1",
                    "page_number": 1,
                    "chunk_id": "chunk-2",
                    "excerpt": "仪表压缩空气设计温度与设计压力见清单。",
                },
            ]
            path.write_text(
                "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
                encoding="utf-8",
            )
            path.chmod(0o600)
            index = LocalIndex.from_file(path)

            result = index.search(
                query="M607B 设备维护",
                dataset_ids=["m607b-first-corpus"],
                document_ids=["K-C01", "K-C03"],
                limit=5,
            )
            self.assertEqual("K-C01", result[0]["document_id"])
            self.assertEqual(4, result[0]["page_number"])
            self.assertNotIn(str(path), str(result))

    def test_document_allowlist_is_applied_before_search(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "index.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "dataset_id": "ds",
                        "document_id": "denied",
                        "chunk_id": "chunk",
                        "excerpt": "M607B maintenance",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            path.chmod(0o600)
            self.assertEqual(
                [],
                LocalIndex.from_file(path).search(
                    query="M607B",
                    dataset_ids=["ds"],
                    document_ids=["allowed"],
                    limit=5,
                ),
            )

    def test_private_index_rejects_broad_permissions(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "index.jsonl"
            path.write_text("{}\n", encoding="utf-8")
            path.chmod(0o644)
            with self.assertRaises(LocalIndexError):
                LocalIndex.from_file(path)

    def test_tokenizer_keeps_equipment_and_chinese_bigrams(self):
        tokens = tokenize("M607B 设备维护")
        self.assertIn("m607b", tokens)
        self.assertIn("设备", tokens)
        self.assertIn("维护", tokens)


if __name__ == "__main__":
    unittest.main()
