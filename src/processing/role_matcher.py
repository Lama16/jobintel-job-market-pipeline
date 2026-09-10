import yaml
import re

def load_role_families(yaml_path="config/role_families.yaml"):
    """Load the role families dictionary from the yaml config file."""
    with open(yaml_path, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    return data


def clean_title(raw_title):
    """Remove anything in parentheses and lowercase the title."""
    no_parens = re.sub(r"\(.*?\)", "", raw_title)
    return no_parens.lower().strip()

def match_role_family(raw_title, families):
    """Return the matching role family name, or None if nothing matches."""
    cleaned = clean_title(raw_title)

    for family_name, keywords in families.items():
        for keyword in keywords:
            if keyword.lower() in cleaned:
                return family_name

    return None

if __name__ == "__main__":
    families = load_role_families()

    test_titles = [
        "Data Engineer",
        "IT SPECIALIST (NETWORK) (TITLE 32)",
        "Node-React Full Stack Web Application Developer",
        "DOD SkillBridge Program - Industry leading benefits package",
        "We're Hiring Engineers at ZipRecruiter!",
    ]

    for title in test_titles:
        result = match_role_family(title, families)
        print(f"{title!r} -> {result}")