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
from branca.element import Element

# PAGE CONFIG
st.set_page_config(layout="wide")

logo = Image.open(r"chicago_logo.png")

# IMAGE
st.markdown(
    """
    <style>
    .logo-container {
        position: absolute;
        top: 2rem;
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
            text-align: center;
            background-color: #f0f0f0;  /* light grey */
            border-radius: 12px;         /* rounded corners */
            padding: 1em 2em;
            box-shadow: 1px 1px 5px rgba(0,0,0,0.1);
            min-width: 140px;
        }
    </style>
""", unsafe_allow_html=True)

# TITLE
st.markdown('<h1 class="main-title">Chicago Urban Food Ecosystem Map</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">An initiative from the Office of Mayor Brandon Johnson</p>', unsafe_allow_html=True)

# FILE PATHS
SHAPEFILE_PATH = "neighborhoods_shapefile.shp"
CUAMPS_CSV_PATH = "cuamp_gardens geocoded.csv"
FOOD_TAVERNS_CSV_PATH = "Food_Tavern_PackGoods_Current.csv"
FOOD_ECOSYSTEM_CSV_PATH = "Food_Ecosystem_Data_2025.csv"
FARMERS_MARKETS_CSV_PATH = "Farmers_Markets.csv"
SNAP_PATH = r"C:\Users\488325\Python\chicago_urban_food_infrastructure\SNAP.csv"

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
    snap = pd.read_csv(SNAP_PATH)
    farmers = pd.read_csv(FARMERS_MARKETS_CSV_PATH)
    return cuamps, taverns, ecosystem, farmers, snap

# LOAD DATA
file = load_shapefile()
cuamps, taverns, ecosystem, farmers, snap = load_csv_data()

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

@st.cache_data
def perform_spatial_joins(_file, _cuamps, _taverns, _ecosystem, _farmers, _snap):
    def point_gdf(df, lat_col, lon_col):
        return gpd.GeoDataFrame(df.copy(), geometry=gpd.points_from_xy(df[lon_col], df[lat_col]), crs="EPSG:4326")

    cuamps_gdf = point_gdf(_cuamps, 'Latitude', 'Longitude')
    taverns_gdf = point_gdf(_taverns, 'Latitude', 'Longitude')
    ecosystem_gdf = point_gdf(_ecosystem, 'Latitude', 'Longitude')
    farmers_gdf = point_gdf(_farmers, 'Latitude', 'Longitude')
    snap_gdf = point_gdf(_snap, 'Latitude', 'Longitude')

    def join(gdf): return gpd.sjoin(gdf, _file, how='left', predicate='within').rename(columns={"neighborhood_right": "neighborhood"})

    return (
        join(cuamps_gdf),
        join(taverns_gdf),
        join(ecosystem_gdf),
        join(farmers_gdf),
        join(snap_gdf)
    )

cuamps_joined, taverns_joined, ecosystem_joined, farmers_joined, snap_joined = perform_spatial_joins(file, cuamps, taverns, ecosystem, farmers, snap)

# FILTERS
with st.sidebar:
    st.markdown("### 🔍 Filters")
    all_neighborhoods = sorted(file["neighborhood"].dropna().unique())
    selected_neighborhoods = st.multiselect("Neighborhood", all_neighborhoods, default= all_neighborhoods)
    show_wards = st.checkbox("Ward Labels", value=False)
    

    #show_gardens = st.checkbox("Community Gardens", value=False)
    show_ecosystem = st.checkbox("Ecosystem Sites", value=False)
    show_taverns = st.checkbox("Food Establishments", value=False)
    show_farmers = st.checkbox("Farmers Markets", value=False)
    show_snap = st.checkbox("Grocery Stores (SNAP)", value=False)
    if show_snap:
        all_store_types = sorted(snap["Store_Type"].unique())
        selected_store_types = st.sidebar.multiselect("Select Store Types", all_store_types, default=all_store_types)
        filtered_snap = snap[snap["Store_Type"].isin(selected_store_types)]
    else:
        filtered_snap = pd.DataFrame()

    #selected_food = st.multiselect("Food Producing Gardens", ["Yes", "N/A"], default=["Yes", "N/A"]) if show_gardens else []
    tavern_types = taverns['License Name'].dropna().unique().tolist() if show_taverns else []
    selected_tavern_types = st.multiselect("License Type", tavern_types, default=tavern_types) if show_taverns else []
    dcase_options = ["Supported by DCASE", "Not Supported"] if show_farmers else []
    selected_dcase = st.multiselect("DCASE Support", dcase_options, default=dcase_options) if show_farmers else []

@st.cache_data
def filter_snap(_snap_df, selected_store_types, neighborhoods):
    return _snap_df[
        (_snap_df["Store_Type"].isin(selected_store_types)) &
        (_snap_df["neighborhood"].isin(neighborhoods))
    ]

@st.cache_data
def filter_taverns(_taverns_df, selected_types, neighborhoods):
    return _taverns_df[
        (_taverns_df["License Name"].isin(selected_types)) &
        (_taverns_df["neighborhood"].isin(neighborhoods))
    ]

@st.cache_data
def filter_ecosystem(_ecosystem_df, neighborhoods):
    return _ecosystem_df[_ecosystem_df["neighborhood"].isin(neighborhoods)]

@st.cache_data
def filter_farmers(_farmers_df, selected_support, neighborhoods):
    return _farmers_df[
        (_farmers_df["Support"].isin(selected_support)) &
        (_farmers_df["neighborhood"].isin(neighborhoods))
    ]

# APPLY FILTERS
#filtered_cuamps = cuamps_joined[(cuamps_joined["Food Producing"].isin(selected_food)) & (cuamps_joined["neighborhood"].isin(selected_neighborhoods))] if show_gardens else pd.DataFrame(columns=cuamps.columns)
filtered_snap = filter_snap(snap_joined, selected_store_types, selected_neighborhoods) if show_snap else pd.DataFrame()
filtered_taverns = filter_taverns(taverns_joined, selected_tavern_types, selected_neighborhoods) if show_taverns else pd.DataFrame()
filtered_ecosystem = filter_ecosystem(ecosystem_joined, selected_neighborhoods) if show_ecosystem else pd.DataFrame()
filtered_farmers = filter_farmers(farmers_joined, selected_dcase, selected_neighborhoods) if show_farmers else pd.DataFrame()

# DEFINE COLORS FOR FILTER TYPES
license_colors = {
    'Retail Food Establishment': '#1f78b4',      # blue
    'Tavern': '#6a3d9a',                        # purple
    'Package Goods': '#b15928',                  # brownish dark orange
    'Shared Kitchen User (Long Term)': '#ff7f00', # bright orange
    'Wholesale Food Establishment': '#33a02c',   # green
    'Food - Shared Kitchen': '#a6cee3',           # light blue
    'Mobile Food License': '#fb9a99',              # pinkish red
    'Food - Shared Kitchen - Supplemental': '#cab2d6'  # light purple
}

dcase_color = {
    "Supported by DCASE": '#33a02c',  # green
    "Not Supported": '#b2df8a'        # light green (different from gray)
}

snap_colors = {
    'Grocery Store': '#e31a1c',            # red
    'Specialty Store': '#6a3d9a',          # purple (distinct from tavern)
    'Super Store': '#1f78b4',              # blue (distinct from retail food)
    'Other': '#ff7f00',                    # orange
    'Convenience Store': '#fb9a99',        # pinkish
    'Farmers and Markets': '#b15928',      # brownish orange
    'Restaurant Meals Program': '#a6cee3'  # light blue
}

# MAP
map_center = [41.8781, -87.6298]
base_map = folium.Map(location=map_center, zoom_start=11, tiles="cartodbpositron")

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
    ward_centroids = cuamps_joined.groupby('ward')[['Latitude', 'Longitude']].mean().dropna().reset_index()
    for _, row in ward_centroids.iterrows():
        folium.map.Marker(
            [row['Latitude'], row['Longitude']],
            icon=folium.DivIcon(html=f"<div style='font-size:10pt; font-weight:bold; color:black'>Ward {int(row['ward'])}</div>")
        ).add_to(base_map)

# if show_gardens and not filtered_cuamps.empty:
#     cluster = MarkerCluster(name="Community Gardens").add_to(base_map)
#     for _, row in filtered_cuamps.iterrows():
#         tooltip = f"{row['growing_site_name']} </b><br> Address:  {row.get('address', 'Address N/A')}"
#         folium.CircleMarker(
#             location=(row["Latitude"], row["Longitude"]),
#             radius=5,
#             color="green",
#             fill=True,
#             fill_opacity=0.6,
#             popup=folium.Popup(f"<b>{row['growing_site_name']}</b><br>Food Producing: {row['Food Producing']}", max_width=300),
#             tooltip=tooltip
#         ).add_to(cluster)

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
        license_name = row['License Name']
        color = license_colors.get(license_name, 'purple')
        tooltip = f"{row['DBA Name']} </b><br><b>Address:</b>  {row.get('Address', 'Address N/A')}"
        folium.CircleMarker(
            location=(row["Latitude"], row["Longitude"]),
            radius=5,
            color=color,
            fill=True,
            fill_opacity=0.6,
            popup=folium.Popup(f"<b>{row['DBA Name']}</b><br>License: {license_name}", max_width=300),
            tooltip=tooltip
        ).add_to(cluster)

if show_farmers and not filtered_farmers.empty:
    cluster = MarkerCluster(name="Farmers Markets").add_to(base_map)
    for _, row in filtered_farmers.iterrows():
        color = dcase_color.get(row['Support'], 'gray')
        tooltip = f"{row['Market Name']} </b><br><b>Address:</b>  {row.get('Address', 'Address N/A')}<br>{row['Support']}"
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

if show_snap and not filtered_snap.empty:
    cluster = MarkerCluster(name="Grocery Stores (SNAP)").add_to(base_map)
    for _, row in filtered_snap.iterrows():
        store_type = row.get("Store_Type", "Other")
        marker_color = snap_colors.get(store_type, "gray")
        tooltip = f"{row['Store_Name']} — {row.get('Address', 'Address N/A')}"

        folium.CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=5,
            color=marker_color,
            fill=True,
            fill_color=marker_color,
            fill_opacity=0.6,
            tooltip=tooltip,
            popup=folium.Popup(f"<b>{row['Store_Name']}</b><br>{row.get('Address', 'Address N/A')}", max_width=300)
        ).add_to(cluster)

# SUMMARY METRICS

st.markdown("<div class='metrics-row'>" +
    #f"<div class='metric-container'><h4><b>Total Gardens<b></h4><p><b>{len(filtered_cuamps)}<b></p></div>" +
    f"<div class='metric-container'><h4><b>Ecosystem Sites</b></h4><p><b>{len(filtered_ecosystem)}</b></p></div>" +
    f"<div class='metric-container'><h4><b>Food Establishments</b></h4><p><b>{len(filtered_taverns)}</b></p></div>" +
    f"<div class='metric-container'><h4><b>Grocery Stores</b></h4><p><b>{len(filtered_snap)}</b></p></div>" +
    f"<div class='metric-container'><h4><b>Farmers Markets</b></h4><p><b>{len(filtered_farmers)}</b></p></div>" +
    "</div>", unsafe_allow_html=True)
#LEGEND
legend_html_sections = []

if show_ecosystem:
    ecosystem_section = '<strong>Ecosystem Sites</strong><br>'
    ecosystem_section += f'<i style="background:orange; width:10px; height:10px; float:left; margin-right:6px;"></i> Ecosystem Sites<br><br>'
    legend_html_sections.append(ecosystem_section)

if show_farmers:
    farmers_section = '<strong>Farmers Markets</strong><br>'
    for support_type, color in dcase_color.items():
        if support_type in selected_dcase:
            farmers_section += f'<i style="background:{color}; width:10px; height:10px; float:left; margin-right:6px;"></i> {support_type}<br>'
    farmers_section += '<br>'
    legend_html_sections.append(farmers_section)

if show_snap:
    snap_section = '<strong>Grocery Stores</strong><br>'
    for store_type in selected_store_types:
        color = snap_colors.get(store_type, "black")
        snap_section += f'<i style="background:{color}; width:10px; height:10px; float:left; margin-right:6px;"></i> {store_type}<br>'
    snap_section += '<br>'
    legend_html_sections.append(snap_section)

if show_taverns:
    tavern_section = '<strong>Food Establishments</strong><br>'
    for license_type in selected_tavern_types:
        color = license_colors.get(license_type, "black")
        tavern_section += f'<i style="background:{color}; width:10px; height:10px; float:left; margin-right:6px;"></i> {license_type}<br>'
    tavern_section += '<br>'
    legend_html_sections.append(tavern_section)

if legend_html_sections:
    legend_html = f"""
    <div style="
        position: fixed;
        bottom: 50px;
        right: 50px;
        z-index: 9999;
        background-color: white;
        padding: 10px;
        border: 2px solid black;
        border-radius: 8px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
        font-size: 13px;
        max-width: 250px;
    ">
        {''.join(legend_html_sections)}
        <div style="clear: both;"></div>
    </div>
    """
    base_map.get_root().html.add_child(Element(legend_html))

st_folium(base_map, width=1000, height=700)
