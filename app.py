import streamlit as st
import plotly.graph_objects as go

st.title("Map Isolation Test")

# fake route (Bristol-ish coordinates)
lat = [51.4591, 51.4592, 51.4593, 51.4594, 51.4595]
lon = [-2.593, -2.592, -2.591, -2.590, -2.589]

fig = go.Figure()

fig.add_trace(go.Scattermapbox(
    lat=lat,
    lon=lon,
    mode="lines",
    line=dict(width=4, color="blue")
))

fig.update_layout(
    mapbox=dict(
        style="open-street-map",
        center=dict(lat=51.4593, lon=-2.5915),
        zoom=13
    ),
    margin=dict(l=0, r=0, t=0, b=0),
    height=600
)

st.plotly_chart(fig, use_container_width=True)
