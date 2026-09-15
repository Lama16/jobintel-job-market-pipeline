# Data Sources — JobIntel

## Included Sources

### USAJOBS API
- **Access:** Free API key, registered via developer.usajobs.gov
- **Filter used:** JobCategoryCode = 2210 (Information Technology Management)
- **Verified count:** 330 postings returned (tested 2026-09-06)
- **Why included:** Official US federal job board, structured data, real published salary ranges

### Adzuna API
- **Access:** Free developer tier, registered via developer.adzuna.com
- **Filter used:** category = it-jobs
- **Verified count:** 463,330 postings available (tested 2026-09-06)
- **Known limitation:** Adzuna's "it-jobs" category is broader than expected — sample review
  found non-technical postings included (e.g. HVAC Technician, Material Handler, Digital
  Prepress Technician). This will be addressed during the Week 2 standardisation/filtering
  step using our controlled role-family vocabulary, not at the collection stage.
- **Why included:** Covers the broader private-sector market, complements USAJOBS

## Excluded Sources

| Source | Reason for exclusion |
|---|---|
| LinkedIn | Terms of service prohibit automated/programmatic data collection |
| Indeed | Terms of service prohibit automated/programmatic data collection |
| Glassdoor | Terms of service prohibit automated/programmatic data collection |

## Notes
- Both sources verified live and returning real data before proceeding to Week 2.
- USAJOBS JobCategoryCode may be expanded later (e.g. adding 1550, 0854/0855) after
  reviewing the full official code list.

## Known Limitations

**Adzuna description truncation:** Adzuna's API returns job descriptions
truncated at roughly 300-400 characters, often ending mid-sentence. This
means skill extraction from Adzuna postings is systematically less complete
than from USAJOBS, whose QualificationSummary field is returned in full.
Verified by inspecting raw description fields directly (e.g. job ID
5870299019, description ends "...and…"). This is a source limitation, not
a defect in the extraction logic.