import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fitparse import FitFile

st.title("🚴 eBike Ride Dashboard")

uploaded_file = st.file_uploader("Upload your FIT file", type=["fit"])

if uploaded_file:
    fitfile = FitFile(uploaded_file)

    data = []

    for record in fitfile.get_messages("record"):
        row = {}
        for field in record:
            row[field.name] = field.value
        data.append(row)

    df = pd.DataFrame(data)

    st.write("Raw data preview:")
    st.write(df.head())

    # Basic cleaning
    df = df.dropna(subset=["heart_rate", "altitude", "distance"])

    df['elevation_diff'] = df['altitude'].diff()
    df['distance_diff'] = df['distance'].diff()
    df['gradient'] = (df['elevation_diff'] / df['distance_diff']) * 100

    # Plot 1: Heart Rate over time
    st.subheader("❤️ Heart Rate Over Time")
    fig1, ax1 = plt.subplots()
    ax1.plot(df['timestamp'], df['heart_rate'])
    st.pyplot(fig1)

    # Plot 2: Gradient over time
    st.subheader("⛰️ Gradient Over Time")
    fig2, ax2 = plt.subplots()
    ax2.plot(df['timestamp'], df['gradient'])
    st.pyplot(fig2)

    # Plot 3: HR vs Gradient
    st.subheader("📊 Effort vs Gradient")
    fig3, ax3 = plt.subplots()
    ax3.scatter(df['gradient'], df['heart_rate'])
    ax3.set_xlabel("Gradient (%)")
    ax3.set_ylabel("Heart Rate")
    st.pyplot(fig3)
