"""
03_eda_analysis.py
-------------------
Exploratory data analysis on the cleaned star schema. Produces a set of
publication-quality charts (saved to eda_charts/) and prints a summary
stats block used as the narrative backbone of the project README.
"""
import sqlite3
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.edgecolor": "#333333",
    "axes.grid": True,
    "grid.color": "#e6e6e6",
    "grid.linewidth": 0.6,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})
NAVY = "#1B2A4A"
GOLD = "#E8A33D"
TEAL = "#2AA79A"
CORAL = "#E4634C"
OUT = "eda_charts"

conn = sqlite3.connect("data/retail_ecommerce.db")
fact = pd.read_sql("SELECT * FROM fact_sales WHERE order_status='Delivered'", conn, parse_dates=["order_date"])
products = pd.read_sql("SELECT * FROM dim_products", conn)
customers = pd.read_sql("SELECT * FROM dim_customers", conn, parse_dates=["signup_date"])
fact_all = pd.read_sql("SELECT * FROM fact_sales", conn, parse_dates=["order_date"])
conn.close()

fact = fact.merge(products[["product_id", "category"]], on="product_id")

# ---------------------------------------------------------------------------
# Chart 1: Monthly revenue trend
# ---------------------------------------------------------------------------
monthly = fact.set_index("order_date").resample("MS")["sales_amount"].sum()
fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(monthly.index, monthly.values, color=NAVY, linewidth=2.2)
ax.fill_between(monthly.index, monthly.values, color=NAVY, alpha=0.08)
ax.set_title("Monthly Revenue Trend — NovaCart", fontsize=14, fontweight="bold", color=NAVY)
ax.set_ylabel("Revenue (₹)")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"₹{x/1e6:.1f}M"))
fig.tight_layout()
fig.savefig(f"{OUT}/01_monthly_revenue_trend.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------------------------------
# Chart 2: Revenue & profit by category
# ---------------------------------------------------------------------------
cat = fact.groupby("category").agg(revenue=("sales_amount", "sum"), profit=("profit_amount", "sum")).sort_values("revenue", ascending=True)
fig, ax = plt.subplots(figsize=(10, 6))
ax.barh(cat.index, cat["revenue"], color=GOLD, label="Revenue")
ax.barh(cat.index, cat["profit"], color=NAVY, label="Profit")
ax.set_title("Revenue vs Profit by Category", fontsize=14, fontweight="bold", color=NAVY)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"₹{x/1e6:.0f}M"))
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(f"{OUT}/02_category_revenue_profit.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------------------------------
# Chart 3: Channel mix (donut)
# ---------------------------------------------------------------------------
channel = fact.groupby("channel")["sales_amount"].sum().sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(7, 7))
colors = [NAVY, GOLD, TEAL, CORAL]
wedges, _ = ax.pie(channel.values, colors=colors, startangle=90, wedgeprops=dict(width=0.42, edgecolor="white"))
ax.legend(wedges, [f"{c} ({v/channel.sum()*100:.0f}%)" for c, v in channel.items()],
          loc="center", frameon=False, fontsize=11)
ax.set_title("Revenue Share by Sales Channel", fontsize=14, fontweight="bold", color=NAVY)
fig.tight_layout()
fig.savefig(f"{OUT}/03_channel_mix_donut.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------------------------------
# Chart 4: Top 10 products
# ---------------------------------------------------------------------------
top_products = fact.groupby("product_id").agg(
    name=("product_id", "first"), revenue=("sales_amount", "sum")
)
top_products = fact.merge(products[["product_id", "product_name"]], on="product_id", suffixes=("", "_p")) \
    .groupby("product_name")["sales_amount"].sum().sort_values(ascending=True).tail(10)
fig, ax = plt.subplots(figsize=(10, 6))
ax.barh(top_products.index, top_products.values, color=TEAL)
ax.set_title("Top 10 Products by Revenue", fontsize=14, fontweight="bold", color=NAVY)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"₹{x/1e6:.1f}M"))
fig.tight_layout()
fig.savefig(f"{OUT}/04_top10_products.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------------------------------
# Chart 5: RFM segment distribution
# ---------------------------------------------------------------------------
rfm = fact.groupby("customer_id").agg(
    recency=("order_date", lambda s: (pd.Timestamp("2026-06-30") - s.max()).days),
    frequency=("order_id", "nunique"),
    monetary=("sales_amount", "sum"),
)
rfm["r"] = pd.qcut(rfm["recency"].rank(method="first"), 4, labels=[4, 3, 2, 1]).astype(int)
rfm["f"] = pd.qcut(rfm["frequency"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
rfm["m"] = pd.qcut(rfm["monetary"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)

def segment(row):
    if row.r >= 3 and row.f >= 3 and row.m >= 3:
        return "Champions"
    if row.f >= 3 and row.m >= 3:
        return "Loyal Customers"
    if row.r >= 3 and row.f <= 2:
        return "New / Promising"
    if row.r <= 2 and row.f >= 3:
        return "At Risk"
    return "Needs Attention"

rfm["segment"] = rfm.apply(segment, axis=1)
seg_counts = rfm["segment"].value_counts()
fig, ax = plt.subplots(figsize=(9, 5.5))
bars = ax.bar(seg_counts.index, seg_counts.values, color=[NAVY, GOLD, TEAL, CORAL, "#8892A6"])
ax.set_title("Customer RFM Segments", fontsize=14, fontweight="bold", color=NAVY)
ax.set_ylabel("Number of customers")
for b in bars:
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 8, f"{int(b.get_height())}", ha="center", fontsize=10)
fig.tight_layout()
fig.savefig(f"{OUT}/05_rfm_segments.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------------------------------
# Chart 6: Cohort retention heatmap
# ---------------------------------------------------------------------------
first_purchase = fact.groupby("customer_id")["order_date"].min().rename("cohort_date")
fact_c = fact.join(first_purchase, on="customer_id")
fact_c["cohort_month"] = fact_c["cohort_date"].dt.to_period("M")
fact_c["order_month"] = fact_c["order_date"].dt.to_period("M")
fact_c["month_index"] = (fact_c["order_month"] - fact_c["cohort_month"]).apply(lambda x: x.n)
cohort_pivot = fact_c.groupby(["cohort_month", "month_index"])["customer_id"].nunique().unstack(fill_value=0)
cohort_size = cohort_pivot.iloc[:, 0]
retention = cohort_pivot.divide(cohort_size, axis=0) * 100
retention = retention.iloc[:12, :12]  # first 12 cohorts x 12 months for readability

fig, ax = plt.subplots(figsize=(11, 7))
im = ax.imshow(retention.values, cmap="YlGnBu", aspect="auto", vmin=0, vmax=100)
ax.set_xticks(range(retention.shape[1]))
ax.set_yticks(range(retention.shape[0]))
ax.set_xticklabels(retention.columns)
ax.set_yticklabels([str(p) for p in retention.index])
ax.set_xlabel("Months since first purchase")
ax.set_ylabel("Signup cohort (month)")
ax.set_title("Monthly Cohort Retention (%)", fontsize=14, fontweight="bold", color=NAVY)
for i in range(retention.shape[0]):
    for j in range(retention.shape[1]):
        v = retention.values[i, j]
        if not pd.isna(v):
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7,
                     color="white" if v > 55 else "black")
fig.colorbar(im, ax=ax, label="% retained", shrink=0.8)
fig.tight_layout()
fig.savefig(f"{OUT}/06_cohort_retention_heatmap.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------------------------------
# Summary stats block
# ---------------------------------------------------------------------------
total_revenue = fact["sales_amount"].sum()
total_profit = fact["profit_amount"].sum()
total_orders = fact["order_id"].nunique()
aov = total_revenue / total_orders
n_customers = customers.shape[0]
return_rate = (fact_all["order_status"] == "Returned").mean() * 100
repeat_rate = (rfm["frequency"] > 1).mean() * 100

summary = f"""
NovaCart — EDA Summary
=======================
Total revenue (delivered)   : Rs {total_revenue:,.0f}
Total profit (delivered)    : Rs {total_profit:,.0f}
Overall profit margin       : {total_profit/total_revenue*100:.1f}%
Total delivered orders      : {total_orders:,}
Average order value         : Rs {aov:,.0f}
Total registered customers  : {n_customers:,}
Repeat purchase rate        : {repeat_rate:.1f}%
Return rate (all line items): {return_rate:.1f}%

Charts written to {OUT}/:
  01_monthly_revenue_trend.png
  02_category_revenue_profit.png
  03_channel_mix_donut.png
  04_top10_products.png
  05_rfm_segments.png
  06_cohort_retention_heatmap.png
"""
print(summary)
with open("docs/eda_summary.txt", "w") as f:
    f.write(summary)
