-- 核心建表 SQL 快照（Postgres 语法）

BEGIN;

-- 用户表
CREATE TABLE IF NOT EXISTS users (
  user_id SERIAL PRIMARY KEY,
  name VARCHAR(50) NOT NULL CHECK (TRIM(name) <> ''),
  department VARCHAR(100) NOT NULL DEFAULT '未填写' CHECK (TRIM(department) <> '')
);

-- 教师/学生（共享主键）
CREATE TABLE IF NOT EXISTS teacher (
  user_id INT PRIMARY KEY REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE CASCADE,
  title VARCHAR(100) NOT NULL DEFAULT '未定' CHECK (TRIM(title) <> '')
);

CREATE TABLE IF NOT EXISTS student (
  user_id INT PRIMARY KEY REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE CASCADE,
  major VARCHAR(100) NOT NULL DEFAULT '未填写' CHECK (TRIM(major) <> '')
);

-- 校区、建筑、设施
CREATE TABLE IF NOT EXISTS campus (
  campus_id SERIAL PRIMARY KEY,
  name VARCHAR(50) NOT NULL,
  address VARCHAR(255) NOT NULL DEFAULT '未填写',
  CONSTRAINT ux_campus_name UNIQUE (name),
  CONSTRAINT chk_campus_name CHECK (TRIM(name) <> ''),
  CONSTRAINT chk_campus_address CHECK (TRIM(address) <> '')
);

CREATE TABLE IF NOT EXISTS building (
  building_id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  type VARCHAR(50) NOT NULL DEFAULT '其他',
  campus_id INT NOT NULL,
  CONSTRAINT chk_building_name CHECK (TRIM(name) <> ''),
  CONSTRAINT chk_building_type CHECK (type IN ('教学楼','图书馆','宿舍','食堂','体育场馆','办公楼','实验楼','医院','综合楼','其他')),
  CONSTRAINT fk_building_campus FOREIGN KEY (campus_id) REFERENCES campus(campus_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT ux_building_campus_name UNIQUE (campus_id, name)
);

CREATE TABLE IF NOT EXISTS facility (
  facility_id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  type VARCHAR(50) NOT NULL DEFAULT '其他',
  open_time VARCHAR(100) NOT NULL DEFAULT '以现场公告为准',
  building_id INT NOT NULL,
  CONSTRAINT chk_facility_name CHECK (TRIM(name) <> ''),
  CONSTRAINT chk_facility_type CHECK (type IN ('教室','自习室','会议室','实验室','报告厅','图书阅览室','体育设施','餐饮服务','办公服务','其他')),
  CONSTRAINT chk_facility_open_time CHECK (TRIM(open_time) <> ''),
  CONSTRAINT fk_facility_building FOREIGN KEY (building_id) REFERENCES building(building_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT ux_facility_building_name UNIQUE (building_id, name)
);

-- 课程相关
CREATE TABLE IF NOT EXISTS course (
  course_master_code VARCHAR(20) PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  CONSTRAINT chk_course_master_code CHECK (TRIM(course_master_code) <> ''),
  CONSTRAINT chk_course_name CHECK (TRIM(name) <> '')
);

CREATE TABLE IF NOT EXISTS course_section (
  course_code VARCHAR(30) PRIMARY KEY,
  course_master_code VARCHAR(20) NOT NULL,
  CONSTRAINT chk_course_code_not_empty CHECK (TRIM(course_code) <> ''),
  CONSTRAINT chk_course_code_format CHECK (course_code LIKE course_master_code || '.%'),
  CONSTRAINT fk_course_section_master FOREIGN KEY (course_master_code) REFERENCES course(course_master_code) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS course_offering (
  offering_id SERIAL PRIMARY KEY,
  course_code VARCHAR(30) NOT NULL,
  semester VARCHAR(50) NOT NULL,
  CONSTRAINT chk_course_offering_semester CHECK (TRIM(semester) <> ''),
  CONSTRAINT fk_course_offering_section FOREIGN KEY (course_code) REFERENCES course_section(course_code) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS course_offering_schedule (
  offering_id INT NOT NULL,
  day_of_week VARCHAR(10) NOT NULL,
  start_period INT NOT NULL,
  end_period INT NOT NULL,
  week_type VARCHAR(20) NOT NULL DEFAULT '每周',
  facility_id INT NOT NULL,
  PRIMARY KEY (offering_id, day_of_week, start_period, end_period, week_type),
  CONSTRAINT chk_schedule_day_of_week CHECK (day_of_week IN ('周一','周二','周三','周四','周五','周六','周日')),
  CONSTRAINT chk_schedule_start CHECK (start_period BETWEEN 1 AND 13),
  CONSTRAINT chk_schedule_end CHECK (end_period BETWEEN 1 AND 13),
  CONSTRAINT chk_schedule_week_type CHECK (week_type IN ('每周','单周','双周')),
  CONSTRAINT chk_schedule_periods CHECK (start_period <= end_period),
  CONSTRAINT fk_schedule_offering FOREIGN KEY (offering_id) REFERENCES course_offering(offering_id) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_schedule_facility FOREIGN KEY (facility_id) REFERENCES facility(facility_id) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS course_offering_teacher (
  offering_id INT NOT NULL,
  teacher_id INT NOT NULL,
  CONSTRAINT fk_offering_teacher_offering FOREIGN KEY (offering_id) REFERENCES course_offering(offering_id) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_offering_teacher_teacher FOREIGN KEY (teacher_id) REFERENCES teacher(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  PRIMARY KEY (offering_id, teacher_id)
);

-- 活动与用户行为
CREATE TABLE IF NOT EXISTS activity (
  activity_id SERIAL PRIMARY KEY,
  name VARCHAR(150) NOT NULL,
  description TEXT NOT NULL DEFAULT '暂无简介',
  start_time TIMESTAMP NOT NULL,
  end_time TIMESTAMP,
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
  CONSTRAINT fk_useractivity_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_useractivity_activity FOREIGN KEY (activity_id) REFERENCES activity(activity_id) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT chk_useractivity_status CHECK (status IN ('待参加','已签到','已完成','已取消','已缺席')),
  PRIMARY KEY (user_id, activity_id)
);


COMMIT;
