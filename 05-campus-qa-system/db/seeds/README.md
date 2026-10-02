# 种子数据

存放用于初始化和演示的数据（CSV 或 SQL 插入）。
本目录当前以面向演示的确定性 CSV 和一份轻量 SQL 初始数据为主，便于演示、截图与重复导入。

## 内容

- `001_initial_data.sql`：可直接通过 `psql` 导入的初始测试数据，覆盖用户、教师、学生、校区、建筑、设施、课程、排课、活动、用户活动参与和查询记录。
- `import_csv.sql`：可直接通过 `psql` 导入 `csv/` 下演示数据的脚本，包含清表、CSV 导入和序列重置。
- `csv/`：可直接导入的演示 CSV 文件。

所有在 PostgreSQL 中使用 `SERIAL` 的表均使用显式 ID 填充，以保证关联、截图与重复导入时的一致性。

## 快速导入

仓库根目录下可执行完整初始化入口：

```bash
psql -P pager=off -v ON_ERROR_STOP=1 -d fcqa -f db/init.sql
```

如果数据库表结构已经存在，也可以单独导入 SQL 测试数据：

```bash
psql -P pager=off -v ON_ERROR_STOP=1 -d fcqa -f db/seeds/001_initial_data.sql
```

如果需要导入 CSV 演示数据，请从仓库根目录执行：

```bash
psql -P pager=off -v ON_ERROR_STOP=1 -d fcqa -f db/init_csv.sql
```

`db/init_csv.sql` 会先执行建表脚本，再调用 `db/seeds/import_csv.sql`；`import_csv.sql` 会按外键依赖顺序导入 CSV，并把所有 `SERIAL` 序列重置到当前最大 ID。

## 数据集范围

- SQL 测试数据包含用户、教师、学生、校区、建筑、设施、课程、排课、活动、用户活动参与和查询记录。
- CSV 演示数据规模更大，便于演示、截图和后续批量导入扩展。
- 校区范围：仅包含 邯郸校区、江湾校区、枫林校区、张江校区。
- 空间数据：建筑与设施使用真实或近似真实的校区命名风格以便展示。
- 用户数据：姓名为示例生成，学院/专业映射保持语义合理。
- 课程数据：课程编号、章节、开课、排课与授课教师互相参照且可直接导入。
- 活动数据：活动名称、主办方、场地与用户参与记录内部一致。

## CSV 当前规模

| 表名 | 行数 |
| :--- | ---: |
| campus | 4 |
| building | 15 |
| facility | 37 |
| users | 50 |
| teacher | 12 |
| student | 38 |
| course | 20 |
| course_section | 25 |
| course_offering | 30 |
| course_offering_schedule | 60 |
| course_offering_teacher | 33 |
| activity | 15 |
| user_activity | 60 |
| query_log | 100 |

## 导入顺序

1. campus
2. building
3. facility
4. users
5. teacher
6. student
7. course
8. course_section
9. course_offering
10. course_offering_schedule
11. course_offering_teacher
12. activity
13. user_activity
14. query_log

## 说明

- 物理的用户基础表为 `users`，不是 `user`。
- `query_log.user_id` 与 `user_activity.user_id` 均引用 `users(user_id)`。
- `course_offering_schedule.week_type` 仅允许值：`每周`、`单周`、`双周`。
- `building.type` 与 `facility.type` 必须在 migrations 中声明的枚举值范围内。
- 该数据面向演示展示，不作为官方校园名录或权威数据使用。
