"""
ER Wait-Time Scorecard: validation and statistics in Python
===========================================================
Rebuilds the Power BI data model from the raw Ontario Health exports and
reproduces the key numbers in the report, so they can be checked independently.

Run from the repository folder:   python er_analysis.py
Needs: pandas, numpy, openpyxl, statsmodels, matplotlib
       (pip install pandas numpy openpyxl statsmodels matplotlib)
"""
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

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


# ---- 5. Is the Credit Valley gap explained by volume or patient mix? (regression) ----
# One row per site-month for Mississauga and Credit Valley (2 sites x 13 months = 26 rows;
# Queensway is an urgent care centre with no admissions). The site coefficient is Credit
# Valley's gap in hours relative to Mississauga. If busier months or a sicker patient mix
# explained the gap, it would shrink once those are in the model. HC3 robust standard errors
# because the sample is small. Exploratory: 26 rows, and months within a site aren't independent.
wide = (trends[trends["Location"].isin(["Mississauga", "Credit Valley", "Ontario"])]
        .pivot_table(index=["Location", "Date"], columns=["Measure", "Metric"], values="Value"))
wide.columns = [f"{m}_{k}" for m, k in wide.columns]
wide = wide.reset_index()
ontario = wide[wide["Location"] == "Ontario"].set_index("Date")
reg = wide[wide["Location"] != "Ontario"].copy()
reg["site"] = pd.Categorical(reg["Location"], ["Mississauga", "Credit Valley"])
reg["visits_k"] = reg["FirstAssessment_vol"] / 1000                                    # monthly visits (thousands)
reg["pct_admitted"] = 100 * reg["LOSadmitted_vol"] / reg["FirstAssessment_vol"]        # % of visits admitted
reg["pct_high"] = 100 * reg["LOShigh_vol"] / reg["FirstAssessment_vol"]                # % high urgency, sent home
reg["ontario_admitted"] = reg["Date"].map(ontario["LOSadmitted_avg"])                  # province-wide monthly level

MODELS = [
    ("Admitted patients' time in ED", "LOSadmitted_avg", "unadjusted", ""),
    ("Admitted patients' time in ED", "LOSadmitted_avg", "+ volume and patient mix", " + visits_k + pct_admitted + pct_high"),
    ("Admitted patients' time in ED", "LOSadmitted_avg", "+ mix + Ontario monthly level", " + visits_k + pct_admitted + pct_high + ontario_admitted"),
    ("Time to first doctor assessment", "FirstAssessment_avg", "unadjusted", ""),
    ("Time to first doctor assessment", "FirstAssessment_avg", "+ volume and patient mix", " + visits_k + pct_admitted + pct_high"),
]
print("\nCredit Valley's gap vs Mississauga, before and after adjustment (OLS, n = 26 site-months)")
reg_rows = []
for outcome, col, model, extra in MODELS:
    fit = smf.ols(f"{col} ~ site{extra}", data=reg).fit(cov_type="HC3")
    term = "site[T.Credit Valley]"
    lo, hi = fit.conf_int().loc[term]
    reg_rows.append({"Outcome": outcome, "Model": model, "Gap (h)": fit.params[term],
                     "95% CI": f"{lo:.1f} to {hi:.1f}", "p": f"{fit.pvalues[term]:.3g}", "R²": fit.rsquared})
print(pd.DataFrame(reg_rows).round(2).to_string(index=False))
full = smf.ols("LOSadmitted_avg ~ site + visits_k + pct_admitted + pct_high", data=reg).fit(cov_type="HC3")
print("\nAdjusted model for admitted patients (coefficients in hours):")
print(full.summary().tables[1])

# Figure: the gap before and after adjustment (saved to images/regression-gap.png)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

res = pd.DataFrame(reg_rows)
res[["lo", "hi"]] = res["95% CI"].str.split(" to ", expand=True).astype(float)
fig, axes = plt.subplots(1, 2, figsize=(12, 3.8), gridspec_kw={"width_ratios": [3, 2]})
for ax, outcome in zip(axes, res["Outcome"].unique()):
    r = res[res["Outcome"] == outcome].iloc[::-1].reset_index(drop=True)
    ax.errorbar(r["Gap (h)"], r.index, xerr=[r["Gap (h)"] - r["lo"], r["hi"] - r["Gap (h)"]],
                fmt="o", color="#426871", ecolor="#87ACB6", elinewidth=2, capsize=4, ms=8)
    for i, g in enumerate(r["Gap (h)"]):
        ax.annotate(f"{g:.1f} h", (g, i), textcoords="offset points", xytext=(0, 9), ha="center", fontsize=9)
    ax.axvline(0, color="#6B7280", lw=1, ls="--")
    ax.set_yticks(r.index, [m[0].upper() + m[1:] for m in r["Model"]])
    ax.set_ylim(-0.6, len(r) - 0.4)
    ax.set_xlim(left=min(-0.5, r["lo"].min() - 0.5))
    ax.set_title(outcome, fontsize=11, loc="left")
    ax.set_xlabel("Credit Valley minus Mississauga, hours (95% CI)", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
fig.suptitle("Credit Valley's longer waits remain after adjusting for volume and patient mix "
             "(26 site-months, Jul 2025 to Jul 2026)", fontsize=11.5, x=0.01, ha="left")
fig.tight_layout(rect=(0, 0, 1, 0.93), w_pad=3)
fig.savefig(Path(__file__).parent / "images" / "regression-gap.png", dpi=200, bbox_inches="tight")
print("\nSaved images/regression-gap.png")
