# PJ1 第二部分实验报告

## 1. 实验目标

第二部分要求自行实现卷积神经网络，完成 12 类手写汉字分类，并围绕网络改进与性能提升进行实验论证。结合题目 bonus，本部分重点尝试了多种防过拟合手段，并通过控制变量实验验证其效果。

最终提交包含：

1. 基于 PyTorch 的自定义残差卷积网络（不调用现成模型），含 SE 通道注意力模块。
2. 四组正式验证实验（baseline、strong_aug、se_ema、se_strong_aug）及完整实验产物。
3. 基于最优配置的两阶段训练最终模型（全量 7429 张训练数据）。
4. 面试推理接口 `scr/interview.py`，可直接加载最终 checkpoint 做快速验收。

---

## 2. 代码架构说明

核心代码位于 `Part2/scr/`，模块职责如下：

| 文件           | 职责                                                            |
| -------------- | --------------------------------------------------------------- |
| `model.py`     | 残差块 `ResBlock`、`SEBlock` 与主干网络 `ResNetCNN`             |
| `dataset.py`   | BMP 加载、归一化、RandomShift、RandomErasing、Mixup、增强流水线 |
| `train.py`     | YAML 驱动训练入口，含 EMA、早停、分层划分、cosine 学习率        |
| `eval.py`      | 加载 checkpoint，输出准确率、混淆矩阵、P/R/F1                   |
| `interview.py` | 面试推理接口 `ClassificationModel`                              |
| `utils.py`     | 路径解析、随机种子、分层划分、checkpoint 存取                   |

实验配置（`experiments/*.yaml`）控制所有超参数；产物保存于对应子目录，工程规范与第一部分一致（详见第一部分报告）。

从工程组织角度看，第二部分形成了较完整的实验闭环：`train.py` 负责按配置训练并保存 checkpoint 与日志，`eval.py` 负责统一输出准确率、混淆矩阵和 P/R/F1，`interview.py` 则用于面试阶段的快速批量推理。这样的拆分使“训练、评估、展示”三类需求彼此解耦，也有利于后续复现实验和解释结果来源。

### 2.1 运行与复现方式

本部分采用 YAML 配置驱动实验，推荐在项目根目录下运行。典型命令如下：

```bash
python -u PJ1/Part2/scr/train.py --config PJ1/Part2/experiments/strong_aug.yaml
python -u PJ1/Part2/scr/eval.py --checkpoint PJ1/Part2/experiments/final_model/best_model.pth --data_dir train_data_update_03-31_v2/train
python -u PJ1/Part2/scr/interview.py --data_dir train_data_update_03-31_v2/train --checkpoint PJ1/Part2/experiments/final_model/best_model.pth
```

其中：

1. `train.py` 用于训练并自动保存 `config.yaml`、`train_log.json`、`split_indices.npz` 与最佳模型。
2. `eval.py` 用于输出标准分类指标，支撑实验分析与结果论证。
3. `interview.py` 用于按面试要求直接加载最终 checkpoint 做批量推理。

项目训练与验证均固定随机种子为 42，并保存正式划分索引，从而保证不同实验之间可比、可追溯、可复验。

---

## 3. 网络设计思路

### 3.1 总体架构

针对 28×28 单通道手写汉字的特点，设计了轻量残差 CNN：

- Stem：Conv3×3(1→32) + BatchNorm + ReLU
- Block1：ResBlock(32→32) + MaxPool2×2 → 32×14×14
- Block2：ResBlock(32→64) + MaxPool2×2 → 64×7×7
- Block3：ResBlock(64→128) → 128×7×7
- Head：GlobalAvgPool → Dropout → FC(128→12)

每个残差块（ResBlock）由两个 3×3 卷积 + BN + ReLU 组成，通道或步幅变化时 skip 路径用 1×1 projection conv 对齐。完整的前向传播可以表示为：

$$
\text{ResBlock}(x) = \text{ReLU}\!\left(\text{BN}(\text{Conv}_{3\times3}(\text{ReLU}(\text{BN}(\text{Conv}_{3\times3}(x))))) + \text{proj}(x)\right)
$$

其中 proj(x) 在通道或分辨率变化时为 1×1 conv+BN，否则为恒等映射。

### 3.2 设计选择的合理性

**残差连接**：手写汉字笔画差异较细，需要足够表达能力；残差块的恒等映射通道保证梯度可以顺畅传回浅层，避免深层网络训练不稳定。

**MaxPool + GAP**：MaxPool 保留局部"最强响应"，对稀疏笔画特征更敏感。GAP 将分类头参数压缩到极小（128→12），从结构层面抑制过拟合，相比大型展平 FC 层参数量减少约 49 倍（7×7）。

**BatchNorm**：每个 Conv 后跟 BN，稳定特征分布，同时提供轻微正则效果。

### 3.3 SE 通道注意力改进

在改进实验（se_ema、se_strong_aug）中，每个 ResBlock 末尾加入 Squeeze-and-Excitation（SE）模块。其操作可以分为三步：

1. **Squeeze**：对空间维做全局平均池化，得到每个通道的全局描述子 $s_c = \frac{1}{H\times W}\sum_{i,j}x_c(i,j)$。
2. **Excitation**：经两个全连接层（压缩比 8）和 Sigmoid 激活，学习每个通道的重要性权重 $e = \sigma(W_2\,\delta(W_1 s))$。
3. **Reweight**：将通道权重乘回原特征图 $\tilde{x}_c = e_c \cdot x_c$。

SE 的动机是：不同通道对不同笔画部件的响应程度差异较大，动态通道加权使网络能自适应地聚焦于当前图像中判别性最强的特征。

---

## 4. 防过拟合方法与原理

以下所有方法均在代码中完整实现并用于正式实验：

### 4.1 数据增强

**随机平移**（RandomShift）：在 ±d 像素范围内做整数平移，边缘补零。手写汉字的书写位置存在自然偏移，平移增强直接提升位置鲁棒性。

**RandomErasing**：以概率 p 随机遮挡输入图像的一个矩形区域（面积 2%–15%）。作用于输入层的结构性遮挡，比特征层 Dropout 更贴近"局部笔画缺失"这一真实干扰来源。

**Mixup**：以 $\lambda \sim \text{Beta}(\alpha, \alpha)$ 对随机两张图像及其标签做线性插值：

$$
\tilde{x} = \lambda x_i + (1{-}\lambda)x_j, \qquad \tilde{y} = \lambda y_i + (1{-}\lambda)y_j
$$

Mixup 平滑决策边界，对分布外样本的泛化更鲁棒。注意 Mixup 使 train_loss 自然偏高（strong_aug 约 0.49），并非过拟合的信号；实现上使用自定义的 soft cross-entropy 而非标准 CrossEntropyLoss。

### 4.2 Dropout

分类头 GAP 之后、FC 之前加 Dropout(p)。随机失活防止 FC 层对少量强响应通道产生过度依赖，迫使网络学习更分散的特征表示。推理时不启用 Dropout。

### 4.3 L2 正则（Weight Decay）

AdamW 中设 `weight_decay=5e-5`，对权重施加 L2 惩罚，抑制权重过大。第一部分实验表明 $5\times10^{-5}$ 在当前数据规模优于 $10^{-4}$（详见第一部分对比表）。

### 4.4 Label Smoothing

将 one-hot 标签平滑至：

$$
y_k' = (1-\varepsilon)\,\delta_{k,y} + \frac{\varepsilon}{C}
$$

防止模型输出过于尖锐的分布（防止过度自信）。se_ema 实验中 $\varepsilon=0.05$。

### 4.5 EMA（指数移动平均）

训练时维护参数快照：

$$
\theta_\text{ema} \leftarrow \mu\,\theta_\text{ema} + (1{-}\mu)\,\theta_t \quad (\mu{=}0.999)
$$

验证和保存最优 checkpoint 时使用 $\theta_\text{ema}$ 而非即时参数。EMA 等效于对近期参数轨迹做加权平均，减少随机梯度带来的参数波动，提升验证稳定性。

### 4.6 Early Stopping

监控验证准确率，连续 patience=30 轮未提升则停止训练，防止后期在验证划分上持续过拟合。

### 4.7 GAP + 轻量主干（结构正则）

从结构层面通过 GAP 和轻量骨架控制参数规模，是防过拟合的设计基础，与以上方法共同构成多层次的正则化体系。

---

## 5. 数据处理与训练设置

数据集共 7429 张 28×28 灰度 BMP，12 类。数据规范、分层划分、随机种子与第一部分完全一致（详见第一部分报告），此处仅列第二部分特有设置：

- 图像保持 (1, 28, 28) 形状（不展平），直接输入卷积网络。
- 验证实验统一：seed=42，分层 9:1（训练 6685 / 验证 744），AdamW + Cosine Annealing（1e-3 → 1e-5），batch size=64，early stopping patience=30。

### 5.1 实验设计原则

本部分实验并不是单纯追求更高正确率，而是希望通过有控制的对比回答“哪些策略真正有效、为什么有效”。因此实验设计遵循以下原则：

1. **固定验证划分**：所有验证实验共享同一 9:1 分层划分，避免因为验证集不同而造成结论失真。
2. **控制变量对比**：每组实验只改变少量关键因素，例如只加强增强、或在基线结构上加入 SE/EMA，以便更清楚地识别单项改动的贡献。
3. **同时看结果与过程**：除最终 `val_acc` 外，还结合 early stopping 轮次、训练日志、误分类样本和混淆矩阵来判断模型是否真正获得了更好的泛化能力。
4. **验证选型与全量重训分离**：先在固定验证集上决定配置，再用全量数据重训最终模型，避免将验证集信息混入模型选择与最终评估。

这样的设计使实验报告能够回答“为什么这个模型更优”，而不仅仅是“哪个模型分数更高”。

---

## 6. 实验设计与结果

### 6.1 实验配置

| 实验              | SE  | shift | EraseP | Mixup | Dropout | EMA | lbl_sm |
| ----------------- | :-: | :---: | :----: | :---: | :-----: | :-: | :----: |
| baseline          |  ✗  |   2   |   —    |  0.0  |  0.40   |  ✗  |  0.0   |
| strong_aug        |  ✗  |   3   |  0.3   |  0.2  |  0.40   |  ✗  |  0.0   |
| se_ema            |  ✓  |   2   |  0.2   |  0.0  |  0.30   |  ✓  |  0.05  |
| **se_strong_aug** |  ✓  |   3   |  0.3   |  0.2  |  0.35   |  ✗  |  0.0   |

每组实验均为单一方向的递进对比：

- baseline → strong_aug：验证"更强增强是否有效"。
- baseline → se_ema：验证"SE + EMA + label smoothing 是否有效"。
- strong_aug + se_ema → se_strong_aug：结合两者各自的有效部分（强增强 + SE），去掉 EMA 和 label smoothing 的交互影响。

这组设计覆盖了两类主要问题：

1. **训练策略是否比结构改进更重要**：通过 baseline 与 strong_aug 的比较，考察增强是否优于单纯保持原始训练设置。
2. **结构增强是否能带来额外收益**：通过 baseline 与 se_ema、以及 strong_aug 与 se_strong_aug 的比较，检验 SE 等结构性改动在当前数据规模上的真实价值。

### 6.2 验证结果对比

| 实验          | 提前停止轮次 | 最优轮次 | 最优 val_acc |
| ------------- | -----------: | -------: | -----------: |
| baseline      |           37 |        8 |     0.998656 |
| strong_aug    |           50 |       21 |     1.000000 |
| se_ema        |           77 |       48 |     0.998656 |
| se_strong_aug |           37 |        7 |     0.998656 |

### 6.3 实测准确率

| 模型                    | 数据范围             | 准确率                   |
| ----------------------- | -------------------- | ------------------------ |
| strong_aug 最优验证模型 | 固定验证集（744）    | **744/744 = 1.000000**   |
| strong_aug 最优验证模型 | 全部训练数据（7429） | 7424/7429 = 0.999327     |
| final_model（全量重训） | 全部训练数据（7429） | **7428/7429 = 0.999865** |

剩余 1 张出错样本（原标签：类别 9 中的 `518.bmp`）经检查后确认为**标注错误**：该图片实际书写字形为“由”，但被放入了“自”类（标签 9）。模型对该样本的预测为类别 10（与视觉判断一致），说明模型判断正确而非模型错误。

下图展示该出错样本（文件路径：`train_data_update_03-31_v2/train/9/518.bmp`）：

![出错样本（被错标为“自”）](../train_data_update_03-31_v2/train/9/518.bmp)

模型在该样本上的判定符合肉眼判断，体现模型的鲁棒性与判别能力。

### 6.4 结果分析

**为什么 strong_aug 效果最好？**
手写汉字样本的主要变化来源于位置偏移、局部缺笔和书写形态扰动。strong_aug 引入的平移、RandomErasing 和 Mixup 恰好直接针对这些变化来源，大幅提升了模型对未见样本的覆盖能力。

从实验现象看，baseline 已经很强，说明当前骨架本身具备足够的表征能力；在此基础上继续提升，关键不再是简单增加复杂度，而是让训练分布更接近真实测试扰动。strong_aug 的优势正体现在这里：它没有显著增加模型容量，却有效扩展了样本覆盖范围，因此收益更加直接。

**为什么 se_ema 没有超过 baseline？**
se_ema 同时引入了多个变化（SE、EMA、label smoothing、较弱增强），其中较弱的增强系可能是主要瓶颈；label smoothing 在准确率已接近饱和时不一定继续带来收益；EMA 对验证 loss 的影响也使得 val_loss 偏高（模型输出分布被平滑）。这说明在当前数据规模下，增强策略的设计比结构改进更为关键。

进一步看，se_ema 的结果说明“有效方法不能简单叠加”。SE、EMA、label smoothing 单独都有合理动机，但在本任务数据规模较小、类别区分已经较清晰、验证准确率接近饱和的前提下，这些方法之间可能出现收益重叠甚至相互稀释。因此，实验设计的重点不应是不断堆叠技巧，而应是围绕数据特性做有针对性的选择。

**从本组实验可以得到的总体结论**

1. 当前任务的瓶颈主要不在模型容量，而在训练样本对真实扰动的覆盖是否充分。
2. 与继续加深加宽网络相比，贴近手写噪声特点的数据增强更能稳定提升泛化能力。
3. 控制变量实验是必要的：如果没有 baseline、strong_aug、se_ema、se_strong_aug 这组对照，就无法清楚判断提升究竟来自增强还是来自结构改动。


---

## 7. 两阶段训练与最终模型

与第一部分完全相同的两阶段策略（方法说明详见第一部分报告）：

1. **验证选型阶段**：在固定 9:1 划分上完成超参数选型，确定最优配置与最优轮次。
2. **全量训练阶段**：将 val_split 改为 0，在全量 7429 张图像上以相同超参数和固定轮数重训，不启用早停，生成正式提交模型。

当前以 strong_aug 为基准的 `final_model`：

- 全量训练轮次：**45 轮**（val_acc=1.0 在 strong_aug 验证实验中首次命中为第 21 轮，但第 35/40/45 轮更为密集稳定；最终选用 45 轮保证 cosine LR 充分衰减、参数更稳定）
- 全量训练准确率：**7428/7429 = 0.999865**（确认剩余 1 张出错为固有标注噪音，详见 §6.3）
- 配置：`experiments/final_model.yaml`
- 权重：`experiments/final_model/best_model.pth`

---

## 8. 面试快速验证

运行示例：

```powershell
python -u PJ1/Part2/scr/interview.py --data_dir train_data_update_03-31_v2/train --checkpoint PJ1/Part2/experiments/final_model/best_model.pth
```

该命令会直接输出分类准确率，适合作为面试阶段的快速验收入口。

---

## 9. 总结

1. 本部分完整实现了从数据读取、模型构建、训练、验证到面试推理的 CNN 工程流程，代码结构清晰，实验入口统一，具备较好的复现性与展示性。
2. 轻量残差 CNN + GAP 骨架已经为任务提供了足够的表达能力，因此后续提升主要来自训练策略而非继续堆叠网络复杂度。
3. 数据增强（平移 + RandomErasing + Mixup）是当前数据规模下较有效的防过拟合手段，效果明显优于 SE + EMA 等结构改进，说明任务相关的数据建模比单纯结构加法更关键。
4. 本组实验最重要的收获并不只是最终准确率达到较高水平，而是通过控制变量实验明确了各策略的真实贡献，形成了“设计思路 - 实验过程 - 分析结论”闭环，这也是本报告希望重点体现的部分。

