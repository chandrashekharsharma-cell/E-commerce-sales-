-- =============================================================================
-- NovaCart Retail & E-Commerce Analytics — Analytical Query Library
-- Tested against data/retail_ecommerce.db (SQLite). Portable to any ANSI-SQL
-- engine; only date functions (strftime/julianday) would need swapping for
-- PostgreSQL (DATE_TRUNC) or SQL Server (DATEDIFF/FORMAT).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Monthly revenue, profit & margin trend
-- -----------------------------------------------------------------------------
SELECT
    strftime('%Y-%m', order_date)                              AS year_month,
    COUNT(DISTINCT order_id)                                   AS orders,
    ROUND(SUM(sales_amount), 2)                                AS revenue,
    ROUND(SUM(profit_amount), 2)                               AS profit,
    ROUND(SUM(profit_amount) * 100.0 / SUM(sales_amount), 2)   AS profit_margin_pct
FROM fact_sales
WHERE order_status = 'Delivered'
GROUP BY 1
ORDER BY 1;

-- -----------------------------------------------------------------------------
-- 2. Year-over-year revenue growth
-- -----------------------------------------------------------------------------
WITH yearly AS (
    SELECT strftime('%Y', order_date) AS yr, SUM(sales_amount) AS revenue
    FROM fact_sales
    WHERE order_status = 'Delivered'
    GROUP BY 1
)
SELECT
    yr,
    ROUND(revenue, 2)                                            AS revenue,
    ROUND(LAG(revenue) OVER (ORDER BY yr), 2)                    AS prev_year_revenue,
    ROUND((revenue - LAG(revenue) OVER (ORDER BY yr)) * 100.0
          / LAG(revenue) OVER (ORDER BY yr), 2)                  AS yoy_growth_pct
FROM yearly
ORDER BY yr;

-- -----------------------------------------------------------------------------
-- 3. Top 10 products by revenue
-- -----------------------------------------------------------------------------
SELECT
    p.product_name, p.category, p.brand,
    SUM(f.quantity)          AS units_sold,
    ROUND(SUM(f.sales_amount), 2) AS revenue
FROM fact_sales f
JOIN dim_products p ON f.product_id = p.product_id
WHERE f.order_status = 'Delivered'
GROUP BY p.product_id
ORDER BY revenue DESC
LIMIT 10;

-- -----------------------------------------------------------------------------
-- 4. Category-level profitability
-- -----------------------------------------------------------------------------
SELECT
    p.category,
    ROUND(SUM(f.sales_amount), 2)                              AS revenue,
    ROUND(SUM(f.profit_amount), 2)                              AS profit,
    ROUND(SUM(f.profit_amount) * 100.0 / SUM(f.sales_amount), 2) AS margin_pct
FROM fact_sales f
JOIN dim_products p ON f.product_id = p.product_id
WHERE f.order_status = 'Delivered'
GROUP BY p.category
ORDER BY revenue DESC;

-- -----------------------------------------------------------------------------
-- 5. Sales channel performance (revenue + average order value)
-- -----------------------------------------------------------------------------
SELECT
    channel,
    COUNT(DISTINCT order_id)                                    AS orders,
    ROUND(SUM(sales_amount), 2)                                 AS revenue,
    ROUND(SUM(sales_amount) / COUNT(DISTINCT order_id), 2)      AS avg_order_value
FROM fact_sales
WHERE order_status = 'Delivered'
GROUP BY channel
ORDER BY revenue DESC;

-- -----------------------------------------------------------------------------
-- 6. RFM (Recency / Frequency / Monetary) customer segmentation
-- -----------------------------------------------------------------------------
WITH cust_rfm AS (
    SELECT
        customer_id,
        julianday('2026-06-30') - julianday(MAX(order_date)) AS recency_days,
        COUNT(DISTINCT order_id)                              AS frequency,
        SUM(sales_amount)                                     AS monetary
    FROM fact_sales
    WHERE order_status = 'Delivered'
    GROUP BY customer_id
),
scored AS (
    SELECT *,
        NTILE(4) OVER (ORDER BY recency_days DESC) AS r_score,
        NTILE(4) OVER (ORDER BY frequency ASC)     AS f_score,
        NTILE(4) OVER (ORDER BY monetary ASC)      AS m_score
    FROM cust_rfm
)
SELECT
    customer_id, ROUND(recency_days) AS recency_days, frequency, ROUND(monetary, 2) AS monetary,
    r_score, f_score, m_score,
    CASE
        WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Champions'
        WHEN f_score >= 3 AND m_score >= 3                  THEN 'Loyal Customers'
        WHEN r_score >= 3 AND f_score <= 2                  THEN 'New / Promising'
        WHEN r_score <= 2 AND f_score >= 3                  THEN 'At Risk'
        ELSE 'Needs Attention'
    END AS rfm_segment
FROM scored
ORDER BY monetary DESC;

-- -----------------------------------------------------------------------------
-- 7. Monthly cohort retention (cohort = month of first purchase)
-- -----------------------------------------------------------------------------
WITH first_purchase AS (
    SELECT customer_id, MIN(order_date) AS first_order_date
    FROM fact_sales WHERE order_status = 'Delivered'
    GROUP BY customer_id
),
cohort AS (
    SELECT
        f.customer_id,
        strftime('%Y-%m', fp.first_order_date) AS cohort_month,
        strftime('%Y-%m', f.order_date)        AS order_month
    FROM fact_sales f
    JOIN first_purchase fp ON f.customer_id = fp.customer_id
    WHERE f.order_status = 'Delivered'
),
cohort_index AS (
    SELECT customer_id, cohort_month, order_month,
        (CAST(strftime('%Y', order_month || '-01') AS INT) * 12
         + CAST(strftime('%m', order_month || '-01') AS INT))
        - (CAST(strftime('%Y', cohort_month || '-01') AS INT) * 12
         + CAST(strftime('%m', cohort_month || '-01') AS INT)) AS month_index
    FROM cohort
)
SELECT cohort_month, month_index, COUNT(DISTINCT customer_id) AS active_customers
FROM cohort_index
GROUP BY cohort_month, month_index
ORDER BY cohort_month, month_index;

-- -----------------------------------------------------------------------------
-- 8. Repeat purchase rate
-- -----------------------------------------------------------------------------
WITH order_counts AS (
    SELECT customer_id, COUNT(DISTINCT order_id) AS n_orders
    FROM fact_sales WHERE order_status = 'Delivered'
    GROUP BY customer_id
)
SELECT
    COUNT(*)                                                            AS total_customers,
    SUM(CASE WHEN n_orders > 1 THEN 1 ELSE 0 END)                       AS repeat_customers,
    ROUND(SUM(CASE WHEN n_orders > 1 THEN 1 ELSE 0 END) * 100.0
          / COUNT(*), 2)                                                AS repeat_rate_pct
FROM order_counts;

-- -----------------------------------------------------------------------------
-- 9. Regional sales breakdown
-- -----------------------------------------------------------------------------
SELECT
    c.region,
    COUNT(DISTINCT f.customer_id)     AS customers,
    ROUND(SUM(f.sales_amount), 2)     AS revenue
FROM fact_sales f
JOIN dim_customers c ON f.customer_id = c.customer_id
WHERE f.order_status = 'Delivered'
GROUP BY c.region
ORDER BY revenue DESC;

-- -----------------------------------------------------------------------------
-- 10. Return rate by category
-- -----------------------------------------------------------------------------
SELECT
    p.category,
    COUNT(*)                                                            AS total_line_items,
    SUM(CASE WHEN f.order_status = 'Returned' THEN 1 ELSE 0 END)        AS returned_items,
    ROUND(SUM(CASE WHEN f.order_status = 'Returned' THEN 1 ELSE 0 END)
          * 100.0 / COUNT(*), 2)                                        AS return_rate_pct
FROM fact_sales f
JOIN dim_products p ON f.product_id = p.product_id
GROUP BY p.category
ORDER BY return_rate_pct DESC;

-- -----------------------------------------------------------------------------
-- 11. Average order value by quarter
-- -----------------------------------------------------------------------------
SELECT
    dd.year, dd.quarter,
    ROUND(SUM(f.sales_amount) / COUNT(DISTINCT f.order_id), 2) AS avg_order_value
FROM fact_sales f
JOIN dim_date dd ON f.order_date = dd.date_id
WHERE f.order_status = 'Delivered'
GROUP BY dd.year, dd.quarter
ORDER BY dd.year, dd.quarter;
