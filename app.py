import streamlit as st
import pandas as pd
from fitparse import FitFile
import plotly.graph_objects as go

st.title("🚴 FIT Ride Viewer (Clean Rebuild)")

uploaded_file = st.file_uploader("Upload FIT file")

if uploaded_file:

    fitfile = FitFile(uploaded_file)

    # -------------------------
    # RAW RECORD EXTRACTION
    # -------------------------
    data = []
    for record in fitfile.get_messages("record"):
        row = {}
        for field in record:
            row[field.name] = field.value
        data.append(row)

    df = pd.DataFrame(data)

    st.subheader("Data sanity check")
    st.write("Rows:", len(df))
    st.write("Columns:", df.columns.tolist())

    # -------------------------
    # CLEAN GPS (NO GUESSING)
    # -------------------------
    df = df.dropna(subset=["position_lat", "position_long"])

    lat = pd.to_numeric(df["position_lat"], errors="coerce")
    lon = pd.to_numeric(df["position_long"], errors="coerce")

    mask = lat.notna() & lon.notna()

    lat = lat[mask]
    lon = lon[mask]

    st.write("GPS points:", len(lat))

    # -------------------------
    # MAP (MINIMAL, ROBUST)
    # -------------------------
    fig = go.Figure()

    fig.add_trace(go.Scattermapbox(
        lat=lat.tolist(),
        lon=lon.tolist(),
        mode="lines"
    ))

    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(
                lat=float(lat.mean()),
                lon=float(lon.mean())
            ),
            zoom=12
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)
