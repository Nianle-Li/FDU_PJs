-- PostgreSQL schema entrypoint.
-- Run from the repository root with:
--   psql -v ON_ERROR_STOP=1 -d fcqa -f db/schema.sql

\set ON_ERROR_STOP on

\ir ../migrations/001_create_extensions.sql
\ir ../migrations/002_create_schema_migrations.sql
\ir ../migrations/010_create_user.sql
\ir ../migrations/020_create_teacher_student.sql
\ir ../migrations/030_create_campus_building_facility.sql
\ir ../migrations/040_create_course_tables.sql
\ir ../migrations/050_create_course_offering_and_schedule.sql
\ir ../migrations/060_create_activity_querylog_useractivity.sql
\ir ../migrations/070_create_indexes.sql
