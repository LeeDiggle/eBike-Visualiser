import streamlit as st
import pandas as pd
from fitparse import FitFile
import plotly.graph_objects as go

st.title("🚴 E-Bike FIT Viewer (Clean Base)")

uploaded_file = st.file_uploader("Upload FIT file")

if uploaded_file:

    fitfile = FitFile(uploaded_file)

    data = []
    for record in fitfile.get_messages("record"):
        row = {}
        for field in record:
            row[field.name] = field.value
        data.append(row)

    df = pd.DataFrame(data)

    st.subheader("Data preview")
    st.write(df.head())

    # -------------------------
    # GPS CLEAN ONLY
    # -------------------------
    df = df.dropna(subset=["position_lat", "position_long"])

    lat = pd.to_numeric(df["position_lat"], errors="coerce")
    lon = pd.to_numeric(df["position_long"], errors="coerce")

    mask = lat.notna() & lon.notna()

    lat = lat[mask]
    lon = lon[mask]

    st.write("GPS points:", len(lat))

    # -------------------------
    # MAP ONLY (NO CHARTS YET)
    # -------------------------
    fig = go.Figure()

    fig.add_trace(go.Scattermapbox(
        lat=lat.tolist(),
        lon=lon.tolist(),
        mode="lines",
        line=dict(width=4, color="blue")
    ))

    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=float(lat.mean()), lon=float(lon.mean())),
            zoom=12
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)
