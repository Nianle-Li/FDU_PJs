"""评估模块：提供官方 token-level micro F1 与 span-level 实体 F1。"""
from typing import List, Tuple, Dict

from sklearn.metrics import precision_recall_fscore_support


def _parse_entities(tokens: List[str], tags: List[str]) -> set:
    """
    从 token 列表和标签列表中解析实体集合。
    返回 set of (start, end, entity_type)。
    同时兼容 BIO 和 BMES 标注体系。
    """
    entities = set()
    i = 0
    while i < len(tags):
        tag = tags[i]
        if tag == "O":
            i += 1
            continue

        prefix = tag.split("-")[0]
        entity_type = tag.split("-", 1)[1] if "-" in tag else tag

        if prefix == "S":
            entities.add((i, i + 1, entity_type))
            i += 1
        elif prefix == "B":
            j = i + 1
            while j < len(tags):
                next_prefix = tags[j].split("-")[0]
                next_type = tags[j].split("-", 1)[1] if "-" in tags[j] else tags[j]
                if next_prefix in ("M", "I") and next_type == entity_type:
                    j += 1
                elif next_prefix == "E" and next_type == entity_type:
                    j += 1
                    break
                else:
                    break
            entities.add((i, j, entity_type))
            i = j
        else:
            # 异常情况（如单独出现的 M/E/I），跳过
            i += 1
    return entities


def compute_official_f1(
    gold_sentences: List[List[Tuple[str, str]]],
    pred_sentences: List[List[str]],
) -> Dict[str, float]:
    """
    计算与 check.py 一致的 token-level micro F1（忽略 O 标签）。
    """
    y_true = []
    y_pred = []
    label_set = set()

    for gold_sent, pred_tags in zip(gold_sentences, pred_sentences):
        gold_tags = [tag for _, tag in gold_sent]
        if len(gold_tags) != len(pred_tags):
            raise ValueError("Prediction length does not match gold sentence length.")
        y_true.extend(gold_tags)
        y_pred.extend(pred_tags)
        label_set.update(gold_tags)
        label_set.update(pred_tags)

    entity_labels = sorted(label for label in label_set if label != "O")
    if not entity_labels:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=entity_labels,
        average="micro",
        zero_division=0,
    )
    return {
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
    }


def compute_span_f1(
    gold_sentences: List[List[Tuple[str, str]]],
    pred_sentences: List[List[str]],
) -> Dict[str, float]:
    """
    计算 micro-average precision、recall、F1。

    Args:
        gold_sentences: [(token, gold_tag), ...] 列表
        pred_sentences: [pred_tag, ...] 列表

    Returns:
        dict with keys: precision, recall, f1
    """
    tp = fp = fn = 0

    for gold_sent, pred_tags in zip(gold_sentences, pred_sentences):
        tokens = [t for t, _ in gold_sent]
        gold_tags = [t for _, t in gold_sent]

        gold_entities = _parse_entities(tokens, gold_tags)
        pred_entities = _parse_entities(tokens, pred_tags)

        tp += len(gold_entities & pred_entities)
        fp += len(pred_entities - gold_entities)
        fn += len(gold_entities - pred_entities)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {"precision": precision, "recall": recall, "f1": f1}


def compute_f1(
    gold_sentences: List[List[Tuple[str, str]]],
    pred_sentences: List[List[str]],
) -> Dict[str, float]:
    """兼容旧接口，默认返回官方 token-level micro F1。"""
    return compute_official_f1(gold_sentences, pred_sentences)


def print_metrics(metrics: Dict[str, float], prefix: str = "") -> None:
    prefix = f"[{prefix}] " if prefix else ""
    print(
        f"{prefix}Precision: {metrics['precision']:.4f}  "
        f"Recall: {metrics['recall']:.4f}  "
        f"F1: {metrics['f1']:.4f}"
    )
