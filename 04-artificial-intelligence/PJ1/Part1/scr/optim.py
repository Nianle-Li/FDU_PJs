from typing import Dict

import numpy as np


class SGD:
    """简单的 SGD 优化器，支持 momentum 与 L2 权重衰减（weight decay）。

    使用方法：optimizer.step(params, grads)，会就地更新 params 字典中的数组。
    约定：只对以 `W_` 开头的键应用 weight decay（避免对 bias 应用 L2）。
    """

    def __init__(self, lr: float, momentum: float = 0.0, weight_decay: float = 0.0) -> None:
        self.lr = lr
        self.momentum = momentum
        self.weight_decay = weight_decay
        self.velocity: Dict[str, np.ndarray] = {}

    def step(self, params: Dict[str, np.ndarray], grads: Dict[str, np.ndarray]) -> None:
        # 对 params 中每个参数按 grads 更新（键名必须与 model.params 对齐）
        for k, v in params.items():
            grad = grads.get(k)
            if grad is None:
                # 如果该参数没有对应梯度，则跳过（例如某些层被固定）
                continue
            # L2 正则：仅对权重 W_ 加上 weight_decay * W
            if self.weight_decay > 0.0 and k.startswith("W_"):
                grad = grad + self.weight_decay * v
            if self.momentum > 0.0:
                # 使用动量项进行加速
                if k not in self.velocity:
                    self.velocity[k] = np.zeros_like(v)
                self.velocity[k] = self.momentum * self.velocity[k] - self.lr * grad
                params[k] = v + self.velocity[k]
            else:
                # 标准 SGD 步长
                params[k] = v - self.lr * grad

