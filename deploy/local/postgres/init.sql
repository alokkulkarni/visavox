-- Local cell database roles (ADR-004, NFR-O5). Runs once, when the postgres container first starts.
-- Migrations run as visavox_owner; services connect as visavox_app, which owns nothing and cannot
-- bypass row-level security. 'local-only' passwords are for this loopback-bound, synthetic-data
-- container and are never used anywhere else.
CREATE ROLE visavox_owner LOGIN PASSWORD 'local-only' NOSUPERUSER NOCREATEROLE NOCREATEDB NOBYPASSRLS;
CREATE ROLE visavox_app LOGIN PASSWORD 'local-only' NOSUPERUSER NOCREATEROLE NOCREATEDB NOBYPASSRLS;
CREATE DATABASE visavox OWNER visavox_owner;
REVOKE ALL ON DATABASE visavox FROM PUBLIC;
GRANT CONNECT ON DATABASE visavox TO visavox_app;

\connect visavox
ALTER SCHEMA public OWNER TO visavox_owner;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO visavox_app;
