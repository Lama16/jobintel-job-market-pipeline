import json

from role_matcher import load_role_families, match_role_family
from location_normalizer import load_us_states, get_primary_usajobs_location, normalize_adzuna_location
from salary_normalizer import normalize_salary
from skill_extractor import load_skills, extract_skills

def process_one_usajobs_job(raw_job, role_families, us_states, skills_list):
    descriptor = raw_job["MatchedObjectDescriptor"]

    job_id = raw_job.get("MatchedObjectId")
    title = descriptor["PositionTitle"]

    role_family = match_role_family(title, role_families)

    location = get_primary_usajobs_location(descriptor["PositionLocation"])

    salary = normalize_salary(raw_job, "usajobs")

    description = descriptor.get("QualificationSummary", "")
    skills = extract_skills(description, skills_list)

    return {
        "job_id": job_id,
        "title": title,
        "role_family": role_family,
        "city": location["city"],
        "state": location["state"],
        "salary_min": salary["salary_min"],
        "salary_max": salary["salary_max"],
        "is_estimated": salary["is_estimated"],
        "skills": skills,
    }

def process_one_adzuna_job(raw_job, role_families, us_states, skills_list):
    job_id = raw_job.get("id")
    title = raw_job.get("title", "")
    role_family = match_role_family(title, role_families)

    company = raw_job.get("company", {}).get("display_name")

    area = raw_job.get("location", {}).get("area", [])
    location = normalize_adzuna_location(area)

    salary = normalize_salary(raw_job, "adzuna")

    description = raw_job.get("description", "")
    skills = extract_skills(description, skills_list)

    return {
        "job_id": job_id,
        "title": title,
        "company": company,
        "role_family": role_family,
        "city": location["city"],
        "state": location["state"],
        "salary_min": salary["salary_min"],
        "salary_max": salary["salary_max"],
        "is_estimated": salary["is_estimated"],
        "skills": skills,
    }


def save_processed_jobs(processed_jobs, output_path):
    """Save the list of cleaned job records to a JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(processed_jobs, f, indent=2)
    print(f"Saved {len(processed_jobs)} processed jobs to {output_path}")


if __name__ == "__main__":
    role_families = load_role_families()
    us_states = load_us_states()
    skills_list = load_skills()

    with open("data/raw/usajobs/2026-09-08.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    jobs = data["SearchResult"]["SearchResultItems"]

    processed_jobs = []
    for job in jobs:
        result = process_one_usajobs_job(job, role_families, us_states, skills_list)
        processed_jobs.append(result)

    save_processed_jobs(processed_jobs, "data/processed/usajobs_2026-09-08.json")
    
    with open("data/raw/adzuna/2026-09-08.json", "r", encoding="utf-8") as f:
        adzuna_data = json.load(f)

    adzuna_jobs = adzuna_data["results"]

    processed_adzuna = []
    for job in adzuna_jobs:
        result = process_one_adzuna_job(job, role_families, us_states, skills_list)
        processed_adzuna.append(result)

    save_processed_jobs(processed_adzuna, "data/processed/adzuna_2026-09-08.json")   