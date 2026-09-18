-- JobIntel - read-only access for the team.
-- Creates a role that can SELECT from the star schema and nothing else,
-- so nobody can drop or overwrite the loaded data by accident.
--
-- Run this once, as ACCOUNTADMIN. The users themselves are created in a
-- separate file that is NOT committed, because it contains passwords.
-- Safe to run more than once.

USE ROLE ACCOUNTADMIN;

CREATE ROLE IF NOT EXISTS JOBINTEL_READER;

GRANT USAGE ON WAREHOUSE JOBINTEL_WH TO ROLE JOBINTEL_READER;
GRANT USAGE ON DATABASE JOBINTEL TO ROLE JOBINTEL_READER;
GRANT USAGE ON SCHEMA JOBINTEL.MARKET TO ROLE JOBINTEL_READER;

GRANT SELECT ON ALL TABLES IN SCHEMA JOBINTEL.MARKET TO ROLE JOBINTEL_READER;
-- FUTURE keeps new tables readable without re-running the grant above.
GRANT SELECT ON FUTURE TABLES IN SCHEMA JOBINTEL.MARKET TO ROLE JOBINTEL_READER;

SHOW GRANTS TO ROLE JOBINTEL_READER;
