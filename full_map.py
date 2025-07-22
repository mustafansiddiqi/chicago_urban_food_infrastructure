import geopandas as gpd
import pandas as pd
import folium
from shapely.geometry import Point
import numpy as np
import streamlit as st
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

# PAGE CONFIG
st.set_page_config(layout="wide")

# CUSTOM CSS
st.markdown("""
    <style>
        .block-container {
            padding: 2rem 2rem;
            max-width: 100%;
        }
        .main-title {
            text-align: center;
            font-size: 2.5em;
            margin-bottom: 0.2em;
        }
        .sub-title {
            text-align: center;
            color: gray;
            font-size: 1.2em;
            margin-bottom: 1em;
        }
    </style>
""", unsafe_allow_html=True)

# TITLE
st.markdown('<h1 class="main-title">Chicago Urban Agriculture & Food Ecosystem Map</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">An initiative from the Office of Mayor Brandon Johnson</p>', unsafe_allow_html=True)

# FILE PATHS
SHAPEFILE_PATH = "neighborhoods_shapefile.shp"
CUAMPS_CSV_PATH = "cuamp_gardens geocoded.csv"
FOOD_TAVERNS_CSV_PATH = "Food_Tavern_PackGoods_Current.csv"
FOOD_ECOSYSTEM_CSV_PATH = "Food_Ecosystem_Data_2025.csv"
FARMERS_MARKETS_CSV_PATH = "Farmers_Markets.csv"

# LOAD DATA
file = gpd.read_file(SHAPEFILE_PATH)
file = file.rename(columns={'neighborho': 'neighborhood'})

cuamps = pd.read_csv(CUAMPS_CSV_PATH)
taverns = pd.read_csv(FOOD_TAVERNS_CSV_PATH)
ecosystem = pd.read_csv(FOOD_ECOSYSTEM_CSV_PATH)
farmers = pd.read_csv(FARMERS_MARKETS_CSV_PATH)

# CLEAN COORDINATES
for df in [cuamps, taverns, ecosystem]:
    df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
    df.dropna(subset=['Latitude', 'Longitude'], inplace=True)

farmers['Latitude'] = pd.to_numeric(farmers['Latitude'], errors='coerce')
farmers['Longitude'] = pd.to_numeric(farmers['Longitude'], errors='coerce')
farmers.dropna(subset=['Latitude', 'Longitude'], inplace=True)

farmers['DCASE'] = farmers['DCASE'].astype(bool)
cuamps['Food Producing'] = np.where(cuamps["food_producing"] == True, 'Yes', 'N/A')
farmers['Support'] = np.where(farmers['DCASE'], "Supported by DCASE", "Not Supported")

# LAYOUT COLUMNS
col1, col2 = st.columns([1, 3])

with col1:
    with st.expander("🔍 Filters"):
        all_neighborhoods = sorted(file["neighborhood"].dropna().unique())
        selected_neighborhoods = st.multiselect("Neighborhood", all_neighborhoods, default=all_neighborhoods)

        show_gardens = st.checkbox("Community Gardens", value=True)
        show_ecosystem = st.checkbox("Ecosystem Sites", value=True)
        show_taverns = st.checkbox("Taverns", value=True)
        show_farmers = st.checkbox("Farmers Markets", value=True)

        if show_gardens:
            selected_food = st.multiselect("Food Producing Gardens", ["Yes", "N/A"], default=["Yes", "N/A"])
            filtered_cuamps = cuamps[cuamps["Food Producing"].isin(selected_food) & cuamps["neighborhood"].isin(selected_neighborhoods)]
        else:
            filtered_cuamps = pd.DataFrame(columns=cuamps.columns)

        if show_ecosystem:
            all_tifs = sorted(ecosystem["TIF District"].dropna().unique())
            selected_tifs = st.multiselect("TIF District", all_tifs, default=all_tifs)
            filtered_ecosystem = ecosystem[ecosystem["TIF District"].isin(selected_tifs)]
        else:
            filtered_ecosystem = pd.DataFrame(columns=ecosystem.columns)

        if show_taverns:
            all_names = sorted(taverns["DBA Name"].dropna().unique())
            search_name = st.text_input("Search Tavern Name")
            filtered_taverns = taverns[taverns["DBA Name"].isin(all_names)]
            if search_name:
                filtered_taverns = filtered_taverns[filtered_taverns["DBA Name"].str.contains(search_name, case=False)]
        else:
            filtered_taverns = pd.DataFrame(columns=taverns.columns)

        if show_farmers:
            selected_support = st.multiselect("Farmers Markets Supported by DCASE", ["Supported by DCASE", "Not Supported"], default=["Supported by DCASE", "Not Supported"])
            filtered_farmers = farmers[farmers['Support'].isin(selected_support)]
        else:
            filtered_farmers = pd.DataFrame(columns=farmers.columns)

    with st.expander("📈 Summary Stats"):
        st.metric("Total Gardens", len(filtered_cuamps))
        st.metric("Ecosystem Sites", len(filtered_ecosystem))
        st.metric("Taverns", len(filtered_taverns))
        st.metric("Farmers Markets", len(filtered_farmers))

with col2:
    # BASE MAP
    map_center = [41.8781, -87.6298]
    base_map = folium.Map(location=map_center, zoom_start=11, tiles="CartoDB positron")

    # NEIGHBORHOODS
    folium.GeoJson(
        file,
        name="Neighborhoods",
        tooltip=folium.GeoJsonTooltip(fields=["neighborhood"]),
    ).add_to(base_map)

    for _, row in file.iterrows():
        centroid = row["geometry"].centroid
        folium.map.Marker(
            [centroid.y, centroid.x],
            icon=folium.DivIcon(html=f"<div style='font-size:8pt; color:black'>{row['neighborhood']}</div>")
        ).add_to(base_map)

    # GARDENS
    if show_gardens and not filtered_cuamps.empty:
        cluster = MarkerCluster(name="Community Gardens").add_to(base_map)
        for _, row in filtered_cuamps.iterrows():
            folium.CircleMarker(
                location=(row["Latitude"], row["Longitude"]),
                radius=5,
                color="green",
                fill=True,
                fill_opacity=0.6,
                popup=folium.Popup(f"<b>{row['growing_site_name']}</b><br>Food Producing: {row['Food Producing']}", max_width=300)
            ).add_to(cluster)

    # ECOSYSTEM
    if show_ecosystem and not filtered_ecosystem.empty:
        cluster = MarkerCluster(name="Ecosystem Sites").add_to(base_map)
        for _, row in filtered_ecosystem.iterrows():
            folium.CircleMarker(
                location=(row["Latitude"], row["Longitude"]),
                radius=5,
                color="orange",
                fill=True,
                fill_opacity=0.6,
                popup=folium.Popup(f"<b>{row['Primary']}</b><br>TIF: {row['TIF District']}", max_width=300)
            ).add_to(cluster)

    # TAVERNS
    if show_taverns and not filtered_taverns.empty:
        cluster = MarkerCluster(name="Taverns").add_to(base_map)
        for _, row in filtered_taverns.iterrows():
            folium.CircleMarker(
                location=(row["Latitude"], row["Longitude"]),
                radius=5,
                color="purple",
                fill=True,
                fill_opacity=0.6,
                popup=folium.Popup(f"<b>{row['DBA Name']}</b>", max_width=300)
            ).add_to(cluster)

    # FARMERS MARKETS
    if show_farmers and not filtered_farmers.empty:
        cluster = MarkerCluster(name="Farmers Markets").add_to(base_map)
        for _, row in filtered_farmers.iterrows():
            color = "yellow" if row["DCASE"] else "orange"
            popup_text = f"<b>{row['Market Name']}</b><br>{row['Address']}"
            if row["DCASE"]:
                popup_text += "<br><b>Supported by DCASE</b>"
            folium.CircleMarker(
                location=(row["Latitude"], row["Longitude"]),
                radius=5,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.6,
                popup=folium.Popup(popup_text, max_width=300)
            ).add_to(cluster)

    folium.LayerControl(collapsed=False).add_to(base_map)
    st_folium(base_map, width=1000, height=700)
