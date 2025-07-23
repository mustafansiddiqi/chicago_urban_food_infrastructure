from pickle import TRUE
import geopandas as gpd
import pandas as pd
import folium
from shapely.geometry import Point
import numpy as np
import streamlit as st
from streamlit_folium import st_folium
from PIL import Image
from folium.plugins import MarkerCluster


# PAGE CONFIG
st.set_page_config(layout="wide")

logo = Image.open(r"chicago_logo.png")

#IMAGE
st.markdown(
    """
    <style>
    .logo-container {
        position: absolute;
        top: 96px;
        right: 1.5rem;
        z-index: 100;
    }
    </style>
    <div class="logo-container">
    """, unsafe_allow_html=True
)

st.image(logo, width=110)
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
        .metrics-row {
            display: flex;
            justify-content: space-around;
            margin: 1em 0 2em 0;
        }
        .metric-container {
            text-align: center;
        }
        .metric-container h4 {
            font-size: 1.5em;
            margin-bottom: 0.2em;
        }
        .metric-container p {
            font-size: 1.5em;
            font-weight: bold;
            margin: 0;
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

# CACHED DATA LOADERS
@st.cache_resource
def load_shapefile():
    gdf = gpd.read_file(SHAPEFILE_PATH).rename(columns={'neighborho': 'neighborhood'})
    gdf["neighborhood"] = gdf["neighborhood"].str.strip().str.title()
    return gdf

@st.cache_data
def load_csv_data():
    cuamps = pd.read_csv(CUAMPS_CSV_PATH)
    taverns = pd.read_csv(FOOD_TAVERNS_CSV_PATH)
    ecosystem = pd.read_csv(FOOD_ECOSYSTEM_CSV_PATH)
    farmers = pd.read_csv(FARMERS_MARKETS_CSV_PATH)
    return cuamps, taverns, ecosystem, farmers

# LOAD DATA
file = load_shapefile()
cuamps, taverns, ecosystem, farmers = load_csv_data()

# CLEAN & STANDARDIZE DATA
cuamps["neighborhood"] = cuamps["neighborhood"].astype(str).str.strip().str.title()

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

# CONVERT POINT DATA TO GEODATAFRAMES FOR SPATIAL FILTERING
cuamps_gdf = gpd.GeoDataFrame(
    cuamps,
    geometry=gpd.points_from_xy(cuamps['Longitude'], cuamps['Latitude']),
    crs='EPSG:4326'
)
cuamps_joined = gpd.sjoin(cuamps_gdf, file, how='left', predicate='within')
cuamps_joined = cuamps_joined.rename(columns={"neighborhood_right": "neighborhood"})

ecosystem_gdf = gpd.GeoDataFrame(
    ecosystem,
    geometry=gpd.points_from_xy(ecosystem['Longitude'], ecosystem['Latitude']),
    crs='EPSG:4326'
)
ecosystem_joined = gpd.sjoin(ecosystem_gdf, file, how='left', predicate='within')
ecosystem_joined = ecosystem_joined.rename(columns={"neighborhood_right": "neighborhood"})

taverns_gdf = gpd.GeoDataFrame(
    taverns,
    geometry=gpd.points_from_xy(taverns['Longitude'], taverns['Latitude']),
    crs='EPSG:4326'
)
taverns_joined = gpd.sjoin(taverns_gdf, file, how='left', predicate='within')
taverns_joined = taverns_joined.rename(columns={"neighborhood_right": "neighborhood"})

farmers_gdf = gpd.GeoDataFrame(
    farmers,
    geometry=gpd.points_from_xy(farmers['Longitude'], farmers['Latitude']),
    crs='EPSG:4326'
)
farmers_joined = gpd.sjoin(farmers_gdf, file, how='left', predicate='within')
farmers_joined = farmers_joined.rename(columns={"neighborhood_right": "neighborhood"})

# FILTERS
with st.sidebar:
    st.markdown("### 🔍 Filters")
    all_neighborhoods = sorted(file["neighborhood"].dropna().unique())
    selected_neighborhoods = st.multiselect("Neighborhood", all_neighborhoods)
    show_wards = st.checkbox("Ward Labels", value=False)

    show_gardens = st.checkbox("Community Gardens", value=False)
    show_ecosystem = st.checkbox("Ecosystem Sites", value=False)
    show_taverns = st.checkbox("Taverns", value=False)
    show_farmers = st.checkbox("Farmers Markets", value=False)

    if show_gardens:
        selected_food = st.multiselect("Food Producing Gardens", ["Yes", "N/A"], default=["Yes", "N/A"])
        filtered_cuamps = cuamps_joined[
            (cuamps_joined["Food Producing"].isin(selected_food)) &
            (cuamps_joined["neighborhood"].isin(selected_neighborhoods))
        ]
    else:
        filtered_cuamps = pd.DataFrame(columns=cuamps.columns)

    if show_ecosystem:
        filtered_ecosystem = ecosystem_joined[ecosystem_joined["neighborhood"].isin(selected_neighborhoods)]
    else:
        filtered_ecosystem = pd.DataFrame(columns=ecosystem.columns)

    if show_taverns:
        filtered_taverns = taverns_joined[taverns_joined["neighborhood"].isin(selected_neighborhoods)]
    else:
        filtered_taverns = pd.DataFrame(columns=taverns.columns)

    if show_farmers:
        filtered_farmers = farmers_joined[farmers_joined["neighborhood"].isin(selected_neighborhoods)]
    else:
        filtered_farmers = pd.DataFrame(columns=farmers.columns)

# STATS CONTAINER
st.markdown("<div class='metrics-row'>" +
    f"<div class='metric-container'><h4>Total Gardens</h4><p>{len(filtered_cuamps)}</p></div>" +
    f"<div class='metric-container'><h4>Ecosystem Sites</h4><p>{len(filtered_ecosystem)}</p></div>" +
    f"<div class='metric-container'><h4>Taverns</h4><p>{len(filtered_taverns)}</p></div>" +
    f"<div class='metric-container'><h4>Farmers Markets</h4><p>{len(filtered_farmers)}</p></div>" +
    "</div>", unsafe_allow_html=True)

# LAYOUT COLUMNS
col1, col2 = st.columns([1, 3])

with col2:
    map_center = [41.8781, -87.6298]
    base_map = folium.Map(location=map_center, zoom_start=11, tiles="CartoDB positron")

    for _, row in file.iterrows():
        opacity = 0.6 if row['neighborhood'] in selected_neighborhoods else 0.2
        folium.GeoJson(
            row['geometry'],
            name=row['neighborhood'],
            style_function=lambda feature, o=opacity: {
                'fillColor': 'grey',
                'color': 'grey',
                'weight': 1.25,
                'fillOpacity': o
            },
            tooltip=folium.Tooltip(row['neighborhood']) if row['neighborhood'] in selected_neighborhoods else None
        ).add_to(base_map)

        if row['neighborhood'] in selected_neighborhoods:
            centroid = row["geometry"].centroid
            folium.map.Marker(
                [centroid.y, centroid.x],
                icon=folium.DivIcon(html=f"<div style='font-size:8pt; color:black'>{row['neighborhood']}</div>")
            ).add_to(base_map)

    if show_wards and 'ward' in cuamps_joined.columns:
        ward_centroids = (
            cuamps_joined
            .groupby('ward')[['Latitude', 'Longitude']]
            .mean()
            .dropna()
            .reset_index()
        )
        for _, row in ward_centroids.iterrows():
            folium.map.Marker(
                [row['Latitude'], row['Longitude']],
                icon=folium.DivIcon(
                    html=f"<div style='font-size:10pt; font-weight:bold; color:black'>Ward {int(row['ward'])}</div>"
                )
            ).add_to(base_map)

    if show_gardens and not filtered_cuamps.empty:
        cluster = MarkerCluster(name="Community Gardens").add_to(base_map)
        for _, row in filtered_cuamps.iterrows():
            tooltip = f"{row['growing_site_name']} </b><br> Address:  {row.get('address', 'Address N/A')}"
            folium.CircleMarker(
                location=(row["Latitude"], row["Longitude"]),
                radius=5,
                color="green",
                fill=True,
                fill_opacity=0.6,
                popup=folium.Popup(f"<b>{row['growing_site_name']}</b><br>Food Producing: {row['Food Producing']}", max_width=300),
                tooltip=tooltip
            ).add_to(cluster)

    if show_ecosystem and not filtered_ecosystem.empty:
        cluster = MarkerCluster(name="Ecosystem Sites").add_to(base_map)
        for _, row in filtered_ecosystem.iterrows():
            tooltip = f"{row['Primary']}</b><br><b>Address:</b> {row.get('Project Address', 'Address N/A')}"
            folium.CircleMarker(
                location=(row["Latitude"], row["Longitude"]),
                radius=5,
                color="orange",
                fill=True,
                fill_opacity=0.6,
                popup=folium.Popup(f"<b>{row['Primary']}</b><br>TIF: {row['TIF District']}", max_width=300),
                tooltip=tooltip
            ).add_to(cluster)

    if show_taverns and not filtered_taverns.empty:
        cluster = MarkerCluster(name="Taverns").add_to(base_map)
        for _, row in filtered_taverns.iterrows():
            tooltip = f"{row['DBA Name']} </b><br><b>Address:</b>  {row.get('Address', 'Address N/A')}"
            folium.CircleMarker(
                location=(row["Latitude"], row["Longitude"]),
                radius=5,
                color="purple",
                fill=True,
                fill_opacity=0.6,
                popup=folium.Popup(f"<b>{row['DBA Name']}</b>", max_width=300),
                tooltip=tooltip
            ).add_to(cluster)

    if show_farmers and not filtered_farmers.empty:
        cluster = MarkerCluster(name="Farmers Markets").add_to(base_map)
        for _, row in filtered_farmers.iterrows():
            tooltip = f"{row['Market Name']} </b><br><b>Address:</b>  {row.get('Address', 'Address N/A')}"
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
                popup=folium.Popup(popup_text, max_width=300),
                tooltip=tooltip
            ).add_to(cluster)

    st_folium(base_map, width=1000, height=700)
