"""中英文未知词归一化规则。

训练和推理共享同一套归一化与未知词类别映射，降低 OOV（Out-Of-Vocabulary）对 HMM 发射概率的影响。

归一化 + UNK 类别伪计数：训练时词频 ≤ threshold 的词，同时向其 UNK 类别（UNK_CAP、UNK_DIGIT 等）贡献 unk_weight 的伪计数。
推理时未见词先查 UNK 类别，查不到才回退 NEG_INF。

未知词类别（UNK_KEYS）设计思路：
  - 同一类别的 token（如全部为数字）在 NER 中往往具有相似的标注规律
  - 将形态相似的未知词映射到同一 UNK key，可以在稀疏数据下共享统计量
  - 英文类别更细（大写/首字母大写/含连字符/后缀），以捕捉命名实体特征
"""
import re
import unicodedata


def is_digit(token: str) -> bool:
    """判断 token 是否全为数字/小数点（含中文句号形式）。"""
    return bool(re.fullmatch(r"[\d\.，,．]+", token))


def is_punct(token: str) -> bool:
    """判断 token 是否全为标点符号（按 Unicode 类别 P/S 判断）。"""
    return all(unicodedata.category(c).startswith("P") or
               unicodedata.category(c) == "Po" for c in token)


def is_alpha(token: str) -> bool:
    """判断 token 是否全为 ASCII 字母。"""
    return bool(re.fullmatch(r"[A-Za-z]+", token))


def normalize_zh(token: str) -> str:
    """
    中文 token 归一化。

    当前策略：直接返回原始字符串（中文字符形态固定，无需额外归一化）。
    若后续需要繁简转换或全角转半角，可在此处扩展。
    """
    return token


def unk_class_zh(token: str) -> str:
    """
    对中文未见词返回粗粒度 UNK 类别 key。

    分类规则（优先级由高到低）：
      - UNK_DIGIT : 纯数字
      - UNK_ALPHA : 纯英文字母（中文文本中的外文词）
      - UNK_PUNC  : 纯标点
      - UNK_OTHER : 其余情况（如中文汉字、混合词等）

    Args:
        token: 原始 token

    Returns:
        UNK 类别字符串，与 HMM 发射表的 key 对应
    """
    if re.fullmatch(r"\d+", token):
        return "UNK_DIGIT"
    if is_alpha(token):
        return "UNK_ALPHA"
    if is_punct(token):
        return "UNK_PUNC"
    return "UNK_OTHER"


# 英文常见命名实体后缀，用于识别人名地名等形态学线索
COMMON_SUFFIXES = (
    "ing", "tion", "sion", "ness", "ment", "able", "ible",
    "son", "ton", "man", "men", "land", "ism",
)


def normalize_en(token: str, lowercase: bool = True) -> str:
    """
    英文 token 归一化。

    Args:
        token:     原始 token
        lowercase: 是否转为小写（True 可降低因大小写导致的 OOV，但会丢失大写信息）

    Returns:
        归一化后的 token（小写或原始）
    """
    return token.lower() if lowercase else token


def unk_class_en(token: str) -> str:
    """
    对英文未见词返回粗粒度 UNK 类别 key。

    分类规则（优先级由高到低）：
      - UNK_DIGIT  : 数字/日期/货币等数值串
      - UNK_HYPHEN : 含连字符（如 "Coca-Cola"，常为复合词或外来词）
      - UNK_UPPER  : 全大写且长度>1（如 "NATO", "UNESCO"，通常为缩写组织名）
      - UNK_CAP    : 首字母大写（如 "London", "Smith"，通常为专有名词）
      - UNK_SUFFIX : 匹配常见形态后缀（如 "-tion", "-ism"）
      - UNK_OTHER  : 其余情况

    Args:
        token: 原始英文 token（区分大小写）

    Returns:
        UNK 类别字符串
    """
    if re.fullmatch(r"[\d\-\.,/]+", token):
        return "UNK_DIGIT"
    if "-" in token:
        return "UNK_HYPHEN"
    if token.isupper() and len(token) > 1:
        return "UNK_UPPER"
    if token[0].isupper():
        return "UNK_CAP"
    lower = token.lower()
    for suf in COMMON_SUFFIXES:
        if lower.endswith(suf):
            return "UNK_SUFFIX"
    return "UNK_OTHER"
