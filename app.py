import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fitparse import FitFile
import numpy as np
import pydeck as pdk

st.title("🚴 E-Bike Ride Visualiser (Stable + Map Fixed)")

uploaded_file = st.file_uploader("Upload your ride file")

if uploaded_file:

    # -----------------------
    # Load FIT file (records only)
    # -----------------------
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

    # -----------------------
    # Basic validation
    # -----------------------
    required_cols = ["distance"]
    if "distance" not in df.columns:
        st.error("No distance data found")
        st.stop()

    df = df.sort_values("distance").reset_index(drop=True)
    df["distance_km"] = df["distance"] / 1000

    # -----------------------
    # Numeric cleanup
    # -----------------------
    for col in ["altitude", "power", "speed"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # -----------------------
    # Power cleanup
    # -----------------------
    if "power" in df.columns:
        df.loc[df["power"] <= 0, "power"] = np.nan
        df.loc[df["power"] > 1200, "power"] = np.nan

    # -----------------------
    # Downsample (keeps charts readable)
    # -----------------------
    df = df.iloc[::3].reset_index(drop=True)

    # -----------------------
    # Smoothing
    # -----------------------
    if "altitude" in df.columns:
        df["altitude_smooth"] = df["altitude"].rolling(40, min_periods=1).median()

    if "power" in df.columns:
        df["power_smooth"] = df["power"].rolling(40, min_periods=1).median()

    # -----------------------
    # Gradient
    # -----------------------
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
        ax2.plot(df["distance_km"], df["power_smooth"], color="orange", label="Power")
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
    # GPS (REBUILT FROM RAW FIT STREAM)
    # =======================
    gps_data = []
    for record in fitfile.get_messages("record"):
        row = {}
        for field in record:
            row[field.name] = field.value
        gps_data.append(row)

    gps_df = pd.DataFrame(gps_data)

    if "position_lat" in gps_df.columns and "position_long" in gps_df.columns:

        gps_df["lat"] = pd.to_numeric(gps_df["position_lat"], errors="coerce")
        gps_df["lon"] = pd.to_numeric(gps_df["position_long"], errors="coerce")

        gps_df = gps_df.dropna(subset=["lat", "lon"]).reset_index(drop=True)

        st.subheader("Route Map")

        st.write("GPS points:", len(gps_df))

        if len(gps_df) > 1:

            layer = pdk.Layer(
                "PathLayer",
                data=[{
                    "path": list(zip(gps_df["lon"], gps_df["lat"]))
                }],
                get_path="path",
                get_width=3,
                get_color=[0, 0, 255],
            )

            view_state = pdk.ViewState(
                latitude=float(gps_df["lat"].iloc[0]),
                longitude=float(gps_df["lon"].iloc[0]),
                zoom=12
            )

            deck = pdk.Deck(
                layers=[layer],
                initial_view_state=view_state,
                map_style="light"
            )

            st.pydeck_chart(deck)

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
