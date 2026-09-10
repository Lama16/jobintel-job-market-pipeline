import json
def normalize_usajobs_location(location_data):
    """
    Takes one location object from USAJOBS PositionLocation list
    and returns a standardized dict: city, state, region.
    """
    city = location_data.get("CityName")
    state = location_data.get("CountrySubDivisionCode")
    region = None  # نحددها لاحقًا لو احتجناها

    return {
        "city": city,
        "state": state,
        "region": region
    }
def get_primary_usajobs_location(position_location_list):
    """
    Takes the full PositionLocation list from USAJOBS
    and returns the normalized city/state/region of the FIRST location only.
    """
    if not position_location_list:
        return {"city": None, "state": None, "region": None}

    first_location = position_location_list[0]
    return normalize_usajobs_location(first_location)
def normalize_adzuna_location(area_list):
    """
    Takes the 'area' list from Adzuna (ordered country -> ... -> city)
    and returns a standardized dict: city, state, region.
    """
    if not area_list:
        return {"city": None, "state": None, "region": None}

    city = area_list[-1]

    if len(area_list) >= 2:
        state = area_list[-2]
    else:
        state = None

    region = None

    return {
        "city": city,
        "state": state,
        "region": region

    }

def load_usajobs_file(filepath):
    """
    Opens a USAJOBS raw JSON file and returns the list of job postings.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    jobs = data["SearchResult"]["SearchResultItems"]
    return jobs
if __name__ == "__main__":
    sample_position_location = [
        {
            "LocationName": "Washington, District of Columbia",
            "CountryCode": "United States",
            "CountrySubDivisionCode": "District of Columbia",
            "CityName": "Washington, District of Columbia",
            "Longitude": -77.03968,
            "Latitude": 38.89702
        }
    ]

    result = get_primary_usajobs_location(sample_position_location)
    print(result)
    sample_area = ["US", "Washington", "Grays Harbor County", "Woodlawn"]
    adzuna_result = normalize_adzuna_location(sample_area)
    print(adzuna_result)
    real_jobs = load_usajobs_file("data/raw/usajobs/2026-09-08.json")
    print("Total jobs loaded:", len(real_jobs))