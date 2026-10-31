-- Q6: Cohort retention. Cohort = month of a customer's first order.
-- Columns show the % of the cohort that ordered again 1, 2, 3 and 6 months later.
WITH o AS (
    SELECT customer_unique_id, strftime('%Y-%m', purchase_ts) AS ym FROM order_facts
),
first_month AS (SELECT customer_unique_id, MIN(ym) AS cohort FROM o GROUP BY customer_unique_id),
activity AS (
    SELECT DISTINCT f.cohort, o.customer_unique_id,
           (CAST(substr(o.ym,1,4) AS INT) * 12 + CAST(substr(o.ym,6,2) AS INT))
         - (CAST(substr(f.cohort,1,4) AS INT) * 12 + CAST(substr(f.cohort,6,2) AS INT)) AS m
    FROM o JOIN first_month f ON f.customer_unique_id = o.customer_unique_id
)
SELECT cohort,
       COUNT(DISTINCT CASE WHEN m = 0 THEN customer_unique_id END) AS cohort_size,
       ROUND(100.0 * COUNT(DISTINCT CASE WHEN m = 1 THEN customer_unique_id END)
             / COUNT(DISTINCT CASE WHEN m = 0 THEN customer_unique_id END), 2) AS month_1_pct,
       ROUND(100.0 * COUNT(DISTINCT CASE WHEN m = 2 THEN customer_unique_id END)
             / COUNT(DISTINCT CASE WHEN m = 0 THEN customer_unique_id END), 2) AS month_2_pct,
       ROUND(100.0 * COUNT(DISTINCT CASE WHEN m = 3 THEN customer_unique_id END)
             / COUNT(DISTINCT CASE WHEN m = 0 THEN customer_unique_id END), 2) AS month_3_pct,
       ROUND(100.0 * COUNT(DISTINCT CASE WHEN m = 6 THEN customer_unique_id END)
             / COUNT(DISTINCT CASE WHEN m = 0 THEN customer_unique_id END), 2) AS month_6_pct
FROM activity
WHERE cohort BETWEEN '2017-01' AND '2017-12'
GROUP BY cohort
ORDER BY cohort;
