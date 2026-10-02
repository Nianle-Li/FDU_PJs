from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import context  # noqa: F401

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.import_csv import ImportFailure, chunk_rows, normalize_entity, read_csv_rows  # noqa: E402


class ImportCsvCliTest(unittest.TestCase):
    def test_normalize_entity_accepts_alias(self) -> None:
        self.assertEqual(normalize_entity("building"), "buildings")
        self.assertEqual(normalize_entity("query_log"), "query_logs")

    def test_read_csv_rows_maps_chinese_headers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "buildings.csv"
            csv_path.write_text("建筑名称,建筑类型,校区ID\n批量测试楼,教学楼,1\n", encoding="utf-8")

            rows = read_csv_rows("buildings", csv_path)

        self.assertEqual(rows, [{"name": "批量测试楼", "type": "教学楼", "campus_id": "1"}])

    def test_read_csv_rows_rejects_empty_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "empty.csv"
            csv_path.write_text("name,type,campus_id\n", encoding="utf-8")

            with self.assertRaises(ImportFailure):
                read_csv_rows("buildings", csv_path)

    def test_chunk_rows_splits_by_batch_size(self) -> None:
        rows = [{"name": str(index)} for index in range(5)]
        batches = chunk_rows(rows, 2)

        self.assertEqual([len(batch) for batch in batches], [2, 2, 1])


if __name__ == "__main__":
    unittest.main()
