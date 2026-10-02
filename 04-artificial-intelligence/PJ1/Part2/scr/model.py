"""Part2 模型定义：残差块（ResBlock）与基线 CNN（ResNetCNN）。

支持选项（通过构造参数控制）：
  - downsample_mode: 'maxpool' | 'stride'  每个 Block 后的下采样方式
  - use_se: bool                           是否在每个 ResBlock 后加 SE 注意力
  - dropout: float                         分类头 Dropout 比例
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


# ── SE（Squeeze-and-Excitation）模块 ─────────────────────────────────────────

class SEBlock(nn.Module):
    """轻量通道注意力：全局池化 → 压缩 FC → 扩展 FC → Sigmoid 加权。"""

    def __init__(self, channels: int, reduction: int = 8) -> None:
        super().__init__()
        mid = max(channels // reduction, 4)
        self.fc = nn.Sequential(
            nn.Linear(channels, mid, bias=False),
            nn.ReLU(inplace=True),
            nn.Linear(mid, channels, bias=False),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (N, C, H, W)
        w = x.mean(dim=[2, 3])          # (N, C) 全局平均
        w = self.fc(w).unsqueeze(-1).unsqueeze(-1)   # (N, C, 1, 1)
        return x * w


# ── 残差块 ────────────────────────────────────────────────────────────────────

class ResBlock(nn.Module):
    """两层 3×3 卷积残差块，支持 1×1 projection skip 与可选 SE 注意力。

    Args:
        in_ch:   输入通道数
        out_ch:  输出通道数
        stride:  第一层卷积步幅（1 = 保持分辨率）
        use_se:  是否在块末尾加 SEBlock
    """

    def __init__(self, in_ch: int, out_ch: int, stride: int = 1, use_se: bool = False) -> None:
        super().__init__()
        self.conv1 = nn.Conv2d(in_ch, out_ch, 3, stride=stride, padding=1, bias=False)
        self.bn1   = nn.BatchNorm2d(out_ch)
        self.conv2 = nn.Conv2d(out_ch, out_ch, 3, stride=1, padding=1, bias=False)
        self.bn2   = nn.BatchNorm2d(out_ch)

        # 当通道变化或下采样时，需要 projection 对齐 skip
        self.projection: nn.Sequential | None = None
        if stride != 1 or in_ch != out_ch:
            self.projection = nn.Sequential(
                nn.Conv2d(in_ch, out_ch, 1, stride=stride, bias=False),
                nn.BatchNorm2d(out_ch),
            )

        self.se = SEBlock(out_ch) if use_se else None

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        skip = self.projection(x) if self.projection is not None else x

        out = F.relu(self.bn1(self.conv1(x)), inplace=True)
        out = self.bn2(self.conv2(out))

        if self.se is not None:
            out = self.se(out)

        return F.relu(out + skip, inplace=True)


# ── 基线 CNN ──────────────────────────────────────────────────────────────────

class ResNetCNN(nn.Module):
    """基线残差卷积网络，用于 28×28 单通道手写汉字 12 分类。

    网络结构（默认 maxpool 模式）：
        Stem:   Conv3×3(1→32) + BN + ReLU
        Block1: ResBlock(32→32)  → MaxPool2×2   → 32×14×14
        Block2: ResBlock(32→64)  → MaxPool2×2   → 64×7×7
        Block3: ResBlock(64→128)                → 128×7×7
        Head:   GlobalAvgPool → Dropout → FC(128→12)

    Args:
        num_classes:      输出类别数（默认 12）
        downsample_mode:  'maxpool'（在 Block 外做 MaxPool）或
                          'stride'（在 Block 内 stride=2 + projection）
        use_se:           ResBlock 内是否启用 SEBlock
        dropout:          分类头 Dropout 比例
    """

    def __init__(
        self,
        num_classes: int = 12,
        downsample_mode: str = "maxpool",
        use_se: bool = False,
        dropout: float = 0.4,
    ) -> None:
        super().__init__()
        assert downsample_mode in ("maxpool", "stride"), \
            "downsample_mode 需为 'maxpool' 或 'stride'"

        # Stem
        self.stem = nn.Sequential(
            nn.Conv2d(1, 32, 3, stride=1, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
        )

        if downsample_mode == "maxpool":
            # 下采样由块外的 MaxPool 完成，Block 内 stride=1
            self.block1 = ResBlock(32, 32, stride=1, use_se=use_se)
            self.pool1  = nn.MaxPool2d(2, 2)
            self.block2 = ResBlock(32, 64, stride=1, use_se=use_se)
            self.pool2  = nn.MaxPool2d(2, 2)
            self.block3 = ResBlock(64, 128, stride=1, use_se=use_se)
        else:  # stride 模式：下采样集成在 Block 首层 stride=2 + projection
            self.block1 = ResBlock(32, 32,  stride=1, use_se=use_se)
            self.pool1  = None
            self.block2 = ResBlock(32, 64,  stride=2, use_se=use_se)   # 14→7
            self.pool2  = None
            self.block3 = ResBlock(64, 128, stride=2, use_se=use_se)   # 7→4

        # Head
        self.gap     = nn.AdaptiveAvgPool2d(1)
        self.dropout = nn.Dropout(dropout)
        self.fc      = nn.Linear(128, num_classes)

        self._init_weights()

    def _init_weights(self) -> None:
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode="fan_out", nonlinearity="relu")
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (N, 1, 28, 28)
        out = self.stem(x)

        out = self.block1(out)
        if self.pool1 is not None:
            out = self.pool1(out)

        out = self.block2(out)
        if self.pool2 is not None:
            out = self.pool2(out)

        out = self.block3(out)

        out = self.gap(out)          # (N, 128, 1, 1)
        out = out.flatten(1)         # (N, 128)
        out = self.dropout(out)
        return self.fc(out)          # (N, num_classes) logits


def build_model(config: dict) -> ResNetCNN:
    """从 YAML config 的 model 节点构建 ResNetCNN。"""
    mcfg = config["model"]
    return ResNetCNN(
        num_classes     = mcfg.get("num_classes", 12),
        downsample_mode = mcfg.get("downsample_mode", "maxpool"),
        use_se          = mcfg.get("use_se", False),
        dropout         = mcfg.get("dropout", 0.4),
    )
