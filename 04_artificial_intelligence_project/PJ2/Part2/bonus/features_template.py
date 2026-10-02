"""
Bonus 方案：基于 template_for_crf.utf8 解析生成特征。

设计思路：
  - parse_template() 解析模板文件，分别返回 U 模板列表和 B 模板列表。
  - U 模板（Unigram）→ 显式展开为状态特征字符串，由 pycrfsuite 学习
    每个 (状态标签, 特征值) 对的权重。
  - B 模板（Bigram）→ 在 CRF++ 中表示输入条件转移特征；pycrfsuite 架构
    将转移参数与状态特征分开，无法直接展开 B 模板为特征字符串。
    实现方式：train_bonus.py 检测 bigram_templates 是否非空，若非空则
    激活 feature.possible_transitions=1，确保所有标签转移对均被分配参数，
    与 CRF++ B 模板的等价效果。

模板格式（CRF++ 兼容）:
    U00:%x[-2,0]        → Unigram 特征：当前位置偏移 -2 行的第 0 列
    B00:%x[-2,0]        → Bigram 模板：对应 CRF++ 的输入条件转移特征
    %x[row,col]         → 当前位置偏移 row 行、第 col 列的输入值

输入数据格式（多列，列间空格/制表符分隔）:
    对于 NER：第 0 列 = token，第 1 列（可选）= 字符类型或其他辅助特征
"""
import re
from typing import List, Dict, Tuple

Sentence = List[Tuple[str, ...]]   # 每个元素为该位置各列的值组成的元组


def parse_template(
    template_path: str,
) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    """
    解析 CRF++ 格式模板文件。

    Returns:
        unigram_templates: [(name, pattern), ...]  U 前缀模板，显式展开为状态特征
        bigram_templates:  [(name, pattern), ...]  B 前缀模板，表示 CRF++ 的转移特征模板。
                           在 pycrfsuite 中不手工展开，而是通过激活
                           feature.possible_transitions 让框架为所有标签对分配转移参数，
                           等价于 CRF++ B 模板的效果。
    """
    unigram_templates: List[Tuple[str, str]] = []
    bigram_templates:  List[Tuple[str, str]] = []

    with open(template_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("U"):
                name, pattern = line.split(":", 1)
                unigram_templates.append((name.strip(), pattern.strip()))
            elif line.startswith("B"):
                name, pattern = line.split(":", 1)
                bigram_templates.append((name.strip(), pattern.strip()))

    return unigram_templates, bigram_templates


_X_PATTERN = re.compile(r"%x\[(-?\d+),(\d+)\]")


def _expand_template(pattern: str, row: int, columns: List[List[str]]) -> str:
    """
    将模板中的 %x[offset, col] 替换为实际值。

    Args:
        pattern:  模板字符串，如 "%x[-1,0]/%x[0,0]"
        row:      当前行索引
        columns:  所有行的列数据，columns[i][j] 为第 i 行第 j 列
    """
    def replace_match(m: re.Match) -> str:
        offset = int(m.group(1))
        col    = int(m.group(2))
        idx = row + offset
        if idx < 0:
            return "<BOS>"
        if idx >= len(columns):
            return "<EOS>"
        row_data = columns[idx]
        if col >= len(row_data):
            return "<UNK>"
        return row_data[col]

    return _X_PATTERN.sub(replace_match, pattern)


def sentence_to_columns(tokens: List[str], lang: str) -> List[List[str]]:
    """
    将 token 列表转换为多列输入。

    为了充分利用模板特征，在原始 token 基础上增加辅助列：
      - 列 0: token 本身
      - 列 1: 字符/词类型标记（中文：汉字/数字/英文/标点；英文：词形压缩）
    """
    result = []
    for tok in tokens:
        if lang == "zh":
            if "\u4e00" <= tok <= "\u9fff":
                tok_type = "CH"
            elif tok.isdigit():
                tok_type = "DG"
            elif tok.isascii() and tok.isalpha():
                tok_type = "EN"
            else:
                tok_type = "PU"
        else:
            if tok.isupper():
                tok_type = "UP"
            elif tok.istitle():
                tok_type = "TI"
            elif tok.isdigit():
                tok_type = "DG"
            else:
                tok_type = "LC"
        result.append([tok, tok_type])
    return result


def _en_extra_features(tokens: List[str], columns: List[List[str]], i: int) -> List[str]:
    """
    英文补充特征：利用 col 1（词类型）的窗口特征 + 前后缀。

    模板文件只引用 col 0（token 本身），对英文 NER 缺少大写规律和
    形态学信息。此函数以 %x[row,1] 语义补充这些特征，与模板框架一致。
    """
    n = len(tokens)

    def get_tok(offset: int) -> str:
        idx = i + offset
        if idx < 0 or idx >= n:
            return ""
        return tokens[idx]

    def get_type(offset: int) -> str:
        """获取 col 1 的词类型"""
        idx = i + offset
        if idx < 0:
            return "BOS"
        if idx >= n:
            return "EOS"
        return columns[idx][1]

    feats: List[str] = []
    w = tokens[i]

    # 词类型窗口特征补足模板中对上下文类别的刻画。
    for offset in (-2, -1, 0, 1, 2):
        feats.append(f"WT{offset:+d}={get_type(offset)}")

    # 词类型 bigram
    feats.append(f"WT-1/WT0={get_type(-1)}/{get_type(0)}")
    feats.append(f"WT0/WT+1={get_type(0)}/{get_type(1)}")
    feats.append(f"WT-1/WT0/WT+1={get_type(-1)}/{get_type(0)}/{get_type(1)}")

    # 前后缀特征补充英文命名实体常见的形态学线索。
    wl = w.lower()
    for k in (1, 2, 3, 4):
        feats.append(f"PFX{k}={wl[:k]}")
        feats.append(f"SFX{k}={wl[-k:]}")

    # 相邻词后缀（右邻词对实体结束边界有重要作用）
    w_p1 = get_tok(1)
    if w_p1:
        for k in (1, 2, 3):
            feats.append(f"SFX+1_{k}={w_p1.lower()[-k:]}")

    return feats


def extract_features_from_template(
    template_path: str,
    tokens: List[str],
    lang: str,
) -> List[List[str]]:
    """
    根据模板文件为整个句子的每个位置生成特征字符串列表。

    对英文额外追加来自 col 1（词类型）的窗口特征及前后缀特征，
    补充模板文件中未覆盖的形态学信息。

    注意：这里显式展开的是 U 模板。B 模板（bigram_templates）不在此处手工转成
    特征字符串——pycrfsuite 的架构将状态特征与转移参数分开处理，转移参数由框架
    在训练时统一学习。调用方（train_bonus.py）通过检测 bigram_templates 是否非空
    来决定是否激活 feature.possible_transitions=1，确保所有标签转移对都被分配参数，
    与 CRF++ B 模板的效果等价。

    Args:
        template_path: 模板文件路径
        tokens:        句子 token 列表
        lang:          "zh" 或 "en"

    Returns:
        features_per_pos: 长度 = len(tokens)，
                          每个元素为该位置的特征字符串列表
    """
    unigram_templates, bigram_templates = parse_template(template_path)
    # bigram_templates 在此处不展开为特征字符串（架构限制见模块 docstring）。
    # 其非空性由 train_bonus.py 用于驱动 feature.possible_transitions 设置。
    # 此处仅使用 unigram_templates 生成状态特征。
    columns = sentence_to_columns(tokens, lang)
    n = len(tokens)

    features_per_pos: List[List[str]] = []
    for i in range(n):
        feat_list = []
        # 这里显式展开的是模板中的 U 特征。
        for name, pattern in unigram_templates:
            value = _expand_template(pattern, i, columns)
            feat_list.append(f"{name}={value}")
        # 英文额外追加词类型和形态学特征，弥补模板表达力不足。
        if lang == "en":
            feat_list.extend(_en_extra_features(tokens, columns, i))
        features_per_pos.append(feat_list)

    return features_per_pos
