"""
ER Wait-Time Scorecard: validation and statistics in Python
===========================================================
Rebuilds the Power BI data model from the raw Ontario Health exports and
reproduces the key numbers in the report, so they can be checked independently.

Run from the repository folder:   python er_analysis.py
Needs: pandas, numpy, openpyxl  (pip install pandas numpy openpyxl)
"""
from pathlib import Path
import numpy as np
import pandas as pd

DATA = Path(__file__).parent / "data"
SITES = {"Mississauga": "Mississauga", "CreditValley": "Credit Valley", "Queensway": "Queensway (UCC)"}
LABELS = {
    "FirstAssessment": "Time to first doctor assessment",
    "LOSlow": "Length of stay: low urgency, sent home",
    "LOShigh": "Length of stay: high urgency, sent home",
    "LOSadmitted": "Length of stay: admitted patients",
}


# ---- 1. Combine the 30 trend exports into one tidy table (same steps as Power Query) ----
def load_trends() -> pd.DataFrame:
    rows = []
    for f in sorted((DATA / "trends").glob("*.csv")):
        hospital, measure, metric = f.stem.split("_")          # e.g. CreditValley_LOSadmitted_avg
        raw = pd.read_csv(f, skiprows=4, dtype=str)            # skip title, label, blank, hospital name
        raw = raw[raw.iloc[:, 0].str.match(r"^20\d{4}$", na=False)]   # keep only month rows
        raw.columns = ["Month", "Ontario", "Site"]
        for col, loc in (("Ontario", "Ontario"), ("Site", SITES[hospital])):
            part = raw[["Month", col]].rename(columns={col: "Value"})
            part["Location"], part["Measure"], part["Metric"] = loc, measure, metric
            rows.append(part)
    df = pd.concat(rows, ignore_index=True)
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")  # "NV" / "NDA" become blank
    df["Date"] = pd.to_datetime(df["Month"] + "01", format="%Y%m%d")
    df = df.drop(columns="Month").drop_duplicates()            # Ontario appears once per file
    return df[["Date", "Location", "Measure", "Metric", "Value"]]


def load_rankings() -> pd.DataFrame:
    sheets = pd.read_excel(DATA / "hospital_rankings_2026-07.xlsx", sheet_name=None)
    out = []
    for name, sheet in sheets.items():
        sheet = sheet.iloc[:, :2]
        sheet.columns = ["Hospital", "Avg_Hours"]
        sheet["Measure"] = "FirstAssessment" if name.startswith("FirstAss") else name
        out.append(sheet)
    return pd.concat(out, ignore_index=True).dropna()


trends = load_trends()
rankings = load_rankings()
print(f"Tidy trend table: {len(trends)} rows (Power BI: 533)")
print(f"Rankings table:   {len(rankings)} rows\n")

latest = trends["Date"].max()
prior = latest - pd.DateOffset(years=1)


def value(loc, measure, metric, date=latest):
    s = trends.query("Location == @loc and Measure == @measure and Metric == @metric and Date == @date")["Value"]
    return s.iloc[0] if len(s) else np.nan


def province_rank(loc, measure):
    name = {"Mississauga": "Trillium Health Partners-Mississauga",
            "Credit Valley": "Trillium Health Partners-Credit Valley",
            "Queensway (UCC)": "Trillium Health Partners-Queensway Hlth"}[loc]
    r = rankings[(rankings["Measure"] == measure) & (rankings["Hospital"] != "Ontario")]
    mine = r.loc[r["Hospital"] == name, "Avg_Hours"]
    if mine.empty:
        return ""
    return f"#{(r['Avg_Hours'] < mine.iloc[0]).sum() + 1} of {len(r)}"


# ---- 2. Scorecard (matches the Scorecard page and hidden QA page) ----
rows = []
for measure, label in LABELS.items():
    for loc in ["Credit Valley", "Mississauga", "Queensway (UCC)"]:
        site, ont = value(loc, measure, "avg"), value("Ontario", measure, "avg")
        rows.append({
            "Measure": label, "Site": loc,
            "Site (h)": site, "Ontario (h)": ont, "Gap (h)": site - ont,
            "% within target": value(loc, measure, "pct"),
            "Ontario rank": province_rank(loc, measure),
            "vs last year (h)": site - value(loc, measure, "avg", prior),
        })
scorecard = pd.DataFrame(rows).round(1)
print(f"Scorecard, {latest:%B %Y}")
print(scorecard.to_string(index=False), "\n")

# ---- 3. Patient mix: share of visits by patient group (13 months) ----
vol = trends[trends["Metric"] == "vol"].pivot_table(index="Location", columns="Measure", values="Value", aggfunc="sum")
mix = vol[["LOSlow", "LOShigh", "LOSadmitted"]].div(vol["FirstAssessment"], axis=0).mul(100).round(1)
mix["Visits per month"] = (vol["FirstAssessment"] / 13).round(0)
print("Patient mix (% of total ED visits)")
print(mix.fillna(0).to_string(), "\n")

# ---- 4. Do busier months mean longer waits? (Pearson r, 13 months per site) ----
print("Correlation between monthly ED visits and average hours (n = 13 months)")
for loc in ["Credit Valley", "Mississauga"]:
    visits = trends.query("Location == @loc and Measure == 'FirstAssessment' and Metric == 'vol'").set_index("Date")["Value"]
    out = []
    for measure in LABELS:
        hours = trends.query("Location == @loc and Measure == @measure and Metric == 'avg'").set_index("Date")["Value"]
        out.append(f"{measure} r = {visits.corr(hours):+.2f}")
    print(f"  {loc:14s} " + " | ".join(out))

median_admitted = rankings.query("Measure == 'LOSadmitted' and Hospital != 'Ontario'")["Avg_Hours"].median()
print(f"\nMedian Ontario ED, admitted patients' length of stay: {median_admitted:.1f} h")
