import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from fitparse import FitFile

st.set_page_config(layout="wide")
st.title("🚴 eBike Ride Visualiser")

# =======================
# RESET
# =======================
if st.button("🔄 Reset App"):
    st.session_state.clear()
    st.rerun()

# =======================
# UPLOADER (STABLE)
# =======================
uploaded_file = st.file_uploader(
    "Upload your FIT file",
    type=None,
    key="fit_upload_stable"
)

# =======================
# PROCESS FILE
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

    if df.empty:
        st.error("No data found in FIT file")
        st.stop()

    # =======================
    # CLEAN DATA
    # =======================
    df = df.reset_index(drop=True)

    # =======================
    # METRICS
    # =======================
    st.subheader("📊 Ride Summary")

    col1, col2, col3 = st.columns(3)

    if "distance" in df.columns:
        distance_km = df["distance"].max() / 1000
        col1.metric("Distance (km)", f"{distance_km:.2f}")
    else:
        col1.metric("Distance", "N/A")

    if "power" in df.columns:
        avg_power = df["power"].mean()
        col2.metric("Avg Power (W)", f"{avg_power:.0f}")
        col3.metric("Max Power (W)", f"{df['power'].max():.0f}")
    else:
        col2.metric("Avg Power", "N/A")
        col3.metric("Max Power", "N/A")

    # =======================
    # CHARTS (FIXED)
    # =======================
    st.subheader("📈 Charts")

    if "power" in df.columns:
        power_df = df[["power"]].dropna().reset_index()
        power_df.columns = ["Time", "Power"]

        st.line_chart(power_df, x="Time", y="Power")
    else:
        st.info("No power data available")

    if "altitude" in df.columns:
        alt_df = df[["altitude"]].dropna().reset_index()
        alt_df.columns = ["Time", "Altitude"]

        st.line_chart(alt_df, x="Time", y="Altitude")

    # =======================
    # GPS CONVERSION (CORRECT)
    # =======================
    gps_points = []

    if "position_lat" in df.columns and "position_long" in df.columns:

        df["lat"] = pd.to_numeric(df["position_lat"], errors="coerce") * (180 / 2**31)
        df["lon"] = pd.to_numeric(df["position_long"], errors="coerce") * (180 / 2**31)

        gps_df = df[["lat", "lon"]].dropna()

        gps_points = list(zip(gps_df["lat"], gps_df["lon"]))

    st.write("GPS points:", len(gps_points))

    # =======================
    # MAP (ISOLATED - WON’T BREAK OTHER STUFF)
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
            weight=4,
            opacity=0.8
        ).add_to(m)

        st_folium(m, width=900, height=500)

    else:
        st.warning("No valid GPS data")

else:
    st.info("Upload a FIT file to begin")
