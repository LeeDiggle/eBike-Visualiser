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
# RESET BUTTON (fixes iPad issues)
# =======================
if st.button("🔄 Reset App"):
    st.session_state.clear()
    st.rerun()

# =======================
# FILE UPLOADER (FIXED)
# =======================
uploaded_file = st.file_uploader(
    "Upload your FIT file",
    type=None,                     # allow any file
    accept_multiple_files=False,
    key="fit_upload_v3"            # 🔥 change this if it ever locks again
)

# =======================
# MAIN APP
# =======================
if uploaded_file:

    st.success("File uploaded successfully")

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

    st.write("Total records:", len(df))

    # Debug view (helps if anything breaks again)
    with st.expander("🔍 Debug data"):
        st.write(df.head())

    # =======================
    # GPS CONVERSION (CRITICAL FIX)
    # =======================
    gps_points = []

    if "position_lat" in df.columns and "position_long" in df.columns:

        # Convert semicircles → degrees
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

        center_lat = gps_points[0][0]
        center_lon = gps_points[0][1]

        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=13,
            tiles="CartoDB positron"   # ✅ reliable tiles
        )

        folium.PolyLine(
            gps_points,
            color="blue",
            weight=4,
            opacity=0.8
        ).add_to(m)

        st_folium(m, width=900, height=500)

    else:
        st.warning("No valid GPS data found")

else:
    st.info("Upload a FIT file to begin")
