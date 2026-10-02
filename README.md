# FDU_PJs | 复旦大学计院本科课程项目合集

**复旦大学计算与智能创新学院 · 本科课程项目归档仓库**

本仓库汇总本人本科阶段的核心课程项目，内容包含源码、实验报告、设计文档与演示材料，用于课程复盘与技术展示。项目彼此独立，可单独查阅与运行。

> 课程名称后的 `H` 为荣誉（Honors）课程批次标识。

---

## 📚 项目清单

| 序号 | 目录 | 课程名称 | 课程代码 | 技术栈 | 一句话简介 |
|:---:|:---|:---|:---|:---|:---|
| 00 | [`00-maze`](./00-maze) | 程序设计 | CS10004 | C（Windows 控制台） | 控制台迷宫寻宝游戏 |
| 01 | [`01-board-games`](./01-board-games) | 面向对象程序设计 | SOFT130059 | Java 17 / JavaFX / Maven | 支持三种棋类的双端（控制台 + GUI）棋类对弈系统 |
| 02 | [`02-dungeon-project`](./02-dungeon-project) | 数据结构 | CS20009 | Python / Flask / 原生 JS | 图 + 树结构的地下城探险游戏，含路径规划与可视化 |
| 03 | [`03-dcd`](./03-dcd) | 数字逻辑与部件设计 | CS20008 | Verilog / Vivado / Nexys4 DDR | 从组合逻辑、ALU、状态机到单周期 RISC-V CPU 的实验 |
| 04 | [`04-artificial-intelligence`](./04-artificial-intelligence) | 人工智能 `H` | CS30057 | Python / PyTorch / CRF | 手写 MLP 与 ResNet 图像分类 + 中英文命名实体识别三任务 |
| 05 | [`05-campus-qa-system`](./05-campus-qa-system) | 数据库设计 `H` | CS20021 | PostgreSQL / Docker / Python | 校园信息问答系统：关系建模、NL2SQL 与 LLM 增强查询 |

---

## 📂 项目详情

### 00 · `00-maze` — 迷宫寻宝（C / Windows 控制台）

> 课程：程序设计（CS10004）｜源码：[`00-maze/scr/`](./00-maze/scr)｜说明：[`readme.pdf`](./00-maze/readme.pdf)

三层模块划分：`ui`（菜单与地图渲染）、`game_logic`（移动与局面状态）、`file`（地图读写与存档）。

- **关卡数据**：内置三张地图 `level-1 ordinary journey` / `level-2 grand journey` / `level-3 devil's journey`，地图上限 21×21。
- **核心玩法**：WASD 移动寻路、收集宝藏、统计步数消耗，并可切换多种游戏模式。
- **悔棋 / 重做**：用双向链表 `Op` 记录每一步操作，支持 `undo` / `redo`。
- **存档续玩**：`save_game_progress` / `load_game_progress` 可将地图、步数、宝藏进度与上次游玩时间落盘，启动时自动提示是否恢复历史记录。
- **运行方式**：源码依赖 `conio.h` 与 `windows.h`，需在 Windows 下编译（MinGW / MSVC）；仓库同时保留了可直接运行的 `build/main.exe`。

### 01 · `01-board-games` — 棋类对弈系统（Java 17 / JavaFX）

> 课程：面向对象程序设计（SOFT130059）｜工程：[`01-board-games/pj/`](./01-board-games/pj)｜说明：[`Readme.pdf`](./01-board-games/Readme.pdf)｜UML：[`attachment/uml.svg`](./01-board-games/attachment/uml.svg)

Maven 工程（`sourceDirectory` 指向 `lab`，JavaFX 17.0.2），内建三种棋类：**和平棋**、**黑白棋**、**五子棋**，由 `GameFactory` 以注册式工厂统一管理，扩展新棋类只需注册一个构造器。

- **领域层（`domain`）**：`Board` / `Piece` / `PieceColor` / `Location` / `Direction` 抽象棋盘与落子，`Game` 及三个具体棋类实现规则与胜负判定。
- **控制台端（`console`）**：命令模式（`NewGame` / `SelectGame` / `PlacePiece` / `UseBomb` / `Pass` / `Playback` / `Quit`），以 `PlayGround` 同时挂载多局并与两名 `Player` 绑定，支持命令行 replay 回放。
- **桌面端（`gui`）**：JavaFX + FXML（`main.fxml` / `MainController` / `BoardView` / `GameListView`），并有 `GameState` / `GameStateManager` / `SerializableGame` 负责对局状态管理与序列化存档。

### 02 · `02-dungeon-project` — 地下城探险（Flask + 原生前端）

> 课程：数据结构（CS20009）｜后端：[`backend/`](./02-dungeon-project/backend)｜前端：[`frontend/`](./02-dungeon-project/frontend)｜说明：[`Readme.pdf`](./02-dungeon-project/Readme.pdf)

前后端分离的地下城探险游戏，把课程中的图、树两类数据结构落到实际玩法里。后端仅依赖 `flask==2.3.0` 与 `flask-cors==4.0.0`。

- **图（`graph.py`）**：`DungeonGraph` 维护房间与通道，对外提供最短路径与按代价排序的多条候选路径接口，对应 `/api/path/shortest`、`/api/path/all-ranked`。
- **树（`tree.py`）**：`TreasureTree` / `TreasureTreeNode` 组织宝藏层级，供 `/api/treasure/tree` 查询。
- **玩法与状态**：随机出牌匣房间连通布局、怪物与 Boss 状态、玩家移动、稀疏 `AdventureLog` 探险日志与游戏重置。
- **前端**：原生 JS + HTML + Bootstrap 5，借助 `vis-network` 渲染 Room 拓扑图，配合 `map_renderer` / `path_controller` / `treasure_viewer` / `log_viewer` 等模块，并支持 `html2canvas` 导出地图快照。
- **启动**：`pip install -r requirements.txt` 后运行 `backend/app.py`，访问 `http://localhost:5000/`。

### 03 · `03-dcd` — 数字逻辑与部件设计（Verilog / Vivado）

> 课程：数字逻辑与部件设计（CS20008）｜工程：[`03-dcd/Vivado/`](./03-dcd/Vivado)

Vivado 工程按实验递进组织，源码与 testbench 一一配套，并附带实验报告。

| 目录 | 内容 |
|:---|:---|
| `lab1/` | 基础组合逻辑，`srcs/` 两个设计 + `sim/` 两个 testbench，附 `Lab1_实验报告.pdf` |
| `lab2/` | 算术逻辑单元 `ALU.v` 与 `ALU_tb.v`，附实验报告 |
| `lab3/` | 自动售货机状态机 `vending.v` / `tb_vending.v`，含 Nexys4 DDR 引脚约束 `Nexys4DDR_Master.xdc` 与开发板资料 |
| `pj/` | 课程大作业：**单周期 RISC-V CPU** |

大作业 `pj/pj/` 为一个**单周期 RISC-V CPU**（`cpu_top.v` 顶层），子模块包括 `pc`、`pm`（程序存储器，配套 `pm_init.hex` 测试程序）、`decoder`、`regfile`、`alu`、`imm_gen`、`dm`，并编写 `tb/tb_cpu.v` 仿真；另附《项目报告》《波形图具体展示与说明》《RISC-V 测试指令》等文档。

### 04 · `04-artificial-intelligence` — 人工智能 `H`（PyTorch）

> 课程：人工智能 H（CS30057）｜依赖：`PJ1/requirements.txt`、`PJ2/requirements.txt`

**PJ1：从手写网络到自定义卷积网络**（[`PJ1/`](./04-artificial-intelligence/PJ1)，含 [`README.md`](./04-artificial-intelligence/PJ1/README.md) 与两篇实验报告）

- **Part1（纯 NumPy）**：不依赖深度学习框架，手写多层感知机、损失函数、反向传播与优化器，完成 `sin(x)` 回归与手写汉字分类，并用 `grad_check` 做梯度校验。
- **Part2（PyTorch）**：自行搭建带残差块与 SE 注意力（`SEBlock`）的 CNN（`ResNetCNN`），围绕数据增强（`RandomShift` / `RandomErasing` / `Mixup`）、正则化（`Dropout` / weight decay / label smoothing）与 EMA、早停等策略做对比实验。
- **已实现 Bonus**：防过拟合的系统性实验与结论。

**PJ2：中英文命名实体识别**（[`PJ2/`](./04-artificial-intelligence/PJ2)，含 [`PJ2 简要说明.md`](./04-artificial-intelligence/PJ2/PJ2%20简要说明.md) 与三份实验报告）

围绕同一套中英文 NER 数据集的三个递进任务，评分由 `PJ2/NER/check.py`（token-level micro F1）统一评测：

| 任务 | 方法 | 关键实现 |
|:---|:---|:---|
| 任务一 | 手写 HMM | `hmm.py` + `decoder.py`（Viterbi）+ `gazetteer.py` 词典特征 + `constraints.py` 合法转移约束 |
| 任务二 | CRF | `sklearn-crfsuite` / `python-crfsuite` 判别式序列建模，并附 Bonus 模板特征方案 |
| 任务三 | Transformer + CRF | CRF 手写（`crf.py`），实验配置同时覆盖 BERT 版与 vanilla 版（`experiments/*.yaml`） |

### 05 · `05-campus-qa-system` — 校园问答系统（PostgreSQL / Docker）

> 课程：数据库设计 H（CS20021）｜入口：[`README.md`](./05-campus-qa-system/README.md)｜`docker compose up` 一键启动 db + backend 两个服务

一个完整的校园信息问答系统，覆盖「数据库设计 → 后端服务 → 前端交互 → 部署」全流程。

- **数据库**：PostgreSQL 16。`db/schema.sql` 定义校园、建筑、设施、师生、课程、开课与课表、活动、查询日志等表；`migrations/001~070` 为可复现的版本化迁移；`db/seeds/csv/` 提供种子数据与 `scripts/import_csv.py` 导入脚本。
- **后端**（`backend/`，依赖 `psycopg[binary]`）：自研轻量级服务框架 `fcqa/`，含 `nl_query.py`（自然语言 → SQL）、`llm_query.py`（可选 DeepSeek 大模型增强）、`validation.py`、`privacy.py`、`sql_examples.py`、`repositories/`（Postgres 与 Demo 两种数据源），并配有 pytest 测试。
- **前端**（`frontend/`）：原生 HTML / CSS / JS，含用户问答页与 `admin.html` 管理页。
- **文档**：`docs/` 收录需求分析、完整表结构、关系模式、规范性分析、约束设计、导入与查询、测试验收、功能演示共 8 篇设计文档，`design/` 另有数据流程活动图（`.drawio`）。

---

## 🗂 仓库结构

```
FDU_PJs/
├── 00-maze/                      # C 迷宫寻宝：scr/(源码) + build/(地图与可执行文件)
├── 01-board-games/               # Java 棋类：pj/(Maven 工程) + attachment/(UML)
├── 02-dungeon-project/           # 地下城游戏：backend/(Flask) + frontend/(原生 JS)
├── 03-dcd/                       # 数字逻辑：Vivado/{lab1,lab2,lab3,pj}
├── 04-artificial-intelligence/   # 人工智能：PJ1/(图像分类) + PJ2/(NER)
└── 05-campus-qa-system/          # 校园问答系统：backend/ db/ docs/ frontend/ migrations/ scripts/
```

## 📌 仓库说明

- **子项目彼此独立**：各目录为单独课程工程，运行环境依赖与启动步骤请以该目录下的说明为准 —— 其中 `00-maze`、`01-board-games`、`02-dungeon-project` 的说明为目录下的 PDF 文档；`04-artificial-intelligence` 见 [`PJ1/README.md`](./04-artificial-intelligence/PJ1/README.md) 与 [`PJ2/PJ2 简要说明.md`](./04-artificial-intelligence/PJ2/PJ2%20简要说明.md)；`05-campus-qa-system` 见其 [`README.md`](./05-campus-qa-system/README.md)；`03-dcd` 的实验报告存放于各 lab / pj 目录内。
- **文件取舍**：整体以源码、设计文档与配置为主，模型权重、大规模数据集、日志与部分编译产物未随仓库一并归档。
- **维护状态**：课程项目已结课归档，代码基本不再更新，仅供学习参考。

---

## ⚠️ 声明

本仓库所有内容仅用于个人学习归档、课程复盘与技术展示。**严禁抄袭、盗用、商用，或直接作为课程作业提交。**

未经作者书面许可，不得将本仓库内容用于任何商业用途。
