"""Part1 实验主入口。

脚本串联训练、验证集预测、指标导出和参数搜索，便于快速比较 HMM 变体的效果。
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from data import load_sentences, load_tokens, write_predictions
from hmm import HMM
from decoder import viterbi
from constraints import build_constraint_mask, build_end_mask, build_start_mask
from evaluate import evaluate
from train import train, DATA_CONFIG
from gazetteer import Gazetteer

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


def run_one(
    language: str,
    k_transition: float,
    k_emission: float,
    lowercase: bool,
    unk_threshold: int,
    unk_weight: float,
    use_constraint: bool,
    use_gazetteer: bool = False,
    gaz_alpha: float = 1.5,
    include_validation: bool = False,
) -> float:
    """运行一组配置并返回验证集 F1。"""
    cfg = DATA_CONFIG[language]
    scheme = cfg["scheme"]

    model = train(
        language, k_transition, k_emission, lowercase,
        unk_threshold, unk_weight, include_validation
    )

    constraint_mask = build_constraint_mask(model.tags, scheme) if use_constraint else None
    start_mask = build_start_mask(model.tags, scheme) if use_constraint else None
    end_mask = build_end_mask(model.tags, scheme) if use_constraint else None

    gazetteer = Gazetteer(language) if use_gazetteer else None

    val_sentences, val_flags = load_tokens(cfg["val"])
    preds = [
        viterbi(model, sent, constraint_mask, start_mask, end_mask, gazetteer, gaz_alpha)
        for sent in val_sentences
    ]

    lang_key = language.lower()
    pred_path = os.path.join(BASE_DIR, "outputs", lang_key, "val_pred.txt")
    os.makedirs(os.path.dirname(pred_path), exist_ok=True)
    write_predictions(pred_path, val_flags, preds)

    print(f"\n=== {language} 验证集评测 ===")
    f1 = evaluate(language, cfg["val"], pred_path)
    print(f"  micro F1 = {f1:.4f}\n")

    metrics_path = os.path.join(BASE_DIR, "outputs", lang_key, "metrics.txt")
    with open(metrics_path, "w", encoding="utf-8") as mf:
        mf.write(
            f"language={language}\n"
            f"k_transition={k_transition}\n"
            f"k_emission={k_emission}\n"
            f"lowercase={lowercase}\n"
            f"unk_threshold={unk_threshold}\n"
            f"unk_weight={unk_weight}\n"
            f"use_constraint={use_constraint}\n"
            f"use_gazetteer={use_gazetteer}\n"
            f"gaz_alpha={gaz_alpha}\n"
            f"micro_f1={f1:.4f}\n"
        )
    return f1


def grid_search(language: str, use_gazetteer: bool = False, gaz_alpha: float = 1.5) -> None:
    """枚举关键平滑参数并输出最优配置。"""
    best_f1 = -1
    best_cfg = {}
    k_values = [0.05, 0.1, 0.5, 1.0]
    unk_threshold_values = [1, 2] if language == "Chinese" else [1]
    unk_weight_values = [0.5, 0.75, 1.0]
    lc_values = [True, False] if language == "English" else [True]
    cst_values = [True, False]

    results = []
    for kt in k_values:
        for ke in k_values:
            for lc in lc_values:
                for uth in unk_threshold_values:
                    for uw in unk_weight_values:
                        for cst in cst_values:
                            print(
                                f"\n>>> k_trans={kt} k_emit={ke} lowercase={lc}"
                                f" unk_threshold={uth} unk_weight={uw}"
                                f" constraint={cst} gazetteer={use_gazetteer}"
                            )
                            f1 = run_one(language, kt, ke, lc, uth, uw, cst, use_gazetteer, gaz_alpha)
                            results.append((f1, kt, ke, lc, uth, uw, cst))
                            if f1 > best_f1:
                                best_f1 = f1
                                best_cfg = dict(
                                    k_transition=kt, k_emission=ke,
                                    lowercase=lc, unk_threshold=uth, unk_weight=uw,
                                    use_constraint=cst, gaz_alpha=gaz_alpha,
                                )

    results.sort(reverse=True)
    print("\n=== Grid Search 结果排名 ===")
    for rank, (f1, kt, ke, lc, uth, uw, cst) in enumerate(results[:10], 1):
        print(
            f"  #{rank}  F1={f1:.4f}  k_trans={kt}  k_emit={ke}"
            f"  lc={lc}  unk_threshold={uth}  unk_weight={uw}  cst={cst}"
        )
    print(f"\n最优配置: {best_cfg}  F1={best_f1:.4f}")


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
    parser.add_argument("--gazetteer", action="store_true",
                        help="开启外部词典加成（默认关闭，仅作补充实验）")
    parser.add_argument("--no_constraint", action="store_true")
    parser.add_argument("--no_gazetteer", action="store_true",
                        help="显式关闭外部词典加成")
    parser.add_argument("--gaz_alpha", type=float, default=1.5,
                        help="词典加成强度 alpha（默认 1.5）")
    parser.add_argument("--include_validation", action="store_true",
                        help="训练时合并 train+val（用于最终模型）")
    parser.add_argument("--grid_search", action="store_true",
                        help="遍历所有参数组合，找最优配置")
    args = parser.parse_args()

    use_gazetteer = False
    if args.gazetteer:
        use_gazetteer = True
    if args.no_gazetteer:
        use_gazetteer = False

    if args.grid_search:
        grid_search(args.language, use_gazetteer, args.gaz_alpha)
    else:
        run_one(
            language=args.language,
            k_transition=args.k_transition,
            k_emission=args.k_emission,
            lowercase=not args.no_lowercase,
            unk_threshold=args.unk_threshold,
            unk_weight=args.unk_weight,
            use_constraint=not args.no_constraint,
            use_gazetteer=use_gazetteer,
            gaz_alpha=args.gaz_alpha,
            include_validation=args.include_validation,
        )
