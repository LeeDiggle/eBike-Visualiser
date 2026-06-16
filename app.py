import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from fitparse import FitFile

st.set_page_config(layout="wide")

st.title("🚴 eBike Ride Visualiser")

uploaded_file = st.file_uploader("Upload your FIT file", type=["fit"])

if uploaded_file:

    # =======================
    # READ FIT FILE
    # =======================
    fitfile = FitFile(uploaded_file)

    records = []
    for record in fitfile.get_messages("record"):
        row = {}
        for field in record:
            row[field.name] = field.value
        records.append(row)

    df = pd.DataFrame(records)

    st.write("Records:", len(df))

    # =======================
    # FIX GPS CONVERSION
    # =======================
    if "position_lat" in df.columns and "position_long" in df.columns:

        # Convert semicircles → degrees
        df["lat"] = pd.to_numeric(df["position_lat"], errors="coerce") * (180 / 2**31)
        df["lon"] = pd.to_numeric(df["position_long"], errors="coerce") * (180 / 2**31)

        gps_df = df[["lat", "lon"]].dropna()

        gps_points = list(zip(gps_df["lat"], gps_df["lon"]))

    else:
        gps_points = []

    st.write("GPS points:", len(gps_points))

    # =======================
    # MAP
    # =======================
    st.subheader("Route Map")

    if len(gps_points) > 1:

        center_lat = gps_points[0][0]
        center_lon = gps_points[0][1]

        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=13,
            tiles="CartoDB positron"
        )

        folium.PolyLine(
            gps_points,
            color="blue",
            weight=4
        ).add_to(m)

        st_folium(m, width=900, height=500)

    else:
        st.warning("No valid GPS data found")
