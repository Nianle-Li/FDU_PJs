from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ENTITY_DEFINITIONS: dict[str, dict[str, Any]] = {
    "buildings": {
        "aliases": {
            "建筑名称": "name",
            "名称": "name",
            "建筑类型": "type",
            "类型": "type",
            "所属校区ID": "campus_id",
            "校区ID": "campus_id",
            "campus": "campus_id",
        },
    },
    "facilities": {
        "aliases": {
            "设施名称": "name",
            "名称": "name",
            "设施类型": "type",
            "类型": "type",
            "开放时间": "open_time",
            "所属建筑ID": "building_id",
            "建筑ID": "building_id",
        },
    },
    "activities": {
        "aliases": {
            "活动名称": "name",
            "名称": "name",
            "主办单位": "organizer",
            "主办": "organizer",
            "开始时间": "start_time",
            "结束时间": "end_time",
            "举办设施ID": "facility_id",
            "设施ID": "facility_id",
            "活动简介": "description",
            "简介": "description",
        },
    },
    "query_logs": {
        "aliases": {
            "用户ID": "user_id",
            "查询类别": "query_category",
            "类别": "query_category",
            "查询内容": "query_content",
            "内容": "query_content",
        },
    },
}

ENTITY_ALIASES = {
    "building": "buildings",
    "buildings": "buildings",
    "facility": "facilities",
    "facilities": "facilities",
    "activity": "activities",
    "activities": "activities",
    "query_log": "query_logs",
    "query_logs": "query_logs",
}


class ImportFailure(Exception):
    pass


def normalize_entity(value: str) -> str:
    entity = ENTITY_ALIASES.get(value.strip())
    if entity is None:
        allowed = ", ".join(sorted(ENTITY_DEFINITIONS))
        raise ImportFailure(f"导入对象不支持：{value}。可选：{allowed}")
    return entity


def normalize_header(entity: str, header: str) -> str:
    name = header.strip().lstrip("\ufeff")
    return str(ENTITY_DEFINITIONS[entity]["aliases"].get(name, name)).strip()


def read_csv_rows(entity: str, csv_path: Path) -> list[dict[str, str]]:
    if not csv_path.exists():
        raise ImportFailure(f"CSV 文件不存在：{csv_path}")
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames:
            raise ImportFailure("CSV 文件缺少表头")
        headers = [normalize_header(entity, header) for header in reader.fieldnames]
        rows: list[dict[str, str]] = []
        for raw_row in reader:
            row: dict[str, str] = {}
            for index, header in enumerate(headers):
                value = raw_row.get(reader.fieldnames[index], "")
                text = "" if value is None else str(value).strip()
                if header and text:
                    row[header] = text
            if row:
                rows.append(row)
    if not rows:
        raise ImportFailure("CSV 文件没有可导入的数据行")
    return rows


def chunk_rows(rows: list[dict[str, str]], batch_size: int) -> list[list[dict[str, str]]]:
    return [rows[index : index + batch_size] for index in range(0, len(rows), batch_size)]


def post_import(base_url: str, entity: str, rows: list[dict[str, str]], timeout: int) -> dict[str, Any]:
    payload = json.dumps({"entity": entity, "rows": rows}, ensure_ascii=False).encode("utf-8")
    request = Request(
        f"{base_url.rstrip('/')}/api/import",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise ImportFailure(f"导入接口返回 HTTP {exc.code}：{details}") from exc
    except URLError as exc:
        raise ImportFailure(f"无法连接导入接口：{exc}") from exc


def import_csv(
    entity: str,
    csv_path: Path,
    *,
    base_url: str,
    batch_size: int,
    timeout: int,
    dry_run: bool = False,
) -> tuple[int, int]:
    rows = read_csv_rows(entity, csv_path)
    batches = chunk_rows(rows, batch_size)
    print(f"准备导入 {csv_path} -> {entity}，共 {len(rows)} 行，{len(batches)} 批。")
    if dry_run:
        print("dry-run：仅解析 CSV，不提交到后端。")
        return len(rows), 0

    created_total = 0
    failed_total = 0
    for batch_index, batch in enumerate(batches, start=1):
        result = post_import(base_url, entity, batch, timeout)
        created_count = int(result.get("created_count", 0))
        failed_count = int(result.get("failed_count", 0))
        created_total += created_count
        failed_total += failed_count
        print(f"批次 {batch_index}/{len(batches)}：成功 {created_count} 行，失败 {failed_count} 行")
        for error in result.get("errors", []):
            print(f"  - 第 {error.get('row')} 行：{error.get('error')}")
    print(f"导入完成：成功 {created_total} 行，失败 {failed_total} 行。")
    return created_total, failed_total


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="通过后端 /api/import 批量导入 CSV 文件。")
    parser.add_argument("entity", help="导入对象：buildings、facilities、activities、query_logs")
    parser.add_argument("csv_file", type=Path, help="CSV 文件路径，首行为字段名")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="后端服务地址")
    parser.add_argument("--batch-size", type=int, default=200, help="每批提交行数，最大 200")
    parser.add_argument("--timeout", type=int, default=20, help="请求超时时间，单位秒")
    parser.add_argument("--dry-run", action="store_true", help="只解析 CSV，不提交导入")
    parser.add_argument("--allow-row-errors", action="store_true", help="允许部分行导入失败时仍返回 0")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        entity = normalize_entity(args.entity)
        if args.batch_size < 1 or args.batch_size > 200:
            raise ImportFailure("batch-size 必须在 1 到 200 之间")
        _, failed_count = import_csv(
            entity,
            args.csv_file,
            base_url=args.base_url,
            batch_size=args.batch_size,
            timeout=args.timeout,
            dry_run=args.dry_run,
        )
    except ImportFailure as exc:
        print(f"CSV 导入失败：{exc}", file=sys.stderr)
        return 1
    return 0 if args.allow_row_errors or failed_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
