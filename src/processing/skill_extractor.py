import yaml
import re
import os


def load_skills(yaml_path="config/skills.yaml"):
    """Load the list of skills from the yaml config file."""
    with open(yaml_path, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    return data["skills"]


def extract_skills(job_description, skills_list):
    """
    Scan a job description and return all skills from skills_list
    that appear in it as a whole word, not as part of another word.
    Matching is case-insensitive.
    """
    found_skills = []
    description_lower = job_description.lower()

    for skill in skills_list:
        skill_lower = skill.lower()
        pattern = r"\b" + re.escape(skill_lower) + r"\b"
        if re.search(pattern, description_lower):
            found_skills.append(skill)

    return found_skills


if __name__ == "__main__":
    skills = load_skills()

    sample_description = """
    We are looking for a Data Engineer with strong experience in
    Python, SQL, and AWS. Familiarity with Docker and Airflow
    is a plus. Knowledge of Snowflake is preferred.
    """

    result = extract_skills(sample_description, skills)
    print("Skills found:", result)

    tricky_description = """
    We are looking for a candidate with a strong background in
    project management and government contracting experience.
    """
    tricky_result = extract_skills(tricky_description, skills)
    print("Tricky test (should be empty):", tricky_result)