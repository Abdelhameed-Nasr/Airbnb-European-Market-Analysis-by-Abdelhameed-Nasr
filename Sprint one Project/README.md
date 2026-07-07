# Airbnb European Market Analysis

## Project Overview
This is a data analytics and engineering project analyzing 51,707 Airbnb listings across 10 major European cities. The project takes raw, messy CSV data, processes it through a Bronze/Silver/Gold architecture using Python (Pandas), enriches the dataset with live web scraping (Selenium), and visualizes the insights using interactive Power BI Dashboards.

## Tech Stack
* Python (Pandas): Data cleaning, transformation, and feature engineering.
* Python (Selenium): scrape live real-time Airbnb reviews and ratings.
* Power BI: Data modeling (Star Schema), DAX, and building interactive UI dashboards.
* Data Architecture: Medallion Architecture (Bronze -> Silver -> Gold).

##  The Data Pipeline

### 1. Bronze Layer (Raw Data)
* Imported 20 separate CSV files containing raw Airbnb data for 10 European cities (Amsterdam, Athens, Barcelona, Berlin, Budapest, Lisbon, London, Paris, Rome, Vienna).
* Data was split across weekdays and weekends with varying column structures and missing identifiers.

### 2. Silver Layer (Data Cleaning & Transformation)
A Python script was used to clean and unify the dataset:
* Combined all 20 CSV files into a single dataset.
* Feature Engineering: Calculated price_per_night (raw data was a 2-night sum), generated host_type classifications (Individual, Semi-Professional, Professional), and categorized locations by distance to the city center.
* Formatting: Standardized boolean columns, corrected data types, and removed redundant/garbage columns.

### 3. Live Data Enrichment (Web Scraping)
To validate the historical dataset against current market conditions, a custom Python scraper was built:
* Sampled random coordinate points (Latitude/Longitude) per city from the Silver dataset.
* Bypassed bot detection and extracted live, real-time Ratings and Review Counts for specific properties.
* Appended this fresh data as a standalone table for comparison against historical guest satisfaction scores.

### 4. Gold Layer (SQL)
modeled the cleaned data into a Star Schema (Fact and Dimension tables) ready for business intelligence querying.

### 5. Dashboards (Power BI)
Built a comprehensive, 4-page interactive dashboard connecting to the Gold layer:
1. Executive Summary: High-level KPIs, average pricing by city, and weekday vs. weekend comparisons.
2. Location Impact: Geospatial mapping of average prices, distance-to-center scatter plots, and neighborhood attraction indexes.
3. Host & Property Attributes: Market share by host type, superhost pricing analysis, and cleanliness breakdowns.
4. Live Market Sentiment:** Real-time scraped data comparing top 10 reviewed properties and current review volumes across Europe.

