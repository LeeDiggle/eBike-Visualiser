import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fitparse import FitFile
import plotly.graph_objects as go

st.title("🚴 E-Bike Debug Dashboard (FIT Inspector)")

uploaded_file = st.file_uploader("Upload FIT file")

if uploaded_file:

    fitfile = FitFile(uploaded_file)

    raw_records = []
    all_fields = set()

    # -------------------------
    # RAW EXTRACTION (NO FILTERING)
    # -------------------------
    for record in fitfile.get_messages("record"):
        row = {}

        for field in record:
            row[field.name] = field.value
            all_fields.add(field.name)

        raw_records.append(row)

    df = pd.DataFrame(raw_records)

    st.subheader("ALL AVAILABLE FIT FIELDS")
    st.write(sorted(list(all_fields)))

    st.subheader("Raw Data Sample")
    st.dataframe(df.head(20))

    # -------------------------
    # TRY ALL POSSIBLE GPS FIELD NAMES
    # -------------------------
    gps_lat_candidates = [
        "position_lat",
        "position_latitude",
        "enhanced_position_lat",
        "lat"
    ]

    gps_lon_candidates = [
        "position_long",
        "position_longitude",
        "enhanced_position_long",
        "lon"
    ]

    lat_col = next((c for c in gps_lat_candidates if c in df.columns), None)
    lon_col = next((c for c in gps_lon_candidates if c in df.columns), None)

    if not lat_col or not lon_col:
        st.error("No GPS columns found in FIT file")
        st.stop()

    st.success(f"Using GPS columns: {lat_col} / {lon_col}")

    df = df.dropna(subset=[lat_col, lon_col])

    # -------------------------
    # GPS decode (only if needed)
    # -------------------------
    if df[lat_col].abs().max() > 180:
        df["lat"] = df[lat_col] * (180 / 2**31)
        df["lon"] = df[lon_col] * (180 / 2**31)
    else:
        df["lat"] = df[lat_col]
        df["lon"] = df[lon_col]

    # -------------------------
    # Distance
    # -------------------------
    if "distance" in df.columns:
        df["distance_km"] = pd.to_numeric(df["distance"], errors="coerce") / 1000
    else:
        df["distance_km"] = range(len(df))

    # -------------------------
    # Clean numeric fields safely
    # -------------------------
    for col in ["speed", "power", "altitude"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # -------------------------
    # MAP
    # -------------------------
    st.subheader("🗺️ Ride Map")

    fig_map = go.Figure()

    fig_map.add_trace(go.Scattermapbox(
        lat=df["lat"],
        lon=df["lon"],
        mode="lines",
        line=dict(width=4, color="blue")
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
