"""
05_prepare_dashboard_data.py
-----------------------------
Computes every aggregate the animated HTML dashboard needs (overall +
per-channel KPIs, trends, category/product breakdowns, RFM segments,
cohort retention, and a sample order feed) and writes a single JSON file:
dashboard/dashboard_data.json — which 06_build_dashboard.py then embeds
directly into the HTML so the dashboard is a self-contained file.
"""
import sqlite3
import json
import pandas as pd
import numpy as np

conn = sqlite3.connect("data/retail_ecommerce.db")
fact = pd.read_sql("SELECT * FROM fact_sales", conn, parse_dates=["order_date"])
products = pd.read_sql("SELECT * FROM dim_products", conn)
customers = pd.read_sql("SELECT * FROM dim_customers", conn, parse_dates=["signup_date"])
conn.close()

fact = fact.merge(products[["product_id", "product_name", "category"]], on="product_id")
fact = fact.merge(customers[["customer_id", "region"]], on="customer_id")

AS_OF = pd.Timestamp("2026-06-30")
CHANNELS = ["All", "Website", "Mobile App", "Marketplace", "Social Commerce"]


def slice_channel(df, ch):
    return df if ch == "All" else df[df["channel"] == ch]


def kpis_for(df):
    d = df[df["order_status"] == "Delivered"]
    revenue = float(d["sales_amount"].sum())
    profit = float(d["profit_amount"].sum())
    orders = int(d["order_id"].nunique())
    cust_n = int(d["customer_id"].nunique())
    aov = revenue / orders if orders else 0
    freq = d.groupby("customer_id")["order_id"].nunique()
    repeat_rate = float((freq > 1).mean() * 100) if len(freq) else 0
    all_lines = df
    return_rate = float((all_lines["order_status"] == "Returned").mean() * 100) if len(all_lines) else 0
    return {
        "revenue": round(revenue, 2), "profit": round(profit, 2),
        "margin_pct": round(profit / revenue * 100, 2) if revenue else 0,
        "orders": orders, "customers": cust_n, "aov": round(aov, 2),
        "repeat_rate_pct": round(repeat_rate, 2), "return_rate_pct": round(return_rate, 2),
    }


def monthly_trend_for(df):
    d = df[df["order_status"] == "Delivered"].copy()
    d["ym"] = d["order_date"].dt.to_period("M").astype(str)
    g = d.groupby("ym").agg(revenue=("sales_amount", "sum"), profit=("profit_amount", "sum"),
                             orders=("order_id", "nunique")).reset_index()
    return [{"month": r.ym, "revenue": round(r.revenue, 2), "profit": round(r.profit, 2),
             "orders": int(r.orders)} for r in g.itertuples()]


def category_perf_for(df):
    d = df[df["order_status"] == "Delivered"]
    g = d.groupby("category").agg(revenue=("sales_amount", "sum"), profit=("profit_amount", "sum")).reset_index()
    g["margin_pct"] = (g["profit"] / g["revenue"] * 100).round(2)
    g = g.sort_values("revenue", ascending=False)
    return [{"category": r.category, "revenue": round(r.revenue, 2),
             "profit": round(r.profit, 2), "margin_pct": r.margin_pct} for r in g.itertuples()]


def top_products_for(df, n=8):
    d = df[df["order_status"] == "Delivered"]
    g = d.groupby(["product_name", "category"]).agg(
        revenue=("sales_amount", "sum"), units=("quantity", "sum")).reset_index()
    g = g.sort_values("revenue", ascending=False).head(n)
    return [{"name": r.product_name, "category": r.category, "revenue": round(r.revenue, 2),
             "units": int(r.units)} for r in g.itertuples()]


def region_perf_for(df):
    d = df[df["order_status"] == "Delivered"]
    g = d.groupby("region").agg(revenue=("sales_amount", "sum")).reset_index().sort_values("revenue", ascending=False)
    return [{"region": r.region, "revenue": round(r.revenue, 2)} for r in g.itertuples()]


data = {"channels": {}}
for ch in CHANNELS:
    sub = slice_channel(fact, ch)
    data["channels"][ch] = {
        "kpis": kpis_for(sub),
        "monthly_trend": monthly_trend_for(sub),
        "category_performance": category_perf_for(sub),
        "top_products": top_products_for(sub),
        "region_performance": region_perf_for(sub),
    }

# ---- channel mix (always overall, for the donut) ----
delivered = fact[fact["order_status"] == "Delivered"]
ch_mix = delivered.groupby("channel")["sales_amount"].sum().sort_values(ascending=False)
total = ch_mix.sum()
data["channel_mix"] = [{"channel": k, "revenue": round(float(v), 2),
                        "share_pct": round(float(v) / total * 100, 2)} for k, v in ch_mix.items()]

# ---- RFM segments + scatter sample ----
rfm = delivered.groupby("customer_id").agg(
    recency=("order_date", lambda s: (AS_OF - s.max()).days),
    frequency=("order_id", "nunique"),
    monetary=("sales_amount", "sum"),
).reset_index()
rfm["r"] = pd.qcut(rfm["recency"].rank(method="first"), 4, labels=[4, 3, 2, 1]).astype(int)
rfm["f"] = pd.qcut(rfm["frequency"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
rfm["m"] = pd.qcut(rfm["monetary"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)


def seg(row):
    if row.r >= 3 and row.f >= 3 and row.m >= 3:
        return "Champions"
    if row.f >= 3 and row.m >= 3:
        return "Loyal Customers"
    if row.r >= 3 and row.f <= 2:
        return "New / Promising"
    if row.r <= 2 and row.f >= 3:
        return "At Risk"
    return "Needs Attention"


rfm["segment"] = rfm.apply(seg, axis=1)
seg_counts = rfm.groupby("segment").agg(count=("customer_id", "count"),
                                         avg_monetary=("monetary", "mean")).reset_index()
data["rfm_segments"] = [{"segment": r.segment, "count": int(r.count),
                          "avg_monetary": round(r.avg_monetary, 2)} for r in seg_counts.itertuples()]

SEG_ORDER = ["Champions", "Loyal Customers", "New / Promising", "At Risk", "Needs Attention"]
sample_parts = []
for seg_name, g in rfm.groupby("segment"):
    sample_parts.append(g.sample(min(len(g), 40), random_state=1))
sample = pd.concat(sample_parts, ignore_index=True)
data["rfm_scatter"] = [{"recency": int(row["recency"]), "frequency": int(row["frequency"]),
                         "monetary": round(float(row["monetary"]), 2), "segment": row["segment"]}
                        for _, row in sample.iterrows()]

# ---- cohort retention (first 10 cohorts x 10 months, for a compact grid) ----
first_purchase = delivered.groupby("customer_id")["order_date"].min().rename("cohort_date")
fc = delivered.join(first_purchase, on="customer_id")
fc["cohort_month"] = fc["cohort_date"].dt.to_period("M")
fc["order_month"] = fc["order_date"].dt.to_period("M")
fc["month_index"] = (fc["order_month"] - fc["cohort_month"]).apply(lambda x: x.n)
pivot = fc.groupby(["cohort_month", "month_index"])["customer_id"].nunique().unstack(fill_value=0)
cohort_size = pivot.iloc[:, 0]
retention = (pivot.divide(cohort_size, axis=0) * 100).round(1)
retention = retention.iloc[:10, :10]
data["cohort_retention"] = {
    "cohorts": [str(p) for p in retention.index],
    "months": [int(c) for c in retention.columns],
    "matrix": [[None if pd.isna(v) else float(v) for v in row] for row in retention.values],
    "cohort_sizes": [int(cohort_size.loc[p]) for p in retention.index],
}

# ---- recent order feed for the ticker ----
recent = delivered.merge(customers[["customer_id", "city"]], on="customer_id").sort_values(
    "order_date", ascending=False).head(60)
data["recent_orders"] = [{"order_id": r.order_id, "city": r.city, "category": r.category,
                          "amount": round(r.sales_amount, 2), "channel": r.channel}
                         for r in recent.itertuples()]

data["meta"] = {
    "company": "NovaCart",
    "currency": "\u20b9",
    "date_range": f"{fact['order_date'].min().date()} to {fact['order_date'].max().date()}",
    "generated_for": "Retail & E-Commerce Analytics Portfolio Project",
}

with open("dashboard/dashboard_data.json", "w") as f:
    json.dump(data, f)

print("Wrote dashboard/dashboard_data.json")
print("Top-level keys:", list(data.keys()))
print("Overall KPIs:", data["channels"]["All"]["kpis"])
