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