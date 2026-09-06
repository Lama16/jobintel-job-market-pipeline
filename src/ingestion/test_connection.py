import os
import requests
from dotenv import load_dotenv

load_dotenv()

# --- Test USAJOBS ---
print("Testing USAJOBS...")
usajobs_headers = {
    "Host": "data.usajobs.gov",
    "User-Agent": os.getenv("USAJOBS_EMAIL"),
    "Authorization-Key": os.getenv("USAJOBS_API_KEY"),
}
usajobs_params = {"Keyword": "data engineer", "ResultsPerPage": 5}
r1 = requests.get("https://data.usajobs.gov/api/search", headers=usajobs_headers, params=usajobs_params)
print("USAJOBS status:", r1.status_code)
print("Sample:", r1.json()["SearchResult"]["SearchResultItems"][0]["MatchedObjectDescriptor"]["PositionTitle"])

print()

# --- Test Adzuna ---
print("Testing Adzuna...")
adzuna_params = {
    "app_id": os.getenv("ADZUNA_APP_ID"),
    "app_key": os.getenv("ADZUNA_APP_KEY"),
    "results_per_page": 5,
    "what": "data engineer",
}
r2 = requests.get("https://api.adzuna.com/v1/api/jobs/us/search/1", params=adzuna_params)
print("Adzuna status:", r2.status_code)
print("Sample:", r2.json()["results"][0]["title"])