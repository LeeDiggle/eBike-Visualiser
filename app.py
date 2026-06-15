import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fitparse import FitFile
import numpy as np

import folium
from streamlit_folium import st_folium

st.title("🚴 E-Bike Ride Visualiser (Stable Final Version)")

uploaded_file = st.file_uploader("Upload your ride file")

if uploaded_file:

    # =======================
    # LOAD FIT FILE
    # =======================
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

    # =======================
    # VALIDATION
    # =======================
    if "distance" not in df.columns:
        st.error("No distance data found")
        st.stop()

    df = df.sort_values("distance").reset_index(drop=True)
    df["distance_km"] = df["distance"] / 1000

    # =======================
    # CLEAN NUMERIC DATA
    # =======================
    for col in ["altitude", "power", "speed"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Power cleanup
    if "power" in df.columns:
        df.loc[df["power"] <= 0, "power"] = np.nan
        df.loc[df["power"] > 1200, "power"] = np.nan

    # =======================
    # DOWN SAMPLE (charts only)
    # =======================
    df = df.iloc[::3].reset_index(drop=True)

    # =======================
    # SMOOTHING
    # =======================
    if "altitude" in df.columns:
        df["altitude_smooth"] = df["altitude"].rolling(40, min_periods=1).median()

    if "power" in df.columns:
        df["power_smooth"] = df["power"].rolling(40, min_periods=1).median()

    # =======================
    # GRADIENT
    # =======================
    df["distance_diff"] = df["distance"].diff()

    if "altitude_smooth" in df.columns:
        df["alt_diff"] = df["altitude_smooth"].diff()
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
        ax1.plot(df["distance_km"], df["altitude_smooth"], label="Elevation")

    ax1.set_xlabel("Distance (km)")
    ax1.set_ylabel("Altitude (m)")

    if "power_smooth" in df.columns:
        ax2 = ax1.twinx()
        ax2.plot(df["distance_km"], df["power_smooth"], color="orange")
        ax2.set_ylabel("Power (W)")

    st.pyplot(fig)

    # =======================
    # GRADIENT
    # =======================
    st.subheader("Gradient")

    fig2, ax = plt.subplots(figsize=(12, 3))
    ax.plot(df["distance_km"], df["gradient"])
    ax.set_xlabel("Distance (km)")
    ax.set_ylabel("Gradient %")

    st.pyplot(fig2)

    # =======================
    # GPS MAP (FULLY FIXED)
    # =======================
    st.subheader("Route Map")

    gps_df = pd.DataFrame(data)

    if "position_lat" in gps_df.columns and "position_long" in gps_df.columns:

        gps_df["lat"] = pd.to_numeric(gps_df["position_lat"], errors="coerce")
        gps_df["lon"] = pd.to_numeric(gps_df["position_long"], errors="coerce")

        # IMPORTANT: clean + ORDER correctly
        if "timestamp" in gps_df.columns:
            gps_df = gps_df.sort_values("timestamp")

        gps_df = gps_df.dropna(subset=["lat", "lon"]).reset_index(drop=True)

        st.write("GPS points:", len(gps_df))

        if len(gps_df) > 1:

            center_lat = gps_df["lat"].iloc[0]
            center_lon = gps_df["lon"].iloc[0]

            m = folium.Map(location=[center_lat, center_lon], zoom_start=13)

            folium.PolyLine(
                list(zip(gps_df["lat"], gps_df["lon"])),
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
    st.subheader("Ride Summary")

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
