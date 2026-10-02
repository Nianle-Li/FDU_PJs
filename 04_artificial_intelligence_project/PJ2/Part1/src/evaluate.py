"""
evaluate.py  ——  在验证集上运行推断并计算 F1

纯 Python 手写 micro avg F1，不依赖任何机器学习框架。
"""
from collections import defaultdict
from typing import List


SORTED_LABELS_ENG = [
    "O", "B-PER", "I-PER", "B-ORG", "I-ORG",
    "B-LOC", "I-LOC", "B-MISC", "I-MISC",
]

SORTED_LABELS_CHN = [
    "O",
    "B-NAME", "M-NAME", "E-NAME", "S-NAME",
    "B-CONT", "M-CONT", "E-CONT", "S-CONT",
    "B-EDU", "M-EDU", "E-EDU", "S-EDU",
    "B-TITLE", "M-TITLE", "E-TITLE", "S-TITLE",
    "B-ORG", "M-ORG", "E-ORG", "S-ORG",
    "B-RACE", "M-RACE", "E-RACE", "S-RACE",
    "B-PRO", "M-PRO", "E-PRO", "S-PRO",
    "B-LOC", "M-LOC", "E-LOC", "S-LOC",
]


def _classification_report(
    y_true: List[str],
    y_pred: List[str],
    labels: List[str],
) -> float:
    """
    手写 per-label 精度/召回/F1 报告，返回 micro avg F1。

    micro avg 只统计 labels 中的标签（即排除 "O"），与 sklearn
    classification_report 使用同名 labels 参数时的行为一致。
    """
    tp: dict = defaultdict(int)
    fp: dict = defaultdict(int)
    fn: dict = defaultdict(int)
    support: dict = defaultdict(int)

    label_set = set(labels)

    for gold, pred in zip(y_true, y_pred):
        if gold in label_set:
            support[gold] += 1
            if gold == pred:
                tp[gold] += 1
            else:
                fn[gold] += 1
        if pred in label_set and pred != gold:
            fp[pred] += 1

    # per-label 输出
    header = f"{'':>20s}  {'precision':>9s}  {'recall':>9s}  {'f1-score':>9s}  {'support':>8s}"
    print(header)
    print()
    for lbl in labels:
        p = tp[lbl] / (tp[lbl] + fp[lbl]) if (tp[lbl] + fp[lbl]) > 0 else 0.0
        r = tp[lbl] / (tp[lbl] + fn[lbl]) if (tp[lbl] + fn[lbl]) > 0 else 0.0
        f = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
        print(f"{lbl:>20s}  {p:9.4f}  {r:9.4f}  {f:9.4f}  {support[lbl]:>8d}")

    print()

    # micro avg
    total_tp = sum(tp[l] for l in labels)
    total_fp = sum(fp[l] for l in labels)
    total_fn = sum(fn[l] for l in labels)
    micro_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    micro_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    micro_f = 2 * micro_p * micro_r / (micro_p + micro_r) if (micro_p + micro_r) > 0 else 0.0
    total_support = sum(support[l] for l in labels)
    print(f"{'micro avg':>20s}  {micro_p:9.4f}  {micro_r:9.4f}  {micro_f:9.4f}  {total_support:>8d}")
    print()

    return micro_f


def evaluate(
    language: str,
    gold_path: str,
    pred_path: str,
) -> float:
    """返回 micro avg F1；同时打印 per-label 分类报告。"""
    sort_labels = SORTED_LABELS_ENG if language == "English" else SORTED_LABELS_CHN

    y_true, y_pred = [], []
    with open(gold_path, encoding="utf-8") as gf, open(pred_path, encoding="utf-8") as mf:
        gold_lines = gf.readlines()
        pred_lines = mf.readlines()

    if len(gold_lines) != len(pred_lines):
        raise ValueError(f"预测文件行数不一致: gold={len(gold_lines)} pred={len(pred_lines)}")

    for line_no, (g_line, m_line) in enumerate(zip(gold_lines, pred_lines), start=1):
        if g_line.strip() == "":
            if m_line.strip() != "":
                raise ValueError(f"第 {line_no} 行应为空行")
            continue
        g_parts = g_line.strip().split()
        m_parts = m_line.strip().split()
        if len(g_parts) != 2 or len(m_parts) != 2:
            raise ValueError(f"第 {line_no} 行格式错误")
        if g_parts[0] != m_parts[0]:
            raise ValueError(f"第 {line_no} 行 token 不一致: {g_parts[0]} != {m_parts[0]}")
        y_true.append(g_parts[1])
        y_pred.append(m_parts[1])

    # 排除 "O"，与官方 check.py 口径一致
    return _classification_report(y_true, y_pred, sort_labels[1:])
