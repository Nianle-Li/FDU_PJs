"""Part2 工具函数：路径解析、随机种子、目录管理、checkpoint 存取、指标统计。"""

import json
import os
import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np


# ── 路径工具 ──────────────────────────────────────────────────────────────────

def get_part2_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def get_pj1_root() -> str:
    return os.path.abspath(os.path.join(get_part2_root(), os.pardir))


def resolve_existing_path(path: str, extra_bases: List[str] | None = None) -> str:
    """解析路径；相对路径依次从多个 base 尝试，返回第一个存在的。"""
    if os.path.isabs(path) and os.path.exists(path):
        return path
    bases: List[str] = list(extra_bases or [])
    bases += [os.getcwd(), get_part2_root(), get_pj1_root()]
    seen: set = set()
    for base in bases:
        base = os.path.abspath(base)
        if base in seen:
            continue
        seen.add(base)
        candidate = os.path.abspath(os.path.join(base, path))
        if os.path.exists(candidate):
            return candidate
    return os.path.abspath(os.path.join(get_part2_root(), path))


def resolve_output_path(path: str, base_dir: str | None = None) -> str:
    """解析输出路径；相对路径默认相对于 Part2 根目录。"""
    if os.path.isabs(path):
        return path
    anchor = base_dir if base_dir else get_part2_root()
    return os.path.abspath(os.path.join(anchor, path))


# ── 基础工具 ────────────────────────────────────────────────────────────────

def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    except ImportError:
        pass


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


# ── 数据划分 ─────────────────────────────────────────────────────────────────

def stratified_split(labels: np.ndarray, val_ratio: float, seed: int) -> Tuple[np.ndarray, np.ndarray]:
    """按类别分层划分，返回 (train_idx, val_idx)。"""
    rng = np.random.default_rng(seed)
    train_idx, val_idx = [], []
    for cls in np.unique(labels):
        cls_idx = np.where(labels == cls)[0]
        rng.shuffle(cls_idx)
        split = int(len(cls_idx) * (1.0 - val_ratio))
        train_idx.append(cls_idx[:split])
        val_idx.append(cls_idx[split:])
    return np.concatenate(train_idx), np.concatenate(val_idx)


# ── 评估指标 ──────────────────────────────────────────────────────────────────

def confusion_matrix(pred: np.ndarray, labels: np.ndarray, num_classes: int) -> np.ndarray:
    cm = np.zeros((num_classes, num_classes), dtype=np.int64)
    for p, t in zip(pred, labels):
        cm[t, p] += 1
    return cm


def precision_recall_f1(cm: np.ndarray) -> Dict[str, np.ndarray]:
    tp = np.diag(cm).astype(np.float32)
    fp = cm.sum(axis=0) - tp
    fn = cm.sum(axis=1) - tp
    precision = np.divide(tp, tp + fp, out=np.zeros_like(tp), where=(tp + fp) > 0)
    recall = np.divide(tp, tp + fn, out=np.zeros_like(tp), where=(tp + fn) > 0)
    f1 = np.divide(2 * precision * recall, precision + recall,
                   out=np.zeros_like(tp), where=(precision + recall) > 0)
    return {"precision": precision, "recall": recall, "f1": f1}


# ── 训练日志 ──────────────────────────────────────────────────────────────────

@dataclass
class MetricTracker:
    history: List[Dict] = field(default_factory=list)

    def add(self, record: Dict) -> None:
        self.history.append(record)

    def save_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2)


# ── Checkpoint 存取 ──────────────────────────────────────────────────────────

def save_checkpoint(path: str, state_dict: Dict, config: Dict, metrics: Dict) -> None:
    """保存 PyTorch 模型 state_dict 与训练配置到单一文件。"""
    import torch
    torch.save({"state_dict": state_dict, "config": config, "metrics": metrics}, path)


def load_checkpoint(path: str) -> Dict:
    """加载由 save_checkpoint 保存的文件。"""
    import torch
    data = torch.load(path, map_location="cpu", weights_only=False)
    return data
