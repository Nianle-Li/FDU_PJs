from __future__ import annotations

import unittest

import context  # noqa: F401
from fcqa.nl_query import build_nl_query, extract_search_term


class NaturalLanguageQueryTest(unittest.TestCase):
    def test_teacher_course_intent(self) -> None:
        plan = build_nl_query("李芳老师教什么课？")
        self.assertEqual(plan["intent"], "teacher_courses")
        self.assertEqual(plan["category"], "教师")
        self.assertEqual(plan["params"], ("%李芳%",))

    def test_building_facility_intent(self) -> None:
        plan = build_nl_query("第二教学楼有哪些自习室？")
        self.assertEqual(plan["intent"], "building_facilities")
        self.assertEqual(plan["params"], ("%第二教学楼%", "自习室"))

    def test_hot_activity_intent(self) -> None:
        plan = build_nl_query("热门活动有哪些？")
        self.assertEqual(plan["intent"], "hot_activities")

    def test_generic_activity_question_returns_recent_activities(self) -> None:
        plan = build_nl_query("校园活动？")
        self.assertEqual(plan["intent"], "recent_activities")
        self.assertEqual(plan["title"], "查询近期校园活动")
        self.assertEqual(plan["params"], ())

    def test_global_search_fallback_keeps_useful_term(self) -> None:
        self.assertEqual(extract_search_term("请问光华楼在哪里？"), "光华楼在")


if __name__ == "__main__":
    unittest.main()
