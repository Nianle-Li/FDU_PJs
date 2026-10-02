"""Viterbi 解码器。

在 log-space 中搜索全局最优标签路径，并支持合法转移约束和外部词典加成。

算法核心：
  dp[t][j] = max_{i} (dp[t-1][i] + log_trans[i,j]) + log_emit[j, x_t]
  最优路径通过回溯指针 bp[t][j] 还原。

初始化 dp[0][j] = log_init[j] + emit(j, x_0)
递推   dp[t][j] = max_i(dp[t-1][i] + log_trans[i,j]) + emit(j, x_t)  // 违反约束的 i→j 跳过
终止   找 end_mask 允许的最大 dp[T-1][j]
回溯   bp[t][j] 记录最优前驱，逆向还原路径
"""
from typing import List, Optional

from hmm import HMM, NEG_INF


def viterbi(
    model: HMM,
    tokens: List[str],
    constraint_mask: Optional[List[List[bool]]] = None,
    start_mask: Optional[List[bool]] = None,
    end_mask: Optional[List[bool]] = None,
    gazetteer=None,
    gaz_alpha: float = 1.5,
) -> List[str]:
    """
    Viterbi 算法：返回给定 token 序列的全局最优标签路径。

    在 log-space 运算，避免概率连乘下溢。
    约束掩码将非法转移的路径分数设为 NEG_INF，等效于强制排除这些路径。

    Args:
        model:            已训练的 HMM 模型（提供 log_init / log_trans / emit）
        tokens:           待标注的 token 序列（原始字符串列表）
        constraint_mask:  n_tags × n_tags 布尔矩阵，constraint_mask[prev][cur]=False 表示禁止该转移
                          为 None 时不施加转移约束
        start_mask:       长度 n_tags 的布尔列表，start_mask[t]=False 表示 t 不能作为句首标签
        end_mask:         长度 n_tags 的布尔列表，end_mask[t]=False 表示 t 不能作为句尾标签
        gazetteer:        外部词典实例（Gazetteer），为特定 token-tag 对提供 log 加成
        gaz_alpha:        词典加成系数，命中时在发射分数上加 log(gaz_alpha)

    Returns:
        List[str]: 最优标签序列（与 tokens 等长）
    """
    n_tags = len(model.tags)
    T = len(tokens)
    if T == 0:
        return []

    # dp[t][j]  = 到时刻 t、以标签 j 结尾的最优路径 log 分数
    # bp[t][j]  = dp[t][j] 对应的上一时刻最优前驱标签 id（用于回溯）
    dp = [[NEG_INF] * n_tags for _ in range(T)]
    bp = [[-1] * n_tags for _ in range(T)]

    # ── 初始化：t=0，dp[0][j] = log_init[j] + log_emit[j, x_0] ──
    for tid in range(n_tags):
        if start_mask is not None and not start_mask[tid]:
            continue  # 该标签不允许在句首，跳过
        dp[0][tid] = model.log_init.get(tid, NEG_INF) + model.emit(tid, tokens[0], gazetteer, gaz_alpha)

    # ── 递推：t=1..T-1，从所有合法前驱中选最优 ──
    for t in range(1, T):
        # 预先计算当前位置所有标签的发射分数，避免重复调用
        emit_scores = [model.emit(tid, tokens[t], gazetteer, gaz_alpha) for tid in range(n_tags)]
        for cur in range(n_tags):
            best_score = NEG_INF
            best_prev = -1
            for prev in range(n_tags):
                if dp[t - 1][prev] <= NEG_INF:
                    continue  # 前驱路径不可达，跳过
                if constraint_mask is not None and not constraint_mask[prev][cur]:
                    continue  # 非法转移（BIO/BMES 约束），跳过
                trans = model.log_trans.get((prev, cur), NEG_INF)
                score = dp[t - 1][prev] + trans
                if score > best_score:
                    best_score = score
                    best_prev = prev
            # 最优前驱路径分 + 发射分
            dp[t][cur] = best_score + emit_scores[cur]
            bp[t][cur] = best_prev  # 记录回溯指针

    # ── 终止：找最后时刻分数最高的合法结束标签 ──
    last_candidates = [
        tid for tid in range(n_tags)
        if end_mask is None or end_mask[tid]
    ]
    best_last = max(last_candidates, key=lambda tid: dp[T - 1][tid])

    # ── 回溯：从最优终止标签逐步向前恢复完整路径 ──
    path = [best_last]
    for t in range(T - 1, 0, -1):
        path.append(bp[t][path[-1]])
    path.reverse()  # 反转为从前到后的顺序

    return [model.tags[tid] for tid in path]
