"""Part2 评估入口：加载 checkpoint，在指定数据目录上输出分类指标。"""

import argparse

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from dataset import HandwritingDataset
from model import ResNetCNN
from utils import (
    confusion_matrix, precision_recall_f1,
    resolve_existing_path, load_checkpoint,
)


def eval_classification(checkpoint_path: str, data_dir: str, invert: bool = True) -> None:
    ckpt   = load_checkpoint(checkpoint_path)
    config = ckpt.get("config", {})
    mcfg   = config.get("model", {})

    model = ResNetCNN(
        num_classes     = mcfg.get("num_classes", 12),
        downsample_mode = mcfg.get("downsample_mode", "maxpool"),
        use_se          = mcfg.get("use_se", False),
        dropout         = mcfg.get("dropout", 0.4),
    )
    model.load_state_dict(ckpt["state_dict"])
    model.eval()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    ds     = HandwritingDataset(resolve_existing_path(data_dir), invert=invert)
    loader = DataLoader(ds, batch_size=128, shuffle=False, num_workers=0)

    criterion = nn.CrossEntropyLoss()
    total_loss, correct, total = 0.0, 0, 0
    all_pred, all_true = [], []

    with torch.no_grad():
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            logits = model(images)
            loss   = criterion(logits, labels)
            total_loss += loss.item() * images.size(0)
            pred = logits.argmax(dim=1)
            correct += (pred == labels).sum().item()
            total   += images.size(0)
            all_pred.append(pred.cpu().numpy())
            all_true.append(labels.cpu().numpy())

    all_pred = np.concatenate(all_pred)
    all_true = np.concatenate(all_true)
    acc      = correct / total
    avg_loss = total_loss / total
    num_cls  = mcfg.get("num_classes", 12)

    cm  = confusion_matrix(all_pred, all_true, num_cls)
    prf = precision_recall_f1(cm)

    print(f"Loss:     {avg_loss:.6f}")
    print(f"Accuracy: {acc:.4f}  ({correct}/{total})")
    print("Confusion matrix (rows=true, cols=pred):")
    print(cm)
    print("Per-class precision:", np.round(prf["precision"], 4))
    print("Per-class recall:   ", np.round(prf["recall"],    4))
    print("Per-class F1:       ", np.round(prf["f1"],        4))

    # 列出误分类样本统计
    errors = [(int(t), int(p)) for t, p in zip(all_true, all_pred) if t != p]
    if errors:
        from collections import Counter
        print(f"\n误分类共 {len(errors)} 个：")
        for (t, p), cnt in Counter(errors).most_common(10):
            print(f"  类别 {t+1} 被误判为 {p+1} : {cnt} 次")
    else:
        print("\n零误分类！")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True, help=".pth checkpoint 路径")
    parser.add_argument("--data_dir",   required=True, help="测试/验证数据目录")
    parser.add_argument("--no_invert",  action="store_true", help="不反相（默认反相）")
    args = parser.parse_args()

    eval_classification(
        resolve_existing_path(args.checkpoint),
        args.data_dir,
        invert=not args.no_invert,
    )


if __name__ == "__main__":
    main()
