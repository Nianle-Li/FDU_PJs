"""Bonus 模板特征推理入口。

脚本使用 pycrfsuite 和模板特征完成测试集预测，方便与基础 CRF 方案做直接对比。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pycrfsuite

from src.data import load_tokens, write_predictions
from bonus.features_template import extract_features_from_template


def parse_args():
    """解析模板推理参数。"""
    parser = argparse.ArgumentParser(description="Bonus: CRF NER 推理")
    parser.add_argument("--lang",        required=True, choices=["zh", "en"])
    parser.add_argument("--model_path",  required=True, help=".crfsuite 模型文件")
    parser.add_argument("--test_path",   required=True)
    parser.add_argument("--template",    required=True, help="CRF++ 模板文件路径")
    parser.add_argument("--output_path", required=True)
    return parser.parse_args()


def main():
    args = parse_args()

    tagger = pycrfsuite.Tagger()
    tagger.open(args.model_path)
    print(f"[bonus predict] 模型已加载: {args.model_path}")

    token_sents = load_tokens(args.test_path)
    print(f"[bonus predict] 句子数: {len(token_sents)}")

    X_test = [
        extract_features_from_template(args.template, tokens, args.lang)
        for tokens in token_sents
    ]

    y_pred = [tagger.tag(xseq) for xseq in X_test]

    Path(args.output_path).parent.mkdir(parents=True, exist_ok=True)
    write_predictions(args.test_path, y_pred, args.output_path)
    print(f"[bonus predict] 结果已保存: {args.output_path}")


if __name__ == "__main__":
    main()
