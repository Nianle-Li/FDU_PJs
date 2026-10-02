"""
constraints.py  ——  BIO / BMES 合法转移掩码

掩码矩阵 mask[prev][cur] = True 表示允许该转移，False 表示禁止。
在 Viterbi 中将 mask=False 的转移路径直接设为 NEG_INF，等效于强制约束。

BIO 规则：
  - I-X 只能跟在 B-X 或 I-X 后面（且实体类型 X 相同）
  - B/O 可以出现在任意位置之后

BMES 规则（中文 NER 常用）：
  - B/S/O 可以作为句首；M/E 不能作为句首
  - E/S/O 可以作为句尾；B/M 不能作为句尾
  - B-X 只能跟 M-X 或 E-X
  - M-X 只能跟 M-X 或 E-X
  - E/S/O 后只能跟 B/S/O
"""
from typing import List


NEG_INF = -1e12


def _split_tag(tag: str) -> tuple:
    """将 "B-PER" 拆分为 ("B", "PER")，将 "O" 拆分为 ("O", "")。"""
    if tag == "O":
        return "O", ""
    prefix, entity_type = tag.split("-", 1)
    return prefix, entity_type


def is_valid_start(tag: str, scheme: str) -> bool:
    """
    判断 tag 是否可以作为句首标签。

    Args:
        tag:    标签字符串，如 "B-PER", "O", "I-ORG"
        scheme: 标注体系，"BIO" 或 "BMES"

    Returns:
        BIO  下：I 不能作为句首（实体必须由 B 开始）
        BMES 下：只有 B/S/O 可以作为句首
    """
    prefix, _ = _split_tag(tag)
    if scheme == "BIO":
        return prefix != "I"
    if scheme == "BMES":
        return prefix in ("B", "S", "O")
    return True


def is_valid_end(tag: str, scheme: str) -> bool:
    """
    判断 tag 是否可以作为句尾标签。

    Args:
        tag:    标签字符串
        scheme: "BIO" 或 "BMES"

    Returns:
        BMES 下：只有 E/S/O 可以作为句尾（B/M 表示实体未结束）
        BIO  下：任何标签均可结尾
    """
    prefix, _ = _split_tag(tag)
    if scheme == "BMES":
        return prefix in ("E", "S", "O")
    return True


def is_valid_transition(prev_tag: str, cur_tag: str, scheme: str) -> bool:
    """
    判断从 prev_tag 到 cur_tag 的标签转移是否合法。

    Args:
        prev_tag: 前一时刻的标签，如 "B-PER"
        cur_tag:  当前时刻的标签，如 "I-PER"
        scheme:   "BIO" 或 "BMES"

    Returns:
        True 表示合法转移，False 表示非法

    BIO 约束：
      - I-X 只能跟 B-X 或 I-X（类型必须相同）

    BMES 约束：
      - B-X 后只能跟 M-X 或 E-X（同类型）
      - M-X 后只能跟 M-X 或 E-X（同类型）
      - E/S/O 后只能跟 B/S/O
    """
    prev_prefix, prev_type = _split_tag(prev_tag)
    cur_prefix, cur_type = _split_tag(cur_tag)

    if scheme == "BIO":
        # I-X 必须跟在 B-X 或 I-X 后（且实体类型相同）
        if cur_prefix == "I":
            return prev_prefix in ("B", "I") and prev_type == cur_type
        return True

    if scheme == "BMES":
        # B/M 中间必须保持实体连续
        if prev_prefix in ("B", "M"):
            return cur_prefix in ("M", "E") and prev_type == cur_type
        # E/S/O 结束后只能开始新实体或 O
        if prev_prefix in ("E", "S", "O"):
            return cur_prefix in ("B", "S", "O")

    return True


def build_start_mask(tags: List[str], scheme: str) -> List[bool]:
    """返回每个标签是否可以作为句首。"""
    return [is_valid_start(tag, scheme) for tag in tags]


def build_end_mask(tags: List[str], scheme: str) -> List[bool]:
    """返回每个标签是否可以作为句尾。"""
    return [is_valid_end(tag, scheme) for tag in tags]


def build_constraint_mask(tags: List[str], scheme: str) -> List[List[bool]]:
    """
    返回 n_tags × n_tags 布尔矩阵。
    scheme: "BIO" 或 "BMES"
    """
    n = len(tags)
    mask = [[True] * n for _ in range(n)]

    for prev_id, prev_tag in enumerate(tags):
        for cur_id, cur_tag in enumerate(tags):
            mask[prev_id][cur_id] = is_valid_transition(prev_tag, cur_tag, scheme)

    return mask
