"""
评估模块：调用 check.py 的 check() 函数，输出分类报告并保存到文件
"""
import sys
import io
from pathlib import Path

# 定位 check.py 所在目录（PJ2/NER/check.py）
# __file__ = .../PJ2/Part2/src/evaluate.py
# parent x3  → .../PJ2/
_NER_DIR = Path(__file__).resolve().parent.parent.parent / "NER"
sys.path.insert(0, str(_NER_DIR))

from check import check  # type: ignore


def evaluate_and_report(
    language: str,
    gold_path: str,
    pred_path: str,
    output_path: str,
) -> None:
    """
    调用 check.py 中的 check() 输出评估报告，同时保存到文件。

    Args:
        language:    "Chinese" 或 "English"
        gold_path:   黄金标注文件路径
        pred_path:   预测文件路径
        output_path: 评估报告保存路径
    """
    # 捕获 check() 的标准输出
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        check(language=language, gold_path=gold_path, my_path=pred_path)
    finally:
        sys.stdout = old_stdout

    report = buf.getvalue()
    print(report)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"Language: {language}\n")
        f.write(f"Gold:     {gold_path}\n")
        f.write(f"Pred:     {pred_path}\n\n")
        f.write(report)
    print(f"[evaluate] 报告已保存: {output_path}")
