-- Full initialization entrypoint: schema + initial test data.
-- Run from the repository root with:
--   psql -v ON_ERROR_STOP=1 -d fcqa -f db/init.sql

\set ON_ERROR_STOP on

\ir schema.sql
\ir seeds/001_initial_data.sql
