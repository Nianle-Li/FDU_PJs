-- 070_create_indexes.sql
-- 建议在表创建完后执行。索引面向基础查询、关联查询、统计查询和关键词检索。
BEGIN;

-- 关键词检索辅助列与 GIN 索引。
-- 中文短文本查询主要依赖 trigram/ILIKE；tsvector 保留给后续英文或分词方案扩展。
ALTER TABLE activity
  ADD COLUMN IF NOT EXISTS description_tsv tsvector GENERATED ALWAYS AS (
    to_tsvector('simple', coalesce(name,'') || ' ' || coalesce(description,''))
  ) STORED;
CREATE INDEX IF NOT EXISTS idx_activity_description_tsv ON activity USING GIN (description_tsv);

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS name_tsv tsvector GENERATED ALWAYS AS (
    to_tsvector('simple', coalesce(name,''))
  ) STORED;
CREATE INDEX IF NOT EXISTS idx_users_name_tsv ON users USING GIN (name_tsv);

ALTER TABLE course
  ADD COLUMN IF NOT EXISTS name_tsv tsvector GENERATED ALWAYS AS (
    to_tsvector('simple', coalesce(name,''))
  ) STORED;
CREATE INDEX IF NOT EXISTS idx_course_name_tsv ON course USING GIN (name_tsv);

ALTER TABLE facility
  ADD COLUMN IF NOT EXISTS name_tsv tsvector GENERATED ALWAYS AS (
    to_tsvector('simple', coalesce(name,''))
  ) STORED;
CREATE INDEX IF NOT EXISTS idx_facility_name_tsv ON facility USING GIN (name_tsv);

ALTER TABLE query_log
  ADD COLUMN IF NOT EXISTS content_tsv tsvector GENERATED ALWAYS AS (
    to_tsvector('simple', coalesce(query_content,''))
  ) STORED;
CREATE INDEX IF NOT EXISTS idx_querylog_content_tsv ON query_log USING GIN (content_tsv);

-- trigram 索引用于名称、活动、查询内容的模糊/相似搜索。
CREATE INDEX IF NOT EXISTS idx_user_name_trgm ON users USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_activity_name_trgm ON activity USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_querylog_content_trgm ON query_log USING gin (query_content gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_course_name_trgm ON course USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_facility_name_trgm ON facility USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_building_name_trgm ON building USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_campus_name_trgm ON campus USING gin (name gin_trgm_ops);

-- 外键与高频 JOIN 索引。
CREATE INDEX IF NOT EXISTS idx_facility_building ON facility (building_id);
CREATE INDEX IF NOT EXISTS idx_building_campus ON building (campus_id);
CREATE INDEX IF NOT EXISTS idx_course_section_master ON course_section (course_master_code);
CREATE INDEX IF NOT EXISTS idx_course_offering_course_code ON course_offering (course_code);
CREATE INDEX IF NOT EXISTS idx_schedule_facility_time
  ON course_offering_schedule (facility_id, day_of_week, start_period, end_period, week_type);
CREATE INDEX IF NOT EXISTS idx_offering_teacher_teacher
  ON course_offering_teacher (teacher_id, offering_id);
CREATE INDEX IF NOT EXISTS idx_activity_facility_start
  ON activity (facility_id, start_time);
CREATE INDEX IF NOT EXISTS idx_querylog_user_time
  ON query_log (user_id, query_time DESC);
CREATE INDEX IF NOT EXISTS idx_useractivity_activity_status
  ON user_activity (activity_id, status);

-- 筛选、排序和统计场景索引。
CREATE INDEX IF NOT EXISTS idx_building_type ON building (type);
CREATE INDEX IF NOT EXISTS idx_facility_type ON facility (type);
CREATE INDEX IF NOT EXISTS idx_course_offering_semester ON course_offering (semester);
CREATE INDEX IF NOT EXISTS idx_activity_start_time ON activity (start_time);
CREATE INDEX IF NOT EXISTS idx_querylog_category_time ON query_log (query_category, query_time DESC);
CREATE INDEX IF NOT EXISTS idx_useractivity_user_status ON user_activity (user_id, status);

COMMIT;
