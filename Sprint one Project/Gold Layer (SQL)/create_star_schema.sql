

-- Create the database if it doesn't exist yet
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'AirbnbEuropeDB')
    CREATE DATABASE AirbnbEuropeDB;
GO

USE AirbnbEuropeDB;
GO

-- Drop ALL old tables because it has foreign keys, then dimensions, then staging
IF OBJECT_ID('fact_listings', 'U') IS NOT NULL DROP TABLE fact_listings;
IF OBJECT_ID('dim_city', 'U') IS NOT NULL DROP TABLE dim_city;
IF OBJECT_ID('dim_property_type', 'U') IS NOT NULL DROP TABLE dim_property_type;
IF OBJECT_ID('dim_room_type', 'U') IS NOT NULL DROP TABLE dim_room_type;
IF OBJECT_ID('dim_host', 'U') IS NOT NULL DROP TABLE dim_host;
IF OBJECT_ID('dim_date', 'U') IS NOT NULL DROP TABLE dim_date;
IF OBJECT_ID('staging_listings', 'U') IS NOT NULL DROP TABLE staging_listings;
GO

CREATE TABLE staging_listings (
    price_per_night               FLOAT,
    room_type                     NVARCHAR(50),
    person_capacity               TINYINT,
    bedrooms                      TINYINT,
    city                          NVARCHAR(50),
    day_type                      NVARCHAR(50),
    price_per_person              FLOAT,
    host_is_superhost             NVARCHAR(50),
    host_type                     NVARCHAR(50),
    guest_satisfaction_overall    TINYINT,
    cleanliness_rating            TINYINT,
    distance_to_center_km         FLOAT,
    distance_to_metro_km          FLOAT,
    attraction_index_normalized   FLOAT,
    restaurant_index_normalized   FLOAT,
    longitude                     FLOAT,
    latitude                      FLOAT,
    location_category             NVARCHAR(50),
    is_price_outlier              NVARCHAR(50)
);
GO

-- Dimension Tables


-- City Dimension
CREATE TABLE dim_city (
    city_key           INT IDENTITY(1,1) PRIMARY KEY,
    city_name          NVARCHAR(50) NOT NULL,
    location_category  NVARCHAR(50) -- city_center, near_center, etc.
);
GO

-- Property Type Dimension
CREATE TABLE dim_property_type (
    property_type_key  INT IDENTITY(1,1) PRIMARY KEY,
    property_type_name NVARCHAR(50) NOT NULL, -- e.g., "Private room"
    person_capacity    INT NOT NULL           -- e.g., 2
);
GO

-- Room Type Dimension 
CREATE TABLE dim_room_type (
    room_type_key      INT IDENTITY(1,1) PRIMARY KEY,
    room_type_name     NVARCHAR(50) NOT NULL, -- e.g., "Entire home/apt"
    bedrooms           INT NOT NULL           -- e.g., 3
);
GO

--Host Dimension
CREATE TABLE dim_host (
    host_key           INT IDENTITY(1,1) PRIMARY KEY,
    host_type          NVARCHAR(50) NOT NULL, -- Individual, Professional, semi
    is_superhost       BIT NOT NULL           -- true/false
);
GO

-- 5. Date Dimension
CREATE TABLE dim_date (
    date_key           INT IDENTITY(1,1) PRIMARY KEY,
    day_type           NVARCHAR(50) NOT NULL  -- weekday, weekend
);
GO


-- Create the Fact Table

CREATE TABLE fact_listings (
    listing_id             INT IDENTITY(1,1) PRIMARY KEY,
    
    -- Foreign Keys to Dimensions
    city_key               INT NOT NULL,
    property_type_key      INT NOT NULL,
    room_type_key          INT NOT NULL,
    host_key               INT NOT NULL,
    date_key               INT NOT NULL,
    
    -- Measures
    price_per_night        DECIMAL(10,2),
    price_per_person       DECIMAL(10,2),
    guest_satisfaction     DECIMAL(5,2),
    cleanliness_rating     DECIMAL(5,2),
    distance_to_center_km  DECIMAL(10,4),
    distance_to_metro_km   DECIMAL(10,4),
    attraction_index       DECIMAL(10,4),
    restaurant_index       DECIMAL(10,4),
    latitude               DECIMAL(10,5),
    longitude              DECIMAL(10,5),
    is_price_outlier       BIT,

    -- Relationships (Foreign Keys)
    CONSTRAINT FK_fact_city          FOREIGN KEY (city_key)          REFERENCES dim_city(city_key),
    CONSTRAINT FK_fact_property_type FOREIGN KEY (property_type_key) REFERENCES dim_property_type(property_type_key),
    CONSTRAINT FK_fact_room_type     FOREIGN KEY (room_type_key)     REFERENCES dim_room_type(room_type_key),
    CONSTRAINT FK_fact_host          FOREIGN KEY (host_key)          REFERENCES dim_host(host_key),
    CONSTRAINT FK_fact_date          FOREIGN KEY (date_key)          REFERENCES dim_date(date_key)
);
GO
