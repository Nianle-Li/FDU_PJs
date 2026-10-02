"""Part2 CRF 推理入口。

脚本负责加载训练好的 CRF、生成测试特征并导出预测结果，输出格式与提交文件保持一致。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import load_tokens, write_predictions
from src.features import tokens2features
from src.model import load_model


def parse_args():
    """解析推理所需参数。"""
    parser = argparse.ArgumentParser(description="CRF NER 推理")
    parser.add_argument("--lang",        required=True, choices=["zh", "en"],
                        help="语言：zh 或 en")
    parser.add_argument("--model_path",  required=True, help="模型文件路径（.pkl）")
    parser.add_argument("--test_path",   required=True, help="测试文件路径（test.txt）")
    parser.add_argument("--output_path", required=True, help="预测结果输出路径")
    return parser.parse_args()


def main():
    args = parse_args()

    crf = load_model(args.model_path)

    print(f"[predict] 加载测试文件: {args.test_path}")
    token_sents = load_tokens(args.test_path)
    print(f"[predict] 句子数: {len(token_sents)}")

    X_test = [tokens2features(tokens, args.lang) for tokens in token_sents]

    y_pred = crf.predict(X_test)

    Path(args.output_path).parent.mkdir(parents=True, exist_ok=True)
    write_predictions(args.test_path, y_pred, args.output_path)
    print(f"[predict] 结果已保存: {args.output_path}")


if __name__ == "__main__":
    main()
