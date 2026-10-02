"""
gazetteer.py  ——  外部词典，为 HMM 发射概率提供软约束加成

使用方式：
    gaz = Gazetteer("English")
    bonus = gaz.get_bonus("Smith", "B-PER", alpha=1.5)  # 返回 log(1.5)

加成原理：
    log P_final(x | y) = log P_hmm(x | y) + bonus(x, y)
    bonus(x, y) = log(alpha)  if token x ∈ gazetteer[y 的实体类型]
               = 0.0          otherwise
"""
import math
import os
from typing import Dict, Optional, Set


class Gazetteer:
    """
    支持语言：
      - English: PER（名+姓）、LOC（国家/城市）、ORG（机构后缀/关键词）
      - Chinese:  NAME（姓氏首字）、LOC（省市地名）
    """

    def __init__(self, language: str, gazetteer_dir: Optional[str] = None):
        self.language = language
        if gazetteer_dir is None:
            gazetteer_dir = os.path.join(os.path.dirname(__file__), "gazetteers")

        self.sets: Dict[str, Set[str]] = {}

        if language == "English":
            self._load("PER_FIRST", os.path.join(gazetteer_dir, "en_first_names.txt"), lc=True)
            self._load("PER_LAST",  os.path.join(gazetteer_dir, "en_last_names.txt"),  lc=True)
            self._load("LOC",       os.path.join(gazetteer_dir, "en_locations.txt"),   lc=True)
            self._load("ORG",       os.path.join(gazetteer_dir, "en_org_indicators.txt"), lc=True)
        elif language == "Chinese":
            self._load("NAME", os.path.join(gazetteer_dir, "zh_surnames.txt"),  lc=False)
            self._load("LOC",  os.path.join(gazetteer_dir, "zh_locations.txt"), lc=False)

    def _load(self, key: str, path: str, lc: bool = True) -> None:
        """从文件加载词典（空格/换行分隔，# 开头为注释行）。"""
        s: Set[str] = set()
        if not os.path.exists(path):
            self.sets[key] = s
            return
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                for token in line.split():
                    token = token.strip()
                    if token and not token.startswith("#"):
                        s.add(token.lower() if lc else token)
        self.sets[key] = s

    def get_bonus(self, token: str, tag: str, alpha: float = 1.5) -> float:
        """
        若 token 匹配 tag 对应的词典，返回 log(alpha)，否则返回 0.0。

        英文额外约束：token 首字母须大写（避免对常见小写词产生误加成）。
        """
        if not token:
            return 0.0

        lower_tok = token.lower()

        if self.language == "English":
            # 仅对首字母大写的 token 生效（命名实体通常大写）
            if not token[0].isupper():
                return 0.0

            if tag in ("B-PER", "I-PER"):
                if (lower_tok in self.sets.get("PER_FIRST", set()) or
                        lower_tok in self.sets.get("PER_LAST", set())):
                    return math.log(alpha)

            elif tag in ("B-LOC", "I-LOC"):
                if lower_tok in self.sets.get("LOC", set()):
                    return math.log(alpha)

            elif tag in ("B-ORG", "I-ORG"):
                if lower_tok in self.sets.get("ORG", set()):
                    return math.log(alpha)

        elif self.language == "Chinese":
            if tag in ("B-NAME", "S-NAME"):
                if token in self.sets.get("NAME", set()):
                    return math.log(alpha)

            elif tag in ("B-LOC", "S-LOC", "M-LOC", "E-LOC"):
                if token in self.sets.get("LOC", set()):
                    return math.log(alpha)

        return 0.0
