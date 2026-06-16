import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from fitparse import FitFile

# =======================
# PAGE SETUP
# =======================
st.set_page_config(layout="wide")
st.title("🚴 eBike Ride Visualiser")

# =======================
# RESET BUTTON
# =======================
if st.button("🔄 Reset App"):
    st.session_state.clear()
    st.rerun()

# =======================
# FILE UPLOADER (FIXED)
# =======================
uploaded_file = st.file_uploader(
    "Upload your FIT file",
    type=None,
    key="fit_upload_v4"
)

# =======================
# MAIN
# =======================
if uploaded_file:

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
    # METRICS (RESTORED)
    # =======================
    col1, col2, col3 = st.columns(3)

    if "distance" in df.columns:
        distance_km = df["distance"].max() / 1000
        col1.metric("Distance (km)", f"{distance_km:.2f}")

    if "power" in df.columns:
        avg_power = df["power"].mean()
        col2.metric("Avg Power (W)", f"{avg_power:.0f}")

    if "power" in df.columns:
        max_power = df["power"].max()
        col3.metric("Max Power (W)", f"{max_power:.0f}")

    # =======================
    # CHART (RESTORED)
    # =======================
    if "power" in df.columns:
        st.subheader("Power Over Time")
        st.line_chart(df["power"])

    # =======================
    # GPS FIX
    # =======================
    gps_points = []

    if "position_lat" in df.columns and "position_long" in df.columns:

        df["lat"] = pd.to_numeric(df["position_lat"], errors="coerce") * (180 / 2**31)
        df["lon"] = pd.to_numeric(df["position_long"], errors="coerce") * (180 / 2**31)

        gps_df = df[["lat", "lon"]].dropna()
        gps_points = list(zip(gps_df["lat"], gps_df["lon"]))

    st.write("GPS points:", len(gps_points))

    # =======================
    # MAP
    # =======================
    st.subheader("🗺️ Route Map")

    if len(gps_points) > 1:

        m = folium.Map(
            location=[gps_points[0][0], gps_points[0][1]],
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
        st.warning("No GPS data")

else:
    st.info("Upload a FIT file to begin")
