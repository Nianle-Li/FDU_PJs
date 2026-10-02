"""
data.py  ——  数据读写与句子切分
"""
from typing import List, Tuple, Optional


Sentence = List[Tuple[str, str]]   # [(token, tag), ...]


def load_sentences(path: str) -> List[Sentence]:
    """读取 BIO/BMES 格式文件，返回句子列表。每个句子是 (token, tag) 对列表。"""
    sentences: List[Sentence] = []
    current: Sentence = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.strip() == "":
                if current:
                    sentences.append(current)
                    current = []
            else:
                parts = line.strip().split()
                if len(parts) == 2:
                    token, tag = parts
                    current.append((token, tag))
                # 跳过格式异常行
    if current:
        sentences.append(current)
    return sentences


def load_tokens(path: str) -> Tuple[List[List[str]], List[Optional[str]]]:
    """
    读取测试集（可能有 tag 也可能没有 tag），返回：
      - sentences: [[token, ...], ...]
      - line_flags: 原始文件每行的 token（非空行）或 None（空行），用于还原输出
    """
    sentences: List[List[str]] = []
    line_flags: List[Optional[str]] = []
    current: List[str] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            stripped = line.rstrip("\n")
            if stripped.strip() == "":
                line_flags.append(None)
                if current:
                    sentences.append(current)
                    current = []
            else:
                parts = stripped.strip().split()
                token = parts[0]
                current.append(token)
                line_flags.append(token)
    if current:
        sentences.append(current)
    return sentences, line_flags


def write_predictions(
    path: str,
    line_flags: List[Optional[str]],
    predictions: List[List[str]],
) -> None:
    """
    按原始文件行结构写出预测结果。
    line_flags 中 None 对应空行，str 对应 token 行。
    predictions 是 [[tag, ...], ...] 按句子排列。
    """
    sent_idx = 0
    token_idx = 0
    lines = []
    for flag in line_flags:
        if flag is None:
            lines.append("")
            if token_idx > 0:
                token_idx = 0
                sent_idx += 1
        else:
            if sent_idx >= len(predictions) or token_idx >= len(predictions[sent_idx]):
                raise ValueError("预测序列与输入文件 token 数不一致")
            tag = predictions[sent_idx][token_idx]
            lines.append(f"{flag} {tag}")
            token_idx += 1
    if sent_idx < len(predictions):
        expected_sent_idx = sent_idx + (1 if token_idx > 0 else 0)
        if expected_sent_idx != len(predictions):
            raise ValueError("预测句子数与输入文件句子数不一致")
    with open(path, encoding="utf-8", mode="w") as f:
        f.write("\n".join(lines))
        if lines:
            f.write("\n")
