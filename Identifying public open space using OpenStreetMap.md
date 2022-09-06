# Description of method of identifying public open space using OpenStreetMap 
*Supplementary section from main manuscript Policy-relevant health-related liveability indicator datasets for residential addresses in Australia’s 21 largest cities* 

We operationalised the Victorian Planning Authority definition of public open space [^1], so that it could be applied to OpenStreetMap, as a subset of a broader concept of [Areas of Open Space](https://github.com/healthy-liveable-cities/australian-national-liveability-study/blob/main/15_aos_setup.py) (AOS).  If in an individual open space spatial feature which might be identified as being public were identified as being a public open space, it may not actually be accessible due to hierarchies of accessibility.  For example, a park which is next to another park which is next to a road; you get to that first park by going through the second, and  depending on your outlook its all the one 'Area of Open Space'. By creating a nested hierarchy of contiguous open space, we are able to identify what is the contiguous area of that area of open space which is publicly accessible.  Some spaces within an other-wise publicly accessible area of open space may be private or require a fee to entry (e.g. a zoo within a park, as is the case of Royal Park in Melbourne); the latter may play a role as an amenity or attraction to the public open space, but shouldn’t count towards its publicly accessible area when evaluating size.  The below implementation of AOS features can be queried based on some definition of interest, for example a definition of 'Public Open Space' to suit a specific policy setting.  If access is pre-evaluated for a reasonable distance (i.e. 3200 metres) for addresses to all areas of open space, based on pseudo-entry points generated at regular 20 metre intervals within 30 metres of the pedestrian network’s line representation, then post hoc querying of access to public open space based on ad hoc characteristics becomes possible: for example, a public open space with a water feature, and within 100 metres of both a café and a public toilet. 
 
The following provides a plain language description of stages of processing along with snippets of code and lists of values used, which in the actual project were defined in a configuration file stored external to code.  Collectively, the code and the parameters in the project configuration are used to define a set of spatial features termed 'Areas of Open Space', and identify a subset of AOS which the available information suggests may be considered 'public'.  When we ran the code, the parameters were drawn to complete the queries which used; those completed queries are used below to describe the creation of the OpenStreetMap-derived datasets of areas of open space and public open space. 
 
In addition to the VPA definition of public open space, we identified key-value pairs used fo classification of open space according to tagged characteristics using OpenStreetMap TagInfo, as well as tags listed on the historic [Green space access ITO map](https://wiki.openstreetmap.org/wiki/Green_space_access_ITO_map)’ OpenStreetMap Wiki page and following the [Australian Tagging Guidelines](https://wiki.openstreetmap.org/wiki/Australian_Tagging_Guidelines). 
  
1. First we identify areas that are clearly not open space (NOS) drawing on exclusion criteria based on key-value pair tags from OpenStreetMap (OSM) 
```sql 
-- Create a 'Not Open Space' table 
DROP TABLE IF EXISTS not_open_space; 
CREATE TABLE not_open_space AS 
SELECT ST_Union(geom) AS geom FROM osm_20181001_polygon p 
WHERE military IS NOT NULL 
   OR agricultural IS NOT NULL 
   OR forestry IS NOT NULL 
   OR "access" IN ('employee','no','private','privates','staff') 
   OR "landuse" IN ('military','industrial'); 
```

2. Now we create a preliminary open space (OS) table.  
 If certain keys (see below) are not null, they are flagged as an OS (note this does not mean they are public). Some excluded areas may be located within valid OS, and we will deal with such exclusions later.  Some features have values for they keys 'landuse' and 'boundary' which flag them as open space features.   
```sql
-- Create an 'Open Space' table 
DROP TABLE IF EXISTS open_space; 
CREATE TABLE open_space AS 
SELECT p.* FROM osm_20181001_polygon p 
WHERE (p.leisure IS NOT NULL 
    OR p.natural IS NOT NULL 
    OR p.sport IS NOT NULL 
    OR p.landuse IN ('common','conservation','forest','garden','leisure','park','pitch','recreation_ground','sport','trees','village_green','winter_sports','wood','dog_park','nature_reserve','off_leash ','sports_centre') 
    OR p.boundary IN ('protected_area','national_park','nature_reserve','forest','water_protection_area','state_forest','state_park','regional_park','park','county_park') 
    OR p.beach IS NOT NULL 
    OR p.river IS NOT NULL 
    OR p.water IS NOT NULL 
    OR p.waterway IS NOT NULL 
    OR p.wetland IS NOT NULL ); 
```

3. A new unique ID is added for OS features, as the given OSM (osm_id) is not reliably unique 
```sql
-- Create unique POS id and add indices 
ALTER TABLE open_space ADD COLUMN os_id SERIAL PRIMARY KEY; 
CREATE INDEX open_space_idx ON open_space USING GIST (geom); 
CREATE INDEX  not_open_space_idx ON not_open_space USING GIST (geom); 
```

4. We remove any portions of OS features' geometry which overlaps the excluded NOS regions we defined earlier.  If no geometry remains for an OS it is entirely excluded, and so deleted from the OS feature set.   
```sql
-- Remove any portions of open space geometry intersecting excluded regions 
UPDATE open_space p 
   SET geom = ST_Difference(p.geom,x.geom) 
  FROM not_open_space x 
 WHERE ST_Intersects(p.geom,x.geom); 
-- Drop any empty geometries (ie. those which were wholly covered by excluded regions) 
DELETE FROM open_space WHERE ST_IsEmpty(geom); 
```

5.  We add in a variable for OS feature size 
```sql
-- Create variable for park size 
ALTER TABLE open_space ADD COLUMN area_ha double precision; 
UPDATE open_space SET area_ha = ST_Area(geom)/10000.0; 
```

 6. We associate each OS with attributes from any line and point features which intersect if they has values which may relate to the OS concept 
In particular, any line with records relating to amenities, leisure activities, natural environment features, tourism, waterways (e.g. rivers may be a line feature going through parks) or historic 'points of interest'. 
```sql
-- Create variable for associated line tags 
ALTER TABLE open_space ADD COLUMN tags_line jsonb; 
WITH tags AS ( 
SELECT o.os_id, 
              jsonb_strip_nulls(to_jsonb((SELECT d FROM (SELECT l.amenity,l.leisure,l."natural",l.tourism,l.waterway) d)))AS attributes 
FROM osm_20181001_line  l,open_space o 
WHERE ST_Intersects (l.geom,o.geom) ) 
UPDATE open_space o SET tags_line = attributes 
FROM (SELECT os_id, 
             jsonb_agg(distinct(attributes)) AS attributes 
        FROM tags 
       WHERE attributes != '{}'::jsonb 
    GROUP BY os_id) t 
WHERE o.os_id = t.os_id 
  AND t.attributes IS NOT NULL 
; 
   
-- Create variable for associated point tags 
ALTER TABLE open_space ADD COLUMN tags_point jsonb; 
WITH tags AS ( 
SELECT o.os_id, 
       jsonb_strip_nulls(to_jsonb((SELECT d FROM (SELECT l.amenity,l.leisure,l."natural",l.tourism,l.historic) d)))AS attributes 
FROM osm_20181001_point l,open_space o 
WHERE ST_Intersects (l.geom,o.geom) ) 
UPDATE open_space o SET tags_point = attributes 
FROM (SELECT os_id, 
             jsonb_agg(distinct(attributes)) AS attributes 
        FROM tags 
       WHERE attributes != '{}'::jsonb 
    GROUP BY os_id) t 
WHERE o.os_id = t.os_id 
  AND t.attributes IS NOT NULL 
; 
```

 7.  We create an indicator to record whether the available information suggests that an OS feature is a water feature (ie. blue space). 
Specific values are evaluated for the keys 'natural','landuse' and leisure; likewise, certain water sports imply presence of water, and other keys with any value are also water features (beach, river, water, waterway, wetland). 
```sql
-- Create water feature indicator 
ALTER TABLE open_space ADD COLUMN water_feature boolean; 
UPDATE open_space SET water_feature = FALSE; 
UPDATE open_space SET water_feature = TRUE 
 WHERE "natural" IN ('atoll','awash_rock','bay','beach','coastal','coastline','coastline_old','glacier','high-water','hot_spring','island','islet','lake','marsh','oasis','old_coastline_import','peninsula','pond','river','river_terrace','riverbank','riverbed','shoal','spring','strait','stream','swamp','swimming_pool','underwater_rock','unprotected_spring','unprotected_well','water','water_park','waterfall','waterhole','waterway','wetland') 
    OR landuse IN ('atoll','awash_rock','bay','beach','coastal','coastline','coastline_old','glacier','high-water','hot_spring','island','islet','lake','marsh','oasis','old_coastline_import','peninsula','pond','river','river_terrace','riverbank','riverbed','shoal','spring','strait','stream','swamp','swimming_pool','underwater_rock','unprotected_spring','unprotected_well','water','water_park','waterfall','waterhole','waterway','wetland') 
    OR leisure IN ('atoll','awash_rock','bay','beach','coastal','coastline','coastline_old','glacier','high-water','hot_spring','island','islet','lake','marsh','oasis','old_coastline_import','peninsula','pond','river','river_terrace','riverbank','riverbed','shoal','spring','strait','stream','swamp','swimming_pool','underwater_rock','unprotected_spring','unprotected_well','water','water_park','waterfall','waterhole','waterway','wetland') 
    OR sport IN ('swimming','surfing','canoe','scuba_diving','rowing','sailing','fishing','water_ski','water_sports','diving','windsurfing','canoeing','kayak') 
    OR beach IS NOT NULL 
    OR river IS NOT NULL 
    OR water IS NOT NULL 
    OR waterway IS NOT NULL 
    OR wetland IS NOT NULL; 
```

8. Some water features are by nature linear, and cause challenges for incorporating into broader areas of open space; we identify them first based on name.  
```sql
ALTER TABLE open_space ADD COLUMN linear_waterway boolean; 
UPDATE open_space SET linear_waterway = TRUE 
 WHERE waterway IN ('river','riverbank','riverbed','strait','waterway','stream','ditch','river','drain','canal','rapids','drystream','brook','derelict_canal','fairway') 
    OR "natural" IN ('river','riverbank','riverbed','strait','waterway','stream','ditch','river','drain','canal','rapids','drystream','brook','derelict_canal','fairway') 
    OR landuse IN ('river','riverbank','riverbed','strait','waterway','stream','ditch','river','drain','canal','rapids','drystream','brook','derelict_canal','fairway') 
    OR leisure IN ('river','riverbank','riverbed','strait','waterway','stream','ditch','river','drain','canal','rapids','drystream','brook','derelict_canal','fairway') ; 
```

 9. We create geometries for water features in particular so that if desired these can be readily mapped seperately 
```sql
-- Create variable for AOS water geometry 
ALTER TABLE open_space ADD COLUMN water_geom geometry; 
UPDATE open_space SET water_geom = geom WHERE water_feature = TRUE; 
```
  
10. We record attributes to determine the 'roundness' and 'linearity' of features 

```sql 
-- Create variables for determining roundness of feature 
ALTER TABLE open_space ADD COLUMN min_bounding_circle_area double precision; 
UPDATE open_space SET min_bounding_circle_area = ST_Area(ST_MinimumBoundingCircle(geom)); 
  
ALTER TABLE open_space ADD COLUMN min_bounding_circle_diameter double precision; 
UPDATE open_space SET min_bounding_circle_diameter = 2*sqrt(min_bounding_circle_area / pi()); 
  
ALTER TABLE open_space ADD COLUMN roundness double precision; 
UPDATE open_space SET roundness = ST_Area(geom)/(ST_Area(ST_MinimumBoundingCircle(geom))); 
  
-- Create indicator for linear features informed through EDA of OS topology 
ALTER TABLE open_space ADD COLUMN linear_feature boolean; 
UPDATE open_space SET linear_feature = FALSE; 
UPDATE open_space SET linear_feature = TRUE 
WHERE (area_ha > 0.5 AND roundness < 0.25) 
   OR ( 
       waterway IS NOT NULL 
       OR river IS NOT NULL 
      ); 
```
 
 11.  We use a set of rules to determine if an otherwise identified 'linear' OS is acceptable in terms of aggregation into a broader Area of Open Space (AOS) 
These rules are explained further in comments below. 

```sql
---- Create 'Acceptable Linear Feature' indicator 
ALTER TABLE open_space ADD COLUMN acceptable_linear_feature boolean; 
UPDATE open_space SET acceptable_linear_feature = FALSE WHERE linear_feature = TRUE; 
UPDATE open_space o SET acceptable_linear_feature = TRUE 
FROM (SELECT os_id,geom FROM open_space WHERE linear_feature = FALSE) nlf 
WHERE o.linear_feature IS TRUE 
  AND  ( 
        -- acceptable if within a non-linear feature 
        ST_Within(o.geom,nlf.geom) 
        OR  ( 
        -- acceptable if it intersects a non-linear feature if it is not too long 
        -- and it has some reasonably strong relation with a non-linear feature 
        o.min_bounding_circle_diameter < 800 
        AND ( 
             -- a considerable proportion of geometry is within the non-linear feature 
            (ST_Intersects(o.geom,nlf.geom) 
            AND 
            (st_area(st_intersection(o.geom,nlf.geom))/st_area(o.geom)) > .2) 
            OR ( 
                -- acceptable if there is sufficent conjoint distance (> 50m) with a nlf 
                ST_Length(ST_CollectionExtract(ST_Intersection(o.geom,nlf.geom), 2)) > 50 
                AND o.os_id < nlf.os_id 
                AND ST_Touches(o.geom,nlf.geom))
            )
        ) 
    ); 
-- a feature identified as linear is acceptable as an OS if it is 
--  large enough to contain an OS of sufficient size (0.4 Ha?) 
-- (suggests it may be an odd shaped park with a lake; something like that) 
-- Still, if it is really big its acceptability should be constrained 
-- hence limit of min bounding circle diameter 
UPDATE open_space o SET acceptable_linear_feature = TRUE 
FROM open_space alt 
WHERE o.linear_feature IS TRUE 
  AND  o.acceptable_linear_feature IS FALSE 
  AND o.min_bounding_circle_diameter < 800 
  AND  o.geom && alt.geom 
  AND st_area(st_intersection(o.geom,alt.geom))/10000.0 > 0.4 
  AND o.os_id != alt.os_id; 
```
  
 12. Schools are a subset of Open Space; we now identify those OS features which are located in school polygons (which we set up in an earlier script) 
Schools include primary schools, secondary schools and universities. To set up schools, we first selected any polygons from OSM with amenity or landuse in school, college or university.  If an OSM school polygon intersects a school point sourced from the ACARA dataset it is taken to represent that school.  Otherwise, if a school polygon is within 100m of a point which wasn't otherwise matched, it is taken as representative of that school.  If a school is present in ACARA, but could not be matched to a school in OSM, then we create a pseudo geometry for it using a 20m buffered point.  This serves as an access point to that school when doing network analysis (e.g. where is the closest school), however is conservative with the extent of the generated geometry since we were unable to determine the school's true extent from the given point location alone. 
 
 
If an OS feature intersects one of our school polygons, it is flagged as being 'in_school'.  Implicitly, this means it is not public. 
 
```sql
-- Set up OS for distinction based on location within a school 
ALTER TABLE open_space ADD COLUMN in_school boolean; 
UPDATE open_space SET in_school = FALSE; 
UPDATE open_space SET in_school = TRUE 
  FROM school_polys 
 WHERE ST_CoveredBy(open_space.geom,school_polys.geom); 
ALTER TABLE open_space ADD COLUMN is_school boolean; 
UPDATE open_space SET is_school = FALSE; 
```

13. School polygons (as described above) are inserted as special class of OS features, retaining associated ACARA or OSM tags describing the school's attributes  
```sql
-- Insert school polygons in open space, restricting to relevant de-identified subset of tags (ie. no school names, contact details, etc) 
ALTER TABLE open_space ADD COLUMN school_tags jsonb; 
INSERT INTO open_space (amenity,area_ha,school_tags,tags,is_school,geom) 
SELECT  amenity, 
        area_ha, 
        school_tags, 
        slice(tags, 
              ARRAY['amenity', 
                  'designation'     , 
                  'fee'             , 
                  'grades'          , 
                  'isced'           , 
                  'school:gender'   , 
                  'school:enrolment', 
                  'school:selective', 
                  'school:specialty']), 
        is_school, 
        geom 
FROM school_polys; 
```

14. We remove tags which may identify a park by name (which could be problematic if linked to a survey participant especially along with distance) 
```sql
-- Remove potentially identifying tags from records 
UPDATE open_space SET tags =  tags - (SELECT array_agg(tags) from (SELECT DISTINCT(skeys(tags)) tags FROM open_space) t WHERE tags ILIKE '%name%') - ARRAY['addr:city','addr:full','addr:place','addr:postcode','addr:province','addr:street','website','wikipedia','description','addr:housenumber','addr:interpolation','designation','email','phone','ref:capad2014_osm','nswlpi:cadid','wikidata','url'] 
; 
```

 15. Create a 'public' indicator based on the available information 
Based on the VPA definition, our audit of OSM tags, and prior case studies for POS creation, we identified a series of tags which OS features may have which would mean they should not be considered public.  Some of these may flag indoors areas, many identify commercial enterprises or private clubs.  However, such features (e.g. a zoo or gallery in a park) may be located within a broader public access area, and so we retain them in the dataset since they offer further rich information about our features. 
 
For the Melbourne test, we did not record swimming pools and swimming as public open space.  However, this is likely not an appropriate criteria to apply as a rule nationally where there are many more locations where these may indicate public facilities (e.g. ocean baths, beaches).  As such this exclusion criteria is not implemented below (it is commented out, preceded by two hyphens). 
```sql
-- Create variable to indicate public access 
ALTER TABLE open_space ADD COLUMN IF NOT EXISTS public_access boolean; 
UPDATE open_space SET public_access = FALSE; 
UPDATE open_space SET public_access = TRUE 
  WHERE is_school = FALSE 
    AND in_school = FALSE 
    AND ("amenity" IS NULL OR "amenity" NOT IN ('aged_care','animal_boarding','allotments','animal_boarding','bank','bar','biergarten','boatyard','carpark','childcare','casino','church','club','club_house','college','conference_centre','embassy','fast_food','garden_centre','grave_yard','hospital','gym','kindergarten','monastery','motel','nursing home','parking','parking_space','prison','retirement','retirement_home','retirement_village','school','scout_hut','university','golf_course','horse_riding', 'racetrack','summer_camp','sports_club','stadium','sports_centre','school','showground','school_playing_field','horse_racing','show_grounds','school_playing_fields','archery','badminton','bocce','boules','bowls','croquet','dog_racing','equestrian','futsal','gokarts','golf','greyhound_racing','horse_racing','karting','lacross','lacrosse','lawn_bowls','motocross','motor','motorcycle','polo','shooting','trugo','customers','alpine_hut','apartment','aquarium','bed_and_breakfast','caravan_site','chalet','gallery','guest_house','hostel','hotel','information','motel','museum','theme_park','zoo')) 
    AND ("leisure" IS NULL OR "leisure" NOT IN ('aged_care','animal_boarding','allotments','animal_boarding','bank','bar','biergarten','boatyard','carpark','childcare','casino','church','club','club_house','college','conference_centre','embassy','fast_food','garden_centre','grave_yard','hospital','gym','kindergarten','monastery','motel','nursing home','parking','parking_space','prison','retirement','retirement_home','retirement_village','school','scout_hut','university','golf_course','horse_riding', 'racetrack','summer_camp','sports_club','stadium','sports_centre','school','showground','school_playing_field','horse_racing','show_grounds','school_playing_fields','archery','badminton','bocce','boules','bowls','croquet','dog_racing','equestrian','futsal','gokarts','golf','greyhound_racing','horse_racing','karting','lacross','lacrosse','lawn_bowls','motocross','motor','motorcycle','polo','shooting','trugo','customers','alpine_hut','apartment','aquarium','bed_and_breakfast','caravan_site','chalet','gallery','guest_house','hostel','hotel','information','motel','museum','theme_park','zoo')) 
    AND ("area" IS NULL OR "area" NOT IN ('aged_care','animal_boarding','allotments','animal_boarding','bank','bar','biergarten','boatyard','carpark','childcare','casino','church','club','club_house','college','conference_centre','embassy','fast_food','garden_centre','grave_yard','hospital','gym','kindergarten','monastery','motel','nursing home','parking','parking_space','prison','retirement','retirement_home','retirement_village','school','scout_hut','university','golf_course','horse_riding', 'racetrack','summer_camp','sports_club','stadium','sports_centre','school','showground','school_playing_field','horse_racing','show_grounds','school_playing_fields','archery','badminton','bocce','boules','bowls','croquet','dog_racing','equestrian','futsal','gokarts','golf','greyhound_racing','horse_racing','karting','lacross','lacrosse','lawn_bowls','motocross','motor','motorcycle','polo','shooting','trugo','customers','alpine_hut','apartment','aquarium','bed_and_breakfast','caravan_site','chalet','gallery','guest_house','hostel','hotel','information','motel','museum','theme_park','zoo')) 
    AND ("recreation_ground" IS NULL OR "recreation_ground" NOT IN ('aged_care','animal_boarding','allotments','animal_boarding','bank','bar','biergarten','boatyard','carpark','childcare','casino','church','club','club_house','college','conference_centre','embassy','fast_food','garden_centre','grave_yard','hospital','gym','kindergarten','monastery','motel','nursing home','parking','parking_space','prison','retirement','retirement_home','retirement_village','school','scout_hut','university','golf_course','horse_riding', 'racetrack','summer_camp','sports_club','stadium','sports_centre','school','showground','school_playing_field','horse_racing','show_grounds','school_playing_fields','archery','badminton','bocce','boules','bowls','croquet','dog_racing','equestrian','futsal','gokarts','golf','greyhound_racing','horse_racing','karting','lacross','lacrosse','lawn_bowls','motocross','motor','motorcycle','polo','shooting','trugo','customers','alpine_hut','apartment','aquarium','bed_and_breakfast','caravan_site','chalet','gallery','guest_house','hostel','hotel','information','motel','museum','theme_park','zoo')) 
    AND ("sport" IS NULL OR "sport" NOT IN ('aged_care','animal_boarding','allotments','animal_boarding','bank','bar','biergarten','boatyard','carpark','childcare','casino','church','club','club_house','college','conference_centre','embassy','fast_food','garden_centre','grave_yard','hospital','gym','kindergarten','monastery','motel','nursing home','parking','parking_space','prison','retirement','retirement_home','retirement_village','school','scout_hut','university','golf_course','horse_riding', 'racetrack','summer_camp','sports_club','stadium','sports_centre','school','showground','school_playing_field','horse_racing','show_grounds','school_playing_fields','archery','badminton','bocce','boules','bowls','croquet','dog_racing','equestrian','futsal','gokarts','golf','greyhound_racing','horse_racing','karting','lacross','lacrosse','lawn_bowls','motocross','motor','motorcycle','polo','shooting','trugo','customers','alpine_hut','apartment','aquarium','bed_and_breakfast','caravan_site','chalet','gallery','guest_house','hostel','hotel','information','motel','museum','theme_park','zoo')) 
    AND ("access" IS NULL OR "access" NOT IN ('aged_care','animal_boarding','allotments','animal_boarding','bank','bar','biergarten','boatyard','carpark','childcare','casino','church','club','club_house','college','conference_centre','embassy','fast_food','garden_centre','grave_yard','hospital','gym','kindergarten','monastery','motel','nursing home','parking','parking_space','prison','retirement','retirement_home','retirement_village','school','scout_hut','university','golf_course','horse_riding', 'racetrack','summer_camp','sports_club','stadium','sports_centre','school','showground','school_playing_field','horse_racing','show_grounds','school_playing_fields','archery','badminton','bocce','boules','bowls','croquet','dog_racing','equestrian','futsal','gokarts','golf','greyhound_racing','horse_racing','karting','lacross','lacrosse','lawn_bowls','motocross','motor','motorcycle','polo','shooting','trugo','customers','alpine_hut','apartment','aquarium','bed_and_breakfast','caravan_site','chalet','gallery','guest_house','hostel','hotel','information','motel','museum','theme_park','zoo')) 
    AND ("tourism" IS NULL OR "tourism" NOT IN ('aged_care','animal_boarding','allotments','animal_boarding','bank','bar','biergarten','boatyard','carpark','childcare','casino','church','club','club_house','college','conference_centre','embassy','fast_food','garden_centre','grave_yard','hospital','gym','kindergarten','monastery','motel','nursing home','parking','parking_space','prison','retirement','retirement_home','retirement_village','school','scout_hut','university','golf_course','horse_riding', 'racetrack','summer_camp','sports_club','stadium','sports_centre','school','showground','school_playing_field','horse_racing','show_grounds','school_playing_fields','archery','badminton','bocce','boules','bowls','croquet','dog_racing','equestrian','futsal','gokarts','golf','greyhound_racing','horse_racing','karting','lacross','lacrosse','lawn_bowls','motocross','motor','motorcycle','polo','shooting','trugo','customers','alpine_hut','apartment','aquarium','bed_and_breakfast','caravan_site','chalet','gallery','guest_house','hostel','hotel','information','motel','museum','theme_park','zoo')) AND (golf IS NULL) 
---- NOTE: the following criteria are for Melbourne test purposes but may not be appropriate nationally 
-- hence, commented out 
--AND (amenity IS NULL OR amenity NOT IN ('swimming_pool','swimming')) 
--AND (leisure IS NULL OR leisure NOT IN ('swimming_pool','swimming')) 
--AND (sport IS NULL OR sport NOT IN ('swimming_pool','swimming')) 
  ; 
```

 16. We record if any particular OS feature which is considered 'public' is nested within another, larger publicly accessible OS feature 
```sql
  -- Check if area is within an indicated public access area 
  ALTER TABLE open_space ADD COLUMN within_public boolean; 
  UPDATE open_space SET within_public = FALSE; 
  UPDATE open_space o 
     SET within_public = TRUE 
    FROM open_space x 
   WHERE x.public_access = TRUE 
     AND ST_CoveredBy(o.geom,x.geom) 
     AND o.os_id!=x.os_id; 
```
 17.  We ensure that any feature located within a non-public OS feature is also recorded as being not publicly accessible (e.g. a park within a zoo) . 
```sql
  -- Check if area is within an indicated not public access area 
  -- for example, an OS may be within a non-public area nested within a public area 
  -- this additional check is required to ensure within_public is set to false 
  UPDATE open_space o 
     SET public_access = FALSE 
    FROM open_space x 
   WHERE o.public_access = TRUE 
     AND x.public_access = FALSE 
     AND ST_CoveredBy(o.geom,x.geom) 
     AND o.os_id!=x.os_id; 
  
  -- If an open space is within or co-extant with a space flagged as not having public access 
  -- which is not itself covered by a public access area 
  -- then it too should be flagged as not public (ie. public_access = FALSE) 
  UPDATE open_space o 
     SET public_access = FALSE 
    FROM open_space x 
   WHERE o.public_access = TRUE 
     AND x.public_access = FALSE 
     AND x.within_public = FALSE 
     AND ST_CoveredBy(o.geom,x.geom); 
```

 18. We create additional geometry columns for 'public' and 'not public' OS features 
```sql
ALTER TABLE open_space ADD COLUMN IF NOT EXISTS geom_public geometry; 
ALTER TABLE open_space ADD COLUMN IF NOT EXISTS geom_not_public geometry; 
UPDATE open_space SET geom_public = geom WHERE public_access = TRUE; 
UPDATE open_space SET geom_not_public = geom WHERE public_access = FALSE; 
```

 19.  We collate our OS features into Areas of Open Space.  We do this because many OS features in fact overlap (e.g. a cricket pitch within a football oval, within a fenced area, within a stadium, within a public park). 
By creating richly attributed AOS features, we allow future researchers to use this data to use various techniques to consider OS quality and value for particular purposes based on co-locations of other OS features and associated amenities. 
 
The operation to create these feature is complicated in the details, but conceptually simple: we group our AOS into those which are clearly 'public (not linear)', 'not public', 'linear but public' or 'waterways'.  Linear features (which might include street verges or long tracks) and waterways could link otherwise quite distance open space features into a much larger AOS expanse if we didn't keep them seperate, so we do. 
 
Examples are Royal Park in Melbourne, which contains a number of OS features, not all of which are public (e.g. grasslands, a zoo, a golf course).  All of these features are accessed from the boundary of Royal Park itself. 
```sql
-- Create Areas of Open Space (AOS) table 
-- this includes schools and contains indicators to differentiate schools, and parks within schools 
-- the 'geom' attributes is the area within an AOS not including a school 
--    -- this is what we want to use to evaluate collective OS area within the AOS (aos_ha) 
-- the 'geom' attribute is the area including the school (so if there is no school, this is equal to geom) 
--    -- this is what we will use to create entry nodes for the parks (as otherwise school ovals would be inaccessible) 
-- School AOS features 
--    -- can always be excluded from analysis, or an analysis can be restricted to focus on these. 
--    -- contains a subset of anonymised tags present for the school itself 
--    -- specifically, 'designation', 'fee', 'grades', 'isced', 'school:gender', 'school:enrolment', 'school:selective', 'school:specialty' 
  
DROP TABLE IF EXISTS open_space_areas; 
CREATE TABLE open_space_areas AS 
WITH clusters AS( 
    SELECT unnest(ST_ClusterWithin(open_space.geom, .001)) AS gc 
      FROM open_space 
     WHERE (public_access IS TRUE 
            OR (public_access IS FALSE 
                AND 
                within_public IS TRUE 
                AND (acceptable_linear_feature IS TRUE 
                     OR 
                     linear_feature IS FALSE))) 
       AND in_school IS FALSE 
       AND is_school IS FALSE 
       AND (linear_feature IS FALSE 
            OR 
            (acceptable_linear_feature IS TRUE 
            AND within_public IS TRUE)) 
       AND linear_waterway IS NULL 
    UNION 
        SELECT unnest(ST_ClusterWithin(not_public_os.geom, .001)) AS gc 
          FROM open_space AS not_public_os 
         WHERE public_access IS FALSE 
           AND within_public IS FALSE 
           AND linear_waterway IS NULL 
    ----  This implicitly includes schools unless the following code is uncommented 
    --     AND in_school IS FALSE 
    --     AND is_school IS FALSE 
    -- UNION 
    --   SELECT  unnest(ST_ClusterWithin(school_os.geom, .001)) AS gc 
    --     FROM open_space AS school_os 
    --    WHERE (in_school IS TRUE 
    --       OR is_school IS TRUE) 
    --      AND linear_waterway IS NULL 
    UNION 
        SELECT  linear_os.geom AS gc 
          FROM open_space AS linear_os 
         WHERE (linear_feature IS TRUE 
                AND acceptable_linear_feature IS FALSE 
                AND in_school IS FALSE 
                AND is_school IS FALSE) 
           AND public_access IS TRUE 
           AND linear_waterway IS NULL 
    UNION 
        SELECT  waterway_os.geom AS gc 
          FROM open_space AS waterway_os 
         WHERE linear_waterway IS TRUE 
) 
, unclustered AS( --unpacking GeomCollections 
                SELECT row_number() OVER () AS cluster_id, 
                       (ST_DUMP(gc)).geom AS geom 
                FROM clusters) 
SELECT cluster_id as aos_id, 
       jsonb_agg(
            jsonb_strip_nulls(
                to_jsonb(
                    (SELECT d FROM (
                        SELECT "os_id", 
                               "area_ha", 
                               "beach", 
                               "river", 
                               "public_access", 
                               "within_public", 
                               "amenity", 
                               "access", 
                               "boundary", 
                               "golf", 
                               "landuse", 
                               "leisure", 
                               "natural", 
                               "playground", 
                               "recreation_ground", 
                               "sport", 
                               "tourism", 
                               "water", 
                               "wetland", 
                               "waterway", 
                               "wood", 
                               "in_school", 
                               "is_school", 
                               "school_tags", 
                               "water_feature", 
                               "min_bounding_circle_area", 
                               "min_bounding_circle_diameter", 
                               "roundness", 
                               "linear_feature", 
                               "acceptable_linear_feature"
                           ) d
                       )
                   ) 
            || hstore_to_jsonb(tags) 
            || jsonb_build_object('school_tags',school_tags) 
            || jsonb_build_object('tags_line',tags_line) 
            || jsonb_build_object('tags_point',tags_point))
       ) AS attributes, 
       COUNT(1) AS numgeom, 
       ST_Union(geom_public) AS geom_public, 
       ST_Union(geom_not_public) AS geom_not_public, 
       ST_Union(water_geom) AS geom_water, 
       ST_Union(geom) AS geom 
       FROM open_space 
       INNER JOIN unclustered USING(geom) 
       GROUP BY cluster_id; 
          
CREATE UNIQUE INDEX aos_idx ON open_space_areas (aos_id); 
CREATE INDEX idx_aos_jsb ON open_space_areas USING GIN (attributes); 
```

20. We record size of AOS 
```sql
-- Create variable for AOS size 
ALTER TABLE open_space_areas ADD COLUMN aos_ha_public double precision; 
ALTER TABLE open_space_areas ADD COLUMN aos_ha_not_public double precision; 
-- note aos_ha_total includes school area 
ALTER TABLE open_space_areas ADD COLUMN aos_ha double precision; 
ALTER TABLE open_space_areas ADD COLUMN aos_ha_water double precision; 
  
-- Calculate total area of AOS in Ha for various kinds of AOS (if no extent for that category, record as zero) 
UPDATE open_space_areas SET aos_ha_public = COALESCE(ST_Area(geom_public)/10000.0,0); 
UPDATE open_space_areas SET aos_ha_not_public = COALESCE(ST_Area(geom_not_public)/10000.0,0); 
UPDATE open_space_areas SET aos_ha = ST_Area(geom)/10000.0; 
UPDATE open_space_areas SET aos_ha_water = COALESCE(ST_Area(geom_water)/10000.0,0); 
```

 21. We record if an AOS contains a water feature and the estimated percent of water within the AOS 
Note that this cannot be taken too literally; water features may not be truly all water.  It is more indicative than true. 
```sql
  -- Set water_feature as true where OS feature intersects a noted water feature 
  -- wet by association 
ALTER TABLE open_space_areas ADD COLUMN has_water_feature boolean; 
UPDATE open_space_areas SET has_water_feature = FALSE; 
UPDATE open_space_areas o SET has_water_feature = TRUE 
  FROM (SELECT * from open_space WHERE water_feature = TRUE) w 
 WHERE ST_Intersects (o.geom,w.geom); 
  
-- Create variable for Water percent 
ALTER TABLE open_space_areas ADD COLUMN water_percent numeric; 
UPDATE open_space_areas SET water_percent = 0; 
UPDATE open_space_areas SET water_percent = 100 * aos_ha_water/aos_ha::numeric WHERE aos_ha > 0; 
```

### 22. We create outlines around the AOS to mark the edges by which they are entered 
```sql
-- Create a linestring aos table 
-- the 'school_bounds' prereq feature un-nests the multipolygons to straight polygons, so we can take their exterior rings 
DROP TABLE IF EXISTS aos_line; 
CREATE TABLE aos_line AS 
WITH school_bounds AS 
    (SELECT aos_id, ST_SetSRID(st_astext((ST_Dump(geom)).geom),7845) AS geom  FROM open_space_areas) 
SELECT aos_id, 
       ST_Length(geom)::numeric AS length, 
       geom 
FROM (SELECT aos_id, ST_ExteriorRing(geom) AS geom FROM school_bounds) t; 
```

### 23. Pseudo-entry points are generated every 20m around AOS boundaries. 
```sql
-- Generate a point every 20m along a park outlines: 
DROP TABLE IF EXISTS aos_nodes; 
CREATE TABLE aos_nodes AS 
  WITH aos AS 
  (SELECT aos_id, 
          length, 
          generate_series(0,1,20/length) AS fraction, 
          geom FROM aos_line) 
SELECT aos_id, 
       row_number() over(PARTITION BY aos_id) AS node, 
       ST_LineInterpolatePoint(geom, fraction)  AS geom 
FROM aos; 
  
CREATE INDEX aos_nodes_idx ON aos_nodes USING GIST (geom); 
ALTER TABLE aos_nodes ADD COLUMN aos_entryid varchar; 
UPDATE aos_nodes SET aos_entryid = aos_id::text || ',' || node::text; 
```

### 24. The subset of pseudo-entry points within 30m of a road are recorded in a seperate table to be used for network analyses.  
```sql
-- Create table of points within 30m of lines (should be your road network) 
-- Distinct is used to avoid redundant duplication of points where they are within 20m of multiple roads 
DROP TABLE IF EXISTS aos_nodes_30m_line; 
CREATE TABLE aos_nodes_30m_line AS 
SELECT DISTINCT n.* 
FROM aos_nodes n, 
     edges l 
WHERE ST_DWithin(n.geom ,l.geom,30); 
```  
### 25. A table of public open space areas is created  
```sql
-- Create subset data for public_open_space_areas 
DROP TABLE IF EXISTS aos_public_osm; 
CREATE TABLE aos_public_osm AS 
SELECT DISTINCT ON (pos.aos_id) pos.* 
  FROM  open_space_areas pos 
 WHERE EXISTS (SELECT 1 FROM open_space_areas o, 
                      jsonb_array_elements(attributes) obj 
                WHERE obj->'public_access' = 'true' 
                  AND  pos.aos_id = o.aos_id); 
```
 
 
[^1]: Victorian Planning Authority. Metropolitan Open Space Network: Provision and Distribution.  (2017). <https://vpa.vic.gov.au/wp-content/uploads/2018/02/Open-Space-Network-Provision-and-Distribution-Reduced-Size.pdf>.