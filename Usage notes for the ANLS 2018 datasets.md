# Usage notes and Example code for loading and using datasets from the [Australian National Liveability Study 2018](https://doi.org/10.25439/rmt.15001230)
We recommend using an SQL database with appropriate use of [indexes](http://postgis.net/workshops/postgis-intro/indexing.html) to support managing and querying of data.  Below we provide example code for the popular free and open-source database management system [PostgreSQL](https://www.postgresql.org/) (e.g. version 14 or higher) along with the [PostGIS](https://postgis.net/) extension (e.g. version 3.2.3 or higher) for spatial datatypes and analysis.  Once the software is installed, the following code can be entered at the command line interactively, or run as an .sql file using the psql terminal interface.  The below code examples also assume that the [Australian National Liveability Study 2018 data files](https://doi.org/10.25439/rmt.15001230) have been retrieved and extracted.  

We have provided our data and data dictionaries in a plain text CSV format for archival purposes, to maximise accessibility and usability of the data.  In addition, an [Excel file containing the data dictionaries as formatted worksheets](https://rmit.figshare.com/ndownloader/files/36948940) is also included.  The data dictionaries describe the variables (columns) included in the CSV data, in addition to the data types for interpreting these (e.g. integer, numerical, string or text, etc). 

This document provides examples for loading all provided datasets and illustrate how to get started using the data in a PostgreSQL database.  Users may draw on this code freely, updating any file paths with corresponding locations of their own downloaded data.  

## Contents
- [Create and connect to a new database for the Australian National Liveability Study](#create-and-connect-to-a-new-database-for-the-australian-national-liveability-study)
- [Loading the indicator datasets](#loading-the-indicators-datasets)
  - [General process and tips](#general-process-and-tips)
  - [Address points](#loading-the-address-indicator-data)
  - [Mesh Blocks](#loading-the-mesh-block-indicator-data)
  - [Stastistical Area 1](#loading-the-statistical-area-1-(sa1)-indicator-data)
  - [Stastistical Area 2](#loading-the-statistical-area-2-(sa2)-indicator-data)
  - [Stastistical Area 3](#loading-the-statistical-area-3-(sa3)-indicator-data)
  - [Stastistical Area 4](#loading-the-statistical-area-4-(sa4)-indicator-data)
  - [Suburb](#loading-the-suburb-indicator-data)
  - [Local Government Area](#loading-the-local-government-area-indicator-data)
  - [City (overall summary)](#loading-the-city-indicator-data-(overall-city-summaries))
- [Additional custom SQL functions](#Additional-custom-SQL-functions)

## Create and connect to a new database for the Australian National Liveability Study
First, a new database called anls_2018 is created and then connected to he PostGIS extension may optionally be created; this would allow the residential address indicator coordinates to be interpreted as a Point geometry datatype, and link up the area aggregate indicators with their corresponding boundary geometries from the Australian Statistical Geography Standard retrieved from the Australian Bureau of Statistics for mapping.  

```sql
CREATE DATABASE anls_2018;
\c anls_2018
CREATE EXTENSION IF NOT EXISTS postgis; 
SELECT postgis_full_version(); 
```

## Loading the indicators datasets

### General process and tips
To load data, empty table(s) are created for the datasets to be loaded into first; the column names and data types of the data to be loaded from the CSV source file are defined (e.g., drawing on the variable names and data types in the supplied data dictionary files).  Then, the data itself may be copied from the CSV file into the newly created table.

In the create table statement, you declare all the columns and their data types.  This can be quite verbose to list all of these (125 variables for the address indicators table, or more than 200 in the area aggregation tables which also contain distance to closest measures), so the code has been set to be collapsable in such cases below.

Note the file for residential address indicators is large (> 1Gb), and some versions of PostgreSQL (eg 13) have issues copying data from large files (see https://stackoverflow.com/questions/53523051/error-could-not-stat-file-xx-csv-unknown-error).  There are work arounds, but most elegant is probably to install PostgreSQL 14 (the current version at time of writing in August 2022) or newer.

The address indicator data contains latitude and longitude coordinates using a spatial reference of GDA2020 GA LCC, EPSG 7845.  Example code is provided for calculating a point geometry column and creating a spatial index for this.

The area indicator datasets may be linked up using the provided linkage codes with boundaries and other data from Australian Bureau of Statistics (ABS) 2016 release of the Australian Statistical Geography Standard (ASGS) using the [Main Structure and Greater Capital City Statistical Areas ASGS Ed 2016 Digital Boundaries Geopackage](https://www.abs.gov.au/AUSSTATS/subscriber.nsf/log?openagent&1270055001_ASGS_2016_vol_1_geopackage.zip&1270.0.55.001&Data%20Cubes&C406A18CE1A6A50ACA257FED00145B1D&0&July%202016&12.07.2016&Latest) (for Mesh Block, SA1, SA2, SA3, SA4 areas) and [Non ABS Structure ASGS Ed 2016 Digital Boundaries in Geopackage ](https://www.abs.gov.au/AUSSTATS/subscriber.nsf/log?openagent&1270055003_asgs_2016_vol_3_aust_gpkg.zip&1270.0.55.003&Data%20Cubes&5B5A14600B65C072CA25833D000EB95E&0&July%202016&07.11.2018&Previous) (Suburbs and Local Government Areas).

You can add in comments to describe the data, drawing on and incorporating the data dictionary descriptions.  You may want to use dollar quoting (ie. using dollar signs "$$" instead of quote marks "'") to avoid use of apostrophes in descriptions causing errors (it may look like the comment has ended, and then the remaining characters can't be interpreted raising an error).  

To view the list of tables in the database with comments when using psql, type `\dt+`; this can effectively serve as a data dictionary for the loaded datasets.  To view a data dictionary displaying the data type and description for variables commented on a specific table, a custom function can help.  This can be created by copying and pasting the following code in psql:

```sql
CREATE OR REPLACE FUNCTION dictionary(commented_table text) 
RETURNS TABLE (column_name text, data_type text, col_description text) AS 
$$
SELECT a.attname column,
  pg_catalog.format_type(a.atttypid, a.atttypmod) type,
  pg_catalog.col_description(a.attrelid, a.attnum) description
FROM pg_catalog.pg_attribute a
WHERE a.attrelid =commented_table::regclass::oid AND a.attnum > 0 AND NOT a.attisdropped
ORDER BY a.attnum;
$$ language sql;
```

So, to display a data dictionary for the address indicators table, you can use the query, `SELECT * FROM dictionary('li_2018_address_indicators');`.  Running this after using the code below to load the address indicators would display the following:

<details>
  <summary>
    Click to view example data dictionary for address indicators returned from using the custom dictionary(table) function described above
  </summary>

```
anls_2018=# SELECT * FROM dictionary('li_2018_address_indicators');
         column_name          |       data_type       |             col_description  
------------------------------+-----------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
 gnaf_pid                     | character varying(15) | Unique identifier using PSMA Open G-NAF 2018 data
 count_objectid               | integer               | Count of co-located G-NAF points (only first unique location retained)
 point_x                      | double precision      | Easting (metres; EPSG 7845)
 point_y                      | double precision      | Northing (metres; EPSG 7845)
 study_region                 | text                  | City name
 mb_code_2016                 | text                  | Mesh Block (ASGS 2016) identifier
 mb_category_name_2016        | text                  | Mesh Block category
 sa1_maincode_2016            | text                  | Statistical Area 1 (SA1) maincode identifier
 sa2_name_2016                | text                  | SA2 name
 sa3_name_2016                | text                  | SA3 name
 sa4_name_2016                | text                  | SA4 name
 gccsa_name_2016              | text                  | Greater Capital City Statistical Area name
 state_name_2016              | text                  | State name
 ssc_name_2016                | text                  | Suburb name
 lga_name_2016                | text                  | LGA name
 ucl_name_2016                | text                  | Urban centre and locality name 
 sos_name_2016                | text                  | Section of state name
 uli_city                     | double precision      | Urban Liveability Index, relative to locations within this city
 uli_national                 | double precision      | Urban Liveability Index, relative to locations across Australia's 21 largest cities
 li_community_culture_leisure | double precision      | Score for access to community, culture and leisure destinations (community centre and library within 1000m, and museum/art gallery and cinema/theater within 3200m) (/1)
 li_early_years               | double precision      | Score for access to child care (any meeting ACECQA recommendations) within 800 metres and childcare (outside school hours meeting recommendations) within 1600 metres (/1)
 li_education                 | double precision      | Score for access to primary and secondary public schools within 1600 metres (/1)
 li_health_services           | double precision      | Score for access to health services (GP, pharmacy, maternal, child and family health care, aged care facility and other community health care) within 1000 metres (/1)
 li_sport_rec                 | double precision      | Score for access to an area of open space with sport/recreation facilities within 1000 metres, and a public swimming pool within 1200 metres (/1)
 li_food                      | double precision      | Score for access to a supermarket and fresh fruit and vegetables within 1000 metres, and meat/seafood within 3200 metres (/1)
 li_convenience               | double precision      | Score for access to convenience destinations (convenience store and petrol station within 1000 metres, and a newsagent within 3200 metres) (/1)
 li_pt_regular_400m           | double precision      | Within 400 m of public transport with an average weekday service frequency of 30 minutes or less between 7am and 7pm within 400 metres
 li_public_os_large_400m      | double precision      | Within 400 m of public open space larger than 1.5 Ha
 li_street_connectivity_1600m | double precision      | Street connectivity
 li_dwelling_density_1600m    | double precision      | Dwelling density
 li_sa1_30_40_housing_stress  | double precision      | Percentage of SA1 households with income in the bottom 40% of the income distribution spending more than 30% of household income on housing costs
 li_sa1_sa3_local_employment  | double precision      | Percentage of employed persons working in the community (SA3) in which they live
 walkability_city             | double precision      | Walkability index, combining street connectivity, dwelling density and daily living destinations, relative to locations within this city
 walkability_national         | double precision      | Walkability index, combining street connectivity, dwelling density and daily living destinations, relative to locations across Australia's 21 largest cities
 daily_living_access_1600m    | double precision      | Score for access to daily living destinations within 1600 metres (supermarket, convenience and any public transport stop)
 social_infrastructure_mix    | double precision      | Social infrastructure mix score (/16)
 walk_02                      | integer               | Within 1000 metres of an activity centre with a supermarket
 walk_12                      | integer               | At least 15 dwellings per hectare in local walkable neighbourhood
 walk_13                      | integer               | At least 30 dwellings per hectare in local walkable neighbourhood
 walk_16                      | integer               | Distance to closest activity centre
 walk_17                      | double precision      | Pedshed ratio
 walk_21                      | double precision      | Local living destination types present
 trans_01                     | integer               | Access to bus stop < 400 m OR < 600 m of a tram stop OR < 800 m of a train station
 trans_02                     | integer               | Access to bus stop < 400 m
 trans_03                     | integer               | Within 400 m walk from a neighbourhood or town centre, or a bus stop, or in a 800 m walk from a railway station
 trans_04                     | integer               | Within 400 metres of an existing or planned public transport stop
 trans_05                     | integer               | Within 400 m of a bus stop every 30 min, or 800 m of a train station every 15 min
 trans_06                     | integer               | Within 400 m of public transport stop with a regular scheduled weekday service
 trans_07                     | integer               | Within 400 m of public transport with an average weekday service frequency of 30 minutes or less between 7am and 7pm within 400 metres
 trans_08                     | integer               | Within 400 m of public transport with an average weekday service frequency of 25 minutes or less between 7am and 7pm within 400 metres
 trans_09                     | integer               | Within 400 m of public transport with an average weekday service frequency of 20 minutes or less between 7am and 7pm within 400 metres
 os_public_01                 | integer               | Within 400 m of public open space
 os_public_02                 | integer               | Within 400 m of public open space larger than 1.5 Ha
 os_public_03                 | integer               | Within 400 m of public open space
 os_public_04                 | integer               | Within 300 m of any public open space
 os_public_05                 | integer               | Within 400 m of any local park of size 0.4 to 1 Ha
 os_public_06                 | integer               | Within 800 m of any neighbourhood park of size 1 to 5 Ha
 os_public_07                 | integer               | Within 2 km of any district park of size 5 to 20 Ha
 os_public_08                 | integer               | Within 400 m of a neighbourhood recreation park larger than 0.5 Ha
 os_public_09                 | integer               | Within 2.5 km of a district recreation park larger than 5 Ha
 os_public_10                 | integer               | Within 400 m of a park larger than 0.5 Ha
 os_public_11                 | integer               | Within 2 km of a park >2 Ha
 os_public_12                 | integer               | Distance to closest public open space with a public toilet within 100 metres
 os_public_14                 | integer               | Distance to closest public open space (OSM, 2018) within 3200 metres
 os_public_15                 | integer               | Distance to closest public open space <=0.4 Ha (OSM, 2018) within 3200 metres
 os_public_16                 | integer               | Distance to closest public open space >0.4 Ha (OSM, 2018) within 3200 metres
 os_public_17                 | integer               | Distance to closest public open space >0.5 Ha (OSM, 2018) within 3200 metres
 os_public_18                 | integer               | Distance to closest public open space >1.5 Ha (OSM, 2018) within 3200 metres
 os_public_19                 | integer               | Distance to closest public open space >2 Ha (OSM, 2018) within 3200 metres
 os_public_20                 | integer               | Distance to closest public open space >0.4 to <=1 Ha (OSM, 2018) within 3200 metres
 os_public_21                 | integer               | Distance to closest public open space >1 to <= 5 Ha (OSM, 2018) within 3200 metres
 os_public_22                 | integer               | Distance to closest public open space >5 Ha to <=20 Ha (OSM, 2018) within 3200 metres
 os_public_23                 | integer               | Distance to closest public open space >5 Ha (OSM, 2018) within 3200 metres
 os_public_24                 | integer               | Distance to closest public open space >20 Ha (OSM, 2018) within 3200 metres
 os_public_25                 | integer               | Distance to closest public open space with a sport facility (OSM, 2018) within 3200 metres
 hous_02                      | double precision      | Renting as a proportion of total
 hous_04                      | double precision      | Employed persons aged 15 and over using active transport as primary mode of travel to work
 hous_05                      | double precision      | Employed persons aged 15 and over using public transport as primary mode to travel to work
 hous_06                      | double precision      | Employed persons aged 15 and over using private vehicle/s as primary mode to travel to work
 food_12                      | bigint                | Count of supermarkets within 1600 m (OSM or 2017 in-house)
 food_13                      | bigint                | Count of fruit and vegetable grocers within 1600 m (OSM)
 food_14                      | bigint                | Count of other specialty food stores (bakeries, butchers, fishmongers and delicatessens) within 1600 m (OSM and/or 2017 in-house)
 food_15                      | bigint                | Count of healthier food outlets (supermarkets and fruit and vegetable grocers) within 1600 m (OSM and/or 2017 in-house)
 food_16                      | bigint                | Count of fast food outlets within 1600 m (OSM or 2017 in-house)
 food_17                      | double precision      | Percentage of food outlets within 1600 m that provide healthier food options (ie. supermarkets and fruit and vegetable grocers; OSM and/or 2017 in-house)
 food_18                      | double precision      | Ratio of food outlets within 1600 m that provide healthier food options (ie. supermarkets and fruit and vegetable grocers) to fast food outlets; OSM and/or 2017 in-house)
 food_19                      | double precision      | Percentage of food outlets within 1600 m that provide fresh food options  (ie. supermarkets, fruit and vegetable grocers, bakeries, butchers, fishmongers and delicatessens; OSM and/or 2017 in-house)
 food_20                      | double precision      | Ratio of food outlets within 1600 m that provide fresh food options (ie. supermarkets, fruit and vegetable grocers, bakeries, butchers, fishmongers and delicatessens) to fast food outlets (OSM and/or 2017 in-house)
 food_21                      | integer               | No food outlets within 1600 m (only considering supermarkets, fruit and vegetable grocers, and fast food as per healthier food measure;  OSM and/or 2017 in-house)
 food_22                      | integer               | No food outlets within 1600 m (including specialty food outlets: bakeries, butchers, fish mongers and delicatessens;  OSM and/or 2017 in-house)
 food_23_hard                 | integer               | Within 1km of a supermarket (OSM or 2017 in-house)
 food_24                      | integer               | Distance to closest fresh food outlet (bakery, fruit and vegetables grocer, delicatessen, and fish, meat, poultry outlet; OSM, 2018)
 food_25                      | integer               | Distance to closest healthy food outlet (supermarket or fruit and vegetables grocer; OSM, 2018)
 food_26                      | integer               | Distance to closest fast food outlet (HLC, 2017; OSM, 2018)
 food_27                      | integer               | Distance to closest dining establishment (cafe, restaurant, pub; OSM, 2018)
 community_01                 | integer               | Distance to closest community centre (HLC, 2016; OSM, 2018)
 community_02                 | integer               | Distance to closest cultural institution (museum, theatre, cinema, art gallery or art centre; OSM, 2018)
 alc_01                       | bigint                | Number of on-licenses within 400 m
 alc_02                       | bigint                | Number of off-licenses within 800 m
 alc_03                       | integer               | Distance to closest bar, pub or nightclub (OSM, 2018)
 childcare_01                 | integer               | Within 1600 m of a children's day care which meets guidelines
 childcare_02                 | integer               | Within 1600 m of a children's out of school hours care which meets guidelines
 health_01                    | integer               | Within 1600 m of a GP
 geom                         | geometry(Point,7845)  |
(104 rows)
```
</details>


### Loading the address indicator data

#### Initialise Address indicators table, defining variables and their data types

<details>
  <summary>
    Click to view code
  </summary>
  
```sql
CREATE TABLE li_2018_address_indicators 
(
gnaf_pid character varying(15) PRIMARY KEY,
count_objectid integer,
point_x double precision,
point_y double precision,
study_region text,
mb_code_2016 text,
mb_category_name_2016 text,
sa1_maincode_2016 text,
sa2_name_2016 text,
sa3_name_2016 text,
sa4_name_2016 text,
gccsa_name_2016 text,
state_name_2016 text,
ssc_name_2016 text,
lga_name_2016 text,
ucl_name_2016 text,
sos_name_2016 text,
uli_city double precision,
uli_national double precision,
li_community_culture_leisure double precision,
li_early_years double precision,
li_education double precision,
li_health_services double precision,
li_sport_rec double precision,
li_food double precision,
li_convenience double precision,
li_pt_regular_400m double precision,
li_public_os_large_400m double precision,
li_street_connectivity_1600m double precision,
li_dwelling_density_1600m double precision,
li_sa1_30_40_housing_stress double precision,
li_sa1_sa3_local_employment double precision,
walkability_city double precision,
walkability_national double precision,
daily_living_access_1600m double precision,
social_infrastructure_mix double precision,
walk_02 integer,
walk_12 integer,
walk_13 integer,
walk_16 integer,
walk_17 double precision,
walk_21 double precision,
trans_01 integer,
trans_02 integer,
trans_03 integer,
trans_04 integer,
trans_05 integer,
trans_06 integer,
trans_07 integer,
trans_08 integer,
trans_09 integer,
os_public_01 integer,
os_public_02 integer,
os_public_03 integer,
os_public_04 integer,
os_public_05 integer,
os_public_06 integer,
os_public_07 integer,
os_public_08 integer,
os_public_09 integer,
os_public_10 integer,
os_public_11 integer,
os_public_12 integer,
os_public_14 integer,
os_public_15 integer,
os_public_16 integer,
os_public_17 integer,
os_public_18 integer,
os_public_19 integer,
os_public_20 integer,
os_public_21 integer,
os_public_22 integer,
os_public_23 integer,
os_public_24 integer,
os_public_25 integer,
hous_02 double precision,
hous_04 double precision,
hous_05 double precision,
hous_06 double precision,
food_12 bigint,
food_13 bigint,
food_14 bigint,
food_15 bigint,
food_16 bigint,
food_17 double precision,
food_18 double precision,
food_19 double precision,
food_20 double precision,
food_21 integer,
food_22 integer,
food_23_hard integer,
food_24 integer,
food_25 integer,
food_26 integer,
food_27 integer,
community_01 integer,
community_02 integer,
alc_01 bigint,
alc_02 bigint,
alc_03 integer,
childcare_01 integer,
childcare_02 integer,
health_01 integer
);
```
</details>

#### Copy the data from CSV.  

```sql
COPY li_2018_address_indicators FROM 'D:/projects/ntnl_li_2018/data/National Liveability 2018 - Final Outputs/For dissemination/hlc_ntnl_liveability_2018_address_points_indicators_epsg7845.csv' WITH DELIMITER ',' CSV HEADER;
```
#### Add in a geometry column
```sql
ALTER TABLE li_2018_address_indicators ADD COLUMN geom geometry(Point, 7845);
UPDATE li_2018_address_indicators SET geom = ST_SetSRID(ST_MakePoint(point_x, point_y), 7845);
```
#### Create spatial index
```sql
CREATE INDEX li_2018_address_indicators_geom_idx ON li_2018_address_indicators USING GIST (geom);
```
#### Optionally describe the data

<details>
  <summary>
    Click to view code
  </summary>
  
```sql
COMMENT ON TABLE li_2018_address_indicators IS $$Liveability indicators for residential locations (address points in urban Mesh Blocks with dwellings at 2016 census)$$;
COMMENT ON COLUMN li_2018_address_indicators.gnaf_pid IS $$Unique identifier using PSMA Open G-NAF 2018 data$$;
COMMENT ON COLUMN li_2018_address_indicators.count_objectid IS $$Count of co-located G-NAF points (only first unique location retained)$$;
COMMENT ON COLUMN li_2018_address_indicators.point_x IS $$Easting (metres; EPSG 7845)$$;
COMMENT ON COLUMN li_2018_address_indicators.point_y IS $$Northing (metres; EPSG 7845)$$;
COMMENT ON COLUMN li_2018_address_indicators.study_region IS $$City name$$;
COMMENT ON COLUMN li_2018_address_indicators.mb_code_2016 IS $$Mesh Block (ASGS 2016) identifier$$;
COMMENT ON COLUMN li_2018_address_indicators.mb_category_name_2016 IS $$Mesh Block category$$;
COMMENT ON COLUMN li_2018_address_indicators.sa1_maincode_2016 IS $$Statistical Area 1 (SA1) maincode identifier$$;
COMMENT ON COLUMN li_2018_address_indicators.sa2_name_2016 IS $$SA2 name$$;
COMMENT ON COLUMN li_2018_address_indicators.sa3_name_2016 IS $$SA3 name$$;
COMMENT ON COLUMN li_2018_address_indicators.sa4_name_2016 IS $$SA4 name$$;
COMMENT ON COLUMN li_2018_address_indicators.gccsa_name_2016 IS $$Greater Capital City Statistical Area name$$;
COMMENT ON COLUMN li_2018_address_indicators.state_name_2016 IS $$State name$$;
COMMENT ON COLUMN li_2018_address_indicators.ssc_name_2016 IS $$Suburb name$$;
COMMENT ON COLUMN li_2018_address_indicators.lga_name_2016 IS $$LGA name$$;
COMMENT ON COLUMN li_2018_address_indicators.ucl_name_2016 IS $$Urban centre and locality name$$;
COMMENT ON COLUMN li_2018_address_indicators.sos_name_2016 IS $$Section of state name $$;
COMMENT ON COLUMN li_2018_address_indicators.uli_city IS $$Urban Liveability Index, relative to locations within this city$$;
COMMENT ON COLUMN li_2018_address_indicators.uli_national IS $$Urban Liveability Index, relative to locations across Australia's 21 largest cities$$;
COMMENT ON COLUMN li_2018_address_indicators.li_community_culture_leisure IS $$Score for access to community, culture and leisure destinations (community centre and library within 1000m, and museum/art gallery and cinema/theater within 3200m) (/1)$$;
COMMENT ON COLUMN li_2018_address_indicators.li_early_years IS $$Score for access to child care (any meeting ACECQA recommendations) within 800 metres and childcare (outside school hours meeting recommendations) within 1600 metres (/1)$$;
COMMENT ON COLUMN li_2018_address_indicators.li_education IS $$Score for access to primary and secondary public schools within 1600 metres (/1)$$;
COMMENT ON COLUMN li_2018_address_indicators.li_health_services IS $$Score for access to health services (GP, pharmacy, maternal, child and family health care, aged care facility and other community health care) within 1000 metres (/1)$$;
COMMENT ON COLUMN li_2018_address_indicators.li_sport_rec IS $$Score for access to an area of open space with sport/recreation facilities within 1000 metres, and a public swimming pool within 1200 metres (/1)$$;
COMMENT ON COLUMN li_2018_address_indicators.li_food IS $$Score for access to a supermarket and fresh fruit and vegetables within 1000 metres, and meat/seafood within 3200 metres (/1)$$;
COMMENT ON COLUMN li_2018_address_indicators.li_convenience IS $$Score for access to convenience destinations (convenience store and petrol station within 1000 metres, and a newsagent within 3200 metres) (/1)$$;
COMMENT ON COLUMN li_2018_address_indicators.li_pt_regular_400m IS $$Within 400 m of public transport with an average weekday service frequency of 30 minutes or less between 7am and 7pm within 400 metres$$;
COMMENT ON COLUMN li_2018_address_indicators.li_public_os_large_400m IS $$Within 400 m of public open space larger than 1.5 Ha$$;
COMMENT ON COLUMN li_2018_address_indicators.li_street_connectivity_1600m IS $$Street connectivity$$;
COMMENT ON COLUMN li_2018_address_indicators.li_dwelling_density_1600m IS $$Dwelling density$$;
COMMENT ON COLUMN li_2018_address_indicators.li_sa1_30_40_housing_stress IS $$Percentage of SA1 households with income in the bottom 40% of the income distribution spending more than 30% of household income on housing costs$$;
COMMENT ON COLUMN li_2018_address_indicators.li_sa1_sa3_local_employment IS $$Percentage of employed persons working in the community (SA3) in which they live$$;
COMMENT ON COLUMN li_2018_address_indicators.walkability_city IS $$Walkability index, combining street connectivity, dwelling density and daily living destinations, relative to locations within this city$$;
COMMENT ON COLUMN li_2018_address_indicators.walkability_national IS $$Walkability index, combining street connectivity, dwelling density and daily living destinations, relative to locations across Australia's 21 largest cities$$;
COMMENT ON COLUMN li_2018_address_indicators.daily_living_access_1600m IS $$Score for access to daily living destinations within 1600 metres (supermarket, convenience and any public transport stop)$$;
COMMENT ON COLUMN li_2018_address_indicators.social_infrastructure_mix IS $$Social infrastructure mix score (/16)$$;
COMMENT ON COLUMN li_2018_address_indicators.walk_02 IS $$Within 1000 metres of an activity centre with a supermarket$$;
COMMENT ON COLUMN li_2018_address_indicators.walk_12 IS $$At least 15 dwellings per hectare in local walkable neighbourhood$$;
COMMENT ON COLUMN li_2018_address_indicators.walk_13 IS $$At least 30 dwellings per hectare in local walkable neighbourhood$$;
COMMENT ON COLUMN li_2018_address_indicators.walk_16 IS $$Distance to closest activity centre$$;
COMMENT ON COLUMN li_2018_address_indicators.walk_17 IS $$Pedshed ratio$$;
COMMENT ON COLUMN li_2018_address_indicators.walk_21 IS $$Local living destination types present$$;
COMMENT ON COLUMN li_2018_address_indicators.trans_01 IS $$Access to bus stop < 400 m OR < 600 m of a tram stop OR < 800 m of a train station$$;
COMMENT ON COLUMN li_2018_address_indicators.trans_02 IS $$Access to bus stop < 400 m$$;
COMMENT ON COLUMN li_2018_address_indicators.trans_03 IS $$Within 400 m walk from a neighbourhood or town centre, or a bus stop, or in a 800 m walk from a railway station$$;
COMMENT ON COLUMN li_2018_address_indicators.trans_04 IS $$Within 400 metres of an existing or planned public transport stop$$;
COMMENT ON COLUMN li_2018_address_indicators.trans_05 IS $$Within 400 m of a bus stop every 30 min, or 800 m of a train station every 15 min$$;
COMMENT ON COLUMN li_2018_address_indicators.trans_06 IS $$Within 400 m of public transport stop with a regular scheduled weekday service$$;
COMMENT ON COLUMN li_2018_address_indicators.trans_07 IS $$Within 400 m of public transport with an average weekday service frequency of 30 minutes or less between 7am and 7pm within 400 metres$$;
COMMENT ON COLUMN li_2018_address_indicators.trans_08 IS $$Within 400 m of public transport with an average weekday service frequency of 25 minutes or less between 7am and 7pm within 400 metres$$;
COMMENT ON COLUMN li_2018_address_indicators.trans_09 IS $$Within 400 m of public transport with an average weekday service frequency of 20 minutes or less between 7am and 7pm within 400 metres$$;
COMMENT ON COLUMN li_2018_address_indicators.os_public_01 IS $$Within 400 m of public open space$$;
COMMENT ON COLUMN li_2018_address_indicators.os_public_02 IS $$Within 400 m of public open space larger than 1.5 Ha$$;
COMMENT ON COLUMN li_2018_address_indicators.os_public_03 IS $$Within 400 m of public open space$$;
COMMENT ON COLUMN li_2018_address_indicators.os_public_04 IS $$Within 300 m of any public open space$$;
COMMENT ON COLUMN li_2018_address_indicators.os_public_05 IS $$Within 400 m of any local park of size 0.4 to 1 Ha$$;
COMMENT ON COLUMN li_2018_address_indicators.os_public_06 IS $$Within 800 m of any neighbourhood park of size 1 to 5 Ha$$;
COMMENT ON COLUMN li_2018_address_indicators.os_public_07 IS $$Within 2 km of any district park of size 5 to 20 Ha$$;
COMMENT ON COLUMN li_2018_address_indicators.os_public_08 IS $$Within 400 m of a neighbourhood recreation park larger than 0.5 Ha$$;
COMMENT ON COLUMN li_2018_address_indicators.os_public_09 IS $$Within 2.5 km of a district recreation park larger than 5 Ha$$;
COMMENT ON COLUMN li_2018_address_indicators.os_public_10 IS $$Within 400 m of a park larger than 0.5 Ha$$;
COMMENT ON COLUMN li_2018_address_indicators.os_public_11 IS $$Within 2 km of a park >2 Ha$$;
COMMENT ON COLUMN li_2018_address_indicators.os_public_12 IS $$Distance to closest public open space with a public toilet within 100 metres$$;
COMMENT ON COLUMN li_2018_address_indicators.os_public_14 IS $$Distance to closest public open space (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_address_indicators.os_public_15 IS $$Distance to closest public open space <=0.4 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_address_indicators.os_public_16 IS $$Distance to closest public open space >0.4 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_address_indicators.os_public_17 IS $$Distance to closest public open space >0.5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_address_indicators.os_public_18 IS $$Distance to closest public open space >1.5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_address_indicators.os_public_19 IS $$Distance to closest public open space >2 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_address_indicators.os_public_20 IS $$Distance to closest public open space >0.4 to <=1 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_address_indicators.os_public_21 IS $$Distance to closest public open space >1 to <= 5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_address_indicators.os_public_22 IS $$Distance to closest public open space >5 Ha to <=20 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_address_indicators.os_public_23 IS $$Distance to closest public open space >5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_address_indicators.os_public_24 IS $$Distance to closest public open space >20 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_address_indicators.os_public_25 IS $$Distance to closest public open space with a sport facility (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_address_indicators.hous_02 IS $$Renting as a proportion of total$$;
COMMENT ON COLUMN li_2018_address_indicators.hous_04 IS $$Employed persons aged 15 and over using active transport as primary mode of travel to work $$;
COMMENT ON COLUMN li_2018_address_indicators.hous_05 IS $$Employed persons aged 15 and over using public transport as primary mode to travel to work$$;
COMMENT ON COLUMN li_2018_address_indicators.hous_06 IS $$Employed persons aged 15 and over using private vehicle/s as primary mode to travel to work$$;
COMMENT ON COLUMN li_2018_address_indicators.food_12 IS $$Count of supermarkets within 1600 m (OSM or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_address_indicators.food_13 IS $$Count of fruit and vegetable grocers within 1600 m (OSM)$$;
COMMENT ON COLUMN li_2018_address_indicators.food_14 IS $$Count of other specialty food stores (bakeries, butchers, fishmongers and delicatessens) within 1600 m (OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_address_indicators.food_15 IS $$Count of healthier food outlets (supermarkets and fruit and vegetable grocers) within 1600 m (OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_address_indicators.food_16 IS $$Count of fast food outlets within 1600 m (OSM or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_address_indicators.food_17 IS $$Percentage of food outlets within 1600 m that provide healthier food options (ie. supermarkets and fruit and vegetable grocers; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_address_indicators.food_18 IS $$Ratio of food outlets within 1600 m that provide healthier food options (ie. supermarkets and fruit and vegetable grocers) to fast food outlets; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_address_indicators.food_19 IS $$Percentage of food outlets within 1600 m that provide fresh food options  (ie. supermarkets, fruit and vegetable grocers, bakeries, butchers, fishmongers and delicatessens; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_address_indicators.food_20 IS $$Ratio of food outlets within 1600 m that provide fresh food options (ie. supermarkets, fruit and vegetable grocers, bakeries, butchers, fishmongers and delicatessens) to fast food outlets (OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_address_indicators.food_21 IS $$No food outlets within 1600 m (only considering supermarkets, fruit and vegetable grocers, and fast food as per healthier food measure;  OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_address_indicators.food_22 IS $$No food outlets within 1600 m (including specialty food outlets: bakeries, butchers, fish mongers and delicatessens;  OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_address_indicators.food_23_hard IS $$Within 1km of a supermarket (OSM or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_address_indicators.food_24 IS $$Distance to closest fresh food outlet (bakery, fruit and vegetables grocer, delicatessen, and fish, meat, poultry outlet; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_address_indicators.food_25 IS $$Distance to closest healthy food outlet (supermarket or fruit and vegetables grocer; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_address_indicators.food_26 IS $$Distance to closest fast food outlet (HLC, 2017; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_address_indicators.food_27 IS $$Distance to closest dining establishment (cafe, restaurant, pub; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_address_indicators.community_01 IS $$Distance to closest community centre (HLC, 2016; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_address_indicators.community_02 IS $$Distance to closest cultural institution (museum, theatre, cinema, art gallery or art centre; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_address_indicators.alc_01 IS $$Number of on-licenses within 400 m$$;
COMMENT ON COLUMN li_2018_address_indicators.alc_02 IS $$Number of off-licenses within 800 m$$;
COMMENT ON COLUMN li_2018_address_indicators.alc_03 IS $$Distance to closest bar, pub or nightclub (OSM, 2018)$$;
COMMENT ON COLUMN li_2018_address_indicators.childcare_01 IS $$Within 1600 m of a children's day care which meets guidelines$$;
COMMENT ON COLUMN li_2018_address_indicators.childcare_02 IS $$Within 1600 m of a children's out of school hours care which meets guidelines$$;
COMMENT ON COLUMN li_2018_address_indicators.health_01 IS $$Within 1600 m of a GP$$;
```
</details>

To view comments for the table we just created, type `\d+ li_2018_address_indicators`.   Alternatively, for a more concisely formatted data dictionary use the provided custom dictionary function to query by running:
`SELECT * FROM dictionary('li_2018_address_indicators')`;

### Loading the Mesh Block indicator data

#### Initialise Mesh Block indicators table, defining variables and their data types

<details>
  <summary>
    Click to view code
  </summary>

```sql
CREATE TABLE li_2018_mb_indicators 
(
mb_code_2016 text PRIMARY KEY,
study_region text,
mb_category_name_2016 text,
sa1_maincode_2016 text,
sa2_name_2016 text,
sa3_name_2016 text,
sa4_name_2016 text,
gccsa_name_2016 text,
state_name_2016 text,
ssc_name_2016 text,
lga_name_2016 text,
ucl_name_2016 text,
sos_name_2016 text,
dwelling int,
person int,
sample_count int,
sample_count_per_ha float,
area_ha float,
dwellings_per_ha float,
uli_city float,
uli_national float,
li_community_culture_leisure float,
li_early_years float,
li_education float,
li_health_services float,
li_sport_rec float,
li_food float,
li_convenience float,
li_pt_regular_400m float,
li_public_os_large_400m float,
li_street_connectivity_1600m float,
li_dwelling_density_1600m float,
li_sa1_30_40_housing_stress float,
li_sa1_sa3_local_employment float,
walkability_city float,
walkability_national float,
daily_living_access_1600m float,
social_infrastructure_mix float,
walk_02 float,
walk_02_policy boolean,
walk_12 float,
walk_12_policy boolean,
walk_13 float,
walk_13_policy boolean,
walk_14_policy boolean,
walk_15_policy boolean,
walk_16 float,
walk_17 float,
walk_21 float,
trans_01 float,
trans_01_policy boolean,
trans_02 float,
trans_02_policy boolean,
trans_03 float,
trans_03_policy boolean,
trans_04 float,
trans_04_policy boolean,
trans_05 float,
trans_05_policy boolean,
trans_06 float,
trans_07 float,
trans_08 float,
trans_09 float,
os_public_01 float,
os_public_02 float,
os_public_03 float,
os_public_03_policy boolean,
os_public_04 float,
os_public_04_policy boolean,
os_public_05 float,
os_public_05_policy boolean,
os_public_06 float,
os_public_06_policy boolean,
os_public_07 float,
os_public_07_policy boolean,
os_public_08 float,
os_public_08_policy boolean,
os_public_09 float,
os_public_09_policy boolean,
os_public_10 float,
os_public_10_policy boolean,
os_public_11 float,
os_public_11_policy boolean,
os_public_12 float,
os_public_14 float,
os_public_15 float,
os_public_16 float,
os_public_17 float,
os_public_18 float,
os_public_19 float,
os_public_20 float,
os_public_21 float,
os_public_22 float,
os_public_23 float,
os_public_24 float,
os_public_25 float,
hous_02 float,
hous_04 float,
hous_05 float,
hous_06 float,
food_12 float,
food_13 float,
food_14 float,
food_15 float,
food_16 float,
food_17 float,
food_18 float,
food_19 float,
food_20 float,
food_21 float,
food_22 float,
food_23_hard float,
food_24 float,
food_25 float,
food_26 float,
food_27 float,
community_01 float,
community_02 float,
alc_01 float,
alc_02 float,
alc_03 float,
childcare_01 float,
childcare_02 float,
health_01 float,
dist_m_activity_centres float,
dist_m_alcohol_offlicence float,
dist_m_alcohol_onlicence float,
dist_m_alcohol_osm float,
dist_m_all_schools float,
dist_m_art_centre_osm float,
dist_m_art_gallery_osm float,
dist_m_bakery_osm float,
dist_m_bar_osm float,
dist_m_cafe_osm float,
dist_m_childcare_all float,
dist_m_childcare_all_exc float,
dist_m_childcare_all_meet float,
dist_m_childcare_oshc float,
dist_m_childcare_oshc_exc float,
dist_m_childcare_oshc_meet float,
dist_m_childcare_preschool float,
dist_m_childcare_preschool_exc float,
dist_m_childcare_preschool_meet float,
dist_m_cinema_osm float,
dist_m_community_centre_osm float,
dist_m_convenience_osm float,
dist_m_deli_osm float,
dist_m_disability_employment float,
dist_m_fast_food float,
dist_m_fastfood_osm float,
dist_m_food_court_osm float,
dist_m_food_health_osm float,
dist_m_food_other_osm float,
dist_m_fruit_veg_osm float,
dist_m_gtfs_2018_stop_30_mins_final float,
dist_m_gtfs_2018_stops float,
dist_m_gtfs_2018_stops_bus float,
dist_m_gtfs_2018_stops_ferry float,
dist_m_gtfs_2018_stops_train float,
dist_m_gtfs_2018_stops_tram float,
dist_m_gtfs_20191008_20191205_bus_0015 float,
dist_m_gtfs_20191008_20191205_bus_0030 float,
dist_m_gtfs_20191008_20191205_bus_0045 float,
dist_m_gtfs_20191008_20191205_bus_any float,
dist_m_gtfs_20191008_20191205_ferry_0015 float,
dist_m_gtfs_20191008_20191205_ferry_0030 float,
dist_m_gtfs_20191008_20191205_ferry_0045 float,
dist_m_gtfs_20191008_20191205_ferry_any float,
dist_m_gtfs_20191008_20191205_revised_all float,
dist_m_gtfs_20191008_20191205_revised_frequent30 float,
dist_m_gtfs_20191008_20191205_train_0015 float,
dist_m_gtfs_20191008_20191205_train_0030 float,
dist_m_gtfs_20191008_20191205_train_0045 float,
dist_m_gtfs_20191008_20191205_train_any float,
dist_m_gtfs_20191008_20191205_tram_0015 float,
dist_m_gtfs_20191008_20191205_tram_0030 float,
dist_m_gtfs_20191008_20191205_tram_0045 float,
dist_m_gtfs_20191008_20191205_tram_any float,
dist_m_hlc_2016_community_centres float,
dist_m_libraries float,
dist_m_market_osm float,
dist_m_meat_seafood_osm float,
dist_m_museum_osm float,
dist_m_newsagent_osm float,
dist_m_nhsd_2017_aged_care_residential float,
dist_m_nhsd_2017_dentist float,
dist_m_nhsd_2017_gp float,
dist_m_nhsd_2017_hospital float,
dist_m_nhsd_2017_mc_family_health float,
dist_m_nhsd_2017_other_community_health_care float,
dist_m_nhsd_2017_pharmacy float,
dist_m_P_12_Schools float,
dist_m_P_12_Schools_catholic float,
dist_m_P_12_Schools_gov float,
dist_m_P_12_Schools_indep float,
dist_m_petrolstation_osm float,
dist_m_pharmacy_osm float,
dist_m_place_of_worship_osm float,
dist_m_playgrounds float,
dist_m_postoffice_osm float,
dist_m_primary_schools float,
dist_m_primary_schools_catholic float,
dist_m_primary_schools_gov float,
dist_m_primary_schools_indep float,
dist_m_pub_osm float,
dist_m_public_swimming_pool_osm float,
dist_m_restaurant_osm float,
dist_m_secondary_schools float,
dist_m_secondary_schools_catholic float,
dist_m_secondary_schools_gov float,
dist_m_secondary_schools_indep float,
dist_m_special_schools float,
dist_m_supermarket float,
dist_m_supermarket_osm float,
dist_m_theatre_osm float
);
```
</details>

### Copy the data from CSV
```sql
COPY li_2018_mb_indicators FROM 'D:/projects/ntnl_li_2018/data/National Liveability 2018 - Final Outputs/For dissemination/hlc_ntnl_liveability_2018_Mesh_Block_2016.csv' WITH DELIMITER ',' CSV HEADER;
```

#### Optionally describe the data

<details>
  <summary>
    Click to view code
  </summary>

```sql
COMMENT ON TABLE li_2018_mb_indicators IS $$Mesh Block averages of residential liveability indicators and distance to closest estimates, with dwelling and person counts as well as area linkage codes to support aggregation to larger area scales (optionally with weighting; recommended)$$;
COMMENT ON COLUMN li_2018_mb_indicators.mb_code_2016 IS $$Mesh Block (ASGS 2016) identifier$$;
COMMENT ON COLUMN li_2018_mb_indicators.study_region IS $$City name$$;
COMMENT ON COLUMN li_2018_mb_indicators.mb_category_name_2016 IS $$Mesh Block category$$;
COMMENT ON COLUMN li_2018_mb_indicators.sa1_maincode_2016 IS $$Statistical Area 1 (SA1) maincode identifier$$;
COMMENT ON COLUMN li_2018_mb_indicators.sa2_name_2016 IS $$SA2 name$$;
COMMENT ON COLUMN li_2018_mb_indicators.sa3_name_2016 IS $$SA3 name$$;
COMMENT ON COLUMN li_2018_mb_indicators.sa4_name_2016 IS $$SA4 name$$;
COMMENT ON COLUMN li_2018_mb_indicators.gccsa_name_2016 IS $$Greater Capital City Statistical Area name$$;
COMMENT ON COLUMN li_2018_mb_indicators.state_name_2016 IS $$State name$$;
COMMENT ON COLUMN li_2018_mb_indicators.ssc_name_2016 IS $$Suburb name$$;
COMMENT ON COLUMN li_2018_mb_indicators.lga_name_2016 IS $$LGA name$$;
COMMENT ON COLUMN li_2018_mb_indicators.ucl_name_2016 IS $$Urban centre and locality name$$;
COMMENT ON COLUMN li_2018_mb_indicators.sos_name_2016 IS $$Section of state name$$;
COMMENT ON COLUMN li_2018_mb_indicators.dwelling IS $$Dwelling count (Mesh Block dwelling count > 0 was an inclusion criteria for sampling)$$;
COMMENT ON COLUMN li_2018_mb_indicators.person IS $$Person count (persons usually resident)$$;
COMMENT ON COLUMN li_2018_mb_indicators.sample_count IS $$address points in area$$;
COMMENT ON COLUMN li_2018_mb_indicators.sample_count_per_ha IS $$address point density per hectare$$;
COMMENT ON COLUMN li_2018_mb_indicators.area_ha IS $$Area in hectares$$;
COMMENT ON COLUMN li_2018_mb_indicators.dwellings_per_ha IS $$gross dwelling density$$;
COMMENT ON COLUMN li_2018_mb_indicators.uli_city IS $$Average Urban Liveability Index, relative to locations within this city$$;
COMMENT ON COLUMN li_2018_mb_indicators.uli_national IS $$Average Urban Liveability Index, relative to locations across Australia's 21 largest cities$$;
COMMENT ON COLUMN li_2018_mb_indicators.li_community_culture_leisure IS $$Average score for access to community, culture and leisure destinations (community centre and library within 1000m, and museum/art gallery and cinema/theater within 3200m) (/1)$$;
COMMENT ON COLUMN li_2018_mb_indicators.li_early_years IS $$Average score for access to child care (any meeting ACECQA recommendations) within 800 metres and childcare (outside school hours meeting recommendations) within 1600 metres (/1)$$;
COMMENT ON COLUMN li_2018_mb_indicators.li_education IS $$Average score for access to primary and secondary public schools within 1600 metres (/1)$$;
COMMENT ON COLUMN li_2018_mb_indicators.li_health_services IS $$Average score for access to health services (GP, pharmacy, maternal, child and family health care, aged care facility and other community health care) within 1000 metres (/1)$$;
COMMENT ON COLUMN li_2018_mb_indicators.li_sport_rec IS $$Average score for access to an area of open space with sport/recreation facilities within 1000 metres, and a public swimming pool within 1200 metres (/1)$$;
COMMENT ON COLUMN li_2018_mb_indicators.li_food IS $$Average score for access to a supermarket and fresh fruit and vegetables within 1000 metres, and meat/seafood within 3200 metres (/1)$$;
COMMENT ON COLUMN li_2018_mb_indicators.li_convenience IS $$Average score for access to convenience destinations (convenience store and petrol station within 1000 metres, and a newsagent within 3200 metres) (/1)$$;
COMMENT ON COLUMN li_2018_mb_indicators.li_pt_regular_400m IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 30 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_mb_indicators.li_public_os_large_400m IS $$Percentage of dwellings < 400 m of public open space > 1.5 ha$$;
COMMENT ON COLUMN li_2018_mb_indicators.li_street_connectivity_1600m IS $$Average local street connectivity per square kilometre$$;
COMMENT ON COLUMN li_2018_mb_indicators.li_dwelling_density_1600m IS $$Average local dwelling density per hectare (Ha) $$;
COMMENT ON COLUMN li_2018_mb_indicators.li_sa1_30_40_housing_stress IS $$Percentage of SA1 households with income in the bottom 40% of the income distribution spending more than 30% of household income on housing costs$$;
COMMENT ON COLUMN li_2018_mb_indicators.li_sa1_sa3_local_employment IS $$Percentage of employed persons who live and work in the same community$$;
COMMENT ON COLUMN li_2018_mb_indicators.walkability_city IS $$Average walkability index, combining street connectivity, dwelling density and daily living destinations, relative to locations within this city$$;
COMMENT ON COLUMN li_2018_mb_indicators.walkability_national IS $$Average walkability index, combining street connectivity, dwelling density and daily living destinations, relative to locations across Australia's 21 largest cities$$;
COMMENT ON COLUMN li_2018_mb_indicators.daily_living_access_1600m IS $$Average number of daily living types present, measured as a score of 0-3, with 1 point for each category of convenience store/petrol station/newsagent, PT stop, supermarket within 1600m network distance$$;
COMMENT ON COLUMN li_2018_mb_indicators.social_infrastructure_mix IS $$Average social infrastructure mix score (/16)$$;
COMMENT ON COLUMN li_2018_mb_indicators.walk_02 IS $$Percentage of dwellings <1 km walking distance of an activity centre with a supermarket$$;
COMMENT ON COLUMN li_2018_mb_indicators.walk_02_policy IS $$At least 80% of dwellings are within 1 km walking distance of an activity centre with a supermarket$$;
COMMENT ON COLUMN li_2018_mb_indicators.walk_12 IS $$Percentage of dwellings with local dwelling density of 15 dwellings per hectare or greater$$;
COMMENT ON COLUMN li_2018_mb_indicators.walk_12_policy IS $$15 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_mb_indicators.walk_13 IS $$Percentage of dwellings with local dwelling density of 30 dwellings per hectare or greater$$;
COMMENT ON COLUMN li_2018_mb_indicators.walk_13_policy IS $$Local dwelling density of 30 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_mb_indicators.walk_14_policy IS $$Gross dwelling density of 15 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_mb_indicators.walk_15_policy IS $$Gross dwelling density of 30 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_mb_indicators.walk_16 IS $$Average distance to closest activity centre (proxy measure: supermarket within a commercial zoned Mesh Block)$$;
COMMENT ON COLUMN li_2018_mb_indicators.walk_17 IS $$Average pedshed ratio, defined as the area of the 400 m pedestrian network from each residential dwelling buffered by 50m divided by the radial 400 m "crow flies" area (i.e. 50.2 Ha.)$$;
COMMENT ON COLUMN li_2018_mb_indicators.walk_21 IS $$Average number of local living types present (see paper of Mavoa et al)$$;
COMMENT ON COLUMN li_2018_mb_indicators.trans_01 IS $$Percentage of dwellings with access to bus stop within 400 m, a tram stop within 600m, or a train station within 800 m$$;
COMMENT ON COLUMN li_2018_mb_indicators.trans_01_policy IS $$95% or more of dwellings with access to bus stop within 400 m, a tram stop within 600m, or a train station within 800 m$$;
COMMENT ON COLUMN li_2018_mb_indicators.trans_02 IS $$Percentage of dwellings with access to bus stop < 400 m$$;
COMMENT ON COLUMN li_2018_mb_indicators.trans_02_policy IS $$95% or more of dwellings with access to bus stop < 400 m$$;
COMMENT ON COLUMN li_2018_mb_indicators.trans_03 IS $$Percentage of dwellings < 400m walk from a neighbourhood or town centre, or a bus stop, or in a 800m walk from a railway station.$$;
COMMENT ON COLUMN li_2018_mb_indicators.trans_03_policy IS $$60% or more of dwellings < 400m walk from a neighbourhood or town centre, or a bus stop, or in a 800m walk from a railway station.$$;
COMMENT ON COLUMN li_2018_mb_indicators.trans_04 IS $$Percentage of dwellings < 400 metres of an existing or planned public transport stop$$;
COMMENT ON COLUMN li_2018_mb_indicators.trans_04_policy IS $$100% of dwellings < 400 metres of an existing or planned public transport stop$$;
COMMENT ON COLUMN li_2018_mb_indicators.trans_05 IS $$Percentage of dwellings < 400 m of a bus stop every 30 min OR < 800 m of a train station every 15 min$$;
COMMENT ON COLUMN li_2018_mb_indicators.trans_05_policy IS $$100% of dwellings < 400 m of a bus stop every 30 min OR < 800 m of a train station every 15 min$$;
COMMENT ON COLUMN li_2018_mb_indicators.trans_06 IS $$Percentage of dwellings < 400 m of a public transport stop with a scheduled service at least every 30 minutes between 7am and 7pm on a normal weekday (= a combined measure of proximity and frequency)$$;
COMMENT ON COLUMN li_2018_mb_indicators.trans_07 IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 30 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_mb_indicators.trans_08 IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 25 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_mb_indicators.trans_09 IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 20 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_01 IS $$Percentage of dwellings within 400 m or less distance of public open space$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_02 IS $$Percentage of dwellings < 400 m of public open space > 1.5 ha$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_03 IS $$Percentage of dwellings within 400 m or less distance of public open space$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_03_policy IS $$95% or more of dwellings within 400 m or less distance of public open space$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_04 IS $$Percentage of dwellings within 300 m or less distance of any public open space$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_04_policy IS $$100% of dwellings within 300 m or less distance of any public open space$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_05 IS $$Percentage of dwellings within 400 m or less distance of any local park (> 0.4 to <=1 ha)$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_05_policy IS $$50% or more of dwellings within 400 m or less distance of any local park (> 0.4 to <=1 ha)$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_06 IS $$Percentage of dwellings within 800 m or less distance of any neighbourhood park (>1 ha to <= 5ha)$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_06_policy IS $$50% or more of dwellings within 800 m or less distance of any neighbourhood park (>1 ha to <= 5ha)$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_07 IS $$Percentage of dwellings within 2 km or less of any district park (>5 ha to <=20 ha)$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_07_policy IS $$50% or more of dwellings within 2 km or less of any district park (>5 ha to <=20 ha)$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_08 IS $$Percentage of dwellings within 400 m or less distance of a neighbourhood recreation park (>0.5 ha)$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_08_policy IS $$90% or more of dwellings within 400 m or less distance of a neighbourhood recreation park (>0.5 ha)$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_09 IS $$Percentage of dwellings within 2.5 km or less distance of a district recreation park (>5 ha)$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_09_policy IS $$90% or more of dwellings within 2.5 km or less distance of a district recreation park (>5 ha)$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_10 IS $$Percentage of dwellings within 400 m or less distance of a park larger than 0.5 Ha$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_10_policy IS $$50% or more of dwellings within 400 m or less distance of a park larger than 0.5 Ha$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_11 IS $$Percentage of dwellings within 2 km or less distance of a park larger than 2 Ha$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_11_policy IS $$50% or more of dwellings within 2 km or less distance of a park larger than 2 Ha$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_12 IS $$Average distance to closest POS with a public toilet within 100 metres$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_14 IS $$Average distance to closest public open space (OSM, 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_15 IS $$Average distance to closest public open space <=0.4 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_16 IS $$Average distance to closest public open space >0.4 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_17 IS $$Average distance to closest public open space >0.5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_18 IS $$Average distance to closest public open space >1.5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_19 IS $$Average distance to closest public open space >2 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_20 IS $$Average distance to closest public open space >0.4 to <=1 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_21 IS $$Average distance to closest public open space >1 to <= 5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_22 IS $$Average distance to closest public open space >5 Ha to <=20 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_23 IS $$Average distance to closest public open space >5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_24 IS $$Average distance to closest public open space >20 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_mb_indicators.os_public_25 IS $$Average distance to closest public open space with a sport facility (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_mb_indicators.hous_02 IS $$Percentage of dwellings renting as a proportion of total$$;
COMMENT ON COLUMN li_2018_mb_indicators.hous_04 IS $$Percentage of employed persons aged 15 and over using active transport to travel to work$$;
COMMENT ON COLUMN li_2018_mb_indicators.hous_05 IS $$Percentage of employed persons aged 15 and over using public transport to travel to work$$;
COMMENT ON COLUMN li_2018_mb_indicators.hous_06 IS $$Percentage of employed persons aged 15 and over using private vehicle/s to travel to work$$;
COMMENT ON COLUMN li_2018_mb_indicators.food_12 IS $$Average count of supermarkets within 1.6km$$;
COMMENT ON COLUMN li_2018_mb_indicators.food_13 IS $$Average count of fruit and vegetable grocers within 1.6km$$;
COMMENT ON COLUMN li_2018_mb_indicators.food_14 IS $$Average count of specialty food stores (bakeries, butchers, fishmongers and delicatessens) within 1.6km$$;
COMMENT ON COLUMN li_2018_mb_indicators.food_15 IS $$Average count of healther food outlets (supermarkets and fruit and vegetable grocers) within 1.6 km (OSM, or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_mb_indicators.food_16 IS $$Average count of fast food outlets within 1.6km (OSM, or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_mb_indicators.food_17 IS $$Average percentage of food outlets within 1.6km that provide healthier food options (ie. supermarkets and fruit and vegetable grocers; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_mb_indicators.food_18 IS $$Average ratio of food outlets within 1.6km that provide healthier food options (ie. supermarkets and fruit and vegetable grocers) to fast food outlets; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_mb_indicators.food_19 IS $$Average percentage of food outlets within 1.6km that provide fresh food options  (ie. supermarkets, fruit and vegetable grocers, bakeries, butchers, fishmongers and delicatessens; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_mb_indicators.food_20 IS $$Average ratio of food outlets within 1.6km that provide fresh food options (ie. supermarkets, fruit and vegetable grocers, bakeries, butchers, fishmongers and delicatessens) to fast food outlets (OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_mb_indicators.food_21 IS $$Percentage of dwellings with no availability of healthy or unhealthy food within 1.6km$$;
COMMENT ON COLUMN li_2018_mb_indicators.food_22 IS $$Percentage of dwellings with no food outlets within 1.6km$$;
COMMENT ON COLUMN li_2018_mb_indicators.food_23_hard IS $$Percentage of dwellings within 1km of a supermarket$$;
COMMENT ON COLUMN li_2018_mb_indicators.food_24 IS $$Average distance to closest fresh food outlet (bakery, fruit and vegetables grocer, delicatessen, and fish, meat, poultry outlet; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.food_25 IS $$Average distance to closest healthy food outlet (supermarket or fruit and vegetables grocer; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.food_26 IS $$Average distance to closest fast food outlet (HLC, 2017; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.food_27 IS $$Average distance to closest dining establishment (cafe, restaurant, pub; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.community_01 IS $$Average distance to closest community centre (HLC, 2016; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.community_02 IS $$Average distance to closest cultural institution (museum, theatre, cinema, art gallery or art centre; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.alc_01 IS $$Average number of on-licenses within 400 m$$;
COMMENT ON COLUMN li_2018_mb_indicators.alc_02 IS $$Average number of off-licenses within 800 m$$;
COMMENT ON COLUMN li_2018_mb_indicators.alc_03 IS $$Average distance to closest bar, pub or nightclub (OSM, 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.childcare_01 IS $$Percentage of dwellings within 1600m of a children's day care which meets guidelines$$;
COMMENT ON COLUMN li_2018_mb_indicators.childcare_02 IS $$Percentage of dwellings within 1600m of a children's day care (OSHC) which meets guidelines$$;
COMMENT ON COLUMN li_2018_mb_indicators.health_01 IS $$Percentage of dwellings within 1600m of a GP$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_activity_centres IS $$Average distance to closest activity centre$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_alcohol_offlicence IS $$Average distance to closest offlicence alcohol outlet (HLC, 2017-19)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_alcohol_onlicence IS $$Average distance to closest onlicence alcohol outlet (HLC, 2017-19)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_alcohol_osm IS $$Average distance to closest alcohol outlet (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_all_schools IS $$Average distance to closest schools (all; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_art_centre_osm IS $$Average distance to closest art centre (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_art_gallery_osm IS $$Average distance to closest art gallery (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_bakery_osm IS $$Average distance to closest bakery (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_bar_osm IS $$Average distance to closest bar (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_cafe_osm IS $$Average distance to closest cafe (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_childcare_all IS $$Average distance to closest child care (all, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_childcare_all_exc IS $$Average distance to closest child care (exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_childcare_all_meet IS $$Average distance to closest child care (meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_childcare_oshc IS $$Average distance to closest child care (outside school hours, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_childcare_oshc_exc IS $$Average distance to closest child care (outside school hours exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_childcare_oshc_meet IS $$Average distance to closest child care (outside school hours meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_childcare_preschool IS $$Average distance to closest child care (pre-school, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_childcare_preschool_exc IS $$Average distance to closest child care (pre-school exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_childcare_preschool_meet IS $$Average distance to closest child care (pre-school meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_cinema_osm IS $$Average distance to closest cinema (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_community_centre_osm IS $$Average distance to closest community centre (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_convenience_osm IS $$Average distance to closest convenience store (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_deli_osm IS $$Average distance to closest deli (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_disability_employment IS $$Average distance to closest disabilty employment service $$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_fast_food IS $$Average distance to closest fast food (in house 2017)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_fastfood_osm IS $$Average distance to closest fast food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_food_court_osm IS $$Average distance to closest food court (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_food_health_osm IS $$Average distance to closest health food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_food_other_osm IS $$Average distance to closest other food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_fruit_veg_osm IS $$Average distance to closest fruit and veg (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_gtfs_2018_stop_30_mins_final IS $$Average distance to closest transport stop with frequent daytime service$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_gtfs_2018_stops IS $$Average distance to closest public transport stop$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_gtfs_2018_stops_bus IS $$Average distance to closest bus stop$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_gtfs_2018_stops_ferry IS $$Average distance to closest ferry terminal$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_gtfs_2018_stops_train IS $$Average distance to closest train station$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_gtfs_2018_stops_tram IS $$Average distance to closest tram stop$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_gtfs_20191008_20191205_bus_0015 IS $$Average distance to closest bus stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_gtfs_20191008_20191205_bus_0030 IS $$Average distance to closest bus stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_gtfs_20191008_20191205_bus_0045 IS $$Average distance to closest bus stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_gtfs_20191008_20191205_bus_any IS $$Average distance to closest bus stop$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_gtfs_20191008_20191205_ferry_0015 IS $$Average distance to closest ferry stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_gtfs_20191008_20191205_ferry_0030 IS $$Average distance to closest ferry stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_gtfs_20191008_20191205_ferry_0045 IS $$Average distance to closest ferry stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_gtfs_20191008_20191205_ferry_any IS $$Average distance to closest ferry stop$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_gtfs_20191008_20191205_revised_all IS $$Average distance to closest public transport stop$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_gtfs_20191008_20191205_revised_frequent30 IS $$Average distance to closest public transport stop with an average weekday service frequency of 30 minutes or less$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_gtfs_20191008_20191205_train_0015 IS $$Average distance to closest train stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_gtfs_20191008_20191205_train_0030 IS $$Average distance to closest train stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_gtfs_20191008_20191205_train_0045 IS $$Average distance to closest train stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_gtfs_20191008_20191205_train_any IS $$Average distance to closest train stop$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_gtfs_20191008_20191205_tram_0015 IS $$Average distance to closest tram stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_gtfs_20191008_20191205_tram_0030 IS $$Average distance to closest tram stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_gtfs_20191008_20191205_tram_0045 IS $$Average distance to closest tram stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_gtfs_20191008_20191205_tram_any IS $$Average distance to closest tram stop$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_hlc_2016_community_centres IS $$Average distance to closest community centre (2016)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_libraries IS $$Average distance to closest libraries (multiple sources, in-house, 2015-18)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_market_osm IS $$Average distance to closest market (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_meat_seafood_osm IS $$Average distance to closest meat / seafood (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_museum_osm IS $$Average distance to closest museum (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_newsagent_osm IS $$Average distance to closest newsagent (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_nhsd_2017_aged_care_residential IS $$Average distance to closest aged care residential service$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_nhsd_2017_dentist IS $$Average distance to closest dentist (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_nhsd_2017_gp IS $$Average distance to closest general practice/GP/doctor (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_nhsd_2017_hospital IS $$Average distance to closest hospital (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_nhsd_2017_mc_family_health IS $$Average distance to closest maternal, child and family health (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_nhsd_2017_other_community_health_care IS $$Average distance to closest 'other community health care' destination (not pharmacy or maternal and child health)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_nhsd_2017_pharmacy IS $$Average distance to closest pharmacy (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_P_12_Schools IS $$Average distance to closest schools (K - 12; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_P_12_Schools_catholic IS $$Average distance to closest schools (K - 12, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_P_12_Schools_gov IS $$Average distance to closest schools (K - 12, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_P_12_Schools_indep IS $$Average distance to closest schools (K - 12, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_petrolstation_osm IS $$Average distance to closest petrol station (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_pharmacy_osm IS $$Average distance to closest pharmacy (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_place_of_worship_osm IS $$Average distance to closest place of worship (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_playgrounds IS $$Average distance to closest playground (in house 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_postoffice_osm IS $$Average distance to post office (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_primary_schools IS $$Average distance to closest schools (primary; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_primary_schools_catholic IS $$Average distance to closest schools (primary, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_primary_schools_gov IS $$Average distance to closest schools (primary, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_primary_schools_indep IS $$Average distance to closest schools (primary, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_pub_osm IS $$Average distance to closest pub (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_public_swimming_pool_osm IS $$Average distance to closest public swimming pool (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_restaurant_osm IS $$Average distance to closest restaurant (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_secondary_schools IS $$Average distance to closest schools (secondary; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_secondary_schools_catholic IS $$Average distance to closest schools (secondary, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_secondary_schools_gov IS $$Average distance to closest schools (secondary, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_secondary_schools_indep IS $$Average distance to closest schools (secondary, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_special_schools IS $$Average distance to closest schools (special; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_supermarket IS $$Average distance to closest supermarket (in house 2017)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_supermarket_osm IS $$Average distance to closest supermarket (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_mb_indicators.dist_m_theatre_osm IS $$Average distance to closest theatre (OSM, October 2018)$$;
```
</details>

Display information (including size and description) for this particular table: `\dt+ li_2018_mb_indicators`
Display custom data dictionary by running `SELECT * FROM dictionary('li_2018_mb_indicators');`

### Loading the Statistical Area 1 (SA1) indicator data


#### Initialise table defining variables and their data types

<details>
  <summary>
    Click to view code
  </summary>

```sql
CREATE TABLE li_2018_sa1_indicators 
(
sa1_maincode_2016 text PRIMARY KEY,
study_region text,
dwelling int,
person int,
sample_count int,
sample_count_per_ha float,
area_ha float,
dwellings_per_ha float,
net_dwelling float,
net_area     float,
net_density  float,
uli_city float,
uli_national float,
li_community_culture_leisure float,
li_early_years float,
li_education float,
li_health_services float,
li_sport_rec float,
li_food float,
li_convenience float,
li_pt_regular_400m float,
li_public_os_large_400m float,
li_street_connectivity_1600m float,
li_dwelling_density_1600m float,
li_sa1_30_40_housing_stress float,
li_sa1_sa3_local_employment float,
walkability_city float,
walkability_national float,
daily_living_access_1600m float,
social_infrastructure_mix float,
walk_02 float,
walk_02_policy boolean,
walk_03_policy boolean,
walk_05_policy boolean,
walk_12 float,
walk_12_policy boolean,
walk_13 float,
walk_13_policy boolean,
walk_14_policy boolean,
walk_15_policy boolean,
walk_16 float,
walk_17 float,
walk_21 float,
trans_01 float,
trans_01_policy boolean,
trans_02 float,
trans_02_policy boolean,
trans_03 float,
trans_03_policy boolean,
trans_04 float,
trans_04_policy boolean,
trans_05 float,
trans_05_policy boolean,
trans_06 float,
trans_07 float,
trans_08 float,
trans_09 float,
os_public_01 float,
os_public_02 float,
os_public_03 float,
os_public_03_policy boolean,
os_public_04 float,
os_public_04_policy boolean,
os_public_05 float,
os_public_05_policy boolean,
os_public_06 float,
os_public_06_policy boolean,
os_public_07 float,
os_public_07_policy boolean,
os_public_08 float,
os_public_08_policy boolean,
os_public_09 float,
os_public_09_policy boolean,
os_public_10 float,
os_public_10_policy boolean,
os_public_11 float,
os_public_11_policy boolean,
os_public_12 float,
os_public_14 float,
os_public_15 float,
os_public_16 float,
os_public_17 float,
os_public_18 float,
os_public_19 float,
os_public_20 float,
os_public_21 float,
os_public_22 float,
os_public_23 float,
os_public_24 float,
os_public_25 float,
hous_02 float,
hous_04 float,
hous_05 float,
hous_06 float,
food_12 float,
food_13 float,
food_14 float,
food_15 float,
food_16 float,
food_17 float,
food_18 float,
food_19 float,
food_20 float,
food_21 float,
food_22 float,
food_23_hard float,
food_24 float,
food_25 float,
food_26 float,
food_27 float,
community_01 float,
community_02 float,
alc_01 float,
alc_02 float,
alc_03 float,
childcare_01 float,
childcare_02 float,
health_01 float,
dist_m_activity_centres float,
dist_m_alcohol_offlicence float,
dist_m_alcohol_onlicence float,
dist_m_alcohol_osm float,
dist_m_all_schools float,
dist_m_art_centre_osm float,
dist_m_art_gallery_osm float,
dist_m_bakery_osm float,
dist_m_bar_osm float,
dist_m_cafe_osm float,
dist_m_childcare_all float,
dist_m_childcare_all_exc float,
dist_m_childcare_all_meet float,
dist_m_childcare_oshc float,
dist_m_childcare_oshc_exc float,
dist_m_childcare_oshc_meet float,
dist_m_childcare_preschool float,
dist_m_childcare_preschool_exc float,
dist_m_childcare_preschool_meet float,
dist_m_cinema_osm float,
dist_m_community_centre_osm float,
dist_m_convenience_osm float,
dist_m_deli_osm float,
dist_m_disability_employment float,
dist_m_fast_food float,
dist_m_fastfood_osm float,
dist_m_food_court_osm float,
dist_m_food_health_osm float,
dist_m_food_other_osm float,
dist_m_fruit_veg_osm float,
dist_m_gtfs_2018_stop_30_mins_final float,
dist_m_gtfs_2018_stops float,
dist_m_gtfs_2018_stops_bus float,
dist_m_gtfs_2018_stops_ferry float,
dist_m_gtfs_2018_stops_train float,
dist_m_gtfs_2018_stops_tram float,
dist_m_gtfs_20191008_20191205_bus_0015 float,
dist_m_gtfs_20191008_20191205_bus_0030 float,
dist_m_gtfs_20191008_20191205_bus_0045 float,
dist_m_gtfs_20191008_20191205_bus_any float,
dist_m_gtfs_20191008_20191205_ferry_0015 float,
dist_m_gtfs_20191008_20191205_ferry_0030 float,
dist_m_gtfs_20191008_20191205_ferry_0045 float,
dist_m_gtfs_20191008_20191205_ferry_any float,
dist_m_gtfs_20191008_20191205_revised_all float,
dist_m_gtfs_20191008_20191205_revised_frequent30 float,
dist_m_gtfs_20191008_20191205_train_0015 float,
dist_m_gtfs_20191008_20191205_train_0030 float,
dist_m_gtfs_20191008_20191205_train_0045 float,
dist_m_gtfs_20191008_20191205_train_any float,
dist_m_gtfs_20191008_20191205_tram_0015 float,
dist_m_gtfs_20191008_20191205_tram_0030 float,
dist_m_gtfs_20191008_20191205_tram_0045 float,
dist_m_gtfs_20191008_20191205_tram_any float,
dist_m_hlc_2016_community_centres float,
dist_m_libraries float,
dist_m_market_osm float,
dist_m_meat_seafood_osm float,
dist_m_museum_osm float,
dist_m_newsagent_osm float,
dist_m_nhsd_2017_aged_care_residential float,
dist_m_nhsd_2017_dentist float,
dist_m_nhsd_2017_gp float,
dist_m_nhsd_2017_hospital float,
dist_m_nhsd_2017_mc_family_health float,
dist_m_nhsd_2017_other_community_health_care float,
dist_m_nhsd_2017_pharmacy float,
dist_m_P_12_Schools float,
dist_m_P_12_Schools_catholic float,
dist_m_P_12_Schools_gov float,
dist_m_P_12_Schools_indep float,
dist_m_petrolstation_osm float,
dist_m_pharmacy_osm float,
dist_m_place_of_worship_osm float,
dist_m_playgrounds float,
dist_m_postoffice_osm float,
dist_m_primary_schools float,
dist_m_primary_schools_catholic float,
dist_m_primary_schools_gov float,
dist_m_primary_schools_indep float,
dist_m_pub_osm float,
dist_m_public_swimming_pool_osm float,
dist_m_restaurant_osm float,
dist_m_secondary_schools float,
dist_m_secondary_schools_catholic float,
dist_m_secondary_schools_gov float,
dist_m_secondary_schools_indep float,
dist_m_special_schools float,
dist_m_supermarket float,
dist_m_supermarket_osm float,
dist_m_theatre_osm float
);
```
</details>

### Copy the data from CSV
```sql
COPY li_2018_sa1_indicators FROM 'D:/projects/ntnl_li_2018/data/National Liveability 2018 - Final Outputs/For dissemination/hlc_ntnl_liveability_2018_sa1_2016.csv' WITH DELIMITER ',' CSV HEADER;
```

#### Optionally describe the data
<details>
  <summary>
    Click to view code
  </summary>

```sql
COMMENT ON TABLE li_2018_sa1_indicators IS $$Liveability indicators for dwellings, aggregated for Statistical Areas Level 1 (SA1)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.sa1_maincode_2016 IS $$Statistical Area 1 (SA1) maincode identifier$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dwelling IS $$Dwelling count (Mesh Block dwelling count > 0 was an inclusion criteria for sampling)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.person IS $$Person count (persons usually resident)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.sample_count IS $$address points in area$$;
COMMENT ON COLUMN li_2018_sa1_indicators.sample_count_per_ha IS $$address point density per hectare$$;
COMMENT ON COLUMN li_2018_sa1_indicators.area_ha IS $$Area in hectares$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dwellings_per_ha IS $$gross dwelling density$$;
COMMENT ON COLUMN li_2018_sa1_indicators.net_dwelling IS $$net dwelling density (ie. for areas classified as residential at Mesh Block level)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.net_area IS $$net area (ie. for areas classified as residential at Mesh Block level)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.net_density IS $$net density (ie. for areas classified as residential at Mesh Block level)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.uli_city IS $$Average Urban Liveability Index, relative to locations within this city$$;
COMMENT ON COLUMN li_2018_sa1_indicators.uli_national IS $$Average Urban Liveability Index, relative to locations across Australia's 21 largest cities$$;
COMMENT ON COLUMN li_2018_sa1_indicators.li_community_culture_leisure IS $$Average score for access to community, culture and leisure destinations (community centre and library within 1000m, and museum/art gallery and cinema/theater within 3200m) (/1)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.li_early_years IS $$Average score for access to child care (any meeting ACECQA recommendations) within 800 metres and childcare (outside school hours meeting recommendations) within 1600 metres (/1)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.li_education IS $$Average score for access to primary and secondary public schools within 1600 metres (/1)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.li_health_services IS $$Average score for access to health services (GP, pharmacy, maternal, child and family health care, aged care facility and other community health care) within 1000 metres (/1)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.li_sport_rec IS $$Average score for access to an area of open space with sport/recreation facilities within 1000 metres, and a public swimming pool within 1200 metres (/1)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.li_food IS $$Average score for access to a supermarket and fresh fruit and vegetables within 1000 metres, and meat/seafood within 3200 metres (/1)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.li_convenience IS $$Average score for access to convenience destinations (convenience store and petrol station within 1000 metres, and a newsagent within 3200 metres) (/1)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.li_pt_regular_400m IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 30 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_sa1_indicators.li_public_os_large_400m IS $$Percentage of dwellings < 400 m of public open space > 1.5 ha$$;
COMMENT ON COLUMN li_2018_sa1_indicators.li_street_connectivity_1600m IS $$Average local street connectivity per square kilometre$$;
COMMENT ON COLUMN li_2018_sa1_indicators.li_dwelling_density_1600m IS $$Average local dwelling density per hectare (Ha) $$;
COMMENT ON COLUMN li_2018_sa1_indicators.li_sa1_30_40_housing_stress IS $$Percentage of SA1 households with income in the bottom 40% of the income distribution spending more than 30% of household income on housing costs$$;
COMMENT ON COLUMN li_2018_sa1_indicators.li_sa1_sa3_local_employment IS $$Percentage of employed persons who live and work in the same community$$;
COMMENT ON COLUMN li_2018_sa1_indicators.walkability_city IS $$Average walkability index, combining street connectivity, dwelling density and daily living destinations, relative to locations within this city$$;
COMMENT ON COLUMN li_2018_sa1_indicators.walkability_national IS $$Average walkability index, combining street connectivity, dwelling density and daily living destinations, relative to locations across Australia's 21 largest cities$$;
COMMENT ON COLUMN li_2018_sa1_indicators.daily_living_access_1600m IS $$Average number of daily living types present, measured as a score of 0-3, with 1 point for each category of convenience store/petrol station/newsagent, PT stop, supermarket within 1600m network distance$$;
COMMENT ON COLUMN li_2018_sa1_indicators.social_infrastructure_mix IS $$Average social infrastructure mix score (/16)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.walk_02 IS $$Percentage of dwellings <1 km walking distance of an activity centre with a supermarket$$;
COMMENT ON COLUMN li_2018_sa1_indicators.walk_02_policy IS $$At least 80% of dwellings are within 1 km walking distance of an activity centre with a supermarket$$;
COMMENT ON COLUMN li_2018_sa1_indicators.walk_03_policy IS $$Area has at least 15 dwellings per net developable hectare$$;
COMMENT ON COLUMN li_2018_sa1_indicators.walk_05_policy IS $$Area has at least 26 dwellings per net developable hectare$$;
COMMENT ON COLUMN li_2018_sa1_indicators.walk_12 IS $$Percentage of dwellings with local dwelling density of 15 dwellings per hectare or greater$$;
COMMENT ON COLUMN li_2018_sa1_indicators.walk_12_policy IS $$15 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_sa1_indicators.walk_13 IS $$Percentage of dwellings with local dwelling density of 30 dwellings per hectare or greater$$;
COMMENT ON COLUMN li_2018_sa1_indicators.walk_13_policy IS $$Local dwelling density of 30 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_sa1_indicators.walk_14_policy IS $$Gross dwelling density of 15 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_sa1_indicators.walk_15_policy IS $$Gross dwelling density of 30 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_sa1_indicators.walk_16 IS $$Average distance to closest activity centre (proxy measure: supermarket within a commercial zoned Mesh Block)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.walk_17 IS $$Average pedshed ratio, defined as the area of the 400 m pedestrian network from each residential dwelling buffered by 50m divided by the radial 400 m "crow flies" area (i.e. 50.2 Ha.)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.walk_21 IS $$Average number of local living types present (see paper of Mavoa et al)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.trans_01 IS $$Percentage of dwellings with access to bus stop within 400 m, a tram stop within 600m, or a train station within 800 m$$;
COMMENT ON COLUMN li_2018_sa1_indicators.trans_01_policy IS $$95% or more of dwellings with access to bus stop within 400 m, a tram stop within 600m, or a train station within 800 m$$;
COMMENT ON COLUMN li_2018_sa1_indicators.trans_02 IS $$Percentage of dwellings with access to bus stop < 400 m$$;
COMMENT ON COLUMN li_2018_sa1_indicators.trans_02_policy IS $$95% or more of dwellings with access to bus stop < 400 m$$;
COMMENT ON COLUMN li_2018_sa1_indicators.trans_03 IS $$Percentage of dwellings < 400m walk from a neighbourhood or town centre, or a bus stop, or in a 800m walk from a railway station.$$;
COMMENT ON COLUMN li_2018_sa1_indicators.trans_03_policy IS $$60% or more of dwellings < 400m walk from a neighbourhood or town centre, or a bus stop, or in a 800m walk from a railway station.$$;
COMMENT ON COLUMN li_2018_sa1_indicators.trans_04 IS $$Percentage of dwellings < 400 metres of an existing or planned public transport stop$$;
COMMENT ON COLUMN li_2018_sa1_indicators.trans_04_policy IS $$100% of dwellings < 400 metres of an existing or planned public transport stop$$;
COMMENT ON COLUMN li_2018_sa1_indicators.trans_05 IS $$Percentage of dwellings < 400 m of a bus stop every 30 min OR < 800 m of a train station every 15 min$$;
COMMENT ON COLUMN li_2018_sa1_indicators.trans_05_policy IS $$100% of dwellings < 400 m of a bus stop every 30 min OR < 800 m of a train station every 15 min$$;
COMMENT ON COLUMN li_2018_sa1_indicators.trans_06 IS $$Percentage of dwellings < 400 m of a public transport stop with a scheduled service at least every 30 minutes between 7am and 7pm on a normal weekday (= a combined measure of proximity and frequency)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.trans_07 IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 30 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_sa1_indicators.trans_08 IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 25 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_sa1_indicators.trans_09 IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 20 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_01 IS $$Percentage of dwellings within 400 m or less distance of public open space$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_02 IS $$Percentage of dwellings < 400 m of public open space > 1.5 ha$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_03 IS $$Percentage of dwellings within 400 m or less distance of public open space$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_03_policy IS $$95% or more of dwellings within 400 m or less distance of public open space$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_04 IS $$Percentage of dwellings within 300 m or less distance of any public open space$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_04_policy IS $$100% of dwellings within 300 m or less distance of any public open space$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_05 IS $$Percentage of dwellings within 400 m or less distance of any local park (> 0.4 to <=1 ha)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_05_policy IS $$50% or more of dwellings within 400 m or less distance of any local park (> 0.4 to <=1 ha)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_06 IS $$Percentage of dwellings within 800 m or less distance of any neighbourhood park (>1 ha to <= 5ha)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_06_policy IS $$50% or more of dwellings within 800 m or less distance of any neighbourhood park (>1 ha to <= 5ha)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_07 IS $$Percentage of dwellings within 2 km or less of any district park (>5 ha to <=20 ha)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_07_policy IS $$50% or more of dwellings within 2 km or less of any district park (>5 ha to <=20 ha)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_08 IS $$Percentage of dwellings within 400 m or less distance of a neighbourhood recreation park (>0.5 ha)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_08_policy IS $$90% or more of dwellings within 400 m or less distance of a neighbourhood recreation park (>0.5 ha)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_09 IS $$Percentage of dwellings within 2.5 km or less distance of a district recreation park (>5 ha)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_09_policy IS $$90% or more of dwellings within 2.5 km or less distance of a district recreation park (>5 ha)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_10 IS $$Percentage of dwellings within 400 m or less distance of a park larger than 0.5 Ha$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_10_policy IS $$50% or more of dwellings within 400 m or less distance of a park larger than 0.5 Ha$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_11 IS $$Percentage of dwellings within 2 km or less distance of a park larger than 2 Ha$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_11_policy IS $$50% or more of dwellings within 2 km or less distance of a park larger than 2 Ha$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_12 IS $$Average distance to closest POS with a public toilet within 100 metres$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_14 IS $$Average distance to closest public open space (OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_15 IS $$Average distance to closest public open space <=0.4 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_16 IS $$Average distance to closest public open space >0.4 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_17 IS $$Average distance to closest public open space >0.5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_18 IS $$Average distance to closest public open space >1.5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_19 IS $$Average distance to closest public open space >2 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_20 IS $$Average distance to closest public open space >0.4 to <=1 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_21 IS $$Average distance to closest public open space >1 to <= 5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_22 IS $$Average distance to closest public open space >5 Ha to <=20 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_23 IS $$Average distance to closest public open space >5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_24 IS $$Average distance to closest public open space >20 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa1_indicators.os_public_25 IS $$Average distance to closest public open space with a sport facility (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa1_indicators.hous_02 IS $$Percentage of dwellings renting as a proportion of total$$;
COMMENT ON COLUMN li_2018_sa1_indicators.hous_04 IS $$Percentage of employed persons aged 15 and over using active transport to travel to work$$;
COMMENT ON COLUMN li_2018_sa1_indicators.hous_05 IS $$Percentage of employed persons aged 15 and over using public transport to travel to work$$;
COMMENT ON COLUMN li_2018_sa1_indicators.hous_06 IS $$Percentage of employed persons aged 15 and over using private vehicle/s to travel to work$$;
COMMENT ON COLUMN li_2018_sa1_indicators.food_12 IS $$Average count of supermarkets within 1.6km$$;
COMMENT ON COLUMN li_2018_sa1_indicators.food_13 IS $$Average count of fruit and vegetable grocers within 1.6km$$;
COMMENT ON COLUMN li_2018_sa1_indicators.food_14 IS $$Average count of specialty food stores (bakeries, butchers, fishmongers and delicatessens) within 1.6km$$;
COMMENT ON COLUMN li_2018_sa1_indicators.food_15 IS $$Average count of healther food outlets (supermarkets and fruit and vegetable grocers) within 1.6 km (OSM, or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.food_16 IS $$Average count of fast food outlets within 1.6km (OSM, or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.food_17 IS $$Average percentage of food outlets within 1.6km that provide healthier food options (ie. supermarkets and fruit and vegetable grocers; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.food_18 IS $$Average ratio of food outlets within 1.6km that provide healthier food options (ie. supermarkets and fruit and vegetable grocers) to fast food outlets; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.food_19 IS $$Average percentage of food outlets within 1.6km that provide fresh food options  (ie. supermarkets, fruit and vegetable grocers, bakeries, butchers, fishmongers and delicatessens; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.food_20 IS $$Average ratio of food outlets within 1.6km that provide fresh food options (ie. supermarkets, fruit and vegetable grocers, bakeries, butchers, fishmongers and delicatessens) to fast food outlets (OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.food_21 IS $$Percentage of dwellings with no availability of healthy or unhealthy food within 1.6km$$;
COMMENT ON COLUMN li_2018_sa1_indicators.food_22 IS $$Percentage of dwellings with no food outlets within 1.6km$$;
COMMENT ON COLUMN li_2018_sa1_indicators.food_23_hard IS $$Percentage of dwellings within 1km of a supermarket$$;
COMMENT ON COLUMN li_2018_sa1_indicators.food_24 IS $$Average distance to closest fresh food outlet (bakery, fruit and vegetables grocer, delicatessen, and fish, meat, poultry outlet; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.food_25 IS $$Average distance to closest healthy food outlet (supermarket or fruit and vegetables grocer; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.food_26 IS $$Average distance to closest fast food outlet (HLC, 2017; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.food_27 IS $$Average distance to closest dining establishment (cafe, restaurant, pub; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.community_01 IS $$Average distance to closest community centre (HLC, 2016; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.community_02 IS $$Average distance to closest cultural institution (museum, theatre, cinema, art gallery or art centre; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.alc_01 IS $$Average number of on-licenses within 400 m$$;
COMMENT ON COLUMN li_2018_sa1_indicators.alc_02 IS $$Average number of off-licenses within 800 m$$;
COMMENT ON COLUMN li_2018_sa1_indicators.alc_03 IS $$Average distance to closest bar, pub or nightclub (OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.childcare_01 IS $$Percentage of dwellings within 1600m of a children's day care which meets guidelines$$;
COMMENT ON COLUMN li_2018_sa1_indicators.childcare_02 IS $$Percentage of dwellings within 1600m of a children's day care (OSHC) which meets guidelines$$;
COMMENT ON COLUMN li_2018_sa1_indicators.health_01 IS $$Percentage of dwellings within 1600m of a GP$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_activity_centres IS $$Average distance to closest activity centre$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_alcohol_offlicence IS $$Average distance to closest offlicence alcohol outlet (HLC, 2017-19)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_alcohol_onlicence IS $$Average distance to closest onlicence alcohol outlet (HLC, 2017-19)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_alcohol_osm IS $$Average distance to closest alcohol outlet (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_all_schools IS $$Average distance to closest schools (all; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_art_centre_osm IS $$Average distance to closest art centre (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_art_gallery_osm IS $$Average distance to closest art gallery (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_bakery_osm IS $$Average distance to closest bakery (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_bar_osm IS $$Average distance to closest bar (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_cafe_osm IS $$Average distance to closest cafe (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_childcare_all IS $$Average distance to closest child care (all, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_childcare_all_exc IS $$Average distance to closest child care (exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_childcare_all_meet IS $$Average distance to closest child care (meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_childcare_oshc IS $$Average distance to closest child care (outside school hours, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_childcare_oshc_exc IS $$Average distance to closest child care (outside school hours exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_childcare_oshc_meet IS $$Average distance to closest child care (outside school hours meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_childcare_preschool IS $$Average distance to closest child care (pre-school, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_childcare_preschool_exc IS $$Average distance to closest child care (pre-school exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_childcare_preschool_meet IS $$Average distance to closest child care (pre-school meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_cinema_osm IS $$Average distance to closest cinema (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_community_centre_osm IS $$Average distance to closest community centre (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_convenience_osm IS $$Average distance to closest convenience store (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_deli_osm IS $$Average distance to closest deli (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_disability_employment IS $$Average distance to closest disabilty employment service $$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_fast_food IS $$Average distance to closest fast food (in house 2017)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_fastfood_osm IS $$Average distance to closest fast food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_food_court_osm IS $$Average distance to closest food court (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_food_health_osm IS $$Average distance to closest health food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_food_other_osm IS $$Average distance to closest other food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_fruit_veg_osm IS $$Average distance to closest fruit and veg (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_gtfs_2018_stop_30_mins_final IS $$Average distance to closest transport stop with frequent daytime service$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_gtfs_2018_stops IS $$Average distance to closest public transport stop$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_gtfs_2018_stops_bus IS $$Average distance to closest bus stop$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_gtfs_2018_stops_ferry IS $$Average distance to closest ferry terminal$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_gtfs_2018_stops_train IS $$Average distance to closest train station$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_gtfs_2018_stops_tram IS $$Average distance to closest tram stop$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_gtfs_20191008_20191205_bus_0015 IS $$Average distance to closest bus stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_gtfs_20191008_20191205_bus_0030 IS $$Average distance to closest bus stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_gtfs_20191008_20191205_bus_0045 IS $$Average distance to closest bus stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_gtfs_20191008_20191205_bus_any IS $$Average distance to closest bus stop$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_gtfs_20191008_20191205_ferry_0015 IS $$Average distance to closest ferry stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_gtfs_20191008_20191205_ferry_0030 IS $$Average distance to closest ferry stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_gtfs_20191008_20191205_ferry_0045 IS $$Average distance to closest ferry stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_gtfs_20191008_20191205_ferry_any IS $$Average distance to closest ferry stop$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_gtfs_20191008_20191205_revised_all IS $$Average distance to closest public transport stop$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_gtfs_20191008_20191205_revised_frequent30 IS $$Average distance to closest public transport stop with an average weekday service frequency of 30 minutes or less$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_gtfs_20191008_20191205_train_0015 IS $$Average distance to closest train stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_gtfs_20191008_20191205_train_0030 IS $$Average distance to closest train stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_gtfs_20191008_20191205_train_0045 IS $$Average distance to closest train stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_gtfs_20191008_20191205_train_any IS $$Average distance to closest train stop$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_gtfs_20191008_20191205_tram_0015 IS $$Average distance to closest tram stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_gtfs_20191008_20191205_tram_0030 IS $$Average distance to closest tram stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_gtfs_20191008_20191205_tram_0045 IS $$Average distance to closest tram stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_gtfs_20191008_20191205_tram_any IS $$Average distance to closest tram stop$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_hlc_2016_community_centres IS $$Average distance to closest community centre (2016)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_libraries IS $$Average distance to closest libraries (multiple sources, in-house, 2015-18)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_market_osm IS $$Average distance to closest market (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_meat_seafood_osm IS $$Average distance to closest meat / seafood (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_museum_osm IS $$Average distance to closest museum (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_newsagent_osm IS $$Average distance to closest newsagent (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_nhsd_2017_aged_care_residential IS $$Average distance to closest aged care residential service$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_nhsd_2017_dentist IS $$Average distance to closest dentist (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_nhsd_2017_gp IS $$Average distance to closest general practice/GP/doctor (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_nhsd_2017_hospital IS $$Average distance to closest hospital (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_nhsd_2017_mc_family_health IS $$Average distance to closest maternal, child and family health (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_nhsd_2017_other_community_health_care IS $$Average distance to closest 'other community health care' destination (not pharmacy or maternal and child health)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_nhsd_2017_pharmacy IS $$Average distance to closest pharmacy (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_P_12_Schools IS $$Average distance to closest schools (K - 12; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_P_12_Schools_catholic IS $$Average distance to closest schools (K - 12, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_P_12_Schools_gov IS $$Average distance to closest schools (K - 12, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_P_12_Schools_indep IS $$Average distance to closest schools (K - 12, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_petrolstation_osm IS $$Average distance to closest petrol station (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_pharmacy_osm IS $$Average distance to closest pharmacy (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_place_of_worship_osm IS $$Average distance to closest place of worship (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_playgrounds IS $$Average distance to closest playground (in house 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_postoffice_osm IS $$Average distance to post office (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_primary_schools IS $$Average distance to closest schools (primary; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_primary_schools_catholic IS $$Average distance to closest schools (primary, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_primary_schools_gov IS $$Average distance to closest schools (primary, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_primary_schools_indep IS $$Average distance to closest schools (primary, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_pub_osm IS $$Average distance to closest pub (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_public_swimming_pool_osm IS $$Average distance to closest public swimming pool (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_restaurant_osm IS $$Average distance to closest restaurant (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_secondary_schools IS $$Average distance to closest schools (secondary; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_secondary_schools_catholic IS $$Average distance to closest schools (secondary, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_secondary_schools_gov IS $$Average distance to closest schools (secondary, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_secondary_schools_indep IS $$Average distance to closest schools (secondary, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_special_schools IS $$Average distance to closest schools (special; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_supermarket IS $$Average distance to closest supermarket (in house 2017)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_supermarket_osm IS $$Average distance to closest supermarket (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa1_indicators.dist_m_theatre_osm IS $$Average distance to closest theatre (OSM, October 2018)$$;
```
</details>

Display information (including size and description) for this particular table: `\dt+ li_2018_sa1_indicators`
Display custom data dictionary by running `SELECT * FROM dictionary('li_2018_sa1_indicators');`


### Loading the Statistical Area 2 (SA2) indicator data

#### Initialise SA2 indicators table, defining variables and their data types


<details>
  <summary>
    Click to view code
  </summary>

```sql
CREATE TABLE li_2018_sa2_indicators 
(
sa2_name_2016 text PRIMARY KEY,
study_region text,
dwelling int,
person int,
sample_count int,
sample_count_per_ha float,
area_ha float,
dwellings_per_ha float,
net_dwelling float,
net_area     float,
net_density  float,
uli_city float,
uli_national float,
li_community_culture_leisure float,
li_early_years float,
li_education float,
li_health_services float,
li_sport_rec float,
li_food float,
li_convenience float,
li_pt_regular_400m float,
li_public_os_large_400m float,
li_street_connectivity_1600m float,
li_dwelling_density_1600m float,
li_sa1_30_40_housing_stress float,
li_sa1_sa3_local_employment float,
walkability_city float,
walkability_national float,
daily_living_access_1600m float,
social_infrastructure_mix float,
walk_02 float,
walk_02_policy boolean,
walk_03_policy boolean,
walk_05_policy boolean,
walk_12 float,
walk_12_policy boolean,
walk_13 float,
walk_13_policy boolean,
walk_14_policy boolean,
walk_15_policy boolean,
walk_16 float,
walk_17 float,
walk_21 float,
trans_01 float,
trans_01_policy boolean,
trans_02 float,
trans_02_policy boolean,
trans_03 float,
trans_03_policy boolean,
trans_04 float,
trans_04_policy boolean,
trans_05 float,
trans_05_policy boolean,
trans_06 float,
trans_07 float,
trans_08 float,
trans_09 float,
os_public_01 float,
os_public_02 float,
os_public_03 float,
os_public_03_policy boolean,
os_public_04 float,
os_public_04_policy boolean,
os_public_05 float,
os_public_05_policy boolean,
os_public_06 float,
os_public_06_policy boolean,
os_public_07 float,
os_public_07_policy boolean,
os_public_08 float,
os_public_08_policy boolean,
os_public_09 float,
os_public_09_policy boolean,
os_public_10 float,
os_public_10_policy boolean,
os_public_11 float,
os_public_11_policy boolean,
os_public_12 float,
os_public_14 float,
os_public_15 float,
os_public_16 float,
os_public_17 float,
os_public_18 float,
os_public_19 float,
os_public_20 float,
os_public_21 float,
os_public_22 float,
os_public_23 float,
os_public_24 float,
os_public_25 float,
hous_02 float,
hous_04 float,
hous_05 float,
hous_06 float,
food_12 float,
food_13 float,
food_14 float,
food_15 float,
food_16 float,
food_17 float,
food_18 float,
food_19 float,
food_20 float,
food_21 float,
food_22 float,
food_23_hard float,
food_24 float,
food_25 float,
food_26 float,
food_27 float,
community_01 float,
community_02 float,
alc_01 float,
alc_02 float,
alc_03 float,
childcare_01 float,
childcare_02 float,
health_01 float,
dist_m_activity_centres float,
dist_m_alcohol_offlicence float,
dist_m_alcohol_onlicence float,
dist_m_alcohol_osm float,
dist_m_all_schools float,
dist_m_art_centre_osm float,
dist_m_art_gallery_osm float,
dist_m_bakery_osm float,
dist_m_bar_osm float,
dist_m_cafe_osm float,
dist_m_childcare_all float,
dist_m_childcare_all_exc float,
dist_m_childcare_all_meet float,
dist_m_childcare_oshc float,
dist_m_childcare_oshc_exc float,
dist_m_childcare_oshc_meet float,
dist_m_childcare_preschool float,
dist_m_childcare_preschool_exc float,
dist_m_childcare_preschool_meet float,
dist_m_cinema_osm float,
dist_m_community_centre_osm float,
dist_m_convenience_osm float,
dist_m_deli_osm float,
dist_m_disability_employment float,
dist_m_fast_food float,
dist_m_fastfood_osm float,
dist_m_food_court_osm float,
dist_m_food_health_osm float,
dist_m_food_other_osm float,
dist_m_fruit_veg_osm float,
dist_m_gtfs_2018_stop_30_mins_final float,
dist_m_gtfs_2018_stops float,
dist_m_gtfs_2018_stops_bus float,
dist_m_gtfs_2018_stops_ferry float,
dist_m_gtfs_2018_stops_train float,
dist_m_gtfs_2018_stops_tram float,
dist_m_gtfs_20191008_20191205_bus_0015 float,
dist_m_gtfs_20191008_20191205_bus_0030 float,
dist_m_gtfs_20191008_20191205_bus_0045 float,
dist_m_gtfs_20191008_20191205_bus_any float,
dist_m_gtfs_20191008_20191205_ferry_0015 float,
dist_m_gtfs_20191008_20191205_ferry_0030 float,
dist_m_gtfs_20191008_20191205_ferry_0045 float,
dist_m_gtfs_20191008_20191205_ferry_any float,
dist_m_gtfs_20191008_20191205_revised_all float,
dist_m_gtfs_20191008_20191205_revised_frequent30 float,
dist_m_gtfs_20191008_20191205_train_0015 float,
dist_m_gtfs_20191008_20191205_train_0030 float,
dist_m_gtfs_20191008_20191205_train_0045 float,
dist_m_gtfs_20191008_20191205_train_any float,
dist_m_gtfs_20191008_20191205_tram_0015 float,
dist_m_gtfs_20191008_20191205_tram_0030 float,
dist_m_gtfs_20191008_20191205_tram_0045 float,
dist_m_gtfs_20191008_20191205_tram_any float,
dist_m_hlc_2016_community_centres float,
dist_m_libraries float,
dist_m_market_osm float,
dist_m_meat_seafood_osm float,
dist_m_museum_osm float,
dist_m_newsagent_osm float,
dist_m_nhsd_2017_aged_care_residential float,
dist_m_nhsd_2017_dentist float,
dist_m_nhsd_2017_gp float,
dist_m_nhsd_2017_hospital float,
dist_m_nhsd_2017_mc_family_health float,
dist_m_nhsd_2017_other_community_health_care float,
dist_m_nhsd_2017_pharmacy float,
dist_m_P_12_Schools float,
dist_m_P_12_Schools_catholic float,
dist_m_P_12_Schools_gov float,
dist_m_P_12_Schools_indep float,
dist_m_petrolstation_osm float,
dist_m_pharmacy_osm float,
dist_m_place_of_worship_osm float,
dist_m_playgrounds float,
dist_m_postoffice_osm float,
dist_m_primary_schools float,
dist_m_primary_schools_catholic float,
dist_m_primary_schools_gov float,
dist_m_primary_schools_indep float,
dist_m_pub_osm float,
dist_m_public_swimming_pool_osm float,
dist_m_restaurant_osm float,
dist_m_secondary_schools float,
dist_m_secondary_schools_catholic float,
dist_m_secondary_schools_gov float,
dist_m_secondary_schools_indep float,
dist_m_special_schools float,
dist_m_supermarket float,
dist_m_supermarket_osm float,
dist_m_theatre_osm float
);
```
</details>

### Copy the data from CSV
```sql
COPY li_2018_sa2_indicators FROM 'D:/projects/ntnl_li_2018/data/National Liveability 2018 - Final Outputs/For dissemination/hlc_ntnl_liveability_2018_sa2_2016.csv' WITH DELIMITER ',' CSV HEADER;
```

#### Optionally describe the data
<details>
  <summary>
    Click to view code
  </summary>

```sql
COMMENT ON TABLE li_2018_sa2_indicators IS $$Liveability indicators for dwellings, aggregated for Statistical Areas Level 2 (SA2)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.sa2_name_2016 IS $$SA2 name$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dwelling IS $$Dwelling count (Mesh Block dwelling count > 0 was an inclusion criteria for sampling)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.person IS $$Person count (persons usually resident)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.sample_count IS $$address points in area$$;
COMMENT ON COLUMN li_2018_sa2_indicators.sample_count_per_ha IS $$address point density per hectare$$;
COMMENT ON COLUMN li_2018_sa2_indicators.area_ha IS $$Area in hectares$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dwellings_per_ha IS $$gross dwelling density$$;
COMMENT ON COLUMN li_2018_sa2_indicators.net_dwelling IS $$net dwelling density (ie. for areas classified as residential at Mesh Block level)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.net_area IS $$net area (ie. for areas classified as residential at Mesh Block level)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.net_density IS $$net density (ie. for areas classified as residential at Mesh Block level)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.uli_city IS $$Average Urban Liveability Index, relative to locations within this city$$;
COMMENT ON COLUMN li_2018_sa2_indicators.uli_national IS $$Average Urban Liveability Index, relative to locations across Australia's 21 largest cities$$;
COMMENT ON COLUMN li_2018_sa2_indicators.li_community_culture_leisure IS $$Average score for access to community, culture and leisure destinations (community centre and library within 1000m, and museum/art gallery and cinema/theater within 3200m) (/1)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.li_early_years IS $$Average score for access to child care (any meeting ACECQA recommendations) within 800 metres and childcare (outside school hours meeting recommendations) within 1600 metres (/1)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.li_education IS $$Average score for access to primary and secondary public schools within 1600 metres (/1)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.li_health_services IS $$Average score for access to health services (GP, pharmacy, maternal, child and family health care, aged care facility and other community health care) within 1000 metres (/1)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.li_sport_rec IS $$Average score for access to an area of open space with sport/recreation facilities within 1000 metres, and a public swimming pool within 1200 metres (/1)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.li_food IS $$Average score for access to a supermarket and fresh fruit and vegetables within 1000 metres, and meat/seafood within 3200 metres (/1)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.li_convenience IS $$Average score for access to convenience destinations (convenience store and petrol station within 1000 metres, and a newsagent within 3200 metres) (/1)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.li_pt_regular_400m IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 30 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_sa2_indicators.li_public_os_large_400m IS $$Percentage of dwellings < 400 m of public open space > 1.5 ha$$;
COMMENT ON COLUMN li_2018_sa2_indicators.li_street_connectivity_1600m IS $$Average local street connectivity per square kilometre$$;
COMMENT ON COLUMN li_2018_sa2_indicators.li_dwelling_density_1600m IS $$Average local dwelling density per hectare (Ha) $$;
COMMENT ON COLUMN li_2018_sa2_indicators.li_sa1_30_40_housing_stress IS $$Percentage of SA1 households with income in the bottom 40% of the income distribution spending more than 30% of household income on housing costs$$;
COMMENT ON COLUMN li_2018_sa2_indicators.li_sa1_sa3_local_employment IS $$Percentage of employed persons who live and work in the same community$$;
COMMENT ON COLUMN li_2018_sa2_indicators.walkability_city IS $$Average walkability index, combining street connectivity, dwelling density and daily living destinations, relative to locations within this city$$;
COMMENT ON COLUMN li_2018_sa2_indicators.walkability_national IS $$Average walkability index, combining street connectivity, dwelling density and daily living destinations, relative to locations across Australia's 21 largest cities$$;
COMMENT ON COLUMN li_2018_sa2_indicators.daily_living_access_1600m IS $$Average number of daily living types present, measured as a score of 0-3, with 1 point for each category of convenience store/petrol station/newsagent, PT stop, supermarket within 1600m network distance$$;
COMMENT ON COLUMN li_2018_sa2_indicators.social_infrastructure_mix IS $$Average social infrastructure mix score (/16)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.walk_02 IS $$Percentage of dwellings <1 km walking distance of an activity centre with a supermarket$$;
COMMENT ON COLUMN li_2018_sa2_indicators.walk_02_policy IS $$At least 80% of dwellings are within 1 km walking distance of an activity centre with a supermarket$$;
COMMENT ON COLUMN li_2018_sa2_indicators.walk_03_policy IS $$Area has at least 15 dwellings per net developable hectare$$;
COMMENT ON COLUMN li_2018_sa2_indicators.walk_05_policy IS $$Area has at least 26 dwellings per net developable hectare$$;
COMMENT ON COLUMN li_2018_sa2_indicators.walk_12 IS $$Percentage of dwellings with local dwelling density of 15 dwellings per hectare or greater$$;
COMMENT ON COLUMN li_2018_sa2_indicators.walk_12_policy IS $$15 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_sa2_indicators.walk_13 IS $$Percentage of dwellings with local dwelling density of 30 dwellings per hectare or greater$$;
COMMENT ON COLUMN li_2018_sa2_indicators.walk_13_policy IS $$Local dwelling density of 30 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_sa2_indicators.walk_14_policy IS $$Gross dwelling density of 15 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_sa2_indicators.walk_15_policy IS $$Gross dwelling density of 30 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_sa2_indicators.walk_16 IS $$Average distance to closest activity centre (proxy measure: supermarket within a commercial zoned Mesh Block)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.walk_17 IS $$Average pedshed ratio, defined as the area of the 400 m pedestrian network from each residential dwelling buffered by 50m divided by the radial 400 m "crow flies" area (i.e. 50.2 Ha.)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.walk_21 IS $$Average number of local living types present (see paper of Mavoa et al)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.trans_01 IS $$Percentage of dwellings with access to bus stop within 400 m, a tram stop within 600m, or a train station within 800 m$$;
COMMENT ON COLUMN li_2018_sa2_indicators.trans_01_policy IS $$95% or more of dwellings with access to bus stop within 400 m, a tram stop within 600m, or a train station within 800 m$$;
COMMENT ON COLUMN li_2018_sa2_indicators.trans_02 IS $$Percentage of dwellings with access to bus stop < 400 m$$;
COMMENT ON COLUMN li_2018_sa2_indicators.trans_02_policy IS $$95% or more of dwellings with access to bus stop < 400 m$$;
COMMENT ON COLUMN li_2018_sa2_indicators.trans_03 IS $$Percentage of dwellings < 400m walk from a neighbourhood or town centre, or a bus stop, or in a 800m walk from a railway station.$$;
COMMENT ON COLUMN li_2018_sa2_indicators.trans_03_policy IS $$60% or more of dwellings < 400m walk from a neighbourhood or town centre, or a bus stop, or in a 800m walk from a railway station.$$;
COMMENT ON COLUMN li_2018_sa2_indicators.trans_04 IS $$Percentage of dwellings < 400 metres of an existing or planned public transport stop$$;
COMMENT ON COLUMN li_2018_sa2_indicators.trans_04_policy IS $$100% of dwellings < 400 metres of an existing or planned public transport stop$$;
COMMENT ON COLUMN li_2018_sa2_indicators.trans_05 IS $$Percentage of dwellings < 400 m of a bus stop every 30 min OR < 800 m of a train station every 15 min$$;
COMMENT ON COLUMN li_2018_sa2_indicators.trans_05_policy IS $$100% of dwellings < 400 m of a bus stop every 30 min OR < 800 m of a train station every 15 min$$;
COMMENT ON COLUMN li_2018_sa2_indicators.trans_06 IS $$Percentage of dwellings < 400 m of a public transport stop with a scheduled service at least every 30 minutes between 7am and 7pm on a normal weekday (= a combined measure of proximity and frequency)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.trans_07 IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 30 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_sa2_indicators.trans_08 IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 25 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_sa2_indicators.trans_09 IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 20 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_01 IS $$Percentage of dwellings within 400 m or less distance of public open space$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_02 IS $$Percentage of dwellings < 400 m of public open space > 1.5 ha$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_03 IS $$Percentage of dwellings within 400 m or less distance of public open space$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_03_policy IS $$95% or more of dwellings within 400 m or less distance of public open space$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_04 IS $$Percentage of dwellings within 300 m or less distance of any public open space$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_04_policy IS $$100% of dwellings within 300 m or less distance of any public open space$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_05 IS $$Percentage of dwellings within 400 m or less distance of any local park (> 0.4 to <=1 ha)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_05_policy IS $$50% or more of dwellings within 400 m or less distance of any local park (> 0.4 to <=1 ha)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_06 IS $$Percentage of dwellings within 800 m or less distance of any neighbourhood park (>1 ha to <= 5ha)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_06_policy IS $$50% or more of dwellings within 800 m or less distance of any neighbourhood park (>1 ha to <= 5ha)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_07 IS $$Percentage of dwellings within 2 km or less of any district park (>5 ha to <=20 ha)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_07_policy IS $$50% or more of dwellings within 2 km or less of any district park (>5 ha to <=20 ha)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_08 IS $$Percentage of dwellings within 400 m or less distance of a neighbourhood recreation park (>0.5 ha)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_08_policy IS $$90% or more of dwellings within 400 m or less distance of a neighbourhood recreation park (>0.5 ha)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_09 IS $$Percentage of dwellings within 2.5 km or less distance of a district recreation park (>5 ha)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_09_policy IS $$90% or more of dwellings within 2.5 km or less distance of a district recreation park (>5 ha)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_10 IS $$Percentage of dwellings within 400 m or less distance of a park larger than 0.5 Ha$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_10_policy IS $$50% or more of dwellings within 400 m or less distance of a park larger than 0.5 Ha$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_11 IS $$Percentage of dwellings within 2 km or less distance of a park larger than 2 Ha$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_11_policy IS $$50% or more of dwellings within 2 km or less distance of a park larger than 2 Ha$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_12 IS $$Average distance to closest POS with a public toilet within 100 metres$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_14 IS $$Average distance to closest public open space (OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_15 IS $$Average distance to closest public open space <=0.4 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_16 IS $$Average distance to closest public open space >0.4 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_17 IS $$Average distance to closest public open space >0.5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_18 IS $$Average distance to closest public open space >1.5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_19 IS $$Average distance to closest public open space >2 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_20 IS $$Average distance to closest public open space >0.4 to <=1 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_21 IS $$Average distance to closest public open space >1 to <= 5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_22 IS $$Average distance to closest public open space >5 Ha to <=20 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_23 IS $$Average distance to closest public open space >5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_24 IS $$Average distance to closest public open space >20 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa2_indicators.os_public_25 IS $$Average distance to closest public open space with a sport facility (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa2_indicators.hous_02 IS $$Percentage of dwellings renting as a proportion of total$$;
COMMENT ON COLUMN li_2018_sa2_indicators.hous_04 IS $$Percentage of employed persons aged 15 and over using active transport to travel to work$$;
COMMENT ON COLUMN li_2018_sa2_indicators.hous_05 IS $$Percentage of employed persons aged 15 and over using public transport to travel to work$$;
COMMENT ON COLUMN li_2018_sa2_indicators.hous_06 IS $$Percentage of employed persons aged 15 and over using private vehicle/s to travel to work$$;
COMMENT ON COLUMN li_2018_sa2_indicators.food_12 IS $$Average count of supermarkets within 1.6km$$;
COMMENT ON COLUMN li_2018_sa2_indicators.food_13 IS $$Average count of fruit and vegetable grocers within 1.6km$$;
COMMENT ON COLUMN li_2018_sa2_indicators.food_14 IS $$Average count of specialty food stores (bakeries, butchers, fishmongers and delicatessens) within 1.6km$$;
COMMENT ON COLUMN li_2018_sa2_indicators.food_15 IS $$Average count of healther food outlets (supermarkets and fruit and vegetable grocers) within 1.6 km (OSM, or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.food_16 IS $$Average count of fast food outlets within 1.6km (OSM, or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.food_17 IS $$Average percentage of food outlets within 1.6km that provide healthier food options (ie. supermarkets and fruit and vegetable grocers; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.food_18 IS $$Average ratio of food outlets within 1.6km that provide healthier food options (ie. supermarkets and fruit and vegetable grocers) to fast food outlets; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.food_19 IS $$Average percentage of food outlets within 1.6km that provide fresh food options  (ie. supermarkets, fruit and vegetable grocers, bakeries, butchers, fishmongers and delicatessens; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.food_20 IS $$Average ratio of food outlets within 1.6km that provide fresh food options (ie. supermarkets, fruit and vegetable grocers, bakeries, butchers, fishmongers and delicatessens) to fast food outlets (OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.food_21 IS $$Percentage of dwellings with no availability of healthy or unhealthy food within 1.6km$$;
COMMENT ON COLUMN li_2018_sa2_indicators.food_22 IS $$Percentage of dwellings with no food outlets within 1.6km$$;
COMMENT ON COLUMN li_2018_sa2_indicators.food_23_hard IS $$Percentage of dwellings within 1km of a supermarket$$;
COMMENT ON COLUMN li_2018_sa2_indicators.food_24 IS $$Average distance to closest fresh food outlet (bakery, fruit and vegetables grocer, delicatessen, and fish, meat, poultry outlet; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.food_25 IS $$Average distance to closest healthy food outlet (supermarket or fruit and vegetables grocer; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.food_26 IS $$Average distance to closest fast food outlet (HLC, 2017; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.food_27 IS $$Average distance to closest dining establishment (cafe, restaurant, pub; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.community_01 IS $$Average distance to closest community centre (HLC, 2016; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.community_02 IS $$Average distance to closest cultural institution (museum, theatre, cinema, art gallery or art centre; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.alc_01 IS $$Average number of on-licenses within 400 m$$;
COMMENT ON COLUMN li_2018_sa2_indicators.alc_02 IS $$Average number of off-licenses within 800 m$$;
COMMENT ON COLUMN li_2018_sa2_indicators.alc_03 IS $$Average distance to closest bar, pub or nightclub (OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.childcare_01 IS $$Percentage of dwellings within 1600m of a children's day care which meets guidelines$$;
COMMENT ON COLUMN li_2018_sa2_indicators.childcare_02 IS $$Percentage of dwellings within 1600m of a children's day care (OSHC) which meets guidelines$$;
COMMENT ON COLUMN li_2018_sa2_indicators.health_01 IS $$Percentage of dwellings within 1600m of a GP$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_activity_centres IS $$Average distance to closest activity centre$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_alcohol_offlicence IS $$Average distance to closest offlicence alcohol outlet (HLC, 2017-19)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_alcohol_onlicence IS $$Average distance to closest onlicence alcohol outlet (HLC, 2017-19)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_alcohol_osm IS $$Average distance to closest alcohol outlet (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_all_schools IS $$Average distance to closest schools (all; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_art_centre_osm IS $$Average distance to closest art centre (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_art_gallery_osm IS $$Average distance to closest art gallery (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_bakery_osm IS $$Average distance to closest bakery (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_bar_osm IS $$Average distance to closest bar (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_cafe_osm IS $$Average distance to closest cafe (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_childcare_all IS $$Average distance to closest child care (all, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_childcare_all_exc IS $$Average distance to closest child care (exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_childcare_all_meet IS $$Average distance to closest child care (meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_childcare_oshc IS $$Average distance to closest child care (outside school hours, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_childcare_oshc_exc IS $$Average distance to closest child care (outside school hours exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_childcare_oshc_meet IS $$Average distance to closest child care (outside school hours meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_childcare_preschool IS $$Average distance to closest child care (pre-school, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_childcare_preschool_exc IS $$Average distance to closest child care (pre-school exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_childcare_preschool_meet IS $$Average distance to closest child care (pre-school meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_cinema_osm IS $$Average distance to closest cinema (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_community_centre_osm IS $$Average distance to closest community centre (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_convenience_osm IS $$Average distance to closest convenience store (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_deli_osm IS $$Average distance to closest deli (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_disability_employment IS $$Average distance to closest disabilty employment service $$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_fast_food IS $$Average distance to closest fast food (in house 2017)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_fastfood_osm IS $$Average distance to closest fast food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_food_court_osm IS $$Average distance to closest food court (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_food_health_osm IS $$Average distance to closest health food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_food_other_osm IS $$Average distance to closest other food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_fruit_veg_osm IS $$Average distance to closest fruit and veg (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_gtfs_2018_stop_30_mins_final IS $$Average distance to closest transport stop with frequent daytime service$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_gtfs_2018_stops IS $$Average distance to closest public transport stop$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_gtfs_2018_stops_bus IS $$Average distance to closest bus stop$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_gtfs_2018_stops_ferry IS $$Average distance to closest ferry terminal$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_gtfs_2018_stops_train IS $$Average distance to closest train station$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_gtfs_2018_stops_tram IS $$Average distance to closest tram stop$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_gtfs_20191008_20191205_bus_0015 IS $$Average distance to closest bus stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_gtfs_20191008_20191205_bus_0030 IS $$Average distance to closest bus stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_gtfs_20191008_20191205_bus_0045 IS $$Average distance to closest bus stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_gtfs_20191008_20191205_bus_any IS $$Average distance to closest bus stop$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_gtfs_20191008_20191205_ferry_0015 IS $$Average distance to closest ferry stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_gtfs_20191008_20191205_ferry_0030 IS $$Average distance to closest ferry stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_gtfs_20191008_20191205_ferry_0045 IS $$Average distance to closest ferry stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_gtfs_20191008_20191205_ferry_any IS $$Average distance to closest ferry stop$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_gtfs_20191008_20191205_revised_all IS $$Average distance to closest public transport stop$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_gtfs_20191008_20191205_revised_frequent30 IS $$Average distance to closest public transport stop with an average weekday service frequency of 30 minutes or less$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_gtfs_20191008_20191205_train_0015 IS $$Average distance to closest train stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_gtfs_20191008_20191205_train_0030 IS $$Average distance to closest train stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_gtfs_20191008_20191205_train_0045 IS $$Average distance to closest train stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_gtfs_20191008_20191205_train_any IS $$Average distance to closest train stop$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_gtfs_20191008_20191205_tram_0015 IS $$Average distance to closest tram stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_gtfs_20191008_20191205_tram_0030 IS $$Average distance to closest tram stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_gtfs_20191008_20191205_tram_0045 IS $$Average distance to closest tram stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_gtfs_20191008_20191205_tram_any IS $$Average distance to closest tram stop$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_hlc_2016_community_centres IS $$Average distance to closest community centre (2016)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_libraries IS $$Average distance to closest libraries (multiple sources, in-house, 2015-18)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_market_osm IS $$Average distance to closest market (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_meat_seafood_osm IS $$Average distance to closest meat / seafood (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_museum_osm IS $$Average distance to closest museum (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_newsagent_osm IS $$Average distance to closest newsagent (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_nhsd_2017_aged_care_residential IS $$Average distance to closest aged care residential service$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_nhsd_2017_dentist IS $$Average distance to closest dentist (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_nhsd_2017_gp IS $$Average distance to closest general practice/GP/doctor (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_nhsd_2017_hospital IS $$Average distance to closest hospital (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_nhsd_2017_mc_family_health IS $$Average distance to closest maternal, child and family health (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_nhsd_2017_other_community_health_care IS $$Average distance to closest 'other community health care' destination (not pharmacy or maternal and child health)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_nhsd_2017_pharmacy IS $$Average distance to closest pharmacy (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_P_12_Schools IS $$Average distance to closest schools (K - 12; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_P_12_Schools_catholic IS $$Average distance to closest schools (K - 12, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_P_12_Schools_gov IS $$Average distance to closest schools (K - 12, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_P_12_Schools_indep IS $$Average distance to closest schools (K - 12, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_petrolstation_osm IS $$Average distance to closest petrol station (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_pharmacy_osm IS $$Average distance to closest pharmacy (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_place_of_worship_osm IS $$Average distance to closest place of worship (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_playgrounds IS $$Average distance to closest playground (in house 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_postoffice_osm IS $$Average distance to post office (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_primary_schools IS $$Average distance to closest schools (primary; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_primary_schools_catholic IS $$Average distance to closest schools (primary, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_primary_schools_gov IS $$Average distance to closest schools (primary, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_primary_schools_indep IS $$Average distance to closest schools (primary, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_pub_osm IS $$Average distance to closest pub (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_public_swimming_pool_osm IS $$Average distance to closest public swimming pool (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_restaurant_osm IS $$Average distance to closest restaurant (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_secondary_schools IS $$Average distance to closest schools (secondary; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_secondary_schools_catholic IS $$Average distance to closest schools (secondary, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_secondary_schools_gov IS $$Average distance to closest schools (secondary, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_secondary_schools_indep IS $$Average distance to closest schools (secondary, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_special_schools IS $$Average distance to closest schools (special; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_supermarket IS $$Average distance to closest supermarket (in house 2017)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_supermarket_osm IS $$Average distance to closest supermarket (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa2_indicators.dist_m_theatre_osm IS $$Average distance to closest theatre (OSM, October 2018)$$;
```
</details>

Display information (including size and description) for this particular table: `\dt+ li_2018_sa2_indicators`
Display custom data dictionary by running `SELECT * FROM dictionary('li_2018_sa2_indicators');`



### Loading the Statistical Area 3 (SA3) indicator data


#### Initialise table defining variables and their data types

<details>
  <summary>
    Click to view code
  </summary>

```sql
CREATE TABLE li_2018_sa3_indicators 
(
sa3_name_2016 text PRIMARY KEY,
study_region text,
dwelling int,
person int,
sample_count int,
sample_count_per_ha float,
area_ha float,
dwellings_per_ha float,
net_dwelling float,
net_area     float,
net_density  float,
uli_city float,
uli_national float,
li_community_culture_leisure float,
li_early_years float,
li_education float,
li_health_services float,
li_sport_rec float,
li_food float,
li_convenience float,
li_pt_regular_400m float,
li_public_os_large_400m float,
li_street_connectivity_1600m float,
li_dwelling_density_1600m float,
li_sa1_30_40_housing_stress float,
li_sa1_sa3_local_employment float,
walkability_city float,
walkability_national float,
daily_living_access_1600m float,
social_infrastructure_mix float,
walk_02 float,
walk_02_policy boolean,
walk_03_policy boolean,
walk_05_policy boolean,
walk_12 float,
walk_12_policy boolean,
walk_13 float,
walk_13_policy boolean,
walk_14_policy boolean,
walk_15_policy boolean,
walk_16 float,
walk_17 float,
walk_21 float,
trans_01 float,
trans_01_policy boolean,
trans_02 float,
trans_02_policy boolean,
trans_03 float,
trans_03_policy boolean,
trans_04 float,
trans_04_policy boolean,
trans_05 float,
trans_05_policy boolean,
trans_06 float,
trans_07 float,
trans_08 float,
trans_09 float,
os_public_01 float,
os_public_02 float,
os_public_03 float,
os_public_03_policy boolean,
os_public_04 float,
os_public_04_policy boolean,
os_public_05 float,
os_public_05_policy boolean,
os_public_06 float,
os_public_06_policy boolean,
os_public_07 float,
os_public_07_policy boolean,
os_public_08 float,
os_public_08_policy boolean,
os_public_09 float,
os_public_09_policy boolean,
os_public_10 float,
os_public_10_policy boolean,
os_public_11 float,
os_public_11_policy boolean,
os_public_12 float,
os_public_14 float,
os_public_15 float,
os_public_16 float,
os_public_17 float,
os_public_18 float,
os_public_19 float,
os_public_20 float,
os_public_21 float,
os_public_22 float,
os_public_23 float,
os_public_24 float,
os_public_25 float,
hous_02 float,
hous_04 float,
hous_05 float,
hous_06 float,
food_12 float,
food_13 float,
food_14 float,
food_15 float,
food_16 float,
food_17 float,
food_18 float,
food_19 float,
food_20 float,
food_21 float,
food_22 float,
food_23_hard float,
food_24 float,
food_25 float,
food_26 float,
food_27 float,
community_01 float,
community_02 float,
alc_01 float,
alc_02 float,
alc_03 float,
childcare_01 float,
childcare_02 float,
health_01 float,
dist_m_activity_centres float,
dist_m_alcohol_offlicence float,
dist_m_alcohol_onlicence float,
dist_m_alcohol_osm float,
dist_m_all_schools float,
dist_m_art_centre_osm float,
dist_m_art_gallery_osm float,
dist_m_bakery_osm float,
dist_m_bar_osm float,
dist_m_cafe_osm float,
dist_m_childcare_all float,
dist_m_childcare_all_exc float,
dist_m_childcare_all_meet float,
dist_m_childcare_oshc float,
dist_m_childcare_oshc_exc float,
dist_m_childcare_oshc_meet float,
dist_m_childcare_preschool float,
dist_m_childcare_preschool_exc float,
dist_m_childcare_preschool_meet float,
dist_m_cinema_osm float,
dist_m_community_centre_osm float,
dist_m_convenience_osm float,
dist_m_deli_osm float,
dist_m_disability_employment float,
dist_m_fast_food float,
dist_m_fastfood_osm float,
dist_m_food_court_osm float,
dist_m_food_health_osm float,
dist_m_food_other_osm float,
dist_m_fruit_veg_osm float,
dist_m_gtfs_2018_stop_30_mins_final float,
dist_m_gtfs_2018_stops float,
dist_m_gtfs_2018_stops_bus float,
dist_m_gtfs_2018_stops_ferry float,
dist_m_gtfs_2018_stops_train float,
dist_m_gtfs_2018_stops_tram float,
dist_m_gtfs_20191008_20191205_bus_0015 float,
dist_m_gtfs_20191008_20191205_bus_0030 float,
dist_m_gtfs_20191008_20191205_bus_0045 float,
dist_m_gtfs_20191008_20191205_bus_any float,
dist_m_gtfs_20191008_20191205_ferry_0015 float,
dist_m_gtfs_20191008_20191205_ferry_0030 float,
dist_m_gtfs_20191008_20191205_ferry_0045 float,
dist_m_gtfs_20191008_20191205_ferry_any float,
dist_m_gtfs_20191008_20191205_revised_all float,
dist_m_gtfs_20191008_20191205_revised_frequent30 float,
dist_m_gtfs_20191008_20191205_train_0015 float,
dist_m_gtfs_20191008_20191205_train_0030 float,
dist_m_gtfs_20191008_20191205_train_0045 float,
dist_m_gtfs_20191008_20191205_train_any float,
dist_m_gtfs_20191008_20191205_tram_0015 float,
dist_m_gtfs_20191008_20191205_tram_0030 float,
dist_m_gtfs_20191008_20191205_tram_0045 float,
dist_m_gtfs_20191008_20191205_tram_any float,
dist_m_hlc_2016_community_centres float,
dist_m_libraries float,
dist_m_market_osm float,
dist_m_meat_seafood_osm float,
dist_m_museum_osm float,
dist_m_newsagent_osm float,
dist_m_nhsd_2017_aged_care_residential float,
dist_m_nhsd_2017_dentist float,
dist_m_nhsd_2017_gp float,
dist_m_nhsd_2017_hospital float,
dist_m_nhsd_2017_mc_family_health float,
dist_m_nhsd_2017_other_community_health_care float,
dist_m_nhsd_2017_pharmacy float,
dist_m_P_12_Schools float,
dist_m_P_12_Schools_catholic float,
dist_m_P_12_Schools_gov float,
dist_m_P_12_Schools_indep float,
dist_m_petrolstation_osm float,
dist_m_pharmacy_osm float,
dist_m_place_of_worship_osm float,
dist_m_playgrounds float,
dist_m_postoffice_osm float,
dist_m_primary_schools float,
dist_m_primary_schools_catholic float,
dist_m_primary_schools_gov float,
dist_m_primary_schools_indep float,
dist_m_pub_osm float,
dist_m_public_swimming_pool_osm float,
dist_m_restaurant_osm float,
dist_m_secondary_schools float,
dist_m_secondary_schools_catholic float,
dist_m_secondary_schools_gov float,
dist_m_secondary_schools_indep float,
dist_m_special_schools float,
dist_m_supermarket float,
dist_m_supermarket_osm float,
dist_m_theatre_osm float
);
```
</details>

### Copy the data from CSV
```sql
COPY li_2018_sa3_indicators FROM 'D:/projects/ntnl_li_2018/data/National Liveability 2018 - Final Outputs/For dissemination/hlc_ntnl_liveability_2018_sa3_2016.csv' WITH DELIMITER ',' CSV HEADER;
```

#### Optionally describe the data
<details>
  <summary>
    Click to view code
  </summary>

```sql
COMMENT ON TABLE li_2018_sa3_indicators IS $$Liveability indicators for dwellings, aggregated for Statistical Areas Level 3 (SA3)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.sa3_name_2016 IS $$SA3 name$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dwelling IS $$Dwelling count (Mesh Block dwelling count > 0 was an inclusion criteria for sampling)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.person IS $$Person count (persons usually resident)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.sample_count IS $$address points in area$$;
COMMENT ON COLUMN li_2018_sa3_indicators.sample_count_per_ha IS $$address point density per hectare$$;
COMMENT ON COLUMN li_2018_sa3_indicators.area_ha IS $$Area in hectares$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dwellings_per_ha IS $$gross dwelling density$$;
COMMENT ON COLUMN li_2018_sa3_indicators.net_dwelling IS $$net dwelling density (ie. for areas classified as residential at Mesh Block level)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.net_area IS $$net area (ie. for areas classified as residential at Mesh Block level)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.net_density IS $$net density (ie. for areas classified as residential at Mesh Block level)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.uli_city IS $$Average Urban Liveability Index, relative to locations within this city$$;
COMMENT ON COLUMN li_2018_sa3_indicators.uli_national IS $$Average Urban Liveability Index, relative to locations across Australia's 21 largest cities$$;
COMMENT ON COLUMN li_2018_sa3_indicators.li_community_culture_leisure IS $$Average score for access to community, culture and leisure destinations (community centre and library within 1000m, and museum/art gallery and cinema/theater within 3200m) (/1)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.li_early_years IS $$Average score for access to child care (any meeting ACECQA recommendations) within 800 metres and childcare (outside school hours meeting recommendations) within 1600 metres (/1)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.li_education IS $$Average score for access to primary and secondary public schools within 1600 metres (/1)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.li_health_services IS $$Average score for access to health services (GP, pharmacy, maternal, child and family health care, aged care facility and other community health care) within 1000 metres (/1)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.li_sport_rec IS $$Average score for access to an area of open space with sport/recreation facilities within 1000 metres, and a public swimming pool within 1200 metres (/1)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.li_food IS $$Average score for access to a supermarket and fresh fruit and vegetables within 1000 metres, and meat/seafood within 3200 metres (/1)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.li_convenience IS $$Average score for access to convenience destinations (convenience store and petrol station within 1000 metres, and a newsagent within 3200 metres) (/1)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.li_pt_regular_400m IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 30 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_sa3_indicators.li_public_os_large_400m IS $$Percentage of dwellings < 400 m of public open space > 1.5 ha$$;
COMMENT ON COLUMN li_2018_sa3_indicators.li_street_connectivity_1600m IS $$Average local street connectivity per square kilometre$$;
COMMENT ON COLUMN li_2018_sa3_indicators.li_dwelling_density_1600m IS $$Average local dwelling density per hectare (Ha) $$;
COMMENT ON COLUMN li_2018_sa3_indicators.li_sa1_30_40_housing_stress IS $$Percentage of SA1 households with income in the bottom 40% of the income distribution spending more than 30% of household income on housing costs$$;
COMMENT ON COLUMN li_2018_sa3_indicators.li_sa1_sa3_local_employment IS $$Percentage of employed persons who live and work in the same community$$;
COMMENT ON COLUMN li_2018_sa3_indicators.walkability_city IS $$Average walkability index, combining street connectivity, dwelling density and daily living destinations, relative to locations within this city$$;
COMMENT ON COLUMN li_2018_sa3_indicators.walkability_national IS $$Average walkability index, combining street connectivity, dwelling density and daily living destinations, relative to locations across Australia's 21 largest cities$$;
COMMENT ON COLUMN li_2018_sa3_indicators.daily_living_access_1600m IS $$Average number of daily living types present, measured as a score of 0-3, with 1 point for each category of convenience store/petrol station/newsagent, PT stop, supermarket within 1600m network distance$$;
COMMENT ON COLUMN li_2018_sa3_indicators.social_infrastructure_mix IS $$Average social infrastructure mix score (/16)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.walk_02 IS $$Percentage of dwellings <1 km walking distance of an activity centre with a supermarket$$;
COMMENT ON COLUMN li_2018_sa3_indicators.walk_02_policy IS $$At least 80% of dwellings are within 1 km walking distance of an activity centre with a supermarket$$;
COMMENT ON COLUMN li_2018_sa3_indicators.walk_03_policy IS $$Area has at least 15 dwellings per net developable hectare$$;
COMMENT ON COLUMN li_2018_sa3_indicators.walk_05_policy IS $$Area has at least 26 dwellings per net developable hectare$$;
COMMENT ON COLUMN li_2018_sa3_indicators.walk_12 IS $$Percentage of dwellings with local dwelling density of 15 dwellings per hectare or greater$$;
COMMENT ON COLUMN li_2018_sa3_indicators.walk_12_policy IS $$15 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_sa3_indicators.walk_13 IS $$Percentage of dwellings with local dwelling density of 30 dwellings per hectare or greater$$;
COMMENT ON COLUMN li_2018_sa3_indicators.walk_13_policy IS $$Local dwelling density of 30 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_sa3_indicators.walk_14_policy IS $$Gross dwelling density of 15 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_sa3_indicators.walk_15_policy IS $$Gross dwelling density of 30 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_sa3_indicators.walk_16 IS $$Average distance to closest activity centre (proxy measure: supermarket within a commercial zoned Mesh Block)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.walk_17 IS $$Average pedshed ratio, defined as the area of the 400 m pedestrian network from each residential dwelling buffered by 50m divided by the radial 400 m "crow flies" area (i.e. 50.2 Ha.)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.walk_21 IS $$Average number of local living types present (see paper of Mavoa et al)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.trans_01 IS $$Percentage of dwellings with access to bus stop within 400 m, a tram stop within 600m, or a train station within 800 m$$;
COMMENT ON COLUMN li_2018_sa3_indicators.trans_01_policy IS $$95% or more of dwellings with access to bus stop within 400 m, a tram stop within 600m, or a train station within 800 m$$;
COMMENT ON COLUMN li_2018_sa3_indicators.trans_02 IS $$Percentage of dwellings with access to bus stop < 400 m$$;
COMMENT ON COLUMN li_2018_sa3_indicators.trans_02_policy IS $$95% or more of dwellings with access to bus stop < 400 m$$;
COMMENT ON COLUMN li_2018_sa3_indicators.trans_03 IS $$Percentage of dwellings < 400m walk from a neighbourhood or town centre, or a bus stop, or in a 800m walk from a railway station.$$;
COMMENT ON COLUMN li_2018_sa3_indicators.trans_03_policy IS $$60% or more of dwellings < 400m walk from a neighbourhood or town centre, or a bus stop, or in a 800m walk from a railway station.$$;
COMMENT ON COLUMN li_2018_sa3_indicators.trans_04 IS $$Percentage of dwellings < 400 metres of an existing or planned public transport stop$$;
COMMENT ON COLUMN li_2018_sa3_indicators.trans_04_policy IS $$100% of dwellings < 400 metres of an existing or planned public transport stop$$;
COMMENT ON COLUMN li_2018_sa3_indicators.trans_05 IS $$Percentage of dwellings < 400 m of a bus stop every 30 min OR < 800 m of a train station every 15 min$$;
COMMENT ON COLUMN li_2018_sa3_indicators.trans_05_policy IS $$100% of dwellings < 400 m of a bus stop every 30 min OR < 800 m of a train station every 15 min$$;
COMMENT ON COLUMN li_2018_sa3_indicators.trans_06 IS $$Percentage of dwellings < 400 m of a public transport stop with a scheduled service at least every 30 minutes between 7am and 7pm on a normal weekday (= a combined measure of proximity and frequency)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.trans_07 IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 30 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_sa3_indicators.trans_08 IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 25 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_sa3_indicators.trans_09 IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 20 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_01 IS $$Percentage of dwellings within 400 m or less distance of public open space$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_02 IS $$Percentage of dwellings < 400 m of public open space > 1.5 ha$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_03 IS $$Percentage of dwellings within 400 m or less distance of public open space$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_03_policy IS $$95% or more of dwellings within 400 m or less distance of public open space$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_04 IS $$Percentage of dwellings within 300 m or less distance of any public open space$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_04_policy IS $$100% of dwellings within 300 m or less distance of any public open space$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_05 IS $$Percentage of dwellings within 400 m or less distance of any local park (> 0.4 to <=1 ha)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_05_policy IS $$50% or more of dwellings within 400 m or less distance of any local park (> 0.4 to <=1 ha)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_06 IS $$Percentage of dwellings within 800 m or less distance of any neighbourhood park (>1 ha to <= 5ha)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_06_policy IS $$50% or more of dwellings within 800 m or less distance of any neighbourhood park (>1 ha to <= 5ha)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_07 IS $$Percentage of dwellings within 2 km or less of any district park (>5 ha to <=20 ha)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_07_policy IS $$50% or more of dwellings within 2 km or less of any district park (>5 ha to <=20 ha)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_08 IS $$Percentage of dwellings within 400 m or less distance of a neighbourhood recreation park (>0.5 ha)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_08_policy IS $$90% or more of dwellings within 400 m or less distance of a neighbourhood recreation park (>0.5 ha)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_09 IS $$Percentage of dwellings within 2.5 km or less distance of a district recreation park (>5 ha)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_09_policy IS $$90% or more of dwellings within 2.5 km or less distance of a district recreation park (>5 ha)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_10 IS $$Percentage of dwellings within 400 m or less distance of a park larger than 0.5 Ha$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_10_policy IS $$50% or more of dwellings within 400 m or less distance of a park larger than 0.5 Ha$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_11 IS $$Percentage of dwellings within 2 km or less distance of a park larger than 2 Ha$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_11_policy IS $$50% or more of dwellings within 2 km or less distance of a park larger than 2 Ha$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_12 IS $$Average distance to closest POS with a public toilet within 100 metres$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_14 IS $$Average distance to closest public open space (OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_15 IS $$Average distance to closest public open space <=0.4 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_16 IS $$Average distance to closest public open space >0.4 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_17 IS $$Average distance to closest public open space >0.5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_18 IS $$Average distance to closest public open space >1.5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_19 IS $$Average distance to closest public open space >2 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_20 IS $$Average distance to closest public open space >0.4 to <=1 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_21 IS $$Average distance to closest public open space >1 to <= 5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_22 IS $$Average distance to closest public open space >5 Ha to <=20 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_23 IS $$Average distance to closest public open space >5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_24 IS $$Average distance to closest public open space >20 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa3_indicators.os_public_25 IS $$Average distance to closest public open space with a sport facility (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa3_indicators.hous_02 IS $$Percentage of dwellings renting as a proportion of total$$;
COMMENT ON COLUMN li_2018_sa3_indicators.hous_04 IS $$Percentage of employed persons aged 15 and over using active transport to travel to work$$;
COMMENT ON COLUMN li_2018_sa3_indicators.hous_05 IS $$Percentage of employed persons aged 15 and over using public transport to travel to work$$;
COMMENT ON COLUMN li_2018_sa3_indicators.hous_06 IS $$Percentage of employed persons aged 15 and over using private vehicle/s to travel to work$$;
COMMENT ON COLUMN li_2018_sa3_indicators.food_12 IS $$Average count of supermarkets within 1.6km$$;
COMMENT ON COLUMN li_2018_sa3_indicators.food_13 IS $$Average count of fruit and vegetable grocers within 1.6km$$;
COMMENT ON COLUMN li_2018_sa3_indicators.food_14 IS $$Average count of specialty food stores (bakeries, butchers, fishmongers and delicatessens) within 1.6km$$;
COMMENT ON COLUMN li_2018_sa3_indicators.food_15 IS $$Average count of healther food outlets (supermarkets and fruit and vegetable grocers) within 1.6 km (OSM, or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.food_16 IS $$Average count of fast food outlets within 1.6km (OSM, or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.food_17 IS $$Average percentage of food outlets within 1.6km that provide healthier food options (ie. supermarkets and fruit and vegetable grocers; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.food_18 IS $$Average ratio of food outlets within 1.6km that provide healthier food options (ie. supermarkets and fruit and vegetable grocers) to fast food outlets; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.food_19 IS $$Average percentage of food outlets within 1.6km that provide fresh food options  (ie. supermarkets, fruit and vegetable grocers, bakeries, butchers, fishmongers and delicatessens; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.food_20 IS $$Average ratio of food outlets within 1.6km that provide fresh food options (ie. supermarkets, fruit and vegetable grocers, bakeries, butchers, fishmongers and delicatessens) to fast food outlets (OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.food_21 IS $$Percentage of dwellings with no availability of healthy or unhealthy food within 1.6km$$;
COMMENT ON COLUMN li_2018_sa3_indicators.food_22 IS $$Percentage of dwellings with no food outlets within 1.6km$$;
COMMENT ON COLUMN li_2018_sa3_indicators.food_23_hard IS $$Percentage of dwellings within 1km of a supermarket$$;
COMMENT ON COLUMN li_2018_sa3_indicators.food_24 IS $$Average distance to closest fresh food outlet (bakery, fruit and vegetables grocer, delicatessen, and fish, meat, poultry outlet; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.food_25 IS $$Average distance to closest healthy food outlet (supermarket or fruit and vegetables grocer; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.food_26 IS $$Average distance to closest fast food outlet (HLC, 2017; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.food_27 IS $$Average distance to closest dining establishment (cafe, restaurant, pub; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.community_01 IS $$Average distance to closest community centre (HLC, 2016; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.community_02 IS $$Average distance to closest cultural institution (museum, theatre, cinema, art gallery or art centre; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.alc_01 IS $$Average number of on-licenses within 400 m$$;
COMMENT ON COLUMN li_2018_sa3_indicators.alc_02 IS $$Average number of off-licenses within 800 m$$;
COMMENT ON COLUMN li_2018_sa3_indicators.alc_03 IS $$Average distance to closest bar, pub or nightclub (OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.childcare_01 IS $$Percentage of dwellings within 1600m of a children's day care which meets guidelines$$;
COMMENT ON COLUMN li_2018_sa3_indicators.childcare_02 IS $$Percentage of dwellings within 1600m of a children's day care (OSHC) which meets guidelines$$;
COMMENT ON COLUMN li_2018_sa3_indicators.health_01 IS $$Percentage of dwellings within 1600m of a GP$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_activity_centres IS $$Average distance to closest activity centre$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_alcohol_offlicence IS $$Average distance to closest offlicence alcohol outlet (HLC, 2017-19)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_alcohol_onlicence IS $$Average distance to closest onlicence alcohol outlet (HLC, 2017-19)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_alcohol_osm IS $$Average distance to closest alcohol outlet (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_all_schools IS $$Average distance to closest schools (all; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_art_centre_osm IS $$Average distance to closest art centre (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_art_gallery_osm IS $$Average distance to closest art gallery (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_bakery_osm IS $$Average distance to closest bakery (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_bar_osm IS $$Average distance to closest bar (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_cafe_osm IS $$Average distance to closest cafe (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_childcare_all IS $$Average distance to closest child care (all, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_childcare_all_exc IS $$Average distance to closest child care (exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_childcare_all_meet IS $$Average distance to closest child care (meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_childcare_oshc IS $$Average distance to closest child care (outside school hours, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_childcare_oshc_exc IS $$Average distance to closest child care (outside school hours exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_childcare_oshc_meet IS $$Average distance to closest child care (outside school hours meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_childcare_preschool IS $$Average distance to closest child care (pre-school, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_childcare_preschool_exc IS $$Average distance to closest child care (pre-school exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_childcare_preschool_meet IS $$Average distance to closest child care (pre-school meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_cinema_osm IS $$Average distance to closest cinema (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_community_centre_osm IS $$Average distance to closest community centre (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_convenience_osm IS $$Average distance to closest convenience store (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_deli_osm IS $$Average distance to closest deli (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_disability_employment IS $$Average distance to closest disabilty employment service $$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_fast_food IS $$Average distance to closest fast food (in house 2017)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_fastfood_osm IS $$Average distance to closest fast food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_food_court_osm IS $$Average distance to closest food court (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_food_health_osm IS $$Average distance to closest health food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_food_other_osm IS $$Average distance to closest other food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_fruit_veg_osm IS $$Average distance to closest fruit and veg (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_gtfs_2018_stop_30_mins_final IS $$Average distance to closest transport stop with frequent daytime service$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_gtfs_2018_stops IS $$Average distance to closest public transport stop$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_gtfs_2018_stops_bus IS $$Average distance to closest bus stop$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_gtfs_2018_stops_ferry IS $$Average distance to closest ferry terminal$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_gtfs_2018_stops_train IS $$Average distance to closest train station$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_gtfs_2018_stops_tram IS $$Average distance to closest tram stop$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_gtfs_20191008_20191205_bus_0015 IS $$Average distance to closest bus stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_gtfs_20191008_20191205_bus_0030 IS $$Average distance to closest bus stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_gtfs_20191008_20191205_bus_0045 IS $$Average distance to closest bus stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_gtfs_20191008_20191205_bus_any IS $$Average distance to closest bus stop$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_gtfs_20191008_20191205_ferry_0015 IS $$Average distance to closest ferry stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_gtfs_20191008_20191205_ferry_0030 IS $$Average distance to closest ferry stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_gtfs_20191008_20191205_ferry_0045 IS $$Average distance to closest ferry stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_gtfs_20191008_20191205_ferry_any IS $$Average distance to closest ferry stop$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_gtfs_20191008_20191205_revised_all IS $$Average distance to closest public transport stop$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_gtfs_20191008_20191205_revised_frequent30 IS $$Average distance to closest public transport stop with an average weekday service frequency of 30 minutes or less$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_gtfs_20191008_20191205_train_0015 IS $$Average distance to closest train stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_gtfs_20191008_20191205_train_0030 IS $$Average distance to closest train stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_gtfs_20191008_20191205_train_0045 IS $$Average distance to closest train stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_gtfs_20191008_20191205_train_any IS $$Average distance to closest train stop$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_gtfs_20191008_20191205_tram_0015 IS $$Average distance to closest tram stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_gtfs_20191008_20191205_tram_0030 IS $$Average distance to closest tram stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_gtfs_20191008_20191205_tram_0045 IS $$Average distance to closest tram stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_gtfs_20191008_20191205_tram_any IS $$Average distance to closest tram stop$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_hlc_2016_community_centres IS $$Average distance to closest community centre (2016)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_libraries IS $$Average distance to closest libraries (multiple sources, in-house, 2015-18)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_market_osm IS $$Average distance to closest market (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_meat_seafood_osm IS $$Average distance to closest meat / seafood (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_museum_osm IS $$Average distance to closest museum (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_newsagent_osm IS $$Average distance to closest newsagent (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_nhsd_2017_aged_care_residential IS $$Average distance to closest aged care residential service$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_nhsd_2017_dentist IS $$Average distance to closest dentist (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_nhsd_2017_gp IS $$Average distance to closest general practice/GP/doctor (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_nhsd_2017_hospital IS $$Average distance to closest hospital (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_nhsd_2017_mc_family_health IS $$Average distance to closest maternal, child and family health (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_nhsd_2017_other_community_health_care IS $$Average distance to closest 'other community health care' destination (not pharmacy or maternal and child health)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_nhsd_2017_pharmacy IS $$Average distance to closest pharmacy (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_P_12_Schools IS $$Average distance to closest schools (K - 12; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_P_12_Schools_catholic IS $$Average distance to closest schools (K - 12, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_P_12_Schools_gov IS $$Average distance to closest schools (K - 12, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_P_12_Schools_indep IS $$Average distance to closest schools (K - 12, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_petrolstation_osm IS $$Average distance to closest petrol station (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_pharmacy_osm IS $$Average distance to closest pharmacy (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_place_of_worship_osm IS $$Average distance to closest place of worship (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_playgrounds IS $$Average distance to closest playground (in house 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_postoffice_osm IS $$Average distance to post office (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_primary_schools IS $$Average distance to closest schools (primary; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_primary_schools_catholic IS $$Average distance to closest schools (primary, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_primary_schools_gov IS $$Average distance to closest schools (primary, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_primary_schools_indep IS $$Average distance to closest schools (primary, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_pub_osm IS $$Average distance to closest pub (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_public_swimming_pool_osm IS $$Average distance to closest public swimming pool (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_restaurant_osm IS $$Average distance to closest restaurant (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_secondary_schools IS $$Average distance to closest schools (secondary; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_secondary_schools_catholic IS $$Average distance to closest schools (secondary, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_secondary_schools_gov IS $$Average distance to closest schools (secondary, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_secondary_schools_indep IS $$Average distance to closest schools (secondary, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_special_schools IS $$Average distance to closest schools (special; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_supermarket IS $$Average distance to closest supermarket (in house 2017)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_supermarket_osm IS $$Average distance to closest supermarket (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa3_indicators.dist_m_theatre_osm IS $$Average distance to closest theatre (OSM, October 2018)$$;
```
</details>

Display information (including size and description) for this particular table: `\dt+ li_2018_sa3_indicators`
Display custom data dictionary by running `SELECT * FROM dictionary('li_2018_sa3_indicators');`


### Loading the Statistical Area 4 (SA4) indicator data


#### Initialise table defining variables and their data types

<details>
  <summary>
    Click to view code
  </summary>

```sql
CREATE TABLE li_2018_sa4_indicators 
(
sa4_name_2016 text PRIMARY KEY,
study_region text,
dwelling int,
person int,
sample_count int,
sample_count_per_ha float,
area_ha float,
dwellings_per_ha float,
net_dwelling float,
net_area     float,
net_density  float,
uli_city float,
uli_national float,
li_community_culture_leisure float,
li_early_years float,
li_education float,
li_health_services float,
li_sport_rec float,
li_food float,
li_convenience float,
li_pt_regular_400m float,
li_public_os_large_400m float,
li_street_connectivity_1600m float,
li_dwelling_density_1600m float,
li_sa1_30_40_housing_stress float,
li_sa1_sa3_local_employment float,
walkability_city float,
walkability_national float,
daily_living_access_1600m float,
social_infrastructure_mix float,
walk_02 float,
walk_02_policy boolean,
walk_03_policy boolean,
walk_05_policy boolean,
walk_12 float,
walk_12_policy boolean,
walk_13 float,
walk_13_policy boolean,
walk_14_policy boolean,
walk_15_policy boolean,
walk_16 float,
walk_17 float,
walk_21 float,
trans_01 float,
trans_01_policy boolean,
trans_02 float,
trans_02_policy boolean,
trans_03 float,
trans_03_policy boolean,
trans_04 float,
trans_04_policy boolean,
trans_05 float,
trans_05_policy boolean,
trans_06 float,
trans_07 float,
trans_08 float,
trans_09 float,
os_public_01 float,
os_public_02 float,
os_public_03 float,
os_public_03_policy boolean,
os_public_04 float,
os_public_04_policy boolean,
os_public_05 float,
os_public_05_policy boolean,
os_public_06 float,
os_public_06_policy boolean,
os_public_07 float,
os_public_07_policy boolean,
os_public_08 float,
os_public_08_policy boolean,
os_public_09 float,
os_public_09_policy boolean,
os_public_10 float,
os_public_10_policy boolean,
os_public_11 float,
os_public_11_policy boolean,
os_public_12 float,
os_public_14 float,
os_public_15 float,
os_public_16 float,
os_public_17 float,
os_public_18 float,
os_public_19 float,
os_public_20 float,
os_public_21 float,
os_public_22 float,
os_public_23 float,
os_public_24 float,
os_public_25 float,
hous_02 float,
hous_04 float,
hous_05 float,
hous_06 float,
food_12 float,
food_13 float,
food_14 float,
food_15 float,
food_16 float,
food_17 float,
food_18 float,
food_19 float,
food_20 float,
food_21 float,
food_22 float,
food_23_hard float,
food_24 float,
food_25 float,
food_26 float,
food_27 float,
community_01 float,
community_02 float,
alc_01 float,
alc_02 float,
alc_03 float,
childcare_01 float,
childcare_02 float,
health_01 float,
dist_m_activity_centres float,
dist_m_alcohol_offlicence float,
dist_m_alcohol_onlicence float,
dist_m_alcohol_osm float,
dist_m_all_schools float,
dist_m_art_centre_osm float,
dist_m_art_gallery_osm float,
dist_m_bakery_osm float,
dist_m_bar_osm float,
dist_m_cafe_osm float,
dist_m_childcare_all float,
dist_m_childcare_all_exc float,
dist_m_childcare_all_meet float,
dist_m_childcare_oshc float,
dist_m_childcare_oshc_exc float,
dist_m_childcare_oshc_meet float,
dist_m_childcare_preschool float,
dist_m_childcare_preschool_exc float,
dist_m_childcare_preschool_meet float,
dist_m_cinema_osm float,
dist_m_community_centre_osm float,
dist_m_convenience_osm float,
dist_m_deli_osm float,
dist_m_disability_employment float,
dist_m_fast_food float,
dist_m_fastfood_osm float,
dist_m_food_court_osm float,
dist_m_food_health_osm float,
dist_m_food_other_osm float,
dist_m_fruit_veg_osm float,
dist_m_gtfs_2018_stop_30_mins_final float,
dist_m_gtfs_2018_stops float,
dist_m_gtfs_2018_stops_bus float,
dist_m_gtfs_2018_stops_ferry float,
dist_m_gtfs_2018_stops_train float,
dist_m_gtfs_2018_stops_tram float,
dist_m_gtfs_20191008_20191205_bus_0015 float,
dist_m_gtfs_20191008_20191205_bus_0030 float,
dist_m_gtfs_20191008_20191205_bus_0045 float,
dist_m_gtfs_20191008_20191205_bus_any float,
dist_m_gtfs_20191008_20191205_ferry_0015 float,
dist_m_gtfs_20191008_20191205_ferry_0030 float,
dist_m_gtfs_20191008_20191205_ferry_0045 float,
dist_m_gtfs_20191008_20191205_ferry_any float,
dist_m_gtfs_20191008_20191205_revised_all float,
dist_m_gtfs_20191008_20191205_revised_frequent30 float,
dist_m_gtfs_20191008_20191205_train_0015 float,
dist_m_gtfs_20191008_20191205_train_0030 float,
dist_m_gtfs_20191008_20191205_train_0045 float,
dist_m_gtfs_20191008_20191205_train_any float,
dist_m_gtfs_20191008_20191205_tram_0015 float,
dist_m_gtfs_20191008_20191205_tram_0030 float,
dist_m_gtfs_20191008_20191205_tram_0045 float,
dist_m_gtfs_20191008_20191205_tram_any float,
dist_m_hlc_2016_community_centres float,
dist_m_libraries float,
dist_m_market_osm float,
dist_m_meat_seafood_osm float,
dist_m_museum_osm float,
dist_m_newsagent_osm float,
dist_m_nhsd_2017_aged_care_residential float,
dist_m_nhsd_2017_dentist float,
dist_m_nhsd_2017_gp float,
dist_m_nhsd_2017_hospital float,
dist_m_nhsd_2017_mc_family_health float,
dist_m_nhsd_2017_other_community_health_care float,
dist_m_nhsd_2017_pharmacy float,
dist_m_P_12_Schools float,
dist_m_P_12_Schools_catholic float,
dist_m_P_12_Schools_gov float,
dist_m_P_12_Schools_indep float,
dist_m_petrolstation_osm float,
dist_m_pharmacy_osm float,
dist_m_place_of_worship_osm float,
dist_m_playgrounds float,
dist_m_postoffice_osm float,
dist_m_primary_schools float,
dist_m_primary_schools_catholic float,
dist_m_primary_schools_gov float,
dist_m_primary_schools_indep float,
dist_m_pub_osm float,
dist_m_public_swimming_pool_osm float,
dist_m_restaurant_osm float,
dist_m_secondary_schools float,
dist_m_secondary_schools_catholic float,
dist_m_secondary_schools_gov float,
dist_m_secondary_schools_indep float,
dist_m_special_schools float,
dist_m_supermarket float,
dist_m_supermarket_osm float,
dist_m_theatre_osm float
);
```
</details>

### Copy the data from CSV
```sql
COPY li_2018_sa4_indicators FROM 'D:/projects/ntnl_li_2018/data/National Liveability 2018 - Final Outputs/For dissemination/hlc_ntnl_liveability_2018_sa2_2016.csv' WITH DELIMITER ',' CSV HEADER;
```

#### Optionally describe the data
<details>
  <summary>
    Click to view code
  </summary>

```sql
COMMENT ON TABLE li_2018_sa4_indicators IS $$Liveability indicators for dwellings, aggregated for Statistical Areas Level 4 (SA4)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.sa4_name_2016 IS $$SA4 name$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dwelling IS $$Dwelling count (Mesh Block dwelling count > 0 was an inclusion criteria for sampling)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.person IS $$Person count (persons usually resident)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.sample_count IS $$address points in area$$;
COMMENT ON COLUMN li_2018_sa4_indicators.sample_count_per_ha IS $$address point density per hectare$$;
COMMENT ON COLUMN li_2018_sa4_indicators.area_ha IS $$Area in hectares$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dwellings_per_ha IS $$gross dwelling density$$;
COMMENT ON COLUMN li_2018_sa4_indicators.net_dwelling IS $$net dwelling density (ie. for areas classified as residential at Mesh Block level)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.net_area IS $$net area (ie. for areas classified as residential at Mesh Block level)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.net_density IS $$net density (ie. for areas classified as residential at Mesh Block level)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.uli_city IS $$Average Urban Liveability Index, relative to locations within this city$$;
COMMENT ON COLUMN li_2018_sa4_indicators.uli_national IS $$Average Urban Liveability Index, relative to locations across Australia's 21 largest cities$$;
COMMENT ON COLUMN li_2018_sa4_indicators.li_community_culture_leisure IS $$Average score for access to community, culture and leisure destinations (community centre and library within 1000m, and museum/art gallery and cinema/theater within 3200m) (/1)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.li_early_years IS $$Average score for access to child care (any meeting ACECQA recommendations) within 800 metres and childcare (outside school hours meeting recommendations) within 1600 metres (/1)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.li_education IS $$Average score for access to primary and secondary public schools within 1600 metres (/1)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.li_health_services IS $$Average score for access to health services (GP, pharmacy, maternal, child and family health care, aged care facility and other community health care) within 1000 metres (/1)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.li_sport_rec IS $$Average score for access to an area of open space with sport/recreation facilities within 1000 metres, and a public swimming pool within 1200 metres (/1)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.li_food IS $$Average score for access to a supermarket and fresh fruit and vegetables within 1000 metres, and meat/seafood within 3200 metres (/1)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.li_convenience IS $$Average score for access to convenience destinations (convenience store and petrol station within 1000 metres, and a newsagent within 3200 metres) (/1)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.li_pt_regular_400m IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 30 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_sa4_indicators.li_public_os_large_400m IS $$Percentage of dwellings < 400 m of public open space > 1.5 ha$$;
COMMENT ON COLUMN li_2018_sa4_indicators.li_street_connectivity_1600m IS $$Average local street connectivity per square kilometre$$;
COMMENT ON COLUMN li_2018_sa4_indicators.li_dwelling_density_1600m IS $$Average local dwelling density per hectare (Ha) $$;
COMMENT ON COLUMN li_2018_sa4_indicators.li_sa1_30_40_housing_stress IS $$Percentage of SA1 households with income in the bottom 40% of the income distribution spending more than 30% of household income on housing costs$$;
COMMENT ON COLUMN li_2018_sa4_indicators.li_sa1_sa3_local_employment IS $$Percentage of employed persons who live and work in the same community$$;
COMMENT ON COLUMN li_2018_sa4_indicators.walkability_city IS $$Average walkability index, combining street connectivity, dwelling density and daily living destinations, relative to locations within this city$$;
COMMENT ON COLUMN li_2018_sa4_indicators.walkability_national IS $$Average walkability index, combining street connectivity, dwelling density and daily living destinations, relative to locations across Australia's 21 largest cities$$;
COMMENT ON COLUMN li_2018_sa4_indicators.daily_living_access_1600m IS $$Average number of daily living types present, measured as a score of 0-3, with 1 point for each category of convenience store/petrol station/newsagent, PT stop, supermarket within 1600m network distance$$;
COMMENT ON COLUMN li_2018_sa4_indicators.social_infrastructure_mix IS $$Average social infrastructure mix score (/16)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.walk_02 IS $$Percentage of dwellings <1 km walking distance of an activity centre with a supermarket$$;
COMMENT ON COLUMN li_2018_sa4_indicators.walk_02_policy IS $$At least 80% of dwellings are within 1 km walking distance of an activity centre with a supermarket$$;
COMMENT ON COLUMN li_2018_sa4_indicators.walk_03_policy IS $$Area has at least 15 dwellings per net developable hectare$$;
COMMENT ON COLUMN li_2018_sa4_indicators.walk_05_policy IS $$Area has at least 26 dwellings per net developable hectare$$;
COMMENT ON COLUMN li_2018_sa4_indicators.walk_12 IS $$Percentage of dwellings with local dwelling density of 15 dwellings per hectare or greater$$;
COMMENT ON COLUMN li_2018_sa4_indicators.walk_12_policy IS $$15 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_sa4_indicators.walk_13 IS $$Percentage of dwellings with local dwelling density of 30 dwellings per hectare or greater$$;
COMMENT ON COLUMN li_2018_sa4_indicators.walk_13_policy IS $$Local dwelling density of 30 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_sa4_indicators.walk_14_policy IS $$Gross dwelling density of 15 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_sa4_indicators.walk_15_policy IS $$Gross dwelling density of 30 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_sa4_indicators.walk_16 IS $$Average distance to closest activity centre (proxy measure: supermarket within a commercial zoned Mesh Block)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.walk_17 IS $$Average pedshed ratio, defined as the area of the 400 m pedestrian network from each residential dwelling buffered by 50m divided by the radial 400 m "crow flies" area (i.e. 50.2 Ha.)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.walk_21 IS $$Average number of local living types present (see paper of Mavoa et al)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.trans_01 IS $$Percentage of dwellings with access to bus stop within 400 m, a tram stop within 600m, or a train station within 800 m$$;
COMMENT ON COLUMN li_2018_sa4_indicators.trans_01_policy IS $$95% or more of dwellings with access to bus stop within 400 m, a tram stop within 600m, or a train station within 800 m$$;
COMMENT ON COLUMN li_2018_sa4_indicators.trans_02 IS $$Percentage of dwellings with access to bus stop < 400 m$$;
COMMENT ON COLUMN li_2018_sa4_indicators.trans_02_policy IS $$95% or more of dwellings with access to bus stop < 400 m$$;
COMMENT ON COLUMN li_2018_sa4_indicators.trans_03 IS $$Percentage of dwellings < 400m walk from a neighbourhood or town centre, or a bus stop, or in a 800m walk from a railway station.$$;
COMMENT ON COLUMN li_2018_sa4_indicators.trans_03_policy IS $$60% or more of dwellings < 400m walk from a neighbourhood or town centre, or a bus stop, or in a 800m walk from a railway station.$$;
COMMENT ON COLUMN li_2018_sa4_indicators.trans_04 IS $$Percentage of dwellings < 400 metres of an existing or planned public transport stop$$;
COMMENT ON COLUMN li_2018_sa4_indicators.trans_04_policy IS $$100% of dwellings < 400 metres of an existing or planned public transport stop$$;
COMMENT ON COLUMN li_2018_sa4_indicators.trans_05 IS $$Percentage of dwellings < 400 m of a bus stop every 30 min OR < 800 m of a train station every 15 min$$;
COMMENT ON COLUMN li_2018_sa4_indicators.trans_05_policy IS $$100% of dwellings < 400 m of a bus stop every 30 min OR < 800 m of a train station every 15 min$$;
COMMENT ON COLUMN li_2018_sa4_indicators.trans_06 IS $$Percentage of dwellings < 400 m of a public transport stop with a scheduled service at least every 30 minutes between 7am and 7pm on a normal weekday (= a combined measure of proximity and frequency)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.trans_07 IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 30 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_sa4_indicators.trans_08 IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 25 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_sa4_indicators.trans_09 IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 20 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_01 IS $$Percentage of dwellings within 400 m or less distance of public open space$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_02 IS $$Percentage of dwellings < 400 m of public open space > 1.5 ha$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_03 IS $$Percentage of dwellings within 400 m or less distance of public open space$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_03_policy IS $$95% or more of dwellings within 400 m or less distance of public open space$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_04 IS $$Percentage of dwellings within 300 m or less distance of any public open space$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_04_policy IS $$100% of dwellings within 300 m or less distance of any public open space$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_05 IS $$Percentage of dwellings within 400 m or less distance of any local park (> 0.4 to <=1 ha)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_05_policy IS $$50% or more of dwellings within 400 m or less distance of any local park (> 0.4 to <=1 ha)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_06 IS $$Percentage of dwellings within 800 m or less distance of any neighbourhood park (>1 ha to <= 5ha)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_06_policy IS $$50% or more of dwellings within 800 m or less distance of any neighbourhood park (>1 ha to <= 5ha)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_07 IS $$Percentage of dwellings within 2 km or less of any district park (>5 ha to <=20 ha)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_07_policy IS $$50% or more of dwellings within 2 km or less of any district park (>5 ha to <=20 ha)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_08 IS $$Percentage of dwellings within 400 m or less distance of a neighbourhood recreation park (>0.5 ha)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_08_policy IS $$90% or more of dwellings within 400 m or less distance of a neighbourhood recreation park (>0.5 ha)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_09 IS $$Percentage of dwellings within 2.5 km or less distance of a district recreation park (>5 ha)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_09_policy IS $$90% or more of dwellings within 2.5 km or less distance of a district recreation park (>5 ha)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_10 IS $$Percentage of dwellings within 400 m or less distance of a park larger than 0.5 Ha$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_10_policy IS $$50% or more of dwellings within 400 m or less distance of a park larger than 0.5 Ha$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_11 IS $$Percentage of dwellings within 2 km or less distance of a park larger than 2 Ha$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_11_policy IS $$50% or more of dwellings within 2 km or less distance of a park larger than 2 Ha$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_12 IS $$Average distance to closest POS with a public toilet within 100 metres$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_14 IS $$Average distance to closest public open space (OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_15 IS $$Average distance to closest public open space <=0.4 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_16 IS $$Average distance to closest public open space >0.4 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_17 IS $$Average distance to closest public open space >0.5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_18 IS $$Average distance to closest public open space >1.5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_19 IS $$Average distance to closest public open space >2 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_20 IS $$Average distance to closest public open space >0.4 to <=1 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_21 IS $$Average distance to closest public open space >1 to <= 5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_22 IS $$Average distance to closest public open space >5 Ha to <=20 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_23 IS $$Average distance to closest public open space >5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_24 IS $$Average distance to closest public open space >20 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa4_indicators.os_public_25 IS $$Average distance to closest public open space with a sport facility (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_sa4_indicators.hous_02 IS $$Percentage of dwellings renting as a proportion of total$$;
COMMENT ON COLUMN li_2018_sa4_indicators.hous_04 IS $$Percentage of employed persons aged 15 and over using active transport to travel to work$$;
COMMENT ON COLUMN li_2018_sa4_indicators.hous_05 IS $$Percentage of employed persons aged 15 and over using public transport to travel to work$$;
COMMENT ON COLUMN li_2018_sa4_indicators.hous_06 IS $$Percentage of employed persons aged 15 and over using private vehicle/s to travel to work$$;
COMMENT ON COLUMN li_2018_sa4_indicators.food_12 IS $$Average count of supermarkets within 1.6km$$;
COMMENT ON COLUMN li_2018_sa4_indicators.food_13 IS $$Average count of fruit and vegetable grocers within 1.6km$$;
COMMENT ON COLUMN li_2018_sa4_indicators.food_14 IS $$Average count of specialty food stores (bakeries, butchers, fishmongers and delicatessens) within 1.6km$$;
COMMENT ON COLUMN li_2018_sa4_indicators.food_15 IS $$Average count of healther food outlets (supermarkets and fruit and vegetable grocers) within 1.6 km (OSM, or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.food_16 IS $$Average count of fast food outlets within 1.6km (OSM, or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.food_17 IS $$Average percentage of food outlets within 1.6km that provide healthier food options (ie. supermarkets and fruit and vegetable grocers; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.food_18 IS $$Average ratio of food outlets within 1.6km that provide healthier food options (ie. supermarkets and fruit and vegetable grocers) to fast food outlets; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.food_19 IS $$Average percentage of food outlets within 1.6km that provide fresh food options  (ie. supermarkets, fruit and vegetable grocers, bakeries, butchers, fishmongers and delicatessens; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.food_20 IS $$Average ratio of food outlets within 1.6km that provide fresh food options (ie. supermarkets, fruit and vegetable grocers, bakeries, butchers, fishmongers and delicatessens) to fast food outlets (OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.food_21 IS $$Percentage of dwellings with no availability of healthy or unhealthy food within 1.6km$$;
COMMENT ON COLUMN li_2018_sa4_indicators.food_22 IS $$Percentage of dwellings with no food outlets within 1.6km$$;
COMMENT ON COLUMN li_2018_sa4_indicators.food_23_hard IS $$Percentage of dwellings within 1km of a supermarket$$;
COMMENT ON COLUMN li_2018_sa4_indicators.food_24 IS $$Average distance to closest fresh food outlet (bakery, fruit and vegetables grocer, delicatessen, and fish, meat, poultry outlet; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.food_25 IS $$Average distance to closest healthy food outlet (supermarket or fruit and vegetables grocer; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.food_26 IS $$Average distance to closest fast food outlet (HLC, 2017; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.food_27 IS $$Average distance to closest dining establishment (cafe, restaurant, pub; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.community_01 IS $$Average distance to closest community centre (HLC, 2016; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.community_02 IS $$Average distance to closest cultural institution (museum, theatre, cinema, art gallery or art centre; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.alc_01 IS $$Average number of on-licenses within 400 m$$;
COMMENT ON COLUMN li_2018_sa4_indicators.alc_02 IS $$Average number of off-licenses within 800 m$$;
COMMENT ON COLUMN li_2018_sa4_indicators.alc_03 IS $$Average distance to closest bar, pub or nightclub (OSM, 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.childcare_01 IS $$Percentage of dwellings within 1600m of a children's day care which meets guidelines$$;
COMMENT ON COLUMN li_2018_sa4_indicators.childcare_02 IS $$Percentage of dwellings within 1600m of a children's day care (OSHC) which meets guidelines$$;
COMMENT ON COLUMN li_2018_sa4_indicators.health_01 IS $$Percentage of dwellings within 1600m of a GP$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_activity_centres IS $$Average distance to closest activity centre$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_alcohol_offlicence IS $$Average distance to closest offlicence alcohol outlet (HLC, 2017-19)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_alcohol_onlicence IS $$Average distance to closest onlicence alcohol outlet (HLC, 2017-19)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_alcohol_osm IS $$Average distance to closest alcohol outlet (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_all_schools IS $$Average distance to closest schools (all; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_art_centre_osm IS $$Average distance to closest art centre (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_art_gallery_osm IS $$Average distance to closest art gallery (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_bakery_osm IS $$Average distance to closest bakery (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_bar_osm IS $$Average distance to closest bar (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_cafe_osm IS $$Average distance to closest cafe (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_childcare_all IS $$Average distance to closest child care (all, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_childcare_all_exc IS $$Average distance to closest child care (exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_childcare_all_meet IS $$Average distance to closest child care (meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_childcare_oshc IS $$Average distance to closest child care (outside school hours, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_childcare_oshc_exc IS $$Average distance to closest child care (outside school hours exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_childcare_oshc_meet IS $$Average distance to closest child care (outside school hours meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_childcare_preschool IS $$Average distance to closest child care (pre-school, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_childcare_preschool_exc IS $$Average distance to closest child care (pre-school exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_childcare_preschool_meet IS $$Average distance to closest child care (pre-school meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_cinema_osm IS $$Average distance to closest cinema (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_community_centre_osm IS $$Average distance to closest community centre (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_convenience_osm IS $$Average distance to closest convenience store (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_deli_osm IS $$Average distance to closest deli (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_disability_employment IS $$Average distance to closest disabilty employment service $$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_fast_food IS $$Average distance to closest fast food (in house 2017)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_fastfood_osm IS $$Average distance to closest fast food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_food_court_osm IS $$Average distance to closest food court (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_food_health_osm IS $$Average distance to closest health food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_food_other_osm IS $$Average distance to closest other food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_fruit_veg_osm IS $$Average distance to closest fruit and veg (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_gtfs_2018_stop_30_mins_final IS $$Average distance to closest transport stop with frequent daytime service$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_gtfs_2018_stops IS $$Average distance to closest public transport stop$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_gtfs_2018_stops_bus IS $$Average distance to closest bus stop$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_gtfs_2018_stops_ferry IS $$Average distance to closest ferry terminal$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_gtfs_2018_stops_train IS $$Average distance to closest train station$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_gtfs_2018_stops_tram IS $$Average distance to closest tram stop$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_gtfs_20191008_20191205_bus_0015 IS $$Average distance to closest bus stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_gtfs_20191008_20191205_bus_0030 IS $$Average distance to closest bus stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_gtfs_20191008_20191205_bus_0045 IS $$Average distance to closest bus stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_gtfs_20191008_20191205_bus_any IS $$Average distance to closest bus stop$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_gtfs_20191008_20191205_ferry_0015 IS $$Average distance to closest ferry stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_gtfs_20191008_20191205_ferry_0030 IS $$Average distance to closest ferry stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_gtfs_20191008_20191205_ferry_0045 IS $$Average distance to closest ferry stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_gtfs_20191008_20191205_ferry_any IS $$Average distance to closest ferry stop$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_gtfs_20191008_20191205_revised_all IS $$Average distance to closest public transport stop$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_gtfs_20191008_20191205_revised_frequent30 IS $$Average distance to closest public transport stop with an average weekday service frequency of 30 minutes or less$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_gtfs_20191008_20191205_train_0015 IS $$Average distance to closest train stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_gtfs_20191008_20191205_train_0030 IS $$Average distance to closest train stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_gtfs_20191008_20191205_train_0045 IS $$Average distance to closest train stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_gtfs_20191008_20191205_train_any IS $$Average distance to closest train stop$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_gtfs_20191008_20191205_tram_0015 IS $$Average distance to closest tram stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_gtfs_20191008_20191205_tram_0030 IS $$Average distance to closest tram stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_gtfs_20191008_20191205_tram_0045 IS $$Average distance to closest tram stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_gtfs_20191008_20191205_tram_any IS $$Average distance to closest tram stop$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_hlc_2016_community_centres IS $$Average distance to closest community centre (2016)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_libraries IS $$Average distance to closest libraries (multiple sources, in-house, 2015-18)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_market_osm IS $$Average distance to closest market (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_meat_seafood_osm IS $$Average distance to closest meat / seafood (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_museum_osm IS $$Average distance to closest museum (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_newsagent_osm IS $$Average distance to closest newsagent (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_nhsd_2017_aged_care_residential IS $$Average distance to closest aged care residential service$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_nhsd_2017_dentist IS $$Average distance to closest dentist (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_nhsd_2017_gp IS $$Average distance to closest general practice/GP/doctor (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_nhsd_2017_hospital IS $$Average distance to closest hospital (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_nhsd_2017_mc_family_health IS $$Average distance to closest maternal, child and family health (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_nhsd_2017_other_community_health_care IS $$Average distance to closest 'other community health care' destination (not pharmacy or maternal and child health)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_nhsd_2017_pharmacy IS $$Average distance to closest pharmacy (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_P_12_Schools IS $$Average distance to closest schools (K - 12; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_P_12_Schools_catholic IS $$Average distance to closest schools (K - 12, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_P_12_Schools_gov IS $$Average distance to closest schools (K - 12, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_P_12_Schools_indep IS $$Average distance to closest schools (K - 12, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_petrolstation_osm IS $$Average distance to closest petrol station (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_pharmacy_osm IS $$Average distance to closest pharmacy (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_place_of_worship_osm IS $$Average distance to closest place of worship (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_playgrounds IS $$Average distance to closest playground (in house 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_postoffice_osm IS $$Average distance to post office (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_primary_schools IS $$Average distance to closest schools (primary; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_primary_schools_catholic IS $$Average distance to closest schools (primary, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_primary_schools_gov IS $$Average distance to closest schools (primary, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_primary_schools_indep IS $$Average distance to closest schools (primary, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_pub_osm IS $$Average distance to closest pub (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_public_swimming_pool_osm IS $$Average distance to closest public swimming pool (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_restaurant_osm IS $$Average distance to closest restaurant (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_secondary_schools IS $$Average distance to closest schools (secondary; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_secondary_schools_catholic IS $$Average distance to closest schools (secondary, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_secondary_schools_gov IS $$Average distance to closest schools (secondary, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_secondary_schools_indep IS $$Average distance to closest schools (secondary, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_special_schools IS $$Average distance to closest schools (special; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_supermarket IS $$Average distance to closest supermarket (in house 2017)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_supermarket_osm IS $$Average distance to closest supermarket (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_sa4_indicators.dist_m_theatre_osm IS $$Average distance to closest theatre (OSM, October 2018)$$;
```
</details>

Display information (including size and description) for this particular table: `\dt+ li_2018_sa4_indicators`
Display custom data dictionary by running `SELECT * FROM dictionary('li_2018_sa4_indicators');`


### Loading the Suburb indicator data


#### Initialise table defining variables and their data types

<details>
  <summary>
    Click to view code
  </summary>

```sql
CREATE TABLE li_2018_suburb_indicators 
(
ssc_name_2016 text PRIMARY KEY,
study_region text,
dwelling int,
person int,
sample_count int,
sample_count_per_ha float,
area_ha float,
dwellings_per_ha float,
net_dwelling float,
net_area     float,
net_density  float,
uli_city float,
uli_national float,
li_community_culture_leisure float,
li_early_years float,
li_education float,
li_health_services float,
li_sport_rec float,
li_food float,
li_convenience float,
li_pt_regular_400m float,
li_public_os_large_400m float,
li_street_connectivity_1600m float,
li_dwelling_density_1600m float,
li_sa1_30_40_housing_stress float,
li_sa1_sa3_local_employment float,
walkability_city float,
walkability_national float,
daily_living_access_1600m float,
social_infrastructure_mix float,
walk_02 float,
walk_02_policy boolean,
walk_03_policy boolean,
walk_05_policy boolean,
walk_12 float,
walk_12_policy boolean,
walk_13 float,
walk_13_policy boolean,
walk_14_policy boolean,
walk_15_policy boolean,
walk_16 float,
walk_17 float,
walk_21 float,
trans_01 float,
trans_01_policy boolean,
trans_02 float,
trans_02_policy boolean,
trans_03 float,
trans_03_policy boolean,
trans_04 float,
trans_04_policy boolean,
trans_05 float,
trans_05_policy boolean,
trans_06 float,
trans_07 float,
trans_08 float,
trans_09 float,
os_public_01 float,
os_public_02 float,
os_public_03 float,
os_public_03_policy boolean,
os_public_04 float,
os_public_04_policy boolean,
os_public_05 float,
os_public_05_policy boolean,
os_public_06 float,
os_public_06_policy boolean,
os_public_07 float,
os_public_07_policy boolean,
os_public_08 float,
os_public_08_policy boolean,
os_public_09 float,
os_public_09_policy boolean,
os_public_10 float,
os_public_10_policy boolean,
os_public_11 float,
os_public_11_policy boolean,
os_public_12 float,
os_public_14 float,
os_public_15 float,
os_public_16 float,
os_public_17 float,
os_public_18 float,
os_public_19 float,
os_public_20 float,
os_public_21 float,
os_public_22 float,
os_public_23 float,
os_public_24 float,
os_public_25 float,
hous_02 float,
hous_04 float,
hous_05 float,
hous_06 float,
food_12 float,
food_13 float,
food_14 float,
food_15 float,
food_16 float,
food_17 float,
food_18 float,
food_19 float,
food_20 float,
food_21 float,
food_22 float,
food_23_hard float,
food_24 float,
food_25 float,
food_26 float,
food_27 float,
community_01 float,
community_02 float,
alc_01 float,
alc_02 float,
alc_03 float,
childcare_01 float,
childcare_02 float,
health_01 float,
dist_m_activity_centres float,
dist_m_alcohol_offlicence float,
dist_m_alcohol_onlicence float,
dist_m_alcohol_osm float,
dist_m_all_schools float,
dist_m_art_centre_osm float,
dist_m_art_gallery_osm float,
dist_m_bakery_osm float,
dist_m_bar_osm float,
dist_m_cafe_osm float,
dist_m_childcare_all float,
dist_m_childcare_all_exc float,
dist_m_childcare_all_meet float,
dist_m_childcare_oshc float,
dist_m_childcare_oshc_exc float,
dist_m_childcare_oshc_meet float,
dist_m_childcare_preschool float,
dist_m_childcare_preschool_exc float,
dist_m_childcare_preschool_meet float,
dist_m_cinema_osm float,
dist_m_community_centre_osm float,
dist_m_convenience_osm float,
dist_m_deli_osm float,
dist_m_disability_employment float,
dist_m_fast_food float,
dist_m_fastfood_osm float,
dist_m_food_court_osm float,
dist_m_food_health_osm float,
dist_m_food_other_osm float,
dist_m_fruit_veg_osm float,
dist_m_gtfs_2018_stop_30_mins_final float,
dist_m_gtfs_2018_stops float,
dist_m_gtfs_2018_stops_bus float,
dist_m_gtfs_2018_stops_ferry float,
dist_m_gtfs_2018_stops_train float,
dist_m_gtfs_2018_stops_tram float,
dist_m_gtfs_20191008_20191205_bus_0015 float,
dist_m_gtfs_20191008_20191205_bus_0030 float,
dist_m_gtfs_20191008_20191205_bus_0045 float,
dist_m_gtfs_20191008_20191205_bus_any float,
dist_m_gtfs_20191008_20191205_ferry_0015 float,
dist_m_gtfs_20191008_20191205_ferry_0030 float,
dist_m_gtfs_20191008_20191205_ferry_0045 float,
dist_m_gtfs_20191008_20191205_ferry_any float,
dist_m_gtfs_20191008_20191205_revised_all float,
dist_m_gtfs_20191008_20191205_revised_frequent30 float,
dist_m_gtfs_20191008_20191205_train_0015 float,
dist_m_gtfs_20191008_20191205_train_0030 float,
dist_m_gtfs_20191008_20191205_train_0045 float,
dist_m_gtfs_20191008_20191205_train_any float,
dist_m_gtfs_20191008_20191205_tram_0015 float,
dist_m_gtfs_20191008_20191205_tram_0030 float,
dist_m_gtfs_20191008_20191205_tram_0045 float,
dist_m_gtfs_20191008_20191205_tram_any float,
dist_m_hlc_2016_community_centres float,
dist_m_libraries float,
dist_m_market_osm float,
dist_m_meat_seafood_osm float,
dist_m_museum_osm float,
dist_m_newsagent_osm float,
dist_m_nhsd_2017_aged_care_residential float,
dist_m_nhsd_2017_dentist float,
dist_m_nhsd_2017_gp float,
dist_m_nhsd_2017_hospital float,
dist_m_nhsd_2017_mc_family_health float,
dist_m_nhsd_2017_other_community_health_care float,
dist_m_nhsd_2017_pharmacy float,
dist_m_P_12_Schools float,
dist_m_P_12_Schools_catholic float,
dist_m_P_12_Schools_gov float,
dist_m_P_12_Schools_indep float,
dist_m_petrolstation_osm float,
dist_m_pharmacy_osm float,
dist_m_place_of_worship_osm float,
dist_m_playgrounds float,
dist_m_postoffice_osm float,
dist_m_primary_schools float,
dist_m_primary_schools_catholic float,
dist_m_primary_schools_gov float,
dist_m_primary_schools_indep float,
dist_m_pub_osm float,
dist_m_public_swimming_pool_osm float,
dist_m_restaurant_osm float,
dist_m_secondary_schools float,
dist_m_secondary_schools_catholic float,
dist_m_secondary_schools_gov float,
dist_m_secondary_schools_indep float,
dist_m_special_schools float,
dist_m_supermarket float,
dist_m_supermarket_osm float,
dist_m_theatre_osm float
);
```
</details>

### Copy the data from CSV
```sql
COPY li_2018_suburb_indicators FROM 'D:/projects/ntnl_li_2018/data/National Liveability 2018 - Final Outputs/For dissemination/hlc_ntnl_liveability_2018_ssc_2016.csv' WITH DELIMITER ',' CSV HEADER;
```

#### Optionally describe the data
<details>
  <summary>
    Click to view code
  </summary>

```sql
COMMENT ON TABLE li_2018_suburb_indicators IS $$Liveability indicators for dwellings, aggregated for Suburbs$$;
COMMENT ON COLUMN li_2018_suburb_indicators.ssc_name_2016 IS $$Suburb name$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dwelling IS $$Dwelling count (Mesh Block dwelling count > 0 was an inclusion criteria for sampling)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.person IS $$Person count (persons usually resident)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.sample_count IS $$address points in area$$;
COMMENT ON COLUMN li_2018_suburb_indicators.sample_count_per_ha IS $$address point density per hectare$$;
COMMENT ON COLUMN li_2018_suburb_indicators.area_ha IS $$Area in hectares$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dwellings_per_ha IS $$gross dwelling density$$;
COMMENT ON COLUMN li_2018_suburb_indicators.net_dwelling IS $$net dwelling density (ie. for areas classified as residential at Mesh Block level)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.net_area IS $$net area (ie. for areas classified as residential at Mesh Block level)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.net_density IS $$net density (ie. for areas classified as residential at Mesh Block level)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.uli_city IS $$Average Urban Liveability Index, relative to locations within this city$$;
COMMENT ON COLUMN li_2018_suburb_indicators.uli_national IS $$Average Urban Liveability Index, relative to locations across Australia's 21 largest cities$$;
COMMENT ON COLUMN li_2018_suburb_indicators.li_community_culture_leisure IS $$Average score for access to community, culture and leisure destinations (community centre and library within 1000m, and museum/art gallery and cinema/theater within 3200m) (/1)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.li_early_years IS $$Average score for access to child care (any meeting ACECQA recommendations) within 800 metres and childcare (outside school hours meeting recommendations) within 1600 metres (/1)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.li_education IS $$Average score for access to primary and secondary public schools within 1600 metres (/1)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.li_health_services IS $$Average score for access to health services (GP, pharmacy, maternal, child and family health care, aged care facility and other community health care) within 1000 metres (/1)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.li_sport_rec IS $$Average score for access to an area of open space with sport/recreation facilities within 1000 metres, and a public swimming pool within 1200 metres (/1)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.li_food IS $$Average score for access to a supermarket and fresh fruit and vegetables within 1000 metres, and meat/seafood within 3200 metres (/1)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.li_convenience IS $$Average score for access to convenience destinations (convenience store and petrol station within 1000 metres, and a newsagent within 3200 metres) (/1)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.li_pt_regular_400m IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 30 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_suburb_indicators.li_public_os_large_400m IS $$Percentage of dwellings < 400 m of public open space > 1.5 ha$$;
COMMENT ON COLUMN li_2018_suburb_indicators.li_street_connectivity_1600m IS $$Average local street connectivity per square kilometre$$;
COMMENT ON COLUMN li_2018_suburb_indicators.li_dwelling_density_1600m IS $$Average local dwelling density per hectare (Ha) $$;
COMMENT ON COLUMN li_2018_suburb_indicators.li_sa1_30_40_housing_stress IS $$Percentage of SA1 households with income in the bottom 40% of the income distribution spending more than 30% of household income on housing costs$$;
COMMENT ON COLUMN li_2018_suburb_indicators.li_sa1_sa3_local_employment IS $$Percentage of employed persons who live and work in the same community$$;
COMMENT ON COLUMN li_2018_suburb_indicators.walkability_city IS $$Average walkability index, combining street connectivity, dwelling density and daily living destinations, relative to locations within this city$$;
COMMENT ON COLUMN li_2018_suburb_indicators.walkability_national IS $$Average walkability index, combining street connectivity, dwelling density and daily living destinations, relative to locations across Australia's 21 largest cities$$;
COMMENT ON COLUMN li_2018_suburb_indicators.daily_living_access_1600m IS $$Average number of daily living types present, measured as a score of 0-3, with 1 point for each category of convenience store/petrol station/newsagent, PT stop, supermarket within 1600m network distance$$;
COMMENT ON COLUMN li_2018_suburb_indicators.social_infrastructure_mix IS $$Average social infrastructure mix score (/16)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.walk_02 IS $$Percentage of dwellings <1 km walking distance of an activity centre with a supermarket$$;
COMMENT ON COLUMN li_2018_suburb_indicators.walk_02_policy IS $$At least 80% of dwellings are within 1 km walking distance of an activity centre with a supermarket$$;
COMMENT ON COLUMN li_2018_suburb_indicators.walk_03_policy IS $$Area has at least 15 dwellings per net developable hectare$$;
COMMENT ON COLUMN li_2018_suburb_indicators.walk_05_policy IS $$Area has at least 26 dwellings per net developable hectare$$;
COMMENT ON COLUMN li_2018_suburb_indicators.walk_12 IS $$Percentage of dwellings with local dwelling density of 15 dwellings per hectare or greater$$;
COMMENT ON COLUMN li_2018_suburb_indicators.walk_12_policy IS $$15 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_suburb_indicators.walk_13 IS $$Percentage of dwellings with local dwelling density of 30 dwellings per hectare or greater$$;
COMMENT ON COLUMN li_2018_suburb_indicators.walk_13_policy IS $$Local dwelling density of 30 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_suburb_indicators.walk_14_policy IS $$Gross dwelling density of 15 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_suburb_indicators.walk_15_policy IS $$Gross dwelling density of 30 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_suburb_indicators.walk_16 IS $$Average distance to closest activity centre (proxy measure: supermarket within a commercial zoned Mesh Block)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.walk_17 IS $$Average pedshed ratio, defined as the area of the 400 m pedestrian network from each residential dwelling buffered by 50m divided by the radial 400 m "crow flies" area (i.e. 50.2 Ha.)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.walk_21 IS $$Average number of local living types present (see paper of Mavoa et al)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.trans_01 IS $$Percentage of dwellings with access to bus stop within 400 m, a tram stop within 600m, or a train station within 800 m$$;
COMMENT ON COLUMN li_2018_suburb_indicators.trans_01_policy IS $$95% or more of dwellings with access to bus stop within 400 m, a tram stop within 600m, or a train station within 800 m$$;
COMMENT ON COLUMN li_2018_suburb_indicators.trans_02 IS $$Percentage of dwellings with access to bus stop < 400 m$$;
COMMENT ON COLUMN li_2018_suburb_indicators.trans_02_policy IS $$95% or more of dwellings with access to bus stop < 400 m$$;
COMMENT ON COLUMN li_2018_suburb_indicators.trans_03 IS $$Percentage of dwellings < 400m walk from a neighbourhood or town centre, or a bus stop, or in a 800m walk from a railway station.$$;
COMMENT ON COLUMN li_2018_suburb_indicators.trans_03_policy IS $$60% or more of dwellings < 400m walk from a neighbourhood or town centre, or a bus stop, or in a 800m walk from a railway station.$$;
COMMENT ON COLUMN li_2018_suburb_indicators.trans_04 IS $$Percentage of dwellings < 400 metres of an existing or planned public transport stop$$;
COMMENT ON COLUMN li_2018_suburb_indicators.trans_04_policy IS $$100% of dwellings < 400 metres of an existing or planned public transport stop$$;
COMMENT ON COLUMN li_2018_suburb_indicators.trans_05 IS $$Percentage of dwellings < 400 m of a bus stop every 30 min OR < 800 m of a train station every 15 min$$;
COMMENT ON COLUMN li_2018_suburb_indicators.trans_05_policy IS $$100% of dwellings < 400 m of a bus stop every 30 min OR < 800 m of a train station every 15 min$$;
COMMENT ON COLUMN li_2018_suburb_indicators.trans_06 IS $$Percentage of dwellings < 400 m of a public transport stop with a scheduled service at least every 30 minutes between 7am and 7pm on a normal weekday (= a combined measure of proximity and frequency)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.trans_07 IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 30 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_suburb_indicators.trans_08 IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 25 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_suburb_indicators.trans_09 IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 20 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_01 IS $$Percentage of dwellings within 400 m or less distance of public open space$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_02 IS $$Percentage of dwellings < 400 m of public open space > 1.5 ha$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_03 IS $$Percentage of dwellings within 400 m or less distance of public open space$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_03_policy IS $$95% or more of dwellings within 400 m or less distance of public open space$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_04 IS $$Percentage of dwellings within 300 m or less distance of any public open space$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_04_policy IS $$100% of dwellings within 300 m or less distance of any public open space$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_05 IS $$Percentage of dwellings within 400 m or less distance of any local park (> 0.4 to <=1 ha)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_05_policy IS $$50% or more of dwellings within 400 m or less distance of any local park (> 0.4 to <=1 ha)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_06 IS $$Percentage of dwellings within 800 m or less distance of any neighbourhood park (>1 ha to <= 5ha)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_06_policy IS $$50% or more of dwellings within 800 m or less distance of any neighbourhood park (>1 ha to <= 5ha)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_07 IS $$Percentage of dwellings within 2 km or less of any district park (>5 ha to <=20 ha)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_07_policy IS $$50% or more of dwellings within 2 km or less of any district park (>5 ha to <=20 ha)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_08 IS $$Percentage of dwellings within 400 m or less distance of a neighbourhood recreation park (>0.5 ha)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_08_policy IS $$90% or more of dwellings within 400 m or less distance of a neighbourhood recreation park (>0.5 ha)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_09 IS $$Percentage of dwellings within 2.5 km or less distance of a district recreation park (>5 ha)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_09_policy IS $$90% or more of dwellings within 2.5 km or less distance of a district recreation park (>5 ha)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_10 IS $$Percentage of dwellings within 400 m or less distance of a park larger than 0.5 Ha$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_10_policy IS $$50% or more of dwellings within 400 m or less distance of a park larger than 0.5 Ha$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_11 IS $$Percentage of dwellings within 2 km or less distance of a park larger than 2 Ha$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_11_policy IS $$50% or more of dwellings within 2 km or less distance of a park larger than 2 Ha$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_12 IS $$Average distance to closest POS with a public toilet within 100 metres$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_14 IS $$Average distance to closest public open space (OSM, 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_15 IS $$Average distance to closest public open space <=0.4 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_16 IS $$Average distance to closest public open space >0.4 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_17 IS $$Average distance to closest public open space >0.5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_18 IS $$Average distance to closest public open space >1.5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_19 IS $$Average distance to closest public open space >2 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_20 IS $$Average distance to closest public open space >0.4 to <=1 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_21 IS $$Average distance to closest public open space >1 to <= 5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_22 IS $$Average distance to closest public open space >5 Ha to <=20 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_23 IS $$Average distance to closest public open space >5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_24 IS $$Average distance to closest public open space >20 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_suburb_indicators.os_public_25 IS $$Average distance to closest public open space with a sport facility (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_suburb_indicators.hous_02 IS $$Percentage of dwellings renting as a proportion of total$$;
COMMENT ON COLUMN li_2018_suburb_indicators.hous_04 IS $$Percentage of employed persons aged 15 and over using active transport to travel to work$$;
COMMENT ON COLUMN li_2018_suburb_indicators.hous_05 IS $$Percentage of employed persons aged 15 and over using public transport to travel to work$$;
COMMENT ON COLUMN li_2018_suburb_indicators.hous_06 IS $$Percentage of employed persons aged 15 and over using private vehicle/s to travel to work$$;
COMMENT ON COLUMN li_2018_suburb_indicators.food_12 IS $$Average count of supermarkets within 1.6km$$;
COMMENT ON COLUMN li_2018_suburb_indicators.food_13 IS $$Average count of fruit and vegetable grocers within 1.6km$$;
COMMENT ON COLUMN li_2018_suburb_indicators.food_14 IS $$Average count of specialty food stores (bakeries, butchers, fishmongers and delicatessens) within 1.6km$$;
COMMENT ON COLUMN li_2018_suburb_indicators.food_15 IS $$Average count of healther food outlets (supermarkets and fruit and vegetable grocers) within 1.6 km (OSM, or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.food_16 IS $$Average count of fast food outlets within 1.6km (OSM, or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.food_17 IS $$Average percentage of food outlets within 1.6km that provide healthier food options (ie. supermarkets and fruit and vegetable grocers; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.food_18 IS $$Average ratio of food outlets within 1.6km that provide healthier food options (ie. supermarkets and fruit and vegetable grocers) to fast food outlets; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.food_19 IS $$Average percentage of food outlets within 1.6km that provide fresh food options  (ie. supermarkets, fruit and vegetable grocers, bakeries, butchers, fishmongers and delicatessens; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.food_20 IS $$Average ratio of food outlets within 1.6km that provide fresh food options (ie. supermarkets, fruit and vegetable grocers, bakeries, butchers, fishmongers and delicatessens) to fast food outlets (OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.food_21 IS $$Percentage of dwellings with no availability of healthy or unhealthy food within 1.6km$$;
COMMENT ON COLUMN li_2018_suburb_indicators.food_22 IS $$Percentage of dwellings with no food outlets within 1.6km$$;
COMMENT ON COLUMN li_2018_suburb_indicators.food_23_hard IS $$Percentage of dwellings within 1km of a supermarket$$;
COMMENT ON COLUMN li_2018_suburb_indicators.food_24 IS $$Average distance to closest fresh food outlet (bakery, fruit and vegetables grocer, delicatessen, and fish, meat, poultry outlet; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.food_25 IS $$Average distance to closest healthy food outlet (supermarket or fruit and vegetables grocer; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.food_26 IS $$Average distance to closest fast food outlet (HLC, 2017; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.food_27 IS $$Average distance to closest dining establishment (cafe, restaurant, pub; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.community_01 IS $$Average distance to closest community centre (HLC, 2016; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.community_02 IS $$Average distance to closest cultural institution (museum, theatre, cinema, art gallery or art centre; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.alc_01 IS $$Average number of on-licenses within 400 m$$;
COMMENT ON COLUMN li_2018_suburb_indicators.alc_02 IS $$Average number of off-licenses within 800 m$$;
COMMENT ON COLUMN li_2018_suburb_indicators.alc_03 IS $$Average distance to closest bar, pub or nightclub (OSM, 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.childcare_01 IS $$Percentage of dwellings within 1600m of a children's day care which meets guidelines$$;
COMMENT ON COLUMN li_2018_suburb_indicators.childcare_02 IS $$Percentage of dwellings within 1600m of a children's day care (OSHC) which meets guidelines$$;
COMMENT ON COLUMN li_2018_suburb_indicators.health_01 IS $$Percentage of dwellings within 1600m of a GP$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_activity_centres IS $$Average distance to closest activity centre$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_alcohol_offlicence IS $$Average distance to closest offlicence alcohol outlet (HLC, 2017-19)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_alcohol_onlicence IS $$Average distance to closest onlicence alcohol outlet (HLC, 2017-19)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_alcohol_osm IS $$Average distance to closest alcohol outlet (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_all_schools IS $$Average distance to closest schools (all; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_art_centre_osm IS $$Average distance to closest art centre (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_art_gallery_osm IS $$Average distance to closest art gallery (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_bakery_osm IS $$Average distance to closest bakery (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_bar_osm IS $$Average distance to closest bar (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_cafe_osm IS $$Average distance to closest cafe (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_childcare_all IS $$Average distance to closest child care (all, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_childcare_all_exc IS $$Average distance to closest child care (exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_childcare_all_meet IS $$Average distance to closest child care (meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_childcare_oshc IS $$Average distance to closest child care (outside school hours, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_childcare_oshc_exc IS $$Average distance to closest child care (outside school hours exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_childcare_oshc_meet IS $$Average distance to closest child care (outside school hours meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_childcare_preschool IS $$Average distance to closest child care (pre-school, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_childcare_preschool_exc IS $$Average distance to closest child care (pre-school exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_childcare_preschool_meet IS $$Average distance to closest child care (pre-school meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_cinema_osm IS $$Average distance to closest cinema (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_community_centre_osm IS $$Average distance to closest community centre (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_convenience_osm IS $$Average distance to closest convenience store (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_deli_osm IS $$Average distance to closest deli (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_disability_employment IS $$Average distance to closest disabilty employment service $$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_fast_food IS $$Average distance to closest fast food (in house 2017)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_fastfood_osm IS $$Average distance to closest fast food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_food_court_osm IS $$Average distance to closest food court (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_food_health_osm IS $$Average distance to closest health food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_food_other_osm IS $$Average distance to closest other food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_fruit_veg_osm IS $$Average distance to closest fruit and veg (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_gtfs_2018_stop_30_mins_final IS $$Average distance to closest transport stop with frequent daytime service$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_gtfs_2018_stops IS $$Average distance to closest public transport stop$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_gtfs_2018_stops_bus IS $$Average distance to closest bus stop$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_gtfs_2018_stops_ferry IS $$Average distance to closest ferry terminal$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_gtfs_2018_stops_train IS $$Average distance to closest train station$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_gtfs_2018_stops_tram IS $$Average distance to closest tram stop$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_gtfs_20191008_20191205_bus_0015 IS $$Average distance to closest bus stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_gtfs_20191008_20191205_bus_0030 IS $$Average distance to closest bus stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_gtfs_20191008_20191205_bus_0045 IS $$Average distance to closest bus stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_gtfs_20191008_20191205_bus_any IS $$Average distance to closest bus stop$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_gtfs_20191008_20191205_ferry_0015 IS $$Average distance to closest ferry stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_gtfs_20191008_20191205_ferry_0030 IS $$Average distance to closest ferry stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_gtfs_20191008_20191205_ferry_0045 IS $$Average distance to closest ferry stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_gtfs_20191008_20191205_ferry_any IS $$Average distance to closest ferry stop$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_gtfs_20191008_20191205_revised_all IS $$Average distance to closest public transport stop$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_gtfs_20191008_20191205_revised_frequent30 IS $$Average distance to closest public transport stop with an average weekday service frequency of 30 minutes or less$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_gtfs_20191008_20191205_train_0015 IS $$Average distance to closest train stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_gtfs_20191008_20191205_train_0030 IS $$Average distance to closest train stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_gtfs_20191008_20191205_train_0045 IS $$Average distance to closest train stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_gtfs_20191008_20191205_train_any IS $$Average distance to closest train stop$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_gtfs_20191008_20191205_tram_0015 IS $$Average distance to closest tram stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_gtfs_20191008_20191205_tram_0030 IS $$Average distance to closest tram stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_gtfs_20191008_20191205_tram_0045 IS $$Average distance to closest tram stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_gtfs_20191008_20191205_tram_any IS $$Average distance to closest tram stop$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_hlc_2016_community_centres IS $$Average distance to closest community centre (2016)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_libraries IS $$Average distance to closest libraries (multiple sources, in-house, 2015-18)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_market_osm IS $$Average distance to closest market (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_meat_seafood_osm IS $$Average distance to closest meat / seafood (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_museum_osm IS $$Average distance to closest museum (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_newsagent_osm IS $$Average distance to closest newsagent (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_nhsd_2017_aged_care_residential IS $$Average distance to closest aged care residential service$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_nhsd_2017_dentist IS $$Average distance to closest dentist (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_nhsd_2017_gp IS $$Average distance to closest general practice/GP/doctor (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_nhsd_2017_hospital IS $$Average distance to closest hospital (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_nhsd_2017_mc_family_health IS $$Average distance to closest maternal, child and family health (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_nhsd_2017_other_community_health_care IS $$Average distance to closest 'other community health care' destination (not pharmacy or maternal and child health)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_nhsd_2017_pharmacy IS $$Average distance to closest pharmacy (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_P_12_Schools IS $$Average distance to closest schools (K - 12; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_P_12_Schools_catholic IS $$Average distance to closest schools (K - 12, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_P_12_Schools_gov IS $$Average distance to closest schools (K - 12, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_P_12_Schools_indep IS $$Average distance to closest schools (K - 12, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_petrolstation_osm IS $$Average distance to closest petrol station (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_pharmacy_osm IS $$Average distance to closest pharmacy (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_place_of_worship_osm IS $$Average distance to closest place of worship (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_playgrounds IS $$Average distance to closest playground (in house 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_postoffice_osm IS $$Average distance to post office (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_primary_schools IS $$Average distance to closest schools (primary; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_primary_schools_catholic IS $$Average distance to closest schools (primary, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_primary_schools_gov IS $$Average distance to closest schools (primary, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_primary_schools_indep IS $$Average distance to closest schools (primary, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_pub_osm IS $$Average distance to closest pub (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_public_swimming_pool_osm IS $$Average distance to closest public swimming pool (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_restaurant_osm IS $$Average distance to closest restaurant (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_secondary_schools IS $$Average distance to closest schools (secondary; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_secondary_schools_catholic IS $$Average distance to closest schools (secondary, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_secondary_schools_gov IS $$Average distance to closest schools (secondary, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_secondary_schools_indep IS $$Average distance to closest schools (secondary, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_special_schools IS $$Average distance to closest schools (special; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_supermarket IS $$Average distance to closest supermarket (in house 2017)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_supermarket_osm IS $$Average distance to closest supermarket (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_suburb_indicators.dist_m_theatre_osm IS $$Average distance to closest theatre (OSM, October 2018)$$;

```
</details>

Display information (including size and description) for this particular table: `\dt+ li_2018_suburb_indicators`
Display custom data dictionary by running `SELECT * FROM dictionary('li_2018_suburb_indicators');`


### Loading the Local Government Area indicator data


#### Initialise table defining variables and their data types

<details>
  <summary>
    Click to view code
  </summary>

```sql
CREATE TABLE li_2018_lga_indicators 
(
lga_name_2016 text PRIMARY KEY,
study_region text,
dwelling int,
person int,
sample_count int,
sample_count_per_ha float,
area_ha float,
dwellings_per_ha float,
net_dwelling float,
net_area     float,
net_density  float,
uli_city float,
uli_national float,
li_community_culture_leisure float,
li_early_years float,
li_education float,
li_health_services float,
li_sport_rec float,
li_food float,
li_convenience float,
li_pt_regular_400m float,
li_public_os_large_400m float,
li_street_connectivity_1600m float,
li_dwelling_density_1600m float,
li_sa1_30_40_housing_stress float,
li_sa1_sa3_local_employment float,
walkability_city float,
walkability_national float,
daily_living_access_1600m float,
social_infrastructure_mix float,
walk_02 float,
walk_02_policy boolean,
walk_03_policy boolean,
walk_05_policy boolean,
walk_12 float,
walk_12_policy boolean,
walk_13 float,
walk_13_policy boolean,
walk_14_policy boolean,
walk_15_policy boolean,
walk_16 float,
walk_17 float,
walk_21 float,
trans_01 float,
trans_01_policy boolean,
trans_02 float,
trans_02_policy boolean,
trans_03 float,
trans_03_policy boolean,
trans_04 float,
trans_04_policy boolean,
trans_05 float,
trans_05_policy boolean,
trans_06 float,
trans_07 float,
trans_08 float,
trans_09 float,
os_public_01 float,
os_public_02 float,
os_public_03 float,
os_public_03_policy boolean,
os_public_04 float,
os_public_04_policy boolean,
os_public_05 float,
os_public_05_policy boolean,
os_public_06 float,
os_public_06_policy boolean,
os_public_07 float,
os_public_07_policy boolean,
os_public_08 float,
os_public_08_policy boolean,
os_public_09 float,
os_public_09_policy boolean,
os_public_10 float,
os_public_10_policy boolean,
os_public_11 float,
os_public_11_policy boolean,
os_public_12 float,
os_public_14 float,
os_public_15 float,
os_public_16 float,
os_public_17 float,
os_public_18 float,
os_public_19 float,
os_public_20 float,
os_public_21 float,
os_public_22 float,
os_public_23 float,
os_public_24 float,
os_public_25 float,
hous_02 float,
hous_04 float,
hous_05 float,
hous_06 float,
food_12 float,
food_13 float,
food_14 float,
food_15 float,
food_16 float,
food_17 float,
food_18 float,
food_19 float,
food_20 float,
food_21 float,
food_22 float,
food_23_hard float,
food_24 float,
food_25 float,
food_26 float,
food_27 float,
community_01 float,
community_02 float,
alc_01 float,
alc_02 float,
alc_03 float,
childcare_01 float,
childcare_02 float,
health_01 float,
dist_m_activity_centres float,
dist_m_alcohol_offlicence float,
dist_m_alcohol_onlicence float,
dist_m_alcohol_osm float,
dist_m_all_schools float,
dist_m_art_centre_osm float,
dist_m_art_gallery_osm float,
dist_m_bakery_osm float,
dist_m_bar_osm float,
dist_m_cafe_osm float,
dist_m_childcare_all float,
dist_m_childcare_all_exc float,
dist_m_childcare_all_meet float,
dist_m_childcare_oshc float,
dist_m_childcare_oshc_exc float,
dist_m_childcare_oshc_meet float,
dist_m_childcare_preschool float,
dist_m_childcare_preschool_exc float,
dist_m_childcare_preschool_meet float,
dist_m_cinema_osm float,
dist_m_community_centre_osm float,
dist_m_convenience_osm float,
dist_m_deli_osm float,
dist_m_disability_employment float,
dist_m_fast_food float,
dist_m_fastfood_osm float,
dist_m_food_court_osm float,
dist_m_food_health_osm float,
dist_m_food_other_osm float,
dist_m_fruit_veg_osm float,
dist_m_gtfs_2018_stop_30_mins_final float,
dist_m_gtfs_2018_stops float,
dist_m_gtfs_2018_stops_bus float,
dist_m_gtfs_2018_stops_ferry float,
dist_m_gtfs_2018_stops_train float,
dist_m_gtfs_2018_stops_tram float,
dist_m_gtfs_20191008_20191205_bus_0015 float,
dist_m_gtfs_20191008_20191205_bus_0030 float,
dist_m_gtfs_20191008_20191205_bus_0045 float,
dist_m_gtfs_20191008_20191205_bus_any float,
dist_m_gtfs_20191008_20191205_ferry_0015 float,
dist_m_gtfs_20191008_20191205_ferry_0030 float,
dist_m_gtfs_20191008_20191205_ferry_0045 float,
dist_m_gtfs_20191008_20191205_ferry_any float,
dist_m_gtfs_20191008_20191205_revised_all float,
dist_m_gtfs_20191008_20191205_revised_frequent30 float,
dist_m_gtfs_20191008_20191205_train_0015 float,
dist_m_gtfs_20191008_20191205_train_0030 float,
dist_m_gtfs_20191008_20191205_train_0045 float,
dist_m_gtfs_20191008_20191205_train_any float,
dist_m_gtfs_20191008_20191205_tram_0015 float,
dist_m_gtfs_20191008_20191205_tram_0030 float,
dist_m_gtfs_20191008_20191205_tram_0045 float,
dist_m_gtfs_20191008_20191205_tram_any float,
dist_m_hlc_2016_community_centres float,
dist_m_libraries float,
dist_m_market_osm float,
dist_m_meat_seafood_osm float,
dist_m_museum_osm float,
dist_m_newsagent_osm float,
dist_m_nhsd_2017_aged_care_residential float,
dist_m_nhsd_2017_dentist float,
dist_m_nhsd_2017_gp float,
dist_m_nhsd_2017_hospital float,
dist_m_nhsd_2017_mc_family_health float,
dist_m_nhsd_2017_other_community_health_care float,
dist_m_nhsd_2017_pharmacy float,
dist_m_P_12_Schools float,
dist_m_P_12_Schools_catholic float,
dist_m_P_12_Schools_gov float,
dist_m_P_12_Schools_indep float,
dist_m_petrolstation_osm float,
dist_m_pharmacy_osm float,
dist_m_place_of_worship_osm float,
dist_m_playgrounds float,
dist_m_postoffice_osm float,
dist_m_primary_schools float,
dist_m_primary_schools_catholic float,
dist_m_primary_schools_gov float,
dist_m_primary_schools_indep float,
dist_m_pub_osm float,
dist_m_public_swimming_pool_osm float,
dist_m_restaurant_osm float,
dist_m_secondary_schools float,
dist_m_secondary_schools_catholic float,
dist_m_secondary_schools_gov float,
dist_m_secondary_schools_indep float,
dist_m_special_schools float,
dist_m_supermarket float,
dist_m_supermarket_osm float,
dist_m_theatre_osm float
);
```
</details>

### Copy the data from CSV
```sql
COPY li_2018_lga_indicators FROM 'D:/projects/ntnl_li_2018/data/National Liveability 2018 - Final Outputs/For dissemination/hlc_ntnl_liveability_2018_lga_2016.csv' WITH DELIMITER ',' CSV HEADER;
```

#### Optionally describe the data
<details>
  <summary>
    Click to view code
  </summary>

```sql
COMMENT ON TABLE li_2018_lga_indicators IS $$Liveability indicators for dwellings, aggregated for Local Government Areas$$;
COMMENT ON COLUMN li_2018_lga_indicators.lga_name_2016 IS $$LGA name$$;
COMMENT ON COLUMN li_2018_lga_indicators.dwelling IS $$Dwelling count (Mesh Block dwelling count > 0 was an inclusion criteria for sampling)$$;
COMMENT ON COLUMN li_2018_lga_indicators.person IS $$Person count (persons usually resident)$$;
COMMENT ON COLUMN li_2018_lga_indicators.sample_count IS $$address points in area$$;
COMMENT ON COLUMN li_2018_lga_indicators.sample_count_per_ha IS $$address point density per hectare$$;
COMMENT ON COLUMN li_2018_lga_indicators.area_ha IS $$Area in hectares$$;
COMMENT ON COLUMN li_2018_lga_indicators.dwellings_per_ha IS $$gross dwelling density$$;
COMMENT ON COLUMN li_2018_lga_indicators.net_dwelling IS $$net dwelling density (ie. for areas classified as residential at Mesh Block level)$$;
COMMENT ON COLUMN li_2018_lga_indicators.net_area IS $$net area (ie. for areas classified as residential at Mesh Block level)$$;
COMMENT ON COLUMN li_2018_lga_indicators.net_density IS $$net density (ie. for areas classified as residential at Mesh Block level)$$;
COMMENT ON COLUMN li_2018_lga_indicators.uli_city IS $$Average Urban Liveability Index, relative to locations within this city$$;
COMMENT ON COLUMN li_2018_lga_indicators.uli_national IS $$Average Urban Liveability Index, relative to locations across Australia's 21 largest cities$$;
COMMENT ON COLUMN li_2018_lga_indicators.li_community_culture_leisure IS $$Average score for access to community, culture and leisure destinations (community centre and library within 1000m, and museum/art gallery and cinema/theater within 3200m) (/1)$$;
COMMENT ON COLUMN li_2018_lga_indicators.li_early_years IS $$Average score for access to child care (any meeting ACECQA recommendations) within 800 metres and childcare (outside school hours meeting recommendations) within 1600 metres (/1)$$;
COMMENT ON COLUMN li_2018_lga_indicators.li_education IS $$Average score for access to primary and secondary public schools within 1600 metres (/1)$$;
COMMENT ON COLUMN li_2018_lga_indicators.li_health_services IS $$Average score for access to health services (GP, pharmacy, maternal, child and family health care, aged care facility and other community health care) within 1000 metres (/1)$$;
COMMENT ON COLUMN li_2018_lga_indicators.li_sport_rec IS $$Average score for access to an area of open space with sport/recreation facilities within 1000 metres, and a public swimming pool within 1200 metres (/1)$$;
COMMENT ON COLUMN li_2018_lga_indicators.li_food IS $$Average score for access to a supermarket and fresh fruit and vegetables within 1000 metres, and meat/seafood within 3200 metres (/1)$$;
COMMENT ON COLUMN li_2018_lga_indicators.li_convenience IS $$Average score for access to convenience destinations (convenience store and petrol station within 1000 metres, and a newsagent within 3200 metres) (/1)$$;
COMMENT ON COLUMN li_2018_lga_indicators.li_pt_regular_400m IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 30 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_lga_indicators.li_public_os_large_400m IS $$Percentage of dwellings < 400 m of public open space > 1.5 ha$$;
COMMENT ON COLUMN li_2018_lga_indicators.li_street_connectivity_1600m IS $$Average local street connectivity per square kilometre$$;
COMMENT ON COLUMN li_2018_lga_indicators.li_dwelling_density_1600m IS $$Average local dwelling density per hectare (Ha) $$;
COMMENT ON COLUMN li_2018_lga_indicators.li_sa1_30_40_housing_stress IS $$Percentage of SA1 households with income in the bottom 40% of the income distribution spending more than 30% of household income on housing costs$$;
COMMENT ON COLUMN li_2018_lga_indicators.li_sa1_sa3_local_employment IS $$Percentage of employed persons who live and work in the same community$$;
COMMENT ON COLUMN li_2018_lga_indicators.walkability_city IS $$Average walkability index, combining street connectivity, dwelling density and daily living destinations, relative to locations within this city$$;
COMMENT ON COLUMN li_2018_lga_indicators.walkability_national IS $$Average walkability index, combining street connectivity, dwelling density and daily living destinations, relative to locations across Australia's 21 largest cities$$;
COMMENT ON COLUMN li_2018_lga_indicators.daily_living_access_1600m IS $$Average number of daily living types present, measured as a score of 0-3, with 1 point for each category of convenience store/petrol station/newsagent, PT stop, supermarket within 1600m network distance$$;
COMMENT ON COLUMN li_2018_lga_indicators.social_infrastructure_mix IS $$Average social infrastructure mix score (/16)$$;
COMMENT ON COLUMN li_2018_lga_indicators.walk_02 IS $$Percentage of dwellings <1 km walking distance of an activity centre with a supermarket$$;
COMMENT ON COLUMN li_2018_lga_indicators.walk_02_policy IS $$At least 80% of dwellings are within 1 km walking distance of an activity centre with a supermarket$$;
COMMENT ON COLUMN li_2018_lga_indicators.walk_03_policy IS $$Area has at least 15 dwellings per net developable hectare$$;
COMMENT ON COLUMN li_2018_lga_indicators.walk_05_policy IS $$Area has at least 26 dwellings per net developable hectare$$;
COMMENT ON COLUMN li_2018_lga_indicators.walk_12 IS $$Percentage of dwellings with local dwelling density of 15 dwellings per hectare or greater$$;
COMMENT ON COLUMN li_2018_lga_indicators.walk_12_policy IS $$15 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_lga_indicators.walk_13 IS $$Percentage of dwellings with local dwelling density of 30 dwellings per hectare or greater$$;
COMMENT ON COLUMN li_2018_lga_indicators.walk_13_policy IS $$Local dwelling density of 30 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_lga_indicators.walk_14_policy IS $$Gross dwelling density of 15 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_lga_indicators.walk_15_policy IS $$Gross dwelling density of 30 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_lga_indicators.walk_16 IS $$Average distance to closest activity centre (proxy measure: supermarket within a commercial zoned Mesh Block)$$;
COMMENT ON COLUMN li_2018_lga_indicators.walk_17 IS $$Average pedshed ratio, defined as the area of the 400 m pedestrian network from each residential dwelling buffered by 50m divided by the radial 400 m "crow flies" area (i.e. 50.2 Ha.)$$;
COMMENT ON COLUMN li_2018_lga_indicators.walk_21 IS $$Average number of local living types present (see paper of Mavoa et al)$$;
COMMENT ON COLUMN li_2018_lga_indicators.trans_01 IS $$Percentage of dwellings with access to bus stop within 400 m, a tram stop within 600m, or a train station within 800 m$$;
COMMENT ON COLUMN li_2018_lga_indicators.trans_01_policy IS $$95% or more of dwellings with access to bus stop within 400 m, a tram stop within 600m, or a train station within 800 m$$;
COMMENT ON COLUMN li_2018_lga_indicators.trans_02 IS $$Percentage of dwellings with access to bus stop < 400 m$$;
COMMENT ON COLUMN li_2018_lga_indicators.trans_02_policy IS $$95% or more of dwellings with access to bus stop < 400 m$$;
COMMENT ON COLUMN li_2018_lga_indicators.trans_03 IS $$Percentage of dwellings < 400m walk from a neighbourhood or town centre, or a bus stop, or in a 800m walk from a railway station.$$;
COMMENT ON COLUMN li_2018_lga_indicators.trans_03_policy IS $$60% or more of dwellings < 400m walk from a neighbourhood or town centre, or a bus stop, or in a 800m walk from a railway station.$$;
COMMENT ON COLUMN li_2018_lga_indicators.trans_04 IS $$Percentage of dwellings < 400 metres of an existing or planned public transport stop$$;
COMMENT ON COLUMN li_2018_lga_indicators.trans_04_policy IS $$100% of dwellings < 400 metres of an existing or planned public transport stop$$;
COMMENT ON COLUMN li_2018_lga_indicators.trans_05 IS $$Percentage of dwellings < 400 m of a bus stop every 30 min OR < 800 m of a train station every 15 min$$;
COMMENT ON COLUMN li_2018_lga_indicators.trans_05_policy IS $$100% of dwellings < 400 m of a bus stop every 30 min OR < 800 m of a train station every 15 min$$;
COMMENT ON COLUMN li_2018_lga_indicators.trans_06 IS $$Percentage of dwellings < 400 m of a public transport stop with a scheduled service at least every 30 minutes between 7am and 7pm on a normal weekday (= a combined measure of proximity and frequency)$$;
COMMENT ON COLUMN li_2018_lga_indicators.trans_07 IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 30 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_lga_indicators.trans_08 IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 25 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_lga_indicators.trans_09 IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 20 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_01 IS $$Percentage of dwellings within 400 m or less distance of public open space$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_02 IS $$Percentage of dwellings < 400 m of public open space > 1.5 ha$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_03 IS $$Percentage of dwellings within 400 m or less distance of public open space$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_03_policy IS $$95% or more of dwellings within 400 m or less distance of public open space$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_04 IS $$Percentage of dwellings within 300 m or less distance of any public open space$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_04_policy IS $$100% of dwellings within 300 m or less distance of any public open space$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_05 IS $$Percentage of dwellings within 400 m or less distance of any local park (> 0.4 to <=1 ha)$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_05_policy IS $$50% or more of dwellings within 400 m or less distance of any local park (> 0.4 to <=1 ha)$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_06 IS $$Percentage of dwellings within 800 m or less distance of any neighbourhood park (>1 ha to <= 5ha)$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_06_policy IS $$50% or more of dwellings within 800 m or less distance of any neighbourhood park (>1 ha to <= 5ha)$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_07 IS $$Percentage of dwellings within 2 km or less of any district park (>5 ha to <=20 ha)$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_07_policy IS $$50% or more of dwellings within 2 km or less of any district park (>5 ha to <=20 ha)$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_08 IS $$Percentage of dwellings within 400 m or less distance of a neighbourhood recreation park (>0.5 ha)$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_08_policy IS $$90% or more of dwellings within 400 m or less distance of a neighbourhood recreation park (>0.5 ha)$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_09 IS $$Percentage of dwellings within 2.5 km or less distance of a district recreation park (>5 ha)$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_09_policy IS $$90% or more of dwellings within 2.5 km or less distance of a district recreation park (>5 ha)$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_10 IS $$Percentage of dwellings within 400 m or less distance of a park larger than 0.5 Ha$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_10_policy IS $$50% or more of dwellings within 400 m or less distance of a park larger than 0.5 Ha$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_11 IS $$Percentage of dwellings within 2 km or less distance of a park larger than 2 Ha$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_11_policy IS $$50% or more of dwellings within 2 km or less distance of a park larger than 2 Ha$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_12 IS $$Average distance to closest POS with a public toilet within 100 metres$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_14 IS $$Average distance to closest public open space (OSM, 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_15 IS $$Average distance to closest public open space <=0.4 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_16 IS $$Average distance to closest public open space >0.4 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_17 IS $$Average distance to closest public open space >0.5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_18 IS $$Average distance to closest public open space >1.5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_19 IS $$Average distance to closest public open space >2 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_20 IS $$Average distance to closest public open space >0.4 to <=1 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_21 IS $$Average distance to closest public open space >1 to <= 5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_22 IS $$Average distance to closest public open space >5 Ha to <=20 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_23 IS $$Average distance to closest public open space >5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_24 IS $$Average distance to closest public open space >20 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_lga_indicators.os_public_25 IS $$Average distance to closest public open space with a sport facility (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_lga_indicators.hous_02 IS $$Percentage of dwellings renting as a proportion of total$$;
COMMENT ON COLUMN li_2018_lga_indicators.hous_04 IS $$Percentage of employed persons aged 15 and over using active transport to travel to work$$;
COMMENT ON COLUMN li_2018_lga_indicators.hous_05 IS $$Percentage of employed persons aged 15 and over using public transport to travel to work$$;
COMMENT ON COLUMN li_2018_lga_indicators.hous_06 IS $$Percentage of employed persons aged 15 and over using private vehicle/s to travel to work$$;
COMMENT ON COLUMN li_2018_lga_indicators.food_12 IS $$Average count of supermarkets within 1.6km$$;
COMMENT ON COLUMN li_2018_lga_indicators.food_13 IS $$Average count of fruit and vegetable grocers within 1.6km$$;
COMMENT ON COLUMN li_2018_lga_indicators.food_14 IS $$Average count of specialty food stores (bakeries, butchers, fishmongers and delicatessens) within 1.6km$$;
COMMENT ON COLUMN li_2018_lga_indicators.food_15 IS $$Average count of healther food outlets (supermarkets and fruit and vegetable grocers) within 1.6 km (OSM, or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_lga_indicators.food_16 IS $$Average count of fast food outlets within 1.6km (OSM, or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_lga_indicators.food_17 IS $$Average percentage of food outlets within 1.6km that provide healthier food options (ie. supermarkets and fruit and vegetable grocers; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_lga_indicators.food_18 IS $$Average ratio of food outlets within 1.6km that provide healthier food options (ie. supermarkets and fruit and vegetable grocers) to fast food outlets; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_lga_indicators.food_19 IS $$Average percentage of food outlets within 1.6km that provide fresh food options  (ie. supermarkets, fruit and vegetable grocers, bakeries, butchers, fishmongers and delicatessens; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_lga_indicators.food_20 IS $$Average ratio of food outlets within 1.6km that provide fresh food options (ie. supermarkets, fruit and vegetable grocers, bakeries, butchers, fishmongers and delicatessens) to fast food outlets (OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_lga_indicators.food_21 IS $$Percentage of dwellings with no availability of healthy or unhealthy food within 1.6km$$;
COMMENT ON COLUMN li_2018_lga_indicators.food_22 IS $$Percentage of dwellings with no food outlets within 1.6km$$;
COMMENT ON COLUMN li_2018_lga_indicators.food_23_hard IS $$Percentage of dwellings within 1km of a supermarket$$;
COMMENT ON COLUMN li_2018_lga_indicators.food_24 IS $$Average distance to closest fresh food outlet (bakery, fruit and vegetables grocer, delicatessen, and fish, meat, poultry outlet; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.food_25 IS $$Average distance to closest healthy food outlet (supermarket or fruit and vegetables grocer; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.food_26 IS $$Average distance to closest fast food outlet (HLC, 2017; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.food_27 IS $$Average distance to closest dining establishment (cafe, restaurant, pub; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.community_01 IS $$Average distance to closest community centre (HLC, 2016; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.community_02 IS $$Average distance to closest cultural institution (museum, theatre, cinema, art gallery or art centre; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.alc_01 IS $$Average number of on-licenses within 400 m$$;
COMMENT ON COLUMN li_2018_lga_indicators.alc_02 IS $$Average number of off-licenses within 800 m$$;
COMMENT ON COLUMN li_2018_lga_indicators.alc_03 IS $$Average distance to closest bar, pub or nightclub (OSM, 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.childcare_01 IS $$Percentage of dwellings within 1600m of a children's day care which meets guidelines$$;
COMMENT ON COLUMN li_2018_lga_indicators.childcare_02 IS $$Percentage of dwellings within 1600m of a children's day care (OSHC) which meets guidelines$$;
COMMENT ON COLUMN li_2018_lga_indicators.health_01 IS $$Percentage of dwellings within 1600m of a GP$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_activity_centres IS $$Average distance to closest activity centre$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_alcohol_offlicence IS $$Average distance to closest offlicence alcohol outlet (HLC, 2017-19)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_alcohol_onlicence IS $$Average distance to closest onlicence alcohol outlet (HLC, 2017-19)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_alcohol_osm IS $$Average distance to closest alcohol outlet (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_all_schools IS $$Average distance to closest schools (all; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_art_centre_osm IS $$Average distance to closest art centre (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_art_gallery_osm IS $$Average distance to closest art gallery (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_bakery_osm IS $$Average distance to closest bakery (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_bar_osm IS $$Average distance to closest bar (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_cafe_osm IS $$Average distance to closest cafe (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_childcare_all IS $$Average distance to closest child care (all, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_childcare_all_exc IS $$Average distance to closest child care (exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_childcare_all_meet IS $$Average distance to closest child care (meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_childcare_oshc IS $$Average distance to closest child care (outside school hours, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_childcare_oshc_exc IS $$Average distance to closest child care (outside school hours exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_childcare_oshc_meet IS $$Average distance to closest child care (outside school hours meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_childcare_preschool IS $$Average distance to closest child care (pre-school, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_childcare_preschool_exc IS $$Average distance to closest child care (pre-school exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_childcare_preschool_meet IS $$Average distance to closest child care (pre-school meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_cinema_osm IS $$Average distance to closest cinema (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_community_centre_osm IS $$Average distance to closest community centre (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_convenience_osm IS $$Average distance to closest convenience store (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_deli_osm IS $$Average distance to closest deli (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_disability_employment IS $$Average distance to closest disabilty employment service $$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_fast_food IS $$Average distance to closest fast food (in house 2017)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_fastfood_osm IS $$Average distance to closest fast food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_food_court_osm IS $$Average distance to closest food court (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_food_health_osm IS $$Average distance to closest health food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_food_other_osm IS $$Average distance to closest other food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_fruit_veg_osm IS $$Average distance to closest fruit and veg (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_gtfs_2018_stop_30_mins_final IS $$Average distance to closest transport stop with frequent daytime service$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_gtfs_2018_stops IS $$Average distance to closest public transport stop$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_gtfs_2018_stops_bus IS $$Average distance to closest bus stop$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_gtfs_2018_stops_ferry IS $$Average distance to closest ferry terminal$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_gtfs_2018_stops_train IS $$Average distance to closest train station$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_gtfs_2018_stops_tram IS $$Average distance to closest tram stop$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_gtfs_20191008_20191205_bus_0015 IS $$Average distance to closest bus stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_gtfs_20191008_20191205_bus_0030 IS $$Average distance to closest bus stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_gtfs_20191008_20191205_bus_0045 IS $$Average distance to closest bus stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_gtfs_20191008_20191205_bus_any IS $$Average distance to closest bus stop$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_gtfs_20191008_20191205_ferry_0015 IS $$Average distance to closest ferry stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_gtfs_20191008_20191205_ferry_0030 IS $$Average distance to closest ferry stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_gtfs_20191008_20191205_ferry_0045 IS $$Average distance to closest ferry stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_gtfs_20191008_20191205_ferry_any IS $$Average distance to closest ferry stop$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_gtfs_20191008_20191205_revised_all IS $$Average distance to closest public transport stop$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_gtfs_20191008_20191205_revised_frequent30 IS $$Average distance to closest public transport stop with an average weekday service frequency of 30 minutes or less$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_gtfs_20191008_20191205_train_0015 IS $$Average distance to closest train stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_gtfs_20191008_20191205_train_0030 IS $$Average distance to closest train stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_gtfs_20191008_20191205_train_0045 IS $$Average distance to closest train stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_gtfs_20191008_20191205_train_any IS $$Average distance to closest train stop$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_gtfs_20191008_20191205_tram_0015 IS $$Average distance to closest tram stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_gtfs_20191008_20191205_tram_0030 IS $$Average distance to closest tram stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_gtfs_20191008_20191205_tram_0045 IS $$Average distance to closest tram stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_gtfs_20191008_20191205_tram_any IS $$Average distance to closest tram stop$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_hlc_2016_community_centres IS $$Average distance to closest community centre (2016)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_libraries IS $$Average distance to closest libraries (multiple sources, in-house, 2015-18)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_market_osm IS $$Average distance to closest market (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_meat_seafood_osm IS $$Average distance to closest meat / seafood (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_museum_osm IS $$Average distance to closest museum (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_newsagent_osm IS $$Average distance to closest newsagent (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_nhsd_2017_aged_care_residential IS $$Average distance to closest aged care residential service$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_nhsd_2017_dentist IS $$Average distance to closest dentist (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_nhsd_2017_gp IS $$Average distance to closest general practice/GP/doctor (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_nhsd_2017_hospital IS $$Average distance to closest hospital (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_nhsd_2017_mc_family_health IS $$Average distance to closest maternal, child and family health (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_nhsd_2017_other_community_health_care IS $$Average distance to closest 'other community health care' destination (not pharmacy or maternal and child health)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_nhsd_2017_pharmacy IS $$Average distance to closest pharmacy (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_P_12_Schools IS $$Average distance to closest schools (K - 12; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_P_12_Schools_catholic IS $$Average distance to closest schools (K - 12, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_P_12_Schools_gov IS $$Average distance to closest schools (K - 12, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_P_12_Schools_indep IS $$Average distance to closest schools (K - 12, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_petrolstation_osm IS $$Average distance to closest petrol station (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_pharmacy_osm IS $$Average distance to closest pharmacy (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_place_of_worship_osm IS $$Average distance to closest place of worship (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_playgrounds IS $$Average distance to closest playground (in house 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_postoffice_osm IS $$Average distance to post office (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_primary_schools IS $$Average distance to closest schools (primary; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_primary_schools_catholic IS $$Average distance to closest schools (primary, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_primary_schools_gov IS $$Average distance to closest schools (primary, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_primary_schools_indep IS $$Average distance to closest schools (primary, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_pub_osm IS $$Average distance to closest pub (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_public_swimming_pool_osm IS $$Average distance to closest public swimming pool (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_restaurant_osm IS $$Average distance to closest restaurant (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_secondary_schools IS $$Average distance to closest schools (secondary; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_secondary_schools_catholic IS $$Average distance to closest schools (secondary, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_secondary_schools_gov IS $$Average distance to closest schools (secondary, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_secondary_schools_indep IS $$Average distance to closest schools (secondary, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_special_schools IS $$Average distance to closest schools (special; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_supermarket IS $$Average distance to closest supermarket (in house 2017)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_supermarket_osm IS $$Average distance to closest supermarket (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_lga_indicators.dist_m_theatre_osm IS $$Average distance to closest theatre (OSM, October 2018)$$;
```
</details>

Display information (including size and description) for this particular table: `\dt+ li_2018_lga_indicators`
Display custom data dictionary by running `SELECT * FROM dictionary('li_2018_lga_indicators');`



### Loading the city indicator data (overall city summaries)

#### Initialise table defining variables and their data types

<details>
  <summary>
    Click to view code
  </summary>

```sql
CREATE TABLE li_2018_city_indicators 
(
study_region text PRIMARY KEY,
dwelling int,
person int,
sample_count int,
sample_count_per_ha float,
area_ha float,
dwellings_per_ha float,
net_dwelling float,
net_area     float,
net_density  float,
uli_city float,
uli_national float,
li_community_culture_leisure float,
li_early_years float,
li_education float,
li_health_services float,
li_sport_rec float,
li_food float,
li_convenience float,
li_pt_regular_400m float,
li_public_os_large_400m float,
li_street_connectivity_1600m float,
li_dwelling_density_1600m float,
li_sa1_30_40_housing_stress float,
li_sa1_sa3_local_employment float,
walkability_city float,
walkability_national float,
daily_living_access_1600m float,
social_infrastructure_mix float,
walk_02 float,
walk_02_policy boolean,
walk_03_policy boolean,
walk_05_policy boolean,
walk_12 float,
walk_12_policy boolean,
walk_13 float,
walk_13_policy boolean,
walk_14_policy boolean,
walk_15_policy boolean,
walk_16 float,
walk_17 float,
walk_21 float,
trans_01 float,
trans_01_policy boolean,
trans_02 float,
trans_02_policy boolean,
trans_03 float,
trans_03_policy boolean,
trans_04 float,
trans_04_policy boolean,
trans_05 float,
trans_05_policy boolean,
trans_06 float,
trans_07 float,
trans_08 float,
trans_09 float,
os_public_01 float,
os_public_02 float,
os_public_03 float,
os_public_03_policy boolean,
os_public_04 float,
os_public_04_policy boolean,
os_public_05 float,
os_public_05_policy boolean,
os_public_06 float,
os_public_06_policy boolean,
os_public_07 float,
os_public_07_policy boolean,
os_public_08 float,
os_public_08_policy boolean,
os_public_09 float,
os_public_09_policy boolean,
os_public_10 float,
os_public_10_policy boolean,
os_public_11 float,
os_public_11_policy boolean,
os_public_12 float,
os_public_14 float,
os_public_15 float,
os_public_16 float,
os_public_17 float,
os_public_18 float,
os_public_19 float,
os_public_20 float,
os_public_21 float,
os_public_22 float,
os_public_23 float,
os_public_24 float,
os_public_25 float,
hous_02 float,
hous_04 float,
hous_05 float,
hous_06 float,
food_12 float,
food_13 float,
food_14 float,
food_15 float,
food_16 float,
food_17 float,
food_18 float,
food_19 float,
food_20 float,
food_21 float,
food_22 float,
food_23_hard float,
food_24 float,
food_25 float,
food_26 float,
food_27 float,
community_01 float,
community_02 float,
alc_01 float,
alc_02 float,
alc_03 float,
childcare_01 float,
childcare_02 float,
health_01 float,
dist_m_activity_centres float,
dist_m_alcohol_offlicence float,
dist_m_alcohol_onlicence float,
dist_m_alcohol_osm float,
dist_m_all_schools float,
dist_m_art_centre_osm float,
dist_m_art_gallery_osm float,
dist_m_bakery_osm float,
dist_m_bar_osm float,
dist_m_cafe_osm float,
dist_m_childcare_all float,
dist_m_childcare_all_exc float,
dist_m_childcare_all_meet float,
dist_m_childcare_oshc float,
dist_m_childcare_oshc_exc float,
dist_m_childcare_oshc_meet float,
dist_m_childcare_preschool float,
dist_m_childcare_preschool_exc float,
dist_m_childcare_preschool_meet float,
dist_m_cinema_osm float,
dist_m_community_centre_osm float,
dist_m_convenience_osm float,
dist_m_deli_osm float,
dist_m_disability_employment float,
dist_m_fast_food float,
dist_m_fastfood_osm float,
dist_m_food_court_osm float,
dist_m_food_health_osm float,
dist_m_food_other_osm float,
dist_m_fruit_veg_osm float,
dist_m_gtfs_2018_stop_30_mins_final float,
dist_m_gtfs_2018_stops float,
dist_m_gtfs_2018_stops_bus float,
dist_m_gtfs_2018_stops_ferry float,
dist_m_gtfs_2018_stops_train float,
dist_m_gtfs_2018_stops_tram float,
dist_m_gtfs_20191008_20191205_bus_0015 float,
dist_m_gtfs_20191008_20191205_bus_0030 float,
dist_m_gtfs_20191008_20191205_bus_0045 float,
dist_m_gtfs_20191008_20191205_bus_any float,
dist_m_gtfs_20191008_20191205_ferry_0015 float,
dist_m_gtfs_20191008_20191205_ferry_0030 float,
dist_m_gtfs_20191008_20191205_ferry_0045 float,
dist_m_gtfs_20191008_20191205_ferry_any float,
dist_m_gtfs_20191008_20191205_revised_all float,
dist_m_gtfs_20191008_20191205_revised_frequent30 float,
dist_m_gtfs_20191008_20191205_train_0015 float,
dist_m_gtfs_20191008_20191205_train_0030 float,
dist_m_gtfs_20191008_20191205_train_0045 float,
dist_m_gtfs_20191008_20191205_train_any float,
dist_m_gtfs_20191008_20191205_tram_0015 float,
dist_m_gtfs_20191008_20191205_tram_0030 float,
dist_m_gtfs_20191008_20191205_tram_0045 float,
dist_m_gtfs_20191008_20191205_tram_any float,
dist_m_hlc_2016_community_centres float,
dist_m_libraries float,
dist_m_market_osm float,
dist_m_meat_seafood_osm float,
dist_m_museum_osm float,
dist_m_newsagent_osm float,
dist_m_nhsd_2017_aged_care_residential float,
dist_m_nhsd_2017_dentist float,
dist_m_nhsd_2017_gp float,
dist_m_nhsd_2017_hospital float,
dist_m_nhsd_2017_mc_family_health float,
dist_m_nhsd_2017_other_community_health_care float,
dist_m_nhsd_2017_pharmacy float,
dist_m_P_12_Schools float,
dist_m_P_12_Schools_catholic float,
dist_m_P_12_Schools_gov float,
dist_m_P_12_Schools_indep float,
dist_m_petrolstation_osm float,
dist_m_pharmacy_osm float,
dist_m_place_of_worship_osm float,
dist_m_playgrounds float,
dist_m_postoffice_osm float,
dist_m_primary_schools float,
dist_m_primary_schools_catholic float,
dist_m_primary_schools_gov float,
dist_m_primary_schools_indep float,
dist_m_pub_osm float,
dist_m_public_swimming_pool_osm float,
dist_m_restaurant_osm float,
dist_m_secondary_schools float,
dist_m_secondary_schools_catholic float,
dist_m_secondary_schools_gov float,
dist_m_secondary_schools_indep float,
dist_m_special_schools float,
dist_m_supermarket float,
dist_m_supermarket_osm float,
dist_m_theatre_osm float
);
```
</details>

### Copy the data from CSV
```sql
COPY li_2018_city_indicators FROM 'D:/projects/ntnl_li_2018/data/National Liveability 2018 - Final Outputs/For dissemination/hlc_ntnl_liveability_2018_region.csv' WITH DELIMITER ',' CSV HEADER;
```

#### Optionally describe the data

<details>
  <summary>
    Click to view code
  </summary>

```sql
COMMENT ON TABLE li_2018_city_indicators IS $$Liveability indicators for dwellings, aggregated for cities$$;
COMMENT ON COLUMN li_2018_city_indicators.study_region IS $$City name$$;
COMMENT ON COLUMN li_2018_city_indicators.dwelling IS $$Dwelling count (Mesh Block dwelling count > 0 was an inclusion criteria for sampling)$$;
COMMENT ON COLUMN li_2018_city_indicators.person IS $$Person count (persons usually resident)$$;
COMMENT ON COLUMN li_2018_city_indicators.sample_count IS $$address points in area$$;
COMMENT ON COLUMN li_2018_city_indicators.sample_count_per_ha IS $$address point density per hectare$$;
COMMENT ON COLUMN li_2018_city_indicators.area_ha IS $$Area in hectares$$;
COMMENT ON COLUMN li_2018_city_indicators.dwellings_per_ha IS $$gross dwelling density$$;
COMMENT ON COLUMN li_2018_city_indicators.net_dwelling IS $$net dwelling density (ie. for areas classified as residential at Mesh Block level)$$;
COMMENT ON COLUMN li_2018_city_indicators.net_area IS $$net area (ie. for areas classified as residential at Mesh Block level)$$;
COMMENT ON COLUMN li_2018_city_indicators.net_density IS $$net density (ie. for areas classified as residential at Mesh Block level)$$;
COMMENT ON COLUMN li_2018_city_indicators.uli_city IS $$Average Urban Liveability Index, relative to locations within this city$$;
COMMENT ON COLUMN li_2018_city_indicators.uli_national IS $$Average Urban Liveability Index, relative to locations across Australia's 21 largest cities$$;
COMMENT ON COLUMN li_2018_city_indicators.li_community_culture_leisure IS $$Average score for access to community, culture and leisure destinations (community centre and library within 1000m, and museum/art gallery and cinema/theater within 3200m) (/1)$$;
COMMENT ON COLUMN li_2018_city_indicators.li_early_years IS $$Average score for access to child care (any meeting ACECQA recommendations) within 800 metres and childcare (outside school hours meeting recommendations) within 1600 metres (/1)$$;
COMMENT ON COLUMN li_2018_city_indicators.li_education IS $$Average score for access to primary and secondary public schools within 1600 metres (/1)$$;
COMMENT ON COLUMN li_2018_city_indicators.li_health_services IS $$Average score for access to health services (GP, pharmacy, maternal, child and family health care, aged care facility and other community health care) within 1000 metres (/1)$$;
COMMENT ON COLUMN li_2018_city_indicators.li_sport_rec IS $$Average score for access to an area of open space with sport/recreation facilities within 1000 metres, and a public swimming pool within 1200 metres (/1)$$;
COMMENT ON COLUMN li_2018_city_indicators.li_food IS $$Average score for access to a supermarket and fresh fruit and vegetables within 1000 metres, and meat/seafood within 3200 metres (/1)$$;
COMMENT ON COLUMN li_2018_city_indicators.li_convenience IS $$Average score for access to convenience destinations (convenience store and petrol station within 1000 metres, and a newsagent within 3200 metres) (/1)$$;
COMMENT ON COLUMN li_2018_city_indicators.li_pt_regular_400m IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 30 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_city_indicators.li_public_os_large_400m IS $$Percentage of dwellings < 400 m of public open space > 1.5 ha$$;
COMMENT ON COLUMN li_2018_city_indicators.li_street_connectivity_1600m IS $$Average local street connectivity per square kilometre$$;
COMMENT ON COLUMN li_2018_city_indicators.li_dwelling_density_1600m IS $$Average local dwelling density per hectare (Ha) $$;
COMMENT ON COLUMN li_2018_city_indicators.li_sa1_30_40_housing_stress IS $$Percentage of SA1 households with income in the bottom 40% of the income distribution spending more than 30% of household income on housing costs$$;
COMMENT ON COLUMN li_2018_city_indicators.li_sa1_sa3_local_employment IS $$Percentage of employed persons who live and work in the same community$$;
COMMENT ON COLUMN li_2018_city_indicators.walkability_city IS $$Average walkability index, combining street connectivity, dwelling density and daily living destinations, relative to locations within this city$$;
COMMENT ON COLUMN li_2018_city_indicators.walkability_national IS $$Average walkability index, combining street connectivity, dwelling density and daily living destinations, relative to locations across Australia's 21 largest cities$$;
COMMENT ON COLUMN li_2018_city_indicators.daily_living_access_1600m IS $$Average number of daily living types present, measured as a score of 0-3, with 1 point for each category of convenience store/petrol station/newsagent, PT stop, supermarket within 1600m network distance$$;
COMMENT ON COLUMN li_2018_city_indicators.social_infrastructure_mix IS $$Average social infrastructure mix score (/16)$$;
COMMENT ON COLUMN li_2018_city_indicators.walk_02 IS $$Percentage of dwellings <1 km walking distance of an activity centre with a supermarket$$;
COMMENT ON COLUMN li_2018_city_indicators.walk_02_policy IS $$At least 80% of dwellings are within 1 km walking distance of an activity centre with a supermarket$$;
COMMENT ON COLUMN li_2018_city_indicators.walk_03_policy IS $$Area has at least 15 dwellings per net developable hectare$$;
COMMENT ON COLUMN li_2018_city_indicators.walk_05_policy IS $$Area has at least 26 dwellings per net developable hectare$$;
COMMENT ON COLUMN li_2018_city_indicators.walk_12 IS $$Percentage of dwellings with local dwelling density of 15 dwellings per hectare or greater$$;
COMMENT ON COLUMN li_2018_city_indicators.walk_12_policy IS $$15 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_city_indicators.walk_13 IS $$Percentage of dwellings with local dwelling density of 30 dwellings per hectare or greater$$;
COMMENT ON COLUMN li_2018_city_indicators.walk_13_policy IS $$Local dwelling density of 30 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_city_indicators.walk_14_policy IS $$Gross dwelling density of 15 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_city_indicators.walk_15_policy IS $$Gross dwelling density of 30 dwellings or more per hectare$$;
COMMENT ON COLUMN li_2018_city_indicators.walk_16 IS $$Average distance to closest activity centre (proxy measure: supermarket within a commercial zoned Mesh Block)$$;
COMMENT ON COLUMN li_2018_city_indicators.walk_17 IS $$Average pedshed ratio, defined as the area of the 400 m pedestrian network from each residential dwelling buffered by 50m divided by the radial 400 m "crow flies" area (i.e. 50.2 Ha.)$$;
COMMENT ON COLUMN li_2018_city_indicators.walk_21 IS $$Average number of local living types present (see paper of Mavoa et al)$$;
COMMENT ON COLUMN li_2018_city_indicators.trans_01 IS $$Percentage of dwellings with access to bus stop within 400 m, a tram stop within 600m, or a train station within 800 m$$;
COMMENT ON COLUMN li_2018_city_indicators.trans_01_policy IS $$95% or more of dwellings with access to bus stop within 400 m, a tram stop within 600m, or a train station within 800 m$$;
COMMENT ON COLUMN li_2018_city_indicators.trans_02 IS $$Percentage of dwellings with access to bus stop < 400 m$$;
COMMENT ON COLUMN li_2018_city_indicators.trans_02_policy IS $$95% or more of dwellings with access to bus stop < 400 m$$;
COMMENT ON COLUMN li_2018_city_indicators.trans_03 IS $$Percentage of dwellings < 400m walk from a neighbourhood or town centre, or a bus stop, or in a 800m walk from a railway station.$$;
COMMENT ON COLUMN li_2018_city_indicators.trans_03_policy IS $$60% or more of dwellings < 400m walk from a neighbourhood or town centre, or a bus stop, or in a 800m walk from a railway station.$$;
COMMENT ON COLUMN li_2018_city_indicators.trans_04 IS $$Percentage of dwellings < 400 metres of an existing or planned public transport stop$$;
COMMENT ON COLUMN li_2018_city_indicators.trans_04_policy IS $$100% of dwellings < 400 metres of an existing or planned public transport stop$$;
COMMENT ON COLUMN li_2018_city_indicators.trans_05 IS $$Percentage of dwellings < 400 m of a bus stop every 30 min OR < 800 m of a train station every 15 min$$;
COMMENT ON COLUMN li_2018_city_indicators.trans_05_policy IS $$100% of dwellings < 400 m of a bus stop every 30 min OR < 800 m of a train station every 15 min$$;
COMMENT ON COLUMN li_2018_city_indicators.trans_06 IS $$Percentage of dwellings < 400 m of a public transport stop with a scheduled service at least every 30 minutes between 7am and 7pm on a normal weekday (= a combined measure of proximity and frequency)$$;
COMMENT ON COLUMN li_2018_city_indicators.trans_07 IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 30 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_city_indicators.trans_08 IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 25 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_city_indicators.trans_09 IS $$Percentage of dwellings within 400m of public transport with an average weekday service frequency of 20 minutes or less between 7am and 7pm$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_01 IS $$Percentage of dwellings within 400 m or less distance of public open space$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_02 IS $$Percentage of dwellings < 400 m of public open space > 1.5 ha$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_03 IS $$Percentage of dwellings within 400 m or less distance of public open space$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_03_policy IS $$95% or more of dwellings within 400 m or less distance of public open space$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_04 IS $$Percentage of dwellings within 300 m or less distance of any public open space$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_04_policy IS $$100% of dwellings within 300 m or less distance of any public open space$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_05 IS $$Percentage of dwellings within 400 m or less distance of any local park (> 0.4 to <=1 ha)$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_05_policy IS $$50% or more of dwellings within 400 m or less distance of any local park (> 0.4 to <=1 ha)$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_06 IS $$Percentage of dwellings within 800 m or less distance of any neighbourhood park (>1 ha to <= 5ha)$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_06_policy IS $$50% or more of dwellings within 800 m or less distance of any neighbourhood park (>1 ha to <= 5ha)$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_07 IS $$Percentage of dwellings within 2 km or less of any district park (>5 ha to <=20 ha)$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_07_policy IS $$50% or more of dwellings within 2 km or less of any district park (>5 ha to <=20 ha)$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_08 IS $$Percentage of dwellings within 400 m or less distance of a neighbourhood recreation park (>0.5 ha)$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_08_policy IS $$90% or more of dwellings within 400 m or less distance of a neighbourhood recreation park (>0.5 ha)$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_09 IS $$Percentage of dwellings within 2.5 km or less distance of a district recreation park (>5 ha)$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_09_policy IS $$90% or more of dwellings within 2.5 km or less distance of a district recreation park (>5 ha)$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_10 IS $$Percentage of dwellings within 400 m or less distance of a park larger than 0.5 Ha$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_10_policy IS $$50% or more of dwellings within 400 m or less distance of a park larger than 0.5 Ha$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_11 IS $$Percentage of dwellings within 2 km or less distance of a park larger than 2 Ha$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_11_policy IS $$50% or more of dwellings within 2 km or less distance of a park larger than 2 Ha$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_12 IS $$Average distance to closest POS with a public toilet within 100 metres$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_14 IS $$Average distance to closest public open space (OSM, 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_15 IS $$Average distance to closest public open space <=0.4 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_16 IS $$Average distance to closest public open space >0.4 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_17 IS $$Average distance to closest public open space >0.5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_18 IS $$Average distance to closest public open space >1.5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_19 IS $$Average distance to closest public open space >2 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_20 IS $$Average distance to closest public open space >0.4 to <=1 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_21 IS $$Average distance to closest public open space >1 to <= 5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_22 IS $$Average distance to closest public open space >5 Ha to <=20 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_23 IS $$Average distance to closest public open space >5 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_24 IS $$Average distance to closest public open space >20 Ha (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_city_indicators.os_public_25 IS $$Average distance to closest public open space with a sport facility (OSM, 2018) within 3200 metres$$;
COMMENT ON COLUMN li_2018_city_indicators.hous_02 IS $$Percentage of dwellings renting as a proportion of total$$;
COMMENT ON COLUMN li_2018_city_indicators.hous_04 IS $$Percentage of employed persons aged 15 and over using active transport to travel to work$$;
COMMENT ON COLUMN li_2018_city_indicators.hous_05 IS $$Percentage of employed persons aged 15 and over using public transport to travel to work$$;
COMMENT ON COLUMN li_2018_city_indicators.hous_06 IS $$Percentage of employed persons aged 15 and over using private vehicle/s to travel to work$$;
COMMENT ON COLUMN li_2018_city_indicators.food_12 IS $$Average count of supermarkets within 1.6km$$;
COMMENT ON COLUMN li_2018_city_indicators.food_13 IS $$Average count of fruit and vegetable grocers within 1.6km$$;
COMMENT ON COLUMN li_2018_city_indicators.food_14 IS $$Average count of specialty food stores (bakeries, butchers, fishmongers and delicatessens) within 1.6km$$;
COMMENT ON COLUMN li_2018_city_indicators.food_15 IS $$Average count of healther food outlets (supermarkets and fruit and vegetable grocers) within 1.6 km (OSM, or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_city_indicators.food_16 IS $$Average count of fast food outlets within 1.6km (OSM, or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_city_indicators.food_17 IS $$Average percentage of food outlets within 1.6km that provide healthier food options (ie. supermarkets and fruit and vegetable grocers; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_city_indicators.food_18 IS $$Average ratio of food outlets within 1.6km that provide healthier food options (ie. supermarkets and fruit and vegetable grocers) to fast food outlets; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_city_indicators.food_19 IS $$Average percentage of food outlets within 1.6km that provide fresh food options  (ie. supermarkets, fruit and vegetable grocers, bakeries, butchers, fishmongers and delicatessens; OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_city_indicators.food_20 IS $$Average ratio of food outlets within 1.6km that provide fresh food options (ie. supermarkets, fruit and vegetable grocers, bakeries, butchers, fishmongers and delicatessens) to fast food outlets (OSM and/or 2017 in-house)$$;
COMMENT ON COLUMN li_2018_city_indicators.food_21 IS $$Percentage of dwellings with no availability of healthy or unhealthy food within 1.6km$$;
COMMENT ON COLUMN li_2018_city_indicators.food_22 IS $$Percentage of dwellings with no food outlets within 1.6km$$;
COMMENT ON COLUMN li_2018_city_indicators.food_23_hard IS $$Percentage of dwellings within 1km of a supermarket$$;
COMMENT ON COLUMN li_2018_city_indicators.food_24 IS $$Average distance to closest fresh food outlet (bakery, fruit and vegetables grocer, delicatessen, and fish, meat, poultry outlet; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.food_25 IS $$Average distance to closest healthy food outlet (supermarket or fruit and vegetables grocer; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.food_26 IS $$Average distance to closest fast food outlet (HLC, 2017; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.food_27 IS $$Average distance to closest dining establishment (cafe, restaurant, pub; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.community_01 IS $$Average distance to closest community centre (HLC, 2016; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.community_02 IS $$Average distance to closest cultural institution (museum, theatre, cinema, art gallery or art centre; OSM, 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.alc_01 IS $$Average number of on-licenses within 400 m$$;
COMMENT ON COLUMN li_2018_city_indicators.alc_02 IS $$Average number of off-licenses within 800 m$$;
COMMENT ON COLUMN li_2018_city_indicators.alc_03 IS $$Average distance to closest bar, pub or nightclub (OSM, 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.childcare_01 IS $$Percentage of dwellings within 1600m of a children's day care which meets guidelines$$;
COMMENT ON COLUMN li_2018_city_indicators.childcare_02 IS $$Percentage of dwellings within 1600m of a children's day care (OSHC) which meets guidelines$$;
COMMENT ON COLUMN li_2018_city_indicators.health_01 IS $$Percentage of dwellings within 1600m of a GP$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_activity_centres IS $$Average distance to closest activity centre$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_alcohol_offlicence IS $$Average distance to closest offlicence alcohol outlet (HLC, 2017-19)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_alcohol_onlicence IS $$Average distance to closest onlicence alcohol outlet (HLC, 2017-19)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_alcohol_osm IS $$Average distance to closest alcohol outlet (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_all_schools IS $$Average distance to closest schools (all; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_art_centre_osm IS $$Average distance to closest art centre (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_art_gallery_osm IS $$Average distance to closest art gallery (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_bakery_osm IS $$Average distance to closest bakery (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_bar_osm IS $$Average distance to closest bar (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_cafe_osm IS $$Average distance to closest cafe (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_childcare_all IS $$Average distance to closest child care (all, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_childcare_all_exc IS $$Average distance to closest child care (exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_childcare_all_meet IS $$Average distance to closest child care (meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_childcare_oshc IS $$Average distance to closest child care (outside school hours, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_childcare_oshc_exc IS $$Average distance to closest child care (outside school hours exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_childcare_oshc_meet IS $$Average distance to closest child care (outside school hours meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_childcare_preschool IS $$Average distance to closest child care (pre-school, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_childcare_preschool_exc IS $$Average distance to closest child care (pre-school exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_childcare_preschool_meet IS $$Average distance to closest child care (pre-school meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_cinema_osm IS $$Average distance to closest cinema (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_community_centre_osm IS $$Average distance to closest community centre (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_convenience_osm IS $$Average distance to closest convenience store (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_deli_osm IS $$Average distance to closest deli (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_disability_employment IS $$Average distance to closest disabilty employment service $$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_fast_food IS $$Average distance to closest fast food (in house 2017)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_fastfood_osm IS $$Average distance to closest fast food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_food_court_osm IS $$Average distance to closest food court (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_food_health_osm IS $$Average distance to closest health food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_food_other_osm IS $$Average distance to closest other food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_fruit_veg_osm IS $$Average distance to closest fruit and veg (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_gtfs_2018_stop_30_mins_final IS $$Average distance to closest transport stop with frequent daytime service$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_gtfs_2018_stops IS $$Average distance to closest public transport stop$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_gtfs_2018_stops_bus IS $$Average distance to closest bus stop$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_gtfs_2018_stops_ferry IS $$Average distance to closest ferry terminal$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_gtfs_2018_stops_train IS $$Average distance to closest train station$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_gtfs_2018_stops_tram IS $$Average distance to closest tram stop$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_gtfs_20191008_20191205_bus_0015 IS $$Average distance to closest bus stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_gtfs_20191008_20191205_bus_0030 IS $$Average distance to closest bus stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_gtfs_20191008_20191205_bus_0045 IS $$Average distance to closest bus stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_gtfs_20191008_20191205_bus_any IS $$Average distance to closest bus stop$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_gtfs_20191008_20191205_ferry_0015 IS $$Average distance to closest ferry stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_gtfs_20191008_20191205_ferry_0030 IS $$Average distance to closest ferry stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_gtfs_20191008_20191205_ferry_0045 IS $$Average distance to closest ferry stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_gtfs_20191008_20191205_ferry_any IS $$Average distance to closest ferry stop$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_gtfs_20191008_20191205_revised_all IS $$Average distance to closest public transport stop$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_gtfs_20191008_20191205_revised_frequent30 IS $$Average distance to closest public transport stop with an average weekday service frequency of 30 minutes or less$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_gtfs_20191008_20191205_train_0015 IS $$Average distance to closest train stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_gtfs_20191008_20191205_train_0030 IS $$Average distance to closest train stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_gtfs_20191008_20191205_train_0045 IS $$Average distance to closest train stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_gtfs_20191008_20191205_train_any IS $$Average distance to closest train stop$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_gtfs_20191008_20191205_tram_0015 IS $$Average distance to closest tram stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_gtfs_20191008_20191205_tram_0030 IS $$Average distance to closest tram stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_gtfs_20191008_20191205_tram_0045 IS $$Average distance to closest tram stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_gtfs_20191008_20191205_tram_any IS $$Average distance to closest tram stop$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_hlc_2016_community_centres IS $$Average distance to closest community centre (2016)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_libraries IS $$Average distance to closest libraries (multiple sources, in-house, 2015-18)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_market_osm IS $$Average distance to closest market (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_meat_seafood_osm IS $$Average distance to closest meat / seafood (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_museum_osm IS $$Average distance to closest museum (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_newsagent_osm IS $$Average distance to closest newsagent (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_nhsd_2017_aged_care_residential IS $$Average distance to closest aged care residential service$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_nhsd_2017_dentist IS $$Average distance to closest dentist (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_nhsd_2017_gp IS $$Average distance to closest general practice/GP/doctor (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_nhsd_2017_hospital IS $$Average distance to closest hospital (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_nhsd_2017_mc_family_health IS $$Average distance to closest maternal, child and family health (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_nhsd_2017_other_community_health_care IS $$Average distance to closest 'other community health care' destination (not pharmacy or maternal and child health)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_nhsd_2017_pharmacy IS $$Average distance to closest pharmacy (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_P_12_Schools IS $$Average distance to closest schools (K - 12; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_P_12_Schools_catholic IS $$Average distance to closest schools (K - 12, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_P_12_Schools_gov IS $$Average distance to closest schools (K - 12, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_P_12_Schools_indep IS $$Average distance to closest schools (K - 12, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_petrolstation_osm IS $$Average distance to closest petrol station (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_pharmacy_osm IS $$Average distance to closest pharmacy (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_place_of_worship_osm IS $$Average distance to closest place of worship (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_playgrounds IS $$Average distance to closest playground (in house 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_postoffice_osm IS $$Average distance to post office (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_primary_schools IS $$Average distance to closest schools (primary; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_primary_schools_catholic IS $$Average distance to closest schools (primary, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_primary_schools_gov IS $$Average distance to closest schools (primary, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_primary_schools_indep IS $$Average distance to closest schools (primary, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_pub_osm IS $$Average distance to closest pub (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_public_swimming_pool_osm IS $$Average distance to closest public swimming pool (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_restaurant_osm IS $$Average distance to closest restaurant (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_secondary_schools IS $$Average distance to closest schools (secondary; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_secondary_schools_catholic IS $$Average distance to closest schools (secondary, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_secondary_schools_gov IS $$Average distance to closest schools (secondary, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_secondary_schools_indep IS $$Average distance to closest schools (secondary, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_special_schools IS $$Average distance to closest schools (special; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_supermarket IS $$Average distance to closest supermarket (in house 2017)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_supermarket_osm IS $$Average distance to closest supermarket (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_city_indicators.dist_m_theatre_osm IS $$Average distance to closest theatre (OSM, October 2018)$$;
```
</details>

Display information (including size and description) for this particular table: `\dt+ li_2018_city_indicators`
Display custom data dictionary by running `SELECT * FROM dictionary('li_2018_city_indicators');`


####  Other Tables

```sql
COMMENT ON TABLE li_2018_address_dest_closest IS $$Estimates for distance in metres along pedestrian network to the closest of a range of destination types for residential locations (address points in urban Mesh Blocks with dwellings at 2016 census)$$;
```

```sql
COMMENT ON TABLE li_2018_address_dest_array IS $$Arrays of estimates for distance in metres along pedestrian network to all destinations (within 3200m and the closest) across a range of destination types , for residential locations (address points in urban Mesh Blocks with dwellings at 2016 census)$$;
```


```sql
COMMENT ON TABLE li_2018_gtfs IS $$GTFS transport stops headway analysis of day time weekday public transport service frequency between 8 October 2019 to 5 December 2019, with WKT geometry$$;
```

```sql
COMMENT ON TABLE li_2018_public_open_space IS $$Areas of open space with at least partial public access, as identified using open street map, with WKT geometry for public geometry, water geometry and overall geometry as well as JSON attributes (including public area) and list of co-located amenities within 100m (including public toilets)$$;
```

```sql
COMMENT ON TABLE li_2018_aos_jsonb IS $$JSON list of identifiers and distances of areas of open space for residential address points identified as having areas of open space accessible within 3200m. This dataset is indexed by the residential address point identifier, supporting linkage with attributes from the main address indicator dataset.$$;
```


### Additional custom SQL functions
PostgreSQL allows the definition of custom functions which can be used to query the data and derive new indicators, particularly when using the destination distances array dataset.  We defined the following queries to assist in indicator creation, and data users can also use them to further manipulate the data provided once restored as an SQL database.  To evaluate the count of destinations accessible within a given threshold distance in metres, 

#### Returning counts of destinations accessible within a given threshold distance in metres
To evaluate the count of destinations accessible within a given threshold distance in metres, the following function may be used to query the destination array data set with the query provided with arguments for (destination,  threshold), for example to identify the count of supermarkets within 800m for each address: `SELECT gnaf_pid, count_in_threshold(dist_m_supermarket,800) FROM dest_array_distances`. The results of a query like this could be used for subsequent analysis or mapping if it were used to create a new indicator dataset as a table or update the values of a new column added to the existing address level indicator dataset. 

```sql
CREATE OR REPLACE FUNCTION count_in_threshold(distances int[],threshold int) returns bigint as $$
SELECT COUNT(*) 
FROM unnest(distances) dt(b)
WHERE b < threshold
$$ language sql;
```

#### Return minimum value of an integer array (ie. the distance to the closest accessible destination recorded of a particular type)

The distance to the closest accessible destination recorded of a particular type may be calculated using  the following function, for example, by querying SELECT array_min(dist_m_supermarket)FROM dest_array_distances.  Given knowledge of the distance to closest destination of a particular type, access can be evaluated against a recommended distance threshold to return a binary score (0 or 1) or a continuous score (0 to 1), as described in [Higgs et al. (2019)](https://doi.org/10.1186/s12942-019-0178-8) and using functions defined below.

```sql
CREATE OR REPLACE FUNCTION array_min(integers int[]) returns int as $$
SELECT min(integers) 
FROM unnest(integers) integers
$$ language sql;
```

#### A binary or hard threshold indicator (e.g. of access given distance to a particular destination and a threshold for evaluating this)
```sql
CREATE OR REPLACE FUNCTION threshold_hard(distance int, threshold int, out int) 
RETURNS NULL ON NULL INPUT
AS $$ SELECT (distance < threshold)::int $$
LANGUAGE SQL;
```
#### A soft threshold indicator (e.g. of access given distance and threshold)
```sql
CREATE OR REPLACE FUNCTION threshold_soft(distance int, threshold int) returns float AS 
$$
BEGIN
  -- Negative distances are invalid.  If the value we are exponentiation is less than -100, 
  -- then this means the score for access is effectively zero and treated as such
  -- to avoid risk overflow/underflow error due to the value exceeding the numerical 
  -- limits of PostgreSQL (ie too small a decimal value to be represented). 
  IF (distance < 0) 
      THEN RETURN NULL;
  ELSIF (-5*(distance-threshold)/(threshold::float) < -100) 
THEN RETURN 0;
  ELSE 
RETURN 1 - 1/(1+exp(-5*(distance-threshold)/(threshold::float)));
  END IF;
END;
$$
LANGUAGE plpgsql
RETURNS NULL ON NULL INPUT;  
```