# Scripts

辅助脚本用于最终交付前的本地自测。

## 冒烟测试

启动内置演示数据并完整跑一轮前后端 API：

```bash
python scripts/smoke_test.py --start-demo
```

测试已有后端服务：

```bash
python scripts/smoke_test.py --base-url http://127.0.0.1:8000
```

脚本会验证：

- 后端健康检查
- 前端首页可访问
- 校区、建筑、课程查询
- 建筑、设施、活动新增/修改/删除
- 自然语言查询
- 查询记录写入
- 关键 SQL 示例返回

## CSV 批量导入

通过正在运行的后端服务调用 `/api/import`，把本地 CSV 批量导入到系统中：

```bash
python scripts/import_csv.py buildings path/to/buildings.csv --base-url http://127.0.0.1:8000
```

支持对象：

- `buildings`：字段 `name,type,campus_id`
- `facilities`：字段 `name,type,open_time,building_id`
- `activities`：字段 `name,organizer,start_time,end_time,facility_id,description`
- `query_logs`：字段 `user_id,query_category,query_content`

脚本会按后端限制自动分批提交，每批最多 200 行。CSV 首行可以使用上述英文字段，也可以使用前端导入模板中的中文表头。

常用示例：

```bash
python scripts/import_csv.py buildings .\buildings.csv
python scripts/import_csv.py facilities .\facilities.csv --batch-size 100
python scripts/import_csv.py activities .\activities.csv --dry-run
python scripts/import_csv.py query_logs .\query_logs.csv --allow-row-errors
```
