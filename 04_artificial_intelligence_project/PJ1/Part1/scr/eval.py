"""评估入口，支持分类与回归两类 checkpoint。"""

import argparse
import os
import glob

import numpy as np

from data import load_classification_data, prepare_mlp_input
from losses import cross_entropy_with_logits
from model import MLP
from utils import confusion_matrix, get_part1_root, load_checkpoint, precision_recall_f1, resolve_existing_path


def eval_classification(checkpoint_path: str, data_dir: str, invert: bool = True) -> None:
    """在分类数据上评估已保存的模型。"""
    ckpt = load_checkpoint(checkpoint_path)
    config = ckpt.get("config", {})
    model_cfg = config.get("model")
    if not model_cfg:
        raise ValueError("Checkpoint missing model config")
    model = MLP(model_cfg["layers"], model_cfg["activations"], model_cfg["output_activation"],
                 dropout_rates=model_cfg.get("dropout_rates", None))
    model.load_state(ckpt["state"])

    dataset = load_classification_data(resolve_existing_path(data_dir), invert=invert)
    x = prepare_mlp_input(dataset.images)
    y = dataset.labels

    logits, _ = model.forward(x)
    loss, _ = cross_entropy_with_logits(logits, y)
    pred = np.argmax(logits, axis=1)
    acc = float((pred == y).mean())

    cm = confusion_matrix(pred, y, num_classes=model_cfg["layers"][-1])
    prf = precision_recall_f1(cm)

    print(f"Loss: {loss:.6f}")
    print(f"Accuracy: {acc:.4f}")
    print("Per-class precision:", prf["precision"])
    print("Per-class recall:", prf["recall"])
    print("Per-class f1:", prf["f1"])


def eval_regression(checkpoint_path: str) -> None:
    """对回归任务在验证集上计算 MAE。"""
    ckpt = load_checkpoint(checkpoint_path)
    config = ckpt.get("config", {})
    model_cfg = config.get("model")
    if not model_cfg:
        raise ValueError("Checkpoint missing model config")
    model = MLP(model_cfg["layers"], model_cfg["activations"], model_cfg["output_activation"],
                 dropout_rates=model_cfg.get("dropout_rates", None))
    model.load_state(ckpt["state"])

    n_samples = config["regression"]["n_samples"]
    val_ratio = config["regression"]["val_split"]
    seed = config["seed"]

    from data import generate_sin_data
    from losses import mae

    x, y = generate_sin_data(n_samples, seed)

    exp_dir = os.path.dirname(os.path.abspath(checkpoint_path))
    split_file = os.path.join(exp_dir, "split_indices.npz")
    if os.path.exists(split_file):
        split_data = np.load(split_file)
        val_idx = split_data["val_idx"]
        x_val, y_val = x[val_idx], y[val_idx]
    else:
        import warnings
        warnings.warn("split_indices.npz not found; falling back to tail slice — val set may differ from training.")
        split = int(n_samples * (1.0 - val_ratio))
        x_val, y_val = x[split:], y[split:]

    pred, _ = model.forward(x_val)
    val_mae = mae(pred, y_val)
    status = "PASS" if val_mae < 0.01 else "FAIL"
    print(f"Val MAE: {val_mae:.6f}  [{status}]  (目标 < 0.01)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--data_dir", default=None)
    parser.add_argument("--task", choices=["classification", "regression"], default=None)
    parser.add_argument("--invert", action="store_true")
    args = parser.parse_args()

    def resolve_checkpoint(path: str, task: str | None = None) -> str:
        if os.path.isabs(path) and os.path.exists(path):
            return path
        if os.path.exists(path):
            return path
        basename = os.path.basename(path)
        part1_root = get_part1_root()
        if task:
            candidate = os.path.join(part1_root, "experiments", task, basename)
            if os.path.exists(candidate):
                return candidate
        candidates = glob.glob(os.path.join(part1_root, "experiments", "**", basename), recursive=True)
        if candidates:
            return candidates[0]
        return path

    if args.task is None:
        if args.data_dir:
            args.task = "classification"
        else:
            args.task = "regression"

    args.checkpoint = resolve_checkpoint(args.checkpoint, args.task)

    if args.task == "classification":
        if not args.data_dir:
            raise ValueError("--data_dir is required for classification")
        eval_classification(args.checkpoint, args.data_dir, invert=args.invert)
    else:
        eval_regression(args.checkpoint)


if __name__ == "__main__":
    main()

