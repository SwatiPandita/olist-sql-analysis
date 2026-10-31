-- Q4: Within each seller state, which sellers cause the most late orders?
WITH seller_orders AS (
    SELECT DISTINCT oi.order_id, oi.seller_id FROM order_items oi
),
seller_stats AS (
    SELECT s.seller_id, s.seller_state,
           COUNT(*)                                          AS orders,
           SUM(f.delay_days > 0)                             AS late_orders,
           ROUND(100.0 * SUM(f.delay_days > 0) / COUNT(*), 1) AS late_pct,
           ROUND(AVG(f.review_score), 2)                     AS avg_score
    FROM seller_orders so
    JOIN order_facts f ON f.order_id  = so.order_id
    JOIN sellers s     ON s.seller_id = so.seller_id
    GROUP BY s.seller_id, s.seller_state
    HAVING COUNT(*) >= 50
),
ranked AS (
    SELECT *, RANK() OVER (PARTITION BY seller_state ORDER BY late_orders DESC) AS rank_in_state
    FROM seller_stats
)
SELECT seller_state, rank_in_state, substr(seller_id, 1, 8) AS seller_short,
       orders, late_orders, late_pct, avg_score
FROM ranked
WHERE rank_in_state <= 2
ORDER BY late_orders DESC
LIMIT 15;
