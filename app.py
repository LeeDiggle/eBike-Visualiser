import streamlit as st
from fitparse import FitFile
import pandas as pd

st.title("🔍 FIT Raw Data Inspector")

uploaded_file = st.file_uploader("Upload FIT file")

if uploaded_file:

    fitfile = FitFile(uploaded_file)

    message_types = {}

    # -------------------------
    # COLLECT ALL MESSAGE TYPES
    # -------------------------
    for msg in fitfile:
        name = msg.name

        if name not in message_types:
            message_types[name] = []

        row = {}
        for field in msg:
            row[field.name] = field.value

        message_types[name].append(row)

    # -------------------------
    # SHOW WHAT EXISTS
    # -------------------------
    st.subheader("Message types in FIT file")
    st.write(list(message_types.keys()))

    # -------------------------
    # SHOW RECORD SAMPLE
    # -------------------------
    if "record" in message_types:
        st.subheader("Record sample")
        df_record = pd.DataFrame(message_types["record"])
        st.write(df_record.head(20))
        st.write("Columns:", df_record.columns.tolist())

    # -------------------------
    # SHOW SESSION SAMPLE (IMPORTANT)
    # -------------------------
    if "session" in message_types:
        st.subheader("Session sample")
        df_session = pd.DataFrame(message_types["session"])
        st.write(df_session.head(10))
        st.write("Columns:", df_session.columns.tolist())

    # -------------------------
    # SHOW LAP SAMPLE
    # -------------------------
    if "lap" in message_types:
        st.subheader("Lap sample")
        df_lap = pd.DataFrame(message_types["lap"])
        st.write(df_lap.head(10))
        st.write("Columns:", df_lap.columns.tolist())
