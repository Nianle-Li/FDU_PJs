-- 050_create_course_offering_and_schedule.sql
BEGIN;

CREATE TABLE IF NOT EXISTS course_offering (
  offering_id SERIAL PRIMARY KEY,
  course_code VARCHAR(30) NOT NULL,
  semester VARCHAR(50) NOT NULL,
  CONSTRAINT chk_course_offering_semester CHECK (TRIM(semester) <> ''),
  CONSTRAINT fk_course_offering_section FOREIGN KEY (course_code) REFERENCES course_section(course_code) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS course_offering_schedule (
  offering_id INT NOT NULL,
  day_of_week VARCHAR(10) NOT NULL CHECK (day_of_week IN ('周一','周二','周三','周四','周五','周六','周日')),
  start_period INT NOT NULL CHECK (start_period BETWEEN 1 AND 13),
  end_period INT NOT NULL CHECK (end_period BETWEEN 1 AND 13),
  week_type VARCHAR(20) NOT NULL DEFAULT '每周' CHECK (week_type IN ('每周','单周','双周')),
  facility_id INT NOT NULL,
  PRIMARY KEY (offering_id, day_of_week, start_period, end_period, week_type),
  FOREIGN KEY (offering_id) REFERENCES course_offering(offering_id) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT chk_schedule_periods CHECK (start_period <= end_period),
  CONSTRAINT fk_schedule_facility FOREIGN KEY (facility_id) REFERENCES facility(facility_id) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS course_offering_teacher (
  offering_id INT NOT NULL,
  teacher_id INT NOT NULL,
  PRIMARY KEY (offering_id, teacher_id),
  CONSTRAINT fk_offering_teacher_offering FOREIGN KEY (offering_id) REFERENCES course_offering(offering_id) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_offering_teacher_teacher FOREIGN KEY (teacher_id) REFERENCES teacher(user_id) ON UPDATE CASCADE ON DELETE RESTRICT
);

COMMIT;
