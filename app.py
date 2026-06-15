import streamlit as st
import pandas as pd
from fitparse import FitFile
import plotly.graph_objects as go

st.title("FIT Debug - Truth Check")

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

    st.subheader("1. Raw column check")
    st.write(df.columns.tolist())

    st.subheader("2. Power / Altitude raw stats")
    cols = ["power", "altitude", "speed", "distance"]

    for c in cols:
        if c in df.columns:
            st.write(c, "non-null count:", df[c].notna().sum())
            st.write(c, "sample:", df[c].dropna().head(10).tolist())
        else:
            st.write(c, "MISSING")

    st.subheader("3. GPS check")

    if "position_lat" in df.columns and "position_long" in df.columns:
        st.write("GPS present:", True)

        df = df.dropna(subset=["position_lat", "position_long"])

        lat = df["position_lat"] * (180 / 2**31)
        lon = df["position_long"] * (180 / 2**31)

        st.write("lat sample:", lat.head(10).tolist())
        st.write("lon sample:", lon.head(10).tolist())

        st.subheader("MAP")

        fig = go.Figure()
        fig.add_trace(go.Scattermapbox(
            lat=lat,
            lon=lon,
            mode="lines"
        ))

        fig.update_layout(
            mapbox=dict(
                style="open-street-map",
                center=dict(lat=lat.mean(), lon=lon.mean()),
                zoom=12
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            height=600
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.error("No GPS found")
