import geopandas as gpd
import pandas as pd
import folium
from shapely.geometry import Point
import numpy as np
import streamlit as st
from streamlit_folium import st_folium

# FILE PATHS
SHAPEFILE_PATH = r"C:\Users\488325\Python\neighborhoods_shapefile.shp"
CUAMPS_CSV_PATH = r"C:\Users\488325\Python\cuamp_gardens geocoded.csv"
FOOD_TAVERNS_CSV_PATH = r"C:\Users\488325\Python\Food_Tavern_PackGoods_Current.csv"
FOOD_ECOSYSTEM_CSV_PATH = r"C:\Users\488325\Python\Food_Ecosystem_Data_2025.csv"

# LOAD DATA
file = gpd.read_file(SHAPEFILE_PATH)
file = file.rename(columns={'neighborho': 'neighborhood'})

cuamps = pd.read_csv(CUAMPS_CSV_PATH)
taverns = pd.read_csv(FOOD_TAVERNS_CSV_PATH)
ecosystem = pd.read_csv(FOOD_ECOSYSTEM_CSV_PATH)

# CLEAN COORDINATES
for df in [cuamps, taverns, ecosystem]:
    df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
    df.dropna(subset=['Latitude', 'Longitude'], inplace=True)

# EXTRA COLUMNS
cuamps['Food Producing'] = np.where(cuamps["food_producing"] == True, 'Yes', 'N/A')

# STREAMLIT INTERFACE
st.title("Chicago Urban Agriculture & Food Ecosystem Map")
st.subheader("An initiative from the office of Mayor Brandon Johnson")

# LAYER CHECKBOXES
show_gardens = st.checkbox("Show Community Gardens", value=True)
show_ecosystem = st.checkbox("Show Ecosystem Sites", value=True)
show_taverns = st.checkbox("Show Taverns", value=True)

# FILTERS - Neighborhood (shared)
all_neighborhoods = sorted(file["neighborhood"].dropna().unique())
selected_neighborhoods = st.multiselect("Filter by Neighborhood", all_neighborhoods, default=all_neighborhoods)

# FILTERS - Gardens
if show_gardens:
    garden_options = ["Yes", "N/A"]
    selected_food = st.multiselect("Filter Gardens by Food Production", garden_options, default=garden_options)
    filtered_cuamps = cuamps[cuamps["Food Producing"].isin(selected_food) & cuamps["neighborhood"].isin(selected_neighborhoods)]
else:
    filtered_cuamps = pd.DataFrame(columns=cuamps.columns)

# FILTERS - Ecosystem
if show_ecosystem:
    all_tifs = sorted(ecosystem["TIF District"].dropna().unique())
    selected_tifs = st.multiselect("Filter Ecosystem Sites by TIF District", all_tifs, default=all_tifs)
    filtered_ecosystem = ecosystem[ecosystem["TIF District"].isin(selected_tifs)]
else:
    filtered_ecosystem = pd.DataFrame(columns=ecosystem.columns)

# FILTERS - Taverns
if show_taverns:
    all_names = sorted(taverns["DBA Name"].dropna().unique())
    selected_names = st.multiselect("Filter Taverns by Name", all_names, default=all_names[:50])  # Limit initial load
    filtered_taverns = taverns[taverns["DBA Name"].isin(selected_names)]
else:
    filtered_taverns = pd.DataFrame(columns=taverns.columns)

map_center = [41.8781, -87.6298]
base_map = folium.Map(location=map_center, zoom_start=11)

# Add neighborhoods as GeoJSON
folium.GeoJson(
    file,
    name="Neighborhoods",
    tooltip=folium.GeoJsonTooltip(fields=["neighborhood"]),
).add_to(base_map)

# Add neighborhood labels
for _, row in file.iterrows():
    centroid = row["geometry"].centroid
    folium.map.Marker(
        [centroid.y, centroid.x],
        icon=folium.DivIcon(html=f"""<div style="font-size:8pt; color:black">{row['neighborhood']}</div>""")
    ).add_to(base_map)

# Gardens Layer
if show_gardens and not filtered_cuamps.empty:
    garden_layer = folium.FeatureGroup(name="Community Gardens", show=True)
    for _, row in filtered_cuamps.iterrows():
        folium.CircleMarker(
            location=(row["Latitude"], row["Longitude"]),
            radius=5,
            color="green",
            fill=True,
            fill_opacity=0.6,
            tooltip=f"{row['growing_site_name']}<br>Food Producing: {row['Food Producing']}"
        ).add_to(garden_layer)
    garden_layer.add_to(base_map)

# Ecosystem Layer
if show_ecosystem and not filtered_ecosystem.empty:
    eco_layer = folium.FeatureGroup(name="Ecosystem Sites", show=True)
    for _, row in filtered_ecosystem.iterrows():
        folium.CircleMarker(
            location=(row["Latitude"], row["Longitude"]),
            radius=5,
            color="orange",
            fill=True,
            fill_opacity=0.6,
            tooltip=f"{row['Primary']}<br>TIF: {row['TIF District']}"
        ).add_to(eco_layer)
    eco_layer.add_to(base_map)

# Tavern Layer
if show_taverns and not filtered_taverns.empty:
    tavern_layer = folium.FeatureGroup(name="Taverns", show=True)
    for _, row in filtered_taverns.iterrows():
        folium.CircleMarker(
            location=(row["Latitude"], row["Longitude"]),
            radius=5,
            color="blue",
            fill=True,
            fill_opacity=0.6,
            tooltip=f"{row['DBA Name']}"
        ).add_to(tavern_layer)
    tavern_layer.add_to(base_map)

# Layer toggle
folium.LayerControl(collapsed=False).add_to(base_map)

# Render the map in Streamlit
st_data = st_folium(base_map, width=800, height=600)
