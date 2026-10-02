-- 002_create_schema_migrations.sql
-- 创建记录已执行迁移版本的表，供简单 runner 使用
BEGIN;

CREATE TABLE IF NOT EXISTS schema_migrations (
  version VARCHAR(255) PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMIT;
