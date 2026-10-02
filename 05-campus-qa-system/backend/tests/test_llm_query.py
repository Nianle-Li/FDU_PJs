from __future__ import annotations

import unittest

import context  # noqa: F401
from fcqa.llm_query import (
    LlmQueryError,
    apply_current_user_context,
    chat_completions_url,
    normalize_query_plan,
    parse_json_object,
    prepare_readonly_sql,
)


class LlmQueryTest(unittest.TestCase):
    def test_parse_json_object_accepts_fenced_json(self) -> None:
        parsed = parse_json_object(
            """
```json
{"title":"查询课程","category":"课程","sql":"SELECT 1","params":{}}
```
"""
        )
        self.assertEqual(parsed["category"], "课程")

    def test_prepare_readonly_sql_wraps_limit(self) -> None:
        sql = prepare_readonly_sql("SELECT name FROM campus ORDER BY campus_id", 20)
        self.assertTrue(sql.startswith("SELECT * FROM ("))
        self.assertTrue(sql.endswith("LIMIT 20"))

    def test_prepare_readonly_sql_rejects_writes_and_multiple_statements(self) -> None:
        with self.assertRaises(LlmQueryError):
            prepare_readonly_sql("DELETE FROM users", 20)
        with self.assertRaises(LlmQueryError):
            prepare_readonly_sql("SELECT 1; SELECT 2", 20)

    def test_normalize_query_plan_defaults_unknown_category(self) -> None:
        plan = normalize_query_plan(
            {
                "title": "测试",
                "category": "不存在",
                "sql": "SELECT campus_id, name FROM campus",
                "params": {"q": "%邯郸%"},
            },
            10,
        )
        self.assertEqual(plan["intent"], "llm_sql")
        self.assertEqual(plan["category"], "其他")
        self.assertEqual(plan["params"], {"q": "%邯郸%"})

    def test_chat_url_accepts_base_or_full_endpoint(self) -> None:
        self.assertEqual(chat_completions_url("https://api.deepseek.com"), "https://api.deepseek.com/chat/completions")
        self.assertEqual(
            chat_completions_url("https://example.com/chat/completions"),
            "https://example.com/chat/completions",
        )

    def test_first_person_query_overrides_user_id_param(self) -> None:
        plan = {
            "intent": "llm_sql",
            "title": "我的活动",
            "category": "活动",
            "sql": "SELECT * FROM user_activity WHERE user_id = %(user_id)s",
            "params": {"user_id": 1},
        }
        updated = apply_current_user_context(plan, "我参与了哪些活动？", 2001)
        self.assertEqual(updated["params"]["user_id"], 2001)

    def test_non_first_person_query_keeps_user_id_param(self) -> None:
        plan = {
            "intent": "llm_sql",
            "title": "用户活动",
            "category": "活动",
            "sql": "SELECT * FROM user_activity WHERE user_id = %(user_id)s",
            "params": {"user_id": 1},
        }
        updated = apply_current_user_context(plan, "用户1参与了哪些活动？", 2001)
        self.assertEqual(updated["params"]["user_id"], 1)


if __name__ == "__main__":
    unittest.main()
