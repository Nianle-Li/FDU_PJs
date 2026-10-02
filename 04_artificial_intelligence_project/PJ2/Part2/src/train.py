"""Part2 CRF 训练入口。

脚本负责串联数据读取、特征提取、模型训练和验证集评估，输出可直接复现的模型与指标文件。
"""
import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import load_data, write_predictions
from src.features import sent2features, sent2labels
from src.model import build_model, train, save_model
from src.evaluate import evaluate_and_report


def parse_args():
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="训练 CRF NER 模型")
    parser.add_argument("--lang",       required=True, choices=["zh", "en"],
                        help="语言：zh（中文）或 en（英文）")
    parser.add_argument("--data_dir",   required=True,
                        help="数据集目录（含 train.txt / validation.txt）")
    parser.add_argument("--output_dir", required=True,
                        help="输出目录（model.pkl / val_pred.txt / metrics.txt）")
    parser.add_argument("--c1",         type=float, default=0.05, help="L1 正则化系数")
    parser.add_argument("--c2",         type=float, default=0.05, help="L2 正则化系数")
    parser.add_argument("--max_iter",   type=int,   default=200,  help="最大迭代次数")
    return parser.parse_args()


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    train_path = os.path.join(args.data_dir, "train.txt")
    val_path   = os.path.join(args.data_dir, "validation.txt")

    print(f"[train] 加载训练数据: {train_path}")
    train_sents = load_data(train_path)
    print(f"[train] 训练句子数: {len(train_sents)}")

    print(f"[train] 加载验证数据: {val_path}")
    val_sents = load_data(val_path)
    print(f"[train] 验证句子数: {len(val_sents)}")

    print("[train] 提取特征...")
    t0 = time.time()
    X_train = [sent2features(s, args.lang) for s in train_sents]
    y_train = [sent2labels(s) for s in train_sents]
    X_val   = [sent2features(s, args.lang) for s in val_sents]
    y_val   = [sent2labels(s) for s in val_sents]
    print(f"[train] 特征提取耗时: {time.time() - t0:.1f}s")

    # 训练阶段直接围绕验证集表现选择正则强度。
    print(f"[train] 构建模型 (c1={args.c1}, c2={args.c2}, max_iter={args.max_iter})")
    crf = build_model(c1=args.c1, c2=args.c2, max_iterations=args.max_iter)

    print("[train] 开始训练...")
    t0 = time.time()
    crf = train(crf, X_train, y_train)
    print(f"[train] 训练完成，耗时: {time.time() - t0:.1f}s")

    model_path = output_dir / "model.pkl"
    save_model(crf, str(model_path))

    print("[train] 在验证集上推理...")
    y_pred = crf.predict(X_val)

    val_pred_path = output_dir / "val_pred.txt"
    write_predictions(val_path, y_pred, str(val_pred_path))
    print(f"[train] 验证集预测文件已保存: {val_pred_path}")

    lang_name = "Chinese" if args.lang == "zh" else "English"
    metrics_path = output_dir / "metrics.txt"
    evaluate_and_report(
        language=lang_name,
        gold_path=val_path,
        pred_path=str(val_pred_path),
        output_path=str(metrics_path),
    )
    print(f"[train] 评估报告已保存: {metrics_path}")


if __name__ == "__main__":
    main()
