# Usage notes and Example code for loading and using datasets from the [Australian National Liveability Study 2018](https://doi.org/10.25439/rmt.15001230)
We recommend using an SQL database with appropriate use of [indexes](http://postgis.net/workshops/postgis-intro/indexing.html) to support managing and querying of data.  Below we provide example code for the popular free and open-source database management system [PostgreSQL](https://www.postgresql.org/) (e.g. version 14 or higher) along with the [PostGIS](https://postgis.net/) extension (e.g. version 3.2.3 or higher) for spatial datatypes and analysis.  Once the software is installed, the following code can be entered at the command line interactively, or run as an .sql file using the psql terminal interface.  The below code examples also assume that the [Australian National Liveability Study 2018 data files](https://doi.org/10.25439/rmt.15001230) have been retrieved and extracted.  

We have provided our data and data dictionaries in a plain text CSV format for archival purposes, to maximise accessibility and usability of the data.  In addition, an [Excel file containing the data dictionaries as formatted worksheets](https://rmit.figshare.com/ndownloader/files/36948940) is also included.  The data dictionaries describe the variables (columns) included in the CSV data, in addition to the data types for interpreting these (e.g. integer, numerical, string or text, etc). 

This document provides examples for loading all provided datasets and illustrate how to get started using the data in a PostgreSQL database.  Users may draw on this code freely, updating any file paths with corresponding locations of their own downloaded data.  

Once data has been loaded into PostgreSQL, other programs can connect to your database to load the data.  The following links provide examples for specific programs on how to make a database connection and load data:
- [QGIS](https://qgis.org/) (open source desktop GIS software): [Creating a stored database connection](https://docs.qgis.org/2.18/en/docs/user_manual/managing_data_source/opening_data.html#creating-a-stored-connection)
- [Python](https://www.python.org/) with [Pandas](https://pandas.pydata.org/docs/reference/api/pandas.read_sql.html) (open source data analysis library)
- [Python](https://www.python.org/) with [GeoPandas](https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoDataFrame.from_postgis.html) (open source geospatial data analysis library)
- [R](https://www.r-project.org/) with [sf](https://www.r-bloggers.com/2019/04/interact-with-postgis-from-r/) (open source geospatial data analysis library)
- [Stata](https://qgis.org/) (statistical software): [Load, write, or view data from ODBC sources](https://www.stata.com/manuals13/dodbc.pdf)

Alternatively, the CSV format data files can also be loaded directly into any of the above software for statistical or spatial analysis, linkage with other datasets, and mapping as required.

## Contents
- [Create and connect to a new database for the Australian National Liveability Study](#create-and-connect-to-a-new-database-for-the-australian-national-liveability-study)
- [Loading the indicator datasets](#loading-the-indicators-datasets)
  - [General process and tips](#general-process-and-tips)
  - [Address points](#loading-the-address-indicator-data)
  - [Mesh Blocks](#loading-the-mesh-block-indicator-data)
  - [Stastistical Area 1](#loading-the-statistical-area-1-sa1-indicator-data)
  - [Stastistical Area 2](#loading-the-statistical-area-2-sa2-indicator-data)
  - [Stastistical Area 3](#loading-the-statistical-area-3-sa3-indicator-data)
  - [Stastistical Area 4](#loading-the-statistical-area-4-sa4-indicator-data)
  - [Suburbs](#loading-the-suburb-indicator-data)
  - [Local Government Areas](#loading-the-local-government-area-indicator-data)
  - [City (overall summaries)](#loading-the-city-indicator-data-overall-city-summaries)
- [Loading supplementary datasets](#loading-supplementary-datasets)
  - [Distance to closest destination in metres for residential addresses](#distance-to-closest-destination-in-metres-for-residential-addresses)
  - [Distance arrays (distance in metres to destinations within 3200m, and closest)](#distance-arrays-distance-in-metres-to-destinations-within-3200m-and-closest)
  - [GTFS transport stops headway analysis](#gtfs-transport-stops-headway-analysis)
  - [GTFS transport stops headway analysis](#gtfs-transport-stops-headway-analysis)
  - [JSON look-up for access to open space](#json-look-up-for-access-to-open-space)
- [Additional custom SQL functions](#Additional-custom-SQL-functions)
- [Examples of analyses using the data](#Examples-of-analyses-using-the-data)
  - [Selecting the top and bottom 3-ranking suburbs for a city in terms of liveability](#selecting-the-top-and-bottom-3-ranking-suburbs-for-a-city-in-terms-of-liveability)
  - [Summarising address level access to public transport in Melbourne](#summarising-address-level-access-to-public-transport-in-melbourne)
  - [Using the destination array to query the closest destinations](#using-the-destination-array-to-query-the-closest-destinations)

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

##### Copy the data from CSV.  

```sql
COPY li_2018_address_indicators FROM 'D:/projects/ntnl_li_2018/data/National Liveability 2018 - Final Outputs/For dissemination/hlc_ntnl_liveability_2018_address_points_indicators_epsg7845.csv' WITH DELIMITER ',' CSV HEADER;
CREATE INDEX li_2018_address_indicators_region_idx ON li_2018_address_indicators (study_region);
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

#### Copy the data from CSV
```sql
COPY li_2018_mb_indicators FROM 'D:/projects/ntnl_li_2018/data/National Liveability 2018 - Final Outputs/For dissemination/hlc_ntnl_liveability_2018_Mesh_Block_2016.csv' WITH DELIMITER ',' CSV HEADER;
CREATE INDEX li_2018_mb_indicators_region_idx ON li_2018_mb_indicators (study_region);
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

#### Copy the data from CSV
```sql
COPY li_2018_sa1_indicators FROM 'D:/projects/ntnl_li_2018/data/National Liveability 2018 - Final Outputs/For dissemination/hlc_ntnl_liveability_2018_sa1_2016.csv' WITH DELIMITER ',' CSV HEADER;
CREATE INDEX li_2018_sa1_indicators_region_idx ON li_2018_sa1_indicators (study_region);
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

#### Copy the data from CSV
```sql
COPY li_2018_sa2_indicators FROM 'D:/projects/ntnl_li_2018/data/National Liveability 2018 - Final Outputs/For dissemination/hlc_ntnl_liveability_2018_sa2_2016.csv' WITH DELIMITER ',' CSV HEADER;
CREATE INDEX li_2018_sa2_indicators_region_idx ON li_2018_sa2_indicators (study_region);
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

#### Copy the data from CSV
```sql
COPY li_2018_sa3_indicators FROM 'D:/projects/ntnl_li_2018/data/National Liveability 2018 - Final Outputs/For dissemination/hlc_ntnl_liveability_2018_sa3_2016.csv' WITH DELIMITER ',' CSV HEADER;
CREATE INDEX li_2018_sa3_indicators_region_idx ON li_2018_sa3_indicators (study_region);
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

#### Copy the data from CSV
```sql
COPY li_2018_sa4_indicators FROM 'D:/projects/ntnl_li_2018/data/National Liveability 2018 - Final Outputs/For dissemination/hlc_ntnl_liveability_2018_sa2_2016.csv' WITH DELIMITER ',' CSV HEADER;
CREATE INDEX li_2018_sa4_indicators_region_idx ON li_2018_sa4_indicators (study_region);
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

#### Copy the data from CSV
```sql
COPY li_2018_suburb_indicators FROM 'D:/projects/ntnl_li_2018/data/National Liveability 2018 - Final Outputs/For dissemination/hlc_ntnl_liveability_2018_ssc_2016.csv' WITH DELIMITER ',' CSV HEADER;
CREATE INDEX li_2018_suburb_indicators_region_idx ON li_2018_suburb_indicators (study_region);
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

#### Copy the data from CSV
```sql
COPY li_2018_lga_indicators FROM 'D:/projects/ntnl_li_2018/data/National Liveability 2018 - Final Outputs/For dissemination/hlc_ntnl_liveability_2018_lga_2016.csv' WITH DELIMITER ',' CSV HEADER;
CREATE INDEX li_2018_lga_indicators_region_idx ON li_2018_lga_indicators (study_region);
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

##### Copy the data from CSV
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


##  Loading supplementary datasets

### Distance to closest destination in metres for residential addresses

<details>
  <summary>
    Click to view code
  </summary>
  
```sql
CREATE TABLE li_2018_address_dist_cl_m
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
dist_m_activity_centres integer,
dist_m_alcohol_offlicence integer,
dist_m_alcohol_onlicence integer,
dist_m_alcohol_osm integer,
dist_m_all_schools integer,
dist_m_art_centre_osm integer,
dist_m_art_gallery_osm integer,
dist_m_bakery_osm integer,
dist_m_bar_osm integer,
dist_m_cafe_osm integer,
dist_m_childcare_all integer,
dist_m_childcare_all_exc integer,
dist_m_childcare_all_meet integer,
dist_m_childcare_oshc integer,
dist_m_childcare_oshc_exc integer,
dist_m_childcare_oshc_meet integer,
dist_m_childcare_preschool integer,
dist_m_childcare_preschool_exc integer,
dist_m_childcare_preschool_meet integer,
dist_m_cinema_osm integer,
dist_m_community_centre_osm integer,
dist_m_convenience_osm integer,
dist_m_deli_osm integer,
dist_m_disability_employment integer,
dist_m_fast_food integer,
dist_m_fastfood_osm integer,
dist_m_food_court_osm integer,
dist_m_food_health_osm integer,
dist_m_food_other_osm integer,
dist_m_fruit_veg_osm integer,
dist_m_gtfs_2018_stop_30_mins_final integer,
dist_m_gtfs_2018_stops integer,
dist_m_gtfs_2018_stops_bus integer,
dist_m_gtfs_2018_stops_ferry integer,
dist_m_gtfs_2018_stops_train integer,
dist_m_gtfs_2018_stops_tram integer,
dist_m_gtfs_20191008_20191205_bus_0015 integer,
dist_m_gtfs_20191008_20191205_bus_0030 integer,
dist_m_gtfs_20191008_20191205_bus_0045 integer,
dist_m_gtfs_20191008_20191205_bus_any integer,
dist_m_gtfs_20191008_20191205_ferry_0015 integer,
dist_m_gtfs_20191008_20191205_ferry_0030 integer,
dist_m_gtfs_20191008_20191205_ferry_0045 integer,
dist_m_gtfs_20191008_20191205_ferry_any integer,
dist_m_gtfs_20191008_20191205_revised_all integer,
dist_m_gtfs_20191008_20191205_revised_frequent30 integer,
dist_m_gtfs_20191008_20191205_train_0015 integer,
dist_m_gtfs_20191008_20191205_train_0030 integer,
dist_m_gtfs_20191008_20191205_train_0045 integer,
dist_m_gtfs_20191008_20191205_train_any integer,
dist_m_gtfs_20191008_20191205_tram_0015 integer,
dist_m_gtfs_20191008_20191205_tram_0030 integer,
dist_m_gtfs_20191008_20191205_tram_0045 integer,
dist_m_gtfs_20191008_20191205_tram_any integer,
dist_m_hlc_2016_community_centres integer,
dist_m_libraries integer,
dist_m_market_osm integer,
dist_m_meat_seafood_osm integer,
dist_m_museum_osm integer,
dist_m_newsagent_osm integer,
dist_m_nhsd_2017_aged_care_residential integer,
dist_m_nhsd_2017_dentist integer,
dist_m_nhsd_2017_gp integer,
dist_m_nhsd_2017_hospital integer,
dist_m_nhsd_2017_mc_family_health integer,
dist_m_nhsd_2017_other_community_health_care integer,
dist_m_nhsd_2017_pharmacy integer,
dist_m_P_12_Schools integer,
dist_m_P_12_Schools_catholic integer,
dist_m_P_12_Schools_gov integer,
dist_m_P_12_Schools_indep integer,
dist_m_petrolstation_osm integer,
dist_m_pharmacy_osm integer,
dist_m_place_of_worship_osm integer,
dist_m_playgrounds integer,
dist_m_postoffice_osm integer,
dist_m_primary_schools integer,
dist_m_primary_schools_catholic integer,
dist_m_primary_schools_gov integer,
dist_m_primary_schools_indep integer,
dist_m_pub_osm integer,
dist_m_public_swimming_pool_osm integer,
dist_m_restaurant_osm integer,
dist_m_secondary_schools integer,
dist_m_secondary_schools_catholic integer,
dist_m_secondary_schools_gov integer,
dist_m_secondary_schools_indep integer,
dist_m_special_schools integer,
dist_m_supermarket integer,
dist_m_supermarket_osm integer,
dist_m_theatre_osm integer
);

-- copy in data
COPY li_2018_address_dist_cl_m FROM 'D:/projects/ntnl_li_2018/data/National Liveability 2018 - Final Outputs/For dissemination/hlc_ntnl_liveability_2018_address_points_distance_closest_epsg7845.csv' WITH DELIMITER ',' CSV HEADER;

-- add in geometry column with spatial index
ALTER TABLE li_2018_address_dist_cl_m ADD COLUMN geom geometry(Point, 7845);
UPDATE li_2018_address_dist_cl_m SET geom = ST_SetSRID(ST_MakePoint(point_x, point_y), 7845);
CREATE INDEX li_2018_address_indicators_geom_idx ON li_2018_address_indicators USING GIST (geom);

-- create index on study region
CREATE INDEX li_2018_address_indicators_region_idx ON li_2018_address_indicators (study_region);

-- add comments to describe table and data
COMMENT ON TABLE li_2018_address_dist_cl_m IS $$Estimates for distance in metres along pedestrian network to the closest of a range of destination types for residential locations (address points in urban Mesh Blocks with dwellings at 2016 census)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.gnaf_pid IS $$Unique identifier using PSMA Open G-NAF 2018 data$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.count_objectid IS $$Count of co-located G-NAF points (only first unique location retained)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.point_x IS $$Easting (metres; EPSG 7845)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.point_y IS $$Northing (metres; EPSG 7845)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.study_region IS $$City name$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.mb_code_2016 IS $$Mesh Block (ASGS 2016) identifier$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.mb_category_name_2016 IS $$Mesh Block category$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.sa1_maincode_2016 IS $$Statistical Area 1 (SA1) maincode identifier$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.sa2_name_2016 IS $$SA2 name$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.sa3_name_2016 IS $$SA3 name$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.sa4_name_2016 IS $$SA4 name$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.gccsa_name_2016 IS $$Greater Capital City Statistical Area name$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.state_name_2016 IS $$State name$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.ssc_name_2016 IS $$Suburb name$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.lga_name_2016 IS $$LGA name$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.ucl_name_2016 IS $$Urban centre and locality name$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.sos_name_2016 IS $$Section of state name $$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_activity_centres IS $$Distance to closest activity centre$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_alcohol_offlicence IS $$Distance to closest offlice alcohol outlet (HLC, 2017-19)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_alcohol_onlicence IS $$Distance to closest onlicence alcohol outlet (HLC, 2017-19)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_alcohol_osm IS $$Distance to closest alcohol outlet (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_all_schools IS $$Distance to closest schools (all; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_art_centre_osm IS $$Distance to closest art centre (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_art_gallery_osm IS $$Distance to closest art gallery (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_bakery_osm IS $$Distance to closest bakery (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_bar_osm IS $$Distance to closest bar (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_cafe_osm IS $$Distance to closest cafe (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_childcare_all IS $$Distance to closest child care (all, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_childcare_all_exc IS $$Distance to closest child care (exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_childcare_all_meet IS $$Distance to closest child care (meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_childcare_oshc IS $$Distance to closest child care (outside school hours, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_childcare_oshc_exc IS $$Distance to closest child care (outside school hours exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_childcare_oshc_meet IS $$Distance to closest child care (outside school hours meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_childcare_preschool IS $$Distance to closest child care (pre-school, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_childcare_preschool_exc IS $$Distance to closest child care (pre-school exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_childcare_preschool_meet IS $$Distance to closest child care (pre-school meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_cinema_osm IS $$Distance to closest cinema (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_community_centre_osm IS $$Distance to closest community centre (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_convenience_osm IS $$Distance to closest convenience store (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_deli_osm IS $$Distance to closest deli (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_disability_employment IS $$Distance to closest disability employment service $$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_fast_food IS $$Distance to closest fast food (in house 2017)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_fastfood_osm IS $$Distance to closest fast food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_food_court_osm IS $$Distance to closest food court (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_food_health_osm IS $$Distance to closest health food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_food_other_osm IS $$Distance to closest other food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_fruit_veg_osm IS $$Distance to closest fruit and veg (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_gtfs_2018_stop_30_mins_final IS $$Distance to closest transport stop with frequent daytime service$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_gtfs_2018_stops IS $$Distance to closest public transport stop$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_gtfs_2018_stops_bus IS $$Distance to closest bus stop$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_gtfs_2018_stops_ferry IS $$Distance to closest ferry terminal$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_gtfs_2018_stops_train IS $$Distance to closest train station$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_gtfs_2018_stops_tram IS $$Distance to closest tram stop$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_gtfs_20191008_20191205_bus_0015 IS $$Distance to closest bus stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_gtfs_20191008_20191205_bus_0030 IS $$Distance to closest bus stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_gtfs_20191008_20191205_bus_0045 IS $$Distance to closest bus stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_gtfs_20191008_20191205_bus_any IS $$Distance to closest bus stop$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_gtfs_20191008_20191205_ferry_0015 IS $$Distance to closest ferry stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_gtfs_20191008_20191205_ferry_0030 IS $$Distance to closest ferry stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_gtfs_20191008_20191205_ferry_0045 IS $$Distance to closest ferry stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_gtfs_20191008_20191205_ferry_any IS $$Distance to closest ferry stop$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_gtfs_20191008_20191205_revised_all IS $$Distance to closest public transport stop$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_gtfs_20191008_20191205_revised_frequent30 IS $$Distance to closest public transport stop with an average weekday service frequency of 30 minutes or less$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_gtfs_20191008_20191205_train_0015 IS $$Distance to closest train stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_gtfs_20191008_20191205_train_0030 IS $$Distance to closest train stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_gtfs_20191008_20191205_train_0045 IS $$Distance to closest train stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_gtfs_20191008_20191205_train_any IS $$Distance to closest train stop$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_gtfs_20191008_20191205_tram_0015 IS $$Distance to closest tram stop with usual daytime weekday service frequency of 15 mins or better$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_gtfs_20191008_20191205_tram_0030 IS $$Distance to closest tram stop with usual daytime weekday service frequency of 30 mins or better$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_gtfs_20191008_20191205_tram_0045 IS $$Distance to closest tram stop with usual daytime weekday service frequency of 45 mins or better$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_gtfs_20191008_20191205_tram_any IS $$Distance to closest tram stop$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_hlc_2016_community_centres IS $$Distance to closest community centre (2016)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_libraries IS $$Distance to closest libraries (multiple sources, in-house, 2015-18)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_market_osm IS $$Distance to closest market (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_meat_seafood_osm IS $$Distance to closest meat / seafood (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_museum_osm IS $$Distance to closest museum (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_newsagent_osm IS $$Distance to closest newsagent (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_nhsd_2017_aged_care_residential IS $$Distance to closest aged care residential service$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_nhsd_2017_dentist IS $$Distance to closest dentist (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_nhsd_2017_gp IS $$Distance to closest general practice/GP/doctor (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_nhsd_2017_hospital IS $$Distance to closest hospital (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_nhsd_2017_mc_family_health IS $$Distance to closest maternal, child and family health (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_nhsd_2017_other_community_health_care IS $$Distance to closest 'other community health care' destination (not pharmacy or maternal and child health)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_nhsd_2017_pharmacy IS $$Distance to closest pharmacy (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_P_12_Schools IS $$Distance to closest schools (K - 12; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_P_12_Schools_catholic IS $$Distance to closest schools (K - 12, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_P_12_Schools_gov IS $$Distance to closest schools (K - 12, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_P_12_Schools_indep IS $$Distance to closest schools (K - 12, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_petrolstation_osm IS $$Distance to closest petrol station (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_pharmacy_osm IS $$Distance to closest pharmacy (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_place_of_worship_osm IS $$Distance to closest place of worship (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_playgrounds IS $$Distance to closest playground (in house 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_postoffice_osm IS $$Distance to post office (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_primary_schools IS $$Distance to closest schools (primary; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_primary_schools_catholic IS $$Distance to closest schools (primary, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_primary_schools_gov IS $$Distance to closest schools (primary, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_primary_schools_indep IS $$Distance to closest schools (primary, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_pub_osm IS $$Distance to closest pub (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_public_swimming_pool_osm IS $$Distance to closest public swimming pool (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_restaurant_osm IS $$Distance to closest restaurant (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_secondary_schools IS $$Distance to closest schools (secondary; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_secondary_schools_catholic IS $$Distance to closest schools (secondary, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_secondary_schools_gov IS $$Distance to closest schools (secondary, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_secondary_schools_indep IS $$Distance to closest schools (secondary, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_special_schools IS $$Distance to closest schools (special; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_supermarket IS $$Distance to closest supermarket (in house 2017)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_supermarket_osm IS $$Distance to closest supermarket (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_dist_cl_m.dist_m_theatre_osm IS $$Distance to closest theatre (OSM, October 2018)$$;
```
</details>

### Distance arrays (distance in metres to destinations within 3200m, and closest)
This full dataset is very large, hence the example demonstrates how to load a 100 record sample to allow users to understand the data before loading the full dataset.   The data was  exported from PostgreSQL as pipe-seperated values (PSV) text file instead of a CSV file due to the arrays which contain commas and otherwise require complicated quoting which makes re-import back into PostgreSQL (or other software) more complicated.

<details>
  <summary>
    Click to view code
  </summary>
  
```sql
CREATE TABLE li_2018_address_distances_3200m_cl
(
gnaf_pid character varying(15) PRIMARY KEY,
study_region text,
mb_code_2016 text,
dist_m_activity_centres Integer[],
dist_m_alcohol_offlicence Integer[],
dist_m_alcohol_onlicence Integer[],
dist_m_alcohol_osm Integer[],
dist_m_all_schools Integer[],
dist_m_art_centre_osm Integer[],
dist_m_art_gallery_osm Integer[],
dist_m_bakery_osm Integer[],
dist_m_bar_osm Integer[],
dist_m_cafe_osm Integer[],
dist_m_childcare_all Integer[],
dist_m_childcare_all_exc Integer[],
dist_m_childcare_all_meet Integer[],
dist_m_childcare_oshc Integer[],
dist_m_childcare_oshc_exc Integer[],
dist_m_childcare_oshc_meet Integer[],
dist_m_childcare_preschool Integer[],
dist_m_childcare_preschool_exc Integer[],
dist_m_childcare_preschool_meet Integer[],
dist_m_cinema_osm Integer[],
dist_m_community_centre_osm Integer[],
dist_m_convenience_osm Integer[],
dist_m_deli_osm Integer[],
dist_m_disability_employment Integer[],
dist_m_fast_food Integer[],
dist_m_fastfood_osm Integer[],
dist_m_food_court_osm Integer[],
dist_m_food_health_osm Integer[],
dist_m_food_other_osm Integer[],
dist_m_fruit_veg_osm Integer[],
dist_m_libraries Integer[],
dist_m_market_osm Integer[],
dist_m_meat_seafood_osm Integer[],
dist_m_museum_osm Integer[],
dist_m_newsagent_osm Integer[],
dist_m_nhsd_2017_aged_care_residential Integer[],
dist_m_nhsd_2017_dentist Integer[],
dist_m_nhsd_2017_gp Integer[],
dist_m_nhsd_2017_hospital Integer[],
dist_m_nhsd_2017_mc_family_health Integer[],
dist_m_nhsd_2017_pharmacy Integer[],
dist_m_P_12_Schools Integer[],
dist_m_P_12_Schools_catholic Integer[],
dist_m_P_12_Schools_gov Integer[],
dist_m_P_12_Schools_indep Integer[],
dist_m_petrolstation_osm Integer[],
dist_m_pharmacy_osm Integer[],
dist_m_place_of_worship_osm Integer[],
dist_m_playgrounds Integer[],
dist_m_postoffice_osm Integer[],
dist_m_primary_schools Integer[],
dist_m_primary_schools_catholic Integer[],
dist_m_primary_schools_gov Integer[],
dist_m_primary_schools_indep Integer[],
dist_m_pub_osm Integer[],
dist_m_restaurant_osm Integer[],
dist_m_secondary_schools Integer[],
dist_m_secondary_schools_catholic Integer[],
dist_m_secondary_schools_gov Integer[],
dist_m_secondary_schools_indep Integer[],
dist_m_special_schools Integer[],
dist_m_supermarket Integer[],
dist_m_supermarket_osm Integer[],
dist_m_theatre_osm Integer[]
);

-- copy in data (actually a 100 record sample, which is worth getting to know before loading the full dataset of 11.2GB)
\copy li_2018_address_distances_3200m_cl FROM 'D:/projects/ntnl_li_2018/data/National Liveability 2018 - Final Outputs/For dissemination/hlc_ntnl_liveability_2018_address_points_distance_arrays_100_record_sample.psv' WITH DELIMITER '|' CSV HEADER;

-- Create index on study region
CREATE INDEX li_2018_address_distances_3200m_cl_region_idx ON li_2018_address_distances_3200m_cl (study_region);

-- add comments to describe table and data
COMMENT ON TABLE li_2018_address_distances_3200m_cl IS $$Arrays of estimates for distance in metres along pedestrian network to all destinations (within 3200m and the closest) across a range of destination types , for residential locations (address points in urban Mesh Blocks with dwellings at 2016 census)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.gnaf_pid IS $$Unique identifier using PSMA Open G-NAF 2018 data$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.study_region IS $$City name$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.mb_code_2016 IS $$Mesh Block (ASGS 2016) identifier$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_activity_centres IS $$Distance to closest activity centre$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_alcohol_offlicence IS $$Distance to closest offlice alcohol outlet (HLC, 2017-19)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_alcohol_onlicence IS $$Distance to closest onlicence alcohol outlet (HLC, 2017-19)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_alcohol_osm IS $$Distance to closest alcohol outlet (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_all_schools IS $$Distance to closest schools (all; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_art_centre_osm IS $$Distance to closest art centre (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_art_gallery_osm IS $$Distance to closest art gallery (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_bakery_osm IS $$Distance to closest bakery (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_bar_osm IS $$Distance to closest bar (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_cafe_osm IS $$Distance to closest cafe (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_childcare_all IS $$Distance to closest child care (all, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_childcare_all_exc IS $$Distance to closest child care (exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_childcare_all_meet IS $$Distance to closest child care (meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_childcare_oshc IS $$Distance to closest child care (outside school hours, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_childcare_oshc_exc IS $$Distance to closest child care (outside school hours exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_childcare_oshc_meet IS $$Distance to closest child care (outside school hours meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_childcare_preschool IS $$Distance to closest child care (pre-school, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_childcare_preschool_exc IS $$Distance to closest child care (pre-school exceeding requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_childcare_preschool_meet IS $$Distance to closest child care (pre-school meeting requirements, ACEQUA 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_cinema_osm IS $$Distance to closest cinema (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_community_centre_osm IS $$Distance to closest community centre (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_convenience_osm IS $$Distance to closest convenience store (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_deli_osm IS $$Distance to closest deli (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_disability_employment IS $$Distance to closest disability employment service $$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_fast_food IS $$Distance to closest fast food (in house 2017)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_fastfood_osm IS $$Distance to closest fast food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_food_court_osm IS $$Distance to closest food court (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_food_health_osm IS $$Distance to closest health food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_food_other_osm IS $$Distance to closest other food (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_fruit_veg_osm IS $$Distance to closest fruit and veg (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_libraries IS $$Distance to closest libraries (multiple sources, in-house, 2015-18)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_market_osm IS $$Distance to closest market (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_meat_seafood_osm IS $$Distance to closest meat / seafood (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_museum_osm IS $$Distance to closest museum (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_newsagent_osm IS $$Distance to closest newsagent (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_nhsd_2017_aged_care_residential IS $$Distance to closest aged care residential service$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_nhsd_2017_dentist IS $$Distance to closest dentist (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_nhsd_2017_gp IS $$Distance to closest general practice/GP/doctor (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_nhsd_2017_hospital IS $$Distance to closest hospital (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_nhsd_2017_mc_family_health IS $$Distance to closest maternal, child and family health (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_nhsd_2017_pharmacy IS $$Distance to closest pharmacy (NHSD 2017)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_P_12_Schools IS $$Distance to closest schools (K - 12; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_P_12_Schools_catholic IS $$Distance to closest schools (K - 12, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_P_12_Schools_gov IS $$Distance to closest schools (K - 12, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_P_12_Schools_indep IS $$Distance to closest schools (K - 12, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_petrolstation_osm IS $$Distance to closest petrol station (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_pharmacy_osm IS $$Distance to closest pharmacy (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_place_of_worship_osm IS $$Distance to closest place of worship (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_playgrounds IS $$Distance to closest playground (in house 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_postoffice_osm IS $$Distance to post office (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_primary_schools IS $$Distance to closest schools (primary; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_primary_schools_catholic IS $$Distance to closest schools (primary, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_primary_schools_gov IS $$Distance to closest schools (primary, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_primary_schools_indep IS $$Distance to closest schools (primary, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_pub_osm IS $$Distance to closest pub (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_restaurant_osm IS $$Distance to closest restaurant (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_secondary_schools IS $$Distance to closest schools (secondary; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_secondary_schools_catholic IS $$Distance to closest schools (secondary, Catholic; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_secondary_schools_gov IS $$Distance to closest schools (secondary, Government; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_secondary_schools_indep IS $$Distance to closest schools (secondary, Independent; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_special_schools IS $$Distance to closest schools (special; ACARA, 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_supermarket IS $$Distance to closest supermarket (in house 2017)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_supermarket_osm IS $$Distance to closest supermarket (OSM, October 2018)$$;
COMMENT ON COLUMN li_2018_address_distances_3200m_cl.dist_m_theatre_osm IS $$Distance to closest theatre (OSM, October 2018)$$;
```
</details>

### GTFS transport stops headway analysis

GTFS transport stops headway analysis of day time weekday public transport service frequency between 8 October 2019 to 5 December 2019


<details>
  <summary>
    Click to view code
  </summary>
  
```sql
CREATE TABLE li_2018_gtfs_2019
(
wkt text,
fid integer PRIMARY KEY,
stop_id text,
mode text,
state text,
authority text,
publication_date integer,
headway float
);

-- copy in data
\copy li_2018_gtfs_2019 FROM 'D:/projects/ntnl_li_2018/data/National Liveability 2018 - Final Outputs/For dissemination/hlc_ntnl_liveability_2018_gtfs_20191008_20191205_daytime_tidy_transit_headway_analysis.csv' WITH DELIMITER ',' CSV HEADER;

-- Add in a geometry column
ALTER TABLE li_2018_gtfs_2019 ADD COLUMN geom geometry(Point, 7845);
UPDATE li_2018_gtfs_2019 SET geom = ST_Transform(ST_GeomFromText(wkt, 4326),7845);
CREATE INDEX li_2018_gtfs_2019_geom_idx ON li_2018_gtfs_2019 USING GIST (geom);
ALTER TABLE li_2018_gtfs_2019 DROP COLUMN wkt;

-- Create index on headway
CREATE INDEX li_2018_gtfs_2019_region_idx ON li_2018_gtfs_2019 (headway);

-- add comments to describe table and data
COMMENT ON TABLE li_2018_gtfs_2019 IS $$GTFS transport stops headway analysis of day time weekday public transport service frequency between 8 October 2019 to 5 December 2019, with WKT geometry$$;
COMMENT ON COLUMN li_2018_gtfs_2019.fid IS $$Sequential numeric index$$;
COMMENT ON COLUMN li_2018_gtfs_2019.stop_id IS $$Stop ID number $$;
COMMENT ON COLUMN li_2018_gtfs_2019.mode IS $$Mode of transport$$;
COMMENT ON COLUMN li_2018_gtfs_2019.state IS $$State the GTFS feed relates to$$;
COMMENT ON COLUMN li_2018_gtfs_2019.authority IS $$Public transportation agency$$;
COMMENT ON COLUMN li_2018_gtfs_2019.publication_date IS $$Date of publication of GTFS feed$$;
COMMENT ON COLUMN li_2018_gtfs_2019.headway IS $$Headway (minutes) for day time (7 am to 7 pm) trips on weekdays between 8 October and 5 December 2019, estimated through analysis using Tidy Transit in R$$;
```
</details>


### Areas of open space

Areas of open space with at least partial public access, as identified using open street map, with WKT geometry for public geometry, water geometry and overall geometry as well as JSON attributes (including public area) and list of co-located amenities within 100m (including public toilets).

The data was directly exported from PostgreSQL as a tab-seperated values (TSV) text file instead of a CSV file due to the JSON data structure of the attributes column which contains commas and otherwise requires complicated quoting which makes re-import back into PostgreSQL (or other software) more complicated.

<details>
  <summary>
    Click to view code
  </summary>
  
```sql
CREATE TABLE li_2018_public_open_space
(
aos_id bigint,
attributes jsonb,
numgeom bigint,
aos_ha_public double precision,
aos_ha_not_public double precision,
aos_ha double precision,
aos_ha_water double precision,
has_water_feature boolean,
water_percent numeric,
locale text,
co_location_100m jsonb,
wkt_public text,
wkt_water text,
wkt text
);

-- copy in data
\copy li_2018_public_open_space FROM 'D:/projects/ntnl_li_2018/data/National Liveability 2018 - Final Outputs/For dissemination/hlc_ntnl_liveability_2018_aos_public_osm.tsv';
ALTER TABLE li_2018_public_open_space ADD PRIMARY KEY (aos_id,locale);
CREATE INDEX li_2018_public_open_space_aos_jsb_idx ON li_2018_public_open_space USING GIN (attributes);
CREATE INDEX li_2018_public_open_space_co_location_idx ON li_2018_public_open_space USING GIN (co_location_100m);

-- Add in a geometry column
ALTER TABLE li_2018_public_open_space ADD COLUMN geom_public geometry(Geometry, 7845);
UPDATE li_2018_public_open_space SET geom_public = ST_GeomFromText(wkt_public, 7845);
CREATE INDEX li_2018_public_open_space_geom_public_idx ON li_2018_public_open_space USING GIST (geom_public);
ALTER TABLE li_2018_public_open_space ADD COLUMN geom_water geometry(Geometry, 7845);
UPDATE li_2018_public_open_space SET geom_water = ST_GeomFromText(wkt_water, 7845);
CREATE INDEX li_2018_water_open_space_geom_water_idx ON li_2018_public_open_space USING GIST (geom_water);
ALTER TABLE li_2018_public_open_space ADD COLUMN geom geometry(Geometry, 7845);
UPDATE li_2018_public_open_space SET geom = ST_GeomFromText(wkt, 7845);
CREATE INDEX li_2018_public_open_space_geom_idx ON li_2018_public_open_space USING GIST (geom);
ALTER TABLE li_2018_public_open_space DROP COLUMN wkt_public;
ALTER TABLE li_2018_public_open_space DROP COLUMN wkt_water;
ALTER TABLE li_2018_public_open_space DROP COLUMN wkt;

-- add comments to describe table and data
COMMENT ON TABLE li_2018_public_open_space IS $$Areas of open space with at least partial public access, as identified using open street map, with WKT geometry for public geometry, water geometry and overall geometry as well as JSON attributes (including public area) and list of co-located amenities within 100m (including public toilets)$$;
COMMENT ON COLUMN li_2018_public_open_space.aos_id IS $$Numeric identifier for areas of open space$$;
COMMENT ON COLUMN li_2018_public_open_space.attributes IS $$JSON list of key-value attribute pairs for individual open spaces associated with this larger area of open space, including: os_id (open space identifier); area_ha (area in hectares); in_school (whether the open space is located in a school, and not considered public); is_school (if this open space is a school, and therefore not a public open space); roundness (a morphological statistic of the ratio of area to the minimum bounding circle containing the open space); public_access (whether the open space has been identified as being publicly accessible); water_feature (whether the open space is associated with water features, or 'blue space'); within_public (whether this open space is nested within a larger area which has been identified as being publicly accessible); linear_feature (a morphological classification based on meeting a set of linear feature criteria, used to identify and segment potentially large, linear spaces like rivers and creeks); minimum_bounding_circle_area (a morphological statistic for minimum bounding circle area, in square metres); minimum_bounding_circle_diameter (a morphological statistic for minimum bounding circle diameter)$$;
COMMENT ON COLUMN li_2018_public_open_space.numgeom IS $$Number of geometries associated with this area of open space (ie. the count of individual open spaces, associated with and located within this larger identified contiguous area of open space)$$;
COMMENT ON COLUMN li_2018_public_open_space.aos_ha_public IS $$The area in hectares which is publicly accessible within this area of open space$$;
COMMENT ON COLUMN li_2018_public_open_space.aos_ha_not_public IS $$The area in hectares which is not public accessible within this area of open space$$;
COMMENT ON COLUMN li_2018_public_open_space.aos_ha IS $$The overall area in hectares of this area of open space$$;
COMMENT ON COLUMN li_2018_public_open_space.aos_ha_water IS $$The area in hectares which has been identified as being water or water-like in this area of open space$$;
COMMENT ON COLUMN li_2018_public_open_space.has_water_feature IS $$Whether the area of open space has been identified as having a water feature$$;
COMMENT ON COLUMN li_2018_public_open_space.water_percent IS $$The percentage of the area of open space that is associated with water$$;
COMMENT ON COLUMN li_2018_public_open_space.locale IS $$The study region (or city; lower case, underscores instead of spaces) where this area of open space is located$$;
COMMENT ON COLUMN li_2018_public_open_space.co_location_100m IS $$Other destinations (eg public toilets, public transport stops, cafes, supermarkets) located within 100 metres of this area of open space$$;
COMMENT ON COLUMN li_2018_public_open_space.geom_public IS $$the publicly accessible portion of this area of open space (EPSG 7845)$$;
COMMENT ON COLUMN li_2018_public_open_space.geom_water IS $$portion of this area of open space identified as water, or water-like (EPSG 7845)$$;
COMMENT ON COLUMN li_2018_public_open_space.geom IS $$ overall area of open space (EPSG 7845)$$;
```
</details>


### JSON look-up for access to open space

JSON list of identifiers and distances of areas of open space for residential address points identified as having areas of open space accessible within 3200m. This dataset is indexed by the residential address point identifier, supporting linkage with attributes from the main address indicator dataset.

This full dataset is very large, hence the example demonstrates how to load a 100 record sample to allow users to understand the data before loading the full dataset.   The data was directly exported from PostgreSQL as a tab-seperated values (TSV) text file instead of a CSV file due to the JSON data structure of the attributes column which contains commas and otherwise requires complicated quoting which makes re-import back into PostgreSQL (or other software) more complicated.

<details>
  <summary>
    Click to view code
  </summary>
  
```sql
CREATE TABLE li_2018_aos_jsonb
(
gnaf_pid text PRIMARY KEY,
attributes jsonb,
locale Text
);

-- copy in data
\copy li_2018_aos_jsonb FROM 'D:/projects/ntnl_li_2018/data/National Liveability 2018 - Final Outputs/For dissemination/hlc_ntnl_liveability_2018_od_aos_jsonb_100_record_sample.tsv';

CREATE INDEX li_2018_aos_jsonb_locale_idx ON li_2018_aos_jsonb (locale);
CREATE INDEX li_2018_aos_jsonb_aos_jsb_idx ON li_2018_aos_jsonb USING GIN (attributes);

-- add comments to describe table and data
COMMENT ON COLUMN li_2018_aos_jsonb.gnaf_pid IS $$Numeric identifier for areas of open space$$;
COMMENT ON COLUMN li_2018_aos_jsonb.attributes IS $$JSON list of key-value attribute pairs for area of open space ID (aos_id) and distance (distance) for all areas of open space identified as being accessible within 3200 metres.  This allows for post hoc querying of open space, for example by identifying the set of areas of open space meeting some set of criteria (eg. publicly accessible area larger than 1.5 hectares, or having some amenity such as a public toilet co-located within 100m) and then querying this data to identify the residential address points having such an area of open space accessible within some relevant threshold distance (e.g. 400 metres).$$;
COMMENT ON COLUMN li_2018_aos_jsonb.locale IS $$The study region (or city; lower case, underscores instead of spaces) where this area of open space is located$$;
```
</details>



## Additional custom SQL functions
PostgreSQL allows the definition of custom functions which can be used to query the data and derive new indicators, particularly when using the destination distances array dataset.  We defined the following queries to assist in indicator creation, and data users can also use them to further manipulate the data provided once restored as an SQL database.  To evaluate the count of destinations accessible within a given threshold distance in metres, 

### Returning counts of destinations accessible within a given threshold distance in metres
To evaluate the count of destinations accessible within a given threshold distance in metres, the following function may be used to query the destination array data set with the query provided with arguments for (destination,  threshold), for example to identify the count of supermarkets within 800m for each address: `SELECT gnaf_pid, count_in_threshold(dist_m_supermarket,800) FROM dest_array_distances`. The results of a query like this could be used for subsequent analysis or mapping if it were used to create a new indicator dataset as a table or update the values of a new column added to the existing address level indicator dataset. 

```sql
CREATE OR REPLACE FUNCTION count_in_threshold(distances int[],threshold int) returns bigint as $$
SELECT COUNT(*) 
FROM unnest(distances) dt(b)
WHERE b < threshold
$$ language sql;
```

### Return minimum value of an integer array (ie. the distance to the closest accessible destination recorded of a particular type)

The distance to the closest accessible destination recorded of a particular type may be calculated using  the following function, for example, by querying SELECT array_min(dist_m_supermarket)FROM dest_array_distances.  Given knowledge of the distance to closest destination of a particular type, access can be evaluated against a recommended distance threshold to return a binary score (0 or 1) or a continuous score (0 to 1), as described in [Higgs et al. (2019)](https://doi.org/10.1186/s12942-019-0178-8) and using functions defined below.

```sql
CREATE OR REPLACE FUNCTION array_min(integers int[]) returns int as $$
SELECT min(integers) 
FROM unnest(integers) integers
$$ language sql;
```

### A binary or hard threshold indicator (e.g. of access given distance to a particular destination and a threshold for evaluating this)
```sql
CREATE OR REPLACE FUNCTION threshold_hard(distance int, threshold int, out int) 
RETURNS NULL ON NULL INPUT
AS $$ SELECT (distance < threshold)::int $$
LANGUAGE SQL;
```
### A soft threshold indicator (e.g. of access given distance and threshold)
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

## Examples of analyses using the data
Postgresql is a useful way to manage this data, and can be connected to by your preferred application for analysing or otherwise using data (eg creating maps using QGIS). But it can also be used to analyse and query data: directly using queries in a psql console; by running an SQL script; or by executing parameterised SQL queries from another programming language like R or Python (as we did in the Australian National Liveability Study).

Below some examples are provided for how one could query the data using SQL.  As noted above, this isn't necessary to use the data, it can be loaded into your preferred analysis tool to support your usual way of working.

### Selecting the top and bottom 3-ranking suburbs for a city in terms of liveability
In this query we round the floating point estimates for the within-city Urban Liveability Index and its 13 sub-indicators to 1 decimal place, calculated for Adelaide suburbs, and list the results in descending order limiting to the 'top 3' with regard to liveability within Adelaide.  I multiplied the sub-indicator scores relating to access to destinations by 100, so these are presented on a similar scale to the other measures; they can be interpreted as the suburb average score for dwellings having access to each of these destinations 

If using psql, you can toggle 'expanded output mode' by entering `\x`.  This presents columns within a record as rows, which is convenient when you return results of a query that is too wide for a screen, like this one.

```sql
SELECT ssc_name_2016 "3 Liveable Suburbs in Adelaide",
dwelling,
person,
ROUND(area_ha::numeric,1) area,
ROUND(uli_city::numeric,1) uli_city,
ROUND(li_community_culture_leisure::numeric*100,1) li_community_culture_leisure,
ROUND(li_early_years::numeric*100,1) li_early_years,
ROUND(li_education::numeric*100,1) li_education,
ROUND(li_health_services::numeric*100,1) li_health_services,
ROUND(li_sport_rec::numeric*100,1) li_sport_rec,
ROUND(li_food::numeric*100,1) li_food,
ROUND(li_convenience::numeric*100,1) li_convenience,
ROUND(li_pt_regular_400m::numeric,1) li_pt_regular_400m,
ROUND(li_public_os_large_400m::numeric,1) li_public_os_large_400m,
ROUND(li_street_connectivity_1600m::numeric,1) li_street_connectivity_1600m,
ROUND(li_dwelling_density_1600m::numeric,1) li_dwelling_density_1600m,
ROUND(li_sa1_30_40_housing_stress::numeric,1) li_sa1_30_40_housing_stress,
ROUND(li_sa1_sa3_local_employment::numeric,1) li_sa1_sa3_local_employment
FROM li_2018_suburb_indicators                   
WHERE study_region = 'Adelaide'
ORDER BY uli_city DESC
LIMIT 3;
```

This returns the following, which identifies Glenelg, Adelaide and North Adelaide as the top-3 most liveable suburbs (with results re-formatted as a markdown table for presentation here)

*3 Liveable Suburbs in Adelaide*
|Indicators                     | [Glenelg (SA)](https://www.google.com/maps/place/Glenelg+SA+5045/@-34.9797907,138.5051562,1857m/data=!3m2!1e3!4b1!4m5!3m4!1s0x6ab0c55408d1371b:0x5033654628eb150!8m2!3d-34.980383!4d138.5131191)  | [Adelaide](https://www.google.com/maps/place/Adelaide+SA+5000/@-34.9256374,138.583259,7434m/data=!3m2!1e3!4b1!4m5!3m4!1s0x6ab0ced7a303a4e7:0xb38d70584e1c3e53!8m2!3d-34.9285007!4d138.6007245)     | [North Adelaide](https://www.google.com/maps/place/North+Adelaide+SA+5006/@-34.9090181,138.586206,3718m/data=!3m2!1e3!4b1!4m5!3m4!1s0x6ab0c8947720fdf9:0x5033654628ebac0!8m2!3d-34.9083198!4d138.5919105)|
|-------------------------------|--------------:|-------------:|--------------:|
|dwelling                       | 2321          | 7835         | 3528          |
|person                         | 3354          | 13058        | 6745          |
|area_ha                        | 77.3          | 238.0        | 170.4         |
|uli_city                       | 108.4         | 107.9        | 107.3         |
|li_community_culture_leisure   | 70.8          | 84.1         | 72.0          |
|li_early_years                 | 88.8          | 70.5         | 59.8          |
|li_education                   | 40.1          | 54.4         | 43.9          |
|li_health_services             | 79.5          | 68.7         | 67.8          |
|li_sport_rec                   | 47.2          | 47.3         | 49.3          |
|li_food                        | 61.9          | 56.0         | 73.0          |
|li_convenience                 | 73.2          | 72.9         | 53.4          |
|li_pt_regular_400m             | 89.1          | 78.9         | 84.0          |
|li_public_os_large_400m        | 67.1          | 64.5         | 84.0          |
|li_street_connectivity_1600m   | 112.7         | 142.4        | 124.2         |
|li_dwelling_density_1600m      | 21.3          | 14.1         | 11.1          |
|li_sa1_30_40_housing_stress    | 37.7          | 59.6         | 45.7          |
|li_sa1_sa3_local_employment    | 21.9          | 62.0         | 54.0          |

By changing the following line to retrieve records in ascending rather than descending order, we can get the corresponding bottom 3 suburb records in terms of average liveability for dwellings

```sql
ORDER BY uli_city ASC
```
<details>
  <summary>
    Click to view code with this small alteration
  </summary>
  
```sql
SELECT ssc_name_2016 "3 Lowest-ranking suburbs in Adelaide for Liveability",
dwelling,
person,
ROUND(area_ha::numeric,1) area,
ROUND(uli_city::numeric,1) uli_city,
ROUND(li_community_culture_leisure::numeric*100,1) li_community_culture_leisure,
ROUND(li_early_years::numeric*100,1) li_early_years,
ROUND(li_education::numeric*100,1) li_education,
ROUND(li_health_services::numeric*100,1) li_health_services,
ROUND(li_sport_rec::numeric*100,1) li_sport_rec,
ROUND(li_food::numeric*100,1) li_food,
ROUND(li_convenience::numeric*100,1) li_convenience,
ROUND(li_pt_regular_400m::numeric,1) li_pt_regular_400m,
ROUND(li_public_os_large_400m::numeric,1) li_public_os_large_400m,
ROUND(li_street_connectivity_1600m::numeric,1) li_street_connectivity_1600m,
ROUND(li_dwelling_density_1600m::numeric,1) li_dwelling_density_1600m,
ROUND(li_sa1_30_40_housing_stress::numeric,1) li_sa1_30_40_housing_stress,
ROUND(li_sa1_sa3_local_employment::numeric,1) li_sa1_sa3_local_employment
FROM li_2018_suburb_indicators                   
WHERE study_region = 'Adelaide'
ORDER BY uli_city ASC
LIMIT 3;
```
</details>

|3 Lowest-ranking suburbs in Adelaide for Liveability | [Lewiston](https://www.google.com/maps/place/Lewiston+SA+5501/@-34.6099437,138.5882209,14925m/data=!3m2!1e3!4b1!4m5!3m4!1s0x6ab0a9f8107e1d27:0x5033654628eb6c0!8m2!3d-34.6067942!4d138.5936649)   | [Ward Belt](https://www.google.com/maps/place/Ward+Belt+SA+5118/@-34.5807894,138.6628149,7465m/data=!3m2!1e3!4b1!4m5!3m4!1s0x6aba01d951745d51:0x5033654628ec410!8m2!3d-34.5833781!4d138.6761771)  | [Gawler Belt](https://www.google.com/maps/place/Gawler+Belt+SA+5118/@-34.5756427,138.7279947,1110m/data=!3m1!1e3!4m5!3m4!1s0x6ab9f8d123b75351:0x5033654628eb090!8m2!3d-34.5793104!4d138.7323129)|
|-------------------------------|------------|------------|---------------|
|dwelling                       | 579        | 24         | 315          |
|person                         | 1583       | 69         | 945           |
|area_ha                        | 899.5      | 531.4      | 936.7         |
|uli_city                       | 83.0       | 83.4       | 84.8          |
|li_community_culture_leisure   | 0.0        | 0.2        | 3.2           |
|li_early_years                 | 0.0        | 0.0        | 0.8           |
|li_education                   | 0.0        | 0.0        | 0.3           |
|li_health_services             | 0.0        | 0.0        | 0.1           |
|li_sport_rec                   | 0.0        | 0.3        | 16.5          |
|li_food                        | 0.0        | 0.0        | 0.0           |
|li_convenience                 | 0.0        | 0.0        | 0.1           |
|li_pt_regular_400m             | 0.0        | 0.0        | 0.0           |
|li_public_os_large_400m        | 6.5        | 0.0        | 7.3           |
|li_street_connectivity_1600m   | 13.5       | 17.2       | 17.4          |
|li_dwelling_density_1600m      | 5.1        | 2.6        | 3.8           |
|li_sa1_30_40_housing_stress    | 32.2       | 25.0       | 21.5          |
|li_sa1_sa3_local_employment    | 21.7       | 30.8       | 31.8          |

After running queries like the above, you really want to check out on a map what the context really looks like --- is there a natural explanation for these results, is there missing data, or perhaps a mix of the two?  I've added in hyperlinks to satellite view on Google Maps, which confirms the semi-rural/peri-urban character of these suburbs on Adelaide's northern fringe, separated from the rest of the city by farmland (Lewiston), the Northern Expressway (Ward Belt) and the Sturt Highway (Gawler Belt).  Ward Belt is clearly still mostly rural farming land, however a brief search for the other two suburbs with considerably higher population and dwelling counts using 'Adelaide Lewiston Gawler Belt' on Google Scholar identified a geography Masters thesis from 1998 on 'Population Change in Adelaide's Peri-urban Region: Patterns, Causes and Implications' [Ford, 1998](https://digital.library.adelaide.edu.au/dspace/handle/2440/112763), which could be a good starting point if one was wanting investigate this further.

The top ranking suburb for liveability was Glenelg, a beach side suburb with approximately double the population of Lewiston in an area less than 1/10th the size.  Housing affordability stress (the percentage of persons in the lowest 40% of income spending more than 30% of household income on rent or mortgage) was slightly higher in Glenelg, and opportunities for local employment were comparable, however many-to-most Glenelg residents had access to a range of social infrastructre destinations, well-serviced public transport, as well as large areas of public open space, supported by a relatively well-connected street network.  The absence of walkable access to these amenities in Lewiston is an aspect of the cost of living on the urban fringe in terms of both money and time which the 30:40 measure of housing affordability stress doesn't account for.

### Summarising address level access to public transport in Melbourne
When evaluating access to destinations within recommended distances, like public transport with regular day time weekday service within a walkable distance of 400 m, for address points we calculated this as either a binary indicator (0 or 1) or a continuous indicator (0 to 1), inflecting around a score of 0.5 where a destination was accessible at the given threshold distance.  The latter were used in particular for sub-indicators included in composite indicator scores, as this method of rating access maximises the variation and is arguably more accurate for individual circumstances, with the formula and rationale given in [Higgs et al (2019)](https://doi.org/10.1186/s12942-019-0178-).  Briefly, if a bus stop were accessible at 390 m or 410 m, its intuitive that if you were interested in this level of access being an individual's built environment exposure these distances should score similarly being only arbitrarily different; using a continuous score this is the case (both approximately score 0.5) but using a binary indicator with a threshold of 400 metres the resulting score is at polar extremes (1 or 0, respectively).  For an epidemiological study, the continuous score or even the underlying distance itself may be most relevant to use.  However, for a policy statistic binary indicators are arguably more useful as when aggregated by taking the average they give the proportion of the units being studied having access; multiplied by 100, its the percentage.  As scores are averaged across larger areas, binary scores and continuous scores for access measured in this way converage to become approximately similar --- but percentages calculated using binary scores are easier to explain and more intuitive to understand than 'access scores' which yield pseudo-percentages.  In the context of public transport, the indicator li_pt_regular_400m (a component of the urban liveability index, as implied by its prefix 'li') is a continuous score (or soft threshold0 measure for being within 400 m of public transport with an average weekday service frequency of 30 minutes or less between 7am and 7pm within 400 metres; the binary score (or hard threshold) measure is the indicator trans_07.

So, let's calculate a basic percentage of address points as the average of the proportion of Melbourne address points with access to regular public transport multiplied by 100, with this rounded to 1 decimal place.  This is not how we calculated area summaries in our national study (we presented these as weighted averages with regard to dwellings, or for some projects, persons); we'll introduce how to do this further below.  We'll also calculate a range of other useful statistics for considering the distribution of indicator results, in addition to this  (SD.

```sql
SELECT 
   ROUND(AVG(100*trans_07)::numeric,1) "mean (ie. % with access)",
   ROUND(STDDEV(100*trans_07)::numeric,1) sd,
   ROUND(MIN(trans_07)::numeric,1) min,
   ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY 100*trans_07)::numeric,1) AS p25,
   ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY 100*trans_07)::numeric,1) AS p50,
   ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY 100*trans_07)::numeric,1) AS p75,
   ROUND(MAX(100*trans_07)::numeric,1) max
FROM li_2018_address_indicators
WHERE study_region = 'Melbourne';
```

| mean (ie. % with access) |  sd  | min | p25 | p50  | p75  | max  |
|-------------------------:|-----:|----:|----:|-----:|-----:|-----:|
|                     44.6 | 49.7 | 0.0 | 0.0 | 0.0 | 100.0 | 100.0|
   
So we see that while a minority of urban residential address locations that we measured across the city do have access to public transport with regular weekday service frequency (44.6%), most don't.  But looking at the percentile distribution isn't hugely informative when using a binary indicator --- all address points strictly scored either 0 or 1 for access within 400 m.

If we re-calculate this same measure using the li_pt_regular_400m soft threshold indicator (a component in the urban liveability index)...

```sql
SELECT 
   ROUND(AVG(100*li_pt_regular_400m)::numeric,1) "mean (ie. % with access)",
   ROUND(STDDEV(100*li_pt_regular_400m)::numeric,1) sd,
   ROUND(MIN(li_pt_regular_400m)::numeric,1) min,
   ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY 100*li_pt_regular_400m)::numeric,1) AS p25,
   ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY 100*li_pt_regular_400m)::numeric,1) AS p50,
   ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY 100*li_pt_regular_400m)::numeric,1) AS p75,
   ROUND(MAX(100*li_pt_regular_400m)::numeric,1) max
FROM li_2018_address_indicators
WHERE study_region = 'Melbourne';
```

| mean (ie. % with access) |  sd  | min | p25 | p50  | p75  | max  |
|-------------------------:|-----:|----:|----:|-----:|-----:|-----:|
|                     42.8 | 40.5 | 0.0 | 0.2 | 33.7 | 88.1 | 99.3 |

 then we get a more informative distribution that is 'percentage-like'.  But while it makes more sense to look at, when you go to explain what this is, its in terms of effective access scores and a score based on a sigmoid curve ... its just not so straight forward to communicate to a non-specialised audience.  So --- each of these indicators has its role to play in different contexts.
 
But these are percentages of address points, what if you wanted percentage of dwellings (which has been provided in the area level datasets), or percentage of persons (which wasn't provided)?  We'll look at that now.

The basic formula for a weighted average is the sum of weights multipled by value of interest, divided by the sum of weights.  The reason to calculate an area average weighting for dwellings or people is, if those are the units you are interested in but you didn't or weren't able to directly measure them. This was the case in the Australian National Liveability Study, where we were able to discern address points and restrict these to small areas (Mesh Blocks) with dwellings to estimate exposures for where people could potentially live, although these are highly correlated with where people and dwellings are located they are a bit distinct (ie. we measured address points where dwellings were and where people could be, but not dwellings or people directly).   A weighted average allows you to correct for this to get closer to an estimate for what you're really interested in (e.g. people and dwellings).

So to do this in our study, we first took the Mesh Block average of address points.  Then, we were able to aggregate to larger scales using the Mesh Block dwelling or person counts as a weight, using code like this:

```sql
SELECT
study_region,
SUM(dwelling) dwelling,
SUM(person) person,
(CASE             
    -- if there are no units (dwellings or persons) the indicator is null
    WHEN COALESCE(SUM(dwelling),0) = 0
        THEN NULL
    -- else, calculate the value of the unit weighted indicator
    ELSE                             
       (SUM(dwelling*trans_07::numeric)/SUM(dwelling))::numeric
    END) AS "percentage with access regular public transport"
FROM li_2018_mb_indicators
WHERE study_region = 'Melbourne'
GROUP BY study_region;
```

| study_region | dwelling | person  | percentage with access regular public transport |
|-------------:|---------:|--------:|------------------------------------------------:|
| Melbourne    |  1786894 | 4351584 |                             51.1                |

So, we estimated that just over half of Melbourne dwellings have access to public transport with regular weekday day time service (in Spring 2018, outside school holidays).  This is slightly higher than our earlier naive estimate for 'unique urban addresses in Mesh Blocks with dwellings'.

You can confirm that this is the same result that you would get from the city level aggregate dataset by running 

```sql
SELECT trans_07 FROM li_2018_city_indicators WHERE study_region = 'Melbourne';
```

To do calculate the percentage of people having access instead of dwellings, we replace the variable 'dwelling' with 'person', and we'd still expect to get something similar to the above as these concepts are highly related:

```sql
SELECT
study_region,
SUM(dwelling) dwelling,
SUM(person) person,
(CASE             
    -- if there are no units (dwellings or persons) the indicator is null
    WHEN COALESCE(SUM(person),0) = 0
        THEN NULL
    -- else, calculate the value of the unit weighted indicator
    ELSE                             
       (SUM(person*trans_07::numeric)/SUM(person))::numeric
    END) AS "percentage with access regular public transport"
FROM li_2018_mb_indicators
WHERE study_region = 'Melbourne'
GROUP BY study_region;
```

| study_region | dwelling | person  | percentage with access regular public transport |
|-------------:|---------:|--------:|------------------------------------------------:|
| Melbourne    |  1786894 | 4351584 |                             48.1                |

So, while 51.1% of dwellings had access to regularly serviced public transport, in terms of population its only 48.1%.  One plausible explanation that could be explored is that perhaps this is because household size is larger away from inner suburbs  where  housing is more expensive but are serviced by a mix of trams and trains in addition to buses.

### Using the destination array to query the closest destinations
Note that the code for loading the array dataset above references the 100 record sample test file; for meaningfull results when using this dataset it will be required to load the 11.2GB dataset.  However, the smaller dataset provides a convenient subset for testing queries while getting to know how the data structure works.

So if this were the full dataset of array indicators loaded, you could calculate the mean and standard deviation for distance to closest supermarket like this:

```sql
SELECT study_region, 
COUNT(*),
ROUND(AVG(array_min(dist_m_supermarket)),0) mean_distance_m,
ROUND(stddev(array_min(dist_m_supermarket)),0) sd_distance_m
FROM li_2018_address_distances_3200m_cl 
GROUP BY study_region;
```

Of course, this doesn't return true results when trialling our random sample of address points

|       study_region       | count | mean_distance_m | sd_distance_m|
|-------------------------:|------:|----------------:|-------------:|
| Perth                    |     8 |             893 |           597|
| Canberra                 |     1 |            1080 |              |
| Adelaide                 |    13 |            2025 |          1347|
| Sydney                   |    19 |            1687 |          1341|
| Newcastle - Maitland     |     1 |             953 |              |
| Townsville               |     3 |            1148 |          1062|
| Toowoomba                |     2 |            1372 |           286|
| Brisbane                 |    17 |            1488 |          1614|
| Wollongong               |     2 |             930 |           716|
| Launceston               |     1 |            1926 |              |
| Geelong                  |     1 |             574 |              |
| Mackay                   |     1 |             691 |              |
| Sunshine Coast           |     1 |            5426 |              |
| Gold Coast - Tweed Heads |     2 |            1207 |          1392|
| Melbourne                |    28 |            1173 |           712|

What we can do with the 100 record sample though is look at one individual record, and look how its data is structured and see how it relates to the main estimates for access to destinations for that address in the address destination and indicator databases.

```sql
SELECT 
    gnaf_pid, 
    dist_m_supermarket,
    dist_m_supermarket_osm
FROM li_2018_address_distances_3200m_cl 
LIMIT 1;
```

So displaying this result in extended display mode (/x), this returns the following which represents all the destinations of the types queried accessible within 3200m, or the closest if there is none within 3200m. 

```
-[ RECORD 1 ]----------+--------------------------------------------------------------------------------------
gnaf_pid               | GAVIC419575561
dist_m_supermarket     | {427,640,669,1107,1569,1669,2377,2451,2519,2649,2680,2718,2874,2903,2983,3085}
dist_m_supermarket_osm | {415,419,422,583,648,726,1102,1158,1459,1673,2004,2468,2747,2760,2882,2882,3004,3045}
```

For this particular address point, the estimated distance to the closest major chain supermarket was 427 metres; however a supermarket identified using OpenStreetMap-derived data was 415 m away, so that would be the estimate used for distance to closest supermarket for this address point. 

To calculate this using the custom functions provided above, we could run

```sql
SELECT 
    LEAST(
        array_min(dist_m_supermarket),
        array_min(dist_m_supermarket_osm)
        ) 
FROM li_2018_address_distances_3200m_cl 
WHERE gnaf_pid = 'GAVIC419575561';
```

This gives the result of 415 m as the closest supermarket, considered across web-scraped major chain supermarkets and OpenStreetMap derived supermarkets.

To get the count of supermarkets, we can't pool the major chain and OpenStreetMap-derived supermarket datasets as this would be expected to result in a large degree of double counting.   What can be done however, is to evaluate the count of supermarkets using the two datasets seperately and then take the one with the greatest value under the assumption that both are approximately correct, but the one with the larger count is a more complete representation for that particular location.  To do this (as we did), involves the following:

```sql
SELECT 
    count_in_threshold(dist_m_supermarket,1600) "major chain supermarkets",
    count_in_threshold(dist_m_supermarket_osm,1600) "openstreetmap supermarkets",
    GREATEST(
        COALESCE(count_in_threshold(dist_m_supermarket,1600),0),
        COALESCE(count_in_threshold(dist_m_supermarket_osm,1600),0)
    ) AS supermarkets
FROM li_2018_address_distances_3200m_cl 
WHERE gnaf_pid = 'GAVIC419575561';
```

| major chain supermarkets | openstreetmap supermarkets | supermarkets |
|-------------------------:|---------------------------:|-------------:|
|                        5 |                          9 |            9 |

This query indicates that there are 9 supermarkets located within 1600 metres of this address point, with this being evaluated based on usage of the OpenStreetMap-derived supermarket data, which appeared to be a more comprehensive representation of the offerings in this neighbourhood.

The same result is achieved by retrieving the indicator 'food_12', for "Count of supermarkets within 1600 m (OSM or 2017 in-house)":

```sql
SELECT food_12 FROM li_2018_address_indicators WHERE gnaf_pid = 'GAVIC419575561';
```

### Using the areas of open space array data to query public open space access

When developing our study, we designed it to support others using using our data linked with geocoded survey participants to construct their own indicators from our measures.  This was done for the Australian Early Development Census dataset in particular, for which the researchers were interested in a large number of permutations of indicators relating to distance, size, and features of parks.   So, we developed an approach to allow for post hoc querying of the database of areas of open space to identify those spaces meeting criterion.

This is a bit of a complex process, so its good to understand how the data structure works.

Using psql, you can describe the public open space table by entering `\d li_2018_public_open_space`, which if you've loaded it in using the above directions should return the following information:

```
anls_2018=# \d li_2018_public_open_space
                   Table "public.li_2018_public_open_space"
      Column       |          Type           | Collation | Nullable | Default
-------------------+-------------------------+-----------+----------+---------
 aos_id            | bigint                  |           | not null |
 attributes        | jsonb                   |           |          |
 numgeom           | bigint                  |           |          |
 aos_ha_public     | double precision        |           |          |
 aos_ha_not_public | double precision        |           |          |
 aos_ha            | double precision        |           |          |
 aos_ha_water      | double precision        |           |          |
 has_water_feature | boolean                 |           |          |
 water_percent     | numeric                 |           |          |
 locale            | text                    |           | not null |
 co_location_100m  | jsonb                   |           |          |
 geom_public       | geometry(Geometry,7845) |           |          |
 geom_water        | geometry(Geometry,7845) |           |          |
 geom              | geometry(Geometry,7845) |           |          |
Indexes:
    "li_2018_public_open_space_pkey" PRIMARY KEY, btree (aos_id, locale)
    "li_2018_public_open_space_aos_jsb_idx" gin (attributes)
    "li_2018_public_open_space_co_location_idx" gin (co_location_100m)
    "li_2018_public_open_space_geom_idx" gist (geom)
    "li_2018_public_open_space_geom_public_idx" gist (geom_public)
    "li_2018_water_open_space_geom_water_idx" gist (geom_water)
```

These are records of areas of open space, indexed uniquely by a combination of 'aos_id' (which is unique within each city), and 'locale' which is the city name.  Areas of open space are a collection of contiguous open spaces identified from OpenStreetMap which have been identified to have characteristics related to 'open space', and this particular dataset has been restricted to those areas identified as having some amount of publicly accessible area.   These may be parks, squares, plazas or other natural spaces or areas with sporting/recreation facilities which appear to be publicly accessible; these are not strictly 'green spaces'.   Supplementary analysis with satellite imagery data relating them to NDVI or vegetation percentage could possibly be used to derive a dataset of publicly accessible green spaces; we haven't done this here.  The aos_ha_public field contains the area in hectares of the portion of each area of contiguous open space identified as being publicly accessible, and can be used for queries like for 'public open space larger than 1.5 hectares'.  The attributes and specific tags of open spaces within each area of open space are contained within the 'attributes' field in JSON format. Tags were used to identify features in areas of open space associated with 'blue space', and this dataset could also be queried to identify access to blue space.   In addition an analysis was done identifying other points of interest including public toilets and other destinations within 100 m of each area of open space, and so in addition to size and features of open spaces, they can also be queried relating to presence or count of nearby accessible amenities.  Geometry fields for the overall area of open space, and the portions identified as being publicly accessible or associated with water features have also been provided and may be used for spatial analyses and mapping.

Let's look at a single record for an area of open space, showing how we can view the JSON attribute and co-location data in a readable format.   I've restricted this to an area of open space comprised of fewer than four individual but contiguous open spaces so the result is easier to read when included below:

```sql
SELECT
    aos_id,
    locale city,
    jsonb_pretty(attributes) attributes,
    aos_ha_public,
    water_percent,
    jsonb_pretty(co_location_100m) co_location_100m
FROM li_2018_public_open_space
WHERE numgeom < 4
LIMIT 1;
`
 aos_id |   city   |                        attributes                        |  aos_ha_public   | water_percent |   co_location_100m
--------+----------+----------------------------------------------------------+------------------+---------------+----------------------
   7069 | adelaide | [                                                       +| 272.945592510754 |           100 | [                   +
        |          |     {                                                   +|                  |               |     "viewpoint_osm",+
        |          |         "os_id": 53,                                    +|                  |               |     "toilets"       +
        |          |         "area_ha": 272.945592510754,                    +|                  |               | ]
        |          |         "natural": "water",                             +|                  |               |
        |          |         "in_school": false,                             +|                  |               |
        |          |         "is_school": false,                             +|                  |               |
        |          |         "roundness": 0.11163868357276,                  +|                  |               |
        |          |         "tags_line": [                                  +|                  |               |
        |          |             {                                           +|                  |               |
        |          |                 "waterway": "dam"                       +|                  |               |
        |          |             },                                          +|                  |               |
        |          |             {                                           +|                  |               |
        |          |                 "waterway": "river"                     +|                  |               |
        |          |             }                                           +|                  |               |
        |          |         ],                                              +|                  |               |
        |          |         "public_access": true,                          +|                  |               |
        |          |         "water_feature": true,                          +|                  |               |
        |          |         "within_public": false,                         +|                  |               |
        |          |         "linear_feature": true,                         +|                  |               |
        |          |         "min_bounding_circle_area": 24449015.6794857,   +|                  |               |
        |          |         "acceptable_linear_feature": false,             +|                  |               |
        |          |         "min_bounding_circle_diameter": 5579.37752737447+|                  |               |
        |          |     }                                                   +|                  |               |
        |          | ]                                                        |                  |               |
```

So from this we can see that this open space has been tagged as a natural water feature, specifically a river/dam of 273 hectares in area, and it has a viewpoint and toilet located somewhere within 100 m Euclidean (crow flies) distance of its boundary, or within it (unlikely given its a dam).  There are an additional set of morphological characteristics, about the shape of the feature, as large water ways present some specific challenges when evaluating contiguous area (see [Description of method of identifying public open space using OpenStreetMap](https://github.com/carlhiggs/Australian-National-Liveability-Study-2018-datasets-supplementary-material/blob/main/Identifying%20public%20open%20space%20using%20OpenStreetMap.md#description-of-method-of-identifying-public-open-space-using-openstreetmap)).  The assumption for features like this is that you can walk around them, that they are in fact publicly accessible, and that this is a meaningful type of public open space.  In this case, I loaded up the public open space dataset in QGIS and selected this record to locate it, and based on the tagging information and the view on a satellite this appears to be the case (see Millbrook Reservoir [here](https://www.google.com/maps/place/Millbrook+Reservoir), and according to Google reviews 'it's a great place!'; 'a bit low on water', 'lovely place to visit').  But it is about 7km east of Adelaide's urban area (we included areas up to 10km outside of this when doing analysis as these are still accessible), so not really interesting as a public open space within walkable distance of an urban address.

We imported the 100 random sample of data from the li_2018_aos_jsonb dataset which contains estimates for distance to each open space for address points, so let's look at that as a start for looking into how we query accessible open spaces:

SELECT gnaf_pid, jsonb_pretty(attributes) FROM li_2018_aos_jsonb LIMIT 1;

</details>

The results for this are pretty full on; this particular address in Queensland has access to 127 identified areas of open space within 3200m walking distance. So, I'll just paste a subset so you cna get the idea:

```
    gnaf_pid    |       jsonb_pretty
----------------+--------------------------
 GAQLD155543323 | [                       +
                |     {                   +
                |         "aos_id": 9482, +
                |         "distance": 1683+
                |     },                  +
                |     {                   +
                |         "aos_id": 9483, +
                |         "distance": 1419+
                |     },                  +
                |     {                   +
                |         "aos_id": 9485, +
                |         "distance": 1388+
                |     },                  +
                ...  (123 records omitted!)                       
                |     {                   +
                |         "aos_id": 9481, +
                |         "distance": 1019+
                |     }                   +
                | ]
(1 row)
```

However, if we use a slightly more complicated query to restrict to areas of open space within 400m, there are just two recorded within that distance:

SELECT gnaf_pid,
	        (obj->>'aos_id')::int AS aos_id,
	        (obj->>'distance')::int AS distance
FROM li_2018_aos_jsonb,
    jsonb_array_elements(attributes) obj
WHERE gnaf_pid = 'GAQLD155543323'
  AND (obj->>'distance')::int < 400;

|    gnaf_pid    | aos_id | distance |
|---------------:|-------:|---------:|
| GAQLD155543323 |   8043 |      188 |
| GAQLD155543323 |   8047 |       71 |

Now, let's try a query for our 100 sample points to find all those with access to an areas of open space of area 1.5 hectares or larger with access to a toilet:

```sql
SELECT 
    o.gnaf_pid,
    o.locale,
    COUNT(o.*),
    array_agg(o.aos_id) large_aos_with_toilet_within_400m
FROM
	(SELECT gnaf_pid,
            locale,
	        (obj->>'aos_id')::int AS aos_id,
	        (obj->>'distance')::int AS distance
	FROM li_2018_aos_jsonb,
	    jsonb_array_elements(attributes) obj) o 
	LEFT JOIN li_2018_public_open_space pos 
           ON o.aos_id = pos.aos_id 
          AND o.locale=pos.locale
WHERE pos.aos_id IS NOT NULL
  AND aos_ha_public >= 1.5 
  AND co_location_100m ? 'toilets'
  AND distance < 400
GROUP BY o.gnaf_pid,o.locale;
```

|    gnaf_pid    |       locale       | count | large_aos_with_toilet_within_400m |
|----------------|--------------------|------:|-----------------------------------|
| GANSW704022201 | syd                |     1 | {4852}                            |
| GANSW704073149 | newcastle_maitland |     1 | {2387}                            |
| GANSW704449374 | syd                |     2 | {5655,5650}                       |
| GANSW704693488 | syd                |     1 | {7591}                            |
| GANSW705009126 | syd                |     1 | {4125}                            |
| GANSW705030923 | newcastle_maitland |     1 | {1456}                            |
| GANSW705812628 | syd                |     1 | {2190}                            |
| GANSW710758685 | syd                |     2 | {12732,12731}                     |
| GANSW712462212 | wollongong         |     2 | {496,521}                         |
| GANSW715394401 | newcastle_maitland |     2 | {2187,2387}                       |
| GANSW716872025 | syd                |     1 | {3625}                            |
| GAQLD155036687 | bris               |     2 | {1381,1383}                       |
| GAQLD156728035 | bris               |     1 | {4712}                            |
| GAQLD157781890 | bris               |     1 | {8934}                            |
| GAQLD157815302 | bris               |     1 | {6893}                            |
| GAQLD162340538 | bris               |     1 | {3891}                            |
| GASA_415505615 | adelaide           |     1 | {2121}                            |
| GATAS702296754 | hobart             |     1 | {301}                             |
| GAVIC411542514 | melb               |     2 | {6521,6522}                       |
| GAVIC420546097 | melb               |     1 | {5110}                            |
| GAVIC420954909 | melb               |     2 | {9531,9525}                       |
| GAVIC423801845 | albury_wodonga     |     1 | {1113}                            |
| GAWA_146560420 | perth              |     1 | {4341}                            |
| GAWA_147174310 | perth              |     1 | {4002}                            |
| GAWA_147300989 | perth              |     1 | {4252}                            |
| GAWA_147777655 | perth              |     2 | {9297,9172}                       |

So, based on this query of our random sample of 100 address points taken from 21 cities, 26 of these have access within 400m walk to at least one area of open space with a publicly accessible area of at least 1.5 hectares and a toilet.

In QGIS I identified this first record in Sydney by querying the attributes of the li_2018_public_open_space table with the [advanced expression](https://docs.qgis.org/3.22/en/docs/pyqgis_developer_cookbook/expressions.html) `("aos_id" = 4852) AND ("locale"='syd')` and having identified the location, I then found this using [Google Maps](https://www.google.com/maps/place/33%C2%B054'07.3%22S+150%C2%B059'51.7%22E/@-33.902037,150.9945219,941m).

![Example of an area of public open space identified in Sydney using QGIS](./Example%20of%20an%20area%20of%20public%20open%20space%20identified%20in%20Sydney%20using%20QGIS.jpg?raw=true "Example of an area of public open space identified in Sydney using QGIS")

This particular area of open space is formed as a combination of Manuka Reserve and Carysfield Park in the suburb of Bass Hill in Sydney, New South Wales.  By looking at this on the above web map, it seems that ideally this area of open space may have also included an additional BMX track which is next to these two parks, which is apparently also used by children (reviews are mixed "Nice for skating. Kids like this place", but also "A desolate waste land that was once a bmx track"!); in any case, this was an apparent omission in our analysis identifying openstreetmap areas of open space, and highlights one of the limitations of this approach --- its possible that the dataset of areas of (public) open space fails to identify some locations, and its also possible that some locations identified could be misclassified.  This is a risk with all data, regardless of source, and we describe the approach we took to mitigating this risk and validating our open space data in the technical validation section of our data descriptor manuscript.   And in this case, the omission of this particular BMX track (of dubious quality, apparently) is unlikely to have impacted results in a meaningful way.