-- Conceptual gold KPI query
SELECT
  COUNT(*) FILTER (WHERE status = 'completed') * 1.0 / NULLIF(COUNT(*), 0) AS completion_rate,
  SUM(amount) FILTER (WHERE status = 'completed') AS gmv_completed,
  COUNT(DISTINCT customer_id) AS active_customers
FROM silver_orders
WHERE is_current = TRUE;
