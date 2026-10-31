-- Sanity check: order status mix.
SELECT o.order_status,
       COUNT(*)                                          AS orders,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM orders), 2) AS pct_of_orders
FROM orders o
GROUP BY o.order_status
ORDER BY orders DESC;
