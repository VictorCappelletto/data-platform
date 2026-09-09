-- Olist e-commerce schema (subset aligned with Kaggle Brazilian E-Commerce Public Dataset)
IF DB_ID(N'olist') IS NULL
BEGIN
    CREATE DATABASE olist;
END
GO

USE olist;
GO

IF OBJECT_ID(N'dbo.customers', N'U') IS NOT NULL DROP TABLE dbo.customers;
IF OBJECT_ID(N'dbo.orders', N'U') IS NOT NULL DROP TABLE dbo.orders;
IF OBJECT_ID(N'dbo.order_items', N'U') IS NOT NULL DROP TABLE dbo.order_items;
IF OBJECT_ID(N'dbo.order_payments', N'U') IS NOT NULL DROP TABLE dbo.order_payments;
IF OBJECT_ID(N'dbo.order_reviews', N'U') IS NOT NULL DROP TABLE dbo.order_reviews;
IF OBJECT_ID(N'dbo.geolocation', N'U') IS NOT NULL DROP TABLE dbo.geolocation;
IF OBJECT_ID(N'dbo.sellers', N'U') IS NOT NULL DROP TABLE dbo.sellers;
IF OBJECT_ID(N'dbo.product_category_name_translation', N'U') IS NOT NULL DROP TABLE dbo.product_category_name_translation;
GO

CREATE TABLE dbo.customers (
    customer_id              VARCHAR(32)  NOT NULL PRIMARY KEY,
    customer_unique_id       VARCHAR(32)  NOT NULL,
    customer_zip_code_prefix CHAR(5)      NOT NULL,
    customer_city            VARCHAR(100) NOT NULL,
    customer_state           CHAR(2)      NOT NULL
);

CREATE TABLE dbo.orders (
    order_id                      VARCHAR(32) NOT NULL PRIMARY KEY,
    customer_id                   VARCHAR(32) NOT NULL,
    order_status                  VARCHAR(20) NOT NULL,
    order_purchase_timestamp      DATETIME2   NOT NULL,
    order_approved_at             DATETIME2   NULL,
    order_delivered_carrier_date  DATETIME2   NULL,
    order_delivered_customer_date DATETIME2   NULL,
    order_estimated_delivery_date DATETIME2   NULL,
    CONSTRAINT FK_orders_customers FOREIGN KEY (customer_id) REFERENCES dbo.customers (customer_id)
);

CREATE TABLE dbo.sellers (
    seller_id              VARCHAR(32)  NOT NULL PRIMARY KEY,
    seller_zip_code_prefix CHAR(5)      NOT NULL,
    seller_city            VARCHAR(100) NOT NULL,
    seller_state           CHAR(2)      NOT NULL
);

CREATE TABLE dbo.order_items (
    order_id            VARCHAR(32)    NOT NULL,
    order_item_id       INT            NOT NULL,
    product_id          VARCHAR(32)    NOT NULL,
    seller_id           VARCHAR(32)    NOT NULL,
    shipping_limit_date DATETIME2      NOT NULL,
    price               DECIMAL(10, 2) NOT NULL,
    freight_value       DECIMAL(10, 2) NOT NULL,
    PRIMARY KEY (order_id, order_item_id),
    CONSTRAINT FK_order_items_orders FOREIGN KEY (order_id) REFERENCES dbo.orders (order_id),
    CONSTRAINT FK_order_items_sellers FOREIGN KEY (seller_id) REFERENCES dbo.sellers (seller_id)
);

CREATE TABLE dbo.order_payments (
    order_id              VARCHAR(32)    NOT NULL,
    payment_sequential    INT            NOT NULL,
    payment_type          VARCHAR(20)    NOT NULL,
    payment_installments  INT            NOT NULL,
    payment_value         DECIMAL(10, 2) NOT NULL,
    PRIMARY KEY (order_id, payment_sequential),
    CONSTRAINT FK_order_payments_orders FOREIGN KEY (order_id) REFERENCES dbo.orders (order_id)
);

CREATE TABLE dbo.order_reviews (
    review_id               VARCHAR(32) NOT NULL PRIMARY KEY,
    order_id                VARCHAR(32) NOT NULL,
    review_score            TINYINT     NOT NULL,
    review_comment_title    VARCHAR(255) NULL,
    review_comment_message  VARCHAR(MAX) NULL,
    review_creation_date    DATETIME2   NOT NULL,
    review_answer_timestamp DATETIME2   NULL,
    CONSTRAINT FK_order_reviews_orders FOREIGN KEY (order_id) REFERENCES dbo.orders (order_id)
);

CREATE TABLE dbo.geolocation (
    geolocation_zip_code_prefix CHAR(5)        NOT NULL,
    geolocation_lat             DECIMAL(10, 6) NOT NULL,
    geolocation_lng             DECIMAL(10, 6) NOT NULL,
    geolocation_city            VARCHAR(100)   NOT NULL,
    geolocation_state           CHAR(2)        NOT NULL
);

CREATE TABLE dbo.product_category_name_translation (
    product_category_name          VARCHAR(100) NOT NULL PRIMARY KEY,
    product_category_name_english  VARCHAR(100) NOT NULL
);
GO
