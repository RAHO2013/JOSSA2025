import streamlit as st
import pandas as pd
import os

# Set page configuration
st.set_page_config(page_title="ETERNALS Dashboard", layout="wide")

# Sidebar Navigation
def navigate():
    st.sidebar.title("📌 Navigation")

    with st.sidebar.expander("🏠 Home", expanded=False):
        if st.button("Home", key="nav_home"):
            st.session_state.page = "home"

    with st.sidebar.expander("📄 Student Verifications", expanded=False):
        #if st.button("Verify Choice Filling", key="nav_verify_choice"):
            #st.session_state.page = "verify_choice"
        if st.button("Dashboard Verifier", key="nav_dashboard_verifier"):
            st.session_state.page = "verify_choice_dashboard"

    with st.sidebar.expander("📊 Smart Insights", expanded=False):
        if st.button("Smart Insights", key="nav_smart_insights"):
            st.session_state.page = "smart_insights"
            
    # NEW SECTION: Multi-Student Analyzer
    with st.sidebar.expander("👥 Multi-Student Analyzer", expanded=False):
        if st.button("Batch Analysis", key="nav_multi_student_analyzer"):
            st.session_state.page = "multi_student_analyzer"


# Page Router
def run_page():
    if 'page' not in st.session_state:
        st.session_state.page = "home"

    if st.session_state.page == "home":
        from modules.home import display_home
        display_home()

    #elif st.session_state.page == "verify_choice":
        #from modules.verify_choice_filling import display_verify_choice_filling
        #display_verify_choice_filling()

    elif st.session_state.page == "verify_choice_dashboard":
        from modules.verify_choice_filling_dashboard import display_verify_choice_filling_dashboard
        display_verify_choice_filling_dashboard()

    elif st.session_state.page == "smart_insights":
        from modules.smart_insights import display_smart_insights
        merged_df = st.session_state.get("merged_df", pd.DataFrame()) # Keep this line as it was in your provided snippet
        display_smart_insights()

    # NEW SECTION: Multi-Student Analyzer Page Display
    elif st.session_state.page == "multi_student_analyzer":
        from modules.multi_student_analyzer import display_multi_student_analyzer
        # display_multi_student_analyzer manages its own data from session state
        display_multi_student_analyzer()


# Main Function
def main():
    navigate()
    run_page()

# Run App
if __name__ == "__main__":
    main()
