# PJ1 简要说明

> 本部分为简要说明，详细信息请见两篇实验报告。

本项目分为两个部分，逐步完成从“手写神经网络”到“自定义卷积网络”的实现与优化。

- Part1：不依赖深度学习框架，基于 NumPy 手工实现多层感知机、损失函数、反向传播与优化器，完成 sin(x) 回归和手写汉字分类。
- Part2：基于 PyTorch 自行搭建残差卷积网络，并围绕数据增强、SE、EMA 等策略做对比实验，得到最终分类模型。

## 重要内容位置

- 项目使用依赖：`requirements.txt`
- 第一部分实验报告：`doc/Experiment_Report_Part1.pdf`
- 第二部分实验报告：`doc/Experiment_Report_Part2.pdf`
- 第一部分核心代码：`Part1/scr/`
- 第二部分核心代码：`Part2/scr/`
- 第一部分正式实验与模型：`Part1/experiments/`
- 第二部分正式实验与模型：`Part2/experiments/`


## 整体架构

项目结构按“报告 - 代码 - 实验产物”组织：

- `doc/`：实验报告。
- `Part1/`：纯 NumPy 版本的网络实现、训练评估脚本和实验结果。
- `Part2/`：PyTorch CNN 实现、训练评估脚本和实验结果。
- `train_data_update_03-31_v2/`：训练使用的数据目录。

## 已实现的 Bonus

已实现第一个 Bonus（防止过拟合的尝试）：

- Part2 已落地并验证多种防过拟合手段，包含数据增强（`RandomShift`、`RandomErasing`、`Mixup`）、训练正则与技巧（`Dropout`、`weight decay`、`label smoothing`、`EMA`）以及早停（`EarlyStopping`）；实现与对比实验位于 `Part2/scr/` 与 `Part2/experiments/`，详见 `doc/Experiment_Report_Part2.md`。
- Part1 在设计与训练流程中也使用了基础的防过拟合手段（数据归一化、随机平移增强、Inverted Dropout、L2 正则/weight decay、early stopping 等），相关代码与实验产物位于 `Part1/scr/` 与 `Part1/experiments/`，详见 `doc/Experiment_Report_Part1.md`。


## 快速验收

先安装依赖：

```bash
pip install -r PJ1/requirements.txt
```

### 1. 快速验证 Part1 回归任务

在工作区根目录运行：

```bash
python PJ1/Part1/scr/eval.py --task regression --checkpoint PJ1/Part1/experiments/regression/best_model.npz
```

该命令会在回归任务验证集上输出 `Val MAE`，并直接给出是否达到题目要求 `MAE < 0.01`。

### 2. 快速验证 Part1 分类最终模型

在工作区根目录运行：

```bash
python PJ1/Part1/scr/interview.py --data_dir train_data_update_03-31_v2/train --checkpoint PJ1/Part1/experiments/cls_final/best_model.npz
```

该命令会直接输出分类准确率，用于验证第一部分手写 MLP 的最终模型是否可正常推理。

### 3. 快速验证 Part2 最终模型

在工作区根目录运行：

```bash
python PJ1/Part2/scr/interview.py --data_dir train_data_update_03-31_v2/train --checkpoint PJ1/Part2/experiments/final_model/best_model.pth
```

该命令会直接输出分类准确率，验收形式与第一部分保持一致。

## 本次项目的感悟与收获

这次项目最大的收获，不是单一指标提升了多少，而是对“模型为什么有效”有了更完整的认识。

第一，我真正把反向传播从公式推导落实到了代码实现，理解了缓存中间量、逐层回传梯度和数值梯度校验之间的关系。第二，我更加明确了实验设计不能只看最终分数，必须通过控制变量去判断到底是网络结构、正则强度还是数据增强在起作用。第三，我也体会到在小规模图像任务上，很多时候提升性能的关键不一定是把模型做得更复杂，而是更贴近数据特点地设计训练策略。

整体来看，这个项目让我把“会用模型”进一步推进到了“能解释、能实现、能验证、能比较”的层面，这也是我认为它最有价值的地方。
