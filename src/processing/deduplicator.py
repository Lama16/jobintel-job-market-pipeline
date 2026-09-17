import json
import os
from datetime import datetime
from role_matcher import clean_title

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
        company = job.get("company")
        # USAJOBS jobs don't have a company field, so use the job_id as a
        # stand-in to avoid grouping unrelated government jobs together
        if company is None:
            company = f"usajobs::{job.get('job_id')}"
        cleaned_title = clean_title(job.get("title", ""))
        key = (company, cleaned_title, job.get("city"))
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

    # طباعة تشخيصية مؤقتة - نشوف أمثلة من USAJOBS اتحسبت تكرار
    for key, group_jobs in groups.items():
        if len(group_jobs) > 1 and not str(key[0]).startswith("usajobs::"):
            for j in group_jobs[:1]:
                print(f"GROUP: {key} -> {len(group_jobs)} jobs, e.g. job_id={j.get('job_id')}, title={j.get('title')}")

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
    print(f"Total jobs before merging: {len(jobs)}")

    deduplicated_jobs, removed_count = deduplicate(jobs)
    print(f"Total jobs after deduplication: {len(deduplicated_jobs)}")
    print(f"Duplicates removed: {removed_count}")

    output_path = save_deduplicated(deduplicated_jobs)
    print(f"Saved to: {output_path}")