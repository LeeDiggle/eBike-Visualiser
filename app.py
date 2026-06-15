import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fitparse import FitFile
import plotly.graph_objects as go

st.title("🚴 E-Bike Ride Dashboard (Fixed)")

uploaded_file = st.file_uploader("Upload FIT file")

if uploaded_file:

    fitfile = FitFile(uploaded_file)

    # -------------------------
    # FIXED RECORD PARSING
    # -------------------------
    data = []

    for record in fitfile.get_messages("record"):
        row = {}

        for field in record:
            # ✅ FIX: correct dictionary assignment
            row[field.name] = field.value

        data.append(row)

    df = pd.DataFrame(data)

    # -------------------------
    # GPS
    # -------------------------
    df = df.dropna(subset=["position_lat", "position_long"])

    df["lat"] = df["position_lat"] * (180 / 2**31)
    df["lon"] = df["position_long"] * (180 / 2**31)

    # -------------------------
    # NUMERIC FIELDS
    # -------------------------
    for col in ["distance", "speed", "power", "altitude"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["distance_km"] = df["distance"] / 1000

    # -------------------------
    # SMOOTHING (for readability)
    # -------------------------
    df["alt_smooth"] = df["altitude"].rolling(10, min_periods=1).median()
    df["power_smooth"] = df["power"].rolling(10, min_periods=1).median()

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

    ax1.plot(df["distance_km"], df["alt_smooth"], label="Altitude")

    ax2 = ax1.twinx()
    ax2.plot(df["distance_km"], df["power_smooth"], color="orange", label="Power")

    st.pyplot(fig)

    # -------------------------
    # SUMMARY
    # -------------------------
    st.subheader("Summary")

    col1, col2 = st.columns(2)

    col1.metric("Distance (km)", f"{df['distance_km'].max():.1f}")

    if df["power"].notna().any():
        col2.metric("Max Power", f"{df['power'].max():.0f} W")
    else:
        col2.metric("Max Power", "N/A")
