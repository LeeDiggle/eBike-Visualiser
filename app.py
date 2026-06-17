import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from fitparse import FitFile
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("🚴 eBike Ride Visualiser")

# =======================
# RESET BUTTON
# =======================
if st.button("🔄 Reset App"):
    st.session_state.clear()
    st.rerun()

# =======================
# FILE UPLOADERS
# =======================
col1, col2 = st.columns(2)

with col1:
    flow_file = st.file_uploader("Upload Bosch Flow FIT file", type=None)

with col2:
    hr_file = st.file_uploader("Upload HR FIT file (Garmin/Strava)", type=None)

# =======================
# PARSE FIT WITH TIME
# =======================
def parse_fit(file):
    fitfile = FitFile(file)
    records = []

    for record in fitfile.get_messages("record"):
        row = {}
        for field in record:
            row[field.name] = field.value
        records.append(row)

    df = pd.DataFrame(records)

    if not df.empty:
        df = df.reset_index(drop=True)

    return df

# =======================
# MAIN PROCESS
# =======================
if flow_file:

    df = parse_fit(flow_file)

    if df.empty:
        st.error("No data found in Flow FIT file")
        st.stop()

    st.write("Flow records:", len(df))

    # =======================
    # TIME ALIGNMENT (KEY FIX)
    # =======================
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")

    # =======================
    # MERGE HR BY TIME
    # =======================
    if hr_file:
        hr_df = parse_fit(hr_file)

        if "heart_rate" in hr_df.columns and "timestamp" in hr_df.columns:

            hr_df["timestamp"] = pd.to_datetime(hr_df["timestamp"])
            hr_df = hr_df.sort_values("timestamp")

            # Merge on nearest timestamp
            df = pd.merge_asof(
                df,
                hr_df[["timestamp", "heart_rate"]],
                on="timestamp",
                direction="nearest",
                tolerance=pd.Timedelta("5s")
            )

            df.rename(columns={"heart_rate": "Heart Rate"}, inplace=True)

            st.success("Heart rate aligned by timestamp ✅")

        else:
            st.warning("HR file missing timestamp or heart_rate")

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
        col2.metric("Avg Power (W)", f"{df['power'].mean():.0f}")
        col3.metric("Max Power (W)", f"{df['power'].max():.0f}")
    else:
        col2.metric("Avg Power", "N/A")
        col3.metric("Max Power", "N/A")

    # =======================
    # CHART
    # =======================
    st.subheader("📈 Power, Altitude & Heart Rate")

    fig = go.Figure()

    if "power" in df.columns:
        power_smooth = pd.Series(df["power"]).rolling(10, min_periods=1).mean()

        fig.add_trace(go.Scatter(
            x=df["timestamp"],
            y=power_smooth,
            name="Power (W)",
            yaxis="y1"
        ))

    if "altitude" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["timestamp"],
            y=df["altitude"],
            name="Altitude (m)",
            yaxis="y2"
        ))

    if "Heart Rate" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["timestamp"],
            y=df["Heart Rate"],
            name="Heart Rate (bpm)",
            yaxis="y3"
        ))

    fig.update_layout(
        xaxis=dict(title="Time"),

        yaxis=dict(title="Power (W)", side="left"),

        yaxis2=dict(
            title="Altitude (m)",
            overlaying="y",
            side="right"
        ),

        yaxis3=dict(
            title="Heart Rate (bpm)",
            overlaying="y",
            side="right",
            position=0.95
        ),

        legend=dict(x=0, y=1.1, orientation="h"),
        margin=dict(l=40, r=100, t=40, b=40)
    )

    st.plotly_chart(fig, use_container_width=True)

    # =======================
    # MAP
    # =======================
    st.subheader("🗺️ Route Map")

    gps_points = []

    if "position_lat" in df.columns and "position_long" in df.columns:

        df["lat"] = pd.to_numeric(df["position_lat"], errors="coerce") * (180 / 2**31)
        df["lon"] = pd.to_numeric(df["position_long"], errors="coerce") * (180 / 2**31)

        gps_df = df[["lat", "lon"]].dropna()
        gps_points = list(zip(gps_df["lat"], gps_df["lon"]))

    st.write("GPS points:", len(gps_points))

    if len(gps_points) > 1:

        m = folium.Map(tiles="CartoDB positron")

        folium.PolyLine(
            gps_points,
            color="blue",
            weight=4,
            opacity=0.8
        ).add_to(m)

        lats = [p[0] for p in gps_points]
        lons = [p[1] for p in gps_points]

        bounds = [[min(lats), min(lons)], [max(lats), max(lons)]]
        m.fit_bounds(bounds)

        st_folium(m, width=900, height=500)

    else:
        st.warning("No valid GPS data")

else:
    st.info("Upload at least the Flow FIT file to begin")
