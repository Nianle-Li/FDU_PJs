from __future__ import annotations

import re


FIRST_PERSON_TOKENS = ("我", "我的", "自己", "当前用户")
ACTIVITY_CONTEXT_TOKENS = ("活动", "讲座", "报名", "参加", "参与", "预约")
PARTICIPANT_ROSTER_TOKENS = (
    "哪些用户",
    "哪些人",
    "谁参加",
    "谁参与",
    "都有谁",
    "参加名单",
    "参与名单",
    "报名名单",
    "参加者",
    "参与者",
    "报名用户",
    "参加用户",
    "参与用户",
    "预约用户",
)


def is_activity_participant_roster_question(question: str) -> bool:
    compact = re.sub(r"\s+", "", question)
    if any(token in compact for token in FIRST_PERSON_TOKENS):
        return False
    return any(token in compact for token in ACTIVITY_CONTEXT_TOKENS) and any(
        token in compact for token in PARTICIPANT_ROSTER_TOKENS
    )
