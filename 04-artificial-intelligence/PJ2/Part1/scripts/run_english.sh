#!/usr/bin/env bash
# 英文 HMM NER：训练 + 验证 + 生成预测文件（稳妥提交配置，不使用外部词典）
set -e
cd "$(dirname "$0")/../src"
python main.py --language English \
  --k_transition 0.5 --k_emission 0.05 \
  --no_lowercase --unk_threshold 1 --unk_weight 1.0 \
  --no_gazetteer \
  --gaz_alpha 1.8 \
  "$@"
