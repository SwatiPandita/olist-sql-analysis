-- Q2: Which customer states get the most late orders? RANK() orders them.
WITH by_state AS (
    SELECT customer_state,
           COUNT(*)                                       AS orders,
           SUM(delay_days > 0)                            AS late_orders,
           ROUND(100.0 * SUM(delay_days > 0) / COUNT(*), 1) AS late_pct,
           ROUND(AVG(review_score), 2)                    AS avg_score
    FROM order_facts
    GROUP BY customer_state
    HAVING COUNT(*) >= 500
)
SELECT RANK() OVER (ORDER BY late_pct DESC) AS late_rank, *
FROM by_state
ORDER BY late_rank
LIMIT 10;
