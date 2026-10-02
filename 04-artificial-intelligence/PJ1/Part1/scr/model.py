"""多层感知机实现，负责前向传播、反向传播与参数状态管理。"""

from typing import Dict, List, Optional, Tuple

import numpy as np


def relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(0.0, x)


def relu_grad(x: np.ndarray) -> np.ndarray:
    return (x > 0).astype(np.float32)


def tanh(x: np.ndarray) -> np.ndarray:
    return np.tanh(x)


def tanh_grad(x: np.ndarray) -> np.ndarray:
    y = np.tanh(x)
    return 1.0 - y * y


def linear(x: np.ndarray) -> np.ndarray:
    return x


def linear_grad(x: np.ndarray) -> np.ndarray:
    return np.ones_like(x, dtype=np.float32)


ACTIVATIONS = {
    "relu": (relu, relu_grad),
    "tanh": (tanh, tanh_grad),
    "linear": (linear, linear_grad),
}


class MLP:
    def __init__(
        self,
        layer_sizes: List[int],
        activations: List[str],
        output_activation: str,
        dropout_rates: Optional[List[float]] = None,
    ) -> None:
        """初始化 MLP。

        `dropout_rates` 对应各隐藏层的 Inverted Dropout 丢弃率；
        推理阶段关闭 Dropout，无需额外缩放。
        """
        if len(layer_sizes) < 2:
            raise ValueError("layer_sizes must include input and output")
        if len(activations) != len(layer_sizes) - 2:
            raise ValueError("activations length must match hidden layers")
        self.layer_sizes = layer_sizes
        self.activations = activations
        self.output_activation = output_activation
        self.dropout_rates: List[float] = list(dropout_rates) if dropout_rates else []
        self.params: Dict[str, np.ndarray] = {}
        self.grads: Dict[str, np.ndarray] = {}
        self._init_params()

    def _init_params(self) -> None:
        for i in range(len(self.layer_sizes) - 1):
            in_dim = self.layer_sizes[i]
            out_dim = self.layer_sizes[i + 1]
            if i < len(self.activations):
                act = self.activations[i]
            else:
                act = self.output_activation
            if act == "tanh":
                scale = np.sqrt(2.0 / (in_dim + out_dim))
            elif act == "relu":
                scale = np.sqrt(2.0 / in_dim)
            else:
                scale = 0.01
            self.params[f"W_{i}"] = (np.random.randn(in_dim, out_dim) * scale).astype(np.float32)
            self.params[f"b_{i}"] = np.zeros((1, out_dim), dtype=np.float32)

    def forward(
        self, x: np.ndarray, training: bool = False
    ) -> Tuple[np.ndarray, List[Tuple]]:
        """前向传播；训练阶段对隐藏层按需施加 Inverted Dropout。"""
        cache = []
        out = x
        for i in range(len(self.layer_sizes) - 1):
            w = self.params[f"W_{i}"]
            b = self.params[f"b_{i}"]
            z = out @ w + b
            act_name = self.activations[i] if i < len(self.activations) else self.output_activation
            act_fn, _ = ACTIVATIONS[act_name]
            out = act_fn(z)
            mask = None
            if training and i < len(self.dropout_rates):
                rate = self.dropout_rates[i]
                if rate > 0.0:
                    mask = (np.random.rand(*out.shape) > rate).astype(np.float32)
                    out = out * mask / (1.0 - rate)
            cache.append((out, z, act_name, mask))
        return out, cache

    def backward(self, x: np.ndarray, cache: List[Tuple], dout: np.ndarray) -> None:
        """反向传播并将结果保存到 `self.grads`。"""
        dx = dout
        for i in reversed(range(len(self.layer_sizes) - 1)):
            out, z, act_name, mask = cache[i]
            _, act_grad = ACTIVATIONS[act_name]
            if mask is not None:
                rate = self.dropout_rates[i]
                dx = dx * mask / (1.0 - rate)
            dz = dx * act_grad(z)
            prev_out = x if i == 0 else cache[i - 1][0]
            self.grads[f"W_{i}"] = prev_out.T @ dz
            self.grads[f"b_{i}"] = np.sum(dz, axis=0, keepdims=True)
            dx = dz @ self.params[f"W_{i}"].T

    def apply_gradients(self, optimizer) -> None:
        optimizer.step(self.params, self.grads)

    def get_state(self) -> Dict[str, np.ndarray]:
        return {k: v.copy() for k, v in self.params.items()}

    def load_state(self, state: Dict[str, np.ndarray]) -> None:
        for k, v in state.items():
            if k in self.params:
                self.params[k] = v.copy()

