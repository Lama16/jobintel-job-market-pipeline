"""
Generates the six pages of the JobIntel Power BI dashboard.

The dashboard is saved as a Power BI Project (jobintel_dashboard.pbip), which
stores every page and visual as a JSON file instead of inside one binary .pbix.
This script writes those JSON files, so the whole report layout lives in code:

    Tech Job Market, Salary Explorer, Skills, Geography, Job Listings, Data Quality

It only writes the *report* (pages, visuals, filters). It relies on the measures
and the 'Salary Band' column already defined in
jobintel_dashboard.SemanticModel/definition/tables/FACT_JOB_POSTING.tmdl.

Usage (from the project root, with Power BI Desktop CLOSED - it does not pick
up file changes while open, and saving from it would overwrite them):

    python src/dashboard/build_report.py

Then open jobintel_dashboard.pbip and click Home -> Refresh.

Re-running is safe: every visual is rewritten from scratch each time.
The pipeline stage counts on the Data Quality page are typed in below
(build_quality_page) - update them if the data is reloaded with new numbers.
"""
import json
import os
import sys

# Path to jobintel_dashboard.Report; defaults to the one in the project root.
REPORT = sys.argv[1] if len(sys.argv) > 1 else "jobintel_dashboard.Report"
PAGES = os.path.join(REPORT, "definition", "pages")

VISUAL_SCHEMA = ("https://developer.microsoft.com/json-schemas/fabric/item/report/"
                 "definition/visualContainer/2.5.0/schema.json")
PAGE_SCHEMA = ("https://developer.microsoft.com/json-schemas/fabric/item/report/"
               "definition/page/2.1.0/schema.json")

FACT = "FACT_JOB_POSTING"


# ---------- expression helpers ----------

def lit(value):
    return {"expr": {"Literal": {"Value": value}}}


def col(entity, prop):
    return {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def measure(name):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": FACT}}, "Property": name}}


def proj(field):
    inner = field.get("Column") or field.get("Measure")
    entity = inner["Expression"]["SourceRef"]["Entity"]
    return {"field": field,
            "queryRef": "{}.{}".format(entity, inner["Property"]),
            "nativeQueryRef": inner["Property"]}


def title(text):
    return {"title": [{"properties": {"show": lit("true"),
                                      "text": lit("'{}'".format(text))}}]}


def labels_on():
    return {"labels": [{"properties": {"show": lit("true")}}]}


# ---------- filters ----------

def topn_filter(name, entity, prop, by_measure, n=10):
    alias = entity[0].lower()
    return {
        "name": name,
        "field": col(entity, prop),
        "type": "TopN",
        "filter": {
            "Version": 2,
            "From": [
                {"Name": "subquery", "Type": 2, "Expression": {"Subquery": {"Query": {
                    "Version": 2,
                    "From": [{"Name": alias, "Entity": entity, "Type": 0},
                             {"Name": "m", "Entity": FACT, "Type": 0}],
                    "Select": [{"Column": {"Expression": {"SourceRef": {"Source": alias}},
                                           "Property": prop}, "Name": "field"}],
                    "OrderBy": [{"Direction": 2, "Expression": {"Measure": {
                        "Expression": {"SourceRef": {"Source": "m"}}, "Property": by_measure}}}],
                    "Top": n,
                }}}},
                {"Name": alias, "Entity": entity, "Type": 0},
            ],
            "Where": [{"Condition": {"In": {
                "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": alias}},
                                            "Property": prop}}],
                "Table": {"SourceRef": {"Source": "subquery"}},
            }}}],
        },
        "howCreated": "User",
    }


def min_salary_filter(name, minimum=20000):
    # ComparisonKind 2 = GreaterThanOrEqual
    return {
        "name": name,
        "field": col(FACT, "SALARY_MIN"),
        "type": "Advanced",
        "filter": {
            "Version": 2,
            "From": [{"Name": "f", "Entity": FACT, "Type": 0}],
            "Where": [{"Condition": {"Comparison": {
                "ComparisonKind": 2,
                "Left": {"Column": {"Expression": {"SourceRef": {"Source": "f"}},
                                    "Property": "SALARY_MIN"}},
                "Right": {"Literal": {"Value": "{}D".format(minimum)}},
            }}}],
        },
        "howCreated": "User",
    }


# ---------- visual builders ----------

def container(name, x, y, w, h, z, visual, filters=None):
    data = {"$schema": VISUAL_SCHEMA, "name": name,
            "position": {"x": x, "y": y, "z": z, "width": w, "height": h, "tabOrder": z},
            "visual": visual}
    if filters:
        data["filterConfig"] = {"filters": filters}
    return data


def card(field, caption):
    return {"visualType": "card",
            "query": {"queryState": {"Values": {"projections": [proj(field)]}}},
            "visualContainerObjects": title(caption),
            "drillFilterOtherVisuals": True}


def bar(category, values, caption, sort_by, kind="clusteredBarChart",
        series=None, direction="Descending"):
    query_state = {
        "Category": {"projections": [dict(proj(category), active=True)]},
        "Y": {"projections": [proj(v) for v in values]},
    }
    if series is not None:
        query_state["Series"] = {"projections": [proj(series)]}
    return {"visualType": kind,
            "query": {
                "queryState": query_state,
                "sortDefinition": {"sort": [{"field": sort_by, "direction": direction}],
                                   "isDefaultSort": True},
            },
            "objects": labels_on(),
            "visualContainerObjects": title(caption),
            "drillFilterOtherVisuals": True}


def table(fields, caption, sort_by=None, direction="Descending"):
    query = {"queryState": {"Values": {"projections": [proj(f) for f in fields]}}}
    if sort_by is not None:
        query["sortDefinition"] = {"sort": [{"field": sort_by, "direction": direction}],
                                   "isDefaultSort": True}
    return {"visualType": "tableEx",
            "query": query,
            "visualContainerObjects": title(caption),
            "drillFilterOtherVisuals": True}


def filled_map(location, color_value, tooltips, caption):
    """
    Azure Map with shaded state areas. Power BI converts the older Bing
    'filledMap' into this automatically on open, so it is generated directly.
    """
    return {"visualType": "azureMap",
            "query": {"queryState": {
                "Category": {"projections": [dict(proj(location), active=True)]},
                "Tooltips": {"projections": [proj(t) for t in tooltips]},
                "Y": {"projections": [proj(color_value)]},
            }},
            "objects": {
                "mapControls": [{"properties": {
                    "defaultStyle": lit("'road'"),
                    "showStylePicker": lit("false"),
                    "showNavigationControls": lit("false"),
                    "showSelectionControl": lit("false"),
                    "zoom": lit("1.97D"),
                    "centerLatitude": lit("52.22428530712375D"),
                    "centerLongitude": lit("-121.11334999999997D"),
                }}],
                "categoryLabels": [{"properties": {"show": lit("false")}}],
                "bubbleLayer": [{"properties": {"show": lit("false")}}],
                "filledMap": [{"properties": {"show": lit("true"),
                                              "mapTransparency": lit("40L")}}],
            },
            "visualContainerObjects": title(caption),
            "drillFilterOtherVisuals": True}


def tech_only_filter(name):
    """Page filter: ROLE_FAMILY is not blank (same as the one built by hand on page 1)."""
    return {
        "name": name,
        "field": col(FACT, "ROLE_FAMILY"),
        "type": "Categorical",
        "filter": {
            "Version": 2,
            "From": [{"Name": "f", "Entity": FACT, "Type": 0}],
            "Where": [{"Condition": {"Not": {"Expression": {"In": {
                "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "f"}},
                                            "Property": "ROLE_FAMILY"}}],
                "Values": [[{"Literal": {"Value": "null"}}]],
            }}}}}],
        },
        "howCreated": "User",
        "objects": {"general": [{"properties": {"isInvertedSelectionMode": lit("true")}}]},
    }


def write_page(name, display_name, filters=None):
    page_dir = os.path.join(PAGES, name)
    os.makedirs(page_dir, exist_ok=True)
    data = {"$schema": PAGE_SCHEMA, "name": name, "displayName": display_name,
            "displayOption": "FitToPage", "height": 1080, "width": 1920}
    if filters:
        data["filterConfig"] = {"filters": filters}
    with open(os.path.join(page_dir, "page.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return page_dir


def donut(category, value, caption):
    return {"visualType": "donutChart",
            "query": {"queryState": {
                "Category": {"projections": [dict(proj(category), active=True)]},
                "Y": {"projections": [proj(value)]},
            }},
            "objects": labels_on(),
            "visualContainerObjects": title(caption),
            "drillFilterOtherVisuals": True}


def slicer(field, caption, dropdown=False):
    visual = {"visualType": "slicer",
              "query": {"queryState": {"Values": {"projections": [dict(proj(field), active=True)]}}},
              "visualContainerObjects": title(caption),
              "drillFilterOtherVisuals": True}
    if dropdown:
        visual["objects"] = {"data": [{"properties": {"mode": lit("'Dropdown'")}}]}
    return visual


def textbox(lines):
    """lines: list of (text, size_pt, bold)."""
    paragraphs = []
    for text, size, bold in lines:
        style = {"fontSize": "{}pt".format(size)}
        if bold:
            style["fontWeight"] = "bold"
        paragraphs.append({"textRuns": [{"value": text, "textStyle": style}]})
    return {"visualType": "textbox",
            "objects": {"general": [{"properties": {"paragraphs": paragraphs}}]},
            "drillFilterOtherVisuals": True}


def write_visual(page_dir, data):
    folder = os.path.join(page_dir, "visuals", data["name"])
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "visual.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------- page 1: Tech Job Market ----------

def build_tech_page(page_dir):
    v = []
    v.append(container("t1title00000000000001", 20, 10, 1880, 70, 0, textbox([
        ("JobIntel — US Tech Job Market", 26, True),
        ("Technical roles only (jobs with a role family). Published and estimated salaries are shown separately.", 12, False),
    ])))

    # slicers down the left
    v.append(container("t1slicersource0000001", 20, 100, 260, 190, 1,
                       slicer(col(FACT, "SOURCE"), "Source")))
    v.append(container("t1slicerestimated0001", 20, 300, 260, 190, 2,
                       slicer(col(FACT, "IS_ESTIMATED"), "Salary is estimated")))
    v.append(container("t1slicerstate00000001", 20, 500, 260, 110, 3,
                       slicer(col("DIM_LOCATION", "STATE"), "State", dropdown=True)))

    # headline cards
    cards = [("Total Jobs", "Tech jobs"),
             ("Avg Salary Published", "Avg salary (published)"),
             ("Avg Salary Estimated", "Avg salary (estimated)"),
             ("% Estimated", "Share of estimated salaries")]
    for i, (m, caption) in enumerate(cards):
        v.append(container("t1card{:015d}".format(i + 1), 300 + i * 405, 100, 385, 150, 10 + i,
                           card(measure(m), caption)))

    # row 1 charts
    v.append(container("t1barrole000000000001", 300, 270, 790, 400, 20,
                       bar(col(FACT, "ROLE_FAMILY"), [measure("Total Jobs")],
                           "Jobs by role family", measure("Total Jobs"))))
    v.append(container("t1barsalary0000000001", 1110, 270, 790, 400, 21,
                       bar(col(FACT, "ROLE_FAMILY"),
                           [measure("Avg Salary Published"), measure("Avg Salary Estimated")],
                           "Average salary by role: published vs estimated",
                           measure("Avg Salary Published")),
                       filters=[min_salary_filter("t1fsalarymin00000001")]))

    # row 2 charts
    v.append(container("t1barstate00000000001", 300, 690, 520, 370, 30,
                       bar(col("DIM_LOCATION", "STATE"), [measure("Total Jobs")],
                           "Top 10 states", measure("Total Jobs")),
                       filters=[topn_filter("t1fstatetop10000001", "DIM_LOCATION", "STATE",
                                            "Total Jobs")]))
    v.append(container("t1barskill00000000001", 840, 690, 520, 370, 31,
                       bar(col("BRIDGE_JOB_SKILL", "SKILL"), [measure("Skill Mentions")],
                           "Top 10 skills mentioned", measure("Skill Mentions")),
                       filters=[topn_filter("t1fskilltop10000001", "BRIDGE_JOB_SKILL", "SKILL",
                                            "Skill Mentions")]))
    v.append(container("t1barcompany000000001", 1380, 690, 520, 370, 32,
                       bar(col("DIM_COMPANY", "COMPANY_NAME"), [measure("Total Jobs")],
                           "Top 10 hiring organizations", measure("Total Jobs")),
                       filters=[topn_filter("t1fcompanytop100001", "DIM_COMPANY", "COMPANY_NAME",
                                            "Total Jobs")]))

    for data in v:
        write_visual(page_dir, data)
    return len(v)


# ---------- page 2: Data Quality ----------

def build_quality_page(page_dir):
    v = []
    v.append(container("t2title00000000000001", 20, 10, 1880, 70, 0, textbox([
        ("JobIntel — Data Quality", 26, True),
        ("All 1,261 loaded jobs, including the ones without a role family.", 12, False),
    ])))

    cards = [("Total Jobs", "Jobs loaded"),
             ("Jobs Without Role Family", "Jobs without a role family"),
             ("% Estimated", "Share of estimated salaries")]
    for i, (m, caption) in enumerate(cards):
        v.append(container("t2card{:015d}".format(i + 1), 20 + i * 470, 100, 450, 150, 10 + i,
                           card(measure(m), caption)))

    v.append(container("t2textpipeline0000001", 1430, 100, 470, 460, 13, textbox([
        ("Pipeline stage counts", 16, True),
        ("1. Processed: 1,334 (USAJOBS 334 + Adzuna 1,000)", 12, False),
        ("2. Deduplicated: 1,261 (73 removed)", 12, False),
        ("3. Passed quality gate: 1,261 (0 quarantined)", 12, False),
        ("4. Loaded to Snowflake: 1,261", 12, False),
        ("", 12, False),
        ("Validated with src/quality/trace_job.py: every stage count matches, "
         "no field changed between processed data and Snowflake.", 11, False),
    ])))

    v.append(container("t2donutestimated00001", 20, 270, 450, 390, 20,
                       donut(col(FACT, "IS_ESTIMATED"), measure("Total Jobs"),
                             "Estimated vs published salary")))
    v.append(container("t2barsource0000000001", 490, 270, 920, 390, 21,
                       bar(col(FACT, "SOURCE"), [measure("Total Jobs")],
                           "Jobs by source", measure("Total Jobs"))))
    v.append(container("t2barrolecoverage0001", 20, 680, 920, 380, 30,
                       bar(col(FACT, "ROLE_FAMILY"), [measure("Total Jobs")],
                           "Role family coverage (blank = no tech family matched)",
                           measure("Total Jobs"))))

    v.append(container("t2textlimitations0001", 960, 680, 940, 380, 31, textbox([
        ("Known limitations", 16, True),
        ("• 680 of 1,261 jobs have no role family (mostly non-technical Adzuna postings); "
         "they are excluded from the Tech Job Market page.", 11, False),
        ("• Adzuna truncates job descriptions, so skill counts are low (235 mentions in total).", 11, False),
        ("• Company names are not cleaned: some Adzuna employers include extra text, "
         "e.g. \"SimVentions, Inc - Glassdoor ✪ 4.6\".", 11, False),
        ("• \"(Blank)\" in the states chart means jobs with no state in the source data.", 11, False),
        ("• One Adzuna salary (HelloTech, 40–57) is an hourly rate; it is filtered out of salary charts.", 11, False),
        ("• All jobs share one load date (2026-09-08); posting dates are not in the data yet.", 11, False),
    ])))

    for data in v:
        write_visual(page_dir, data)
    return len(v)


# ---------- page: Salary Explorer ----------

def build_salary_page(page_dir):
    v = []
    v.append(container("t3title00000000000001", 20, 10, 1880, 70, 0, textbox([
        ("Salary Explorer", 26, True),
        ("Technical roles only. Salary = midpoint of the posted min and max. "
         "Published (real) and estimated (Adzuna's prediction) are never mixed.", 12, False),
    ])))

    cards = [("Median Salary Published", "Median salary (published)"),
             ("Median Salary Estimated", "Median salary (estimated)"),
             ("Avg Salary Published", "Average salary (published)"),
             ("Published Jobs", "Jobs with a published salary"),
             ("Estimated Jobs", "Jobs with an estimated salary")]
    for i, (m, caption) in enumerate(cards):
        v.append(container("t3card{:015d}".format(i + 1), 20 + i * 376, 100, 360, 150, 10 + i,
                           card(measure(m), caption)))

    v.append(container("t3colsalaryband000001", 20, 270, 920, 390, 20,
                       bar(col(FACT, "Salary Band"),
                           [measure("Published Jobs"), measure("Estimated Jobs")],
                           "Salary distribution: published vs estimated",
                           col(FACT, "Salary Band"),
                           kind="clusteredColumnChart", direction="Ascending")))
    v.append(container("t3barpublishedrange01", 960, 270, 940, 390, 21,
                       bar(col(FACT, "ROLE_FAMILY"),
                           [measure("Avg Min Salary Published"),
                            measure("Avg Max Salary Published")],
                           "Published salary range by role (average min and max)",
                           measure("Avg Max Salary Published"))))
    v.append(container("t3tablerole0000000001", 20, 680, 1300, 380, 30,
                       table([col(FACT, "ROLE_FAMILY"), measure("Total Jobs"),
                              measure("Published Jobs"), measure("Avg Salary Published"),
                              measure("Median Salary Published"),
                              measure("Avg Salary Estimated")],
                             "Salary summary by role family", measure("Total Jobs"))))
    v.append(container("t3slicersource0000001", 1340, 680, 560, 160, 31,
                       slicer(col(FACT, "SOURCE"), "Source")))
    v.append(container("t3textnote00000000001", 1340, 860, 560, 200, 32, textbox([
        ("How to read this page", 14, True),
        ("• Roles with only a handful of jobs (e.g. data_scientist, data_engineer) "
         "have unstable averages; check the job counts in the table.", 11, False),
        ("• One hourly-rate salary (under $20K) is excluded by the page filter.", 11, False),
        ("• USAJOBS salaries are always published; most Adzuna salaries are estimates.", 11, False),
    ])))

    for data in v:
        write_visual(page_dir, data)
    return len(v)


# ---------- page: Skills ----------

def build_skills_page(page_dir):
    v = []
    v.append(container("t4title00000000000001", 20, 10, 1880, 70, 0, textbox([
        ("Skills in Demand", 26, True),
        ("Technical roles only. Skills are matched against the job description text.", 12, False),
    ])))

    cards = [("Skill Mentions", "Skill mentions"),
             ("Jobs With Skills", "Jobs mentioning at least one skill"),
             ("% Jobs With Skills", "Share of jobs with a skill found")]
    for i, (m, caption) in enumerate(cards):
        v.append(container("t4card{:015d}".format(i + 1), 20 + i * 470, 100, 450, 150, 10 + i,
                           card(measure(m), caption)))
    v.append(container("t4textnote00000000001", 1430, 100, 470, 150, 13, textbox([
        ("Why skill counts are low", 14, True),
        ("Adzuna cuts job descriptions short, so many skills are never visible "
         "to the extractor. USAJOBS descriptions are complete.", 11, False),
    ])))

    v.append(container("t4barskilltop15000001", 20, 270, 600, 790, 20,
                       bar(col("BRIDGE_JOB_SKILL", "SKILL"), [measure("Skill Mentions")],
                           "Top 15 skills", measure("Skill Mentions")),
                       filters=[topn_filter("t4fskilltop15000001", "BRIDGE_JOB_SKILL", "SKILL",
                                            "Skill Mentions", n=15)]))
    v.append(container("t4barskillbyrole00001", 640, 270, 1260, 390, 21,
                       bar(col("BRIDGE_JOB_SKILL", "SKILL"), [measure("Skill Mentions")],
                           "Top 10 skills by role family", measure("Skill Mentions"),
                           kind="barChart", series=col(FACT, "ROLE_FAMILY")),
                       filters=[topn_filter("t4fskillroletop1001", "BRIDGE_JOB_SKILL", "SKILL",
                                            "Skill Mentions")]))
    v.append(container("t4barskillbysource001", 640, 680, 800, 380, 30,
                       bar(col("BRIDGE_JOB_SKILL", "SKILL"), [measure("Skill Mentions")],
                           "Top 10 skills by source", measure("Skill Mentions"),
                           series=col(FACT, "SOURCE")),
                       filters=[topn_filter("t4fskillsrctop10001", "BRIDGE_JOB_SKILL", "SKILL",
                                            "Skill Mentions")]))
    v.append(container("t4slicerrole000000001", 1460, 680, 440, 120, 31,
                       slicer(col(FACT, "ROLE_FAMILY"), "Role family", dropdown=True)))
    v.append(container("t4slicersource0000001", 1460, 820, 440, 240, 32,
                       slicer(col(FACT, "SOURCE"), "Source")))

    for data in v:
        write_visual(page_dir, data)
    return len(v)


# ---------- page: Geography ----------

def build_geo_page(page_dir):
    v = []
    v.append(container("t5title00000000000001", 20, 10, 1880, 70, 0, textbox([
        ("Where the Tech Jobs Are", 26, True),
        ("Technical roles only. Darker states have more job postings; hover a state for salaries.", 12, False),
    ])))

    v.append(container("t5mapstate00000000001", 20, 100, 1140, 620, 10,
                       filled_map(col("DIM_LOCATION", "STATE"), measure("Total Jobs"),
                                  [measure("Avg Salary Published"),
                                   measure("Avg Salary Estimated")],
                                  "Tech jobs by state")))
    v.append(container("t5tablestate000000001", 1180, 100, 720, 620, 11,
                       table([col("DIM_LOCATION", "STATE"), measure("Total Jobs"),
                              measure("Published Jobs"), measure("Avg Salary Published"),
                              measure("Avg Salary Estimated")],
                             "Jobs and salary by state", measure("Total Jobs"))))
    v.append(container("t5barcitytop100000001", 20, 740, 920, 320, 20,
                       bar(col("DIM_LOCATION", "CITY"), [measure("Total Jobs")],
                           "Top 10 cities", measure("Total Jobs")),
                       filters=[topn_filter("t5fcitytop10000001", "DIM_LOCATION", "CITY",
                                            "Total Jobs")]))
    v.append(container("t5barstatesalary00001", 960, 740, 940, 320, 21,
                       bar(col("DIM_LOCATION", "STATE"), [measure("Avg Salary Published")],
                           "Average published salary in the 10 largest states",
                           measure("Avg Salary Published")),
                       filters=[topn_filter("t5fstatetop10000001", "DIM_LOCATION", "STATE",
                                            "Total Jobs")]))

    for data in v:
        write_visual(page_dir, data)
    return len(v)


# ---------- page: Job Listings ----------

def build_listings_page(page_dir):
    v = []
    v.append(container("t6title00000000000001", 20, 10, 1880, 70, 0, textbox([
        ("Job Listings", 26, True),
        ("Every loaded job (including non-technical ones). Use the filters to narrow the list.", 12, False),
    ])))

    slicers = [(col(FACT, "ROLE_FAMILY"), "Role family"),
               (col(FACT, "SOURCE"), "Source"),
               (col("DIM_LOCATION", "STATE"), "State"),
               (col(FACT, "IS_ESTIMATED"), "Salary is estimated")]
    for i, (field, caption) in enumerate(slicers):
        v.append(container("t6slicer{:013d}".format(i + 1), 20 + i * 380, 100, 360, 110, 10 + i,
                           slicer(field, caption, dropdown=True)))
    v.append(container("t6card000000000000001", 1540, 100, 360, 110, 14,
                       card(measure("Total Jobs"), "Jobs shown")))

    v.append(container("t6tablejobs0000000001", 20, 230, 1880, 830, 20,
                       table([col(FACT, "TITLE"), col("DIM_COMPANY", "COMPANY_NAME"),
                              col("DIM_LOCATION", "CITY"), col("DIM_LOCATION", "STATE"),
                              col(FACT, "ROLE_FAMILY"), col(FACT, "SALARY_MIN"),
                              col(FACT, "SALARY_MAX"), col(FACT, "IS_ESTIMATED"),
                              col(FACT, "SOURCE"), col(FACT, "JOB_ID")],
                             "All jobs", col(FACT, "TITLE"), direction="Ascending")))

    for data in v:
        write_visual(page_dir, data)
    return len(v)


def main():
    with open(os.path.join(PAGES, "pages.json"), encoding="utf-8") as f:
        pages = json.load(f)

    tech_page = None
    for page_name in pages["pageOrder"]:
        with open(os.path.join(PAGES, page_name, "page.json"), encoding="utf-8") as f:
            if json.load(f).get("displayName") == "Tech Job Market":
                tech_page = page_name
    if tech_page is None:
        sys.exit("Tech Job Market page not found")

    counts = {"Tech Job Market": build_tech_page(os.path.join(PAGES, tech_page))}

    # (folder name, display name, page filters, builder)
    new_pages = [
        ("salaryexplorer00000001", "Salary Explorer",
         [tech_only_filter("t3ftechonly00000001"), min_salary_filter("t3fsalarymin0000001")],
         build_salary_page),
        ("skills0000000000000001", "Skills",
         [tech_only_filter("t4ftechonly00000001")], build_skills_page),
        ("geography0000000000001", "Geography",
         [tech_only_filter("t5ftechonly00000001")], build_geo_page),
        ("joblistings00000000001", "Job Listings", None, build_listings_page),
        ("dataquality000000000001", "Data Quality", None, build_quality_page),
    ]
    for name, display, filters, builder in new_pages:
        counts[display] = builder(write_page(name, display, filters))

    pages["pageOrder"] = [tech_page] + [p[0] for p in new_pages]
    pages["activePageName"] = tech_page
    with open(os.path.join(PAGES, "pages.json"), "w", encoding="utf-8") as f:
        json.dump(pages, f, indent=2)

    for display, n in counts.items():
        print("{:18} {} visuals".format(display, n))


if __name__ == "__main__":
    main()
