-- Q5: Do customers whose FIRST order arrived late come back less?
-- A repeat order must be placed AFTER the first one was delivered, within 180 days.
-- Only customers whose first order is at least 180 days before the end of the data are counted.
WITH ordered AS (
    SELECT customer_unique_id, order_id, purchase_ts, delivered_ts, delay_group,
           ROW_NUMBER() OVER (PARTITION BY customer_unique_id ORDER BY purchase_ts) AS rn
    FROM order_facts
),
first_order AS (SELECT * FROM ordered WHERE rn = 1),
repeaters AS (
    SELECT DISTINCT f.customer_unique_id
    FROM first_order f
    JOIN ordered o ON o.customer_unique_id = f.customer_unique_id
                  AND o.rn > 1
                  AND o.purchase_ts > f.delivered_ts
                  AND julianday(o.purchase_ts) - julianday(f.purchase_ts) <= 180
)
SELECT f.delay_group,
       COUNT(*)                                              AS customers,
       SUM(r.customer_unique_id IS NOT NULL)                 AS repeat_customers,
       ROUND(100.0 * SUM(r.customer_unique_id IS NOT NULL) / COUNT(*), 2) AS repeat_pct
FROM first_order f
LEFT JOIN repeaters r ON r.customer_unique_id = f.customer_unique_id
WHERE date(f.purchase_ts) <= date((SELECT MAX(purchase_ts) FROM order_facts), '-180 days')
GROUP BY f.delay_group
ORDER BY f.delay_group;
