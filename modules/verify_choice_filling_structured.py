import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt

@st.cache_data
def load_excel(path):
    """
    Loads data from an Excel file (first sheet) with all columns as string type.
    """
    return pd.read_excel(path, sheet_name=0, dtype=str)

def display_verify_choice_filling_dashboard():
    st.title("📊 Choice Filling Dashboard (Analytics + Verifier)")

    uploaded_file = st.file_uploader("📥 Upload Student Choice Excel", type=["xlsx"])
    if not uploaded_file:
        st.info("Upload a student's filled choice Excel file.")
        return

    master_path = os.path.join("data", "MASTER EXCEL.xlsx")
    if not os.path.exists(master_path):
        st.error("❌ MASTER EXCEL.xlsx not found in the 'data/' folder.")
        st.info("Please ensure 'MASTER EXCEL.xlsx' is placed inside the 'data' folder.")
        return

    try:
        # Load and preprocess student data
        student_df = pd.read_excel(uploaded_file, sheet_name=0, dtype=str)
        student_df = student_df.rename(columns={
            'Unnamed: 0': 'College Code',
            'Unnamed: 2': 'COURSE CODE',
            'Institute': 'Institute',
            'Program': 'Program', # Student's Program column
            'Choice No.': 'Choice Number'
        })
        student_df['Main_Code'] = student_df['College Code'].str.strip() + "_" + student_df['COURSE CODE'].str.strip()
        student_df['Choice Number'] = pd.to_numeric(student_df['Choice Number'], errors='coerce')

        # Load and preprocess master data
        master_df = load_excel(master_path)
        # Normalize master_df column names: uppercase and replace spaces with underscores
        master_df.columns = master_df.columns.str.strip().str.upper().str.replace(' ', '_')

        # Critical check for the Main_Code components from Master
        if 'COLLEGE_CODE' not in master_df.columns or 'COURSE_CODE' not in master_df.columns:
            st.error("❌ Master Excel is missing expected columns 'COLLEGE_CODE' or 'COURSE_CODE' (after normalization).")
            st.info(f"Detected master columns: {master_df.columns.tolist()}")
            st.stop()

        master_df['Main_Code'] = master_df['COLLEGE_CODE'].str.strip() + "_" + master_df['COURSE_CODE'].str.strip()

        # Perform the merge operation
        merged_df = pd.merge(student_df, master_df, on='Main_Code', how='left', suffixes=('_student', '_master'))

        # DEBUGGING LINE - KEEP THIS FOR NOW. Check this output for exact column names!
        st.write("DEBUG: Columns available in Merged Data:", merged_df.columns.tolist())

        # Convert relevant numeric fields for styling and calculations
        numeric_fields = [
            col for col in merged_df.columns
            if "FEM" in col or "GEN" in col or "FEE" in col or "CHOICE" in col
        ]
        for col in numeric_fields:
            if col in merged_df.columns:
                merged_df[col] = pd.to_numeric(merged_df[col], errors='coerce')

        # Setup Streamlit tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📑 Merged Data",
            "📊 Student Order Ranges",
            "📋 Unique Tables",
            "🔍 Validation",
            "📈 Dashboards"
        ])

        with tab1:
            st.subheader("Merged Choice Data")

            # DEFINE COLUMNS FOR DISPLAY IN TAB1:
            # ADJUST THESE NAMES BASED ON YOUR DEBUG OUTPUT IF THEY DON'T APPEAR!
            desired_display_columns = [
                'Choice Number', # From student_df
                'College Code',  # From student_df
                'COURSE CODE',   # From student_df
                'Institute',     # From student_df
                'Program',       # From student_df (Program from student_df's original column)
                'ORDER',          # From Master (normalized name, likely no suffix)
                'Main_Code',      # Common merge key
                'TYPE',           # From Master (normalized name, likely no suffix)
                'COLLEGE',        # From Master (normalized name, likely no suffix)
                'ESTB',           # From Master (normalized name, likely no suffix)
                'PROGRAM_master', # From Master (normalized name + suffix, as 'Program' likely collides)
                'COURSE_DURATION',# From Master (normalized name, likely no suffix)
                'PROGRAM_TYPE',   # From Master (normalized name, likely no suffix)
                'DEPARTMENT',     # From Master (normalized name, likely no suffix)
                'STATE',          # From Master (normalized name, likely no suffix)
                'OC_FEM', 'OC_GEN', 'EWS_FEM', 'EWS_GEN', 'OBC_FEM', 'OBC_GEN',
                'SC_FEM', 'SC_GEN', 'ST_FEM', 'ST_GEN' # Master cutoff columns (normalized, likely no suffix)
            ]

            # Filter merged_df to only include the desired columns for this tab
            final_display_df = merged_df[[col for col in desired_display_columns if col in merged_df.columns]].copy()
            final_display_df.index = range(1, len(final_display_df) + 1)

            # Reorder specific columns (ADJUST THESE NAMES IF NEEDED)
            preferred_order_for_display = ["TYPE", "PROGRAM_master"]
            cols = final_display_df.columns.tolist()
            for col_to_order in preferred_order_for_display:
                if col_to_order in cols:
                    cols.remove(col_to_order)
            for col_to_order in reversed(preferred_order_for_display):
                if col_to_order in final_display_df.columns:
                    cols.insert(0, col_to_order)
            final_display_df = final_display_df[cols]

            st.markdown("🧩 **Select columns to display**")
            visible_columns = st.multiselect(
                "Columns to show:",
                options=final_display_df.columns.tolist(),
                default=final_display_df.columns.tolist()
            )
            filtered_df = final_display_df[visible_columns]

            st.markdown("🎨 **Category-based coloring**")
            # Dynamically set default for color columns (ADJUST THESE NAMES IF NEEDED)
            default_color_columns = [
                col for col in ["TYPE", "PROGRAM_master"]
                if col in filtered_df.columns.tolist()
            ]
            color_columns = st.multiselect(
                "Color columns (categorical):",
                options=filtered_df.columns.tolist(),
                default=default_color_columns
            )

            numeric_columns = filtered_df.select_dtypes(include='number').columns.tolist()
            cutoff_column_options = ["None"] + [col for col in numeric_columns if "FEM" in col or "GEN" in col]
            heatmap_column = st.selectbox("🔥 Apply heatmap to numeric column", ["None"] + numeric_columns)
            cutoff_column = st.selectbox("🚨 Highlight cutoffs below threshold", cutoff_column_options)
            threshold = st.number_input("Threshold value", min_value=0, max_value=100000, value=1000)

            styled = filtered_df.style.apply(
                lambda row: style_row(row, color_columns, heatmap_column, cutoff_column, threshold, filtered_df),
                axis=1
            )

            # Format cutoff columns to remove decimals
            cutoff_display_columns_list = [ # Renamed to avoid conflict with function below
                'OC_FEM', 'OC_GEN', 'EWS_FEM', 'EWS_GEN', 'OBC_FEM', 'OBC_GEN',
                'SC_FEM', 'SC_GEN', 'ST_FEM', 'ST_GEN'
            ]
            format_dict = {}
            for col in cutoff_display_columns_list: # Used renamed variable
                if col in filtered_df.columns:
                    format_dict[col] = "{:.0f}"

            styled = styled.format(format_dict)

            st.dataframe(styled)

        with tab2:
            display_student_order_ranges(merged_df)

        with tab3:
            st.subheader("Unique Summaries by Field")
            # Existing grouped tables
            group_fields_to_check = ['TYPE', 'COLLEGE', 'PROGRAM_TYPE', 'DEPARTMENT', 'ORDER']
            
            for group_field in group_fields_to_check:
                if group_field in merged_df.columns:
                    st.write(f"### Grouped by {group_field}")
                    grouped = merged_df.groupby(group_field).agg(
                        Options_Filled=('Main_Code', 'count'),
                        First_Choice=('Choice Number', lambda x: sorted(pd.to_numeric(x, errors='coerce').dropna())[0] if not x.isnull().all() else None)
                    ).reset_index()
                    if group_field == 'ORDER':
                        grouped['First_Choice'] = pd.to_numeric(grouped['First_Choice'], errors='coerce')
                        grouped.sort_values(by=['ORDER', 'First_Choice'], inplace=True)
                    else:
                        grouped.sort_values('First_Choice', inplace=True)
                    st.dataframe(grouped)
                else:
                    st.warning(f"Column '{group_field}' not found for summary table. Please check master file headers and merge suffixes.")
            
            # NEW ADDITION: Cutoff Category Statistics
            st.write("### Cutoff Category Statistics")
            # Ensure only relevant columns are passed to describe and then format them.
            # Use the same list of cutoff columns from above.
            
            # Filter merged_df for only numeric cutoff columns that are present
            numeric_cutoff_df_for_stats = merged_df[[col for col in cutoff_display_columns_list if col in merged_df.columns]].copy()
            
            if not numeric_cutoff_df_for_stats.empty:
                cutoff_summary_df = numeric_cutoff_df_for_stats.describe().transpose()
                # Select only the desired statistics and convert them to integer for display
                # Fill NaN with 0 before converting to int, as describe() might produce NaN for empty columns etc.
                if all(col in cutoff_summary_df.columns for col in ['count', 'mean', 'min', 'max']):
                    cutoff_summary_df = cutoff_summary_df[['count', 'mean', 'min', 'max']].copy()
                    for stat_col in ['mean', 'min', 'max']:
                        # Convert to numeric first, then fillna, then convert to int
                        cutoff_summary_df[stat_col] = pd.to_numeric(cutoff_summary_df[stat_col], errors='coerce').fillna(0).astype(int)
                    st.dataframe(cutoff_summary_df)
                else:
                     st.info("Not enough data or columns found to generate full cutoff statistics.")
            else:
                st.info("No numeric cutoff columns found to generate statistics.")


        with tab4:
            display_validation(merged_df, master_df, student_df)

        with tab5:
            st.subheader("📊 Visual Overview")
            col1, col2 = st.columns(2) 

            with col1: 
                # DASHBOARD CHARTS:
                # ADJUST THIS NAME BASED ON YOUR DEBUG OUTPUT!
                if 'PROGRAM_TYPE' in merged_df.columns:
                    st.write("### Program Type Distribution")
                    st.bar_chart(merged_df['PROGRAM_TYPE'].value_counts())
                else:
                    st.warning("Column 'PROGRAM_TYPE' not found for Program Type Distribution chart. Please check master file headers and merge suffixes.")
            
            # Statewise Options Filled chart has been removed as per your request.
            # The 'col2' might remain empty or could be used for another chart if you add one later.

            # This chart will display in col2 if it exists, or below col1 if col2 is effectively empty
            # ADJUST THIS NAME BASED ON YOUR DEBUG OUTPUT!
            if 'TYPE' in merged_df.columns:
                st.write("### Institute Type (Pie Chart)")
                fig, ax = plt.subplots()
                type_counts = merged_df['TYPE'].value_counts()
                ax.pie(type_counts, labels=type_counts.index, autopct='%1.1f%%', startangle=90)
                ax.axis('equal')
                st.pyplot(fig)
            else:
                st.warning("Column 'TYPE' not found for Institute Type chart. Please check master file headers and merge suffixes.")

    except Exception as e:
        st.error(f"❌ Error during processing: {e}")

# Function definitions (ensure these are present in your file!)
def style_row(row, color_columns, heatmap_col, cutoff_col, threshold, df_for_colors):
    """
    Applies CSS styles to a DataFrame row for categorical coloring, heatmap, and cutoff highlighting.
    """
    styles = [''] * len(row)
    cmap = plt.cm.tab20

    unique_color_maps = {}
    if color_columns:
        for col in color_columns:
            if col in df_for_colors.columns:
                unique_values = df_for_colors[col].dropna().unique()
                if len(unique_values) > 0:
                    unique_color_maps[col] = {
                        v: f'background-color: rgba({int(r*255)}, {int(g*255)}, {int(b*255)}, 0.3)'
                        for v, (r, g, b, *_)
                        in zip(unique_values, cmap(range(len(unique_values))))
                    }

    min_val, max_val = None, None
    if heatmap_col and heatmap_col in df_for_colors.columns:
        try:
            numeric_vals = df_for_colors[heatmap_col].astype(float).dropna()
            if not numeric_vals.empty:
                min_val = numeric_vals.min()
                max_val = numeric_vals.max()
            else:
                heatmap_col = None
        except (ValueError, TypeError):
            heatmap_col = None

    for idx, col in enumerate(row.index):
        style_parts = []

        if col in unique_color_maps:
            val = row[col]
            style_parts.append(unique_color_maps[col].get(val, ''))

        if col == heatmap_col and pd.notna(row[col]) and min_val is not None and max_val is not None:
            try:
                val = float(row[col])
                if max_val > min_val:
                    norm = (val - min_val) / (max_val - min_val)
                else:
                    norm = 0.5
                red = int(255 * norm)
                green = int(255 * (1 - norm))
                style_parts.append(f'background-color: rgb({red}, {green}, 100)')
            except (ValueError, TypeError):
                pass

        if col == cutoff_col:
            try:
                if pd.notna(row[col]) and float(row[col]) < threshold:
                    style_parts.append('background-color: #ffcccc')
            except (ValueError, TypeError):
                pass

        styles[idx] = '; '.join(filter(None, style_parts))

    return styles

def display_student_order_ranges(df):
    """
    Displays a summary of student choice number ranges by program.
    """
    st.subheader("Student Order Ranges by Program")
    # ADJUST THIS: Based on DEBUG output, use 'PROGRAM' or 'PROGRAM_master'
    program_col_name = 'PROGRAM_master' # Default as per previous assumption
    # Check if 'PROGRAM' exists without suffix (if no collision)
    if 'PROGRAM' in df.columns and 'PROGRAM_master' not in df.columns:
        program_col_name = 'PROGRAM'
    elif 'PROGRAM_master' not in df.columns and 'PROGRAM' not in df.columns:
         st.error(f"Required column for Student Order Ranges ('PROGRAM' or 'PROGRAM_master') not found. Please check your master file's program column name.")
         return

    if 'Choice Number' not in df.columns:
        st.error("Required column 'Choice Number' for Student Order Ranges not found.")
        return

    df['Choice Number'] = pd.to_numeric(df['Choice Number'], errors='coerce')
    grouped = df.groupby([program_col_name]).agg(
        Options_Filled=('Main_Code', 'count'),
        Order_Range=('Choice Number', lambda x: split_ranges(sorted(x.dropna().astype(int).tolist())))
    ).reset_index()
    st.dataframe(grouped)

def display_group_summary_tables(df):
    """
    Displays summary tables grouped by various fields from the merged data.
    """
    st.subheader("Unique Summaries by Field")
    # ADJUST THESE NAMES BASED ON YOUR DEBUG OUTPUT!
    group_fields_to_check = ['TYPE', 'COLLEGE', 'PROGRAM_TYPE', 'DEPARTMENT', 'ORDER']
    
    for group_field in group_fields_to_check:
        if group_field in df.columns:
            st.write(f"### Grouped by {group_field}")
            grouped = df.groupby(group_field).agg(
                Options_Filled=('Main_Code', 'count'),
                First_Choice=('Choice Number', lambda x: sorted(pd.to_numeric(x, errors='coerce').dropna())[0] if not x.isnull().all() else None)
            ).reset_index()
            if group_field == 'ORDER':
                grouped['First_Choice'] = pd.to_numeric(grouped['First_Choice'], errors='coerce')
                grouped.sort_values(by=['ORDER', 'First_Choice'], inplace=True)
            else:
                grouped.sort_values('First_Choice', inplace=True)
            st.dataframe(grouped)
        else:
            st.warning(f"Column '{group_field}' not found for summary table. Please check master file headers and merge suffixes.")

def display_validation(merged, master, student):
    """
    Performs and displays validation checks between student and master data.
    """
    st.subheader("Validation Checks")

    st.write("❌ In student file but missing in master:")
    missing_in_master = student[~student['Main_Code'].isin(master['Main_Code'])]
    st.dataframe(missing_in_master) if not missing_in_master.empty else st.success("✅ None")

    st.write("📭 In master but not filled by student:")
    missing_in_upload = master[~master['Main_Code'].isin(student['Main_Code'])]
    st.dataframe(missing_in_upload) if not missing_in_upload.empty else st.success("✅ None")

    st.write("🧩 Duplicate Main_Codes in Student Data:")
    duplicates = student[student.duplicated(subset='Main_Code', keep=False)]
    st.dataframe(duplicates) if not duplicates.empty else st.success("✅ None")

def display_dashboard_charts(df):
    """
    Displays various charts for a visual overview of the merged data.
    """
    st.subheader("📊 Visual Overview")

    col1, col2 = st.columns(2) 

    with col1: 
        # DASHBOARD CHARTS:
        # ADJUST THIS NAME BASED ON YOUR DEBUG OUTPUT!
        if 'PROGRAM_TYPE' in df.columns:
            st.write("### Program Type Distribution")
            st.bar_chart(df['PROGRAM_TYPE'].value_counts())
        else:
            st.warning("Column 'PROGRAM_TYPE' not found for Program Type Distribution chart. Please check master file headers and merge suffixes.")
            
    # Statewise Options Filled chart has been removed as per your request.

    # This chart will display in col2 if it exists, or below col1 if col2 is effectively empty
    # ADJUST THIS NAME BASED ON YOUR DEBUG OUTPUT!
    if 'TYPE' in df.columns:
        st.write("### Institute Type (Pie Chart)")
        fig, ax = plt.subplots()
        type_counts = df['TYPE'].value_counts()
        ax.pie(type_counts, labels=type_counts.index, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')
        st.pyplot(fig)
    else:
        st.warning("Column 'TYPE' not found for Institute Type chart. Please check master file headers and merge suffixes.")


def split_ranges(lst):
    """
    Helper function to convert a list of numbers into a comma-separated string of ranges (e.g., [1,2,3,5,6] -> "1-3, 5-6").
    """
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
