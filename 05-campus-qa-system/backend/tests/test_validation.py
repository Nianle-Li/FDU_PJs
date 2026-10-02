from __future__ import annotations

import unittest
from http import HTTPStatus

import context  # noqa: F401
from fcqa.errors import ApiError
from fcqa.validation import clean_int, clean_text, parse_datetime_text


class ValidationTest(unittest.TestCase):
    def test_clean_text_strips_required_value(self) -> None:
        self.assertEqual(clean_text({"name": "  光华楼  "}, "name"), "光华楼")

    def test_clean_text_rejects_missing_required_value(self) -> None:
        with self.assertRaises(ApiError) as raised:
            clean_text({}, "name")
        self.assertEqual(raised.exception.status, HTTPStatus.BAD_REQUEST)

    def test_clean_int_accepts_numeric_text(self) -> None:
        self.assertEqual(clean_int({"campus_id": "3"}, "campus_id"), 3)

    def test_clean_int_rejects_non_numeric_value(self) -> None:
        with self.assertRaises(ApiError):
            clean_int({"campus_id": "abc"}, "campus_id")

    def test_parse_datetime_text_accepts_browser_datetime_local(self) -> None:
        self.assertEqual(parse_datetime_text("2026-05-30T10:00"), "2026-05-30 10:00")

    def test_parse_datetime_text_rejects_invalid_format(self) -> None:
        with self.assertRaises(ApiError):
            parse_datetime_text("not-a-date")


if __name__ == "__main__":
    unittest.main()
