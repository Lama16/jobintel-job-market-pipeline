import glob
import json
import os

import snowflake.connector
from dotenv import load_dotenv

USAJOBS_FILE = "data/processed/usajobs_2026-09-08.json"
QUARANTINE_FILE = "data/quarantine/quarantined_jobs.json"
SNAPSHOT_DATE = "2026-09-08"

# Children before parents, so TRUNCATE never breaks a reference.
TABLES = ["BRIDGE_JOB_SKILL", "FACT_JOB_POSTING",
          "DIM_DATE", "DIM_LOCATION", "DIM_COMPANY"]


def read_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def newest_deduplicated_file():
    """Find the most recent deduplicated_<date>.json from Step 1."""
    files = sorted(glob.glob("data/processed/deduplicated_*.json"))
    if not files:
        raise FileNotFoundError("Run src/processing/deduplicator.py first.")
    return files[-1]


def load_input_jobs():
    """
    Jobs that survived deduplication AND passed the quality gate.
    Also tags each job with its source, which dedup drops when it merges
    the two files.
    """
    jobs = read_json(newest_deduplicated_file())
    usajobs_ids = {job["job_id"] for job in read_json(USAJOBS_FILE)}
    bad_ids = {row["job_id"] for row in read_json(QUARANTINE_FILE)}

    kept = []
    for job in jobs:
        if job["job_id"] in bad_ids:
            continue
        job["source"] = "usajobs" if job["job_id"] in usajobs_ids else "adzuna"
        kept.append(job)
    return kept


def build_company_dim(jobs):
    """Distinct company names, each given its own surrogate key."""
    keys, rows = {}, []
    for job in jobs:
        name = job.get("company") or "Unknown"
        if name not in keys:
            keys[name] = len(keys) + 1
            rows.append((keys[name], name))
    return keys, rows


def build_location_dim(jobs):
    """Distinct city+state pairs, each given its own surrogate key."""
    keys, rows = {}, []
    for job in jobs:
        pair = (job.get("city"), job.get("state"))
        if pair not in keys:
            keys[pair] = len(keys) + 1
            rows.append((keys[pair], pair[0], pair[1]))
    return keys, rows


def build_date_dim(snapshot_date=SNAPSHOT_DATE):
    """
    One row for the snapshot we loaded. The processed records carry no
    posting date, so this is the load date, not when the job was posted.
    """
    year, month, day = (int(part) for part in snapshot_date.split("-"))
    date_key = year * 10000 + month * 100 + day
    return date_key, [(date_key, snapshot_date, year, month, day)]


def build_fact_rows(jobs, company_keys, location_keys, date_key):
    """One fact row per job, pointing at the dimension keys."""
    rows = []
    for job in jobs:
        company = job.get("company") or "Unknown"
        rows.append((
            job["job_id"],
            company_keys[company],
            location_keys[(job.get("city"), job.get("state"))],
            date_key,
            job.get("title"),
            job.get("role_family"),
            job.get("salary_min"),
            job.get("salary_max"),
            job.get("is_estimated"),
            job["source"],
        ))
    return rows


def build_bridge_rows(jobs):
    """skills is a list, so it needs its own table - one row per skill."""
    return [(job["job_id"], skill)
            for job in jobs
            for skill in (job.get("skills") or [])]


def connect():
    load_dotenv()
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
    )


def main():
    jobs = load_input_jobs()
    print("jobs to load:", len(jobs))

    company_keys, company_rows = build_company_dim(jobs)
    location_keys, location_rows = build_location_dim(jobs)
    date_key, date_rows = build_date_dim()
    fact_rows = build_fact_rows(jobs, company_keys, location_keys, date_key)
    bridge_rows = build_bridge_rows(jobs)

    conn = connect()
    try:
        cursor = conn.cursor()

        # Makes re-running safe - without this every run doubles the rows.
        for table in TABLES:
            cursor.execute("TRUNCATE TABLE " + table)

        # Dimensions first: the fact rows reference their keys.
        cursor.executemany(
            "INSERT INTO DIM_COMPANY VALUES (%s, %s)", company_rows)
        cursor.executemany(
            "INSERT INTO DIM_LOCATION VALUES (%s, %s, %s)", location_rows)
        cursor.executemany(
            "INSERT INTO DIM_DATE VALUES (%s, %s, %s, %s, %s)", date_rows)
        cursor.executemany(
            "INSERT INTO FACT_JOB_POSTING "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", fact_rows)
        cursor.executemany(
            "INSERT INTO BRIDGE_JOB_SKILL VALUES (%s, %s)", bridge_rows)

        conn.commit()

        for table in TABLES:
            count = cursor.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
            print("{:20} {}".format(table, count))
    finally:
        conn.close()


if __name__ == "__main__":
    main()