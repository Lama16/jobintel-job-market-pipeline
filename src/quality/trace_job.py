"""
Step 4 - Validate the Whole Chain.

Follows jobs through every stage of the pipeline and prints what each stage
holds for them, so a person can check nothing changed or went missing:

    raw -> processed -> deduplicated -> quarantine -> Snowflake

Usage:
    python src/quality/trace_job.py                 # stage counts + sample jobs
    python src/quality/trace_job.py 759326100 ...   # stage counts + these jobs
"""
import glob
import json
import os
import sys

from dotenv import load_dotenv

RAW_USAJOBS = "data/raw/usajobs/2026-09-08.json"
RAW_ADZUNA = "data/raw/adzuna/2026-09-08.json"
PROCESSED_USAJOBS = "data/processed/usajobs_2026-09-08.json"
PROCESSED_ADZUNA = "data/processed/adzuna_2026-09-08.json"
QUARANTINE_FILE = "data/quarantine/quarantined_jobs.json"

# One job of each kind worth checking by hand.
SAMPLE_JOBS = {
    "759326100": "USAJOBS job",
    "5759395778": "Adzuna job with a published salary",
    "5823999019": "Mastercard Senior SRE - kept",
    "5827870115": "Mastercard SRE II - different title, so kept separately",
    "859667500": "USAJOBS duplicate of 859667400 - dedup should remove",
    "850999700": "job with no role_family",
}

# Fields compared between processed, deduplicated and Snowflake.
COMPARE_FIELDS = ["title", "role_family", "city", "state",
                  "salary_min", "salary_max", "is_estimated"]


def read_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def newest_deduplicated_file():
    files = sorted(glob.glob("data/processed/deduplicated_*.json"))
    return files[-1] if files else None


def load_raw():
    """job_id -> the few raw values a person can compare against."""
    raw = {}

    usajobs = read_json(RAW_USAJOBS)
    if usajobs:
        for item in usajobs["SearchResult"]["SearchResultItems"]:
            descriptor = item["MatchedObjectDescriptor"]
            pay = (descriptor.get("PositionRemuneration") or [{}])[0]
            raw[str(item["MatchedObjectId"])] = {
                "title": descriptor.get("PositionTitle"),
                "salary_min": pay.get("MinimumRange"),
                "salary_max": pay.get("MaximumRange"),
                "location": descriptor.get("PositionLocationDisplay"),
            }

    adzuna = read_json(RAW_ADZUNA)
    if adzuna:
        for job in adzuna["results"]:
            raw[str(job["id"])] = {
                "title": job.get("title"),
                "salary_min": job.get("salary_min"),
                "salary_max": job.get("salary_max"),
                "salary_is_predicted": job.get("salary_is_predicted"),
                "location": (job.get("location") or {}).get("display_name"),
            }

    return raw


def index_by_id(jobs):
    """job_id -> list of records, a list so repeated ids stay visible."""
    index = {}
    for job in jobs or []:
        index.setdefault(str(job.get("job_id")), []).append(job)
    return index


def connect_snowflake():
    """Returns a connection, or None if Snowflake isn't reachable."""
    try:
        import snowflake.connector
        load_dotenv(".env")
        return snowflake.connector.connect(
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            schema=os.getenv("SNOWFLAKE_SCHEMA"),
        )
    except Exception as error:
        print("Snowflake skipped:", error)
        return None


def snowflake_job(conn, job_id):
    """The job as it sits in Snowflake, joined back to its dimensions."""
    from snowflake.connector import DictCursor

    cursor = conn.cursor(DictCursor)
    cursor.execute(
        "SELECT f.TITLE, f.ROLE_FAMILY, l.CITY, l.STATE, c.COMPANY_NAME, "
        "       f.SALARY_MIN, f.SALARY_MAX, f.IS_ESTIMATED, f.SOURCE "
        "FROM FACT_JOB_POSTING f "
        "JOIN DIM_LOCATION l ON f.LOCATION_KEY = l.LOCATION_KEY "
        "JOIN DIM_COMPANY  c ON f.COMPANY_KEY  = c.COMPANY_KEY "
        "WHERE f.JOB_ID = %s",
        (job_id,),
    )
    rows = cursor.fetchall()
    return [{key.lower(): value for key, value in row.items()} for row in rows]


def snowflake_count(conn):
    if conn is None:
        return None
    return conn.cursor().execute(
        "SELECT COUNT(*) FROM FACT_JOB_POSTING").fetchone()[0]


def print_counts(raw, processed_usajobs, processed_adzuna, deduplicated,
                 quarantined, loaded):
    processed_total = len(processed_usajobs or []) + len(processed_adzuna or [])
    dedup_total = len(deduplicated or [])
    passed = dedup_total - len({q["job_id"] for q in quarantined or []})

    print("=" * 60)
    print("STAGE COUNTS")
    print("=" * 60)
    print("{:28} {}".format("raw", len(raw)))
    print("{:28} {}  (usajobs {} + adzuna {})".format(
        "processed", processed_total,
        len(processed_usajobs or []), len(processed_adzuna or [])))
    print("{:28} {}  ({} removed)".format(
        "deduplicated", dedup_total, processed_total - dedup_total))
    print("{:28} {} passed, {} quarantined".format(
        "quality gate", passed, len(quarantined or [])))
    print("{:28} {}".format(
        "Snowflake fact rows", "skipped" if loaded is None else loaded))

    if loaded is not None and loaded != passed:
        print("  !! Snowflake does not match the quality gate - re-run the loader")

    for label, jobs in (("usajobs", processed_usajobs),
                        ("adzuna", processed_adzuna)):
        repeated = [i for i, rows in index_by_id(jobs).items() if len(rows) > 1]
        if repeated:
            print("  note: processed {} has {} repeated job_ids, e.g. {}".format(
                label, len(repeated), repeated[:3]))


def compare(expected, actual):
    """Print the fields whose value changed between two stages."""
    changed = [field for field in COMPARE_FIELDS
               if expected.get(field) != actual.get(field)]
    if changed:
        for field in changed:
            print("      !! {} changed: {!r} -> {!r}".format(
                field, expected.get(field), actual.get(field)))
    else:
        print("      matches processed")


def trace(job_id, label, raw, processed, deduplicated, quarantined, conn):
    print()
    print("-" * 60)
    print("{}  {}".format(job_id, label))
    print("-" * 60)

    # 1. raw
    if job_id in raw:
        print("  1. raw           found:", raw[job_id])
    else:
        print("  1. raw           NOT FOUND in your local raw files")
        print("      (raw is gitignored - your copy may be older than your team's)")

    # 2. processed
    processed_rows = processed.get(job_id, [])
    if not processed_rows:
        print("  2. processed     NOT FOUND - dropped during processing")
        return
    base = processed_rows[0]
    print("  2. processed     found:", {f: base.get(f) for f in COMPARE_FIELDS})
    if len(processed_rows) > 1:
        print("      note: this job_id appears {} times".format(len(processed_rows)))

    # 3. deduplicated
    dedup_rows = deduplicated.get(job_id, [])
    if dedup_rows:
        print("  3. deduplicated  kept")
        compare(base, dedup_rows[0])
    else:
        print("  3. deduplicated  REMOVED as a duplicate - should not be in Snowflake")

    # 4. quality gate
    reasons = quarantined.get(job_id)
    if reasons:
        print("  4. quality gate  QUARANTINED:", reasons)
    elif dedup_rows:
        print("  4. quality gate  passed")
    else:
        print("  4. quality gate  not checked (removed earlier)")

    # 5. Snowflake
    if conn is None:
        print("  5. Snowflake     skipped")
        return
    rows = snowflake_job(conn, job_id)
    should_be_loaded = bool(dedup_rows) and not reasons
    if rows:
        print("  5. Snowflake     loaded (company: {}, source: {})".format(
            rows[0]["company_name"], rows[0]["source"]))
        compare(base, rows[0])
        if not should_be_loaded:
            print("      !! loaded, but an earlier stage removed it")
    elif should_be_loaded:
        print("  5. Snowflake     !! MISSING - passed every stage but was not loaded")
    else:
        print("  5. Snowflake     not loaded - correct")


def main():
    job_ids = sys.argv[1:] or list(SAMPLE_JOBS)

    raw = load_raw()
    processed_usajobs = read_json(PROCESSED_USAJOBS)
    processed_adzuna = read_json(PROCESSED_ADZUNA)
    dedup_path = newest_deduplicated_file()
    deduplicated = read_json(dedup_path) if dedup_path else None
    quarantine_rows = read_json(QUARANTINE_FILE) or []

    if deduplicated is None:
        print("No deduplicated file - run src/processing/deduplicator.py first.")
        return

    conn = connect_snowflake()
    try:
        print_counts(raw, processed_usajobs, processed_adzuna, deduplicated,
                     quarantine_rows, snowflake_count(conn))

        processed = index_by_id((processed_usajobs or []) + (processed_adzuna or []))
        dedup_index = index_by_id(deduplicated)
        quarantined = {q["job_id"]: q.get("reasons") for q in quarantine_rows}

        for job_id in job_ids:
            trace(job_id, SAMPLE_JOBS.get(job_id, ""), raw, processed,
                  dedup_index, quarantined, conn)
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()
