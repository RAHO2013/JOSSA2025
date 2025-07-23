import streamlit as st
import pandas as pd
import os
import io

# @st.cache_data for efficient data loading
@st.cache_data
def load_excel(path):
    """
    Loads data from an Excel file (first sheet) with all columns as string type.
    """
    return pd.read_excel(path, sheet_name=0, dtype=str)

# Main function to display the Multi-Student Analyzer
def display_multi_student_analyzer():
    st.title("👨‍👩‍👧‍👦 Multi-Student Seat Chance Analyzer")

    # --- File Uploads ---
    st.sidebar.header("📥 Upload Files")
    student_batch_file = st.sidebar.file_uploader("Upload Student Batch Excel/CSV", type=["xlsx", "csv"], key="student_batch_uploader")
    
    # Ensure master Excel is present
    master_path = os.path.join("data", "MASTER EXCEL.xlsx")
    if not os.path.exists(master_path):
        st.error("❌ MASTER EXCEL.xlsx not found in the 'data/' folder. Please ensure it is present.")
        # Clear any old results if master file is missing
        if "analysis_results_df" in st.session_state:
            del st.session_state["analysis_results_df"]
        return

    # --- Data Loading and Preprocessing ---
    master_df = None
    processed_master_df = None 

    try:
        master_df = load_excel(master_path)
        master_df.columns = master_df.columns.str.strip().str.upper().str.replace(' ', '_')

        required_master_cols = ['COLLEGE_CODE', 'COURSE_CODE', 'TYPE']
        if not all(col in master_df.columns for col in required_master_cols):
            st.error(f"❌ MASTER EXCEL.xlsx is missing one or more required columns (after normalization): {required_master_cols}.")
            st.info(f"Detected master columns: {master_df.columns.tolist()}")
            if "analysis_results_df" in st.session_state:
                del st.session_state["analysis_results_df"]
            return

        master_df['Main_Code'] = master_df['COLLEGE_CODE'].str.strip() + "_" + master_df['COURSE_CODE'].str.strip()
        
        all_cutoff_cols = [
            'OC_FEM', 'OC_GEN', 'EWS_FEM', 'EWS_GEN', 'OBC_FEM', 'OBC_GEN',
            'SC_FEM', 'SC_GEN', 'ST_FEM', 'ST_GEN'
        ]

        for col in all_cutoff_cols:
            if col in master_df.columns:
                master_df[col] = pd.to_numeric(master_df[col], errors='coerce')
        
        processed_master_df = master_df 

    except Exception as e:
        st.error(f"❌ Error loading or preprocessing MASTER EXCEL.xlsx: {e}")
        if "analysis_results_df" in st.session_state:
            del st.session_state["analysis_results_df"]
        return

    if not student_batch_file:
        st.info("Upload a student batch file (Excel/CSV) to analyze seat chances.")
        # Clear results if batch file is not uploaded/cleared
        if "analysis_results_df" in st.session_state:
            del st.session_state["analysis_results_df"]
        return

    student_batch_df = None
    try:
        if student_batch_file.name.endswith('.xlsx'):
            student_batch_df = pd.read_excel(student_batch_file, sheet_name=0, dtype=str)
        else: # Assumes .csv
            student_batch_df = pd.read_csv(student_batch_file, dtype=str)
        
        student_batch_df.columns = student_batch_df.columns.str.strip().str.upper().str.replace(' ', '_')

        required_student_cols = [
            'NAME', 'STUDENT_ID', 'GENDER', 'CATEGORY',
            'JEE_ADVACED_CRL_RANK', 'JEE_ADVNCED_CATEGORY_RANK',
            'JEE_MAIN_CRL_RANK', 'JEE_MAIN_CATEGORY_RANK'
        ]
        if not all(col in student_batch_df.columns for col in required_student_cols):
            st.error(f"❌ Student batch file is missing one or more required columns (after normalization): {required_student_cols}.")
            st.info(f"Detected student batch columns: {student_batch_df.columns.tolist()}")
            if "analysis_results_df" in st.session_state:
                del st.session_state["analysis_results_df"]
            return
        
        for col in ['JEE_ADVACED_CRL_RANK', 'JEE_ADVNCED_CATEGORY_RANK',
                    'JEE_MAIN_CRL_RANK', 'JEE_MAIN_CATEGORY_RANK']:
            student_batch_df[col] = pd.to_numeric(student_batch_df[col], errors='coerce')

    except Exception as e:
        st.error(f"❌ Error loading or preprocessing student batch file: {e}")
        if "analysis_results_df" in st.session_state:
            del st.session_state["analysis_results_df"]
        return
    
    st.success(f"Loaded {len(student_batch_df)} students and {len(processed_master_df)} college options for analysis.")

    # --- Trigger Analysis with a Button ---
    if st.button("Run Seat Chance Analysis", key="run_analysis_button"):
        st.session_state["analysis_results_df"] = None # Clear previous results to indicate new run
        
        results_list = []
        category_to_cutoff_map = {
            "OC": {"FEM": "OC_FEM", "GEN": "OC_GEN"},
            "EWS": {"FEM": "EWS_FEM", "GEN": "EWS_GEN"},
            "OBC": {"FEM": "OBC_FEM", "GEN": "OBC_GEN"},
            "SC": {"FEM": "SC_FEM", "GEN": "SC_GEN"},
            "ST": {"FEM": "ST_FEM", "GEN": "ST_GEN"}
        }

        # Use st.spinner or st.status for long operations
        with st.status("Analyzing student chances...", expanded=True) as status:
            my_bar = st.progress(0, text="Starting analysis...")

            for idx, student_row in student_batch_df.iterrows():
                student_name = student_row['NAME']
                student_id = student_row['STUDENT_ID']
                student_category = student_row['CATEGORY']
                student_gender = student_row['GENDER']
                
                status.write(f"Processing {student_name} (ID: {student_id})...")

                if student_category == "OC":
                    current_student_adv_rank = student_row['JEE_ADVACED_CRL_RANK']
                else:
                    current_student_adv_rank = student_row['JEE_ADVNCED_CATEGORY_RANK']
                
                if student_category == "OC":
                    current_student_mains_rank = student_row['JEE_MAIN_CRL_RANK']
                else:
                    current_student_mains_rank = student_row['JEE_MAIN_CATEGORY_RANK']

                current_student_eligible_cutoff_cols = []
                
                if student_category in category_to_cutoff_map:
                    category_map = category_to_cutoff_map.get(student_category)
                    if category_map:
                        if student_gender == "FEM":
                            if category_map.get("FEM") in processed_master_df.columns:
                                current_student_eligible_cutoff_cols.append(category_map["FEM"])
                            if category_map.get("GEN") in processed_master_df.columns:
                                current_student_eligible_cutoff_cols.append(category_map["GEN"])
                        else:
                            if category_map.get("GEN") in processed_master_df.columns:
                                current_student_eligible_cutoff_cols.append(category_map["GEN"])

                    if student_category != "OC":
                        if student_gender == "FEM":
                            if 'OC_GEN' in processed_master_df.columns:
                                current_student_eligible_cutoff_cols.append('OC_GEN')
                            if 'OC_FEM' in processed_master_df.columns:
                                current_student_eligible_cutoff_cols.append('OC_FEM')
                        else:
                            if 'OC_GEN' in processed_master_df.columns:
                                current_student_eligible_cutoff_cols.append('OC_GEN')
                
                current_student_eligible_cutoff_cols = list(set([col for col in current_student_eligible_cutoff_cols if col in processed_master_df.columns]))

                for _, college_option in processed_master_df.iterrows():
                    college_type = college_option['TYPE']
                    college_code = college_option['COLLEGE_CODE']
                    course_code = college_option['COURSE_CODE']
                    program_name = college_option.get('PROGRAM', 'N/A')

                    applicable_student_rank = None
                    rank_type_used = None

                    if college_type == 'IIT':
                        applicable_student_rank = current_student_adv_rank
                        rank_type_used = "JEE Advanced Rank"
                    elif college_type in ['NIT', 'IIIT', 'GFTI']:
                        applicable_student_rank = current_student_mains_rank
                        rank_type_used = "JEE Mains Rank"
                    else:
                        continue 

                    best_eligible_cutoff_for_option = None
                    relevant_cutoffs_for_option_display = [] 

                    if applicable_student_rank is not None and pd.notna(applicable_student_rank):
                        option_cutoffs_values = []
                        
                        for col in current_student_eligible_cutoff_cols:
                            if col in college_option and pd.notna(college_option[col]):
                                option_cutoffs_values.append(pd.to_numeric(college_option[col], errors='coerce'))
                        
                        if option_cutoffs_values:
                            best_eligible_cutoff_for_option = min(option_cutoffs_values)
                            relevant_cutoffs_for_option_display = [f"{col}: {int(college_option[col])}" for col in current_student_eligible_cutoff_cols if col in college_option and pd.notna(college_option[col])]
                        else:
                            best_eligible_cutoff_for_option = None

                    seat_chance = "N/A - No Cutoff"
                    if best_eligible_cutoff_for_option is not None:
                        if applicable_student_rank <= best_eligible_cutoff_for_option:
                            seat_chance = "✅ LIKELY"
                        else:
                            seat_chance = "❌ UNLIKELY"
                    elif applicable_student_rank is None or pd.isna(applicable_student_rank):
                        seat_chance = "N/A - Student Rank Missing"

                    results_list.append({
                        'Student_ID': student_id,
                        'Student_Name': student_name,
                        'Student_Category': student_category,
                        'Student_Gender': student_gender,
                        'College_Type': college_type,
                        'College_Code': college_code,
                        'Program_Name': program_name,
                        'Course_Code': course_code,
                        'Student_Rank_Used': f"{int(applicable_student_rank)}" if pd.notna(applicable_student_rank) else "N/A",
                        'Rank_Type': rank_type_used,
                        'Best_Eligible_Cutoff': f"{int(best_eligible_cutoff_for_option)}" if pd.notna(best_eligible_cutoff_for_option) else "N/A",
                        'Considered_Cutoffs_for_Option': ", ".join(relevant_cutoffs_for_option_display),
                        'Seat_Chance': seat_chance
                    })
                
                my_bar.progress((idx + 1) / len(student_batch_df), text=f"Analyzing student {idx + 1} of {len(student_batch_df)}: {student_name}")

            my_bar.empty()
            status.update(label="Analysis complete!", state="complete", expanded=False)

        st.session_state["analysis_results_df"] = pd.DataFrame(results_list)
        
    # --- Display Results ---
    if "analysis_results_df" in st.session_state and not st.session_state["analysis_results_df"].empty:
        results_df = st.session_state["analysis_results_df"]
        st.subheader("Results:")
        st.dataframe(results_df)

        # Download button
        csv_buffer = io.StringIO()
        results_df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="⬇️ Download Results as CSV",
            data=csv_buffer.getvalue(),
            file_name="seat_chance_analysis_results.csv",
            mime="text/csv"
        )
    elif st.session_state.get("analysis_results_df") is None: # Only if analysis hasn't run yet
         st.info("Click 'Run Seat Chance Analysis' to view results after uploading files.")


# Entry point for the Streamlit app
if __name__ == '__main__':
    display_multi_student_analyzer()
