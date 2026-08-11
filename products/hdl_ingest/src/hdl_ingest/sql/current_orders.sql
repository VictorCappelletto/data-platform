-- Example silver filter used by analytics / KPI jobs
-- (executed conceptually; product code filters in Python for local runs)
SELECT
  order_id,
  customer_id,
  amount,
  status,
  country,
  load_at
FROM silver_orders
WHERE is_current = TRUE
  AND country = 'BR';
