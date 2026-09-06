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
usajobs_params = {"JobCategoryCode": "2210", "ResultsPerPage": 50}  
r1 = requests.get("https://data.usajobs.gov/api/search", headers=usajobs_headers, params=usajobs_params)
print("USAJOBS status:", r1.status_code)

today = date.today().isoformat()
usajobs_path = f"data/raw/usajobs/{today}.json"
with open(usajobs_path, "w") as f:
    json.dump(r1.json(), f, indent=2)
print(f"Saved to {usajobs_path}")

print()

#  Adzuna
print("Fetching Adzuna...")
adzuna_params = {
    "app_id": os.getenv("ADZUNA_APP_ID"),
    "app_key": os.getenv("ADZUNA_APP_KEY"),
    "results_per_page": 50,
    "category": "it-jobs",
}
r2 = requests.get("https://api.adzuna.com/v1/api/jobs/us/search/1", params=adzuna_params)
print("Adzuna status:", r2.status_code)

adzuna_path = f"data/raw/adzuna/{today}.json"
with open(adzuna_path, "w") as f:
    json.dump(r2.json(), f, indent=2)
print(f"Saved to {adzuna_path}")