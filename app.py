import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fitparse import FitFile
import numpy as np

st.title("🚴 E-Bike Ride Visualiser (Tile-Free Stable Version)")

uploaded_file = st.file_uploader("Upload your ride file")

if uploaded_file:

    fitfile = FitFile(uploaded_file)

    data = []
    gps_points = []

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

        data.append(row)

        if lat is not None and lon is not None:
            gps_points.append((lat, lon))

    df = pd.DataFrame(data)

    if "distance" not in df.columns:
        st.error("No distance data found")
        st.stop()

    df = df.sort_values("distance").reset_index(drop=True)
    df["distance_km"] = df["distance"] / 1000

    for col in ["altitude", "power", "speed"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "power" in df.columns:
        df.loc[df["power"] <= 0, "power"] = np.nan
        df.loc[df["power"] > 1200, "power"] = np.nan

    df = df.iloc[::3].reset_index(drop=True)

    if "altitude" in df.columns:
        df["altitude_smooth"] = df["altitude"].rolling(40, min_periods=1).median()

    if "power" in df.columns:
        df["power_smooth"] = df["power"].rolling(40, min_periods=1).median()

    df["distance_diff"] = df["distance"].diff()
    df["alt_diff"] = df["altitude"].diff() if "altitude" in df.columns else np.nan

    df["gradient"] = (df["alt_diff"] / df["distance_diff"]) * 100
    df["gradient"] = df["gradient"].replace([np.inf, -np.inf], np.nan)
    df["gradient"] = df["gradient"].clip(-12, 12)

    # -----------------------
    # CHARTS
    # -----------------------
    st.subheader("Elevation + Power")

    fig, ax1 = plt.subplots(figsize=(12, 5))

    if "altitude_smooth" in df.columns:
        ax1.plot(df["distance_km"], df["altitude_smooth"])

    if "power_smooth" in df.columns:
        ax2 = ax1.twinx()
        ax2.plot(df["distance_km"], df["power_smooth"], color="orange")

    st.pyplot(fig)

    # -----------------------
    # GRADIENT
    # -----------------------
    st.subheader("Gradient")

    fig2, ax = plt.subplots(figsize=(12, 3))
    ax.plot(df["distance_km"], df["gradient"])
    st.pyplot(fig2)

    # -----------------------
    # STATIC MAP (NO TILES)
    # -----------------------
    st.subheader("Route Map (Stable Mode)")

    st.write("GPS points:", len(gps_points))

    if len(gps_points) > 1:

        import matplotlib.pyplot as plt

        lats = [p[0] for p in gps_points]
        lons = [p[1] for p in gps_points]

        fig, ax = plt.subplots(figsize=(6, 6))
        ax.plot(lons, lats, linewidth=2)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_title("Route Geometry (No Map Tiles)")

        st.pyplot(fig)

    # -----------------------
    # SUMMARY
    # -----------------------
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
