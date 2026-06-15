import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fitparse import FitFile

st.title("🚴 E-Bike Ride Visualiser (Bosch Flow)")

uploaded_file = st.file_uploader("Upload your ride file")

if uploaded_file:

    # --- Read FIT file ---
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

    # --- Sort by distance (key for Bosch Flow data) ---
    if "distance" in df.columns:
        df = df.sort_values("distance")

        # Convert to km
        df["distance_km"] = df["distance"] / 1000

    # --- Show available columns ---
    st.subheader("Available data columns")
    st.write(df.columns.tolist())

    # --- Basic cleaning (safe) ---
    for col in ["altitude", "distance", "power"]:
        if col not in df.columns:
            df[col] = None

    df = df.dropna(subset=["distance", "altitude"])

    # --- Gradient calculation ---
    df["gradient"] = df["altitude"].diff() / df["distance"].diff() * 100
    df["gradient"] = df["gradient"].replace([float("inf"), -float("inf")], None)
    df["gradient"] = df["gradient"].clip(-20, 20)

    # --- Preview ---
    st.subheader("Data preview")
    st.dataframe(df[["distance_km", "altitude", "power", "gradient"]].head(20))

    # --- MAIN PLOT ---
    st.subheader("Elevation + Power vs Distance")

    fig, ax1 = plt.subplots()

    # Elevation
    ax1.plot(df["distance_km"], df["altitude"], label="Elevation")
    ax1.set_xlabel("Distance (km)")
    ax1.set_ylabel("Altitude (m)")

    # Power (if available)
    if df["power"].notna().any():
        ax2 = ax1.twinx()
        ax2.plot(df["distance_km"], df["power"], color="orange", label="Power")
        ax2.set_ylabel("Power (W)")

    st.pyplot(fig)

    # --- Extra insight plot ---
    st.subheader("Gradient profile")

    fig2, ax = plt.subplots()
    ax.plot(df["distance_km"], df["gradient"])
    ax.set_xlabel("Distance (km)")
    ax.set_ylabel("Gradient (%)")

    st.pyplot(fig2)

    # --- Summary stats ---
    st.subheader("Quick stats")

    col1, col2, col3 = st.columns(3)

    col1.metric("Max Power", f"{df['power'].max():.0f} W" if df["power"].notna().any() else "N/A")
    col2.metric("Max Gradient", f"{df['gradient'].max():.1f}%")
    col3.metric("Distance", f"{df['distance_km'].max():.1f} km")
