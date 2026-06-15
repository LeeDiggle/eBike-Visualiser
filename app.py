import streamlit as st
import pandas as pd
import numpy as np
from fitparse import FitFile
import plotly.graph_objects as go
import matplotlib.pyplot as plt

st.title("🚴 FIT Dashboard (Recovered)")

uploaded_file = st.file_uploader("Upload FIT file")

if uploaded_file:

    fitfile = FitFile(uploaded_file)

    # =========================
    # 1. RECORD DATA (TRUTH LAYER)
    # =========================
    records = []
    for r in fitfile.get_messages("record"):
        row = {}
        for f in r:
            row[f.name] = f.value
        records.append(row)

    df = pd.DataFrame(records)

    st.write("Record rows:", len(df))
    st.write("Columns:", df.columns.tolist())

    # =========================
    # 2. SESSION DATA (SAFE LAYER)
    # =========================
    session_data = {}
    try:
        session_msg = next(fitfile.get_messages("session"))
        for f in session_msg:
            session_data[f.name] = f.value
    except:
        pass

    # =========================
    # 3. ONLY CONTINUE IF RECORD EXISTS
    # =========================
    if df.empty:
        st.error("No record data found in FIT file")
        st.stop()

    # =========================
    # 4. GPS CLEAN (STRICT BUT SAFE)
    # =========================
    if "position_lat" in df.columns and "position_long" in df.columns:

        gps = df[["position_lat", "position_long"]].copy()

        gps["lat"] = pd.to_numeric(gps["position_lat"], errors="coerce")
        gps["lon"] = pd.to_numeric(gps["position_long"], errors="coerce")

        gps = gps.dropna(subset=["lat", "lon"]).reset_index(drop=True)

        st.write("GPS points:", len(gps))

        # MAP
        fig = go.Figure()

        fig.add_trace(go.Scattermapbox(
            lat=gps["lat"].tolist(),
            lon=gps["lon"].tolist(),
            mode="lines",
            line=dict(width=4, color="blue")
        ))

        fig.update_layout(
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

        st.subheader("🗺️ Route Map")
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("No GPS data in record stream")

    # =========================
    # 5. NUMERIC CLEAN (MINIMAL)
    # =========================
    for col in ["distance", "speed", "power", "altitude"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # =========================
    # 6. CHARTS (ONLY IF DATA EXISTS)
    # =========================
    st.subheader("📊 Charts")

    if "distance" in df.columns:

        df["distance_km"] = df["distance"] / 1000

        fig, ax1 = plt.subplots()

        if "altitude" in df.columns:
            ax1.plot(df["distance_km"], df["altitude"], label="Altitude")

        ax2 = ax1.twinx()

        if "power" in df.columns:
            ax2.plot(df["distance_km"], df["power"], color="orange", label="Power")

        st.pyplot(fig)

    # =========================
    # 7. SUMMARY (SESSION ONLY)
    # =========================
    st.subheader("Summary")

    col1, col2 = st.columns(2)

    if "total_distance" in session_data:
        col1.metric("Distance", f"{session_data['total_distance']/1000:.1f} km")
    else:
        col1.metric("Distance", "N/A")

    if "avg_power" in session_data:
        col2.metric("Avg Power", f"{session_data['avg_power']:.0f} W")
    else:
        col2.metric("Avg Power", "N/A")
