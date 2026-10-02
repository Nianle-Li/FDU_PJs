"""
predict.py  ——  对任意输入文件运行 HMM 推断并输出预测文件

用法：
  python predict.py --language Chinese --input path/to/test.txt --output path/to/pred.txt
  python predict.py --language English --input path/to/test.txt --output path/to/pred.txt
  python predict.py --language English --input ... --output ... --no_constraint --no_gazetteer
"""
import argparse
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(__file__))

from data import load_tokens, write_predictions
from hmm import HMM
from decoder import viterbi
from constraints import build_constraint_mask, build_end_mask, build_start_mask
from gazetteer import Gazetteer

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

MODEL_PATHS = {
    "Chinese": os.path.join(BASE_DIR, "outputs", "chinese", "model.pkl"),
    "English": os.path.join(BASE_DIR, "outputs", "english", "model.pkl"),
}

SCHEME = {
    "Chinese": "BMES",
    "English": "BIO",
}

DEFAULT_CONSTRAINT = {
    "Chinese": False,
    "English": True,
}

DEFAULT_GAZETTEER = {
    "Chinese": False,
    "English": False,
}


def predict(
    language: str,
    input_path: str,
    output_path: str,
    use_constraint: Optional[bool] = None,
    use_gazetteer: Optional[bool] = None,
    gaz_alpha: float = 1.8,
) -> None:
    if use_constraint is None:
        use_constraint = DEFAULT_CONSTRAINT[language]
    if use_gazetteer is None:
        use_gazetteer = DEFAULT_GAZETTEER[language]

    model_path = MODEL_PATHS[language]
    assert os.path.exists(model_path), f"模型不存在: {model_path}，请先运行 train.py"

    model = HMM.load(model_path)
    print(f"[Predict] 已加载模型: {model_path}")

    sentences, line_flags = load_tokens(input_path)
    print(f"  句子数: {len(sentences)}")

    constraint_mask = None
    start_mask = None
    end_mask = None
    if use_constraint:
        constraint_mask = build_constraint_mask(model.tags, SCHEME[language])
        start_mask = build_start_mask(model.tags, SCHEME[language])
        end_mask = build_end_mask(model.tags, SCHEME[language])

    gazetteer = None
    if use_gazetteer:
        gazetteer = Gazetteer(language)
        print(f"  已加载词典 [alpha={gaz_alpha}]")

    predictions = []
    for sent_tokens in sentences:
        tags = viterbi(model, sent_tokens, constraint_mask, start_mask, end_mask, gazetteer, gaz_alpha)
        predictions.append(tags)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    write_predictions(output_path, line_flags, predictions)
    print(f"  预测结果已写出: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", choices=["Chinese", "English"], default="Chinese")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--constraint", action="store_true",
                        help="强制开启 BIO/BMES 合法转移约束")
    parser.add_argument("--no_constraint", action="store_true")
    parser.add_argument("--gazetteer", action="store_true",
                        help="强制开启外部词典加成")
    parser.add_argument("--no_gazetteer", action="store_true")
    parser.add_argument("--gaz_alpha", type=float, default=1.8)
    args = parser.parse_args()
    use_constraint = DEFAULT_CONSTRAINT[args.language]
    if args.constraint:
        use_constraint = True
    if args.no_constraint:
        use_constraint = False

    use_gazetteer = DEFAULT_GAZETTEER[args.language]
    if args.gazetteer:
        use_gazetteer = True
    if args.no_gazetteer:
        use_gazetteer = False

    predict(
        language=args.language,
        input_path=args.input,
        output_path=args.output,
        use_constraint=use_constraint,
        use_gazetteer=use_gazetteer,
        gaz_alpha=args.gaz_alpha,
    )
