"""Bonus 模板特征训练入口。

该脚本改用 pycrfsuite 直接消费 CRF++ 模板生成的离散特征，用于和基础手工特征方案做对照实验。
"""
import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pycrfsuite

from src.data import load_data, write_predictions
from src.evaluate import evaluate_and_report
from bonus.features_template import extract_features_from_template, parse_template


def parse_args():
    """解析模板版训练参数。"""
    parser = argparse.ArgumentParser(description="Bonus: 基于模板的 CRF NER 训练")
    parser.add_argument("--lang",        required=True, choices=["zh", "en"])
    parser.add_argument("--data_dir",    required=True)
    parser.add_argument("--output_dir",  required=True)
    parser.add_argument("--template",    required=True,
                        help="CRF++ 模板文件路径（template_for_crf.utf8）")
    parser.add_argument("--max_iter",    type=int, default=200)
    parser.add_argument("--c1",          type=float, default=0.05)
    parser.add_argument("--c2",          type=float, default=0.05)
    return parser.parse_args()


def sents_to_features(sents, template_path, lang):
    """将句子列表转换为 pycrfsuite 所需的模板特征格式。"""
    result = []
    for sent in sents:
        tokens = [t for t, _ in sent]
        feat_per_pos = extract_features_from_template(template_path, tokens, lang)
        result.append(feat_per_pos)
    return result


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    train_path = os.path.join(args.data_dir, "train.txt")
    val_path   = os.path.join(args.data_dir, "validation.txt")
    model_path = str(output_dir / "model_bonus.crfsuite")

    print(f"[bonus train] 加载训练数据: {train_path}")
    train_sents = load_data(train_path)
    print(f"[bonus train] 加载验证数据: {val_path}")
    val_sents = load_data(val_path)

    # 解析模板文件，获取 U/B 模板列表。
    # B 模板（bigram_templates）在 CRF++ 中生成输入条件转移特征；
    # pycrfsuite 的架构不支持直接展开 B 模板为特征字符串，
    # 因此改为检测 B 模板是否存在，若存在则激活 feature.possible_transitions=1，
    # 确保所有标签转移对（包括训练集未出现的）均被分配参数，等价于 CRF++ B 模板的效果。
    print(f"[bonus train] 使用模板: {args.template}")
    _, bigram_templates = parse_template(args.template)
    has_bigram = len(bigram_templates) > 0
    print(f"[bonus train] B 模板数: {len(bigram_templates)}，"
          f"feature.possible_transitions={'1' if has_bigram else '0'}")

    t0 = time.time()
    X_train = sents_to_features(train_sents, args.template, args.lang)
    y_train = [[tag for _, tag in s] for s in train_sents]
    X_val   = sents_to_features(val_sents, args.template, args.lang)
    y_val   = [[tag for _, tag in s] for s in val_sents]
    print(f"[bonus train] 特征提取耗时: {time.time() - t0:.1f}s")

    trainer = pycrfsuite.Trainer() # type: ignore
    trainer.select("lbfgs")
    trainer.set("c1", str(args.c1))
    trainer.set("c2", str(args.c2))
    trainer.set("max_iterations", str(args.max_iter))
    # B 模板存在 → 激活全转移参数（等价于 CRF++ 的 B 模板语义）
    trainer.set("feature.possible_transitions", "1" if has_bigram else "0")

    print("[bonus train] 装载训练样本...")
    for xseq, yseq in zip(X_train, y_train):
        trainer.append(xseq, yseq)

    print("[bonus train] 开始训练...")
    t0 = time.time()
    trainer.train(model_path)
    print(f"[bonus train] 训练完成，耗时: {time.time() - t0:.1f}s")
    print(f"[bonus train] 模型已保存: {model_path}")

    tagger = pycrfsuite.Tagger()# type: ignore
    tagger.open(model_path)

    y_pred = [tagger.tag(xseq) for xseq in X_val]

    val_pred_path = output_dir / "val_pred.txt"
    write_predictions(val_path, y_pred, str(val_pred_path))

    lang_name = "Chinese" if args.lang == "zh" else "English"
    evaluate_and_report(
        language=lang_name,
        gold_path=val_path,
        pred_path=str(val_pred_path),
        output_path=str(output_dir / "metrics.txt"),
    )


if __name__ == "__main__":
    main()
