"""Part3 模型定义。

统一封装从头训练的 Transformer+CRF 与 BERT+CRF，两种编码器共享 CRF 解码接口，方便训练脚本按配置切换。
"""

import math
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn

from .crf import CRF


class PositionalEncoding(nn.Module):
    """
    固定正弦/余弦位置编码（Sinusoidal Positional Encoding）。

    Transformer 本身对位置没有感知能力，位置编码为每个位置添加一个固定向量，
    使模型能区分不同位置的 token。

    公式：
      PE(pos, 2i)   = sin(pos / 10000^(2i/d_model))
      PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))

    Args:
        d_model: 嵌入维度（必须与 Transformer 的 d_model 一致）
        max_len: 支持的最大序列长度（默认 512）
        dropout: Dropout 比例（作用于 embedding + positional encoding 之和）
    """

    def __init__(self, d_model: int, max_len: int = 512, dropout: float = 0.1) -> None:
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2, dtype=torch.float) * (-math.log(10000.0) / d_model)
        )
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        self.register_buffer("pe", pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (B, T, d_model)"""
        x = x + self.pe[:, : x.size(1), :]  # type: ignore
        return self.dropout(x)


class VanillaTransformerNER(nn.Module):
    """
    从头训练的 Transformer Encoder + 手写 CRF。

    Args:
        vocab_size:      词表大小
        num_tags:        标签数量
        embed_dim:       词嵌入维度（默认 256）
        num_heads:       Multi-Head Attention 头数（默认 8）
        num_layers:      Transformer Encoder 层数（默认 4）
        ff_dim:          前馈网络维度（默认 1024）
        dropout:         Dropout 比例（默认 0.1）
        max_len:         最大序列长度（默认 512）
        pad_id:          PAD token id（默认 0）
        tag2id:          tag 名称到 id 映射，用于 CRF 约束初始化
        use_constraint:  是否启用 CRF 非法转移约束
    """

    def __init__(
        self,
        vocab_size: int,
        num_tags: int,
        embed_dim: int = 256,
        num_heads: int = 8,
        num_layers: int = 4,
        ff_dim: int = 1024,
        dropout: float = 0.1,
        max_len: int = 512,
        pad_id: int = 0,
        tag2id: Optional[Dict[str, int]] = None,
        use_constraint: bool = True,
    ) -> None:
        super().__init__()
        self.pad_id = pad_id

        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=pad_id)
        self.pos_encoding = PositionalEncoding(embed_dim, max_len, dropout)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=num_heads,
            dim_feedforward=ff_dim,
            dropout=dropout,
            batch_first=True,
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        self.layer_norm = nn.LayerNorm(embed_dim)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(embed_dim, num_tags)

        self.crf = CRF(num_tags, tag2id=tag2id, use_constraint=use_constraint)

    def _encode(
        self,
        input_ids: torch.Tensor,
        mask: torch.Tensor,
    ) -> torch.Tensor:
        """
        Args:
            input_ids: (B, T)
            mask:      (B, T) BoolTensor，True 为有效位置

        Returns:
            emissions: (B, T, num_tags)
        """
        # Transformer 的 padding mask 语义与数据集 mask 相反，这里显式翻转一次。
        padding_mask = ~mask  # (B, T)，True 表示 pad 位置

        x = self.embedding(input_ids)
        x = self.pos_encoding(x)
        x = self.transformer_encoder(x, src_key_padding_mask=padding_mask)
        x = self.layer_norm(x)
        x = self.dropout(x)
        emissions = self.fc(x)
        return emissions

    def forward(
        self,
        input_ids: torch.Tensor,
        tags: torch.Tensor,
        mask: torch.Tensor,
    ) -> torch.Tensor:
        """训练时调用，返回 CRF NLL loss。"""
        emissions = self._encode(input_ids, mask)
        loss = self.crf(emissions, tags, mask)
        return loss

    def decode(
        self,
        input_ids: torch.Tensor,
        mask: torch.Tensor,
    ) -> List[List[int]]:
        """推理时调用，返回 Viterbi 最优路径。"""
        emissions = self._encode(input_ids, mask)
        return self.crf.decode(emissions, mask)


class BERTTransformerNER(nn.Module):
    """
    BERT 预训练编码器 + 手写 CRF。

    Args:
        bert_model_name: Hugging Face 模型名称或本地路径
        num_tags:        标签数量
        dropout:         Dropout 比例（默认 0.1）
        tag2id:          tag 名称到 id 映射
        use_constraint:  是否启用 CRF 非法转移约束
    """

    def __init__(
        self,
        bert_model_name: str,
        num_tags: int,
        dropout: float = 0.1,
        tag2id: Optional[Dict[str, int]] = None,
        use_constraint: bool = True,
    ) -> None:
        super().__init__()
        from transformers import AutoModel
        self.bert = AutoModel.from_pretrained(bert_model_name)
        hidden_size = self.bert.config.hidden_size

        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_size, num_tags)
        self.crf = CRF(num_tags, tag2id=tag2id, use_constraint=use_constraint)

    def _pack_valid_tokens(
        self,
        emissions: torch.Tensor,
        label_ids: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        从 BERT 的 subword 序列中提取有效 token（原始词的首子词）的表示。

        BERT tokenizer 会将一个词切分为多个 subword（如 "playing" → "play", "##ing"）。
        NER 标签只对原始词有定义，因此：
          - 仅保留每个词的第一个 subword 位置（label_ids != -100 的位置）
          - [CLS] / [SEP] / 续接子词（label_ids == -100）全部丢弃
          - 将保留的位置压缩为新的固定长度张量（batch 内对齐到最长有效长度）

        Args:
            emissions:  (B, T_subword, num_tags) BERT 完整 subword 序列的发射分数
            label_ids:  (B, T_subword) 标签 id，-100 表示非首子词/特殊符号位置

        Returns:
            packed_emissions: (B, L, num_tags)，L 为 batch 内最大有效 token 数
            packed_tags:      (B, L) 真实标签 id，无效位置填 0
            packed_mask:      (B, L) BoolTensor，True 表示真实 token 位置
        """
        valid_mask = label_ids != -100
        lengths = valid_mask.sum(dim=1)
        max_len = int(lengths.max().item())

        batch_size, _, num_tags = emissions.shape
        packed_emissions = emissions.new_zeros((batch_size, max_len, num_tags))
        packed_tags = label_ids.new_zeros((batch_size, max_len))
        packed_mask = torch.zeros((batch_size, max_len), dtype=torch.bool, device=emissions.device)

        for batch_idx in range(batch_size):
            valid_indices = valid_mask[batch_idx].nonzero(as_tuple=True)[0]
            valid_length = int(valid_indices.numel())
            packed_emissions[batch_idx, :valid_length] = emissions[batch_idx, valid_indices]
            packed_tags[batch_idx, :valid_length] = label_ids[batch_idx, valid_indices]
            packed_mask[batch_idx, :valid_length] = True

        return packed_emissions, packed_tags, packed_mask

    def _encode(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        token_type_ids: torch.Tensor,
    ) -> torch.Tensor:
        """
        Returns:
            emissions: (B, T, num_tags)，T 为 subword 序列长度（含 [CLS]/[SEP]）
        """
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
        )
        sequence_output = outputs.last_hidden_state
        sequence_output = self.dropout(sequence_output)
        emissions = self.fc(sequence_output)
        return emissions

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        token_type_ids: torch.Tensor,
        label_ids: torch.Tensor,
    ) -> torch.Tensor:
        """
        训练时调用，返回 CRF NLL loss。
        label_ids 中 -100 位置（[CLS]/[SEP]/subword 续接）会在进入 CRF 前被移除。
        """
        emissions = self._encode(input_ids, attention_mask, token_type_ids)
        packed_emissions, packed_tags, packed_mask = self._pack_valid_tokens(emissions, label_ids)
        loss = self.crf(packed_emissions, packed_tags, packed_mask)
        return loss

    def decode(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        token_type_ids: torch.Tensor,
        label_ids: torch.Tensor,
    ) -> List[List[int]]:
        """推理时调用，返回真实 token 位置上的 Viterbi 最优路径。"""
        emissions = self._encode(input_ids, attention_mask, token_type_ids)
        packed_emissions, _, packed_mask = self._pack_valid_tokens(emissions, label_ids)
        return self.crf.decode(packed_emissions, packed_mask)


def build_model(
    cfg: dict,
    vocab_size: int,
    num_tags: int,
    tag2id: Optional[Dict[str, int]] = None,
) -> nn.Module:
    """
    根据配置字典构建模型。

    Args:
        cfg:        完整配置字典（来自 YAML）
        vocab_size: 词表大小（BERT 模式下忽略）
        num_tags:   标签数量
        tag2id:     tag→id 映射（用于 CRF 约束）

    Returns:
        model: VanillaTransformerNER 或 BERTTransformerNER
    """
    model_cfg = cfg.get("model", {})
    encoder = model_cfg.get("encoder", "vanilla")
    use_constraint = cfg.get("crf", {}).get("use_constraint", True)

    if encoder == "bert":
        return BERTTransformerNER(
            bert_model_name=model_cfg["bert_model"],
            num_tags=num_tags,
            dropout=model_cfg.get("dropout", 0.1),
            tag2id=tag2id,
            use_constraint=use_constraint,
        )
    else:
        return VanillaTransformerNER(
            vocab_size=vocab_size,
            num_tags=num_tags,
            embed_dim=model_cfg.get("embed_dim", 256),
            num_heads=model_cfg.get("num_heads", 8),
            num_layers=model_cfg.get("num_layers", 4),
            ff_dim=model_cfg.get("ff_dim", 1024),
            dropout=model_cfg.get("dropout", 0.1),
            max_len=model_cfg.get("max_len", 512),
            tag2id=tag2id,
            use_constraint=use_constraint,
        )
