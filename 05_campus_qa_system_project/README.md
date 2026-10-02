# 复旦校园百事通

> fudan-campus-qa-system · 数据库设计课程项目

复旦校园百事通问答系统，数据库设计课程项目。面向复旦校园场景，提供一站式问答与信息管理服务。

**主要功能**

- 自然语言问答：支持规则解析与 DeepSeek LLM 两种模式，将中文问句转为 SQL 并返回结果
- 校园信息浏览：校区、建筑、设施多层次展示，支持按校区筛选
- 活动管理与预约：活动列表、报名、取消；热门活动统计
- 我的行程：按用户查询已预约的活动
- 管理员工作台：建筑/设施/活动的增删改查、CSV 批量导入、查询日志与热门查询统计
- 关键 SQL 示例展示：内置多组典型多表关联查询


## 技术栈

- 数据库：PostgreSQL 16
- 后端：Python 标准库 HTTP 服务，支持 PostgreSQL 正式模式与内置 Demo 模式
- 前端：静态 HTML/CSS/JavaScript，用户端与管理员端

## 数据库概况

数据库为 PostgreSQL 16，包含 14 张核心表，覆盖用户、校区、建筑、设施、课程、活动及查询日志等业务域：

| 业务域 | 主要表 |
| :----- | :----- |
| 用户 | `users`、`teacher`、`student` |
| 校区与建筑 | `campus`、`building`、`facility` |
| 课程 | `course`、`course_section`、`course_offering`、`course_offering_schedule`、`course_offering_teacher` |
| 活动与预约 | `activity`、`user_activity` |
| 查询日志 | `query_log` |

- ER 图：[design/ER.png](design/ER.png)（源文件 [design/ER.drawio](design/ER.drawio)）
- 建表脚本：[migrations/](migrations/)（按功能模块拆分）
- 初始化入口：[db/init.sql](db/init.sql)（SQL 种子数据）/ [db/init_csv.sql](db/init_csv.sql)（CSV 大数据集）

## 快速运行

### Docker 一键启动

在仓库根目录执行：

```bash
docker compose up --build
```

首次启动会创建 PostgreSQL 16 数据库，执行 [db/init.sql](db/init.sql) 并导入初始数据。后端容器连接 `db:5432/fcqa`，并托管 [frontend](frontend) 静态页面。

浏览器访问：

```text
http://localhost:8000
```

### 本地 Demo 模式

如果当前机器没有 PostgreSQL，可用内置演示数据预览前后端交互：

```powershell
python -m pip install -r backend/requirements.txt
$env:FCQA_DEMO_MODE="1"
python backend/app.py
```

浏览器访问：

```text
http://127.0.0.1:8000
```

### 本地 PostgreSQL 模式

初始化数据库并导入初始数据：

```bash
createdb fcqa
psql -P pager=off -v ON_ERROR_STOP=1 -d fcqa -f db/init.sql
```

安装后端依赖并启动服务（PowerShell）：

```powershell
python -m pip install -r backend/requirements.txt
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/fcqa"
python backend/app.py
```

浏览器访问 `http://127.0.0.1:8000`。如需展示更大规模的 CSV 演示数据，将 `db/init.sql` 替换为 `db/init_csv.sql` 初始化数据库。

## 测试

后端单元测试：

```bash
python -m unittest discover -s backend/tests
```

Demo 模式冒烟测试：

```bash
python scripts/smoke_test.py --start-demo
```

## 项目文档

| 文档                                                                 | 说明                                       |
| :------------------------------------------------------------------- | :----------------------------------------- |
| [docs/0-需求分析说明书.md](docs/0-需求分析说明书.md)                 | 系统需求范围、业务规则和验收目标           |
| [docs/1-完整表结构说明.md](docs/1-完整表结构说明.md)                 | 数据库表结构、字段定义和表级约束           |
| [docs/2-关系模式说明.md](docs/2-关系模式说明.md)                     | 关系模式、主键外键设计和建模依据           |
| [docs/3-规范性分析说明.md](docs/3-规范性分析说明.md)                 | 第一范式到 BCNF 的规范化分析               |
| [docs/4-主要约束设计说明.md](docs/4-主要约束设计说明.md)             | 数据库约束和索引策略                       |
| [docs/5-数据库导入与查询说明.md](docs/5-数据库导入与查询说明.md)     | 数据库初始化、CSV 导入、查询展示和写入联调 |
| [docs/6-系统测试与验收说明.md](docs/6-系统测试与验收说明.md)         | 自动化测试、数据库验证和人工验收检查项     |
| [docs/7-系统功能介绍与演示说明.md](docs/7-系统功能介绍与演示说明.md) | **系统功能全景介绍与演示路径（含演示图）**            |
## 仓库目录

| 目录                       | 说明                                                         |
| :------------------------- | :----------------------------------------------------------- |
| [backend/](backend/)       | 后端服务、API 路由、数据仓储实现和单元测试                   |
| [frontend/](frontend/)     | 用户端和管理员端静态页面                                     |
| [db/](db/)                 | 建表脚本、初始化入口、验收查询和种子数据                     |
| [migrations/](migrations/) | 按功能模块拆分的迁移脚本                                     |
| [docs/](docs/)             | 需求分析、关系模式、规范化分析、约束设计、测试验收与演示文档 |
| [design/](design/)         | ER 图与数据流活动图                                          |
| [scripts/](scripts/)       | CSV 批量导入与冒烟测试脚本                                   |
