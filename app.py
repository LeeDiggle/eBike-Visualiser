import streamlit as st
import pandas as pd
from fitparse import FitFile
import plotly.graph_objects as go

st.set_page_config(layout="wide")

st.title("E-Bike Ride Visualiser")

flow_file = st.file_uploader("Upload Bosch Flow FIT file", type=["fit"])
hr_file = st.file_uploader("Upload Strava/Garmin FIT file (Heart Rate)", type=["fit"])

def parse_fit(file, include_hr=False):
    fit = FitFile(file)
    data = []

    for record in fit.get_messages("record"):
        row = {}
        for field in record:
            row[field.name] = field.value

        data.append(row)

    df = pd.DataFrame(data)

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    if not include_hr and "heart_rate" in df.columns:
        df = df.drop(columns=["heart_rate"])

    return df

if flow_file:
    df_flow = parse_fit(flow_file)

    if hr_file:
        df_hr = parse_fit(hr_file, include_hr=True)

        df_hr = df_hr[["timestamp", "heart_rate"]].dropna()

        # 🔧 CRITICAL FIX: forward fill HR before merge
        df_hr = df_hr.sort_values("timestamp")
        df_hr["heart_rate"] = df_hr["heart_rate"].ffill()

        # Merge with tolerance
        df = pd.merge_asof(
            df_flow.sort_values("timestamp"),
            df_hr.sort_values("timestamp"),
            on="timestamp",
            direction="nearest",
            tolerance=pd.Timedelta("5s")
        )
    else:
        df = df_flow

    # Smooth HR slightly
    if "heart_rate" in df.columns:
        df["heart_rate"] = df["heart_rate"].rolling(5, min_periods=1).mean()

    fig = go.Figure()

    # --- Power ---
    if "power" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["timestamp"],
            y=df["power"],
            name="Power (W)",
            yaxis="y1",
            line=dict(width=2)
        ))

    # --- Speed ---
    if "speed" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["timestamp"],
            y=df["speed"] * 3.6,
            name="Speed (km/h)",
            yaxis="y2",
            line=dict(width=2, dash="dot")
        ))

    # --- Heart Rate ---
    if "heart_rate" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["timestamp"],
            y=df["heart_rate"],
            name="Heart Rate (bpm)",
            yaxis="y4",
            line=dict(width=2, color="red")
        ))

    # --- Altitude (FIXED) ---
    if "altitude" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["timestamp"],
            y=df["altitude"],
            name="Altitude (m)",
            yaxis="y3",
            mode="lines",
            line=dict(width=1.5, color="rgba(100,100,100,0.6)"),
            fill="tozeroy",
            fillcolor="rgba(150,150,150,0.2)"
        ))

    # --- Layout with 4 axes ---
    fig.update_layout(
        xaxis=dict(title="Time"),

        yaxis=dict(
            title="Power (W)",
            side="left"
        ),

        yaxis2=dict(
            title="Speed (km/h)",
            overlaying="y",
            side="right",
            position=1.0
        ),

        yaxis3=dict(
            title="Altitude (m)",
            overlaying="y",
            side="left",
            position=0.0,
            showgrid=False
        ),

        yaxis4=dict(
            title="Heart Rate (bpm)",
            overlaying="y",
            side="right",
            position=0.95
        ),

        legend=dict(orientation="h"),
        margin=dict(l=40, r=100, t=40, b=40)
    )

    st.plotly_chart(fig, use_container_width=True)
