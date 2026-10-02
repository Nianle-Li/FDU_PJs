"""Part2 数据集：BMP 加载、预处理、增强、分层划分，与 Part1 保持一致风格。"""

import os
from typing import List, Optional, Tuple

import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset

from utils import stratified_split


# ── 单张图像读取 ───────────────────────────────────────────────────────────────

def load_bmp_as_tensor(path: str, invert: bool = True) -> torch.Tensor:
    """读取单张 BMP → 归一化 float32 张量 (1, H, W)。

    invert=True 时反相，使笔画像素值接近 1.0（与 Part1 保持一致）。
    """
    img = Image.open(path).convert("L")
    arr = np.array(img, dtype=np.float32) / 255.0
    if invert:
        arr = 1.0 - arr
    return torch.from_numpy(arr).unsqueeze(0)  # (1, 28, 28)


# ── 数据集类 ──────────────────────────────────────────────────────────────────

class HandwritingDataset(Dataset):
    """28×28 单通道手写汉字数据集。

    Args:
        data_dir:     根目录，子目录名 1-12 对应类别标签 0-11
        indices:      若指定，只使用这部分样本（用于划分 train/val）
        invert:       是否对像素进行反相（使笔画高亮）
        transform:    可选的训练期增强（callable，对 Tensor (1,H,W) 操作）
    """

    def __init__(
        self,
        data_dir: str,
        indices: Optional[np.ndarray] = None,
        invert: bool = True,
        transform=None,
    ) -> None:
        self.transform = transform
        self.samples: List[Tuple[str, int]] = []

        for cls_name in sorted(os.listdir(data_dir), key=lambda x: int(x)
                               if x.isdigit() else float("inf")):
            cls_dir = os.path.join(data_dir, cls_name)
            if not os.path.isdir(cls_dir) or not cls_name.isdigit():
                continue
            label = int(cls_name) - 1  # 文件夹 1-12 → 标签 0-11
            for fname in os.listdir(cls_dir):
                if fname.lower().endswith(".bmp"):
                    self.samples.append((os.path.join(cls_dir, fname), label))

        # 预先读取全部图像（小数据集，可以放进内存）
        self.images = []
        self.labels = []
        for path, label in self.samples:
            self.images.append(load_bmp_as_tensor(path, invert=invert))
            self.labels.append(label)
        self.images = torch.stack(self.images)   # (N, 1, 28, 28)
        self.labels = np.array(self.labels, dtype=np.int64)

        if indices is not None:
            self.images = self.images[indices]
            self.labels = self.labels[indices]

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int):
        img = self.images[idx]
        if self.transform is not None:
            img = self.transform(img)
        return img, int(self.labels[idx])


# ── 增强操作 ──────────────────────────────────────────────────────────────────

class RandomShift:
    """随机平移（与 Part1 augment_mlp_batch 逻辑对应的 Tensor 版本）。"""

    def __init__(self, shift_range: int = 2) -> None:
        self.shift_range = shift_range

    def __call__(self, img: torch.Tensor) -> torch.Tensor:
        # img: (1, H, W)
        dy = int(torch.randint(-self.shift_range, self.shift_range + 1, (1,)).item())
        dx = int(torch.randint(-self.shift_range, self.shift_range + 1, (1,)).item())
        img = torch.roll(img, shifts=dy, dims=1)
        img = torch.roll(img, shifts=dx, dims=2)
        if dy > 0:
            img[:, :dy, :] = 0.0
        elif dy < 0:
            img[:, dy:, :] = 0.0
        if dx > 0:
            img[:, :, :dx] = 0.0
        elif dx < 0:
            img[:, :, dx:] = 0.0
        return img


class RandomErasing:
    """随机遮挡数据增强（对 Tensor (C, H, W) 操作）。"""

    def __init__(self, p: float = 0.3, scale: Tuple[float, float] = (0.02, 0.15)) -> None:
        self.p = p
        self.scale = scale

    def __call__(self, img: torch.Tensor) -> torch.Tensor:
        if torch.rand(1).item() > self.p:
            return img
        _, H, W = img.shape
        area = H * W
        target_area = torch.empty(1).uniform_(*self.scale).item() * area
        h = int(round(target_area ** 0.5))
        w = h
        h, w = min(h, H), min(w, W)
        top  = int(torch.randint(0, H - h + 1, (1,)).item())
        left = int(torch.randint(0, W - w + 1, (1,)).item())
        img = img.clone()
        img[:, top:top+h, left:left+w] = 0.0
        return img


class Compose:
    def __init__(self, transforms: list) -> None:
        self.transforms = transforms

    def __call__(self, img):
        for t in self.transforms:
            img = t(img)
        return img


# ── Mixup ─────────────────────────────────────────────────────────────────────

def mixup_batch(
    images: torch.Tensor,
    labels: torch.Tensor,
    alpha: float = 0.2,
    num_classes: int = 12,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """对一个 batch 做 Mixup，返回混合图像与 soft label。"""
    lam = float(np.random.beta(alpha, alpha)) if alpha > 0 else 1.0
    idx = torch.randperm(images.size(0))
    mixed_images = lam * images + (1.0 - lam) * images[idx]
    # 构造 soft one-hot label
    n = images.size(0)
    y_a = torch.zeros(n, num_classes).scatter_(1, labels.view(-1, 1), 1.0)
    y_b = torch.zeros(n, num_classes).scatter_(1, labels[idx].view(-1, 1), 1.0)
    soft_labels = lam * y_a + (1.0 - lam) * y_b
    return mixed_images, soft_labels


# ── 构建增强流水线 ─────────────────────────────────────────────────────────────

def build_train_transform(aug_cfg: dict):
    ops = []
    if aug_cfg.get("shift", 0) > 0:
        ops.append(RandomShift(shift_range=aug_cfg["shift"]))
    if aug_cfg.get("random_erasing", False):
        re_p     = aug_cfg.get("random_erasing_p", 0.3)
        re_scale = tuple(aug_cfg.get("random_erasing_scale", [0.02, 0.15]))
        ops.append(RandomErasing(p=re_p, scale=re_scale))
    if aug_cfg.get("affine", False):
        try:
            import torchvision.transforms.functional as TF
            import torchvision.transforms as T
            ops.append(T.RandomAffine(
                degrees  = aug_cfg.get("affine_degrees", 8),
                translate= tuple(aug_cfg.get("affine_translate", [0.1, 0.1])),
                scale    = tuple(aug_cfg.get("affine_scale", [0.9, 1.1])),
            ))
        except ImportError:
            pass
    return Compose(ops) if ops else None
