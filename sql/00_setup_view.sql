-- One row per DELIVERED order. Every later query reads from this table.
-- Delay = delivered date minus estimated date (dates only, so time-of-day does not matter).
-- Positive = late. Reviews: some orders have several, so we keep the latest one.
DROP VIEW IF EXISTS order_facts;
DROP TABLE IF EXISTS order_facts;
CREATE TABLE order_facts AS
WITH latest_review AS (
    SELECT order_id, review_score,
           ROW_NUMBER() OVER (PARTITION BY order_id
                              ORDER BY review_answer_timestamp DESC) AS rn
    FROM order_reviews
),
item_summary AS (
    SELECT oi.order_id,
           COUNT(*)                    AS n_items,
           SUM(oi.price)               AS items_price,
           SUM(oi.freight_value)       AS freight,
           AVG(p.product_weight_g)     AS avg_weight_g
    FROM order_items oi
    LEFT JOIN products p ON p.product_id = oi.product_id
    GROUP BY oi.order_id
)
SELECT o.order_id,
       c.customer_unique_id,
       c.customer_state,
       o.order_purchase_timestamp          AS purchase_ts,
       o.order_delivered_customer_date     AS delivered_ts,
       CAST(julianday(date(o.order_delivered_customer_date))
          - julianday(date(o.order_estimated_delivery_date)) AS INTEGER) AS delay_days,
       CASE
         WHEN julianday(date(o.order_delivered_customer_date))
            - julianday(date(o.order_estimated_delivery_date)) <= 0 THEN '1 On time'
         WHEN julianday(date(o.order_delivered_customer_date))
            - julianday(date(o.order_estimated_delivery_date)) <= 3 THEN '2 Late 1-3 days'
         ELSE '3 Late 4+ days'
       END                                  AS delay_group,
       r.review_score,
       i.n_items, i.items_price, i.freight, i.avg_weight_g
FROM orders o
JOIN customers c     ON c.customer_id = o.customer_id
JOIN item_summary i  ON i.order_id    = o.order_id
LEFT JOIN latest_review r ON r.order_id = o.order_id AND r.rn = 1
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL;

CREATE INDEX idx_of_order ON order_facts(order_id);
CREATE INDEX idx_of_cust ON order_facts(customer_unique_id);
