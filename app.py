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
    bosch_file = st.file_uploader(
        "Upload Bosch Flow FIT file",
        type=None,
        key="bosch_fit"
    )

with col2:
    strava_file = st.file_uploader(
        "Upload Strava FIT file (Heart Rate)",
        type=None,
        key="strava_fit"
    )

# =======================
# FIT → DATAFRAME FUNCTION
# =======================
def fit_to_df(uploaded_file):
    fitfile = FitFile(uploaded_file)

    records = []
    for record in fitfile.get_messages("record"):
        row = {}
        for field in record:
            row[field.name] = field.value
        records.append(row)

    df = pd.DataFrame(records)

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    return df


# =======================
# MAIN PROCESS
# =======================
if bosch_file:

    bosch_df = fit_to_df(bosch_file)

    if bosch_df.empty:
        st.error("No data in Bosch FIT file")
        st.stop()

    df = bosch_df.copy()

    # =======================
    # MERGE HEART RATE
    # =======================
    if strava_file:

        strava_df = fit_to_df(strava_file)

        if "heart_rate" in strava_df.columns:

            hr_df = strava_df[["timestamp", "heart_rate"]].dropna()

            df = df.sort_values("timestamp")
            hr_df = hr_df.sort_values("timestamp")

            df = pd.merge_asof(
                df,
                hr_df,
                on="timestamp",
                direction="nearest",
                tolerance=pd.Timedelta("3s")
            )

            st.success("✅ Heart rate merged successfully")

        else:
            st.warning("No heart rate found in Strava file")

    df = df.reset_index(drop=True)

    st.write("Records:", len(df))

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
    # CHART (MULTI-AXIS)
    # =======================
    st.subheader("📈 Power, Altitude & Heart Rate")

    chart_df = pd.DataFrame()

    if "power" in df.columns:
        chart_df["Power"] = df["power"]

    if "altitude" in df.columns:
        chart_df["Altitude"] = df["altitude"]

    if "heart_rate" in df.columns:
        chart_df["Heart Rate"] = df["heart_rate"]

    chart_df = chart_df.dropna(how="all").reset_index()

    if not chart_df.empty:

        # Smooth signals
        if "Power" in chart_df.columns:
            chart_df["Power Smooth"] = chart_df["Power"].rolling(
                window=10, min_periods=1
            ).mean()

        if "Heart Rate" in chart_df.columns:
            chart_df["HR Smooth"] = chart_df["Heart Rate"].rolling(
                window=15, min_periods=1
            ).mean()

        chart_df = chart_df.rename(columns={"index": "Time"})

        fig = go.Figure()

        # Power (LEFT AXIS)
        if "Power Smooth" in chart_df.columns:
            fig.add_trace(go.Scatter(
                x=chart_df["Time"],
                y=chart_df["Power Smooth"],
                name="Power",
                yaxis="y1"
            ))

        # Heart Rate (RIGHT AXIS)
        if "HR Smooth" in chart_df.columns:
            fig.add_trace(go.Scatter(
                x=chart_df["Time"],
                y=chart_df["HR Smooth"],
                name="Heart Rate",
                yaxis="y2"
            ))

        # Altitude (THIRD AXIS)
        if "Altitude" in chart_df.columns:
            altitude_adjusted = chart_df["Altitude"] - chart_df["Altitude"].min()

            fig.add_trace(go.Scatter(
                x=chart_df["Time"],
                y=altitude_adjusted,
                name="Altitude",
                yaxis="y3",
                opacity=0.4
            ))

        fig.update_layout(
            xaxis=dict(title="Time"),

            yaxis=dict(
                title="Power (W)"
            ),

            yaxis2=dict(
                title="Heart Rate (bpm)",
                overlaying="y",
                side="right"
            ),

            yaxis3=dict(
                title="Altitude (relative m)",
                anchor="free",
                overlaying="y",
                side="right",
                position=1.08
            ),

            legend=dict(orientation="h"),
            margin=dict(l=40, r=100, t=40, b=40)
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("No chart data available")

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
    st.info("Upload your Bosch FIT file to begin")
