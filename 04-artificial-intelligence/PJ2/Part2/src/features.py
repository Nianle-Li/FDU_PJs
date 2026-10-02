"""CRF 特征提取模块。

中文走字符级 BMES 特征，英文走词级 BIO 特征；两者都围绕局部上下文和词形信息构造稀疏模板。

特征设计思路：
  CRF 的条件概率为：P(y|x) ∝ exp(Σ_t Σ_k w_k · f_k(y_t, y_{t-1}, x, t))
  其中 f_k 是特征函数，w_k 是学习到的权重（由 sklearn-crfsuite 的 L-BFGS 优化）。

  中文特征（字符级）：
    - 局部字符窗口 [-2, +2]：相邻字的语义有助于判断实体边界
    - 字符对/三元组：捕捉连续字的搭配模式
    - 字符类型：区分汉字/数字/英文/标点，不同类型有不同命名实体倾向

  英文特征（词级）：
    - 大写模式（isupper/istitle）：专有名词通常首字母大写
    - 前/后缀（prefix/suffix 1-4）：形态学线索，如 "-tion" 通常是普通词
    - 词形（word shape）：压缩大小写模式，如 "John" → "Xxxx"
    - 相邻词特征：上下文窗口 [-2, +2]
"""
import re
import unicodedata
from typing import Dict, List, Tuple

Sentence = List[Tuple[str, str]]

def _is_chinese(ch: str) -> bool:
    """判断字符是否为中文汉字（CJK 统一汉字范围）。"""
    return "\u4e00" <= ch <= "\u9fff" or "\u3400" <= ch <= "\u4dbf"


def _is_digit(ch: str) -> bool:
    return ch.isdigit()


def _is_alpha(ch: str) -> bool:
    return ch.isascii() and ch.isalpha()


def _is_punctuation(ch: str) -> bool:
    cat = unicodedata.category(ch)
    return cat.startswith("P") or cat.startswith("S")


def _word_shape(w: str) -> str:
    """
    压缩英文词形，保留大小写和数字模式。

    映射规则：大写字母 → 'X'，小写字母 → 'x'，数字 → 'd'，其他保留。
    连续相同字符压缩为一个（如 "HELLO" → "X"，"Hello" → "Xx"）。

    例：
      "John"   → "Xxxx" → 压缩后 "Xx"
      "NATO"   → "XXXX" → 压缩后 "X"
      "B2-2"   → "Xd-d" → 压缩后 "Xd-d"
    """
    shape = []
    for c in w:
        if c.isupper():
            shape.append("X")
        elif c.islower():
            shape.append("x")
        elif c.isdigit():
            shape.append("d")
        else:
            shape.append(c)
    compressed = [shape[0]]
    for s in shape[1:]:
        if s != compressed[-1]:
            compressed.append(s)
    return "".join(compressed)


def word2features_zh(sent: Sentence, i: int) -> Dict[str, object]:
    """
    提取第 i 个中文字符的 CRF 特征字典。

    特征涵盖：
      - 单字特征：当前字及前后各 2 个字（w[-2]~w[+2]），越界用 <BOS>/<EOS> 填充
      - 双字/三字特征：相邻字对、三元组（捕捉字间搭配）
      - 字符类型特征：is_chinese / is_digit / is_alpha / is_punctuation
      - 位置特征：BOS（句首）、EOS（句尾）

    Args:
        sent: 当前句子，格式为 [(token, tag), ...]
        i:    当前处理的字符位置（0-based）

    Returns:
        特征字典，key 为特征名，value 为特征值（str/bool/float）
        sklearn-crfsuite 支持字典值类型直接作为特征
    """
    tokens = [t for t, _ in sent]
    w = tokens[i]

    def get(offset: int) -> str:
        idx = i + offset
        if idx < 0:
            return "<BOS>"
        if idx >= len(tokens):
            return "<EOS>"
        return tokens[idx]

    w_m2 = get(-2)
    w_m1 = get(-1)
    w_0  = get(0)
    w_p1 = get(1)
    w_p2 = get(2)

    features: Dict[str, object] = {
        "bias": 1.0,

        "w[0]": w_0,
        "w[-1]": w_m1,
        "w[-2]": w_m2,
        "w[+1]": w_p1,
        "w[+2]": w_p2,
        "w[-2]/w[-1]": f"{w_m2}/{w_m1}",
        "w[-1]/w[0]":  f"{w_m1}/{w_0}",
        "w[0]/w[+1]":  f"{w_0}/{w_p1}",
        "w[+1]/w[+2]": f"{w_p1}/{w_p2}",
        "w[-1]/w[0]/w[+1]": f"{w_m1}/{w_0}/{w_p1}",
        "is_chinese":     _is_chinese(w),
        "is_digit":       _is_digit(w),
        "is_alpha":       _is_alpha(w),
        "is_punctuation": _is_punctuation(w),
    }

    if i == 0:
        features["BOS"] = True
    if i == len(sent) - 1:
        features["EOS"] = True

    return features


def word2features_en(sent: Sentence, i: int) -> Dict[str, object]:
    """
    提取第 i 个英文词的 CRF 特征字典。

    特征涵盖：
      - 词本身：小写形式、是否全大写、是否首字母大写、是否纯数字
      - 词形（word shape）：压缩大小写/数字模式
      - 前/后缀（prefix/suffix 1-4 字符）：形态学线索
      - 上下文词：前后各 2 个词的小写、大写/首字母大写标志、词形
      - 双词特征：w[-1]/w[0]、w[0]/w[+1] 的组合
      - 位置特征：BOS（句首）、EOS（句尾）

    Args:
        sent: 当前句子，格式为 [(token, tag), ...]
        i:    当前处理的词位置（0-based）

    Returns:
        特征字典
    """
    tokens = [t for t, _ in sent]
    w = tokens[i]

    def get(offset: int) -> str:
        idx = i + offset
        if idx < 0:
            return "<BOS>"
        if idx >= len(tokens):
            return "<EOS>"
        return tokens[idx]

    w_m2 = get(-2)
    w_m1 = get(-1)
    w_0  = get(0)
    w_p1 = get(1)
    w_p2 = get(2)

    features: Dict[str, object] = {
        "bias": 1.0,

        "word.lower()":   w_0.lower(),
        "word.isupper()": w_0.isupper(),
        "word.istitle()": w_0.istitle(),
        "word.isdigit()": w_0.isdigit(),
        "word.shape":     _word_shape(w_0),
        "prefix-1": w_0[:1].lower(),
        "prefix-2": w_0[:2].lower(),
        "prefix-3": w_0[:3].lower(),
        "prefix-4": w_0[:4].lower(),
        "suffix-1": w_0[-1:].lower(),
        "suffix-2": w_0[-2:].lower(),
        "suffix-3": w_0[-3:].lower(),
        "suffix-4": w_0[-4:].lower(),

        "w[-1].lower()": w_m1.lower(),
        "w[-2].lower()": w_m2.lower(),
        "w[+1].lower()": w_p1.lower(),
        "w[+2].lower()": w_p2.lower(),

        "w[-1].isupper()": w_m1.isupper() if w_m1 not in ("<BOS>", "<EOS>") else False,
        "w[-1].istitle()": w_m1.istitle() if w_m1 not in ("<BOS>", "<EOS>") else False,
        "w[+1].isupper()": w_p1.isupper() if w_p1 not in ("<BOS>", "<EOS>") else False,
        "w[+1].istitle()": w_p1.istitle() if w_p1 not in ("<BOS>", "<EOS>") else False,

        "w[-1].shape": _word_shape(w_m1),
        "w[+1].shape": _word_shape(w_p1),
        "w[-1]/w[0]": f"{w_m1.lower()}/{w_0.lower()}",
        "w[0]/w[+1]": f"{w_0.lower()}/{w_p1.lower()}",
    }

    if i == 0:
        features["BOS"] = True
    if i == len(sent) - 1:
        features["EOS"] = True

    return features


def sent2features(sent: Sentence, lang: str) -> List[Dict]:
    """
    将整句转换为特征字典列表（每个位置对应一个特征字典）。

    Args:
        sent: [(token, tag), ...] 格式的句子
        lang: "zh"（中文，字符级）或 "en"（英文，词级）

    Returns:
        List[Dict]，长度与句子等长，每个元素为该位置的 CRF 特征字典
    """
    if lang == "zh":
        return [word2features_zh(sent, i) for i in range(len(sent))]
    else:
        return [word2features_en(sent, i) for i in range(len(sent))]


def sent2labels(sent: Sentence) -> List[str]:
    """提取句子的标签序列（用于训练时构造 y_train）。"""
    return [tag for _, tag in sent]


def tokens2features(tokens: List[str], lang: str) -> List[Dict]:
    """
    将无标签 token 序列转换为推理特征列表。

    推理时没有标签，构造哑标签 "O" 填充成 Sentence 格式后复用 sent2features。

    Args:
        tokens: token 字符串列表（测试集）
        lang:   "zh" 或 "en"

    Returns:
        List[Dict]，同 sent2features 输出格式
    """
    dummy_sent: Sentence = [(t, "O") for t in tokens]
    return sent2features(dummy_sent, lang)
