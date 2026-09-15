import json
import os
from datetime import datetime
def load_jobs(usajobs_path, adzuna_path):
    """
    يقرأ ملفي usajobs و adzuna ويرجعهم كقائمة وحدة
    """
    with open(usajobs_path, "r", encoding="utf-8") as f:
        usajobs_data = json.load(f)

    with open(adzuna_path, "r", encoding="utf-8") as f:
        adzuna_data = json.load(f)

    all_jobs = usajobs_data + adzuna_data
    return all_jobs
def group_potential_duplicates(jobs):
    groups = {}
    for job in jobs:
        key = (job.get("company"), job.get("role_family"), job.get("city"))
        if key not in groups:
            groups[key] = []
        groups[key].append(job)
    return groups
def deduplicate(jobs):
    groups = group_potential_duplicates(jobs)

    deduplicated_jobs = []
    removed_count = 0

    for key, group_jobs in groups.items():
        if len(group_jobs) == 1:
            deduplicated_jobs.append(group_jobs[0])
        else:
            newest_job = max(group_jobs, key=lambda j: j.get("created", ""))
            deduplicated_jobs.append(newest_job)
            removed_count += len(group_jobs) - 1

    return deduplicated_jobs, removed_count
def save_deduplicated(jobs, output_dir="data/processed"):
    os.makedirs(output_dir, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    output_path = os.path.join(output_dir, f"deduplicated_{today}.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)

    return output_path

if __name__ == "__main__":
    usajobs_path = "data/processed/usajobs_2026-09-08.json"
    adzuna_path = "data/processed/adzuna_2026-09-08.json"

    jobs = load_jobs(usajobs_path, adzuna_path)
    print(f"عدد الوظائف قبل الدمج: {len(jobs)}")

    deduplicated_jobs, removed_count = deduplicate(jobs)
    print(f"عدد الوظائف بعد إزالة التكرار: {len(deduplicated_jobs)}")
    print(f"عدد الوظائف المحذوفة كتكرار: {removed_count}")

    output_path = save_deduplicated(deduplicated_jobs)
    print(f"تم الحفظ في: {output_path}")