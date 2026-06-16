import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fitparse import FitFile
import numpy as np
import folium
from streamlit_folium import st_folium

st.title("🚴 E-Bike Ride Visualiser")

uploaded_file = st.file_uploader("Upload your ride file")

if uploaded_file:

    fitfile = FitFile(uploaded_file)

    records = []
    gps_points = []

    # =======================
    # EXTRACT DATA
    # =======================
    for record in fitfile.get_messages("record"):

        row = {}
        lat = None
        lon = None

        for field in record:
            row[field.name] = field.value

            if field.name == "position_lat":
                lat = field.value
            if field.name == "position_long":
                lon = field.value

        records.append(row)

        # ONLY store valid paired GPS points
        if lat is not None and lon is not None:
            gps_points.append((lat, lon))

    df = pd.DataFrame(records)

    if "distance" not in df.columns:
        st.error("No distance data found")
        st.stop()

    # =======================
    # CLEAN DATA
    # =======================
    df = df.sort_values("distance").reset_index(drop=True)
    df["distance_km"] = df["distance"] / 1000

    for col in ["altitude", "power", "speed"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # clean power
    if "power" in df.columns:
        df.loc[df["power"] <= 0, "power"] = np.nan
        df.loc[df["power"] > 1200, "power"] = np.nan

    # downsample (charts only)
    df = df.iloc[::3].reset_index(drop=True)

    # smoothing
    if "altitude" in df.columns:
        df["altitude_smooth"] = df["altitude"].rolling(40, min_periods=1).median()

    if "power" in df.columns:
        df["power_smooth"] = df["power"].rolling(40, min_periods=1).median()

    # gradient
    df["distance_diff"] = df["distance"].diff()

    if "altitude" in df.columns:
        df["alt_diff"] = df["altitude"].diff()
    else:
        df["alt_diff"] = np.nan

    df["gradient"] = (df["alt_diff"] / df["distance_diff"]) * 100
    df["gradient"] = df["gradient"].replace([np.inf, -np.inf], np.nan)
    df["gradient"] = df["gradient"].clip(-12, 12)
    df["gradient"] = df["gradient"].rolling(20, min_periods=1).mean()

    # =======================
    # CHARTS
    # =======================
    st.subheader("Elevation + Power")

    fig, ax1 = plt.subplots(figsize=(12, 5))

    if "altitude_smooth" in df.columns:
        ax1.plot(df["distance_km"], df["altitude_smooth"])

    if "power_smooth" in df.columns:
        ax2 = ax1.twinx()
        ax2.plot(df["distance_km"], df["power_smooth"], color="orange")

    ax1.set_xlabel("Distance (km)")
    ax1.set_ylabel("Altitude (m)")

    st.pyplot(fig)

    # =======================
    # GRADIENT
    # =======================
    st.subheader("Gradient")

    fig2, ax = plt.subplots(figsize=(12, 3))
    ax.plot(df["distance_km"], df["gradient"])
    ax.set_xlabel("Distance (km)")
    ax.set_ylabel("Gradient (%)")

    st.pyplot(fig2)

    # =======================
    # MAP (CARTODB TILE FIX)
    # =======================
    st.subheader("Route Map")

    st.write("GPS points:", len(gps_points))

    if len(gps_points) > 1:

        lat_lon = [(float(lat), float(lon)) for lat, lon in gps_points]

        center_lat = lat_lon[0][0]
        center_lon = lat_lon[0][1]

        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=13,
            tiles="CartoDB positron"
        )

        folium.PolyLine(
            lat_lon,
            color="blue",
            weight=4,
            opacity=0.8
        ).add_to(m)

        st_folium(m, width=700, height=500)

    else:
        st.warning("Not enough GPS data")

    # =======================
    # SUMMARY
    # =======================
    st.subheader("Summary")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Max Power",
        f"{np.nanmax(df['power']):.0f} W" if "power" in df.columns else "N/A"
    )

    col2.metric(
        "Max Gradient",
        f"{np.nanmax(df['gradient']):.1f}%"
    )

    col3.metric(
        "Distance",
        f"{df['distance_km'].max():.1f} km"
    )
