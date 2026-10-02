-- 010_create_user.sql
BEGIN;

CREATE TABLE IF NOT EXISTS users (
  user_id SERIAL PRIMARY KEY,
  name VARCHAR(50) NOT NULL CHECK (TRIM(name) <> ''),
  department VARCHAR(100) NOT NULL DEFAULT '未填写' CHECK (TRIM(department) <> '')
);

COMMIT;
