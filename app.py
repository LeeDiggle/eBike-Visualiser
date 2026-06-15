import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fitparse import FitFile
import numpy as np

st.title("🚴 E-Bike Ride Visualiser (Clean + Smoothed)")

uploaded_file = st.file_uploader("Upload your ride file")

if uploaded_file:

    # -----------------------
    # Load FIT file
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
    # Basic cleanup
    # -----------------------
    if "distance" not in df.columns:
        st.error("No distance data found")
        st.stop()

    df = df.sort_values("distance").drop_duplicates(subset=["distance"])
    df["distance_km"] = df["distance"] / 1000

    # Ensure numeric
    for col in ["altitude", "power", "speed"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Remove impossible power spikes (common FIT noise)
    if "power" in df.columns:
        df.loc[df["power"] <= 0, "power"] = np.nan
        df.loc[df["power"] > 1200, "power"] = np.nan  # sanity cap

    # -----------------------
    # Downsample for readability (key fix)
    # -----------------------
    df = df.iloc[::3].reset_index(drop=True)

    # -----------------------
    # Smoothing (critical for Bosch Flow data)
    # -----------------------
    if "altitude" in df.columns:
        df["altitude_smooth"] = df["altitude"].rolling(40, min_periods=1).median()

    if "power" in df.columns:
        df["power_smooth"] = df["power"].rolling(40, min_periods=1).median()

    # -----------------------
    # Gradient (stable version)
    # -----------------------
    df["distance_diff"] = df["distance"].diff()
    df["alt_diff"] = df["altitude_smooth"].diff() if "altitude_smooth" in df.columns else np.nan

    df["gradient"] = (df["alt_diff"] / df["distance_diff"]) * 100
    df["gradient"] = df["gradient"].replace([np.inf, -np.inf], np.nan)
    df["gradient"] = df["gradient"].clip(-12, 12)
    df["gradient"] = df["gradient"].rolling(20, min_periods=1).mean()

    # -----------------------
    # Column preview
    # -----------------------
    st.subheader("Available data columns")
    st.write(df.columns.tolist())

    # -----------------------
    # MAIN PLOT
    # -----------------------
    st.subheader("Elevation + Power (Smoothed)")

    fig, ax1 = plt.subplots(figsize=(12, 5))

    if "altitude_smooth" in df.columns:
        ax1.plot(df["distance_km"], df["altitude_smooth"], linewidth=2, label="Elevation")

    ax1.set_xlabel("Distance (km)")
    ax1.set_ylabel("Altitude (m)")

    if "power_smooth" in df.columns:
        ax2 = ax1.twinx()
        ax2.plot(df["distance_km"], df["power_smooth"], color="orange", alpha=0.7, label="Power")
        ax2.set_ylabel("Power (W)")

    st.pyplot(fig, use_container_width=True)

    # -----------------------
    # Gradient plot
    # -----------------------
    st.subheader("Gradient Profile (Cleaned)")

    fig2, ax = plt.subplots(figsize=(12, 3))
    ax.plot(df["distance_km"], df["gradient"])
    ax.set_xlabel("Distance (km)")
    ax.set_ylabel("Gradient (%)")

    st.pyplot(fig2, use_container_width=True)

    # -----------------------
    # Summary
    # -----------------------
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

# -----------------------
# MAP (ISOLATED ADD-ON)
# -----------------------
if "position_lat" in df.columns and "position_long" in df.columns:

    import plotly.graph_objects as go

    map_df = df[["position_lat", "position_long"]].copy()
    map_df["lat"] = pd.to_numeric(map_df["position_lat"], errors="coerce")
    map_df["lon"] = pd.to_numeric(map_df["position_long"], errors="coerce")

    map_df = map_df.dropna()

    st.subheader("Route Map")

    fig_map = go.Figure()

    fig_map.add_trace(go.Scattermapbox(
        lat=map_df["lat"].tolist(),
        lon=map_df["lon"].tolist(),
        mode="lines",
        line=dict(width=3, color="blue")
    ))

    fig_map.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(
                lat=float(map_df["lat"].iloc[0]),
                lon=float(map_df["lon"].iloc[0])
            ),
            zoom=12
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=500
    )

    st.plotly_chart(fig_map, use_container_width=True)
