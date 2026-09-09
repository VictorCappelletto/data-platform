-- Consumption database schemas (bronze / silver / gold) for ADF publish + Power BI
IF DB_ID(N'olist_dw') IS NULL
BEGIN
    CREATE DATABASE olist_dw;
END
GO

USE olist_dw;
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'bronze')
    EXEC('CREATE SCHEMA bronze');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'silver')
    EXEC('CREATE SCHEMA silver');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'gold')
    EXEC('CREATE SCHEMA gold');
GO
