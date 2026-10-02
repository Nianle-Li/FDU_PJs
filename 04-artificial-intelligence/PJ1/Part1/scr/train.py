"""训练入口，包含回归与分类两类流程。"""

import argparse
import json
import math
import os
from typing import Dict, Tuple

import numpy as np
import yaml

from data import augment_mlp_batch, generate_sin_data, load_classification_data, prepare_mlp_input, split_train_val
from losses import cross_entropy_with_logits, mae, mse_loss
from model import MLP
from optim import SGD
from utils import MetricTracker, ensure_dir, get_part1_root, resolve_existing_path, resolve_output_path, save_checkpoint, set_seed


def load_config(path: str) -> Dict:
    # 额外记录配置文件位置，便于后续解析相对路径。
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    config["__config_path"] = os.path.abspath(path)
    config["__config_dir"] = os.path.dirname(config["__config_path"])
    return config



def build_model(config: Dict) -> MLP:
    layers = config["model"]["layers"]
    activations = config["model"]["activations"]
    output_activation = config["model"]["output_activation"]
    dropout_rates = config["model"].get("dropout_rates", None)
    return MLP(layers, activations, output_activation, dropout_rates=dropout_rates)


def _get_lr(base_lr: float, epoch: int, total_epochs: int, sched_cfg: dict) -> float:
    """根据当前 epoch 计算学习率（支持 cosine / step 两种 schedule）。

    sched_cfg 为 train.lr_schedule 节点；若为 None / 未启用则返回 base_lr。
    cosine: lr_min + 0.5*(base_lr - lr_min)*(1 + cos(π*epoch/total_epochs))
    step:   base_lr * gamma ^ (epoch // step_size)
    """
    if not sched_cfg or not sched_cfg.get("enabled", False):
        return base_lr
    stype = sched_cfg.get("type", "cosine")
    if stype == "cosine":
        lr_min = sched_cfg.get("lr_min", base_lr * 0.01)
        return lr_min + 0.5 * (base_lr - lr_min) * (1.0 + math.cos(math.pi * epoch / total_epochs))
    elif stype == "step":
        step_size = sched_cfg.get("step_size", 100)
        gamma = sched_cfg.get("gamma", 0.5)
        return base_lr * (gamma ** (epoch // step_size))
    return base_lr


def save_config_copy(config: Dict, out_dir: str) -> None:
    serializable_config = {k: v for k, v in config.items() if not str(k).startswith("__")}
    with open(os.path.join(out_dir, "config.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(serializable_config, f, sort_keys=False)


def train_regression(config: Dict) -> None:
    exp_dir = resolve_output_path(config["experiment_dir"], base_dir=get_part1_root())
    ensure_dir(exp_dir)
    save_config_copy(config, exp_dir)

    seed = config["seed"]
    set_seed(seed)

    n_samples = config["regression"]["n_samples"]
    val_ratio = config["regression"]["val_split"]
    x, y = generate_sin_data(n_samples, seed)

    idx = np.arange(n_samples)
    np.random.shuffle(idx)
    split = int(n_samples * (1.0 - val_ratio))
    train_idx, val_idx = idx[:split], idx[split:]
    np.savez(os.path.join(exp_dir, "split_indices.npz"), train_idx=train_idx, val_idx=val_idx)

    x_train, y_train = x[train_idx], y[train_idx]
    x_val, y_val = x[val_idx], y[val_idx]

    model = build_model(config)
    train_cfg = config["train"]
    optimizer = SGD(train_cfg["lr"], train_cfg["momentum"], train_cfg["weight_decay"])

    tracker = MetricTracker()
    best_val_mae = float("inf")
    patience = train_cfg["early_stopping"]["patience"] if train_cfg["early_stopping"]["enabled"] else None
    no_improve = 0

    for epoch in range(1, train_cfg["epochs"] + 1):
        perm = np.random.permutation(x_train.shape[0])
        x_train = x_train[perm]
        y_train = y_train[perm]

        for i in range(0, x_train.shape[0], train_cfg["batch_size"]):
            xb = x_train[i : i + train_cfg["batch_size"]]
            yb = y_train[i : i + train_cfg["batch_size"]]
            pred, cache = model.forward(xb, training=True)
            loss, grad = mse_loss(pred, yb)
            model.backward(xb, cache, grad)
            model.apply_gradients(optimizer)

        val_pred, _ = model.forward(x_val)
        val_mae = mae(val_pred, y_val)

        tracker.add({"epoch": epoch, "val_mae": val_mae})

        if epoch % 20 == 0 or epoch == 1:
            print(f"[Regression] Epoch {epoch:4d}: val_mae={val_mae:.6f}")

        if val_mae < best_val_mae:
            best_val_mae = val_mae
            no_improve = 0
            save_checkpoint(
                os.path.join(exp_dir, "best_model.npz"),
                model.get_state(),
                config,
                {"val_mae": val_mae},
            )
        else:
            no_improve += 1

        if patience is not None and no_improve >= patience:
            break

    tracker.save_json(os.path.join(exp_dir, "train_log.json"))


def train_classification(config: Dict) -> None:
    exp_dir = resolve_output_path(config["experiment_dir"], base_dir=get_part1_root())
    ensure_dir(exp_dir)
    save_config_copy(config, exp_dir)

    seed = config["seed"]
    set_seed(seed)

    data_cfg = config["data"]
    extra_bases = []
    if config.get("__config_dir"):
        extra_bases.append(config["__config_dir"])
    data_dir = resolve_existing_path(data_cfg["data_dir"], extra_bases=extra_bases)
    dataset = load_classification_data(data_dir, invert=data_cfg.get("invert", True))
    train_idx, val_idx = split_train_val(dataset.labels, data_cfg["val_split"], seed)
    np.savez(os.path.join(exp_dir, "split_indices.npz"), train_idx=train_idx, val_idx=val_idx)

    x = prepare_mlp_input(dataset.images)
    y = dataset.labels
    x_train, y_train = x[train_idx], y[train_idx]
    full_train_mode = (len(val_idx) == 0)  # val_split=0 时全量训练，无验证集
    if not full_train_mode:
        x_val, y_val = x[val_idx], y[val_idx]

    model = build_model(config)
    train_cfg = config["train"]
    optimizer = SGD(train_cfg["lr"], train_cfg["momentum"], train_cfg["weight_decay"])

    use_aug = data_cfg.get("augmentation", False)
    aug_shift = data_cfg.get("aug_shift_range", 2)
    aug_rng = np.random.default_rng(seed + 9999)

    tracker = MetricTracker()
    best_val_acc = -1.0
    patience = train_cfg["early_stopping"]["patience"] if (not full_train_mode and train_cfg["early_stopping"]["enabled"]) else None
    no_improve = 0

    label_smoothing = train_cfg.get("label_smoothing", 0.0)
    sched_cfg = train_cfg.get("lr_schedule", {})

    for epoch in range(1, train_cfg["epochs"] + 1):
        optimizer.lr = _get_lr(train_cfg["lr"], epoch, train_cfg["epochs"], sched_cfg)

        perm = np.random.permutation(x_train.shape[0])
        x_train = x_train[perm]
        y_train = y_train[perm]

        batch_losses = []
        for i in range(0, x_train.shape[0], train_cfg["batch_size"]):
            xb = x_train[i : i + train_cfg["batch_size"]]
            yb = y_train[i : i + train_cfg["batch_size"]]
            if use_aug:
                xb = augment_mlp_batch(xb, shift_range=aug_shift, rng=aug_rng)
            logits, cache = model.forward(xb, training=True)
            loss, grad = cross_entropy_with_logits(logits, yb, label_smoothing=label_smoothing)
            batch_losses.append(loss)
            model.backward(xb, cache, grad)
            model.apply_gradients(optimizer)

        train_loss = float(np.mean(batch_losses))

        if full_train_mode:
            # 全量训练模式：无验证集，仅记录训练损失，在最后一轮保存模型
            tracker.add({"epoch": epoch, "train_loss": train_loss, "lr": optimizer.lr})
            if epoch % 10 == 0 or epoch == 1:
                print(f"[Classification-FullTrain] Epoch {epoch:4d}: lr={optimizer.lr:.5f} train_loss={train_loss:.4f}")
            if epoch == train_cfg["epochs"]:
                save_checkpoint(
                    os.path.join(exp_dir, "best_model.npz"),
                    model.get_state(),
                    config,
                    {"train_loss": train_loss},
                )
        else:
            val_logits, _ = model.forward(x_val, training=False)
            val_loss, _ = cross_entropy_with_logits(val_logits, y_val)
            val_pred = np.argmax(val_logits, axis=1)
            val_acc = float((val_pred == y_val).mean())

            tracker.add({"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss,
                         "val_acc": val_acc, "lr": optimizer.lr})

            if epoch % 10 == 0 or epoch == 1:
                print(f"[Classification] Epoch {epoch:4d}: lr={optimizer.lr:.5f} train_loss={train_loss:.4f}, val_loss={val_loss:.4f}, val_acc={val_acc:.4f}  (best={best_val_acc:.4f})")

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                no_improve = 0
                save_checkpoint(
                    os.path.join(exp_dir, "best_model.npz"),
                    model.get_state(),
                    config,
                    {"val_loss": val_loss, "val_acc": val_acc},
                )
            else:
                no_improve += 1

            if patience is not None and no_improve >= patience:
                print(f"[Classification] Early stopping at epoch {epoch}, best val_acc={best_val_acc:.4f}")
                break

    tracker.save_json(os.path.join(exp_dir, "train_log.json"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    config = load_config(args.config)
    task = config["task"]
    if task == "regression":
        train_regression(config)
    elif task == "classification":
        train_classification(config)
    else:
        raise ValueError(f"Unknown task: {task}")


if __name__ == "__main__":
    main()

