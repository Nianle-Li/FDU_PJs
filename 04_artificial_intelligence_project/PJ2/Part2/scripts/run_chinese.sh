#!/usr/bin/env bash
# 运行中文 CRF 实验并将结果写入 outputs/chinese。

set -e
cd "$(dirname "$0")/.."

LANG=zh
DATA_DIR=/users/sama/Artificial-Intelligence-PJ/PJ2/NER/Chinese
OUTPUT_DIR=outputs/chinese

echo "[run] 中文 CRF 训练"
python src/train.py \
    --lang       "$LANG" \
    --data_dir   "$DATA_DIR" \
    --output_dir "$OUTPUT_DIR" \
    --c1 0.05 --c2 0.05 --max_iter 200

echo "[done] 中文训练完成。结果: $OUTPUT_DIR"
