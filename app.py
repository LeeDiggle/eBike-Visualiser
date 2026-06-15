import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fitparse import FitFile
import plotly.graph_objects as go

st.title("🚴 E-Bike Ride Intelligence Dashboard")

uploaded_file = st.file_uploader("Upload your FIT file")

if uploaded_file:

    # -------------------------
    # Load FIT file
    # -------------------------
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

    # -------------------------
    # Validate GPS
    # -------------------------
    required_cols = ["position_lat", "position_long", "distance"]

    for col in required_cols:
        if col not in df.columns:
            st.error(f"Missing required column: {col}")
            st.stop()

    # -------------------------
    # Clean data
    # -------------------------
    df = df.dropna(subset=["position_lat", "position_long", "distance"])
    df = df.sort_values("distance").reset_index(drop=True)

    # Convert coordinates (FIT format → degrees)
    df["lat"] = df["position_lat"] * (180 / 2**31)
    df["lon"] = df["position_long"] * (180 / 2**31)

    df["distance_km"] = df["distance"] / 1000

    # Numeric cleanup
    for col in ["speed", "power", "altitude"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # -------------------------
    # Smoothing (critical for readability)
    # -------------------------
    if "altitude" in df.columns:
        df["alt_smooth"] = df["altitude"].rolling(30, min_periods=1).median()

    if "power" in df.columns:
        df["power_smooth"] = df["power"].rolling(30, min_periods=1).median()

    if "speed" in df.columns:
        df["speed_smooth"] = df["speed"].rolling(30, min_periods=1).median()

    # -------------------------
    # Gradient
    # -------------------------
    df["gradient"] = (
        df["alt_smooth"].diff() / df["distance"].diff()
    ) * 100

    df["gradient"] = df["gradient"].replace([np.inf, -np.inf], np.nan)
    df["gradient"] = df["gradient"].clip(-12, 12)
    df["gradient"] = df["gradient"].rolling(15, min_periods=1).mean()

    # -------------------------
    # SIDEBAR INFO
    # -------------------------
    st.sidebar.subheader("Ride Summary")
    st.sidebar.metric("Distance (km)", f"{df['distance_km'].max():.1f}")
    st.sidebar.metric("Max Speed", f"{df['speed'].max():.1f}" if "speed" in df.columns else "N/A")
    st.sidebar.metric("Max Power", f"{df['power'].max():.0f}" if "power" in df.columns else "N/A")

    # -------------------------
    # MAP (MAIN FEATURE)
    # -------------------------
    st.subheader("🗺️ Ride Map")

    color_metric = "speed_smooth" if "speed_smooth" in df.columns else "alt_smooth"

    fig_map = go.Figure()

    fig_map.add_trace(go.Scattermapbox(
        lat=df["lat"],
        lon=df["lon"],
        mode="lines",
        line=dict(width=4, color="blue"),
        name="Route"
    ))

    fig_map.add_trace(go.Scattermapbox(
        lat=df["lat"],
        lon=df["lon"],
        mode="markers",
        marker=dict(
            size=6,
            color=df[color_metric],
            colorscale="Turbo",
            showscale=True,
            colorbar=dict(title=color_metric)
        ),
        text=[
            f"Speed: {s:.1f} | Power: {p:.0f} | Grad: {g:.1f}"
            for s, p, g in zip(
                df["speed"] if "speed" in df.columns else [0]*len(df),
                df["power"] if "power" in df.columns else [0]*len(df),
                df["gradient"]
            )
        ],
        hoverinfo="text"
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
    # ELEVATION + POWER
    # -------------------------
    st.subheader("📈 Elevation vs Power")

    fig1 = go.Figure()

    fig1.add_trace(go.Scatter(
        x=df["distance_km"],
        y=df["alt_smooth"],
        name="Elevation",
        line=dict(width=2)
    ))

    if "power_smooth" in df.columns:
        fig1.add_trace(go.Scatter(
            x=df["distance_km"],
            y=df["power_smooth"],
            name="Power",
            yaxis="y2",
            opacity=0.6
        ))

    fig1.update_layout(
        yaxis=dict(title="Altitude (m)"),
        yaxis2=dict(title="Power (W)", overlaying="y", side="right"),
        xaxis=dict(title="Distance (km)")
    )

    st.plotly_chart(fig1, use_container_width=True)

    # -------------------------
    # GRADIENT
    # -------------------------
    st.subheader("⛰️ Gradient Profile")

    fig2 = go.Figure()

    fig2.add_trace(go.Scatter(
        x=df["distance_km"],
        y=df["gradient"],
        name="Gradient"
    ))

    fig2.update_layout(
        xaxis_title="Distance (km)",
        yaxis_title="Gradient (%)"
    )

    st.plotly_chart(fig2, use_container_width=True)
