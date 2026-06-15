import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fitparse import FitFile
import plotly.graph_objects as go

st.title("🚴 E-Bike Ride Dashboard (Clean Reset)")

uploaded_file = st.file_uploader("Upload FIT file")

if uploaded_file:

    fitfile = FitFile(uploaded_file)

    data = []

    for record in fitfile.get_messages("record"):
        row = {}

        for field in record:
            row[field.name] = field.value

        data.append(row)

    df = pd.DataFrame(data)

    # -------------------------
    # GPS (DO NOT TOUCH LOGIC)
    # -------------------------
    gps_lat = "position_lat"
    gps_lon = "position_long"

    if gps_lat not in df.columns or gps_lon not in df.columns:
        st.error("Missing GPS data")
        st.stop()

    df = df.dropna(subset=[gps_lat, gps_lon])

    df["lat"] = df[gps_lat]
    df["lon"] = df[gps_lon]

    if df["lat"].abs().max() > 180:
        df["lat"] = df["lat"] * (180 / 2**31)
        df["lon"] = df["lon"] * (180 / 2**31)

    # -------------------------
    # SAFE NUMERIC CONVERSION (ONLY REAL FIELDS)
    # -------------------------
    for col in ["distance", "speed", "power", "altitude"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # -------------------------
    # DISTANCE
    # -------------------------
    if "distance" in df.columns:
        df["distance_km"] = df["distance"] / 1000
    else:
        df["distance_km"] = range(len(df))

    # -------------------------
    # SMOOTHING
    # -------------------------
    if "altitude" in df.columns:
        df["alt_smooth"] = df["altitude"].rolling(15, min_periods=1).median()

    if "power" in df.columns:
        df["power_smooth"] = df["power"].rolling(15, min_periods=1).median()

    # -------------------------
    # MAP
    # -------------------------
    st.subheader("🗺️ Route Map")

    fig_map = go.Figure()

    fig_map.add_trace(go.Scattermapbox(
        lat=df["lat"],
        lon=df["lon"],
        mode="lines",
        line=dict(width=4, color="blue")
    ))

    fig_map.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=df["lat"].mean(), lon=df["lon"].mean()),
            zoom=12
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=600
    )

    st.plotly_chart(fig_map, use_container_width=True)

    # -------------------------
    # CHARTS
    # -------------------------
    st.subheader("📊 Elevation & Power")

    fig, ax1 = plt.subplots()

    plotted = False

    if "alt_smooth" in df.columns and df["alt_smooth"].notna().any():
        ax1.plot(df["distance_km"], df["alt_smooth"])
        plotted = True

    if "power_smooth" in df.columns and df["power_smooth"].notna().any():
        ax2 = ax1.twinx()
        ax2.plot(df["distance_km"], df["power_smooth"], color="orange")
        plotted = True

    if plotted:
        st.pyplot(fig)
    else:
        st.warning("No usable altitude or power data in this file")

    # -------------------------
    # SUMMARY
    # -------------------------
    st.subheader("Summary")

    col1, col2 = st.columns(2)

    col1.metric(
        "Distance (km)",
        f"{df['distance_km'].max():.1f}" if "distance_km" in df.columns else "N/A"
    )

    if "power" in df.columns and df["power"].notna().any():
        col2.metric("Max Power", f"{df['power'].max():.0f} W")
    else:
        col2.metric("Max Power", "N/A")
