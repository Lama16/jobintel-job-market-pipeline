import os
import json
from datetime import date
import requests
from dotenv import load_dotenv

load_dotenv()

#  USAJOBS 
print("Fetching USAJOBS...")
usajobs_headers = {
    "Host": "data.usajobs.gov",
    "User-Agent": os.getenv("USAJOBS_EMAIL"),
    "Authorization-Key": os.getenv("USAJOBS_API_KEY"),
}
usajobs_params = {"JobCategoryCode": "2210", "ResultsPerPage": 500} 
r1 = requests.get("https://data.usajobs.gov/api/search", headers=usajobs_headers, params=usajobs_params)
print("USAJOBS status:", r1.status_code)
print("USAJOBS response:", r1.text)

today = date.today().isoformat()
usajobs_path = f"data/raw/usajobs/{today}.json"
with open(usajobs_path, "w") as f:
    json.dump(r1.json(), f, indent=2)
print(f"Saved to {usajobs_path}")

print()

#  Adzuna
print("Fetching Adzuna...")
all_results = []
pages_to_fetch = 20  

for page in range(1, pages_to_fetch + 1):
    adzuna_params = {
        "app_id": os.getenv("ADZUNA_APP_ID"),
        "app_key": os.getenv("ADZUNA_APP_KEY"),
        "results_per_page": 50,
        "category": "it-jobs",
    }
    r2 = requests.get(f"https://api.adzuna.com/v1/api/jobs/us/search/{page}", params=adzuna_params)
    if r2.status_code != 200:
        print(f"Page {page} failed with status {r2.status_code}")
        break
    page_results = r2.json()["results"]
    if not page_results:
        break
    all_results.extend(page_results)

print(f"Adzuna: fetched {len(all_results)} postings total")

adzuna_path = f"data/raw/adzuna/{today}.json"
with open(adzuna_path, "w") as f:
    json.dump({"results": all_results}, f, indent=2)
print(f"Saved to {adzuna_path}")

import csv

manifest_path = "data/raw/run_manifest.csv"
manifest_exists = os.path.exists(manifest_path)

with open(manifest_path, "a", newline="") as f:
    writer = csv.writer(f)
    if not manifest_exists:
        writer.writerow(["date", "source", "status", "record_count"])
    writer.writerow([today, "usajobs", r1.status_code, r1.json()["SearchResult"]["SearchResultCount"]])
    writer.writerow([today, "adzuna", r2.status_code, len(r2.json()["results"])])

print(f"Manifest updated: {manifest_path}")