
-- RUN AFTER THE CSV IMPORT IS DONE
-- This populates all 5 tables + the fact table


USE AirbnbEuropeDB;
GO


--Populate Dimension Tables


-- Populate dim_city
INSERT INTO dim_city (city_name, location_category)
SELECT DISTINCT city, location_category
FROM staging_listings;
GO

-- Populate dim_property_type
INSERT INTO dim_property_type (property_type_name, person_capacity)
SELECT DISTINCT room_type, person_capacity
FROM staging_listings;
GO

-- Populate dim_room_type
INSERT INTO dim_room_type (room_type_name, bedrooms)
SELECT DISTINCT room_type, bedrooms
FROM staging_listings;
GO

-- Populate dim_host
INSERT INTO dim_host (host_type, is_superhost)
SELECT DISTINCT 
    host_type,
    CASE WHEN host_is_superhost = 'TRUE' THEN 1 
         WHEN host_is_superhost = 'False' THEN 0
         WHEN host_is_superhost = '1' THEN 1
         ELSE 0 
    END
FROM staging_listings;
GO

-- Populate dim_date
INSERT INTO dim_date (day_type)
SELECT DISTINCT day_type
FROM staging_listings;
GO


--  Populate the Fact Table

INSERT INTO fact_listings (
    city_key, property_type_key, room_type_key, host_key, date_key,
    price_per_night, price_per_person, guest_satisfaction, cleanliness_rating,
    distance_to_center_km, distance_to_metro_km, attraction_index, restaurant_index,
    latitude, longitude, is_price_outlier
)
SELECT
    dc.city_key,
    dpt.property_type_key,
    drt.room_type_key,
    dh.host_key,
    dd.date_key,

    s.price_per_night,
    s.price_per_person,
    s.guest_satisfaction_overall,
    s.cleanliness_rating,
    s.distance_to_center_km,
    s.distance_to_metro_km,
    s.attraction_index_normalized,
    s.restaurant_index_normalized,
    s.latitude,
    s.longitude,
    CASE WHEN s.is_price_outlier = 'TRUE' THEN 1 
         WHEN s.is_price_outlier = '1' THEN 1
         ELSE 0 
    END

FROM staging_listings s

INNER JOIN dim_city dc
    ON s.city = dc.city_name
    AND s.location_category = dc.location_category

INNER JOIN dim_property_type dpt
    ON s.room_type = dpt.property_type_name
    AND s.person_capacity = dpt.person_capacity

INNER JOIN dim_room_type drt
    ON s.room_type = drt.room_type_name
    AND s.bedrooms = drt.bedrooms

INNER JOIN dim_host dh
    ON s.host_type = dh.host_type
    AND CASE WHEN s.host_is_superhost = 'TRUE' THEN 1 
             WHEN s.host_is_superhost = '1' THEN 1
             ELSE 0 
        END = dh.is_superhost

INNER JOIN dim_date dd
    ON s.day_type = dd.day_type;
GO


--Verification

SELECT 'staging_listings' AS [Table], COUNT(*) AS [Rows] FROM staging_listings
UNION ALL
SELECT 'fact_listings', COUNT(*) FROM fact_listings
UNION ALL
SELECT 'dim_city', COUNT(*) FROM dim_city
UNION ALL
SELECT 'dim_property_type', COUNT(*) FROM dim_property_type
UNION ALL
SELECT 'dim_room_type', COUNT(*) FROM dim_room_type
UNION ALL
SELECT 'dim_host', COUNT(*) FROM dim_host
UNION ALL
SELECT 'dim_date', COUNT(*) FROM dim_date;
GO


