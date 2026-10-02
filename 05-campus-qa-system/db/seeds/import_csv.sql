-- Import deterministic CSV demo data.
-- This script resets business tables before import so it can replace the
-- smaller SQL seed data during demos. Run from the repository root.

\set ON_ERROR_STOP on

BEGIN;

TRUNCATE TABLE
  user_activity,
  query_log,
  activity,
  course_offering_teacher,
  course_offering_schedule,
  course_offering,
  course_section,
  course,
  student,
  teacher,
  users,
  facility,
  building,
  campus
RESTART IDENTITY CASCADE;

\copy campus(campus_id, name, address) FROM 'db/seeds/csv/campus.csv' WITH (FORMAT csv, HEADER true)
\copy building(building_id, name, type, campus_id) FROM 'db/seeds/csv/building.csv' WITH (FORMAT csv, HEADER true)
\copy facility(facility_id, name, type, open_time, building_id) FROM 'db/seeds/csv/facility.csv' WITH (FORMAT csv, HEADER true)
\copy users(user_id, name, department) FROM 'db/seeds/csv/users.csv' WITH (FORMAT csv, HEADER true)
\copy teacher(user_id, title) FROM 'db/seeds/csv/teacher.csv' WITH (FORMAT csv, HEADER true)
\copy student(user_id, major) FROM 'db/seeds/csv/student.csv' WITH (FORMAT csv, HEADER true)
\copy course(course_master_code, name) FROM 'db/seeds/csv/course.csv' WITH (FORMAT csv, HEADER true)
\copy course_section(course_code, course_master_code) FROM 'db/seeds/csv/course_section.csv' WITH (FORMAT csv, HEADER true)
\copy course_offering(offering_id, course_code, semester) FROM 'db/seeds/csv/course_offering.csv' WITH (FORMAT csv, HEADER true)
\copy course_offering_schedule(offering_id, day_of_week, start_period, end_period, week_type, facility_id) FROM 'db/seeds/csv/course_offering_schedule.csv' WITH (FORMAT csv, HEADER true)
\copy course_offering_teacher(offering_id, teacher_id) FROM 'db/seeds/csv/course_offering_teacher.csv' WITH (FORMAT csv, HEADER true)
\copy activity(activity_id, name, description, start_time, end_time, organizer, facility_id) FROM 'db/seeds/csv/activity.csv' WITH (FORMAT csv, HEADER true)
\copy user_activity(user_id, activity_id, status) FROM 'db/seeds/csv/user_activity.csv' WITH (FORMAT csv, HEADER true)
\copy query_log(log_id, user_id, query_category, query_content, query_time) FROM 'db/seeds/csv/query_log.csv' WITH (FORMAT csv, HEADER true)

SELECT setval(pg_get_serial_sequence('users', 'user_id'), COALESCE((SELECT max(user_id) FROM users), 1), (SELECT count(*) > 0 FROM users));
SELECT setval(pg_get_serial_sequence('campus', 'campus_id'), COALESCE((SELECT max(campus_id) FROM campus), 1), (SELECT count(*) > 0 FROM campus));
SELECT setval(pg_get_serial_sequence('building', 'building_id'), COALESCE((SELECT max(building_id) FROM building), 1), (SELECT count(*) > 0 FROM building));
SELECT setval(pg_get_serial_sequence('facility', 'facility_id'), COALESCE((SELECT max(facility_id) FROM facility), 1), (SELECT count(*) > 0 FROM facility));
SELECT setval(pg_get_serial_sequence('course_offering', 'offering_id'), COALESCE((SELECT max(offering_id) FROM course_offering), 1), (SELECT count(*) > 0 FROM course_offering));
SELECT setval(pg_get_serial_sequence('activity', 'activity_id'), COALESCE((SELECT max(activity_id) FROM activity), 1), (SELECT count(*) > 0 FROM activity));
SELECT setval(pg_get_serial_sequence('query_log', 'log_id'), COALESCE((SELECT max(log_id) FROM query_log), 1), (SELECT count(*) > 0 FROM query_log));

COMMIT;
