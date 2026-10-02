from typing import Tuple

import numpy as np


def mse_loss(pred: np.ndarray, target: np.ndarray) -> Tuple[float, np.ndarray]:
    """均方误差（MSE）。

    返回 (loss, grad)，其中 grad 为 dloss/dpred，已除以 batch_size。
    """
    diff = pred - target
    loss = float(np.mean(diff * diff))
    grad = (2.0 * diff) / pred.shape[0]
    return loss, grad


def mae(pred: np.ndarray, target: np.ndarray) -> float:
    """平均绝对误差（MAE），用于回归的参考指标。"""
    return float(np.mean(np.abs(pred - target)))


def softmax(logits: np.ndarray) -> np.ndarray:
    # 先减去每行最大值，避免指数上溢。
    shifted = logits - np.max(logits, axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / np.sum(exp, axis=1, keepdims=True)


def cross_entropy_with_logits(
    logits: np.ndarray, labels: np.ndarray, label_smoothing: float = 0.0
) -> Tuple[float, np.ndarray]:
    """从 logits 计算交叉熵损失，并返回对 logits 的梯度。"""
    probs = softmax(logits)
    n, num_classes = logits.shape[0], logits.shape[1]

    if label_smoothing > 0.0:
        one_hot = np.zeros_like(probs)
        one_hot[np.arange(n), labels] = 1.0
        soft_target = (1.0 - label_smoothing) * one_hot + label_smoothing / num_classes
        log_probs = np.sum(-soft_target * np.log(np.clip(probs, 1e-12, 1.0)), axis=1)
        loss = float(np.mean(log_probs))
        grad = (probs - soft_target) / n
    else:
        log_probs = -np.log(np.clip(probs[np.arange(n), labels], 1e-12, 1.0))
        loss = float(np.mean(log_probs))
        grad = probs.copy()
        grad[np.arange(n), labels] -= 1.0
        grad /= n

    return loss, grad

