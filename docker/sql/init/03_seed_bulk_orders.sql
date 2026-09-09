-- Bulk mock data: ~300 customers, 1000 orders (+ items, payments)
USE olist;
GO

DELETE FROM dbo.order_reviews;
DELETE FROM dbo.order_payments;
DELETE FROM dbo.order_items;
DELETE FROM dbo.orders;
DELETE FROM dbo.customers;
DELETE FROM dbo.sellers;
GO

;WITH n AS (
    SELECT TOP 300 ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS i
    FROM sys.all_objects a
    CROSS JOIN sys.all_objects b
)
INSERT INTO dbo.customers (customer_id, customer_unique_id, customer_zip_code_prefix, customer_city, customer_state)
SELECT
    CONCAT('cust-', RIGHT(CONCAT('000', i), 4)),
    CONCAT('uniq-', RIGHT(CONCAT('000', i), 4)),
    RIGHT(CONCAT('0000', (10000 + i) % 90000), 5),
    CASE i % 5
        WHEN 0 THEN 'Rio de Janeiro'
        WHEN 1 THEN 'Sao Paulo'
        WHEN 2 THEN 'Belo Horizonte'
        WHEN 3 THEN 'Curitiba'
        ELSE 'Porto Alegre'
    END,
    CASE i % 5 WHEN 0 THEN 'RJ' WHEN 1 THEN 'SP' WHEN 2 THEN 'MG' WHEN 3 THEN 'PR' ELSE 'RS' END
FROM n;
GO

;WITH n AS (
    SELECT TOP 20 ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS i
    FROM sys.all_objects a
)
INSERT INTO dbo.sellers (seller_id, seller_zip_code_prefix, seller_city, seller_state)
SELECT
    CONCAT('sell-', RIGHT(CONCAT('00', i), 3)),
    RIGHT(CONCAT('0000', (20000 + i) % 90000), 5),
    CASE i % 4 WHEN 0 THEN 'Rio de Janeiro' WHEN 1 THEN 'Sao Paulo' WHEN 2 THEN 'Salvador' ELSE 'Recife' END,
    CASE i % 4 WHEN 0 THEN 'RJ' WHEN 1 THEN 'SP' WHEN 2 THEN 'BA' ELSE 'PE' END
FROM n;
GO

;WITH n AS (
    SELECT TOP 1000 ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS i
    FROM sys.all_objects a
    CROSS JOIN sys.all_objects b
)
INSERT INTO dbo.orders (
    order_id, customer_id, order_status, order_purchase_timestamp,
    order_approved_at, order_delivered_carrier_date, order_delivered_customer_date, order_estimated_delivery_date
)
SELECT
    CONCAT('ord-', RIGHT(CONCAT('00000', i), 5)),
    CONCAT('cust-', RIGHT(CONCAT('000', ((i - 1) % 300) + 1), 4)),
    CASE i % 10 WHEN 0 THEN 'cancelled' WHEN 1 THEN 'processing' WHEN 2 THEN 'shipped' ELSE 'delivered' END,
    DATEADD(
        MINUTE, i * 17,
        CAST('2017-01-01' AS DATETIME2)
    ),
    DATEADD(MINUTE, i * 17 + 10, CAST('2017-01-01' AS DATETIME2)),
    CASE WHEN i % 10 IN (0, 1) THEN NULL ELSE DATEADD(DAY, (i % 7) + 1, DATEADD(MINUTE, i * 17, CAST('2017-01-01' AS DATETIME2))) END,
    CASE WHEN i % 10 IN (0, 1, 2) THEN NULL ELSE DATEADD(DAY, (i % 14) + 3, DATEADD(MINUTE, i * 17, CAST('2017-01-01' AS DATETIME2))) END,
    DATEADD(DAY, (i % 21) + 7, DATEADD(MINUTE, i * 17, CAST('2017-01-01' AS DATETIME2)))
FROM n;
GO

;WITH n AS (
    SELECT TOP 1000 ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS i
    FROM sys.all_objects a
    CROSS JOIN sys.all_objects b
)
INSERT INTO dbo.order_items (
    order_id, order_item_id, product_id, seller_id, shipping_limit_date, price, freight_value
)
SELECT
    CONCAT('ord-', RIGHT(CONCAT('00000', i), 5)),
    1,
    CONCAT('prod-', RIGHT(CONCAT('00000', (i % 500) + 1), 5)),
    CONCAT('sell-', RIGHT(CONCAT('00', ((i - 1) % 20) + 1), 3)),
    DATEADD(DAY, 3, DATEADD(MINUTE, i * 17, CAST('2017-01-01' AS DATETIME2))),
    ROUND(20.0 + (i % 97) * 3.75, 2),
    ROUND(5.0 + (i % 11) * 1.25, 2)
FROM n;
GO

;WITH n AS (
    SELECT TOP 1000 ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS i
    FROM sys.all_objects a
    CROSS JOIN sys.all_objects b
)
INSERT INTO dbo.order_payments (order_id, payment_sequential, payment_type, payment_installments, payment_value)
SELECT
    CONCAT('ord-', RIGHT(CONCAT('00000', i), 5)),
    1,
    CASE i % 4 WHEN 0 THEN 'boleto' WHEN 1 THEN 'credit_card' WHEN 2 THEN 'debit_card' ELSE 'voucher' END,
    CASE WHEN i % 4 = 1 THEN (i % 6) + 1 ELSE 1 END,
    ROUND(25.0 + (i % 97) * 4.10, 2)
FROM n;
GO

;WITH n AS (
    SELECT TOP 400 ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS i
    FROM sys.all_objects a
    CROSS JOIN sys.all_objects b
)
INSERT INTO dbo.order_reviews (
    review_id, order_id, review_score, review_comment_title, review_comment_message,
    review_creation_date, review_answer_timestamp
)
SELECT
    CONCAT('rev-', RIGHT(CONCAT('00000', i), 5)),
    CONCAT('ord-', RIGHT(CONCAT('00000', i), 5)),
    (i % 5) + 1,
    CASE WHEN i % 3 = 0 THEN NULL ELSE CONCAT('Title ', i) END,
    CASE WHEN i % 4 = 0 THEN NULL ELSE CONCAT('Review message for order ', i) END,
    DATEADD(DAY, (i % 30) + 1, CAST('2017-06-01' AS DATETIME2)),
    CASE WHEN i % 2 = 0 THEN DATEADD(DAY, (i % 30) + 2, CAST('2017-06-01' AS DATETIME2)) ELSE NULL END
FROM n;
GO

SELECT 'customers' AS tbl, COUNT(*) AS cnt FROM dbo.customers
UNION ALL SELECT 'orders', COUNT(*) FROM dbo.orders
UNION ALL SELECT 'order_items', COUNT(*) FROM dbo.order_items
UNION ALL SELECT 'order_payments', COUNT(*) FROM dbo.order_payments
UNION ALL SELECT 'order_reviews', COUNT(*) FROM dbo.order_reviews
UNION ALL SELECT 'sellers', COUNT(*) FROM dbo.sellers;
GO
