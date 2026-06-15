import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fitparse import FitFile
import plotly.graph_objects as go

st.title("🚴 E-Bike Ride Dashboard (Stable Version)")

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
    # HARD SAFETY CLEANING
    # -------------------------

    # Ensure numeric conversion
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="ignore")

    # Drop rows where GPS is missing
    if "position_lat" in df.columns and "position_long" in df.columns:
        df = df.dropna(subset=["position_lat", "position_long"])

    if df.empty:
        st.error("No GPS data available after cleaning")
        st.stop()

    # -------------------------
    # Decode GPS (only if valid)
    # -------------------------
    if "position_lat" in df.columns:
        df["lat"] = df["position_lat"].apply(
            lambda x: x * (180 / 2**31) if pd.notnull(x) else np.nan
        )

    if "position_long" in df.columns:
        df["lon"] = df["position_long"].apply(
            lambda x: x * (180 / 2**31) if pd.notnull(x) else np.nan
        )

    # Remove invalid GPS rows
    df = df.dropna(subset=["lat", "lon"])

    # -------------------------
    # Distance fallback safety
    # -------------------------
    if "distance" in df.columns:
        df["distance_km"] = df["distance"] / 1000
    else:
        df["distance_km"] = range(len(df))

    # -------------------------
    # Clean numeric fields
    # -------------------------
    for col in ["speed", "power", "altitude"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # -------------------------
    # Basic smoothing
    # -------------------------
    if "altitude" in df.columns:
        df["alt_smooth"] = df["altitude"].rolling(20, min_periods=1).median()

    if "power" in df.columns:
        df["power_smooth"] = df["power"].rolling(20, min_periods=1).median()

    # -------------------------
    # MAP (SAFE VERSION)
    # -------------------------
    st.subheader("🗺️ Ride Map")

    fig_map = go.Figure()

    fig_map.add_trace(go.Scattermapbox(
        lat=df["lat"],
        lon=df["lon"],
        mode="lines",
        line=dict(width=4, color="blue"),
        name="Route"
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
    # SIMPLE CHARTS
    # -------------------------
    st.subheader("Elevation / Power")

    fig, ax1 = plt.subplots()

    if "alt_smooth" in df.columns:
        ax1.plot(df["distance_km"], df["alt_smooth"], label="Elevation")

    if "power_smooth" in df.columns:
        ax2 = ax1.twinx()
        ax2.plot(df["distance_km"], df["power_smooth"], color="orange")

    st.pyplot(fig)

    # -------------------------
    # METRICS (SAFE)
    # -------------------------
    st.subheader("Summary")

    col1, col2 = st.columns(2)

    col1.metric("Distance (km)", f"{df['distance_km'].max():.1f}")

    if "power" in df.columns:
        col2.metric("Max Power", f"{np.nanmax(df['power']):.0f} W")
    else:
        col2.metric("Max Power", "N/A")
