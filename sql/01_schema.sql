-- =============================================================================
-- NovaCart Retail & E-Commerce Analytics — Data Warehouse Schema
-- =============================================================================
-- Star schema: one fact table (fact_sales, grain = one row per order line item)
-- surrounded by four conformed dimensions (customers, products, date, channel).
--
-- Written in SQLite-compatible ANSI SQL (this is how the project's ETL
-- pipeline, python/02_etl_pipeline.py, actually builds data/retail_ecommerce.db).
-- To port to PostgreSQL / SQL Server / MySQL: swap TEXT -> VARCHAR(n),
-- REAL -> DECIMAL(12,2) for money columns, and add an auto-increment/IDENTITY
-- syntax appropriate to that engine for fact_id.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- DIM_CUSTOMERS
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_customers (
    customer_id     TEXT PRIMARY KEY,      -- natural key, e.g. CUST00001
    full_name       TEXT NOT NULL,
    email           TEXT,                  -- NULL where customer omitted it at signup
    gender          TEXT,
    age             INTEGER,
    city            TEXT NOT NULL,         -- 'Unknown' where source data was missing
    state           TEXT NOT NULL,
    region          TEXT NOT NULL,         -- North / South / East / West / Central / Northeast
    signup_date     DATE NOT NULL,
    tenure_days     INTEGER NOT NULL       -- days since signup as of the ETL as-of-date
);

-- -----------------------------------------------------------------------------
-- DIM_PRODUCTS
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_products (
    product_id      TEXT PRIMARY KEY,      -- natural key, e.g. PROD0001
    product_name    TEXT NOT NULL,
    category        TEXT NOT NULL,
    sub_category    TEXT NOT NULL,
    brand           TEXT NOT NULL,
    unit_price      REAL NOT NULL,         -- current catalogue price (INR)
    cost_price      REAL NOT NULL,         -- landed cost (INR)
    launch_date     DATE NOT NULL
);

-- -----------------------------------------------------------------------------
-- DIM_DATE
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_date (
    date_id             DATE PRIMARY KEY,
    day                 INTEGER NOT NULL,
    day_name            TEXT NOT NULL,
    month               INTEGER NOT NULL,
    month_name          TEXT NOT NULL,
    quarter             INTEGER NOT NULL,
    year                INTEGER NOT NULL,
    is_weekend          INTEGER NOT NULL,  -- 0/1 boolean
    is_festive_season   INTEGER NOT NULL   -- 0/1 boolean, Oct-Nov festive/sale season
);

-- -----------------------------------------------------------------------------
-- DIM_CHANNEL
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_channel (
    channel_id      INTEGER PRIMARY KEY,
    channel_name    TEXT NOT NULL UNIQUE  -- Website / Mobile App / Marketplace / Social Commerce
);

-- -----------------------------------------------------------------------------
-- FACT_SALES  (grain: one row per order line item)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_sales (
    fact_id         INTEGER PRIMARY KEY,
    order_item_id   TEXT NOT NULL UNIQUE,
    order_id        TEXT NOT NULL,
    customer_id     TEXT NOT NULL REFERENCES dim_customers(customer_id),
    product_id      TEXT NOT NULL REFERENCES dim_products(product_id),
    order_date      DATE NOT NULL REFERENCES dim_date(date_id),
    channel         TEXT NOT NULL REFERENCES dim_channel(channel_name),
    payment_method  TEXT NOT NULL,
    order_status    TEXT NOT NULL,          -- Delivered / Returned / Cancelled
    quantity        INTEGER NOT NULL,
    unit_price      REAL NOT NULL,
    discount_pct    REAL NOT NULL,
    sales_amount    REAL NOT NULL,          -- net revenue for this line (INR)
    cost_amount     REAL NOT NULL,          -- landed cost for this line (INR)
    profit_amount   REAL NOT NULL,          -- sales_amount - cost_amount
    shipping_cost   REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fact_customer ON fact_sales(customer_id);
CREATE INDEX IF NOT EXISTS idx_fact_product  ON fact_sales(product_id);
CREATE INDEX IF NOT EXISTS idx_fact_date     ON fact_sales(order_date);
