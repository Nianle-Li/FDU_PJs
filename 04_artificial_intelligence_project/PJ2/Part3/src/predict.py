"""
预测脚本：加载最优模型，对 test.txt 进行预测，输出结果文件。

用法：
  python src/predict.py --config experiments/chinese_bert.yaml --test_file ../../NER/Chinese/test.txt --output_file outputs/chinese/test_pred.txt
  python src/predict.py --config experiments/english_bert.yaml --test_file ../../NER/English/test.txt --output_file outputs/english/test_pred.txt
"""

import argparse
import json
import os
import sys
from pathlib import Path

import torch
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import load_tokens, load_data, write_predictions, char_expand_sentence, aggregate_char_to_word
from src.model import build_model


def parse_args():
    parser = argparse.ArgumentParser(description="预测 NER 标签")
    parser.add_argument("--config", required=True, help="YAML 配置文件路径")
    parser.add_argument("--test_file", required=True, help="测试文件路径（test.txt）")
    parser.add_argument("--output_file", required=True, help="输出文件路径")
    parser.add_argument("--checkpoint", default=None, help="模型权重路径（默认读取 output_dir/best_model.pt）")
    return parser.parse_args()


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    args = parse_args()
    cfg = load_config(args.config)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    output_dir = Path(cfg["output_dir"])
    tag2id_path = output_dir / "tag2id.json"
    with open(tag2id_path, "r", encoding="utf-8") as f:
        tag2id = json.load(f)
    id2tag = {v: k for k, v in tag2id.items()}
    num_tags = len(tag2id)

    encoder = cfg.get("model", {}).get("encoder", "vanilla")

    # 加载 token 列表（兼容有/无标签的测试文件）
    test_sentences = load_tokens(args.test_file)
    print(f"[predict] 测试集句子数: {len(test_sentences)}")

    # 构建模型
    if encoder == "bert":
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(cfg["model"]["bert_model"])
        model = build_model(cfg, vocab_size=0, num_tags=num_tags, tag2id=tag2id)
    else:
        token2id_path = output_dir / "token2id.json"
        with open(token2id_path, "r", encoding="utf-8") as f:
            token2id = json.load(f)
        model = build_model(cfg, vocab_size=len(token2id), num_tags=num_tags, tag2id=tag2id)

    ckpt = args.checkpoint or str(output_dir / "best_model.pt")
    model.load_state_dict(torch.load(ckpt, map_location=device, weights_only=True))
    model.to(device)
    model.eval()
    print(f"[predict] 已加载模型: {ckpt}")

    all_preds = []

    if encoder == "bert":
        from src.data import NERDatasetBERT, collate_fn_bert
        from torch.utils.data import DataLoader

        # 将 token 列表包装为带哑标签的句子格式（标签用 O 占位）
        dummy_sents = [[(tok, "O") for tok in sent] for sent in test_sentences]
        batch_size = cfg["training"].get("batch_size", 32)
        max_length = cfg["model"].get("max_len", 512)
        dataset = NERDatasetBERT(dummy_sents, tokenizer, tag2id, max_length)
        loader = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=False,
            collate_fn=lambda b: collate_fn_bert(b, tokenizer.pad_token_id),
        )
        with torch.no_grad():
            for batch in loader:
                input_ids = batch["input_ids"].to(device)
                attention_mask = batch["attention_mask"].to(device)
                token_type_ids = batch["token_type_ids"].to(device)
                label_ids = batch["label_ids"].to(device)
                paths = model.decode(input_ids, attention_mask, token_type_ids, label_ids)
                for path in paths:
                    all_preds.append([id2tag[t] for t in path])
    else:
        from src.data import collate_fn_vanilla, NERDataset
        from torch.utils.data import DataLoader
        PAD_ID = token2id.get("<PAD>", 0)
        UNK_ID = token2id.get("<UNK>", 1)
        char_level = cfg.get("model", {}).get("char_level", False)

        dummy_sents = [[(tok, "O") for tok in sent] for sent in test_sentences]
        if char_level:
            input_sents = [char_expand_sentence(s) for s in dummy_sents]
        else:
            input_sents = dummy_sents
        dataset = NERDataset(input_sents, token2id, tag2id)
        batch_size = cfg["training"].get("batch_size", 64)
        loader = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=False,
            collate_fn=lambda b: collate_fn_vanilla(b, PAD_ID),
        )
        with torch.no_grad():
            for input_ids, _, mask in loader:
                input_ids, mask = input_ids.to(device), mask.to(device)
                paths = model.decode(input_ids, mask)
                for path in paths:
                    all_preds.append([id2tag[t] for t in path])

        if char_level:
            all_preds = aggregate_char_to_word(dummy_sents, all_preds)

    # 写输出文件
    os.makedirs(os.path.dirname(args.output_file) if os.path.dirname(args.output_file) else ".", exist_ok=True)
    write_predictions(args.output_file, test_sentences, all_preds)
    print(f"[predict] 结果已写入: {args.output_file}")


if __name__ == "__main__":

    main()
