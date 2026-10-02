"""CRF 模型封装。

基于 sklearn-crfsuite 暴露统一的构建、训练、保存和加载接口，方便训练脚本与预测脚本共享同一模型约定。

sklearn-crfsuite 底层使用 pycrfsuite（封装 C++ CRF++/crfsuite），训练算法为 L-BFGS。
正则化参数 c1（L1）/ c2（L2）控制特征权重稀疏度，防止过拟合。
"""
import pickle
from pathlib import Path
from typing import List, Dict

import sklearn_crfsuite


def build_model(
    c1: float = 0.05,
    c2: float = 0.05,
    max_iterations: int = 200,
    algorithm: str = "lbfgs",
) -> sklearn_crfsuite.CRF:
    """
    构建未训练的 CRF 实例。

    Args:
        c1:             L1 正则化系数（越大特征权重越稀疏）
        c2:             L2 正则化系数（防止权重过大）
        max_iterations: L-BFGS 最大迭代次数（迭代不足会影响收敛）
        algorithm:      优化算法，默认 "lbfgs"（L-BFGS 拟牛顿法）

    Returns:
        未训练的 sklearn_crfsuite.CRF 实例
    """
    crf = sklearn_crfsuite.CRF(
        algorithm=algorithm,
        c1=c1,
        c2=c2,
        max_iterations=max_iterations,
        all_possible_transitions=True,  # 为训练集中未出现的标签转移也分配参数，避免预测时缺少转移权重
    )
    return crf


def train(
    model: sklearn_crfsuite.CRF,
    X_train: List[List[Dict]],
    y_train: List[List[str]],
) -> sklearn_crfsuite.CRF:
    """
    训练 CRF 模型。

    Args:
        model:   未训练的 CRF 实例（由 build_model 创建）
        X_train: 特征列表，每个元素为一个句子的特征字典列表（由 sent2features 生成）
        y_train: 标签列表，每个元素为一个句子的标签序列（由 sent2labels 生成）

    Returns:
        训练完成的 CRF 实例（原地修改并返回）
    """
    model.fit(X_train, y_train)
    return model


def save_model(model: sklearn_crfsuite.CRF, path: str) -> None:
    """序列化模型到文件。"""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(model, f)
    print(f"[model] 已保存到 {path}")


def load_model(path: str) -> sklearn_crfsuite.CRF:
    """从文件反序列化模型。"""
    with open(path, "rb") as f:
        model = pickle.load(f)
    print(f"[model] 已加载自 {path}")
    return model
