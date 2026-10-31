-- Q1: Do late deliveries get worse reviews?
SELECT delay_group,
       COUNT(*)                                                         AS orders_with_review,
       ROUND(AVG(review_score), 2)                                      AS avg_score,
       ROUND(100.0 * SUM(review_score <= 2) / COUNT(*), 1)              AS pct_1_2_star,
       ROUND(100.0 * SUM(review_score = 5)  / COUNT(*), 1)              AS pct_5_star
FROM order_facts
WHERE review_score IS NOT NULL
GROUP BY delay_group
ORDER BY delay_group;
