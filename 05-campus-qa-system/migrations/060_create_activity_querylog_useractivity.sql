-- 060_create_activity_querylog_useractivity.sql
BEGIN;

CREATE TABLE IF NOT EXISTS activity (
  activity_id SERIAL PRIMARY KEY,
  name VARCHAR(150) NOT NULL,
  description TEXT NOT NULL DEFAULT '暂无简介',
  start_time TIMESTAMP NOT NULL,
  end_time TIMESTAMP NULL,
  organizer VARCHAR(100) NOT NULL DEFAULT '未填写',
  facility_id INT NOT NULL,
  CONSTRAINT chk_activity_name CHECK (TRIM(name) <> ''),
  CONSTRAINT chk_activity_organizer CHECK (TRIM(organizer) <> ''),
  CONSTRAINT fk_activity_facility FOREIGN KEY (facility_id) REFERENCES facility(facility_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT ux_activity_unique UNIQUE (name, start_time, facility_id),
  CONSTRAINT chk_activity_time CHECK (end_time IS NULL OR end_time >= start_time)
);

CREATE TABLE IF NOT EXISTS query_log (
  log_id SERIAL PRIMARY KEY,
  user_id INT NOT NULL,
  query_category VARCHAR(50) NOT NULL DEFAULT '其他',
  query_content TEXT NOT NULL,
  query_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_querylog_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT chk_querylog_category CHECK (query_category IN ('校区','建筑','设施','课程','教师','活动','用户','统计','其他')),
  CONSTRAINT chk_querylog_content CHECK (TRIM(query_content) <> '')
);

CREATE TABLE IF NOT EXISTS user_activity (
  user_id INT NOT NULL,
  activity_id INT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT '待参加',
  PRIMARY KEY (user_id, activity_id),
  CONSTRAINT fk_useractivity_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_useractivity_activity FOREIGN KEY (activity_id) REFERENCES activity(activity_id) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT chk_useractivity_status CHECK (status IN ('待参加','已签到','已完成','已取消','已缺席'))
);

COMMIT;
