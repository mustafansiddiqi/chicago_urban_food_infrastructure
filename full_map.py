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
DPD_SB_CSV_PATH = "Food_Ecosystem_Data_2025.csv"
FARMERS_MARKETS_CSV_PATH = "Farmers_Markets.csv"
SNAP_PATH = "SNAP.csv"
DPD_COM_GRANTS = "DPD_Community_Grants.csv"
NEW_OPP_PATH = "dpd_new_opp.csv"

# CACHED DATA LOADERS
@st.cache_resource
def load_shapefile():
    gdf = gpd.read_file(SHAPEFILE_PATH).rename(columns={'neighborho': 'neighborhood'})
    gdf["neighborhood"] = gdf["neighborhood"].str.strip().str.title()
    return gdf

@st.cache_data
def load_csv_data():
    cuamps = pd.read_csv(CUAMPS_CSV_PATH, header=0)
    taverns = pd.read_csv(FOOD_TAVERNS_CSV_PATH, header=0)
    small_business_dpd = pd.read_csv(DPD_SB_CSV_PATH, header=0)
    snap = pd.read_csv(SNAP_PATH, header=0)
    farmers = pd.read_csv(FARMERS_MARKETS_CSV_PATH, header=0)
    community_dpd = pd.read_csv(DPD_COM_GRANTS, header=0)
    new_opp_dpd = pd.read_csv(NEW_OPP_PATH, header=0)
    return cuamps, taverns, small_business_dpd, farmers, snap, community_dpd, new_opp_dpd

# LOAD DATA
file = load_shapefile()
cuamps, taverns, small_business_dpd, farmers, snap, community_dpd, new_opp_dpd = load_csv_data()

# CLEAN & STANDARDIZE DATA
cuamps["neighborhood"] = cuamps["neighborhood"].astype(str).str.strip().str.title()

for df in [cuamps, taverns, small_business_dpd, community_dpd]:
    df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
    df.dropna(subset=['Latitude', 'Longitude'], inplace=True)

farmers['Latitude'] = pd.to_numeric(farmers['Latitude'], errors='coerce')
farmers['Longitude'] = pd.to_numeric(farmers['Longitude'], errors='coerce')
farmers.dropna(subset=['Latitude', 'Longitude'], inplace=True)

farmers['DCASE'] = farmers['DCASE'].astype(bool)
farmers['Support'] = np.where(farmers['DCASE'], "Supported by DCASE", "Not Supported")
all_store_types = sorted(snap["Store_Type"].dropna().astype(str).unique())

community_dpd['Latitude'] = pd.to_numeric(community_dpd['Latitude'], errors='coerce')
community_dpd['Longitude'] = pd.to_numeric(community_dpd['Longitude'], errors='coerce')
community_dpd.dropna(subset=['Latitude','Longitude'], inplace=True)

@st.cache_data
def perform_spatial_joins(_file, _cuamps, _taverns, _small_business_dpd, _farmers, _snap, _community_dpd, _new_opp_dpd):
    def point_gdf(df, lat_col, lon_col):
        df[lat_col] = pd.to_numeric(df[lat_col], errors='coerce')
        df[lon_col] = pd.to_numeric(df[lon_col], errors='coerce')
        df = df.dropna(subset=[lat_col, lon_col])
        return gpd.GeoDataFrame(df.copy(), geometry=gpd.points_from_xy(df[lon_col], df[lat_col]), crs="EPSG:4326")

    cuamps_gdf = point_gdf(_cuamps, 'Latitude', 'Longitude')
    taverns_gdf = point_gdf(_taverns, 'Latitude', 'Longitude')
    small_business_dpd_gdf = point_gdf(_small_business_dpd, 'Latitude', 'Longitude')
    farmers_gdf = point_gdf(_farmers, 'Latitude', 'Longitude')
    snap_gdf = point_gdf(_snap, 'Latitude', 'Longitude')
    community_dpd_gdf = point_gdf(_community_dpd, 'Latitude', 'Longitude')
    new_opp_dpd_gdf = point_gdf(_new_opp_dpd, 'Latitude', 'Longitude')

    def join(gdf): 
        return gpd.sjoin(gdf, _file, how='left', predicate='within').rename(columns={"neighborhood_right": "neighborhood"})

    return (
        join(cuamps_gdf),
        join(taverns_gdf),
        join(small_business_dpd_gdf),
        join(farmers_gdf),
        join(snap_gdf),
        join(community_dpd_gdf),
        join(new_opp_dpd_gdf)
    )
snap.head()
cuamps_joined, taverns_joined, small_business_dpd_joined, farmers_joined, snap_joined, community_dpd_joined, new_opp_dpd_joined = perform_spatial_joins(file, cuamps, taverns, small_business_dpd, farmers, snap, community_dpd, new_opp_dpd)

# FILTERS
with st.sidebar:
    st.markdown("### 🔍 Filters")
    all_neighborhoods = sorted(file["neighborhood"].dropna().unique())
    selected_neighborhoods = st.multiselect("Neighborhood", all_neighborhoods, default= all_neighborhoods)
    show_wards = st.checkbox("Ward Labels", value=False)
    show_taverns = st.checkbox("Food Establishments-BACP Licenses", value=False)
    show_farmers = st.checkbox("Farmers Markets", value=False)
    show_snap = st.checkbox("SNAP Retailers", value=False)
    if show_snap:
        all_store_types = sorted(snap["Store_Type"].dropna().astype(str).unique())
        selected_store_types = st.sidebar.multiselect("Select Store Types", all_store_types, default=all_store_types)
        filtered_snap = snap[snap["Store_Type"].isin(selected_store_types)]
    else:
        filtered_snap = pd.DataFrame()
    
    show_grants = st.checkbox("DPD Grants", value=False)
    show_small_business_dpd = False
    show_dpd_community = False
    show_new_opp_dpd = False
    if show_grants:
        show_small_business_dpd = st.checkbox("DPD Small Business Improvement Fund", value=False)
        show_dpd_community = st.checkbox("DPD Community Development Grants", value=False)
        show_new_opp_dpd = st.checkbox("New Opportunity Development Grants", value = False)
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
def filter_farmers(_farmers_df, selected_support, neighborhoods):
    return _farmers_df[
        (_farmers_df["Support"].isin(selected_support)) &
        (_farmers_df["neighborhood"].isin(neighborhoods))
    ]

@st.cache_data
def filter_small_business_dpd(_small_business_dpd_df, neighborhoods):
    return _small_business_dpd_df[_small_business_dpd_df["neighborhood"].isin(neighborhoods)]

@st.cache_data
def filter_community_dpd(_community_dpd_df, neighborhoods): 
    return _community_dpd_df[_community_dpd_df["neighborhood"].isin(neighborhoods)]

@st.cache_data
def filter_new_opp_dpd(_new_opp_dpd_df, neighborhoods): 
    return _new_opp_dpd_df[_new_opp_dpd_df["neighborhood"].isin(neighborhoods)]

# APPLY FILTERS
filtered_snap = filter_snap(snap_joined, selected_store_types, selected_neighborhoods) if show_snap else pd.DataFrame()
filtered_taverns = filter_taverns(taverns_joined, selected_tavern_types, selected_neighborhoods) if show_taverns else pd.DataFrame()
filtered_farmers = filter_farmers(farmers_joined, selected_dcase, selected_neighborhoods) if show_farmers else pd.DataFrame()
filtered_small_business_dpd = filter_small_business_dpd(small_business_dpd_joined, selected_neighborhoods) if show_small_business_dpd else pd.DataFrame()
filtered_dpd_community = filter_community_dpd(community_dpd_joined, selected_neighborhoods) if show_dpd_community else pd.DataFrame()
filtered_new_opp = new_opp_dpd_joined[new_opp_dpd_joined["neighborhood"].isin(selected_neighborhoods)] if show_new_opp_dpd else pd.DataFrame()
filtered_dpd = pd.concat([filtered_small_business_dpd, filtered_dpd_community, filtered_new_opp], ignore_index=True) if show_grants else pd.DataFrame()

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

if show_taverns and not filtered_taverns.empty:
    cluster = MarkerCluster(name="Food Establishments - BACP Licenses").add_to(base_map)
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
    cluster = MarkerCluster(name="SNAP Retailers").add_to(base_map)
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

cluster = MarkerCluster(name="DPD Grants").add_to(base_map)
dpd_colors = {"DPD Small Business Improvement Fund":"#3182bd","DPD Community Development Grants":"#e6550d","New Opportunity DPD Grants":"#33a02c"}

for df, show, color_key in [(filtered_small_business_dpd, show_small_business_dpd, "DPD Small Business Improvement Fund"),
                             (filtered_dpd_community, show_dpd_community, "DPD Community Development Grants"),
                             (filtered_new_opp, show_new_opp_dpd, "New Opportunity DPD Grants")]:
    if show and not df.empty:
        for _, row in df.iterrows():
            tooltip = f"{row.get('Project Name', row.get('Business Name','N/A'))}<br>Type: {row.get('Business Type','N/A')}<br>Address: {row.get('Address','N/A')}"
            folium.CircleMarker(
                location=[row['Latitude'], row['Longitude']],
                radius=6,
                color=dpd_colors[color_key],
                fill=True,
                fill_color=dpd_colors[color_key],
                fill_opacity=0.7,
                popup=folium.Popup(tooltip, max_width=300),
                tooltip=tooltip
            ).add_to(cluster)

# SUMMARY METRICS
dpd_count = len(filtered_dpd) if show_grants else 0
st.markdown("<div class='metrics-row'>" +
    f"<div class='metric-container'><h4><b>DPD Grants</b></h4><p><b>{dpd_count}</b></p></div>" +
    f"<div class='metric-container'><h4><b>Food Establishments-BACP Licenses</b></h4><p><b>{len(filtered_taverns)}</b></p></div>" +
    f"<div class='metric-container'><h4><b>SNAP Retailers</b></h4><p><b>{len(filtered_snap)}</b></p></div>" +
    f"<div class='metric-container'><h4><b>Farmers Markets</b></h4><p><b>{len(filtered_farmers)}</b></p></div>" +
    "</div>", unsafe_allow_html=True)

#LEGEND
legend_html_sections = []

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

if show_small_business_dpd or show_dpd_community or show_new_opp_dpd:
    legend_html_sections.append('<strong>CPD Grants</strong><br>')

    for show_flag, key, label in [
        (show_small_business_dpd, 'DPD Small Business Improvement Fund', 'DPD Small Business Improvement Fund'),
        (show_dpd_community, 'DPD Community Development Grants', 'DPD Community Development Grants'),
        (show_new_opp_dpd, 'New Opportunity DPD Grants', 'New Opportunity DPD Grants')
    ]:
        if show_flag:
            legend_html_sections.append(
                f'<i style="background:{dpd_colors[key]}; width:10px; height:10px; float:left; margin-right:6px;"></i> {label}<br>'
            )

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
