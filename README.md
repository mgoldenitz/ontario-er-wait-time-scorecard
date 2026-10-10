# Ontario ER Wait-Time Scorecard: Trillium Health Partners

A five-page Power BI scorecard comparing emergency department (ED) wait times at Trillium Health Partners' three Mississauga-area sites with the Ontario average, provincial targets and neighbouring hospitals. It uses 13 months of public Ontario Health data (July 2025 to July 2026) and a provincial ranking of 150+ EDs.

![Scorecard page](images/scorecard.png)

## Key findings

- **Admitted patients wait longest.** Only **15.4%** of admitted patients at Credit Valley and **27.4%** at Mississauga leave the ED within the 8-hour target (Ontario: 28.2%; provincial goal: 90%).
- **Credit Valley ranks in the bottom fifth of Ontario EDs on every measure**, including **#147 of 154** for admitted patients' time in the ED (26.0 h vs 17.7 h provincially).
- **The problem is regional.** Nearby Osler Etobicoke (27.2 h, #148) and Brampton Civic (30.1 h, #150) rank even lower, while Humber River (13.3 h) and Halton Milton (16.2 h) beat the Ontario average. The pattern points to inpatient bed pressure across Peel.
- **Volume and patient mix don't explain the gap.** Mississauga and Credit Valley each see about **9,300–9,400 visits a month**, with about **17%** of patients admitted at each, yet Credit Valley waits longer on every measure. A regression across 26 site-months confirms it: Credit Valley's admitted patients spend **7.3 h** longer in the ED than Mississauga's, and after adjusting for monthly volume and patient mix the gap is still **8.3 h** (95% CI 2.2 to 14.5).
- **Busier months slow the front door, not admissions.** Time to first doctor rises with monthly volume (r = 0.48–0.62), but admitted patients' time in the ED doesn't (r = −0.10 to −0.60). That's consistent with bed availability, not ED demand, driving admitted-patient delays.
- **Mississauga improved.** Its admitted patients' average ED time fell by **3.9 h** year over year, from a peak of 32.0 h in September 2025 to 20.9 h in July 2026.

With 13 months per site, the volume–wait patterns and the regression are exploratory rather than proof of cause.

## Report pages

| Page | What it shows |
|---|---|
| **Scorecard** | KPI cards and a table for the selected site: value vs Ontario, gap, % within target, Met/Near/Missed status, provincial rank, change vs last year |
| **Trends** | 13-month trend for any measure: selected site vs Ontario, plus % within target against the 90% goal |
| **Province ranking** | Every Ontario ED from shortest to longest wait, and Trillium vs neighbouring EDs (Peel, Halton, west Toronto) |
| **Volume & patient mix** | Share of visits by patient type, monthly visits, and a scatter plot of monthly volume vs wait time |
| **Methods & caveats** | Data source, definitions, how the report was built, and limitations |

![Trends page](images/trends.png)
![Province ranking page](images/province-ranking.png)
![Volume and patient mix page](images/volume-patient-mix.png)

![Regression: Credit Valley's gap before and after adjustment](images/regression-gap.png)

*Credit Valley's gap compared with Mississauga, with 95% confidence intervals (OLS, 26 site-months). Adjusting for monthly volume and patient mix doesn't shrink it, so the gap isn't explained by Credit Valley being busier or seeing sicker patients. Made by `er_analysis.py`.*

## Tools and methods

- **Power Query:** combined 30 CSV exports from a folder, split file names into site, measure and metric, converted `202507`-style months to dates, handled "NV" and "NDA" codes, unpivoted so Ontario becomes its own row (533 rows), and stacked a 4-sheet ranking workbook into one table
- **Data model:** a measure lookup table (labels, targets, sort order) with one-to-many relationships to the trend and ranking tables
- **DAX:** latest-month values, Ontario benchmark (`CALCULATE`), gap to Ontario, target status, provincial rank with ties, year-over-year change (`EDATE`), dynamic titles, and colour measures for conditional formatting
- **Design:** synced slicers, edited visual interactions, dynamic chart titles, a constant goal line, and a custom theme shared with my previous project
- **Python** (pandas): `er_analysis.py` rebuilds the data model from the raw exports and reproduces every number in the report, including the patient mix and the volume–wait correlations
- **Regression** (statsmodels): ordinary least squares with robust (HC3) standard errors, testing whether Credit Valley's gap shrinks once monthly volume, share admitted and share of high-urgency patients are controlled for. It doesn't: the admitted-patient gap goes from 7.3 h unadjusted to 8.3 h adjusted (9.4 h when Ontario's monthly level is also included), and the time-to-first-doctor gap stays at about 0.9 h
- **Validation:** a hidden QA page in the report, cross-checked against the Python output

## Repository contents

| File | Description |
|---|---|
| `ER_Wait_Time_Scorecard.pbix` | Power BI report (open with Power BI Desktop) |
| `Goldenitz_ER_Wait_Time_Scorecard.pdf` | Static PDF of all five pages |
| `er_analysis.py` | Python validation, statistics and regression |
| `data/trends/` | 30 monthly CSV exports, named `Site_Measure_Metric.csv` (avg = average hours, pct = % within target, vol = patient count) |
| `data/hospital_rankings_2026-07.xlsx` | July 2026 hospital comparison table, one sheet per measure |
| `images/` | Page screenshots and the regression chart |

## How to run

**Power BI:** open the `.pbix` in Power BI Desktop. To refresh, go to **Transform data → Data source settings** and point the two sources to your copies of `data/trends/` and `data/hospital_rankings_2026-07.xlsx`.

**Python:** install pandas, numpy, openpyxl, statsmodels and matplotlib (`pip install pandas numpy openpyxl statsmodels matplotlib`), then run `python er_analysis.py` from the repository folder.

## Data

Ontario Health, [Time Spent in Emergency Departments](https://ontariohealth.ca/system/reporting/performance/time-spent-in-emergency-departments), based on the National Ambulatory Care Reporting System (NACRS), Canadian Institute for Health Information (CIHI). Exported September 2026. All data is public and aggregated; no patient-level data was used.

**Definitions:** low urgency = CTAS 4–5 (target 4 h), high urgency = CTAS 1–3 not admitted (target 8 h), admitted patients (target 8 h). The provincial goal is 90% of patients within target. Queensway Health Centre is an urgent care centre with no admissions, so it isn't directly comparable to a full ED.

## Author

**Michael Goldenitz** · Applied Data Analytics and Visualization, Sheridan College · HBSc Psychology and Philosophy, University of Toronto Mississauga
[LinkedIn](https://www.linkedin.com/in/michael-goldenitz-790509265/) · [GitHub](https://github.com/mgoldenitz)
