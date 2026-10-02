"""Part3 数据加载与预处理。

统一支持 CoNLL 读取、Vanilla Transformer 词表构建，以及 BERT 子词对齐后的标签映射。
"""
import os
import re
from typing import List, Tuple, Dict, Optional

import torch
from torch.utils.data import Dataset, DataLoader

Sentence = List[Tuple[str, str]]

def load_data(path: str) -> List[Sentence]:
    """读取带标签的 CoNLL 文件，返回句子列表。"""
    sentences: List[Sentence] = []
    current: Sentence = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.strip() == "":
                if current:
                    sentences.append(current)
                    current = []
            else:
                parts = line.split(" ")
                if len(parts) >= 2:
                    token, tag = parts[0], parts[-1]
                    current.append((token, tag))
    if current:
        sentences.append(current)
    return sentences


def load_tokens(path: str) -> List[List[str]]:
    """读取 token 文件（测试集，可能无标签）。"""
    sentences: List[List[str]] = []
    current: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.strip() == "":
                if current:
                    sentences.append(current)
                    current = []
            else:
                parts = line.split(" ")
                current.append(parts[0])
    if current:
        sentences.append(current)
    return sentences


def write_predictions(
    path: str,
    sentences: List[List[str]],
    predictions: List[List[str]],
) -> None:
    """将预测结果写入文件，格式与 example_my_result.txt 一致。"""
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for tokens, preds in zip(sentences, predictions):
            for token, pred in zip(tokens, preds):
                f.write(f"{token} {pred}\n")
            f.write("\n")


PAD_TOKEN = "<PAD>"
UNK_TOKEN = "<UNK>"
PAD_ID = 0
UNK_ID = 1


def load_tag2id_from_file(tag_file: str) -> Dict[str, int]:
    """
    从 tag.txt 加载完整标签集合（确保覆盖训练集未出现的 tag）。
    tag.txt 中每行包含一个 tag 名称（忽略注释行和非 tag 行）。
    """
    tags = []
    with open(tag_file, "r", encoding="utf-8") as f:
        for line in f:
            matches = re.findall(r"['\"]([A-Z][^'\"]*)['\"]\s*(?::|,|$)", line)
            for m in matches:
                if m not in tags:
                    tags.append(m)
    if not tags:
        with open(tag_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("总共"):
                    tags.append(line)
    return {tag: idx for idx, tag in enumerate(sorted(tags))}


def char_expand_sentence(sent: Sentence) -> Sentence:
    """
    将词级句子展开为字符级句子，适用于英文 BIO 标注。

    规则：
      - O        → 每个字符标 O
      - B-X      → 首字符标 B-X，其余字符标 I-X
      - I-X      → 每个字符标 I-X
    （中文 BMES 通常已是单字级，无需调用本函数。）
    """
    char_sent: Sentence = []
    for token, tag in sent:
        chars = list(token)
        if not chars:
            continue
        if tag.startswith("B-"):
            inner_tag = "I-" + tag[2:]
        else:
            inner_tag = tag
        char_sent.append((chars[0], tag))
        for c in chars[1:]:
            char_sent.append((c, inner_tag))
    return char_sent


def aggregate_char_to_word(
    word_sents: List[Sentence],
    char_preds: List[List[str]],
) -> List[List[str]]:
    """
    将字符级预测序列聚合回词级预测（取每个词第一个字符的预测标签）。

    Args:
        word_sents: 原始词级句子列表 [(token, tag), ...]
        char_preds: 字符级预测结果列表（与 char_expand_sentence 展开结果对齐）
    Returns:
        word_preds: 词级预测标签列表
    """
    word_preds: List[List[str]] = []
    for sent, cpreds in zip(word_sents, char_preds):
        wpred: List[str] = []
        pos = 0
        for token, _ in sent:
            wpred.append(cpreds[pos])
            pos += len(token)
        word_preds.append(wpred)
    return word_preds


def build_vocab(
    sentences: List[Sentence],
    min_freq: int = 1,
    tag_file: Optional[str] = None,
) -> Tuple[Dict[str, int], Dict[str, int]]:
    """
    构建 token→id 和 tag→id 词表。

    Returns:
        token2id: token 到 id 的映射，PAD=0, UNK=1
        tag2id:   tag 到 id 的映射
    """
    from collections import Counter

    token_counter: Counter = Counter()
    tag_set: set = set()

    for sent in sentences:
        for token, tag in sent:
            token_counter[token] += 1
            tag_set.add(tag)

    token2id: Dict[str, int] = {PAD_TOKEN: PAD_ID, UNK_TOKEN: UNK_ID}
    for token, freq in token_counter.items():
        if freq >= min_freq:
            token2id[token] = len(token2id)

    if tag_file is not None and os.path.exists(tag_file):
        tag2id = load_tag2id_from_file(tag_file)
        for tag in sorted(tag_set):
            if tag not in tag2id:
                tag2id[tag] = len(tag2id)
    else:
        tag2id = {tag: idx for idx, tag in enumerate(sorted(tag_set))}
    return token2id, tag2id


def save_vocab(token2id: Dict[str, int], tag2id: Dict[str, int], output_dir: str) -> None:
    import json
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "token2id.json"), "w", encoding="utf-8") as f:
        json.dump(token2id, f, ensure_ascii=False, indent=2)
    with open(os.path.join(output_dir, "tag2id.json"), "w", encoding="utf-8") as f:
        json.dump(tag2id, f, ensure_ascii=False, indent=2)


def load_vocab(output_dir: str) -> Tuple[Dict[str, int], Dict[str, int]]:
    import json
    with open(os.path.join(output_dir, "token2id.json"), "r", encoding="utf-8") as f:
        token2id = json.load(f)
    with open(os.path.join(output_dir, "tag2id.json"), "r", encoding="utf-8") as f:
        tag2id = json.load(f)
    return token2id, tag2id


class NERDataset(Dataset):
    """将句子列表转换为 (input_ids, tag_ids, length) 张量。"""

    def __init__(
        self,
        sentences: List[Sentence],
        token2id: Dict[str, int],
        tag2id: Dict[str, int],
    ) -> None:
        self.samples = []
        for sent in sentences:
            tokens = [t for t, _ in sent]
            tags = [l for _, l in sent]
            input_ids = [token2id.get(t, UNK_ID) for t in tokens]
            tag_ids = [tag2id[tag] for tag in tags]
            self.samples.append((input_ids, tag_ids))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        return self.samples[idx]


def collate_fn_vanilla(batch, pad_id: int = PAD_ID, pad_tag_id: int = -1):
    """
    动态 padding，返回:
      input_ids:  (B, max_len)  LongTensor
      tag_ids:    (B, max_len)  LongTensor，pad 位置为 -1（CRF mask 中排除）
      mask:       (B, max_len)  BoolTensor，True 表示有效位置
    """
    input_ids_list, tag_ids_list = zip(*batch)
    max_len = max(len(x) for x in input_ids_list)

    input_ids_padded = []
    tag_ids_padded = []
    mask_list = []

    for inp, tag in zip(input_ids_list, tag_ids_list):
        length = len(inp)
        pad_len = max_len - length
        input_ids_padded.append(inp + [pad_id] * pad_len)
        tag_ids_padded.append(tag + [pad_tag_id] * pad_len)
        mask_list.append([True] * length + [False] * pad_len)

    return (
        torch.tensor(input_ids_padded, dtype=torch.long),
        torch.tensor(tag_ids_padded, dtype=torch.long),
        torch.tensor(mask_list, dtype=torch.bool),
    )


def get_dataloader_vanilla(
    sentences: List[Sentence],
    token2id: Dict[str, int],
    tag2id: Dict[str, int],
    batch_size: int,
    shuffle: bool = True,
) -> DataLoader:
    dataset = NERDataset(sentences, token2id, tag2id)
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        collate_fn=lambda b: collate_fn_vanilla(b),
    )


class NERDatasetBERT(Dataset):
    """
    BERT 模式下的数据集：使用 tokenizer 对每个 token 进行 subword 切分，
    取每个原始 token 的第一个 subword 位置作为标签位置，其余子词标为 -100。
    """

    def __init__(
        self,
        sentences: List[Sentence],
        tokenizer,
        tag2id: Dict[str, int],
        max_length: int = 512,
    ) -> None:
        self.samples = []
        for sent in sentences:
            tokens = [t for t, _ in sent]
            tags = [l for _, l in sent]
            encoding = tokenizer(
                tokens,
                is_split_into_words=True,
                max_length=max_length,
                truncation=True,
                padding=False,
                return_offsets_mapping=False,
            )
            word_ids = encoding.word_ids()
            label_ids = []
            prev_word_id = None
            for word_id in word_ids:
                if word_id is None:
                    label_ids.append(-100)
                elif word_id != prev_word_id:
                    label_ids.append(tag2id[tags[word_id]])
                else:
                    label_ids.append(-100)
                prev_word_id = word_id
            self.samples.append({
                "input_ids": encoding["input_ids"],
                "attention_mask": encoding["attention_mask"],
                "token_type_ids": encoding.get("token_type_ids", [0] * len(encoding["input_ids"])),
                "label_ids": label_ids,
            })

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        return self.samples[idx]


def collate_fn_bert(batch, pad_token_id: int = 0):
    """BERT 模式动态 padding。"""
    max_len = max(len(x["input_ids"]) for x in batch)
    input_ids_list, attention_mask_list, token_type_ids_list, label_ids_list = [], [], [], []
    for x in batch:
        pad_len = max_len - len(x["input_ids"])
        input_ids_list.append(x["input_ids"] + [pad_token_id] * pad_len)
        attention_mask_list.append(x["attention_mask"] + [0] * pad_len)
        token_type_ids_list.append(x["token_type_ids"] + [0] * pad_len)
        label_ids_list.append(x["label_ids"] + [-100] * pad_len)
    return {
        "input_ids": torch.tensor(input_ids_list, dtype=torch.long),
        "attention_mask": torch.tensor(attention_mask_list, dtype=torch.long),
        "token_type_ids": torch.tensor(token_type_ids_list, dtype=torch.long),
        "label_ids": torch.tensor(label_ids_list, dtype=torch.long),
    }


def get_dataloader_bert(
    sentences: List[Sentence],
    tokenizer,
    tag2id: Dict[str, int],
    batch_size: int,
    max_length: int = 512,
    shuffle: bool = True,
) -> DataLoader:
    dataset = NERDatasetBERT(sentences, tokenizer, tag2id, max_length)
    pad_token_id = tokenizer.pad_token_id
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        collate_fn=lambda b: collate_fn_bert(b, pad_token_id),
    )
