# Backend

轻量后端服务，负责把前端请求转换为 PostgreSQL 查询和写入操作，并提供阶段演示用的关键 SQL 查询结果。

## 代码结构

后端已从单文件脚本拆分为可测试、可替换的模块：

- `app.py`：最小启动入口，只加载配置并启动服务。
- `fcqa/config.py`：环境变量与运行配置。
- `fcqa/api.py`：纯路由层，负责把 HTTP 方法、路径和请求体映射到仓储操作，可直接单元测试。
- `fcqa/server.py`：`http.server` 托管、CORS、JSON 编解码和静态文件服务。
- `fcqa/repositories/postgres.py`：PostgreSQL 数据访问实现。
- `fcqa/repositories/demo.py`：内置演示数据实现，用于无数据库预览和测试。
- `fcqa/nl_query.py`：自然语言问句到 SQL 查询计划的规则。
- `fcqa/llm_query.py`：DeepSeek 自然语言 SQL 生成、JSON 解析和只读 SQL 校验。
- `fcqa/validation.py`：请求字段清洗与类型校验。
- `tests/`：不依赖 PostgreSQL 的单元测试，覆盖校验、NL 查询、演示仓储和路由层。

## 运行方式

先初始化数据库：

```bash
createdb fcqa
psql -v ON_ERROR_STOP=1 -d fcqa -f db/init.sql
```

安装 PostgreSQL 驱动：

```bash
python -m pip install -r backend/requirements.txt
```

启动服务：

```bash
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/fcqa"
python backend/app.py
```

默认访问地址为 `http://127.0.0.1:8000`。后端会同时托管 `frontend/` 静态页面。

## DeepSeek 自然语言查询

默认自然语言查询使用 `fcqa/nl_query.py` 中的规则解析。若要启用 DeepSeek 生成 SQL，复制 `.env.example` 为 `.env`，填写：

```dotenv
FCQA_LLM_MODE=1
DEEPSEEK_API_KEY=你的 DeepSeek API Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
FCQA_LLM_TIMEOUT_SECONDS=30
FCQA_LLM_MAX_ROWS=50
```

启用后，`POST /api/nl-query` 会优先让 DeepSeek 根据内置表结构生成一条 PostgreSQL `SELECT` 查询。后端会拒绝写入、多语句和管理类 SQL，并在只读事务中执行；若未配置 token、模型调用失败或 SQL 校验失败，会自动回退到原有规则解析。

## Docker 部署

在仓库根目录执行：

```bash
docker compose up --build
```

Compose 会启动两个服务：

- `db`：PostgreSQL 16，首次启动时执行 `db/init.sql` 并导入初始测试数据。
- `backend`：Python 后端，容器内使用 `DATABASE_URL=postgresql://postgres:postgres@db:5432/fcqa` 连接数据库，并监听 `0.0.0.0:8000`。

启动后访问 `http://localhost:8000`。如果需要清空并重新初始化数据库，执行：

```bash
docker compose down -v
docker compose up --build
```

如果当前机器暂时没有 PostgreSQL，可使用内置演示数据预览前后端交互：

```powershell
$env:FCQA_DEMO_MODE="1"
python backend/app.py
```

演示模式只用于界面预览；正式联调请使用 PostgreSQL。

## 测试

快速单元测试：

```bash
python -m unittest discover -s backend/tests
```

演示模式端到端 smoke test：

```bash
python scripts/smoke_test.py --start-demo --port 8899
```

CSV 批量导入命令：

```bash
python scripts/import_csv.py buildings path/to/buildings.csv --base-url http://127.0.0.1:8000
```

CLI 会复用后端 `/api/import`，支持 `buildings`、`facilities`、`activities` 和 `query_logs`，并按每批最多 200 行提交。

## 主要 API

- `GET /api/health`：服务与数据库连接状态
- `GET /api/users`：用户列表，用于用户端身份选择
- `GET /api/users/{user_id}/reservations`：查看指定用户的活动预约
- `GET /api/campuses`：校区查询
- `GET/POST/PUT/DELETE /api/buildings`：建筑查询与维护
- `GET/POST/PUT/DELETE /api/facilities`：设施查询与维护
- `GET /api/courses`：课程、教师、排课综合查询
- `GET/POST/PUT/DELETE /api/activities`：活动查询与维护
- `POST /api/activities/{activity_id}/reserve`：预约活动
- `DELETE /api/activities/{activity_id}/reserve/{user_id}`：取消活动预约
- `POST /api/query-log`：写入用户查询记录
- `GET /api/query-logs`：查询历史记录
- `GET /api/insights/popular-queries`：热门查询类别
- `GET /api/insights/popular-activities`：热门活动
- `POST /api/nl-query`：自然语言问句解析为 SQL 并返回查询结果
- `GET /api/sql-examples`：执行并展示关键 SQL 查询效果
