from __future__ import annotations

import unittest
from http import HTTPStatus

import context  # noqa: F401
from fcqa.errors import ApiError
from fcqa.repositories.demo import DemoRepository


class DemoRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = DemoRepository()

    def test_building_lifecycle(self) -> None:
        created = self.repository.create_building({"name": "测试楼", "type": "教学楼", "campus_id": 1})
        self.assertEqual(created["campus_name"], "邯郸校区")

        updated = self.repository.update_building(
            created["building_id"],
            {"name": "测试楼A", "type": "综合楼", "campus_id": 1},
        )
        self.assertEqual(updated["name"], "测试楼A")

        deleted = self.repository.delete_building(created["building_id"])
        self.assertEqual(deleted, {"deleted": 1})

    def test_building_rejects_invalid_foreign_key_duplicate_and_invalid_type(self) -> None:
        with self.assertRaises(ApiError) as raised:
            self.repository.create_building({"name": "不存在校区楼", "type": "教学楼", "campus_id": 999})
        self.assertEqual(raised.exception.status, HTTPStatus.NOT_FOUND)

        with self.assertRaises(ApiError) as raised:
            self.repository.create_building({"name": "第二教学楼", "type": "教学楼", "campus_id": 1})
        self.assertEqual(raised.exception.status, HTTPStatus.BAD_REQUEST)

        with self.assertRaises(ApiError) as raised:
            self.repository.create_building({"name": "非法类型楼", "type": "魔法楼", "campus_id": 1})
        self.assertEqual(raised.exception.status, HTTPStatus.BAD_REQUEST)

    def test_delete_building_with_facilities_is_rejected(self) -> None:
        with self.assertRaises(ApiError) as raised:
            self.repository.delete_building(1)
        self.assertEqual(raised.exception.status, HTTPStatus.BAD_REQUEST)

    def test_facility_rejects_invalid_foreign_key_duplicate_and_referenced_delete(self) -> None:
        with self.assertRaises(ApiError) as raised:
            self.repository.create_facility(
                {"name": "不存在建筑教室", "type": "教室", "open_time": "09:00-18:00", "building_id": 999}
            )
        self.assertEqual(raised.exception.status, HTTPStatus.NOT_FOUND)

        with self.assertRaises(ApiError) as raised:
            self.repository.create_facility(
                {"name": "H2201", "type": "教室", "open_time": "09:00-18:00", "building_id": 2}
            )
        self.assertEqual(raised.exception.status, HTTPStatus.BAD_REQUEST)

        with self.assertRaises(ApiError) as raised:
            self.repository.create_facility(
                {"name": "非法设施", "type": "魔法设施", "open_time": "09:00-18:00", "building_id": 2}
            )
        self.assertEqual(raised.exception.status, HTTPStatus.BAD_REQUEST)

        with self.assertRaises(ApiError) as raised:
            self.repository.delete_facility(1)
        self.assertEqual(raised.exception.status, HTTPStatus.BAD_REQUEST)

    def test_activity_rejects_invalid_foreign_key_duplicate_and_invalid_time_range(self) -> None:
        payload = {
            "name": "边界测试活动",
            "description": "测试",
            "start_time": "2026-06-01T10:00",
            "end_time": "2026-06-01T11:00",
            "organizer": "测试组织",
            "facility_id": 999,
        }
        with self.assertRaises(ApiError) as raised:
            self.repository.create_activity(payload)
        self.assertEqual(raised.exception.status, HTTPStatus.NOT_FOUND)

        created = self.repository.create_activity({**payload, "facility_id": 4})
        self.assertEqual(created["name"], "边界测试活动")
        with self.assertRaises(ApiError) as raised:
            self.repository.create_activity({**payload, "facility_id": 4})
        self.assertEqual(raised.exception.status, HTTPStatus.BAD_REQUEST)

        with self.assertRaises(ApiError) as raised:
            self.repository.create_activity(
                {
                    **payload,
                    "name": "时间错误活动",
                    "start_time": "2026-06-01T12:00",
                    "end_time": "2026-06-01T11:00",
                    "facility_id": 4,
                }
            )
        self.assertEqual(raised.exception.status, HTTPStatus.BAD_REQUEST)

    def test_natural_language_query_returns_demo_rows(self) -> None:
        result = self.repository.natural_language_query({"question": "李芳老师教什么课？"})
        self.assertEqual(result["intent"], "teacher_courses")
        self.assertGreaterEqual(result["row_count"], 1)
        self.assertIn("SELECT", result["sql"])

    def test_empty_result_queries_return_empty_lists_and_zero_count_answer(self) -> None:
        self.assertEqual(self.repository.buildings({"q": "不存在的火星楼"}), [])
        self.assertEqual(self.repository.courses({"teacher": "不存在老师"}), [])
        self.assertEqual(self.repository.query_logs({"q": "不存在的查询内容"}), [])

        result = self.repository.natural_language_query({"question": "不存在的火星楼在哪里？"})
        self.assertEqual(result["row_count"], 0)
        self.assertIn("没有找到", result["answer"])

    def test_query_logs_include_written_records(self) -> None:
        self.repository.create_query_log({"user_id": 4, "query_category": "其他", "query_content": "测试查询"})
        rows = self.repository.query_logs({"q": "测试查询"})
        self.assertEqual(rows[0]["query_content"], "测试查询")

    def test_query_log_rejects_invalid_user_and_invalid_category(self) -> None:
        with self.assertRaises(ApiError) as raised:
            self.repository.create_query_log({"user_id": 999, "query_category": "活动", "query_content": "测试"})
        self.assertEqual(raised.exception.status, HTTPStatus.NOT_FOUND)

        with self.assertRaises(ApiError) as raised:
            self.repository.create_query_log({"user_id": 4, "query_category": "不存在", "query_content": "测试"})
        self.assertEqual(raised.exception.status, HTTPStatus.BAD_REQUEST)

    def test_popular_browse_methods(self) -> None:
        popular_queries = self.repository.popular_queries({})
        popular_activities = self.repository.popular_activities({})

        self.assertGreaterEqual(popular_queries[0]["query_count"], 1)
        self.assertGreaterEqual(popular_activities[0]["participant_count"], 1)

    def test_popular_queries_can_be_scoped_to_one_user(self) -> None:
        rows = self.repository.popular_queries({"user_id": "4", "limit": "20"})
        expected_count = len([row for row in self.repository.query_log_rows if row["user_id"] == 4])
        actual_count = sum(int(row["query_count"]) for row in rows)

        self.assertEqual(actual_count, expected_count)

    def test_natural_language_popular_queries_are_scoped_to_one_user(self) -> None:
        expected_count = len([row for row in self.repository.query_log_rows if row["user_id"] == 4])
        result = self.repository.natural_language_query({"question": "热门查询有哪些？", "user_id": 4})
        actual_count = sum(int(row["query_count"]) for row in result["rows"])

        self.assertEqual(result["intent"], "query_category_stats")
        self.assertEqual(actual_count, expected_count)

    def test_import_rows_reports_success_and_row_errors(self) -> None:
        result = self.repository.import_rows(
            {
                "entity": "query_logs",
                "rows": [
                    {"user_id": 4, "query_category": "活动", "query_content": "批量查询"},
                    {"user_id": 4, "query_category": "不存在", "query_content": "错误类别"},
                ],
            }
        )
        self.assertEqual(result["created_count"], 1)
        self.assertEqual(result["failed_count"], 1)
        self.assertEqual(result["errors"][0]["row"], 2)

    def test_activity_reservation_lifecycle(self) -> None:
        created = self.repository.reserve_activity(3, {"user_id": 4})
        self.assertEqual(created["status"], "待参加")

        reservations = self.repository.user_reservations(4)
        self.assertTrue(any(row["activity_id"] == 3 for row in reservations))

        deleted = self.repository.cancel_activity_reservation(3, 4)
        self.assertEqual(deleted, {"deleted": 1})

    def test_activity_reservation_rejects_missing_user_activity_and_missing_cancel(self) -> None:
        with self.assertRaises(ApiError) as raised:
            self.repository.reserve_activity(3, {"user_id": 999})
        self.assertEqual(raised.exception.status, HTTPStatus.NOT_FOUND)

        with self.assertRaises(ApiError) as raised:
            self.repository.reserve_activity(999, {"user_id": 4})
        self.assertEqual(raised.exception.status, HTTPStatus.NOT_FOUND)

        with self.assertRaises(ApiError) as raised:
            self.repository.cancel_activity_reservation(999, 4)
        self.assertEqual(raised.exception.status, HTTPStatus.NOT_FOUND)


if __name__ == "__main__":
    unittest.main()
