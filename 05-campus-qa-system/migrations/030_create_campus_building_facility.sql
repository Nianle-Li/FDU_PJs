-- 030_create_campus_building_facility.sql
BEGIN;

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

COMMIT;
