"""Part2 训练入口：YAML 驱动，支持固定验证集选型与全量重训两阶段策略。"""

import argparse
import copy
import math
import os
from typing import Dict, Optional

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim_module
import yaml
from torch.utils.data import DataLoader

from dataset import HandwritingDataset, build_train_transform, mixup_batch
from model import build_model
from utils import (
    MetricTracker, ensure_dir, get_part2_root,
    resolve_existing_path, resolve_output_path,
    save_checkpoint, set_seed, stratified_split,
)


# ── 配置加载 ──────────────────────────────────────────────────────────────────

def load_config(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    config["__config_path"] = os.path.abspath(path)
    config["__config_dir"]  = os.path.dirname(config["__config_path"])
    return config


def save_config_copy(config: Dict, out_dir: str) -> None:
    serializable = {k: v for k, v in config.items() if not str(k).startswith("__")}
    with open(os.path.join(out_dir, "config.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(serializable, f, sort_keys=False)


# ── 学习率调度 ────────────────────────────────────────────────────────────────

def get_lr(base_lr: float, epoch: int, total_epochs: int, sched_cfg: dict) -> float:
    """Cosine / Step 学习率衰减（与 Part1 接口一致）。"""
    if not sched_cfg or not sched_cfg.get("enabled", False):
        return base_lr
    stype = sched_cfg.get("type", "cosine")
    if stype == "cosine":
        lr_min = sched_cfg.get("lr_min", base_lr * 0.01)
        return lr_min + 0.5 * (base_lr - lr_min) * (1.0 + math.cos(math.pi * epoch / total_epochs))
    elif stype == "step":
        gamma     = sched_cfg.get("gamma", 0.5)
        step_size = sched_cfg.get("step_size", 50)
        return base_lr * (gamma ** (epoch // step_size))
    return base_lr


# ── EMA（指数移动平均） ───────────────────────────────────────────────────────

class EMA:
    """对模型参数维护指数移动平均快照，推理时使用 EMA 参数。"""

    def __init__(self, model: nn.Module, decay: float = 0.999) -> None:
        self.decay  = decay
        self.shadow = {k: v.clone().detach() for k, v in model.state_dict().items()}

    def update(self, model: nn.Module) -> None:
        for k, v in model.state_dict().items():
            self.shadow[k] = self.decay * self.shadow[k] + (1.0 - self.decay) * v.detach()

    def apply(self, model: nn.Module) -> None:
        model.load_state_dict(self.shadow)

    def state_dict(self) -> Dict[str, torch.Tensor]:
        return {k: v.clone().detach().cpu() for k, v in self.shadow.items()}


# ── 单 epoch 训练 ─────────────────────────────────────────────────────────────

def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    mixup_alpha: float = 0.0,
    num_classes: int = 12,
    ema: Optional[EMA] = None,
) -> float:
    model.train()
    total_loss = 0.0
    for images, labels in loader:
        images = images.to(device)
        labels = labels.to(device)

        if mixup_alpha > 0.0:
            images, soft_labels = mixup_batch(images, labels, alpha=mixup_alpha,
                                               num_classes=num_classes)
            soft_labels = soft_labels.to(device)
            logits = model(images)
            # soft cross-entropy: -sum(soft * log_softmax)
            log_probs = torch.log_softmax(logits, dim=-1)
            loss = -(soft_labels * log_probs).sum(dim=-1).mean()
        else:
            logits = model(images)
            loss = criterion(logits, labels)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        if ema is not None:
            ema.update(model)

        total_loss += loss.item() * images.size(0)

    return total_loss / len(loader.dataset)


# ── 验证 ──────────────────────────────────────────────────────────────────────

@torch.no_grad()
def evaluate(model: nn.Module, loader: DataLoader, criterion: nn.Module,
             device: torch.device) -> Dict:
    model.eval()
    total_loss, correct, total = 0.0, 0, 0
    for images, labels in loader:
        images, labels = images.to(device), labels.to(device)
        logits = model(images)
        loss = criterion(logits, labels)
        total_loss += loss.item() * images.size(0)
        pred = logits.argmax(dim=1)
        correct += (pred == labels).sum().item()
        total += images.size(0)
    return {"loss": total_loss / total, "acc": correct / total}


# ── 主训练流程 ────────────────────────────────────────────────────────────────

def train(config: Dict) -> None:
    exp_dir = resolve_output_path(config["experiment_dir"], base_dir=get_part2_root())
    ensure_dir(exp_dir)
    save_config_copy(config, exp_dir)

    seed = config.get("seed", 42)
    set_seed(seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[Train] device={device}, experiment_dir={exp_dir}")

    # 数据
    extra_bases = [config.get("__config_dir", "")]
    data_cfg    = config["data"]
    data_dir    = resolve_existing_path(data_cfg["data_dir"], extra_bases=extra_bases)
    val_ratio   = data_cfg.get("val_split", 0.1)
    invert      = data_cfg.get("invert", True)
    aug_cfg     = config.get("augment", {})
    train_transform = build_train_transform(aug_cfg)

    # 划分索引
    full_ds = HandwritingDataset(data_dir, invert=invert)
    all_labels = np.asarray(full_ds.labels, dtype=np.int64)

    full_train_mode = (val_ratio == 0.0)
    if full_train_mode:
        train_idx = np.arange(len(all_labels))
        val_idx   = np.array([], dtype=np.int64)
    else:
        train_idx, val_idx = stratified_split(all_labels, val_ratio, seed)

    np.savez(
        os.path.join(exp_dir, "split_indices.npz"),
        train_idx=train_idx, val_idx=val_idx,
    )
    print(f"[Train] total={len(all_labels)}, train={len(train_idx)}, val={len(val_idx)}")

    train_ds = HandwritingDataset(data_dir, indices=train_idx, invert=invert,
                                  transform=train_transform)
    val_ds   = HandwritingDataset(data_dir, indices=val_idx,   invert=invert) \
               if not full_train_mode else None

    train_cfg  = config["train"]
    batch_size = train_cfg.get("batch_size", 64)
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,
                              num_workers=0, pin_memory=False)
    val_loader   = DataLoader(val_ds, batch_size=batch_size, shuffle=False,
                              num_workers=0) if val_ds else None

    # 模型
    model = build_model(config).to(device)
    num_classes = config["model"].get("num_classes", 12)

    # 损失
    label_smoothing = train_cfg.get("label_smoothing", 0.0)
    criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)

    # 优化器
    opt_type  = train_cfg.get("optimizer", "adamw").lower()
    lr        = train_cfg.get("lr", 1e-3)
    wd        = train_cfg.get("weight_decay", 5e-5)
    if opt_type == "adamw":
        optimizer = optim_module.AdamW(model.parameters(), lr=lr, weight_decay=wd)
    elif opt_type == "adam":
        optimizer = optim_module.Adam(model.parameters(), lr=lr, weight_decay=wd)
    elif opt_type == "sgd":
        momentum  = train_cfg.get("momentum", 0.9)
        optimizer = optim_module.SGD(model.parameters(), lr=lr, momentum=momentum,
                                     weight_decay=wd, nesterov=True)
    else:
        raise ValueError(f"未知 optimizer: {opt_type}")

    # EMA
    use_ema    = train_cfg.get("use_ema", False)
    ema_decay  = train_cfg.get("ema_decay", 0.999)
    ema        = EMA(model, decay=ema_decay) if use_ema else None

    # Mixup
    mixup_alpha = aug_cfg.get("mixup_alpha", 0.0)

    # LR schedule
    sched_cfg = train_cfg.get("lr_schedule", {})
    epochs    = train_cfg.get("epochs", 150)

    # Early stopping
    es_cfg    = train_cfg.get("early_stopping", {})
    patience  = es_cfg.get("patience", 30) if (es_cfg.get("enabled", False) and not full_train_mode) else None
    no_improve  = 0
    best_val_acc = -1.0

    tracker = MetricTracker()

    for epoch in range(1, epochs + 1):
        # 更新学习率
        new_lr = get_lr(lr, epoch, epochs, sched_cfg)
        for pg in optimizer.param_groups:
            pg["lr"] = new_lr

        train_loss = train_one_epoch(
            model, train_loader, criterion, optimizer, device,
            mixup_alpha=mixup_alpha, num_classes=num_classes, ema=ema,
        )

        record: Dict = {"epoch": epoch, "train_loss": round(train_loss, 6), "lr": round(new_lr, 8)}

        if val_loader is not None:
            # 若启用 EMA，在 EMA 权重上评估
            if ema is not None:
                eval_model = copy.deepcopy(model)
                eval_model.load_state_dict(ema.shadow)
                eval_model.to(device)
            else:
                eval_model = model

            val_metrics = evaluate(eval_model, val_loader, criterion, device)
            val_loss = val_metrics["loss"]
            val_acc  = val_metrics["acc"]
            record.update({"val_loss": round(val_loss, 6), "val_acc": round(val_acc, 6)})

            if epoch % 10 == 0 or epoch == 1:
                print(f"[Epoch {epoch:4d}/{epochs}] lr={new_lr:.5f}  "
                      f"train_loss={train_loss:.4f}  val_loss={val_loss:.4f}  val_acc={val_acc:.4f}")

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                no_improve   = 0
                best_state_dict = ema.state_dict() if ema is not None else {
                    k: v.detach().cpu() for k, v in model.state_dict().items()
                }
                save_checkpoint(
                    os.path.join(exp_dir, "best_model.pth"),
                    best_state_dict,
                    {k: v for k, v in config.items() if not str(k).startswith("__")},
                    {"val_acc": val_acc, "epoch": epoch},
                )
            else:
                no_improve += 1

            if patience is not None and no_improve >= patience:
                print(f"[EarlyStopping] epoch {epoch}, best_val_acc={best_val_acc:.4f}")
                break
        else:
            # 全量训练，末轮保存
            if epoch % 10 == 0 or epoch == 1:
                print(f"[Epoch {epoch:4d}/{epochs}] lr={new_lr:.5f}  train_loss={train_loss:.4f}")
            if epoch == epochs:
                final_state_dict = ema.state_dict() if ema is not None else {
                    k: v.detach().cpu() for k, v in model.state_dict().items()
                }
                save_checkpoint(
                    os.path.join(exp_dir, "best_model.pth"),
                    final_state_dict,
                    {k: v for k, v in config.items() if not str(k).startswith("__")},
                    {"epoch": epoch},
                )

        tracker.add(record)

    tracker.save_json(os.path.join(exp_dir, "train_log.json"))
    if val_loader is None:
        print(f"[Done] full-data training complete  →  {exp_dir}/best_model.pth")
    else:
        print(f"[Done] best_val_acc={best_val_acc:.4f}  →  {exp_dir}/best_model.pth")


# ── 入口 ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="YAML 配置文件路径")
    args = parser.parse_args()

    config = load_config(args.config)
    train(config)


if __name__ == "__main__":
    main()
