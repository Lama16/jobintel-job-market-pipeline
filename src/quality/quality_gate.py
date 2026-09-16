import json
import yaml
import os


def check_completeness(job):
    """
    Checks that essential fields are not empty.
    Returns True if the job passes, False if it fails.
    """
    required_fields = ["city", "title"]

    for field in required_fields:
        value = job.get(field)
        if not value:
            return False

    return True


def load_valid_role_families(yaml_path="config/role_families.yaml"):
    """Load the list of valid role family names from the yaml config file."""
    with open(yaml_path, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    return list(data.keys())


def load_valid_states(yaml_path="config/us_states.yaml"):
    """Load the list of valid US state names from the yaml config file."""
    with open(yaml_path, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    return data["states"]


def check_role_and_state_validity(job, valid_families, valid_states):
    """
    Checks that role_family (if present) is a known family,
    and that state (if present) is a real US state name.
    Returns True if valid, False if invalid.
    """
    role_family = job.get("role_family")
    if role_family is not None and role_family not in valid_families:
        return False

    state = job.get("state")
    if state is not None and state not in valid_states:
        return False

    return True


def find_duplicate_job_ids(jobs):
    """
    Checks a list of jobs for duplicate job_id values.
    Returns a set of job_id values that appear more than once.
    """
    seen = set()
    duplicates = set()

    for job in jobs:
        job_id = job.get("job_id")
        if job_id in seen:
            duplicates.add(job_id)
        else:
            seen.add(job_id)

    return duplicates


if __name__ == "__main__":
    with open("data/processed/usajobs_2026-09-08.json", "r", encoding="utf-8") as f:
        usajobs_data = json.load(f)

    with open("data/processed/adzuna_2026-09-08.json", "r", encoding="utf-8") as f:
        adzuna_data = json.load(f)

    all_jobs = usajobs_data + adzuna_data

    valid_families = load_valid_role_families()
    valid_states = load_valid_states()
    duplicate_ids = find_duplicate_job_ids(all_jobs)

    quarantined = []
    passed_all = 0

    for job in all_jobs:
        reasons = []

        if not check_completeness(job):
            reasons.append("failed_completeness")

        if not check_role_and_state_validity(job, valid_families, valid_states):
            reasons.append("failed_role_or_state_validity")

        if job.get("job_id") in duplicate_ids:
            reasons.append("duplicate_job_id")

        if reasons:
            quarantined.append({
                "job_id": job.get("job_id"),
                "reasons": reasons
            })
        else:
            passed_all += 1

    os.makedirs("quarantine/data", exist_ok=True)

    with open("quarantine/data/quarantined_jobs.json", "w", encoding="utf-8") as f:
        json.dump(quarantined, f, indent=2, ensure_ascii=False)

    print("Total jobs checked:", len(all_jobs))
    print("Passed all checks:", passed_all)
    print("Quarantined:", len(quarantined))