-- 040_create_course_tables.sql
BEGIN;

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

COMMIT;
