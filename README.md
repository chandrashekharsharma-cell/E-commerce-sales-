# NovaCart — Retail & E-Commerce Analytics

An end-to-end retail analytics portfolio project: a synthetic Indian
e-commerce dataset taken through **SQL + Python ETL → SQLite star schema →
Power BI-ready data model → an animated analytics dashboard**.

> **Data note:** All data is synthetically generated (`python/01_generate_raw_data.py`)
> for demonstration purposes — there is no real company or customer data here.
> Currency is INR (₹). Company name "NovaCart" is fictional.

---

## What's in this project

| Layer | Where | What it proves |
|---|---|---|
| **SQL** | `sql/` | Star-schema DDL + 11 analytical queries (RFM, cohort retention, YoY growth, channel/category performance) |
| **Python** | `python/` | Synthetic data generation → ETL/data cleaning → EDA & charts → Power BI export → dashboard data prep |
| **Power BI** | `powerbi/` | Data model, DAX measure library, and a full build guide (including how to add real animation in Power BI) |
| **Dashboard** | `dashboard/` | A self-contained, animated HTML analytics dashboard (open it directly in a browser) |

## Quick start — view the results without running anything

Open **`dashboard/novacart_dashboard.html`** in any browser. It's fully
self-contained (data is embedded) — no server, no build step needed.

## Reproduce the full pipeline from scratch

```bash
pip install -r requirements.txt

cd python
python 01_generate_raw_data.py       # -> data/raw/*.csv (messy, realistic OLTP export)
python 02_etl_pipeline.py            # -> data/retail_ecommerce.db (clean star schema) + docs/data_quality_report.md
python 03_eda_analysis.py            # -> eda_charts/*.png + docs/eda_summary.txt
python 04_export_for_powerbi.py      # -> data/powerbi_data_model.xlsx + data/csv_for_powerbi/*.csv
python 05_prepare_dashboard_data.py  # -> dashboard/dashboard_data.json
python 06_build_dashboard.py         # -> dashboard/novacart_dashboard.html (final, data-embedded)
```

Each script is numbered and safe to re-run — re-running from `01` regenerates
everything downstream with a fixed random seed (42), so results are
reproducible.

## The data model

One fact table, four dimensions — a standard Kimball-style star schema:

- **`fact_sales`** — grain: one row per order line item (62k+ rows)
- **`dim_customers`** — 4,000 customers, enriched with a precomputed RFM
  (Recency/Frequency/Monetary) snapshot and segment
- **`dim_products`** — 180 SKUs across 10 categories
- **`dim_date`** — full calendar table, June 2023 – June 2026
- **`dim_channel`** — Website / Mobile App / Marketplace / Social Commerce

See `powerbi/star_schema_diagram.png` for the visual, and `sql/01_schema.sql`
for the full DDL.

## Headline numbers (this run's synthetic data)

- ₹58.4 Cr total revenue · ₹22.3 Cr profit (38.2% margin)
- 25,710 delivered orders across 3,900 customers
- ₹22,706 average order value
- 92.3% repeat-purchase rate · 8.0% return rate

(Full breakdown in `docs/eda_summary.txt` and the dashboard itself.)

## The dashboard, and why it's built the way it is

`dashboard/novacart_dashboard.html` is the "professional, animated" piece of
the brief:

- **Live order ticker** — a receipt-styled strip continuously scrolling the
  most recent real orders from the dataset.
- **Count-up KPIs** that animate on load and re-animate when you switch the
  channel filter (Website / Mobile App / Marketplace / Social Commerce).
- **Chart.js visuals** (revenue/profit trend, channel donut, top products,
  category performance, an RFM bubble map, regional revenue) that redraw
  with animated transitions when the channel filter changes.
- **A custom cohort-retention heatmap**, staggered fade-in on load.
- Respects `prefers-reduced-motion`, and degrades gracefully (with a clear
  on-screen message) if the Chart.js CDN can't load rather than breaking the
  whole page.

Power BI, by contrast, is intentionally conservative with motion — see
`powerbi/PowerBI_Build_Guide.md` for a full, honest breakdown of what
animation Power BI genuinely supports natively (Play Axis, bookmark-driven
interactions, animated tooltip pages) versus where the HTML dashboard picks
up the slack. **Building the actual `.pbix` requires Power BI Desktop**
(Windows-only), which isn't available in the environment this project was
built in — so this project ships the data model, DAX measures, and a
step-by-step guide, ready for you to assemble in Power BI Desktop in about
20–30 minutes.

## Folder structure

```
retail-analytics-project/
├── sql/                        DDL + 11 analytical queries
├── python/                     01-06, numbered pipeline scripts
├── data/
│   ├── raw/                    messy synthetic OLTP export
│   ├── clean/                  cleaned star-schema tables (CSV)
│   ├── csv_for_powerbi/        same tables, Power BI-ready
│   ├── powerbi_data_model.xlsx formatted, multi-sheet workbook
│   └── retail_ecommerce.db     SQLite database
├── powerbi/                    build guide, DAX measures, schema diagram
├── dashboard/                  template.html, dashboard_data.json, final HTML
├── eda_charts/                 6 matplotlib charts
├── docs/                       data quality report + EDA summary
└── requirements.txt
```
