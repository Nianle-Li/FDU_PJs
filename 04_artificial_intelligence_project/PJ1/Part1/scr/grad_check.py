"""数值梯度检查工具：使用中心差分对模型参数的梯度进行验证。

在浮点精度要求较高时会将模型临时转为 float64 来提高差分精度。
"""

import argparse

import numpy as np

from losses import mse_loss
from model import MLP


def _to_f64(model: MLP) -> None:
    """将模型参数临时转为 float64 以提高数值精度。"""
    for k in model.params:
        model.params[k] = model.params[k].astype(np.float64)


def numeric_grad(model: MLP, x: np.ndarray, y: np.ndarray, eps: float = 1e-5) -> dict:
    grads = {}
    for name, param in model.params.items():
        grad = np.zeros_like(param, dtype=np.float64)
        it = np.nditer(param, flags=["multi_index"], op_flags=[["readwrite"]])
        while not it.finished:
            idx = it.multi_index
            orig = float(param[idx])
            param[idx] = orig + eps
            pred_pos, _ = model.forward(x)
            loss_pos, _ = mse_loss(pred_pos, y)
            param[idx] = orig - eps
            pred_neg, _ = model.forward(x)
            loss_neg, _ = mse_loss(pred_neg, y)
            grad[idx] = (loss_pos - loss_neg) / (2.0 * eps)
            param[idx] = orig
            it.iternext()
        grads[name] = grad
    return grads


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eps", type=float, default=1e-5)
    args = parser.parse_args()

    # 使用 float64 保证数值梯度精度（threshold 1e-5）
    model = MLP([1, 4, 1], ["tanh"], "linear")
    _to_f64(model)
    x = np.array([[0.2], [-0.4]], dtype=np.float64)
    y = np.sin(x)

    pred, cache = model.forward(x)
    _loss, grad = mse_loss(pred, y)
    model.backward(x, cache, grad)

    num_grads = numeric_grad(model, x, y, eps=args.eps)
    max_diff = 0.0
    for name in model.grads:
        analytic = model.grads[name].astype(np.float64)
        numeric = num_grads[name]
        diff = np.max(np.abs(analytic - numeric))
        max_diff = max(max_diff, diff)
        print(f"  {name}: max_diff={diff:.2e}")

    status = "PASS" if max_diff < 1e-5 else "FAIL"
    print(f"\nMax grad diff: {max_diff:.6e}  [{status}]")


if __name__ == "__main__":
    main()

