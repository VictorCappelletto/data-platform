-- Medallion consumption database: bronze.* (landing) + silver.* (processing) + gold.* (curated)
IF DB_ID(N'olist_dw') IS NULL
BEGIN
    CREATE DATABASE olist_dw;
END
GO

USE olist_dw;
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'bronze')
BEGIN
    EXEC('CREATE SCHEMA bronze');
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'silver')
BEGIN
    EXEC('CREATE SCHEMA silver');
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'gold')
BEGIN
    EXEC('CREATE SCHEMA gold');
END
GO

-- Tables refreshed by consumption/sql_server_publish.py
