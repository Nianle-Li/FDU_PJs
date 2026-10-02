# Database

本目录保存数据库实现交付物，目标数据库为 PostgreSQL 16 兼容版本。

## 文件说明

- `schema_core.sql`：核心建表 SQL 快照，便于课程提交时快速查看表结构。
- `schema.sql`：按顺序执行 `migrations/` 中的扩展、建表和索引脚本。
- `init.sql`：完整初始化入口，执行 `schema.sql` 后继续导入初始测试数据。
- `init_csv.sql`：CSV 版完整初始化入口，执行 `schema.sql` 后导入 `seeds/csv/` 并重置序列。
- `seeds/001_initial_data.sql`：初始测试数据，覆盖基础查询、关联查询和统计查询场景。
- `seeds/import_csv.sql`：CSV 批量导入脚本，按外键顺序清空并导入演示数据。
- `verify_basic_queries.sql`：基础验收查询，用于确认导入后可支撑需求文档中的典型场景。

## 创建数据库并导入数据

使用 Docker Compose 可直接启动 PostgreSQL 16，并在首次创建数据卷时自动执行 `db/init.sql`：

```bash
docker compose up -d db
```

查看数据库状态：

```bash
docker compose ps
```

运行基础验收查询：

```bash
docker compose exec db psql -P pager=off -v ON_ERROR_STOP=1 -U postgres -d fcqa -f /opt/fcqa/db/verify_basic_queries.sql
```

如需完全重建数据库和初始数据，可删除数据卷后重新启动：

```bash
docker compose down -v
docker compose up -d db
```

在本机 PostgreSQL 中创建数据库后，从仓库根目录执行：

```bash
createdb fcqa
psql -P pager=off -v ON_ERROR_STOP=1 -d fcqa -f db/init.sql
```

如需导入规模更大的 CSV 演示数据，从仓库根目录执行 CSV 初始化入口。该入口会串联建表、CSV 导入和序列重置：

```bash
createdb fcqa
psql -P pager=off -v ON_ERROR_STOP=1 -d fcqa -f db/init_csv.sql
```

Docker Compose 环境下可在容器内以 `/opt/fcqa` 为工作目录运行同一个入口：

```bash
docker compose exec -w /opt/fcqa db psql -P pager=off -v ON_ERROR_STOP=1 -U postgres -d fcqa -f db/init_csv.sql
```

如果只需要创建表和索引，不导入测试数据：

```bash
psql -P pager=off -v ON_ERROR_STOP=1 -d fcqa -f db/schema.sql
```

导入完成后可运行基础验收查询：

```bash
psql -P pager=off -v ON_ERROR_STOP=1 -d fcqa -f db/verify_basic_queries.sql
```

CSV 导入后的行数、序列检查和示例查询结果见 [5-数据库导入与查询说明.md](../docs/5-数据库导入与查询说明.md)。

## 约束与索引

主要约束由建表脚本直接声明，包括主键、共享主键、外键、唯一约束、非空、默认值和 `CHECK` 枚举/时间范围约束。详细说明见 [docs/4-主要约束设计说明.md](../docs/4-主要约束设计说明.md)。

索引集中在 `migrations/070_create_indexes.sql`，覆盖外键 JOIN、课程与活动筛选、用户查询记录统计、活动热度统计、名称模糊检索和文本检索辅助列。
