

datasets = [
    "hlc_ntnl_liveability_2018_address_points_indicators_epsg7845.csv",
    "hlc_ntnl_liveability_2018_address_points_distance_closest_epsg7845.csv",
    "hlc_ntnl_liveability_2018_address_points_distance_arrays.csv",
    "hlc_ntnl_liveability_2018_Mesh_Block_2016.csv",
    "hlc_ntnl_liveability_2018_sa1_2016.csv",
    "hlc_ntnl_liveability_2018_sa2_2016.csv",
    "hlc_ntnl_liveability_2018_sa3_2016.csv",
    "hlc_ntnl_liveability_2018_sa4_2016.csv",
    "hlc_ntnl_liveability_2018_ssc_2016.csv",
    "hlc_ntnl_liveability_2018_lga_2016.csv",
    "hlc_ntnl_liveability_2018_region.csv",
    "hlc_ntnl_liveability_2018_gtfs_20191008_20191205_daytime_tidy_transit_headway_analysis.csv",
    "hlc_ntnl_liveability_2018_aos_public_osm.csv",
    "hlc_ntnl_liveability_2018_od_aos_jsonb.csv"
]


roles = [
    "Liveability indicators for residential locations (address points in urban Mesh Blocks with dwellings at 2016 census)",
    "Estimates for distance in metres along pedestrian network to the closest of a range of destination types for residential locations (address points in urban Mesh Blocks with dwellings at 2016 census)",
    "Arrays of estimates for distance in metres along pedestrian network to all destinations (within 3200m and the closest) across a range of destination types , for residential locations (address points in urban Mesh Blocks with dwellings at 2016 census)",
    "Mesh Block averages of residential liveability indicators and distance to closest estimates, with dwelling and person counts as well as area linkage codes to support aggregation to larger area scales (optionally with weighting; recommended)",
    "Liveability indicators for dwellings, aggregated for Statistical Areas Level 1 (SA1)",
    "Liveability indicators for dwellings, aggregated for Statistical Areas Level 2 (SA2)",
    "Liveability indicators for dwellings, aggregated for Statistical Areas Level 3 (SA3)",
    "Liveability indicators for dwellings, aggregated for Statistical Areas Level 4 (SA4)",
    "Liveability indicators for dwellings, aggregated for Suburbs",
    "Liveability indicators for dwellings, aggregated for Local Government Areas",
    "Liveability indicators for dwellings, aggregated for cities",
    "GTFS transport stops headway analysis of day time weekday public transport service frequency between 8 October 2019 to 5 December 2019, with WKT geometry",
    "Areas of open space with at least partial public access, as identified using open street map, with WKT geometry for public geometry, water geometry and overall geometry as well as JSON attributes (including public area) and list of co-located amenities within 100m (including public toilets)",
    "JSON list of identifiers and distances of areas of open space for residential address points identified as having areas of open space accessible within 3200m.  This dataset is indexed by the residential address point identifier, supporting linkage with attributes from the main address indicator dataset."
]


metadata = """
  - dataset: {}
    doi: https://doi.org/10.25439/rmt.15001230
    licence: ODbL
    role: {}"""
  
for d in zip(datasets,roles):
  print(metadata.format(d[0],d[1]))
  

study_regions = {
"type": "FeatureCollection",
"name": "Study region bboxes",
"crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },
"features": [
{ "type": "Feature", "properties": { "study_region": "Adelaide" }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 138.445982137160826, -35.349215154596855 ], [ 138.946370923695241, -35.333886562737739 ], [ 138.909026663325534, -34.550054816769752 ], [ 138.412409140013978, -34.565299283164983 ], [ 138.445982137160826, -35.349215154596855 ] ] ] } },
{ "type": "Feature", "properties": { "study_region": "Albury - Wodonga" }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 146.829935537586181, -36.219431684578772 ], [ 147.042590868734862, -36.201629140795767 ], [ 147.017869732707425, -36.008843305099646 ], [ 146.805611823432827, -36.026622632755654 ], [ 146.829935537586181, -36.219431684578772 ] ] ] } },
{ "type": "Feature", "properties": { "study_region": "Ballarat" }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 143.69663589135223, -37.671893407012938 ], [ 143.936124275918388, -37.656992175380502 ], [ 143.917272308242701, -37.467398986866073 ], [ 143.678234661458248, -37.482281993437724 ], [ 143.69663589135223, -37.671893407012938 ] ] ] } },
{ "type": "Feature", "properties": { "study_region": "Bendigo" }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 144.195265649121723, -36.84765762258256 ], [ 144.406062100601616, -36.833739094903066 ], [ 144.386044455283013, -36.639422619473137 ], [ 144.175649911284751, -36.653323219403916 ], [ 144.195265649121723, -36.84765762258256 ] ] ] } },
{ "type": "Feature", "properties": { "study_region": "Hobart" }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 147.073095913757214, -43.096993916228932 ], [ 147.711835743301975, -43.04690111954347 ], [ 147.651701025196274, -42.642054039723853 ], [ 147.015721182884505, -42.692039093053403 ], [ 147.073095913757214, -43.096993916228932 ] ] ] } },
{ "type": "Feature", "properties": { "study_region": "Brisbane" }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 152.465487375235426, -28.156526487681479 ], [ 153.481138271143891, -28.019494163101793 ], [ 153.274273035805408, -26.831884739774811 ], [ 152.26909093488365, -26.967512973723721 ], [ 152.465487375235426, -28.156526487681479 ] ] ] } },
{ "type": "Feature", "properties": { "study_region": "Cairns" }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 145.681357508072125, -17.043954655944475 ], [ 145.794842863431711, -17.03372783009555 ], [ 145.764758265109549, -16.725612496181014 ], [ 145.651559025954214, -16.735804193173408 ], [ 145.681357508072125, -17.043954655944475 ] ] ] } },
{ "type": "Feature", "properties": { "study_region": "Canberra" }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 149.038796987397802, -35.486460240578893 ], [ 149.250598937472262, -35.465479687841764 ], [ 149.202717506173826, -35.143112763402989 ], [ 148.991567760706999, -35.164046417442378 ], [ 149.038796987397802, -35.486460240578893 ] ] ] } },
{ "type": "Feature", "properties": { "study_region": "Darwin" }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 130.813382783189184, -12.521339321266391 ], [ 131.047864587103675, -12.526967023308314 ], [ 131.052269052550287, -12.342588570786084 ], [ 130.818136797640904, -12.336973612392775 ], [ 130.813382783189184, -12.521339321266391 ] ] ] } },
{ "type": "Feature", "properties": { "study_region": "Launceston" }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 147.053985747613353, -41.517769192860612 ], [ 147.216776754006588, -41.504932861061363 ], [ 147.191549515013861, -41.324854625919833 ], [ 147.029064733685686, -41.337677954186248 ], [ 147.053985747613353, -41.517769192860612 ] ] ] } },
{ "type": "Feature", "properties": { "study_region": "Geelong" }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 144.268447438857095, -38.360075836023448 ], [ 144.674703623605438, -38.33335526076835 ], [ 144.637695836918425, -37.989590064622035 ], [ 144.232835343475955, -38.016252604408251 ], [ 144.268447438857095, -38.360075836023448 ] ] ] } },
{ "type": "Feature", "properties": { "study_region": "Gold Coast - Tweed Heads" }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 153.304290683906686, -28.451569690298943 ], [ 153.611628103591215, -28.409165450120337 ], [ 153.481658824884676, -27.673769813957964 ], [ 153.176293796224513, -27.715908561624289 ], [ 153.304290683906686, -28.451569690298943 ] ] ] } },
{ "type": "Feature", "properties": { "study_region": "Mackay" }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 149.139181264131821, -21.198422491101343 ], [ 149.242638864067089, -21.186636706933758 ], [ 149.2175899592728, -20.993610067279079 ], [ 149.114299069792878, -21.005372789705532 ], [ 149.139181264131821, -21.198422491101343 ] ] ] } },
{ "type": "Feature", "properties": { "study_region": "Melbourne" }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 144.489694060501847, -38.45799994064167 ], [ 145.795134232575037, -38.366691771623223 ], [ 145.657755578636824, -37.201643453543014 ], [ 144.367372123827636, -37.292273275965485 ], [ 144.489694060501847, -38.45799994064167 ] ] ] } },
{ "type": "Feature", "properties": { "study_region": "Newcastle - Maitland" }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 151.345715900947596, -33.155837639423417 ], [ 151.866018576388313, -33.094099254175354 ], [ 151.790515017544408, -32.64798088993183 ], [ 151.272354539970109, -32.709513920149845 ], [ 151.345715900947596, -33.155837639423417 ] ] ] } },
{ "type": "Feature", "properties": { "study_region": "Perth" }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 115.380755714090668, -32.641423466967318 ], [ 116.086005828717703, -32.728728819906138 ], [ 116.280119948475459, -31.571744660552248 ], [ 115.582294841163886, -31.485207469120727 ], [ 115.380755714090668, -32.641423466967318 ] ] ] } },
{ "type": "Feature", "properties": { "study_region": "Sunshine Coast" }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 152.929500450082656, -26.871824016836527 ], [ 153.189707017293529, -26.836153400691 ], [ 153.101732618599755, -26.320961159120326 ], [ 152.842682639390716, -26.356469111090615 ], [ 152.929500450082656, -26.871824016836527 ] ] ] } },
{ "type": "Feature", "properties": { "study_region": "Sydney" }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 150.375114632266417, -34.330026489146157 ], [ 151.76712511517286, -34.172034330010959 ], [ 151.590263499197363, -33.127530630083562 ], [ 150.211785596734728, -33.284324285831758 ], [ 150.375114632266417, -34.330026489146157 ] ] ] } },
{ "type": "Feature", "properties": { "study_region": "Toowoomba" }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 151.850618947448879, -27.722552300518469 ], [ 152.010747001018217, -27.702080088118755 ], [ 151.958561683775656, -27.379255993500433 ], [ 151.798885041046674, -27.399671085738031 ], [ 151.850618947448879, -27.722552300518469 ] ] ] } },
{ "type": "Feature", "properties": { "study_region": "Townsville" }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 146.597728947457995, -19.425465195683302 ], [ 146.868828800100715, -19.399313462320524 ], [ 146.843790535520412, -19.167718602324921 ], [ 146.573211005836754, -19.193806342213971 ], [ 146.597728947457995, -19.425465195683302 ] ] ] } },
{ "type": "Feature", "properties": { "study_region": "Wollongong" }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 150.738639976065713, -34.709501968169128 ], [ 151.080679334415862, -34.671256489877493 ], [ 150.998475248595071, -34.171930118879168 ], [ 150.658042768206514, -34.210039638712409 ], [ 150.738639976065713, -34.709501968169128 ] ] ] } }
]
}

bboxes = dict()

for f in study_regions['features']:
  bboxes[f['properties']['study_region']] = f['geometry']['coordinates']

locations = """   - region:    {}, Australia
     bbox:      {}
     timepoint: [2018:2019]"""
  
for city in sorted(bboxes.keys()):
    print(locations.format(city,bboxes[city])

# test metadata yml file
import yaml

with open(r"C:\Users\carlh\OneDrive\Research\Publications\Australian National Liveability Dataset 2018\metadata.yml", "r") as stream:
    metadata = yaml.safe_load(stream)