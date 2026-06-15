import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fitparse import FitFile

st.title("🚴 E-Bike Ride Visualiser (Clean View)")

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
    # Sort + prepare distance
    # -----------------------
    if "distance" in df.columns:
        df = df.sort_values("distance")
        df["distance_km"] = df["distance"] / 1000
    else:
        st.error("No distance data found")
        st.stop()

    # -----------------------
    # Show available columns
    # -----------------------
    st.subheader("Available data columns")
    st.write(df.columns.tolist())

    # -----------------------
    # Safe defaults
    # -----------------------
    for col in ["altitude", "power"]:
        if col not in df.columns:
            df[col] = None

    # Keep valid rows
    df = df.dropna(subset=["distance", "altitude"])

    # -----------------------
    # Smooth data (IMPORTANT for readability)
    # -----------------------
    df["altitude_smooth"] = df["altitude"].rolling(15, min_periods=1).mean()
    df["power_smooth"] = df["power"].rolling(15, min_periods=1).mean()

    # -----------------------
    # Gradient calculation
    # -----------------------
    df["gradient"] = df["altitude_smooth"].diff() / df["distance"].diff() * 100
    df["gradient"] = df["gradient"].replace([float("inf"), -float("inf")], None)
    df["gradient"] = df["gradient"].clip(-15, 15)

    # -----------------------
    # Preview table
    # -----------------------
    st.subheader("Data preview")
    st.dataframe(df[["distance_km", "altitude_smooth", "power_smooth", "gradient"]].head(20))

    # -----------------------
    # MAIN CHART: Elevation + Power
    # -----------------------
    st.subheader("Elevation + Power vs Distance")

    fig, ax1 = plt.subplots(figsize=(12, 5))

    ax1.plot(df["distance_km"], df["altitude_smooth"], label="Elevation", linewidth=2)
    ax1.set_xlabel("Distance (km)")
    ax1.set_ylabel("Altitude (m)")

    if df["power"].notna().any():
        ax2 = ax1.twinx()
        ax2.plot(df["distance_km"], df["power_smooth"], color="orange", alpha=0.7, label="Power")
        ax2.set_ylabel("Power (W)")

    st.pyplot(fig, use_container_width=True)

    # -----------------------
    # Gradient chart
    # -----------------------
    st.subheader("Gradient Profile")

    fig2, ax = plt.subplots(figsize=(12, 3))
    ax.plot(df["distance_km"], df["gradient"])
    ax.set_xlabel("Distance (km)")
    ax.set_ylabel("Gradient (%)")

    st.pyplot(fig2, use_container_width=True)

    # -----------------------
    # Summary stats
    # -----------------------
    st.subheader("Ride Summary")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Max Power",
        f"{df['power'].max():.0f} W" if df["power"].notna().any() else "N/A"
    )

    col2.metric(
        "Max Gradient",
        f"{df['gradient'].max():.1f}%"
    )

    col3.metric(
        "Distance",
        f"{df['distance_km'].max():.1f} km"
    )
