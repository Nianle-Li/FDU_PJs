"""Part3 训练入口。

训练脚本根据配置切换 Vanilla Transformer 或 BERT 编码器，并统一负责断点恢复、学习率调度和验证集评估。
"""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any

import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR, LinearLR, SequentialLR
import yaml
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import (
    load_data, build_vocab, save_vocab,
    get_dataloader_vanilla, get_dataloader_bert,
    write_predictions, char_expand_sentence, aggregate_char_to_word,
)
from src.model import build_model
from src.evaluate import compute_official_f1, compute_span_f1, print_metrics


def load_config(config_path: str) -> Dict[str, Any]:
    """读取 YAML 配置。"""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_args():
    parser = argparse.ArgumentParser(description="训练 Transformer+CRF NER 模型")
    parser.add_argument("--config", required=True, help="YAML 配置文件路径")
    # 仅保留常用覆盖项，避免为每次试验重复改 YAML。
    parser.add_argument("--training.epochs", type=int, default=None)
    parser.add_argument("--training.batch_size", type=int, default=None)
    parser.add_argument("--training.lr", type=float, default=None)
    return parser.parse_args()


def merge_args(cfg: Dict, args) -> Dict:
    """将命令行参数合并到配置字典（命令行优先）。"""
    if args.__dict__.get("training.epochs"):
        cfg.setdefault("training", {})["epochs"] = args.__dict__["training.epochs"]
    if args.__dict__.get("training.batch_size"):
        cfg.setdefault("training", {})["batch_size"] = args.__dict__["training.batch_size"]
    if args.__dict__.get("training.lr"):
        cfg.setdefault("training", {})["lr"] = args.__dict__["training.lr"]
    return cfg


def build_scheduler(optimizer, cfg: Dict, total_steps: int):
    """
    根据配置构建学习率调度器。

    支持三种策略：
      - cosine（默认）: CosineAnnealingLR，可选 warmup 预热阶段（LinearLR → CosineAnnealingLR）
      - step           : StepLR，每 total_steps//3 步降一次 lr（gamma=0.3）
      - 其他/None      : 不使用调度器，返回 None

    Args:
        optimizer:    PyTorch 优化器实例
        cfg:          配置字典，从 cfg["training"]["lr_scheduler"] 读取策略
        total_steps:  总训练步数（epochs × steps_per_epoch），用于 CosineAnnealingLR 周期

    Returns:
        scheduler 实例，或 None
    """
    scheduler_type = cfg.get("training", {}).get("lr_scheduler", "cosine")
    warmup_steps = cfg.get("training", {}).get("warmup_steps", 0)

    if scheduler_type == "cosine":
        if warmup_steps > 0:
            warmup = LinearLR(optimizer, start_factor=0.01, end_factor=1.0, total_iters=warmup_steps)
            cosine = CosineAnnealingLR(optimizer, T_max=max(total_steps - warmup_steps, 1))
            return SequentialLR(optimizer, schedulers=[warmup, cosine], milestones=[warmup_steps])
        else:
            return CosineAnnealingLR(optimizer, T_max=total_steps)
    elif scheduler_type == "step":
        from torch.optim.lr_scheduler import StepLR
        return StepLR(optimizer, step_size=total_steps // 3, gamma=0.3)
    else:
        return None


def build_optimizer_bert(model, cfg: Dict):
    """
    为 BERT+CRF 模型构建分组优化器（differential learning rate）。

    BERT 主干使用小学习率（通常 2e-5），避免破坏预训练权重；
    分类头（Linear fc）和 CRF 层使用大学习率（head_lr），加速收敛。

    Args:
        model: BERTTransformerNER 实例
        cfg:   配置字典，从 cfg["training"] 读取 lr / head_lr / weight_decay

    Returns:
        AdamW 优化器，内含两组参数（bert_params / head_params）
    """
    lr = cfg["training"].get("lr", 2e-5)
    head_lr = cfg["training"].get("head_lr", lr * 10)
    weight_decay = cfg["training"].get("weight_decay", 0.01)

    bert_params = list(model.bert.parameters())
    head_params = list(model.fc.parameters()) + list(model.crf.parameters())

    return AdamW([
        {"params": bert_params, "lr": lr},
        {"params": head_params, "lr": head_lr},
    ], weight_decay=weight_decay)


def build_optimizer_vanilla(model, cfg: Dict):
    """
    为 Vanilla Transformer+CRF 构建优化器（所有参数统一学习率）。

    Args:
        model: VanillaTransformerNER 实例
        cfg:   配置字典，从 cfg["training"] 读取 lr / weight_decay

    Returns:
        AdamW 优化器
    """
    weight_decay = cfg["training"].get("weight_decay", 0.01)
    lr = cfg["training"].get("lr", 1e-3)
    return AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)


def save_checkpoint(output_dir: Path, epoch: int, model, optimizer, scheduler, best_f1: float):
    """
    保存训练状态到 checkpoint.pt，用于断点恢复。

    保存内容：当前 epoch 编号、模型权重、优化器状态、调度器状态、当前最优 F1。
    下次启动时若检测到 checkpoint.pt，将自动从该 epoch 后继续训练。

    Args:
        output_dir: 输出目录（Path 对象）
        epoch:      当前 epoch 编号
        model:      模型实例
        optimizer:  优化器实例
        scheduler:  学习率调度器实例（可为 None）
        best_f1:    当前记录的最优验证集 F1
    """
    state = {
        "epoch": epoch,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "scheduler_state_dict": scheduler.state_dict() if scheduler is not None else None,
        "best_f1": best_f1,
    }
    torch.save(state, output_dir / "checkpoint.pt")


def load_checkpoint(output_dir: Path, model, optimizer, scheduler):
    """
    若存在 checkpoint.pt，则恢复模型权重和训练状态。

    Args:
        output_dir: 输出目录
        model:      模型实例（原地修改权重）
        optimizer:  优化器实例（原地恢复状态）
        scheduler:  调度器实例（原地恢复状态，可为 None）

    Returns:
        (start_epoch, best_f1): 下一个 epoch 编号和历史最优 F1
        若无 checkpoint，返回 (1, 0.0)
    """
    ckpt_path = output_dir / "checkpoint.pt"
    if not ckpt_path.exists():
        return 1, 0.0
    state = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    model.load_state_dict(state["model_state_dict"])
    optimizer.load_state_dict(state["optimizer_state_dict"])
    if scheduler is not None and state.get("scheduler_state_dict") is not None:
        scheduler.load_state_dict(state["scheduler_state_dict"])
    start_epoch = state["epoch"] + 1
    best_f1 = state.get("best_f1", 0.0)
    print(f"[checkpoint] 已恢复 {ckpt_path}，从 epoch {start_epoch} 继续，best_f1={best_f1:.4f}")
    return start_epoch, best_f1


def train_vanilla(cfg: Dict) -> None:
    """
    训练 Vanilla Transformer（从头训练）+ CRF 的完整流程。

    流程：数据加载 → 词表构建 → DataLoader → 模型构建 → 训练循环
       → 验证集评估 → 最优模型保存 → Early Stopping

    关键设计：
      - safe_tags: 将 pad 位置的 tag_id 替换为 0，避免 CRF 用到无效标签下标
      - mask:      BoolTensor 指示有效位置，CRF 计算时跳过 pad
      - char_level: 中文可选字符级输入，将词级句子展开为字符级后预测，
                   推理结果再聚合回词级
      - Early Stopping: 连续 patience 个 epoch 无提升则终止，防止过拟合

    Args:
        cfg: 配置字典，包含 data_dir / output_dir / model / training 等字段
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[train] 设备: {device}")

    data_dir = cfg["data_dir"]
    output_dir = Path(cfg["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    train_sents = load_data(os.path.join(data_dir, "train.txt"))
    val_sents = load_data(os.path.join(data_dir, "validation.txt"))
    print(f"[data] 训练集: {len(train_sents)} 句，验证集: {len(val_sents)} 句")

    tag_file = os.path.join(data_dir, "tag.txt")
    min_freq = cfg.get("model", {}).get("min_freq", 1)
    char_level = cfg.get("model", {}).get("char_level", False)

    # char-level 模式把词级标注展开为字符级，便于中文实验直接建模字序列。
    if char_level:
        train_sents_model = [char_expand_sentence(s) for s in train_sents]
        val_sents_model = [char_expand_sentence(s) for s in val_sents]
        print(f"[data] char-level 模式：训练字符序列数={len(train_sents_model)}")
    else:
        train_sents_model = train_sents
        val_sents_model = val_sents

    token2id, tag2id = build_vocab(
        train_sents_model,
        min_freq=min_freq,
        tag_file=tag_file if os.path.exists(tag_file) else None,
    )
    save_vocab(token2id, tag2id, str(output_dir))
    id2tag = {v: k for k, v in tag2id.items()}
    print(f"[data] 词表大小: {len(token2id)}，标签数: {len(tag2id)}（min_freq={min_freq}，char_level={char_level}）")

    batch_size = cfg["training"].get("batch_size", 64)
    train_loader = get_dataloader_vanilla(train_sents_model, token2id, tag2id, batch_size, shuffle=True)
    val_loader = get_dataloader_vanilla(val_sents_model, token2id, tag2id, batch_size, shuffle=False)

    model = build_model(cfg, vocab_size=len(token2id), num_tags=len(tag2id), tag2id=tag2id)
    model.to(device)
    print(f"[model] 参数量: {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")

    optimizer = build_optimizer_vanilla(model, cfg)
    epochs = cfg["training"].get("epochs", 80)
    total_steps = len(train_loader) * epochs
    scheduler = build_scheduler(optimizer, cfg, total_steps)
    clip_grad = cfg["training"].get("clip_grad", 1.0)
    patience = cfg["training"].get("early_stopping_patience", 10)

    patience_counter = 0
    start_epoch, best_f1 = load_checkpoint(output_dir, model, optimizer, scheduler)

    for epoch in range(start_epoch, epochs + 1):
        model.train()
        total_loss = 0.0
        for input_ids, tag_ids, mask in tqdm(train_loader, desc=f"Epoch {epoch}", leave=False):
            input_ids, tag_ids, mask = input_ids.to(device), tag_ids.to(device), mask.to(device)
            safe_tags = tag_ids.clone()
            safe_tags[~mask] = 0

            optimizer.zero_grad()
            loss = model(input_ids, safe_tags, mask)
            loss.backward()
            if clip_grad > 0:
                nn.utils.clip_grad_norm_(model.parameters(), clip_grad)
            optimizer.step()
            if scheduler is not None:
                scheduler.step()
            total_loss += loss.item()

        avg_loss = total_loss / len(train_loader)

        val_preds_raw, val_gold = _predict_vanilla(model, val_loader, id2tag, device)
        if char_level:
            val_preds = aggregate_char_to_word(val_sents, val_preds_raw)
        else:
            val_preds = val_preds_raw
        metrics = compute_official_f1(val_sents, val_preds)
        span_metrics = compute_span_f1(val_sents, val_preds)
        print(
            f"Epoch {epoch:3d} | loss={avg_loss:.4f} | "
            f"official_P={metrics['precision']:.4f} official_R={metrics['recall']:.4f} "
            f"official_F1={metrics['f1']:.4f} span_F1={span_metrics['f1']:.4f}"
        )

        if metrics["f1"] > best_f1:
            best_f1 = metrics["f1"]
            patience_counter = 0
            ckpt_path = output_dir / "best_model.pt"
            torch.save(model.state_dict(), ckpt_path)
            print(f"  → 新最优 F1={best_f1:.4f}，已保存 {ckpt_path}")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"Early stopping at epoch {epoch}（连续 {patience} 个 epoch 无改善）")
                break

        save_checkpoint(output_dir, epoch, model, optimizer, scheduler, best_f1)

    # 最终评估
    model.load_state_dict(torch.load(output_dir / "best_model.pt", map_location=device, weights_only=True))
    val_preds_raw, _ = _predict_vanilla(model, val_loader, id2tag, device)
    if char_level:
        val_preds = aggregate_char_to_word(val_sents, val_preds_raw)
    else:
        val_preds = val_preds_raw
    metrics = compute_official_f1(val_sents, val_preds)
    span_metrics = compute_span_f1(val_sents, val_preds)
    print(f"\n[最终验证集] ", end="")
    print_metrics(metrics)
    print_metrics(span_metrics, prefix="span")

    write_predictions(str(output_dir / "val_pred.txt"), [[t for t, _ in s] for s in val_sents], val_preds)
    with open(output_dir / "metrics.txt", "w") as f:
        f.write(f"Official Precision: {metrics['precision']:.4f}\n")
        f.write(f"Official Recall:    {metrics['recall']:.4f}\n")
        f.write(f"Official F1:        {metrics['f1']:.4f}\n")
        f.write(f"Span Precision:     {span_metrics['precision']:.4f}\n")
        f.write(f"Span Recall:        {span_metrics['recall']:.4f}\n")
        f.write(f"Span F1:            {span_metrics['f1']:.4f}\n")


def _predict_vanilla(model, loader, id2tag, device):
    """
    在 DataLoader 上运行 Vanilla Transformer+CRF 推理，返回预测标签序列。

    Args:
        model:   VanillaTransformerNER 实例（eval 模式）
        loader:  DataLoader（collate_fn_vanilla 格式）
        id2tag:  id → tag 名称的映射字典
        device:  推理设备（CPU / GPU）

    Returns:
        (all_preds, all_gold): 预测列表和金标列表（gold 此处为空列表，兼容历史接口）
    """
    model.eval()
    all_preds, all_gold = [], []
    with torch.no_grad():
        for input_ids, tag_ids, mask in loader:
            input_ids, mask = input_ids.to(device), mask.to(device)
            paths = model.decode(input_ids, mask)     # Viterbi 解码，返回 List[List[int]]
            for path in paths:
                all_preds.append([id2tag[t] for t in path])  # 将 id 转回 tag 名称
    return all_preds, all_gold


def train_bert(cfg: Dict) -> None:
    """
    训练 BERT + CRF 的完整流程。

    与 train_vanilla 的核心区别：
      - 使用 AutoTokenizer 对每个词进行 subword 切分（如 BERT-wwm / RoBERTa）
      - 每个词只取第一个 subword 的表示参与 CRF，其余 subword 的 label_id=-100
      - BERTTransformerNER._pack_valid_tokens 在进入 CRF 前先移除 [CLS]/[SEP]/续接子词
      - BERT 主干使用小学习率（2e-5），分类头和 CRF 使用大学习率（head_lr）
      - Early Stopping patience 通常设置较小（默认 5），因 BERT 收敛更快

    Args:
        cfg: 配置字典，需包含 model.bert_model（Hugging Face 模型名或本地路径）
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[train] 设备: {device}")

    data_dir = cfg["data_dir"]
    output_dir = Path(cfg["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    from transformers import AutoTokenizer
    bert_model_name = cfg["model"]["bert_model"]
    tokenizer = AutoTokenizer.from_pretrained(bert_model_name)

    train_sents = load_data(os.path.join(data_dir, "train.txt"))
    val_sents = load_data(os.path.join(data_dir, "validation.txt"))
    print(f"[data] 训练集: {len(train_sents)} 句，验证集: {len(val_sents)} 句")

    # BERT 自带子词词表，这里只保留标签映射。
    from src.data import build_vocab
    tag_file = os.path.join(data_dir, "tag.txt")
    _, tag2id = build_vocab(train_sents, tag_file=tag_file if os.path.exists(tag_file) else None)
    import json
    os.makedirs(str(output_dir), exist_ok=True)
    with open(output_dir / "tag2id.json", "w", encoding="utf-8") as f:
        json.dump(tag2id, f, ensure_ascii=False, indent=2)
    id2tag = {v: k for k, v in tag2id.items()}
    print(f"[data] 标签数: {len(tag2id)}")

    batch_size = cfg["training"].get("batch_size", 32)
    max_length = cfg["model"].get("max_len", 512)
    train_loader = get_dataloader_bert(train_sents, tokenizer, tag2id, batch_size, max_length, shuffle=True)
    val_loader = get_dataloader_bert(val_sents, tokenizer, tag2id, batch_size, max_length, shuffle=False)

    model = build_model(cfg, vocab_size=0, num_tags=len(tag2id), tag2id=tag2id)
    model.to(device)
    print(f"[model] 参数量: {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")

    optimizer = build_optimizer_bert(model, cfg)
    epochs = cfg["training"].get("epochs", 30)
    total_steps = len(train_loader) * epochs
    scheduler = build_scheduler(optimizer, cfg, total_steps)
    clip_grad = cfg["training"].get("clip_grad", 1.0)
    patience = cfg["training"].get("early_stopping_patience", 5)

    patience_counter = 0
    start_epoch, best_f1 = load_checkpoint(output_dir, model, optimizer, scheduler)

    for epoch in range(start_epoch, epochs + 1):
        model.train()
        total_loss = 0.0
        for batch in tqdm(train_loader, desc=f"Epoch {epoch}", leave=False):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            token_type_ids = batch["token_type_ids"].to(device)
            label_ids = batch["label_ids"].to(device)

            optimizer.zero_grad()
            loss = model(input_ids, attention_mask, token_type_ids, label_ids)
            loss.backward()
            if clip_grad > 0:
                nn.utils.clip_grad_norm_(model.parameters(), clip_grad)
            optimizer.step()
            if scheduler is not None:
                scheduler.step()
            total_loss += loss.item()

        avg_loss = total_loss / len(train_loader)

        val_preds = _predict_bert(model, val_loader, id2tag, device)
        metrics = compute_official_f1(val_sents, val_preds)
        span_metrics = compute_span_f1(val_sents, val_preds)
        print(
            f"Epoch {epoch:3d} | loss={avg_loss:.4f} | "
            f"official_P={metrics['precision']:.4f} official_R={metrics['recall']:.4f} "
            f"official_F1={metrics['f1']:.4f} span_F1={span_metrics['f1']:.4f}"
        )

        if metrics["f1"] > best_f1:
            best_f1 = metrics["f1"]
            patience_counter = 0
            ckpt_path = output_dir / "best_model.pt"
            torch.save(model.state_dict(), ckpt_path)
            print(f"  → 新最优 F1={best_f1:.4f}，已保存 {ckpt_path}")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"Early stopping at epoch {epoch}（连续 {patience} 个 epoch 无改善）")
                break

        save_checkpoint(output_dir, epoch, model, optimizer, scheduler, best_f1)

    model.load_state_dict(torch.load(output_dir / "best_model.pt", map_location=device, weights_only=True))
    val_preds = _predict_bert(model, val_loader, id2tag, device)
    metrics = compute_official_f1(val_sents, val_preds)
    span_metrics = compute_span_f1(val_sents, val_preds)
    print(f"\n[最终验证集] ", end="")
    print_metrics(metrics)
    print_metrics(span_metrics, prefix="span")

    write_predictions(str(output_dir / "val_pred.txt"), [[t for t, _ in s] for s in val_sents], val_preds)
    with open(output_dir / "metrics.txt", "w") as f:
        f.write(f"Official Precision: {metrics['precision']:.4f}\n")
        f.write(f"Official Recall:    {metrics['recall']:.4f}\n")
        f.write(f"Official F1:        {metrics['f1']:.4f}\n")
        f.write(f"Span Precision:     {span_metrics['precision']:.4f}\n")
        f.write(f"Span Recall:        {span_metrics['recall']:.4f}\n")
        f.write(f"Span F1:            {span_metrics['f1']:.4f}\n")


def _predict_bert(model, loader, id2tag, device):
    model.eval()
    all_preds = []
    with torch.no_grad():
        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            token_type_ids = batch["token_type_ids"].to(device)
            label_ids = batch["label_ids"].to(device)
            paths = model.decode(input_ids, attention_mask, token_type_ids, label_ids)
            for path in paths:
                all_preds.append([id2tag[t] for t in path])
    return all_preds


def main():
    args = parse_args()
    cfg = load_config(args.config)
    cfg = merge_args(cfg, args)

    encoder = cfg.get("model", {}).get("encoder", "vanilla")
    print(f"[config] 编码器模式: {encoder}，语言: {cfg.get('lang', '?')}")

    if encoder == "bert":
        train_bert(cfg)
    else:
        train_vanilla(cfg)


if __name__ == "__main__":
    main()
