import json
import os
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np


def get_part1_root() -> str:
    """返回 Part1 目录的绝对路径。"""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def get_pj1_root() -> str:
    """返回 PJ1 目录的绝对路径。"""
    return os.path.abspath(os.path.join(get_part1_root(), os.pardir))


def resolve_existing_path(path: str, extra_bases: List[str] | None = None) -> str:
    """解析已有路径，兼容目录迁移后的多种工作目录。"""
    if os.path.isabs(path):
        return path

    bases: List[str] = []
    if extra_bases:
        bases.extend([base for base in extra_bases if base])
    bases.extend([os.getcwd(), get_part1_root(), get_pj1_root()])

    seen = set()
    for base in bases:
        base = os.path.abspath(base)
        if base in seen:
            continue
        seen.add(base)
        candidate = os.path.abspath(os.path.join(base, path))
        if os.path.exists(candidate):
            return candidate
    return os.path.abspath(os.path.join(get_part1_root(), path))


def resolve_output_path(path: str, base_dir: str | None = None) -> str:
    """解析输出路径；相对路径默认相对于 Part1 根目录。"""
    if os.path.isabs(path):
        return path
    anchor = base_dir if base_dir else get_part1_root()
    return os.path.abspath(os.path.join(anchor, path))


def set_seed(seed: int) -> None:
    """设置随机种子，确保实验可复现（影响 numpy 和 random）。"""
    random.seed(seed)
    np.random.seed(seed)


def ensure_dir(path: str) -> None:
    """创建目录（如果不存在）。"""
    os.makedirs(path, exist_ok=True)


def stratified_split(labels: np.ndarray, val_ratio: float, seed: int) -> Tuple[np.ndarray, np.ndarray]:
    """按类别分层划分索引，返回 (train_idx, val_idx)。

    保持每个类别在训练/验证中的比例一致，避免类别不均衡带来偏差。
    """
    rng = np.random.default_rng(seed)
    train_idx = []
    val_idx = []
    for cls in np.unique(labels):
        cls_idx = np.where(labels == cls)[0]
        rng.shuffle(cls_idx)
        split = int(len(cls_idx) * (1.0 - val_ratio))
        train_idx.append(cls_idx[:split])
        val_idx.append(cls_idx[split:])
    return np.concatenate(train_idx), np.concatenate(val_idx)


def one_hot(labels: np.ndarray, num_classes: int) -> np.ndarray:
    """将标签向量转为 one-hot 矩阵，shape (N, num_classes)。"""
    out = np.zeros((labels.shape[0], num_classes), dtype=np.float32)
    out[np.arange(labels.shape[0]), labels] = 1.0
    return out


def accuracy(pred: np.ndarray, labels: np.ndarray) -> float:
    """计算预测准确率（0-1 之间）。"""
    return float((pred == labels).mean())


def confusion_matrix(pred: np.ndarray, labels: np.ndarray, num_classes: int) -> np.ndarray:
    """构造混淆矩阵，rows: true class, cols: predicted class。"""
    cm = np.zeros((num_classes, num_classes), dtype=np.int64)
    for p, t in zip(pred, labels):
        cm[t, p] += 1
    return cm


def precision_recall_f1(cm: np.ndarray) -> Dict[str, np.ndarray]:
    """从混淆矩阵计算 per-class precision/recall/f1。

    返回字典包含 numpy 数组：precision, recall, f1。
    """
    tp = np.diag(cm).astype(np.float32)
    fp = cm.sum(axis=0) - tp
    fn = cm.sum(axis=1) - tp
    precision = np.divide(tp, tp + fp, out=np.zeros_like(tp), where=(tp + fp) > 0)
    recall = np.divide(tp, tp + fn, out=np.zeros_like(tp), where=(tp + fn) > 0)
    f1 = np.divide(2 * precision * recall, precision + recall, out=np.zeros_like(tp), where=(precision + recall) > 0)
    return {"precision": precision, "recall": recall, "f1": f1}


@dataclass
class MetricTracker:
    history: List[Dict]

    def __init__(self) -> None:
        self.history = []

    def add(self, record: Dict) -> None:
        self.history.append(record)

    def save_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2)


def save_checkpoint(path: str, model_state: Dict, config: Dict, metrics: Dict) -> None:
    # 将模型参数以 W_/b_ 为键保存，同时保存 config 与 metrics 的 JSON 字符串
    np.savez(path, **model_state, config=json.dumps(config), metrics=json.dumps(metrics))


def load_checkpoint(path: str) -> Dict:
    # 读取由 save_checkpoint 保存的 npz 文件，恢复参数和配置信息
    data = np.load(path, allow_pickle=True)
    state = {k: data[k] for k in data.files if k.startswith("W_") or k.startswith("b_")}
    config = json.loads(str(data["config"])) if "config" in data.files else {}
    metrics = json.loads(str(data["metrics"])) if "metrics" in data.files else {}
    return {"state": state, "config": config, "metrics": metrics}

