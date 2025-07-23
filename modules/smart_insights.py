import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# @st.cache_data for efficient data loading
@st.cache_data
def load_excel(path):
    """
    Loads data from an Excel file (first sheet) with all columns as string type.
    """
    return pd.read_excel(path, sheet_name=0, dtype=str)

def display_smart_insights(merged_df=None):
    st.title("🧠 Smart Insights Dashboard")

    # Upload if not already loaded
    if merged_df is None or merged_df.empty:
        uploaded_file = st.file_uploader("📥 Upload Student Choice Excel", type=["xlsx"])
        if not uploaded_file:
            st.info("Please upload a student's filled choice Excel file to proceed.")
            return

        master_path = os.path.join("data", "MASTER EXCEL.xlsx")
        if not os.path.exists(master_path):
            st.error("❌ MASTER EXCEL.xlsx not found in the 'data/' folder.")
            return

        try:
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

            master_df = load_excel(master_path)
            # Updated: Normalize master_df column names to replace spaces with underscores
            master_df.columns = master_df.columns.str.strip().str.upper().str.replace(' ', '_')

            # Critical check for Main_Code components from Master
            if 'COLLEGE_CODE' not in master_df.columns or 'COURSE_CODE' not in master_df.columns:
                st.error("❌ MASTER EXCEL.xlsx is missing expected columns 'COLLEGE_CODE' or 'COURSE_CODE' (after normalization).")
                st.info(f"Detected master columns: {master_df.columns.tolist()}")
                return

            master_df['Main_Code'] = master_df['COLLEGE_CODE'].str.strip() + "_" + master_df['COURSE_CODE'].str.strip()

            merged_df = pd.merge(student_df, master_df, on='Main_Code', how='left', suffixes=('_student', '_master'))

            # Updated: Numeric fields now explicitly include FEM/GEN for new cutoff categories
            numeric_fields = [
                col for col in merged_df.columns
                if "FEM" in col or "GEN" in col or "FEE" in col or "CHOICE" in col
            ]
            for col in numeric_fields:
                if col in merged_df.columns:
                    merged_df[col] = pd.to_numeric(merged_df[col], errors='coerce')

            st.session_state["merged_df"] = merged_df

        except Exception as e:
            st.error(f"❌ Error during processing: {e}")
            return

    if merged_df is None or merged_df.empty:
        merged_df = st.session_state.get("merged_df", pd.DataFrame())
        if merged_df.empty:
            st.warning("Merged data not found. Please upload a file.")
            return

    # DEBUGGING LINE REMOVED: No longer shows in output
    # st.write("DEBUG: Columns available in Merged Data:", merged_df.columns.tolist())

    # Define all cutoff columns (normalized names) for various uses
    all_cutoff_cols = [
        'OC_FEM', 'OC_GEN', 'EWS_FEM', 'EWS_GEN', 'OBC_FEM', 'OBC_GEN',
        'SC_FEM', 'SC_GEN', 'ST_FEM', 'ST_GEN'
    ]

    # Mapping for student category to specific cutoff columns
    category_to_cutoff_map = {
        "OC": {"FEM": "OC_FEM", "GEN": "OC_GEN"},
        "EWS": {"FEM": "EWS_FEM", "GEN": "EWS_GEN"},
        "OBC": {"FEM": "OBC_FEM", "GEN": "OBC_GEN"},
        "SC": {"FEM": "SC_FEM", "GEN": "SC_GEN"},
        "ST": {"FEM": "ST_FEM", "GEN": "ST_GEN"}
    }

    # --- Student Input (Rank & Category) ---
    st.sidebar.header("🎓 Student Info")
    student_rank = st.sidebar.number_input("Your Rank (approx):", min_value=1, max_value=1000000, step=1)
    student_category_input = st.sidebar.selectbox("Your Category:", list(category_to_cutoff_map.keys()))
    student_gender_pref = st.sidebar.selectbox("Gender Preference:", ["GEN", "FEM"]) # GEN listed first as it's common
    

    # Determine the specific cutoff column to use for analysis based on user input
    col_to_check = None
    if student_category_input and student_gender_pref:
        selected_category_map = category_to_cutoff_map.get(student_category_input)
        if selected_category_map:
            preferred_col = selected_category_map.get(student_gender_pref)
            general_col = selected_category_map.get("GEN") # Always try to get the General column

            # 1. Try to use the preferred gender-specific column if it exists and has data
            if preferred_col and preferred_col in merged_df.columns and pd.notna(merged_df[preferred_col]).any():
                col_to_check = preferred_col
                if student_gender_pref == "FEM":
                    st.sidebar.info(f"Using your preferred cutoff: '{preferred_col}'.")
                else:
                    st.sidebar.info(f"Using your selected cutoff: '{preferred_col}'.")
            # 2. If preferred is not available or empty, try to fall back to the General column
            elif general_col and general_col in merged_df.columns and pd.notna(merged_df[general_col]).any():
                col_to_check = general_col
                if student_gender_pref == "FEM":
                    st.sidebar.warning(f"'{preferred_col}' not available/empty for your selection. Falling back to '{general_col}' for analysis.")
                else: # User selected GEN, and it's available
                    st.sidebar.info(f"Using your selected cutoff: '{general_col}'.")
            # 3. If neither is available or both are empty
            else:
                st.sidebar.warning(f"No valid cutoff column found for '{student_category_input}' with specified gender ('{student_gender_pref}'). Check data or select another category/gender.")
        else:
            st.sidebar.warning(f"Category '{student_category_input}' not mapped to specific cutoff columns.")
    else:
        st.sidebar.info("Please select your category and gender preference to analyze rank fit.")

    # NEW FEATURE: Filter by College Type (TYPE column)
    filtered_analysis_df = merged_df.copy() # Start with a copy of merged_df for analysis
    if 'TYPE' in merged_df.columns:
        college_types = ["All"] + list(merged_df['TYPE'].dropna().unique())
        selected_type = st.sidebar.selectbox("Filter by College Type:", college_types)
        
        if selected_type != "All":
            filtered_analysis_df = filtered_analysis_df[filtered_analysis_df['TYPE'] == selected_type].copy()
            if filtered_analysis_df.empty:
                st.warning(f"No data available for College Type: '{selected_type}'. Adjust your selections.")
                return
    else:
        st.sidebar.warning("College 'TYPE' column not found for filtering.")

    # --- All subsequent analysis sections will use filtered_analysis_df ---

    # --- 1. Dynamic Rank Fit Analyzer ---
    st.subheader("📏 Dynamic Rank Fit Analyzer")
    if col_to_check:
        # Ensure 'Rank Fit' and 'Rank Status' are calculated on the filtered_analysis_df
        filtered_analysis_df["Rank Fit"] = pd.to_numeric(filtered_analysis_df[col_to_check], errors='coerce')
        filtered_analysis_df["Rank Status"] = filtered_analysis_df["Rank Fit"].apply(
            lambda x: "✅ Likely" if pd.notna(x) and student_rank <= x else "❌ Unlikely"
        )
        
        fit_counts = filtered_analysis_df["Rank Status"].value_counts()
        st.write("Overview of Rank Status:")
        st.dataframe(fit_counts)
        st.bar_chart(fit_counts)

        st.markdown("---") # Separator for detailed list
        st.subheader("Detailed College List by Rank Status")

        # Dropdown to select Rank Status for detailed list
        rank_status_options = ["All", "✅ Likely", "❌ Unlikely"]
        selected_rank_status = st.selectbox("Select colleges with Rank Status:", rank_status_options)

        display_rank_df = filtered_analysis_df.copy() # Create a copy for displaying
        
        if selected_rank_status != "All":
            display_rank_df = display_rank_df[display_rank_df["Rank Status"] == selected_rank_status]

        # Define columns to show in the detailed list
        # Using 'PROGRAM' and 'Institute' as they are likely to be present without suffixes.
        display_cols = [
            'Choice Number', 'College Code', 'Institute', 'Program', 'PROGRAM', # 'PROGRAM' from master data
            col_to_check, # The specific cutoff column used
            "Rank Fit", "Rank Status"
        ]
        
        # Filter display_cols to ensure only existing columns are used
        display_cols = [col for col in display_cols if col in display_rank_df.columns]

        if not display_rank_df.empty:
            # Apply integer formatting to the cutoff column for display
            if col_to_check in display_cols:
                display_rank_df[col_to_check] = display_rank_df[col_to_check].fillna(0).astype(int)
            
            st.dataframe(display_rank_df[display_cols])
        else:
            st.info(f"No colleges found with status: '{selected_rank_status}' for the current filters.")

    else:
        st.warning("No matching cutoff column found for selected category and gender. Please check data and selections.")

    # --- NEW ADDITION: Cutoff Distribution by College Type ---
    st.subheader("📊 Cutoff Distribution by College Type")
    if 'TYPE' in filtered_analysis_df.columns and col_to_check:
        try:
            plot_df = filtered_analysis_df[['TYPE', col_to_check]].dropna().copy()
            plot_df[col_to_check] = pd.to_numeric(plot_df[col_to_check], errors='coerce')
            plot_df.dropna(subset=[col_to_check], inplace=True)

            if not plot_df.empty:
                fig, ax = plt.subplots(figsize=(10, 6))
                sns.boxplot(data=plot_df, x='TYPE', y=col_to_check, ax=ax)
                ax.set_title(f"{col_to_check} Distribution by College Type")
                ax.set_xlabel("College Type")
                ax.set_ylabel(f"{col_to_check}")
                plt.xticks(rotation=45, ha='right')
                st.pyplot(fig)
            else:
                st.info(f"No valid data to plot {col_to_check} distribution by College Type for current filter.")
        except Exception as e:
            st.warning(f"Could not generate Cutoff Distribution by College Type: {e}")
    else:
        st.info("Select a category, gender, and ensure 'TYPE' column is available to view Cutoff Distribution by College Type.")

    # --- 3. Program Type Summary ---
    st.subheader("🏷️ Program Type Summary")
    if "PROGRAM_TYPE" in filtered_analysis_df.columns:
        prog_counts = filtered_analysis_df["PROGRAM_TYPE"].value_counts()
        st.bar_chart(prog_counts)
    else:
        st.warning("Column 'PROGRAM_TYPE' not found for Program Type Summary.")

    # --- 4. Choice Number vs Cutoff Heatmap ---
    st.subheader("📊 Choice Heatmap: Position vs Cutoff")
    if 'Choice Number' in filtered_analysis_df.columns and col_to_check:
        try:
            heatmap_df = filtered_analysis_df[['Choice Number', col_to_check]].dropna().copy()
            heatmap_df = heatmap_df.astype({"Choice Number": int, col_to_check: float})
            
            fig, ax = plt.subplots()
            sns.histplot(
                data=heatmap_df,
                x="Choice Number",
                y=col_to_check,
                bins=20,
                pthresh=0.1,
                cmap="YlOrRd",
                ax=ax
            )
            ax.set_title(f"Choice Number vs {col_to_check} Density")
            st.pyplot(fig)
        except Exception as e:
            st.warning(f"Could not generate heatmap: {e}")
    else:
        st.info("Select a category and gender to generate the Heatmap.")

    # --- 5. Order Intelligence section has been removed as per request ---

    # --- 6. Category Match Alert ---
    st.subheader("⚠️ Category Match Alert")
    relevant_category_cols_for_check = []
    if student_category_input in category_to_cutoff_map:
        relevant_category_cols_for_check = [
            category_to_cutoff_map[student_category_input]["FEM"],
            category_to_cutoff_map[student_category_input]["GEN"]
        ]

    found_relevant_data = False
    if relevant_category_cols_for_check:
        for col in relevant_category_cols_for_check:
            if col in filtered_analysis_df.columns and pd.notna(filtered_analysis_df[col]).any():
                found_relevant_data = True
                break
    if found_relevant_data:
        st.success(f"✅ Your choices include options that match your category ({student_category_input}).")
    else:
        st.error(f"No valid entries found for your selected category ({student_category_input}) — You may not be using your reservation advantage or data is missing.")


    # --- Updated: Cutoff Statistics by College Type ---
    st.subheader("📈 Cutoff Statistics by College Type")
    if 'TYPE' in merged_df.columns and not merged_df['TYPE'].empty:
        unique_types = merged_df['TYPE'].dropna().unique()
        if len(unique_types) > 0:
            for college_type in unique_types:
                st.write(f"#### Type: {college_type}")
                type_df = merged_df[merged_df['TYPE'] == college_type].copy()
                type_numeric_cutoff_df = type_df[[col for col in all_cutoff_cols if col in type_df.columns]].copy()
                
                if not type_numeric_cutoff_df.empty and not type_numeric_cutoff_df.dropna().empty:
                    type_cutoff_summary = type_numeric_cutoff_df.describe().transpose()
                    if all(col in type_cutoff_summary.columns for col in ['count', 'mean', 'min', 'max']):
                        type_cutoff_summary = type_cutoff_summary[['count', 'mean', 'min', 'max']].copy()
                        for stat_col in ['mean', 'min', 'max']:
                            type_cutoff_summary[stat_col] = pd.to_numeric(type_cutoff_summary[stat_col], errors='coerce').fillna(0).astype(int)
                        st.dataframe(type_cutoff_summary)
                    else:
                        st.info(f"Not enough valid numeric data in cutoff columns for Type: '{college_type}' to generate full statistics.")
                else:
                    st.info(f"No valid numeric data found for cutoff columns in Type: '{college_type}'.")
        else:
            st.info("No unique college types found to break down statistics.")
            st.write("### Overall Cutoff Statistics (No Type Breakdown Available)")
            numeric_cutoff_df_for_stats = merged_df[[col for col in all_cutoff_cols if col in merged_df.columns]].copy()
            if not numeric_cutoff_df_for_stats.empty:
                cutoff_summary_df = numeric_cutoff_df_for_stats.describe().transpose()
                if all(col in cutoff_summary_df.columns for col in ['count', 'mean', 'min', 'max']):
                    cutoff_summary_df = cutoff_summary_df[['count', 'mean', 'min', 'max']].copy()
                    for stat_col in ['mean', 'min', 'max']:
                        cutoff_summary_df[stat_col] = pd.to_numeric(cutoff_summary_df[stat_col], errors='coerce').fillna(0).astype(int)
                    st.dataframe(cutoff_summary_df)
                else:
                    st.info("Not enough data or columns found to generate full overall cutoff statistics.")
            else:
                st.info("No numeric cutoff columns found to generate overall statistics.")
    else:
        st.warning("College 'TYPE' column not found in data. Displaying overall cutoff statistics without breakdown.")
        st.write("### Overall Cutoff Statistics")
        numeric_cutoff_df_for_stats = merged_df[[col for col in all_cutoff_cols if col in merged_df.columns]].copy()
        if not numeric_cutoff_df_for_stats.empty:
            cutoff_summary_df = numeric_cutoff_df_for_stats.describe().transpose()
            if all(col in cutoff_summary_df.columns for col in ['count', 'mean', 'min', 'max']):
                cutoff_summary_df = cutoff_summary_df[['count', 'mean', 'min', 'max']].copy()
                for stat_col in ['mean', 'min', 'max']:
                    cutoff_summary_df[stat_col] = pd.to_numeric(cutoff_summary_df[stat_col], errors='coerce').fillna(0).astype(int)
                st.dataframe(cutoff_summary_df)
            else:
                st.info("Not enough data or columns found to generate full overall cutoff statistics.")
        else:
            st.info("No numeric cutoff columns found to generate overall statistics.")


# Helper functions (style_row and split_ranges are included for completeness,
# though they might not be directly used in smart_insights.py's specific analysis sections)
def style_row(row, color_columns, heatmap_col, cutoff_col, threshold, df_for_colors):
    styles = [''] * len(row)
    cmap = plt.cm.tab20
    unique_color_maps = {
        col: {
            v: f'background-color: rgba({int(r*255)}, {int(g*255)}, {int(b*255)}, 0.3)'
            for v, (r, g, b, *_)
            in zip(df_for_colors[col].dropna().unique(), cmap(range(len(df_for_colors[col].dropna().unique()))))
        }
        for col in color_columns
    }
    min_val, max_val = None, None
    if heatmap_col and heatmap_col in df_for_colors.columns:
        try:
            min_val = df_for_colors[heatmap_col].astype(float).min()
            max_val = df_for_colors[heatmap_col].astype(float).max()
        except:
            heatmap_col = None
    for idx, col in enumerate(row.index):
        style_parts = []
        if col in unique_color_maps:
            val = row[col]
            style_parts.append(unique_color_maps[col].get(val, ''))
        if col == heatmap_col and pd.notna(row[col]):
            try:
                val = float(row[col])
                norm = (val - min_val) / max((max_val - min_val), 1)
                red = int(255 * norm)
                green = int(255 * (1 - norm))
                style_parts.append(f'background-color: rgb({red}, {green}, 100)')
            except:
                pass
        if col == cutoff_col:
            try:
                if float(row[col]) < threshold:
                    style_parts.append('background-color: #ffcccc')
            except:
                pass
        styles[idx] = '; '.join(filter(None, style_parts))
    return styles

def split_ranges(lst):
    if not lst:
        return ""
    ranges = []
    start = lst[0]
    for i in range(1, len(lst)):
        if lst[i] != lst[i - 1] + 1:
            end = lst[i - 1]
            ranges.append(f"{start}-{end}" if start != end else f"{start}")
            start = lst[i]
    ranges.append(f"{start}-{lst[-1]}" if start != lst[-1] else f"{start}")
    return ", ".join(ranges)

# Entry point for the Streamlit app
if __name__ == '__main__':
    display_smart_insights()
