#!/bin/bash
# 根据参数选择英文 Vanilla 或 BERT 实验。
set -e

cd "$(dirname "$0")/.."

MODE=${1:-bert}

if [ "$MODE" = "bert" ]; then
    echo "[run] 英文 BERT+CRF 训练"
    python src/train.py --config experiments/english_bert.yaml
else
    echo "[run] 英文 Vanilla Transformer+CRF 训练"
    python src/train.py --config experiments/english_vanilla.yaml
fi
