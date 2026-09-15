import json

from role_matcher import load_role_families, match_role_family
from location_normalizer import load_us_states, get_primary_usajobs_location
from salary_normalizer import normalize_salary
from skill_extractor import load_skills, extract_skills

def process_one_usajobs_job(raw_job, role_families, us_states, skills_list):
    descriptor = raw_job["MatchedObjectDescriptor"]

    title = descriptor["PositionTitle"]
    role_family = match_role_family(title, role_families)

    location = get_primary_usajobs_location(descriptor["PositionLocation"])

    salary = normalize_salary(raw_job, "usajobs")

    description = descriptor.get("QualificationSummary", "")
    skills = extract_skills(description, skills_list)

    return {
        "title": title,
        "role_family": role_family,
        "city": location["city"],
        "state": location["state"],
        "salary_min": salary["salary_min"],
        "salary_max": salary["salary_max"],
        "is_estimated": salary["is_estimated"],
        "skills": skills,
    }

if __name__ == "__main__":
    role_families = load_role_families()
    us_states = load_us_states()
    skills_list = load_skills()

    with open("data/raw/usajobs/2026-09-08.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    jobs = data["SearchResult"]["SearchResultItems"]

    for job in jobs[:30]:
        result = process_one_usajobs_job(job, role_families, us_states, skills_list)
        print(result)