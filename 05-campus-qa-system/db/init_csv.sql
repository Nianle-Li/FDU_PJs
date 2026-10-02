-- Full CSV initialization entrypoint: schema + CSV demo data.
-- Run from the repository root so \copy can resolve db/seeds/csv/*.csv:
--   psql -v ON_ERROR_STOP=1 -d fcqa -f db/init_csv.sql
--
-- Docker Compose example:
--   docker compose exec -w /opt/fcqa db psql -v ON_ERROR_STOP=1 -U postgres -d fcqa -f db/init_csv.sql

\set ON_ERROR_STOP on

\ir schema.sql
\ir seeds/import_csv.sql
