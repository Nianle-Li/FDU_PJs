"""数据加载、划分与轻量图像增强工具。"""

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
from PIL import Image

from utils import stratified_split


@dataclass
class ImageDataset:
    images: np.ndarray
    labels: np.ndarray


def load_bmp_as_array(path: str, invert: bool = True) -> np.ndarray:
    """读取单张 BMP 并返回归一化数组（float32, [0,1]）。

    若 `invert=True`，会执行 `255 - pixel`，使笔画为 1.0。
    返回形状 (H, W)，注意 MLP 输入需展平为 (N, 784)。
    """
    img = Image.open(path).convert("L")
    arr = np.array(img, dtype=np.float32)
    if invert:
        arr = 255.0 - arr
    arr = arr / 255.0
    return arr


def load_classification_data(data_dir: str, invert: bool = True) -> ImageDataset:
    import os as _os
    images = []
    labels = []
    for cls_name in sorted(list_dirs(data_dir), key=lambda x: int(x)):
        cls_idx = int(cls_name) - 1  # 文件夹名 1-12 转为 0-indexed 标签 0-11
        cls_dir = _os.path.join(data_dir, cls_name)
        for file_name in list_files(cls_dir):
            if not file_name.lower().endswith(".bmp"):
                continue
            path = _os.path.join(cls_dir, file_name)
            arr = load_bmp_as_array(path, invert=invert)
            images.append(arr)
            labels.append(cls_idx)
    x = np.stack(images, axis=0).astype(np.float32)
    y = np.array(labels, dtype=np.int64)
    return ImageDataset(images=x, labels=y)


def split_train_val(labels: np.ndarray, val_ratio: float, seed: int) -> Tuple[np.ndarray, np.ndarray]:
    """按类别分层划分训练集与验证集索引。"""
    return stratified_split(labels, val_ratio, seed)


def prepare_mlp_input(images: np.ndarray) -> np.ndarray:
    """将 28×28 图像展平为 784 维向量。"""
    return images.reshape(images.shape[0], -1)


def augment_mlp_batch(xb: np.ndarray, shift_range: int = 2, rng=None) -> np.ndarray:
    """对展平的 28×28 图像批次施加随机平移数据增强。

    每张图像在水平/垂直方向各随机平移 [-shift_range, +shift_range] 个像素，
    超出边界的部分用 0 填充（不做 wrap-around）。

    参数：
        xb: shape (N, 784) 的输入批次（已展平的 28×28 图像）
        shift_range: 最大平移像素数（每方向），默认 2
        rng: np.random.Generator，不传则自动创建（不推荐在训练循环中不传）
    返回：增强后的 (N, 784) float32 数组
    """
    if rng is None:
        rng = np.random.default_rng()
    n = xb.shape[0]
    imgs = xb.reshape(n, 28, 28)
    augmented = np.empty_like(imgs)
    for idx in range(n):
        dy = int(rng.integers(-shift_range, shift_range + 1))
        dx = int(rng.integers(-shift_range, shift_range + 1))
        shifted = np.roll(imgs[idx], dy, axis=0)
        shifted = np.roll(shifted, dx, axis=1)
        if dy > 0:
            shifted[:dy, :] = 0.0
        elif dy < 0:
            shifted[dy:, :] = 0.0
        if dx > 0:
            shifted[:, :dx] = 0.0
        elif dx < 0:
            shifted[:, dx:] = 0.0
        augmented[idx] = shifted
    return augmented.reshape(n, -1)


def generate_sin_data(n_samples: int, seed: int) -> Tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    x = rng.uniform(-np.pi, np.pi, size=(n_samples, 1)).astype(np.float32)
    y = np.sin(x).astype(np.float32)
    return x, y


def list_dirs(path: str) -> List[str]:
    import os
    return [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]


def list_files(path: str) -> List[str]:
    import os
    return [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]

