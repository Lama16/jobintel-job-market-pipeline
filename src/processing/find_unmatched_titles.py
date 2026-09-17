import json
from collections import Counter
from datetime import datetime

today = datetime.now().strftime("%Y-%m-%d")
with open(f"data/processed/deduplicated_{today}.json", "r", encoding="utf-8") as f:
    jobs = json.load(f)

unmatched_titles = [job["title"] for job in jobs if job.get("role_family") is None]

print(f"Total unmatched: {len(unmatched_titles)}")
print()

counter = Counter(unmatched_titles)
for title, count in counter.most_common():
    if count >= 2:
        print(f"{count:3d}  {title}")