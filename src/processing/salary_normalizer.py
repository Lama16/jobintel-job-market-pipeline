import yaml


def load_config(yaml_path="config/salary.yaml"):
    """Load the salary field mappings from the yaml config file."""
    with open(yaml_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def dig(record, path):
    """
    Walk a list of keys / list indexes into a nested record.
    Returns an empty dict if any step is missing, so one absent field
    never makes the whole posting fail.
    """
    current = record
    for step in path:
        if isinstance(step, int):
            if not isinstance(current, list) or len(current) <= step:
                return {}
            current = current[step]
        else:
            if not isinstance(current, dict) or step not in current:
                return {}
            current = current[step]
    return current if isinstance(current, dict) else {}


def to_number(value):
    """
    Turn whatever the API gave us (string, float, None) into a float.
    Returns None for anything missing, unparsable, or zero - a salary of 0
    is not a real figure, it means the posting did not publish one.
    """
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def is_estimated(salary_block, source_config):
    """
    True when the source marks this salary as predicted rather than published.
    A source with no estimated_when rule always publishes real figures.
    """
    rule = source_config.get("estimated_when")
    if not rule:
        return False
    return salary_block.get(rule["field"]) in rule["values"]


def annual_multiplier(salary_block, source_config, multipliers):
    """
    How many of this posting's pay periods make one year.
    Sources without an interval field are already annual, so the answer is 1.
    """
    interval_field = source_config.get("interval_field")
    if not interval_field:
        return 1
    code = salary_block.get(interval_field)
    return multipliers.get(code, 1)


def normalize_salary(raw_job, source, config=None):
    """
    Take one raw posting from `source` ("usajobs" or "adzuna") and return the
    same three fields every time, whichever API it came from:

        {"salary_min": float|None,
         "salary_max": float|None,
         "is_estimated": bool}

    is_estimated is the whole point of this step: it says whether the numbers
    are a published figure or the API's guess. It must survive into the final
    dataset - the proposal promises to keep those two apart.

    A posting with no salary comes back with None for min and max. It is still
    a valid record, it just has nothing to report.
    """
    if config is None:
        config = load_config()

    if source not in config["sources"]:
        raise ValueError(
            "Unknown source '{}'. Add it to config/salary.yaml first.".format(source)
        )

    source_config = config["sources"][source]
    salary_block = dig(raw_job, source_config.get("salary_path", []))
    multiplier = annual_multiplier(
        salary_block, source_config, config.get("annual_multipliers", {})
    )

    minimum = to_number(salary_block.get(source_config["min_field"]))
    maximum = to_number(salary_block.get(source_config["max_field"]))

    if minimum is not None:
        minimum = round(minimum * multiplier, 2)
    if maximum is not None:
        maximum = round(maximum * multiplier, 2)

    # A few postings list the range backwards - fix it rather than drop it.
    if minimum is not None and maximum is not None and minimum > maximum:
        minimum, maximum = maximum, minimum

    return {
        "salary_min": minimum,
        "salary_max": maximum,
        "is_estimated": is_estimated(salary_block, source_config),
    }


if __name__ == "__main__":
    config = load_config()

    usajobs_job = {
        "MatchedObjectDescriptor": {
            "PositionTitle": "Data Engineer",
            "PositionRemuneration": [
                {
                    "MinimumRange": "74584",
                    "MaximumRange": "156755",
                    "RateIntervalCode": "PA",
                    "Description": "Per Year",
                }
            ],
        }
    }

    usajobs_hourly = {
        "MatchedObjectDescriptor": {
            "PositionTitle": "IT Specialist",
            "PositionRemuneration": [
                {
                    "MinimumRange": "25.50",
                    "MaximumRange": "40.00",
                    "RateIntervalCode": "PH",
                    "Description": "Per Hour",
                }
            ],
        }
    }

    adzuna_predicted = {
        "title": "Site Reliability Engineering Intern",
        "salary_min": 44385.89,
        "salary_max": 44385.89,
        "salary_is_predicted": "1",
    }

    adzuna_published = {
        "title": "Senior Data Engineer",
        "salary_min": 120000,
        "salary_max": 160000,
        "salary_is_predicted": "0",
    }

    adzuna_no_salary = {
        "title": "Software Engineer",
        "salary_is_predicted": "0",
    }

    samples = [
        ("usajobs", "annual range", usajobs_job),
        ("usajobs", "hourly range", usajobs_hourly),
        ("adzuna", "predicted", adzuna_predicted),
        ("adzuna", "published", adzuna_published),
        ("adzuna", "no salary", adzuna_no_salary),
    ]

    for source, label, job in samples:
        result = normalize_salary(job, source, config)
        print("{:9} {:14} -> {}".format(source, label, result))
