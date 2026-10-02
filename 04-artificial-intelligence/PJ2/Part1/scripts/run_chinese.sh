#!/usr/bin/env bash
# 中文 HMM NER：训练 + 验证 + 生成预测文件（最优参数）
set -e
cd "$(dirname "$0")/../src"
python main.py --language Chinese \
  --k_transition 0.1 --k_emission 0.5 \
  --unk_threshold 2 --unk_weight 0.75 \
  --no_constraint --no_gazetteer \
  "$@"
