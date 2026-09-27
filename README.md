# JobIntel - US Tech Job Market Intelligence

A data pipeline that collects US technology job postings from two public APIs (USAJOBS and Adzuna), cleans and standardizes them, removes duplicates, runs quality checks, and loads the result into Snowflake for a Power BI dashboard.

## Folder Structure

```
01_data/      Sample and final processed datasets (raw + cleaned)
02_src/       All pipeline source code
  ├── ingestion/     Pulls raw data from USAJOBS + Adzuna APIs
  ├── processing/    Cleans role, location, salary, skills; deduplicates
  ├── quality/       Runs data quality checks
  └── config/        YAML lookup files the code depends on (role families, US states, skills list, salary field mappings)
03_assets/    Dashboard screenshots and diagrams
```

## 1. Setup

### Requirements
- Python 3.10+
- A free [USAJOBS API key](https://developer.usajobs.gov/) (requires the email you registered with)
- A free [Adzuna API key](https://developer.adzuna.com/)

### Install dependencies

```bash
python -m venv venv
source venv/bin/activate          # Mac/Linux
venv\Scripts\Activate.ps1         # Windows PowerShell

pip install -r requirements.txt --break-system-packages
```

### Create your `.env` file

In the project root, create a file named `.env` with your own keys:

```
USAJOBS_API_KEY=your_key_here
USAJOBS_EMAIL=the_email_you_registered_with
ADZUNA_APP_ID=your_app_id_here
ADZUNA_APP_KEY=your_app_key_here
```

`.env` is intentionally not included in this ZIP (it contains private credentials).

### Create the data folders

```bash
mkdir -p data/raw/usajobs data/raw/adzuna data/processed data/quarantine
```

## 2. Running the Pipeline

Run each step in order from the project root:

```bash
# Step 1 — Pull raw postings from both APIs
python 02_src/ingestion/test_connection.py

# Step 2 — Clean, standardize, and combine both sources
python 02_src/processing/test_on_real_data.py

# Step 3 — Remove duplicate postings
python 02_src/processing/deduplicator.py

# Step 4 — Run data quality checks
python 02_src/quality/quality_gate.py
```

Each step prints a summary (record counts, duplicates removed, quality gate results) and writes its output to `data/processed/`.

## 3. Snowflake & Dashboard

Loading the cleaned data into Snowflake and connecting Power BI requires a live Snowflake account and is not automated by this ZIP (it needs personal credentials). The warehouse structure used is documented in the final report:

- **Schemas:** `RAW` → `STAGE` → `CORE`
- **Core tables:** `FACT_JOB_POSTING`, `DIM_COMPANY`, `DIM_LOCATION`, `DIM_DATE`, `BRIDGE_JOB_SKILL`

## 4. Known Limitations

Documented in full in the final report and in `02_src/config/sources.md`, including:
- Adzuna job descriptions are truncated by the source API (~300-400 characters), limiting skill-extraction coverage for Adzuna postings.
- `role_family` is intentionally left blank for postings that cannot be confidently classified (e.g. purely administrative titles) — this is by design, not missing data.

## Team

Lama Bin muryihah
Hawam Al Theeban
Haya Alotaibi
Jawaher Alhqbani