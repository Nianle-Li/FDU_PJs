"""分类任务面试推理入口。"""

import argparse

import numpy as np

from data import load_classification_data, prepare_mlp_input
from model import MLP
from utils import load_checkpoint, resolve_existing_path


class ClassificationModel:
    """封装分类模型并提供批量推理接口。"""

    def __init__(self, checkpoint_path: str, invert: bool = True) -> None:
        ckpt = load_checkpoint(checkpoint_path)
        config = ckpt.get("config", {})
        model_cfg = config.get("model")
        if not model_cfg:
            raise ValueError("Checkpoint missing model config")
        self._model = MLP(model_cfg["layers"], model_cfg["activations"], model_cfg["output_activation"],
                          dropout_rates=model_cfg.get("dropout_rates", None))
        self._model.load_state(ckpt["state"])
        self._invert = invert

    def interview(self, eval_datafile_path: str) -> float:
        """批量推理并返回百分制准确率。"""
        dataset = load_classification_data(resolve_existing_path(eval_datafile_path), invert=self._invert)
        x = prepare_mlp_input(dataset.images)
        y = dataset.labels
        logits, _ = self._model.forward(x)
        pred = np.argmax(logits, axis=1)
        acc = float((pred == y).mean()) * 100.0
        return acc

    def predict(self, images: np.ndarray) -> np.ndarray:
        """对输入图像做预测，返回 0-indexed 类别索引。"""
        if images.ndim == 3:
            images = images.reshape(images.shape[0], -1)
        logits, _ = self._model.forward(images)
        return np.argmax(logits, axis=1)


def interview(data_dir: str, checkpoint_path: str, invert: bool = True) -> float:
    """函数式推理接口，返回 0 到 1 之间的准确率。"""
    ckpt = load_checkpoint(resolve_existing_path(checkpoint_path))
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
    pred = np.argmax(logits, axis=1)
    acc = float((pred == y).mean())
    return acc


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--invert", action="store_true", default=True)
    args = parser.parse_args()

    model = ClassificationModel(resolve_existing_path(args.checkpoint), invert=args.invert)
    test_accuracy = model.interview(args.data_dir)
    print(f"测试准确率: {test_accuracy:.2f}%")


if __name__ == "__main__":
    main()

