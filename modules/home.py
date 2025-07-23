import streamlit as st
def display_home():
    st.title("🏠 Welcome to ETERNALS Dashboard")
        # Insert an image from the 'data' folder with the updated parameter
    st.image("data/maxresdefault.jpg", caption="ETERNALS Logo", use_container_width=True)
    st.markdown("""
        Use the sidebar to:
        - ✅ Upload and verify student choice filling sheets
        - 📊 Filter by course type, duration, colleges, and cutoff
        - 📥 Download filtered results

        ---
        Built for JoSAA counselling support.
    """)

# Call the function
display_home()
