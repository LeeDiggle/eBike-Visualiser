import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fitparse import FitFile
import plotly.graph_objects as go

st.title("🚴 E-Bike Ride Dashboard (Stable Architecture)")

uploaded_file = st.file_uploader("Upload FIT file")

if uploaded_file:

    # =========================
    # 1. RAW INGESTION (DO NOT TOUCH)
    # =========================
    fitfile = FitFile(uploaded_file)

    raw = []
    for record in fitfile.get_messages("record"):
        row = {}
        for field in record:
            row[field.name] = field.value
        raw.append(row)

    df = pd.DataFrame(raw)

    st.subheader("Debug: Available columns")
    st.write(df.columns.tolist())

    # =========================
    # 2. GPS (SAFE ONLY)
    # =========================
    if "position_lat" not in df.columns or "position_long" not in df.columns:
        st.error("No GPS data found")
        st.stop()

    gps = df[["position_lat", "position_long"]].copy()
    gps = gps.dropna()

    df = df.loc[gps.index].copy()

    df["lat"] = df["position_lat"] * (180 / 2**31)
    df["lon"] = df["position_long"] * (180 / 2**31)

    # =========================
    # 3. DISTANCE (NO DESTRUCTION)
    # =========================
    if "distance" in df.columns:
        df["distance_km"] = df["distance"] / 1000
    else:
        df["distance_km"] = range(len(df))

    # =========================
    # 4. KEEP RAW SENSOR DATA AS-IS
    # =========================
    # IMPORTANT: do NOT coerce everything globally

    for col in ["power", "altitude", "speed"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # =========================
    # 5. MAP (UNCHANGED)
    # =========================
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

    # =========================
    # 6. CHARTS (NOW SAFE)
    # =========================
    st.subheader("📊 Elevation & Power")

    fig, ax1 = plt.subplots()

    plotted = False

    if "altitude" in df.columns and df["altitude"].notna().any():
        ax1.plot(df["distance_km"], df["altitude"], label="Altitude")
        plotted = True

    if "power" in df.columns and df["power"].notna().any():
        ax2 = ax1.twinx()
        ax2.plot(df["distance_km"], df["power"], color="orange", label="Power")
        plotted = True

    if plotted:
        st.pyplot(fig)
    else:
        st.warning("No usable altitude or power data detected")

    # =========================
    # 7. SUMMARY (SAFE)
    # =========================
    st.subheader("Summary")

    col1, col2 = st.columns(2)

    col1.metric(
        "Distance (km)",
        f"{df['distance_km'].max():.1f}"
    )

    if "power" in df.columns and df["power"].notna().any():
        col2.metric("Max Power", f"{df['power'].max():.0f} W")
    else:
        col2.metric("Max Power", "N/A")
