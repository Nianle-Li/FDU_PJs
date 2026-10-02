"""Part2 面试推理接口：加载 checkpoint，对指定目录做批量推理，返回准确率。"""

import argparse
import os
from typing import List

import numpy as np
import torch
from torch.utils.data import DataLoader

from dataset import HandwritingDataset
from model import ResNetCNN
from utils import load_checkpoint, resolve_existing_path


class ClassificationModel:
    """封装 Part2 CNN，提供与 Part1 相同接口的批量推理。"""

    def __init__(self, checkpoint_path: str, invert: bool = True) -> None:
        ckpt   = load_checkpoint(checkpoint_path)
        config = ckpt.get("config", {})
        mcfg   = config.get("model", {})

        self._model = ResNetCNN(
            num_classes     = mcfg.get("num_classes", 12),
            downsample_mode = mcfg.get("downsample_mode", "maxpool"),
            use_se          = mcfg.get("use_se", False),
            dropout         = mcfg.get("dropout", 0.4),
        )
        self._model.load_state_dict(ckpt["state_dict"])
        self._model.eval()
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model.to(self._device)
        self._invert = invert

    @torch.no_grad()
    def _predict_batch(self, images: torch.Tensor) -> np.ndarray:
        """对一个 batch 做推理，返回预测类别 numpy 数组。"""
        images = images.to(self._device)
        return self._model(images).argmax(dim=1).cpu().numpy()

    def interview(self, eval_datafile_path: str) -> float:
        """批量推理并返回百分制准确率（与 Part1 接口保持一致）。"""
        ds     = HandwritingDataset(resolve_existing_path(eval_datafile_path),
                                    invert=self._invert)
        loader = DataLoader(ds, batch_size=128, shuffle=False, num_workers=0)
        correct, total = 0, 0
        for images, labels in loader:
            pred      = self._predict_batch(images)
            labels_np = labels.cpu().numpy()
            correct  += int((pred == labels_np).sum())
            total    += len(labels_np)
        return correct / total * 100.0

    def predict(self, images: np.ndarray) -> np.ndarray:
        """对 (N, 1, 28, 28) float32 numpy 数组做预测，返回 0-indexed 类别。"""
        tensor = torch.from_numpy(images).float()
        return self._predict_batch(tensor)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir",   required=True,  help="测试数据目录（与训练数据同格式）")
    parser.add_argument("--checkpoint", required=True,  help=".pth checkpoint 路径")
    parser.add_argument("--no_invert", action="store_true")
    args = parser.parse_args()

    model = ClassificationModel(
        resolve_existing_path(args.checkpoint),
        invert=not args.no_invert,
    )
    acc = model.interview(args.data_dir)
    print("测试准确率: %.2f%%" % acc)


if __name__ == "__main__":
    main()
