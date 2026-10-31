-- Q7: RFM using customer_unique_id (customer_id changes on every order in Olist).
-- Recency is measured from the LAST date in the data, not today.
-- Frequency is bucketed by hand because almost everyone ordered once (NTILE cannot split ties).
WITH pay AS (SELECT order_id, SUM(payment_value) AS order_value FROM order_payments GROUP BY order_id),
cust AS (
    SELECT f.customer_unique_id,
           MAX(date(f.purchase_ts)) AS last_order,
           COUNT(*)                 AS frequency,
           SUM(p.order_value)       AS monetary
    FROM order_facts f JOIN pay p ON p.order_id = f.order_id
    GROUP BY f.customer_unique_id
),
rfm AS (
    SELECT c.*, CAST(julianday((SELECT MAX(date(purchase_ts)) FROM order_facts))
                   - julianday(c.last_order) AS INTEGER) AS recency_days
    FROM cust c
),
scored AS (
    SELECT *,
           NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
           CASE WHEN frequency = 1 THEN 1 WHEN frequency = 2 THEN 3 ELSE 5 END AS f_score,
           NTILE(5) OVER (ORDER BY monetary)          AS m_score
    FROM rfm
),
segmented AS (
    SELECT *,
      CASE
        WHEN f_score >= 3 AND r_score >= 4 THEN 'Champions (repeat, recent)'
        WHEN f_score >= 3                  THEN 'Repeat customers'
        WHEN r_score >= 4 AND m_score >= 4 THEN 'Recent high-value one-timers'
        WHEN r_score <= 2 AND m_score >= 4 THEN 'At risk: lapsed high-value'
        WHEN r_score >= 4                  THEN 'Recent one-timers'
        WHEN r_score <= 2                  THEN 'Lapsed one-timers'
        ELSE 'Mid one-timers'
      END AS segment
    FROM scored
)
SELECT segment,
       COUNT(*)                                                    AS customers,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM segmented), 1) AS pct_of_customers,
       ROUND(SUM(monetary), 0)                                     AS revenue,
       ROUND(100.0 * SUM(monetary) / (SELECT SUM(monetary) FROM segmented), 1) AS pct_of_revenue
FROM segmented
GROUP BY segment
ORDER BY revenue DESC;
