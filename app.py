import streamlit as st
import pandas as pd
import numpy as np
from fitparse import FitFile
import plotly.graph_objects as go
import matplotlib.pyplot as plt

st.title("🚴 E-Bike Ride Dashboard (Stable Build)")

uploaded_file = st.file_uploader("Upload FIT file")

if uploaded_file:

    # =========================
    # 1. READ FIT FILE (RECORD ONLY)
    # =========================
    fitfile = FitFile(uploaded_file)

    data = []
    for record in fitfile.get_messages("record"):
        row = {}
        for field in record:
            row[field.name] = field.value
        data.append(row)

    df = pd.DataFrame(data)

    st.subheader("Data check")
    st.write("Rows:", len(df))
    st.write("Columns:", df.columns.tolist())

    # =========================
    # 2. CLEAN GPS (CRITICAL — NO SPLIT MASKS)
    # =========================
    gps = df[["position_lat", "position_long"]].copy()

    gps["lat"] = pd.to_numeric(gps["position_lat"], errors="coerce")
    gps["lon"] = pd.to_numeric(gps["position_long"], errors="coerce")

    gps = gps.dropna(subset=["lat", "lon"]).reset_index(drop=True)

    st.write("GPS points used:", len(gps))

    # =========================
    # 3. NUMERIC CLEANING (SAFE ONLY)
    # =========================
    for col in ["distance", "speed", "power", "altitude"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # =========================
    # 4. DISTANCE
    # =========================
    if "distance" in df.columns:
        df["distance_km"] = df["distance"] / 1000
    else:
        df["distance_km"] = np.arange(len(df))

    # =========================
    # 5. MAP (FULL ROUTE)
    # =========================
    st.subheader("🗺️ Route Map")

    fig_map = go.Figure()

    fig_map.add_trace(go.Scattermapbox(
        lat=gps["lat"].tolist(),
        lon=gps["lon"].tolist(),
        mode="lines",
        line=dict(width=4, color="blue")
    ))

    fig_map.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(
                lat=float(gps["lat"].iloc[0]),
                lon=float(gps["lon"].iloc[0])
            ),
            zoom=12
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=600
    )

    st.plotly_chart(fig_map, use_container_width=True)

    # =========================
    # 6. CHARTS (ALTITUDE + POWER)
    # =========================
    st.subheader("📊 Elevation & Power")

    fig, ax1 = plt.subplots()

    if "altitude" in df.columns:
        alt = df["altitude"].rolling(10, min_periods=1).median()
        ax1.plot(df["distance_km"], alt, label="Altitude")

    ax2 = ax1.twinx()

    if "power" in df.columns:
        powr = df["power"].rolling(10, min_periods=1).median()
        ax2.plot(df["distance_km"], powr, color="orange", label="Power")

    st.pyplot(fig)

    # =========================
    # 7. SUMMARY (SESSION DATA)
    # =========================
    st.subheader("Summary")

    session = {}
    try:
        for field in fitfile.get_messages("session").__next__():
            session[field.name] = field.value
    except:
        pass

    col1, col2 = st.columns(2)

    col1.metric(
        "Distance (km)",
        f"{df['distance_km'].max():.1f}" if "distance_km" in df else "N/A"
    )

    if "avg_power" in session:
        col2.metric("Avg Power", f"{session['avg_power']:.0f} W")
    else:
        col2.metric("Avg Power", "N/A")
