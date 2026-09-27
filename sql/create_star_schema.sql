-- JobIntel - Week 3, Step 3
-- Creates the star schema that src/loading/snowflake_loader.py loads into.
-- Safe to run more than once: every statement uses IF NOT EXISTS.

CREATE WAREHOUSE IF NOT EXISTS JOBINTEL_WH
  WAREHOUSE_SIZE = 'XSMALL' AUTO_SUSPEND = 60 AUTO_RESUME = TRUE;
CREATE DATABASE IF NOT EXISTS JOBINTEL;
CREATE SCHEMA IF NOT EXISTS JOBINTEL.MARKET;

USE WAREHOUSE JOBINTEL_WH;
USE SCHEMA JOBINTEL.MARKET;

-- Dimension: one row per company / hiring organization.
-- USAJOBS jobs carry the agency name, Adzuna jobs the employer name.
CREATE TABLE IF NOT EXISTS DIM_COMPANY (
  COMPANY_KEY  INT PRIMARY KEY,
  COMPANY_NAME VARCHAR
);

-- Dimension: one row per distinct city + state pair.
CREATE TABLE IF NOT EXISTS DIM_LOCATION (
  LOCATION_KEY INT PRIMARY KEY,
  CITY         VARCHAR,
  STATE        VARCHAR
);

-- Dimension: the snapshot we loaded. The processed records carry no posting
-- date yet, so this holds the load date, not when the job was advertised.
CREATE TABLE IF NOT EXISTS DIM_DATE (
  DATE_KEY  INT PRIMARY KEY,
  FULL_DATE DATE,
  YEAR      INT,
  MONTH     INT,
  DAY       INT
);

-- Fact: one row per job posting that passed the quality gate.
-- IS_ESTIMATED says whether the salary is a published figure or the API's
-- guess - the dashboard must keep the two apart.
CREATE TABLE IF NOT EXISTS FACT_JOB_POSTING (
  JOB_ID       VARCHAR PRIMARY KEY,
  COMPANY_KEY  INT REFERENCES DIM_COMPANY(COMPANY_KEY),
  LOCATION_KEY INT REFERENCES DIM_LOCATION(LOCATION_KEY),
  DATE_KEY     INT REFERENCES DIM_DATE(DATE_KEY),
  TITLE        VARCHAR,
  ROLE_FAMILY  VARCHAR,
  SALARY_MIN   FLOAT,
  SALARY_MAX   FLOAT,
  IS_ESTIMATED BOOLEAN,
  SOURCE       VARCHAR
);

-- Bridge: skills is a list per job, so it cannot live in the fact table.
CREATE TABLE IF NOT EXISTS BRIDGE_JOB_SKILL (
  JOB_ID VARCHAR,
  SKILL  VARCHAR
);

SHOW TABLES IN SCHEMA JOBINTEL.MARKET;
