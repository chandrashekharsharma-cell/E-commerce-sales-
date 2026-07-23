"""
02_etl_pipeline.py
-------------------
Cleans the raw OLTP-style exports and loads a star schema (dim_customers,
dim_products, dim_date, dim_channel, fact_sales) into a SQLite database:
data/retail_ecommerce.db

Also writes cleaned, analysis-ready CSVs into data/clean/ and a short
data-quality report into docs/data_quality_report.md.
"""
import sqlite3
import pandas as pd
import numpy as np
from datetime import date, timedelta

RAW = "data/raw"
CLEAN = "data/clean"
DB_PATH = "data/retail_ecommerce.db"
AS_OF_DATE = date(2026, 6, 30)

quality_log = []


def log(msg):
    print(msg)
    quality_log.append(msg)


# ---------------------------------------------------------------------------
# 1. CUSTOMERS
# ---------------------------------------------------------------------------
cust = pd.read_csv(f"{RAW}/customers_raw.csv", dtype={"customer_id": str})
n0 = len(cust)

cust = cust.drop_duplicates()
log(f"[customers] removed {n0 - len(cust)} exact duplicate rows ({n0:,} -> {len(cust):,})")

cust["first_name"] = cust["first_name"].str.strip().str.title()
cust["last_name"] = cust["last_name"].str.strip().str.title()
cust["full_name"] = cust["first_name"] + " " + cust["last_name"]
cust["gender"] = cust["gender"].str.strip().str.title()

n_missing_email = cust["email"].isna().sum() + (cust["email"] == "").sum()
cust["email"] = cust["email"].replace("", np.nan)
log(f"[customers] {n_missing_email} rows had missing email -> kept row, flagged as NULL")

n_missing_geo = cust["city"].isna().sum()
cust["city"] = cust["city"].fillna("Unknown")
cust["state"] = cust["state"].fillna("Unknown")
cust["region"] = cust["region"].fillna("Unknown")
log(f"[customers] {n_missing_geo} rows had missing city/state/region -> imputed 'Unknown'")

cust["signup_date"] = pd.to_datetime(cust["signup_date"]).dt.date
cust["age"] = AS_OF_DATE.year - cust["birth_year"]
cust["tenure_days"] = cust["signup_date"].apply(lambda d: (AS_OF_DATE - d).days)

dim_customers = cust[[
    "customer_id", "full_name", "email", "gender", "age", "city", "state",
    "region", "signup_date", "tenure_days",
]].drop_duplicates(subset="customer_id").reset_index(drop=True)

# ---------------------------------------------------------------------------
# 2. PRODUCTS
# ---------------------------------------------------------------------------
prod = pd.read_csv(f"{RAW}/products_raw.csv", dtype={"product_id": str})
n0 = len(prod)
prod = prod.drop_duplicates(subset="product_id")
log(f"[products] removed {n0 - len(prod)} duplicate product rows")
prod["product_name"] = prod["product_name"].str.strip()
prod["launch_date"] = pd.to_datetime(prod["launch_date"]).dt.date
dim_products = prod.reset_index(drop=True)

# ---------------------------------------------------------------------------
# 3. ORDERS (header)
# ---------------------------------------------------------------------------
ords = pd.read_csv(f"{RAW}/orders_raw.csv", dtype={"order_id": str, "customer_id": str})
n0 = len(ords)
ords = ords.drop_duplicates(subset="order_id")
log(f"[orders] removed {n0 - len(ords)} duplicate order rows")

n_case_fix = (~ords["channel"].isin(["Website", "Mobile App", "Marketplace", "Social Commerce"])).sum()
ords["channel"] = ords["channel"].str.strip().str.title().replace({"Mobile App": "Mobile App"})
log(f"[orders] standardised casing on {n_case_fix} inconsistent 'channel' values")

ords["order_date"] = pd.to_datetime(ords["order_date"]).dt.date

# ---------------------------------------------------------------------------
# 4. ORDER ITEMS (line grain) -> becomes fact table grain
# ---------------------------------------------------------------------------
items = pd.read_csv(f"{RAW}/order_items_raw.csv", dtype={"order_item_id": str, "order_id": str, "product_id": str})
n0 = len(items)
items = items.drop_duplicates(subset="order_item_id")
log(f"[order_items] removed {n0 - len(items)} duplicate line-item rows (double-scan glitch)")

n_neg_qty = (items["quantity"] < 0).sum()
items["quantity"] = items["quantity"].abs()
log(f"[order_items] corrected {n_neg_qty} negative-quantity data-entry errors")

n_missing_disc = items["discount_pct"].isna().sum()
items["discount_pct"] = items["discount_pct"].fillna(0)
log(f"[order_items] filled {n_missing_disc} missing discount_pct values with 0")

# drop any orphan line items whose order_id/product_id no longer exists after cleaning
before = len(items)
items = items[items["order_id"].isin(ords["order_id"]) & items["product_id"].isin(dim_products["product_id"])]
log(f"[order_items] dropped {before - len(items)} orphan rows with no matching order/product")

# ---------------------------------------------------------------------------
# 5. Build FACT_SALES (join items + orders + product cost)
# ---------------------------------------------------------------------------
cost_map = dict(zip(dim_products["product_id"], dim_products["cost_price"]))
fact = items.merge(ords, on="order_id", how="inner", suffixes=("", "_ord"))

fact["cost_price"] = fact["product_id"].map(cost_map)
fact["sales_amount"] = (fact["quantity"] * fact["unit_price_at_sale"] * (1 - fact["discount_pct"] / 100)).round(2)
fact["cost_amount"] = (fact["quantity"] * fact["cost_price"]).round(2)
fact["profit_amount"] = (fact["sales_amount"] - fact["cost_amount"]).round(2)

fact_sales = fact.rename(columns={"unit_price_at_sale": "unit_price"})[[
    "order_item_id", "order_id", "customer_id", "product_id", "order_date", "channel",
    "payment_method", "order_status", "quantity", "unit_price", "discount_pct",
    "sales_amount", "cost_amount", "profit_amount", "shipping_cost",
]].reset_index(drop=True)
fact_sales.insert(0, "fact_id", range(1, len(fact_sales) + 1))

log(f"[fact_sales] final grain: {len(fact_sales):,} order-line rows")

# ---------------------------------------------------------------------------
# 6. DIM_DATE
# ---------------------------------------------------------------------------
all_days = pd.date_range(fact_sales["order_date"].min(), fact_sales["order_date"].max(), freq="D")
dim_date = pd.DataFrame({"date_id": all_days.date})
dim_date["day"] = all_days.day
dim_date["day_name"] = all_days.day_name()
dim_date["month"] = all_days.month
dim_date["month_name"] = all_days.month_name()
dim_date["quarter"] = all_days.quarter
dim_date["year"] = all_days.year
dim_date["is_weekend"] = all_days.dayofweek >= 5
dim_date["is_festive_season"] = all_days.month.isin([10, 11])

# ---------------------------------------------------------------------------
# 7. DIM_CHANNEL
# ---------------------------------------------------------------------------
dim_channel = pd.DataFrame({
    "channel_id": range(1, 5),
    "channel_name": ["Website", "Mobile App", "Marketplace", "Social Commerce"],
})

# ---------------------------------------------------------------------------
# Write cleaned CSVs + SQLite star schema
# ---------------------------------------------------------------------------
dim_customers.to_csv(f"{CLEAN}/dim_customers.csv", index=False)
dim_products.to_csv(f"{CLEAN}/dim_products.csv", index=False)
dim_date.to_csv(f"{CLEAN}/dim_date.csv", index=False)
dim_channel.to_csv(f"{CLEAN}/dim_channel.csv", index=False)
fact_sales.to_csv(f"{CLEAN}/fact_sales.csv", index=False)

conn = sqlite3.connect(DB_PATH)
dim_customers.to_sql("dim_customers", conn, if_exists="replace", index=False)
dim_products.to_sql("dim_products", conn, if_exists="replace", index=False)
dim_date.to_sql("dim_date", conn, if_exists="replace", index=False)
dim_channel.to_sql("dim_channel", conn, if_exists="replace", index=False)
fact_sales.to_sql("fact_sales", conn, if_exists="replace", index=False)

# helpful indexes for query performance
cur = conn.cursor()
for stmt in [
    "CREATE INDEX IF NOT EXISTS idx_fact_customer ON fact_sales(customer_id)",
    "CREATE INDEX IF NOT EXISTS idx_fact_product ON fact_sales(product_id)",
    "CREATE INDEX IF NOT EXISTS idx_fact_date ON fact_sales(order_date)",
    "CREATE INDEX IF NOT EXISTS idx_cust_id ON dim_customers(customer_id)",
    "CREATE INDEX IF NOT EXISTS idx_prod_id ON dim_products(product_id)",
]:
    cur.execute(stmt)
conn.commit()
conn.close()

log("")
log(f"Star schema loaded into {DB_PATH}:")
log(f"  dim_customers : {len(dim_customers):,} rows")
log(f"  dim_products  : {len(dim_products):,} rows")
log(f"  dim_date      : {len(dim_date):,} rows")
log(f"  dim_channel   : {len(dim_channel):,} rows")
log(f"  fact_sales    : {len(fact_sales):,} rows")

with open("docs/data_quality_report.md", "w") as f:
    f.write("# Data Quality Report — NovaCart ETL Pipeline\n\n")
    f.write(f"Generated by `02_etl_pipeline.py`. As-of date: {AS_OF_DATE.isoformat()}\n\n")
    f.write("## Cleaning steps applied\n\n")
    for line in quality_log:
        f.write(f"- {line}\n")
    f.write("\n## Final star-schema row counts\n\n")
    f.write("| Table | Rows |\n|---|---|\n")
    for name, df in [("dim_customers", dim_customers), ("dim_products", dim_products),
                      ("dim_date", dim_date), ("dim_channel", dim_channel), ("fact_sales", fact_sales)]:
        f.write(f"| {name} | {len(df):,} |\n")

print("\nDone. Data quality report written to docs/data_quality_report.md")
