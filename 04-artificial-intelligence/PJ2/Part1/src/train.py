"""
train.py  ——  HMM 训练入口

用法：
  python train.py --language Chinese
  python train.py --language English
  # 合并 train+validation 训练（测试阶段使用）
  python train.py --language Chinese --include_validation
"""
import argparse
import os
import sys

# 确保能 import 同级模块
sys.path.insert(0, os.path.dirname(__file__))

from data import load_sentences
from hmm import HMM

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
NER_DIR = os.path.join(BASE_DIR, "..", "NER")


DATA_CONFIG = {
    "Chinese": {
        "train": os.path.join(NER_DIR, "Chinese", "train.txt"),
        "val":   os.path.join(NER_DIR, "Chinese", "validation.txt"),
        "model": os.path.join(BASE_DIR, "outputs", "chinese", "model.pkl"),
        "scheme": "BMES",
    },
    "English": {
        "train": os.path.join(NER_DIR, "English", "train.txt"),
        "val":   os.path.join(NER_DIR, "English", "validation.txt"),
        "model": os.path.join(BASE_DIR, "outputs", "english", "model.pkl"),
        "scheme": "BIO",
    },
}


def train(
    language: str,
    k_transition: float = 0.5,
    k_emission: float = 0.5,
    lowercase: bool = True,
    unk_threshold: int = 1,
    unk_weight: float = 0.5,
    include_validation: bool = False,
) -> HMM:
    cfg = DATA_CONFIG[language]
    os.makedirs(os.path.dirname(cfg["model"]), exist_ok=True)

    print(f"[Train] language={language}  k_trans={k_transition}  k_emit={k_emission}"
          f"  unk_threshold={unk_threshold}  unk_weight={unk_weight}"
          f"  include_val={include_validation}")
    sentences = load_sentences(cfg["train"])
    print(f"  训练句子数: {len(sentences)}")

    if include_validation:
        val_sents = load_sentences(cfg["val"])
        sentences = sentences + val_sents
        print(f"  合并验证集后总句子数: {len(sentences)}")

    model = HMM(
        language=language,
        k_transition=k_transition,
        k_emission=k_emission,
        lowercase=lowercase,
        unk_threshold=unk_threshold,
        unk_weight=unk_weight,
    )
    model.fit(sentences)
    model.save(cfg["model"])
    print(f"  模型已保存至: {cfg['model']}")
    return model


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", choices=["Chinese", "English"], default="Chinese")
    parser.add_argument("--k_transition", type=float, default=0.5)
    parser.add_argument("--k_emission", type=float, default=0.5)
    parser.add_argument("--no_lowercase", action="store_true")
    parser.add_argument("--unk_threshold", type=int, default=1,
                        help="词频 <= threshold 的训练词会为对应 UNK 类别贡献伪计数")
    parser.add_argument("--unk_weight", type=float, default=0.5,
                        help="低频词贡献给 UNK 类别的伪计数权重")
    parser.add_argument("--include_validation", action="store_true",
                        help="合并 train+validation 数据训练，用于生成测试集提交模型")
    args = parser.parse_args()
    train(
        language=args.language,
        k_transition=args.k_transition,
        k_emission=args.k_emission,
        lowercase=not args.no_lowercase,
        unk_threshold=args.unk_threshold,
        unk_weight=args.unk_weight,
        include_validation=args.include_validation,
    )
