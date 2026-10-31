-- Q3: "Where should Olist fix first?" A lane = seller state -> customer state.
-- Ranked by NUMBER of late orders (impact), not just rate. Order-seller pairs are de-duplicated.
WITH order_seller AS (
    SELECT DISTINCT order_id, seller_id FROM order_items
),
lane AS (
    SELECT s.seller_state, f.customer_state, f.order_id, f.delay_days
    FROM order_seller os
    JOIN order_facts f ON f.order_id  = os.order_id
    JOIN sellers s     ON s.seller_id = os.seller_id
),
total AS (SELECT SUM(delay_days > 0) AS all_late FROM lane)
SELECT seller_state, customer_state,
       COUNT(*)                                          AS orders,
       SUM(delay_days > 0)                               AS late_orders,
       ROUND(100.0 * SUM(delay_days > 0) / COUNT(*), 1)  AS late_pct,
       ROUND(100.0 * SUM(delay_days > 0) / (SELECT all_late FROM total), 1) AS pct_of_all_late
FROM lane
GROUP BY seller_state, customer_state
HAVING COUNT(*) >= 300
ORDER BY late_orders DESC
LIMIT 15;
