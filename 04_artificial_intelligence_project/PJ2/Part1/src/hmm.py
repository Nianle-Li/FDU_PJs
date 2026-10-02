"""线性链 HMM 实现。

模型在 log-space 中保存初始、转移和发射概率，训练阶段使用 Add-k 平滑，预测阶段为 Viterbi 解码提供稳定的概率查询接口。
"""
import math
import pickle
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

from data import Sentence
from preprocess import normalize_zh, unk_class_zh, normalize_en, unk_class_en


NEG_INF = -1e12


OFFICIAL_TAGS = {
    "English": [
        "O", "B-PER", "I-PER", "B-ORG", "I-ORG",
        "B-LOC", "I-LOC", "B-MISC", "I-MISC",
    ],
    "Chinese": [
        "O",
        "B-NAME", "M-NAME", "E-NAME", "S-NAME",
        "B-CONT", "M-CONT", "E-CONT", "S-CONT",
        "B-EDU", "M-EDU", "E-EDU", "S-EDU",
        "B-TITLE", "M-TITLE", "E-TITLE", "S-TITLE",
        "B-ORG", "M-ORG", "E-ORG", "S-ORG",
        "B-RACE", "M-RACE", "E-RACE", "S-RACE",
        "B-PRO", "M-PRO", "E-PRO", "S-PRO",
        "B-LOC", "M-LOC", "E-LOC", "S-LOC",
    ],
}

UNK_KEYS = {
    "UNK_DIGIT", "UNK_PUNC", "UNK_ALPHA", "UNK_OTHER",
    "UNK_CAP", "UNK_UPPER", "UNK_HYPHEN", "UNK_SUFFIX",
}


class HMM:
    """
    用于序列标注的线性链 HMM（隐马尔可夫模型）。

    模型概率均存储在 log-space，避免长序列下的浮点下溢。
    训练使用 Add-k 平滑（Laplace 平滑的推广），缓解数据稀疏问题。
    低频词被映射到粗粒度 UNK 类别，以提升对未见词的泛化能力。

    主要参数：
      log_init   : dict[tag_id -> float]           初始概率 log P(y_1 = t)
      log_trans  : dict[(prev_id, cur_id) -> float] 转移概率 log P(y_t | y_{t-1})
      log_emit   : dict[(tag_id, word)   -> float]  发射概率 log P(x_t | y_t)
    """

    def __init__(
        self,
        language: str = "Chinese",
        k_transition: float = 0.5,
        k_emission: float = 0.5,
        lowercase: bool = True,
        unk_threshold: int = 1,
        unk_weight: float = 0.5,
    ):
        """
        Args:
            language:      语言种类，"Chinese" 使用 BMES 标注，"English" 使用 BIO 标注
            k_transition:  转移概率 Add-k 平滑系数（越大越平滑，减小稀有转移被完全忽略的风险）
            k_emission:    发射概率 Add-k 平滑系数
            lowercase:     英文 token 是否转小写（降低 OOV）
            unk_threshold: 训练词频 <= 该值时，同时为对应 UNK 类别贡献伪计数
            unk_weight:    低频词贡献给 UNK 类别的伪计数权重（0 表示不贡献）
        """
        assert language in ("Chinese", "English")
        self.language = language
        self.k_trans = k_transition
        self.k_emit = k_emission
        self.lowercase = lowercase
        self.unk_threshold = unk_threshold
        self.unk_weight = unk_weight

        self.tags: List[str] = []
        self.tag2id: Dict[str, int] = {}

        self.log_init: Dict[int, float] = {}
        self.log_trans: Dict[Tuple[int, int], float] = {}
        self.log_emit: Dict[Tuple[int, str], float] = {}

        self.vocab: set = set()

    def _normalize(self, token: str) -> str:
        if self.language == "Chinese":
            return normalize_zh(token)
        return normalize_en(token, self.lowercase)

    def _unk_class(self, token: str) -> str:
        if self.language == "Chinese":
            return unk_class_zh(token)
        return unk_class_en(token)

    def _word_key(self, token: str) -> str:
        """
        返回用于查 log_emit 的 key：已见词用归一化词形，未见词用 UNK 类别字符串。

        Args:
            token: 原始 token 字符串

        Returns:
            若 token 归一化后在词表中，则返回归一化形式；
            否则返回粗粒度 UNK 类别（如 "UNK_CAP" / "UNK_DIGIT" 等）
        """
        norm = self._normalize(token)
        if norm in self.vocab:
            return norm
        return self._unk_class(token)

    def fit(self, sentences: List[Sentence]) -> None:
        """
        根据标注语料用最大似然估计（MLE）+Add-k平滑估计 HMM 三个参数矩阵。

        统计三个概率矩阵

        统计流程：
          1. 收集词频，构建标签集合和词表
          2. 遍历语料统计初始计数、转移计数、发射计数
          3. 低频词额外累加 UNK 类别伪计数（软化 OOV 发射概率）
          4. Add-k 平滑后取 log，写入 log_init / log_trans / log_emit

        Args:
            sentences: 训练语料，每个元素为 [(token, tag), ...] 的句子列表
        """
        tag_set = set(OFFICIAL_TAGS[self.language])
        word_freq: Counter = Counter()
        for sent in sentences:
            for token, tag in sent:
                tag_set.add(tag)
                word_freq[self._normalize(token)] += 1

        # 保证官方标签顺序在前，训练集额外标签追加在后
        official = OFFICIAL_TAGS[self.language]
        extra_tags = sorted(tag_set - set(official))
        self.tags = official + extra_tags
        self.tag2id = {t: i for i, t in enumerate(self.tags)}
        n_tags = len(self.tags)

        # 初始化计数容器
        init_count: Dict[int, float] = defaultdict(float)      # 句首标签计数
        trans_count: Dict[Tuple[int, int], float] = defaultdict(float)  # (prev, cur) 转移计数
        emit_count: Dict[Tuple[int, str], float] = defaultdict(float)   # (tag, word) 发射计数
        tag_count: Dict[int, float] = defaultdict(float)       # 每个标签出现次数
        emit_total: Dict[int, float] = defaultdict(float)      # 每个标签对应的发射总次数（含伪计数）

        for sent in sentences:
            if not sent:
                continue
            # 统计句首标签（用于初始概率）
            first_tid = self.tag2id[sent[0][1]]
            init_count[first_tid] += 1.0

            for i, (token, tag) in enumerate(sent):
                tid = self.tag2id[tag]
                norm = self._normalize(token)
                self.vocab.add(norm)
                emit_count[(tid, norm)] += 1.0  # 发射计数：标签 tid 发射词 norm
                tag_count[tid] += 1.0
                emit_total[tid] += 1.0

                # 低频词策略：同时为该词的 UNK 类别贡献 unk_weight 的伪计数
                # 目的：让 UNK 类别的发射分布与对应低频词的标签分布相似
                if word_freq[norm] <= self.unk_threshold and self.unk_weight > 0:
                    unk = self._unk_class(token)
                    emit_count[(tid, unk)] += self.unk_weight
                    emit_total[tid] += self.unk_weight

                # 统计相邻标签转移（i>0 才有前一个标签）
                if i > 0:
                    prev_tid = self.tag2id[sent[i - 1][1]]
                    trans_count[(prev_tid, tid)] += 1.0

        # ── 估计初始概率 log P(y_1 = t) ──
        # Add-k 平滑：log [(count(t) + k) / (total + k * |T|)]，解决数据稀疏问题，避免得到零概率。
        total_init = sum(init_count.values())
        for tid in range(n_tags):
            cnt = init_count.get(tid, 0.0)
            self.log_init[tid] = math.log(
                (cnt + self.k_trans) / (total_init + self.k_trans * n_tags)
            )

        # ── 估计转移概率 log P(y_t | y_{t-1}) ──
        # 转移概率按前一时刻标签归一化（每个 prev 标签独立 softmax）
        trans_total: Dict[int, float] = defaultdict(float)
        for (prev, cur), cnt in trans_count.items():
            trans_total[prev] += cnt
        for prev in range(n_tags):
            total = trans_total.get(prev, 0.0)
            for cur in range(n_tags):
                cnt = trans_count.get((prev, cur), 0.0)
                self.log_trans[(prev, cur)] = math.log(
                    (cnt + self.k_trans) / (total + self.k_trans * n_tags)
                )

        # ── 估计发射概率 log P(x_t | y_t) ──
        # 词表包含训练词 + 所有 UNK 类别 key，确保推理时总能命中
        all_words = self.vocab | UNK_KEYS
        vocab_size = len(all_words)
        # 对训练中从未出现的标签（tag_count=0），用平均发射总量兜底避免 log(0)
        avg_emit_total = sum(emit_total.values()) / max(1, n_tags)
        for tid in range(n_tags):
            total = emit_total.get(tid, 0.0)
            if tag_count.get(tid, 0.0) == 0.0:
                total = avg_emit_total
            for w in all_words:
                cnt = emit_count.get((tid, w), 0.0)
                self.log_emit[(tid, w)] = math.log(
                    (cnt + self.k_emit) / (total + self.k_emit * vocab_size)
                )

    def save(self, path: str) -> None:
        """序列化整个 HMM 对象。"""
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(path: str) -> "HMM":
        """反序列化 HMM 对象。"""
        with open(path, "rb") as f:
            return pickle.load(f)

    def emit(self, tid: int, token: str, gazetteer=None, gaz_alpha: float = 1.5) -> float:
        """
        查询给定标签对该 token 的发射 log 分数，并可选地叠加外部词典加成。

        查询回退策略（三级）：
          1. 先查归一化词形（已见词）
          2. 若未命中，查 UNK 类别 key（如 UNK_CAP）
          3. 若仍未命中，回退为 NEG_INF（极低概率）

        Args:
            tid:       标签 id（对应 self.tags[tid]）
            token:     原始 token 字符串（未经归一化）
            gazetteer: 外部词典实例（Gazetteer），None 表示不使用
            gaz_alpha: 词典加成系数；命中时在 log 分数上加 log(gaz_alpha)

        Returns:
            log P(token | tag) + 词典加成（若有）
        """
        key = self._word_key(token)
        val = self.log_emit.get((tid, key))
        if val is None:
            # 二级回退：用通用未知词类别 UNK_OTHER
            val = self.log_emit.get((tid, "UNK_OTHER"))
        if val is None:
            val = NEG_INF
        # 词典加成建立在已有发射概率之上，避免为完全未知项引入伪强信号。
        if gazetteer is not None and val > NEG_INF:
            val += gazetteer.get_bonus(token, self.tags[tid], alpha=gaz_alpha)
        return val
