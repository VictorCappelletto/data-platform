-- Mock data for local dev (same role as apps/*/seeds/ in the data-platform)
USE olist;
GO

INSERT INTO dbo.customers (customer_id, customer_unique_id, customer_zip_code_prefix, customer_city, customer_state)
VALUES
    ('cust-001', 'uniq-001', '20000', 'Rio de Janeiro', 'RJ'),
    ('cust-002', 'uniq-002', '01000', 'Sao Paulo', 'SP'),
    ('cust-003', 'uniq-003', '30000', 'Belo Horizonte', 'MG');

INSERT INTO dbo.sellers (seller_id, seller_zip_code_prefix, seller_city, seller_state)
VALUES
    ('sell-001', '20000', 'Rio de Janeiro', 'RJ'),
    ('sell-002', '01000', 'Sao Paulo', 'SP');

INSERT INTO dbo.orders (
    order_id, customer_id, order_status, order_purchase_timestamp,
    order_approved_at, order_delivered_carrier_date, order_delivered_customer_date, order_estimated_delivery_date
)
VALUES
    ('ord-001', 'cust-001', 'delivered', '2017-10-02 10:56:33', '2017-10-02 11:07:15', '2017-10-04 19:55:00', '2017-10-10 21:25:13', '2017-10-18 00:00:00'),
    ('ord-002', 'cust-002', 'delivered', '2017-08-15 12:24:27', '2017-08-15 12:35:31', '2017-08-17 07:24:27', '2017-08-23 18:38:08', '2017-08-29 00:00:00'),
    ('ord-003', 'cust-003', 'shipped',   '2018-05-09 03:45:35', '2018-05-09 03:55:08', '2018-05-11 06:45:00', NULL,                          '2018-05-20 00:00:00');

INSERT INTO dbo.order_items (order_id, order_item_id, product_id, seller_id, shipping_limit_date, price, freight_value)
VALUES
    ('ord-001', 1, 'prod-001', 'sell-001', '2017-10-06 20:48:33', 58.90, 13.29),
    ('ord-002', 1, 'prod-002', 'sell-002', '2017-08-19 09:45:35', 239.90, 19.93),
    ('ord-003', 1, 'prod-003', 'sell-001', '2018-05-13 04:10:20', 120.00, 15.00);

INSERT INTO dbo.order_payments (order_id, payment_sequential, payment_type, payment_installments, payment_value)
VALUES
    ('ord-001', 1, 'credit_card', 1, 72.19),
    ('ord-002', 1, 'boleto',      1, 259.83),
    ('ord-003', 1, 'credit_card', 3, 135.00);

INSERT INTO dbo.order_reviews (review_id, order_id, review_score, review_comment_title, review_comment_message, review_creation_date, review_answer_timestamp)
VALUES
    ('rev-001', 'ord-001', 5, 'Great', 'Fast delivery', '2017-10-12 00:00:00', '2017-10-13 10:00:00'),
    ('rev-002', 'ord-002', 4, NULL,    'Good product',  '2017-08-25 00:00:00', NULL);

INSERT INTO dbo.geolocation (geolocation_zip_code_prefix, geolocation_lat, geolocation_lng, geolocation_city, geolocation_state)
VALUES
    ('20000', -22.9068, -43.1729, 'rio de janeiro', 'RJ'),
    ('01000', -23.5505, -46.6333, 'sao paulo', 'SP');

INSERT INTO dbo.product_category_name_translation (product_category_name, product_category_name_english)
VALUES
    (N'cama_mesa_banho', 'bed_bath_table'),
    (N'informatica_acessorios', 'computers_accessories');
GO
