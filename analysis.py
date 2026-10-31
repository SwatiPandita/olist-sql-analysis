"""Statistics layer: confidence intervals, adjusted effect of late delivery, robustness, sizing.
Run AFTER run_sql.py.   Usage: python analysis.py
Needs: pip install -r requirements.txt
"""
import sqlite3, warnings
import numpy as np, pandas as pd, patsy
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
from statsmodels.stats.proportion import proportion_confint, proportions_ztest
from sklearn.linear_model import LogisticRegression

warnings.filterwarnings("ignore")
rng = np.random.default_rng(42)
OUT = []
def say(*a):
    line = " ".join(str(x) for x in a); print(line); OUT.append(line)

con = sqlite3.connect("olist.db")
df = pd.read_sql_query("SELECT * FROM order_facts", con)
df["late"] = (df["delay_days"] > 0).astype(int)
say(f"Delivered orders: {len(df):,} | late: {df['late'].mean():.1%}")

# ---------- 1. Low-review rate by delay group, with 95% confidence intervals ----------
d = df.dropna(subset=["review_score", "items_price", "freight", "avg_weight_g"]).copy()
d["low_review"] = (d["review_score"] <= 2).astype(int)
say(f"\n1) Orders with a review and complete item data: {len(d):,}")
rows = []
for g, sub in d.groupby("delay_group"):
    k, n = sub["low_review"].sum(), len(sub)
    lo, hi = proportion_confint(k, n, method="wilson")
    rows.append((g, n, k / n * 100, lo * 100, hi * 100))
    say(f"   {g:<16} n={n:>6,}  1-2 star: {k/n*100:5.1f}%  (95% CI {lo*100:.1f}% to {hi*100:.1f}%)")
ci = pd.DataFrame(rows, columns=["group", "n", "pct", "lo", "hi"])

# ---------- 2. Adjusted effect (logistic regression) ----------
rhs = ("C(delay_group, Treatment(reference='1 On time')) + np.log1p(items_price) + np.log1p(freight)"
       " + np.log1p(avg_weight_g) + n_items + C(customer_state)")
model = smf.logit("low_review ~ " + rhs, data=d).fit(disp=0)
say("\n2) Logistic regression: chance of a 1-2 star review")
say("   Controls: price, freight, product weight, items in order, customer state")
for name in model.params.index:
    if "delay_group" in name:
        orr = np.exp(model.params[name]); lo, hi = np.exp(model.conf_int().loc[name])
        label = name.split("[T.")[1].rstrip("]")
        say(f"   {label:<16} odds ratio {orr:6.1f}  (95% CI {lo:.1f} to {hi:.1f}) vs on-time")

late_rows = d[d["delay_group"] != "1 On time"]
cf = late_rows.copy(); cf["delay_group"] = "1 On time"
att = model.predict(late_rows).mean() - model.predict(cf).mean()
say(f"   Late orders: actual predicted low-review rate {model.predict(late_rows).mean():.1%}"
    f" vs {model.predict(cf).mean():.1%} if the same orders had arrived on time")
say(f"   => adjusted effect of lateness: +{att*100:.1f} percentage points")

# bootstrap CI for that effect
y, X = patsy.dmatrices("low_review ~ " + rhs, d, return_type="dataframe")
y = y.values.ravel()
dcols = [c for c in X.columns if "delay_group" in c]
Xcf = X.copy(); Xcf[dcols] = 0
is_late = (d["delay_group"] != "1 On time").values
atts = []
for _ in range(100):
    idx = rng.integers(0, len(X), len(X))
    lr = LogisticRegression(penalty=None, max_iter=1000).fit(X.values[idx], y[idx])
    li = idx[is_late[idx]]
    atts.append(lr.predict_proba(X.values[li])[:, 1].mean() - lr.predict_proba(Xcf.values[li])[:, 1].mean())
lo, hi = np.percentile(atts, [2.5, 97.5])
say(f"   bootstrap 95% CI for the effect (100 resamples): +{lo*100:.1f} to +{hi*100:.1f} points")

# ---------- 3. Robustness ----------
say("\n3) Robustness checks")
top_states = d["customer_state"].value_counts().head(8).index
say("   a) Same comparison inside each big state (does the gap hold everywhere?)")
for s in top_states:
    sub = d[d["customer_state"] == s]
    on, lt = sub[sub["late"] == 0]["low_review"], sub[sub["late"] == 1]["low_review"]
    say(f"      {s}: on-time {on.mean()*100:4.1f}% (n={len(on):,}) vs late {lt.mean()*100:4.1f}% (n={len(lt):,})"
        f"  gap {100*(lt.mean()-on.mean()):+.1f} pts")
single = d[d["n_items"] == 1]
m1 = smf.logit("low_review ~ " + rhs.replace(" + n_items", ""), data=single).fit(disp=0)
for name in m1.params.index:
    if "delay_group" in name and "4+" in name:
        say(f"   b) Single-item orders only (n={len(single):,}): 4+ days late odds ratio "
            f"{np.exp(m1.params[name]):.1f} (95% CI {np.exp(m1.conf_int().loc[name][0]):.1f} to "
            f"{np.exp(m1.conf_int().loc[name][1]):.1f})")

# ---------- 4. Repeat purchase within 180 days of the first delivery ----------
say("\n4) Repeat purchase (180 days, new order placed after first delivery)")
o = df.sort_values(["customer_unique_id", "purchase_ts"]).copy()
o["purchase_ts"] = pd.to_datetime(o["purchase_ts"]); o["delivered_ts"] = pd.to_datetime(o["delivered_ts"])
o["rn"] = o.groupby("customer_unique_id").cumcount() + 1
first = o[o["rn"] == 1].copy()
later = o[o["rn"] > 1][["customer_unique_id", "purchase_ts"]].rename(columns={"purchase_ts": "later_ts"})
m = first.merge(later, on="customer_unique_id", how="left")
m["ok"] = (m["later_ts"] > m["delivered_ts"]) & ((m["later_ts"] - m["purchase_ts"]).dt.total_seconds() / 86400 <= 180)
first["repeat"] = first["customer_unique_id"].isin(m.loc[m["ok"], "customer_unique_id"]).astype(int)
cutoff = pd.to_datetime(df["purchase_ts"]).max().normalize() - pd.Timedelta(days=180)
first = first[first["purchase_ts"].dt.normalize() <= cutoff]
for g, sub in first.groupby("delay_group"):
    k, n = sub["repeat"].sum(), len(sub); lo, hi = proportion_confint(k, n, method="wilson")
    say(f"   {g:<16} customers={n:>6,}  repeat {k/n*100:4.2f}%  (95% CI {lo*100:.2f}% to {hi*100:.2f}%)")
on = first[first["delay_group"] == "1 On time"]["repeat"]; l4 = first[first["delay_group"] == "3 Late 4+ days"]["repeat"]
z, p = proportions_ztest([l4.sum(), on.sum()], [len(l4), len(on)])
say(f"   On-time vs 4+ days late: two-proportion z-test p = {p:.4f}")
first["late_any"] = (first["delay_group"] != "1 On time").astype(int)
mr = smf.logit("repeat ~ late_any + np.log1p(items_price) + np.log1p(freight) + C(customer_state)", data=first.dropna(subset=["items_price", "freight"])).fit(disp=0)
say(f"   Adjusted for price, freight and state: late vs on-time odds ratio {np.exp(mr.params['late_any']):.2f}"
    f" (95% CI {np.exp(mr.conf_int().loc['late_any'][0]):.2f} to {np.exp(mr.conf_int().loc['late_any'][1]):.2f})")
sp = first[first["customer_state"] == "SP"]
say(f"   Sao Paulo only: on-time {sp[sp.late_any==0]['repeat'].mean()*100:.2f}% (n={int((sp.late_any==0).sum()):,}) vs late {sp[sp.late_any==1]['repeat'].mean()*100:.2f}% (n={int((sp.late_any==1).sum()):,})")

# ---------- 5. Sizing: bring the worst lanes down to the average late rate ----------
lanes = pd.read_csv("outputs/04_worst_lanes.csv")
base = df["late"].mean() * 100
bad = lanes[lanes["late_pct"] > 10].copy()
bad["avoidable_late"] = (bad["late_orders"] - bad["orders"] * base / 100).clip(lower=0)
avoid = bad["avoidable_late"].sum()
say(f"\n5) Sizing (assumption-based, not a forecast)")
say(f"   Overall late rate: {base:.1f}%. Lanes above 10% late in the top-15 list: {len(bad)}")
say(f"   If those lanes matched the overall rate: about {avoid:,.0f} fewer late orders")
say(f"   x {att*100:.1f} points extra chance of a 1-2 star review => about {avoid*att:,.0f} fewer 1-2 star reviews")
say("   (Lane orders are seller-order pairs, so this is approximate.)")

# ---------- Charts ----------
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(figsize=(7, 4))
labels = ["On time", "Late 1-3 days", "Late 4+ days"]
ax.bar(labels, ci["pct"], color=["#94A3B8", "#F59E0B", "#DC2626"],
       yerr=[ci["pct"] - ci["lo"], ci["hi"] - ci["pct"]], capsize=5)
for i, (p_, n_) in enumerate(zip(ci["pct"], ci["n"])):
    ax.text(i, p_ + 4, f"{p_:.1f}%\n(n={n_:,})", ha="center", fontsize=9)
ax.set_ylabel("% of orders with a 1-2 star review"); ax.set_ylim(0, 95)
ax.set_title("Late delivery sharply raises bad reviews (95% CI)", loc="left", fontweight="bold")
plt.tight_layout(); plt.savefig("images/review_by_delay.png", dpi=150); plt.close()

top = lanes.head(10).iloc[::-1]
fig, ax = plt.subplots(figsize=(7.5, 4.5))
colors = ["#DC2626" if v > 10 else "#94A3B8" for v in top["late_pct"]]
ax.barh(top["seller_state"] + " -> " + top["customer_state"], top["late_orders"], color=colors)
for i, (n_, p_) in enumerate(zip(top["late_orders"], top["late_pct"])):
    ax.text(n_ + 15, i, f"{n_:,} late ({p_:.1f}%)", va="center", fontsize=8)
ax.set_xlabel("Late orders (red = more than 10% of the lane's orders)")
ax.set_title("Where late orders concentrate (seller state -> customer state)", loc="left", fontweight="bold")
ax.set_xlim(0, top["late_orders"].max() * 1.3)
plt.tight_layout(); plt.savefig("images/worst_lanes.png", dpi=150); plt.close()
open("outputs/analysis_results.txt", "w").write("\n".join(OUT))
