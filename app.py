import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fitparse import FitFile
import plotly.graph_objects as go

st.title("🚴 E-Bike Ride Dashboard (Robust FIT Parser)")

uploaded_file = st.file_uploader("Upload FIT file")

if uploaded_file:

    fitfile = FitFile(uploaded_file)

    # -------------------------
    # STRICT FIELD EXTRACTION
    # -------------------------
    records = []

    for record in fitfile.get_messages("record"):
        data = {
            "distance": None,
            "speed": None,
            "power": None,
            "altitude": None,
            "lat": None,
            "lon": None
        }

        for field in record:
            name = field.name
            value = field.value

            if name in data:
                data[name] = value

        records.append(data)

    df = pd.DataFrame(records)

    st.subheader("Raw data check")
    st.write(df.head())

    # -------------------------
    # CLEAN DATA
    # -------------------------
    df = df.dropna(subset=["lat", "lon"], how="any")

    if df.empty:
        st.error("No GPS data found after cleaning")
        st.stop()

    # -------------------------
    # CONVERT GPS IF NEEDED
    # -------------------------
    # Sometimes FIT already gives degrees, sometimes scaled
    if df["lat"].abs().max() > 180:
        df["lat"] = df["lat"] * (180 / 2**31)
        df["lon"] = df["lon"] * (180 / 2**31)

    # -------------------------
    # DISTANCE
    # -------------------------
    if df["distance"].notna().any():
        df["distance_km"] = pd.to_numeric(df["distance"], errors="coerce") / 1000
    else:
        df["distance_km"] = range(len(df))

    # -------------------------
    # NUMERIC CLEAN
    # -------------------------
    for col in ["speed", "power", "altitude"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # -------------------------
    # REMOVE EMPTY SIGNAL BLOCKS
    # -------------------------
    df = df.dropna(subset=["lat", "lon"], how="any")

    # -------------------------
    # SMOOTHING
    # -------------------------
    if df["altitude"].notna().any():
        df["alt_smooth"] = df["altitude"].rolling(15, min_periods=1).median()

    if df["power"].notna().any():
        df["power_smooth"] = df["power"].rolling(15, min_periods=1).median()

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

    if df["alt_smooth"].notna().any():
        ax1.plot(df["distance_km"], df["alt_smooth"])

    if "power_smooth" in df.columns and df["power_smooth"].notna().any():
        ax2 = ax1.twinx()
        ax2.plot(df["distance_km"], df["power_smooth"], color="orange")

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
