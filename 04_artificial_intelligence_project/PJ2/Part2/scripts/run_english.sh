#!/usr/bin/env bash
# 运行英文 CRF 实验并将结果写入 outputs/english。

set -e
cd "$(dirname "$0")/.."

LANG=en
DATA_DIR=/users/sama/Artificial-Intelligence-PJ/PJ2/NER/English
OUTPUT_DIR=outputs/english

echo "[run] 英文 CRF 训练"
python src/train.py \
    --lang       "$LANG" \
    --data_dir   "$DATA_DIR" \
    --output_dir "$OUTPUT_DIR" \
    --c1 0.05 --c2 0.05 --max_iter 200

echo "[done] 英文训练完成。结果: $OUTPUT_DIR"
