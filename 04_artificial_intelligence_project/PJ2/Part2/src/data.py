"""
数据加载与预处理模块
支持 CoNLL 格式（每行 "token tag"，句子间空行分隔）
"""
from typing import List, Tuple


Sentence = List[Tuple[str, str]]   # [(token, tag), ...]


def load_data(path: str) -> List[Sentence]:
    """读取 train.txt / validation.txt，按空行分句。

    Args:
        path: 文件路径

    Returns:
        sentences: 句子列表，每个句子为 [(token, tag), ...]
    """
    sentences: List[Sentence] = []
    current: Sentence = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.strip() == "":
                if current:
                    sentences.append(current)
                    current = []
            else:
                parts = line.split()
                if len(parts) >= 2:
                    token, tag = parts[0], parts[-1]
                    current.append((token, tag))
                # 跳过格式异常行
    if current:
        sentences.append(current)
    return sentences


def load_tokens(path: str) -> List[List[str]]:
    """读取测试文件（可能无标签），返回 token 列表。

    用于面试时 test.txt 只有 token 的情况；
    如果 test.txt 含标签，也可正确解析（忽略标签列）。
    """
    sentences: List[List[str]] = []
    current: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.strip() == "":
                if current:
                    sentences.append(current)
                    current = []
            else:
                parts = line.split()
                if parts:
                    current.append(parts[0])
    if current:
        sentences.append(current)
    return sentences


def write_predictions(
    path_in: str,
    pred_tags: List[List[str]],
    path_out: str,
) -> None:
    """将预测结果按原文件格式写出（保留空行位置）。

    Args:
        path_in:   原始输入文件（保持行数与空行位置）
        pred_tags: 预测标签列表，每个元素对应一个句子的标签序列
        path_out:  输出文件路径
    """
    sent_idx = 0
    tok_idx = 0
    with open(path_in, "r", encoding="utf-8") as fin, \
         open(path_out, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.rstrip("\n")
            if line.strip() == "":
                fout.write("\n")
                tok_idx = 0
                sent_idx += 1
            else:
                parts = line.split()
                token = parts[0]
                if sent_idx < len(pred_tags) and tok_idx < len(pred_tags[sent_idx]):
                    tag = pred_tags[sent_idx][tok_idx]
                else:
                    tag = "O"
                fout.write(f"{token} {tag}\n")
                tok_idx += 1
