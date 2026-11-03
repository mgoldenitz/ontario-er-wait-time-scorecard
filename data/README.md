# Data

The raw Ontario Health exports are not stored in this repository. Ontario Health's [Terms & Conditions](https://ontariohealth.ca/terms-conditions.html) require written permission to reproduce content from its website, except for personal use. To rebuild the report or run `er_analysis.py`, download the files yourself and put them in this folder.

Source: Ontario Health, [Time Spent in Emergency Departments](https://ontariohealth.ca/system/reporting/performance/time-spent-in-emergency-departments) (NACRS data from the Canadian Institute for Health Information). The files used were exported in September 2026.

1. Monthly trends, July 2025 to July 2026. For Mississauga Hospital, Credit Valley Hospital and Queensway Health Centre, open each measure (time to first assessment; time spent in the ED for low-urgency, high-urgency and admitted patients) and use Export to CSV for the average hours, the percentage within target and the patient count. Save each file in `data/trends/` as `Site_Measure_Metric.csv`, for example `CreditValley_LOSadmitted_avg.csv`. Site is `CreditValley`, `Mississauga` or `Queensway`; Measure is `FirstAssessment`, `LOSlow`, `LOShigh` or `LOSadmitted`; Metric is `avg`, `pct` or `vol`. Queensway has no admitted-patient files, so there are 30 files in all.
2. Hospital comparison, July 2026. Export the provincial ranking table for each of the four measures and save them as one workbook, one sheet per measure, at `data/hospital_rankings_2026-07.xlsx`.
