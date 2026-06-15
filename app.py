import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fitparse import FitFile
import plotly.graph_objects as go

st.title("🚴 E-Bike Ride Dashboard (Final)")

uploaded_file = st.file_uploader("Upload FIT file")

if uploaded_file:

    fitfile = FitFile(uploaded_file)

    data = []
    for record in fitfile.get_messages("record"):
        row = {}
        for field in record:
            row[field.name] = field.value
        data.append(row)

    if not data:
        st.error("No data found in file")
        st.stop()

    df = pd.DataFrame(data)

    st.subheader("Raw columns")
    st.write(df.columns.tolist())

    # -------------------------
    # SAFE NUMERIC CONVERSION (FIXED PROPERLY)
    # -------------------------
    numeric_cols = [
        "position_lat",
        "position_long",
        "distance",
        "speed",
        "power",
        "altitude"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # -------------------------
    # GPS CLEANING
    # -------------------------
    if "position_lat" not in df.columns or "position_long" not in df.columns:
        st.error("No GPS data found")
        st.stop()

    df = df.dropna(subset=["position_lat", "position_long"])

    # Decode GPS
    df["lat"] = df["position_lat"] * (180 / 2**31)
    df["lon"] = df["position_long"] * (180 / 2**31)

    df = df.dropna(subset=["lat", "lon"])

    # -------------------------
    # Distance
    # -------------------------
    if "distance" in df.columns:
        df["distance_km"] = df["distance"] / 1000
    else:
        df["distance_km"] = range(len(df))

    # -------------------------
    # CLEAN INVALID VALUES (IMPORTANT)
    # -------------------------
    for col in ["altitude", "power", "speed", "distance"]:
        if col in df.columns:
            df[col] = df[col].replace([np.inf, -np.inf], np.nan)

    # -------------------------
    # SMOOTHING
    # -------------------------
    if "altitude" in df.columns:
        df["alt_smooth"] = df["altitude"].rolling(20, min_periods=1).median()

    if "power" in df.columns:
        df["power_smooth"] = df["power"].rolling(20, min_periods=1).median()

    # -------------------------
    # MAP
    # -------------------------
    st.subheader("🗺️ Ride Map")

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
    st.subheader("Elevation / Power")

    fig, ax1 = plt.subplots()

    if "alt_smooth" in df.columns:
        ax1.plot(df["distance_km"], df["alt_smooth"])

    if "power_smooth" in df.columns:
        ax2 = ax1.twinx()
        ax2.plot(df["distance_km"], df["power_smooth"], color="orange")

    st.pyplot(fig)

    # -------------------------
    # SAFE SUMMARY (FIXED)
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
