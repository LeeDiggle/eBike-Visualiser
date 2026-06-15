import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fitparse import FitFile

st.title("🚴 E-Bike Ride Visualiser")

uploaded_file = st.file_uploader("Upload your ride file")

if uploaded_file:
    fitfile = FitFile(uploaded_file)

    data = []

    for record in fitfile.get_messages("record"):
        row = {}
        for field in record:
            row[field.name] = field.value
        data.append(row)

    if not data:
        st.error("No data found in file")
    else:
        df = pd.DataFrame(data)

        # Show available columns (VERY useful for debugging)
        st.write("Available data columns:", df.columns.tolist())

        # Drop NA only for columns that exist
        relevant_cols = [c for c in ["heart_rate", "altitude", "distance", "speed"] if c in df.columns]
        if relevant_cols:
            df = df.dropna(subset=relevant_cols)

        st.write("Preview of your data:")
        st.dataframe(df.head())

        # --- Plot ---
        if 'timestamp' in df.columns:
            fig, ax1 = plt.subplots()

            # Primary axis: HR or Speed
            if 'heart_rate' in df.columns:
                ax1.plot(df['timestamp'], df['heart_rate'])
                ax1.set_ylabel('Heart Rate')
            elif 'speed' in df.columns:
                ax1.plot(df['timestamp'], df['speed'])
                ax1.set_ylabel('Speed')

            # Secondary axis: Altitude
            if 'altitude' in df.columns:
                ax2 = ax1.twinx()
                ax2.plot(df['timestamp'], df['altitude'])
                ax2.set_ylabel('Altitude')

            ax1.set_xlabel("Time")
            st.pyplot(fig)
        else:
            st.warning("No timestamp data available for plotting")
