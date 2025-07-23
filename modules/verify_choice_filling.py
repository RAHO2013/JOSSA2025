import streamlit as st
import pandas as pd
import os

@st.cache_data
def load_excel(path):
    return pd.read_excel(path, sheet_name=0, dtype=str)

def display_verify_choice_filling():
    st.title("🎯 Student Choice Filling Verifier")

    # Upload student Excel
    uploaded_file = st.file_uploader("📥 Upload Student Choice Excel", type=["xlsx"])
    if not uploaded_file:
        st.info("Please upload a student's choice filled Excel file.")
        return

    # Load master file
    master_path = os.path.join("data", "MASTER EXCEL.xlsx")
    if not os.path.exists(master_path):
        st.error("❌ MASTER EXCEL.xlsx not found in the 'data/' folder.")
        return

    try:
        # Load and preprocess student file
        student_df = pd.read_excel(uploaded_file, sheet_name=0, dtype=str)
        student_df = student_df.rename(columns={
            'Unnamed: 0': 'College Code',
            'Unnamed: 2': 'COURSE CODE',
            'Institute': 'Institute',
            'Program': 'Program',
            'Choice No.': 'Choice Number'
        })

        student_df['Main_Code'] = student_df['College Code'].str.strip() + "_" + student_df['COURSE CODE'].str.strip()
        student_df['Choice Number'] = pd.to_numeric(student_df['Choice Number'], errors='coerce')

        # Load and preprocess master file
        master_df = load_excel(master_path)
        master_df.columns = master_df.columns.str.strip().str.upper()

        master_df['Main_Code'] = master_df['COLLEGE CODE'].str.strip() + "_" + master_df['COURSE CODE'].str.strip()

        # Merge
        merged_df = pd.merge(student_df, master_df, on='Main_Code', how='left', suffixes=('_student', '_master'))

        if merged_df.empty:
            st.warning("⚠️ No matching records found after merging.")
            return

        # Sidebar filters
        st.sidebar.header("🔍 Filters")

        course_types = sorted(merged_df['PROGRAM TYPE'].dropna().unique())
        selected_types = st.sidebar.multiselect("Program Type", course_types, default=course_types)

        durations = sorted(merged_df['DURATION'].dropna().unique())
        selected_durations = st.sidebar.multiselect("Program Duration", durations, default=durations)

        colleges = sorted(merged_df['COLLEGE'].dropna().unique())
        selected_colleges = st.sidebar.multiselect("Colleges", colleges, default=colleges[:10])

        cutoff_column = st.sidebar.selectbox("Category Cutoff", ['OC CUTOFF', 'EWS CUTOFF', 'OBC CUTOFF', 'SC CUTOFF', 'ST CUTOFF'])

        # Filter merged data
        filtered_df = merged_df[
            (merged_df['PROGRAM TYPE'].isin(selected_types)) &
            (merged_df['DURATION'].isin(selected_durations)) &
            (merged_df['COLLEGE'].isin(selected_colleges))
        ].copy()

        st.subheader("📊 Filtered Student Choices")

        display_cols = [
            'Choice Number', 'Main_Code', 'COLLEGE', 'PROGRAM',
            'TYPE', 'DURATION', 'FEES', cutoff_column
        ]
        display_df = filtered_df[display_cols].rename(columns={
            'COLLEGE': 'College',
            'PROGRAM': 'Program',
            'TYPE': 'Type',
            'DURATION': 'Duration',
            'FEES': 'Fees',
            cutoff_column: 'Cutoff'
        }).sort_values(by='Choice Number')

        st.dataframe(display_df)

        # Download
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Filtered Results",
            data=csv,
            file_name="filtered_choice_verification.csv",
            mime="text/csv"
        )

        # Unmatched rows
        unmatched_df = merged_df[merged_df['PROGRAM'].isna()]
        if not unmatched_df.empty:
            st.subheader("🚨 Unmatched Entries")
            st.dataframe(unmatched_df[['College Code', 'Institute', 'COURSE CODE', 'Program', 'Choice Number']])

    except Exception as e:
        st.error(f"❌ An error occurred during processing:\n\n{e}")
