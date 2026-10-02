"""手写线性链 CRF（Conditional Random Field）。

实现要点：
  - Forward 算法：计算 log-partition function log Z（归一化因子），用于计算 NLL 损失
  - Viterbi 解码：找全局最优标签路径（用于推理）
  - 非法转移约束：在参数初始化时将违反 BIO/BMES 规则的转移分数设为极小值

损失函数：NLL = log Z - score(真实路径)
  - log Z   = log Σ_{所有路径} exp(score)    用 Forward 算法计算
  - score   = Σ_t (start/trans/end 参数 + 发射分数)
  - 最大化真实路径分数 = 最小化 NLL

参数说明：
  transitions[i, j]  : 从标签 i 转移到标签 j 的分数（可学习）
  start_transitions[j]: 以标签 j 开始序列的分数
  end_transitions[i]  : 以标签 i 结束序列的分数
"""

import torch
import torch.nn as nn
from typing import List, Optional

LARGE_NEG = -1e4  # 初始化非法转移分数（足够小但不是 -inf，允许梯度流动使其"软化"）


class CRF(nn.Module):
    """
    线性链 CRF 层。

    Args:
        num_tags:        标签数量（不含 <START>/<STOP> 特殊符号，内部自动添加）
        tag2id:          tag 名称到 id 的映射，用于非法转移约束初始化
        use_constraint:  是否启用 BMES/BIO 非法转移硬约束
    """

    def __init__(
        self,
        num_tags: int,
        tag2id: Optional[dict] = None,
        use_constraint: bool = True,
    ) -> None:
        super().__init__()
        self.num_tags = num_tags

        self.start_transitions = nn.Parameter(torch.empty(num_tags))
        self.end_transitions = nn.Parameter(torch.empty(num_tags))
        self.transitions = nn.Parameter(torch.empty(num_tags, num_tags))

        self._init_parameters()

        if use_constraint and tag2id is not None:
            self._apply_constraints(tag2id)

    def _init_parameters(self) -> None:
        """使用均匀分布初始化参数。"""
        nn.init.uniform_(self.start_transitions, -0.1, 0.1)
        nn.init.uniform_(self.end_transitions, -0.1, 0.1)
        nn.init.uniform_(self.transitions, -0.1, 0.1)

    def _apply_constraints(self, tag2id: dict) -> None:
        """
        根据标注体系设置非法转移的初始分数为 LARGE_NEG。
        支持 BIO 和 BMES 两种体系。
        约束在训练中可以被梯度更新"软化"，视为软约束初始化。
        """
        id2tag = {v: k for k, v in tag2id.items()}
        num_tags = self.num_tags

        with torch.no_grad():
            for i in range(num_tags):
                for j in range(num_tags):
                    tag_from = id2tag.get(i, "O")
                    tag_to = id2tag.get(j, "O")
                    if not self._is_valid_transition(tag_from, tag_to):
                        self.transitions.data[i, j] = LARGE_NEG

            for i in range(num_tags):
                tag = id2tag.get(i, "O")
                if not self._can_start(tag):
                    self.start_transitions.data[i] = LARGE_NEG
                if not self._can_end(tag):
                    self.end_transitions.data[i] = LARGE_NEG

    @staticmethod
    def _can_start(tag: str) -> bool:
        """判断 tag 是否可以作为序列的第一个标签。"""
        prefix = tag.split("-")[0] if "-" in tag else tag
        return prefix not in ("M", "E", "I")

    @staticmethod
    def _can_end(tag: str) -> bool:
        """判断 tag 是否可以作为序列的最后一个标签。"""
        prefix = tag.split("-")[0] if "-" in tag else tag
        return prefix not in ("B", "M")

    @staticmethod
    def _is_valid_transition(tag_from: str, tag_to: str) -> bool:
        """判断从 tag_from 到 tag_to 的转移是否合法。"""
        def get_prefix_entity(tag):
            if "-" in tag:
                parts = tag.split("-", 1)
                return parts[0], parts[1]
            return tag, None

        pf, ef = get_prefix_entity(tag_from)
        pt, et = get_prefix_entity(tag_to)

        if pt == "I":
            if pf not in ("B", "I"):
                return False
            if ef != et:
                return False

        if pt == "M":
            if pf not in ("B", "M"):
                return False
            if ef != et:
                return False
        if pt == "E":
            if pf not in ("B", "M"):
                return False
            if ef != et:
                return False

        return True

    def _log_sum_exp(self, tensor: torch.Tensor, dim: int) -> torch.Tensor:
        """
        数值稳定的 log-sum-exp（LSE）运算。

        直接计算 log(Σ exp(x_i)) 会因 exp 溢出/下溢而不稳定。
        稳定版：log(Σ exp(x_i)) = max + log(Σ exp(x_i - max))

        Args:
            tensor: 任意形状的张量
            dim:    沿哪个维度求 LSE

        Returns:
            沿 dim 维度 LSE 后的张量（维度减一）
        """
        max_val, _ = tensor.max(dim=dim, keepdim=True)
        return (tensor - max_val).exp().sum(dim=dim).log() + max_val.squeeze(dim)

    def _compute_log_partition(
        self,
        emissions: torch.Tensor,
        mask: torch.Tensor,
    ) -> torch.Tensor:
        """
        Forward 算法：计算所有可能路径的 log-partition function log Z。

        log Z = log Σ_{y_1...y_T} exp(score(y_1...y_T))

        迭代公式：
          alpha[0][j]   = start_transitions[j] + emissions[0][j]
          alpha[t][j]   = LSE_i(alpha[t-1][i] + transitions[i,j]) + emissions[t][j]
          log Z         = LSE_j(alpha[T-1][j] + end_transitions[j])

        对 pad 位置（mask=False），alpha 保持不更新（复用前一时刻的值）。

        Args:
            emissions: (batch_size, seq_len, num_tags) Transformer 输出的发射分数
            mask:      (batch_size, seq_len) BoolTensor，True 为真实 token 位置

        Returns:
            log_Z: (batch_size,) 每个样本的归一化因子
        """
        batch_size, seq_len, num_tags = emissions.shape

        # 初始化：t=0 时以 start_transitions + 发射分数作为初始 alpha
        alpha = self.start_transitions.unsqueeze(0) + emissions[:, 0, :]
        # alpha shape: (B, num_tags)

        for t in range(1, seq_len):
            # alpha.unsqueeze(2) shape: (B, num_tags, 1)
            # transitions.unsqueeze(0) shape: (1, num_tags, num_tags)
            # 广播后 shape: (B, num_tags, num_tags)，[b][i][j] = alpha[b][i] + trans[i][j]
            alpha_t = self._log_sum_exp(
                alpha.unsqueeze(2) + self.transitions.unsqueeze(0),
                dim=1,                          # 对"从哪个前驱"维度做 LSE，得 (B, num_tags)
            ) + emissions[:, t, :]

            # pad 位置不更新 alpha（相当于序列到此已结束）
            mask_t = mask[:, t].unsqueeze(1)    # (B, 1)
            alpha = torch.where(mask_t, alpha_t, alpha)

        # 加上终止分数，并对所有结束标签做 LSE
        alpha = alpha + self.end_transitions.unsqueeze(0)
        return self._log_sum_exp(alpha, dim=1)  # (B,)

    def _compute_score(
        self,
        emissions: torch.Tensor,
        tags: torch.Tensor,
        mask: torch.Tensor,
    ) -> torch.Tensor:
        """
        计算真实标签路径的总分数（用于 NLL = log Z - score）。

        score(y_1...y_T) = start_trans[y_1]
                         + Σ_t (emit[t][y_t] + trans[y_{t-1}, y_t])
                         + end_trans[y_T]

        Args:
            emissions: (batch_size, seq_len, num_tags)
            tags:      (batch_size, seq_len) 真实标签 id，padding 位置值任意
            mask:      (batch_size, seq_len) BoolTensor

        Returns:
            score: (batch_size,) 每个样本的真实路径总分
        """
        batch_size, seq_len, _ = emissions.shape

        # 起始分：start_trans[y_1] + emit[0][y_1]
        score = self.start_transitions[tags[:, 0]] + emissions[:, 0, :].gather(
            1, tags[:, 0].unsqueeze(1)
        ).squeeze(1)

        # 逐步累加转移分 + 发射分（pad 位置 mask=False，乘 0 跳过）
        for t in range(1, seq_len):
            trans_score = self.transitions[tags[:, t - 1], tags[:, t]]  # (B,)
            emit_score = emissions[:, t, :].gather(1, tags[:, t].unsqueeze(1)).squeeze(1)
            score += (trans_score + emit_score) * mask[:, t].float()

        # 加上最后一个真实 token 的终止分
        last_idx = mask.long().sum(dim=1) - 1                           # 每个样本的最后有效位置索引
        last_tags = tags.gather(1, last_idx.unsqueeze(1)).squeeze(1)
        score += self.end_transitions[last_tags]

        return score

    def forward(
        self,
        emissions: torch.Tensor,
        tags: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
        reduction: str = "mean",
    ) -> torch.Tensor:
        """
        计算 CRF 负对数似然损失（用于训练）。

        Args:
            emissions: (batch_size, seq_len, num_tags) 发射分数（Transformer 输出经 Linear 投影后）
            tags:      (batch_size, seq_len) 真实标签 id
            mask:      (batch_size, seq_len) BoolTensor，None 时全部有效
            reduction: 'mean' | 'sum' | 'none'

        Returns:
            loss: 标量（reduction='mean'/'sum'）或 (batch_size,)（'none'）
        """
        if mask is None:
            mask = torch.ones(emissions.shape[:2], dtype=torch.bool, device=emissions.device)

        log_Z = self._compute_log_partition(emissions, mask)
        score = self._compute_score(emissions, tags, mask)
        nll = log_Z - score

        if reduction == "mean":
            return nll.mean()
        elif reduction == "sum":
            return nll.sum()
        else:
            return nll

    def decode(
        self,
        emissions: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
    ) -> List[List[int]]:
        """
        Viterbi 解码：找每个样本的全局最优标签路径。

        动态规划公式：
          viterbi[0][j] = start_trans[j] + emit[0][j]
          viterbi[t][j] = max_i(viterbi[t-1][i] + trans[i,j]) + emit[t][j]
          最优路径      = argmax_j viterbi[T-1][j] + end_trans[j] 后回溯

        Args:
            emissions: (batch_size, seq_len, num_tags)
            mask:      (batch_size, seq_len) BoolTensor，None 时全序列有效

        Returns:
            best_paths: List[List[int]]，每个句子的最优标签 id 序列（仅含有效位置）
        """
        if mask is None:
            mask = torch.ones(emissions.shape[:2], dtype=torch.bool, device=emissions.device)

        batch_size, seq_len, num_tags = emissions.shape

        # viterbi[b][j] = 到当前时刻以标签 j 结尾的最优路径分数
        viterbi = self.start_transitions.unsqueeze(0) + emissions[:, 0, :]
        backpointers = []  # 每个时刻各标签的最优前驱标签 id

        for t in range(1, seq_len):
            # v_t[b][i][j] = viterbi[b][i] + trans[i][j]，广播到 (B, K, K)
            v_t = viterbi.unsqueeze(2) + self.transitions.unsqueeze(0)
            best_scores, best_tags = v_t.max(dim=1)   # (B, K)：每个当前标签的最优前驱
            backpointers.append(best_tags)             # 存回溯指针

            new_viterbi = best_scores + emissions[:, t, :]
            # pad 位置保持 viterbi 不变（相当于序列已结束）
            mask_t = mask[:, t].unsqueeze(1)
            viterbi = torch.where(mask_t, new_viterbi, viterbi)

        # 加终止分，找最优结束标签
        viterbi += self.end_transitions.unsqueeze(0)
        best_last_scores, best_last_tags = viterbi.max(dim=1)

        best_last_tags_list = best_last_tags.tolist()

        # 回溯：对每个样本，从最后一个有效位置向前找完整路径
        best_paths = []
        for b in range(batch_size):
            # 获取有效位置索引（升序），跳过 pad
            valid_pos = mask[b].nonzero(as_tuple=True)[0].tolist()
            path = [best_last_tags_list[b]]
            # 从最后一个有效位置开始向前回溯（跳过第一个，它是起点）
            for vp in reversed(valid_pos[1:]):
                # backpointers[vp-1][b][当前标签] = 上一时刻的最优前驱标签
                path.append(backpointers[vp - 1][b][path[-1]].item())
            path.reverse()   # 反转为从前到后的顺序
            best_paths.append(path)

        return best_paths
