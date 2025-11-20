import pandas as pd
import numpy as np
import streamlit as st
import tempfile
import os
import re

# --- UI Configuration ---
st.set_page_config(
    layout="centered", 
    page_title="💰 Financial Assistant" 
) 

# --- Custom CSS for Styling ---
# This CSS targets the primary button style globally to change the background color from red to green.
# This ensures all primary buttons (like 'Generate Report') use the new green color.
st.markdown("""
<style>
/* Change the primary button background color to a nice green */
.stButton>button.primary {
    background-color: #4CAF50; /* Green */
    color: white; /* Keep text white */
    border-color: #4CAF50;
}

/* Center and style the title/header elements */
div[data-testid="stAppViewBlock"] h1 {
    text-align: center;
    color: #00BFFF; /* Light Blue for the main dollar title */
}
div[data-testid="stAppViewBlock"] h3 {
    text-align: center;
}
</style>
""", unsafe_allow_html=True)


# --- Configuration ---
# 1. RECURRING KEYWORDS: FINAL list verified against all your provided samples.
RECURRING_KEYWORDS = [
    'SMALL WORL',
    'Goldfish Swim School',
    'SCHOOL OF MUSIC',      
    'T-MOBILE*AUTO PAY', 
    'NOETIC MATH',
    'FuboTV Inc',
    'OSRX',                 
    'SIMPLISAFE',
    'APPLE.COM/BILL',
    'HULUPULS',             
    'AMAZON PRIME',         
    'AMAZON.COM RING PROTECT',
    'PANERA SIP CLUB',      
    'Supercuts',
    'BAY CLUB'              
]

# 2. Required column names for input files (All 6 columns are included)
REQUIRED_COLUMNS = [
    'Transaction Date',
    'Post Date',
    'Description',
    'Category',
    'Type',
    'Amount'
]

# --- Core Data Processing Functions ---

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans data types and standardizes date format. Retains all 6 original columns.
    """
    # 1. Enforce the 6 column names to match the input file exactly
    df.columns = REQUIRED_COLUMNS 

    # 2. Convert 'Amount' to numeric
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')

    # 3. Convert date columns and format to MM/DD/YY
    for col in ['Transaction Date', 'Post Date']:
        # CRITICAL FIX: Use df[col] to convert column data, not the column name string 'col'
        df[col] = pd.to_datetime(df[col], errors='coerce') 
        df[col] = df[col].dt.strftime('%m/%d/%y')
    
    # Return all 6 columns
    return df

def calculate_metrics(df: pd.DataFrame, keywords: list) -> pd.DataFrame:
    """
    Filters for expenses (Amount <= 0), sorts, and calculates the four required metrics.
    """
    # 1. Filtering: Keep only expense transactions (Amount <= 0)
    expenses_df = df[df['Amount'] <= 0].copy()

    if expenses_df.empty:
        return expenses_df

    # 2. Sorting: Descending order of expense magnitude (largest negative amount first)
    expenses_df = expenses_df.sort_values(by='Amount', ascending=True)

    # Calculate Grand Total (absolute sum of all expenses)
    grand_total_abs = expenses_df['Amount'].abs().sum()

    # 3. Metric Calculation
    
    # 3a. Recurring Flag: Uses improved Regex for robust, case-insensitive phrase matching
    def check_recurring(description):
        if pd.isna(description):
            return 0
        desc_lower = str(description).lower()
        
        for kw in keywords:
            # Create a pattern to match the keyword. re.escape handles special characters.
            pattern = re.escape(kw.lower()) 
            
            if re.search(pattern, desc_lower):
                return 1
                
        return 0

    expenses_df['Recurring Flag'] = expenses_df['Description'].apply(check_recurring)

    # 3b. Cumulative Sum (running total of expenses)
    expenses_df['Cumulative Sum'] = expenses_df['Amount'].cumsum()
    
    # 3c. % of total: Each expense's percentage contribution to the absolute Grand Total
    expenses_df['% of total'] = expenses_df['Amount'].abs() / grand_total_abs

    # 3d. Cumulative % of total (running percentage of the Grand Total)
    expenses_df['Cumulative % of total'] = expenses_df['% of total'].cumsum()
    
    # Reorder columns for the final 'Combined Expenses' sheet (10 columns)
    FINAL_COLUMNS = REQUIRED_COLUMNS + ['Recurring Flag', 'Cumulative Sum', '% of total', 'Cumulative % of total']
    
    return expenses_df[FINAL_COLUMNS]

def create_pivot_summary(expenses_df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates the Category-level roll-up summary (Sheet 4).
    """
    if expenses_df.empty:
        return pd.DataFrame(columns=['Category', 'Total Amount', '% of Grand Total'])
        
    # Group by Category and sum the Amount
    summary_df = expenses_df.groupby('Category')['Amount'].sum().reset_index()
    summary_df.columns = ['Category', 'Total Amount']

    # Calculate Grand Total for the whole report
    grand_total_abs = summary_df['Total Amount'].abs().sum()

    # Calculate % of Grand Total
    summary_df['% of Grand Total'] = summary_df['Total Amount'].abs() / grand_total_abs

    # Add a Grand Total row
    grand_total_row = {
        'Category': '**Grand Total**',
        'Total Amount': summary_df['Total Amount'].sum(),
        '% of Grand Total': summary_df['% of Grand Total'].sum()
    }
    summary_df.loc[len(summary_df)] = grand_total_row
    
    return summary_df

def generate_report(file_a_path: str, file_b_path: str, output_path: str):
    """
    Orchestrates the data processing and report generation into a multi-sheet Excel file.
    """
    # 1. Read and Clean Source Files
    df_a_raw = pd.read_excel(file_a_path)
    df_b_raw = pd.read_excel(file_b_path)
    
    df_a_cleaned = clean_data(df_a_raw.copy())
    df_b_cleaned = clean_data(df_b_raw.copy())
    
    # 2. Combination: Merge all rows
    combined_df = pd.concat([df_a_cleaned, df_b_cleaned], ignore_index=True)

    # 3. Filtering, Sorting, and Metric Calculation
    combined_expenses_df = calculate_metrics(combined_df, RECURRING_KEYWORDS)

    # 4. Expense Pivot Summary
    pivot_summary_df = create_pivot_summary(combined_expenses_df)
    
    # 5. Output Structure: Generate the multi-sheet Excel file
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        
        # Sheet 1: Source A (6 columns)
        df_a_cleaned[REQUIRED_COLUMNS].to_excel(writer, sheet_name='Source A', index=False)
        
        # Sheet 2: Source B (6 columns)
        df_b_cleaned[REQUIRED_COLUMNS].to_excel(writer, sheet_name='Source B', index=False)
        
        # Sheet 3: Combined Expenses (10 columns)
        combined_expenses_df.to_excel(writer, sheet_name='Combined Expenses', index=False)

        # Sheet 4: Expense Pivot Summary
        pivot_summary_df.to_excel(writer, sheet_name='Expense Pivot Summary', index=False)

        # Apply formatting (Currency and Percentage)
        workbook = writer.book
        money_fmt = workbook.add_format({'num_format': '$#,##0.00'})
        percent_fmt = workbook.add_format({'num_format': '0.00%'})
        
        # Combined Expenses formatting 
        worksheet_ce = writer.sheets['Combined Expenses']
        worksheet_ce.set_column('F:F', 12, money_fmt)     # Amount
        worksheet_ce.set_column('H:H', 15, money_fmt)     # Cumulative Sum 
        worksheet_ce.set_column('I:I', 10, percent_fmt)   # % of total 
        worksheet_ce.set_column('J:J', 18, percent_fmt)   # Cumulative % of total 

        # Expense Pivot Summary formatting
        worksheet_ps = writer.sheets['Expense Pivot Summary']
        worksheet_ps.set_column('B:B', 15, money_fmt)     # Total Amount
        worksheet_ps.set_column('C:C', 18, percent_fmt)   # % of Grand Total

    # Return the dataframes and the file path for display and download
    return combined_expenses_df, pivot_summary_df, df_a_cleaned, df_b_cleaned, output_path


# --- Streamlit Web App Interface ---

def main():
    # CUSTOM STYLING FOR BRANDING: HTML is simplified since CSS handles the color and centering
    st.title('💰 Financial Assistant')
    st.markdown('### Generate Your Comprehensive Expense Report')
    
    # --- 1. Upload Section (Clean and Compact) ---
    st.subheader("📁 1. Upload Transaction Files")

    # Use an expander to hide the detailed column requirements
    with st.expander("Click for Required File Format (6 Columns)"):
        st.caption("Please ensure your uploaded files contain exactly these 6 columns:")
        st.markdown(f"**{', '.join(REQUIRED_COLUMNS)}**")
        st.caption("This minimizes clutter on the main page.")

    # Create columns for Source File A to display uploader and status side-by-side
    col_a_label, col_a_status = st.columns([0.8, 0.2])

    with col_a_label:
        file_a = st.file_uploader(
            "Source File A (.xlsx or .xls)",  # Static Label
            type=['xlsx', 'xls'],
            key='file_a_uploader'
        )
    with col_a_status:
        # Check the value returned by the widget itself (which is stored in session state)
        status_a = '✅' if st.session_state.get('file_a_uploader') else '⚠️'
        # Use st.markdown to display the status, aligned with the uploader
        st.markdown(f"<div style='padding-top: 25px;'>{status_a}</div>", unsafe_allow_html=True)


    # Create columns for Source File B
    col_b_label, col_b_status = st.columns([0.8, 0.2])

    with col_b_label:
        file_b = st.file_uploader(
            "Source File B (.xlsx or .xls)",  # Static Label
            type=['xlsx', 'xls'],
            key='file_b_uploader'
        )
    with col_b_status:
        # Check the value returned by the widget itself
        status_b = '✅' if st.session_state.get('file_b_uploader') else '⚠️'
        st.markdown(f"<div style='padding-top: 25px;'>{status_b}</div>", unsafe_allow_html=True)
        
    st.markdown("---") 
    
    # --- 2. Generate and Download Buttons (Side-by-Side) ---
    st.subheader("🚀 2. Report Generation")
    
    # Use two columns for the buttons
    col_generate, col_download = st.columns([1, 1])

    with col_generate:
        # The 'type="primary"' button will now be green due to the custom CSS injection
        button_clicked = st.button('Generate 4-Sheet Expense Report', key='main_generate_button', type="primary")

    with col_download:
        # The download button is defined here but is initially disabled/hidden.
        # It needs the report bytes stored in session state from a previous successful run.
        if st.session_state.get('report_bytes'):
            col_download.download_button(
                label="⬇️ Download Report",
                data=st.session_state.report_bytes,
                file_name=st.session_state.report_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key='download_report_button'
            )
        else:
            # Placeholder text/button when no report is ready
            col_download.button('Report Not Ready', disabled=True, key='placeholder_button')


    st.markdown("---") 

    # Container to hold status and the main output
    output_container = st.container()
    
    status_message = st.empty()
    
    # --- SIDEBAR ---
    st.sidebar.title("⚙️ Configuration")
    st.sidebar.caption("Keywords used to flag recurring transactions.")
    st.sidebar.markdown(f'**Recurring Keywords List:**')
    
    # Display the keywords list in the sidebar
    for keyword in RECURRING_KEYWORDS:
        st.sidebar.caption(f'- {keyword}')


    # Conditional structure for processing
    if button_clicked:
        if file_a is not None and file_b is not None:
            # --- START PROCESSING ---
            try:
                status_message.info("Processing files... this may take a moment.")
                
                with tempfile.TemporaryDirectory() as temp_dir:
                    path_a = os.path.join(temp_dir, file_a.name)
                    path_b = os.path.join(temp_dir, file_b.name)
                    
                    with open(path_a, "wb") as f:
                        f.write(file_a.getvalue())
                    with open(path_b, "wb") as f:
                        f.write(file_b.getvalue())

                    output_filename = 'Financial_Data_Report_Output.xlsx'
                    output_path = os.path.join(temp_dir, output_filename)
                    
                    # CALL THE CORE PROCESSING FUNCTION
                    combined_expenses_df, pivot_summary_df, df_a_cleaned, df_b_cleaned, final_path = generate_report(path_a, path_b, output_path)
                    
                    # Read the generated report file into memory for download
                    with open(final_path, "rb") as f:
                        report_bytes = f.read()
                        
                    # CRITICAL: Store the report data in Session State for the download button on the NEXT rerun
                    st.session_state.report_bytes = report_bytes
                    st.session_state.report_filename = output_filename
                    
                    status_message.success("Report generated successfully! Scroll down for analysis. The download button is now active above.")
                    
                    # --- OUTPUT SECTION (METRICS, CHARTS, TABS, DATAFRAMES) ---
                    output_container.header("3. 📊 Expense Analysis")
                    
                    # Row 1: Key Metrics (st.metric)
                    col_met1, col_met2, col_met3 = output_container.columns(3)
                    
                    grand_total_abs = combined_expenses_df['Amount'].abs().sum()
                    recurring_count = combined_expenses_df['Recurring Flag'].sum()
                    expense_count = len(combined_expenses_df)
                    
                    col_met1.metric(label="Total Expenses for Period", value=f"${grand_total_abs:,.2f}")
                    col_met2.metric(label="Total Transactions", value=expense_count)
                    col_met3.metric(label="Recurring Flagged", value=recurring_count)
                    
                    # Row 2: Charts (Simple Category Bar Chart)
                    output_container.subheader("Top Categories")
                    # Prepare data for chart (exclude Grand Total row)
                    chart_data = pivot_summary_df[pivot_summary_df['Category'] != '**Grand Total**'].copy()
                    chart_data['Amount (Absolute)'] = chart_data['Total Amount'].abs()
                    chart_data = chart_data.sort_values('Amount (Absolute)', ascending=False).head(10)
                    
                    # Display the bar chart
                    output_container.bar_chart(chart_data.set_index('Category')['Amount (Absolute)'])

                    output_container.markdown("---")

                    # Row 3: Tabs for detailed data (st.tabs)
                    tab1, tab2, tab3, tab4 = output_container.tabs([
                        "Combined Expenses (Final)", 
                        "Category Summary", 
                        "Source A Raw", 
                        "Source B Raw"
                    ])

                    # Tab 1: Combined Expenses (10 Columns)
                    tab1.subheader("Combined Expenses Data (10 Columns)")
                    # Apply custom styling for better visibility in the dataframe
                    styled_df = combined_expenses_df.style.format({
                        'Amount': '${:,.2f}',
                        'Cumulative Sum': '${:,.2f}',
                        '%' of total': '{:.2%}',
                        'Cumulative % of total': '{:.2%}'
                    })
                    tab1.dataframe(styled_df, use_container_width=True)

                    # Tab 2: Category Summary (Pivot Table)
                    tab2.subheader("Category Roll-up Summary")
                    tab2.dataframe(pivot_summary_df, use_container_width=True)

                    # Tab 3: Source A Raw
                    tab3.subheader("Source A Data")
                    tab3.dataframe(df_a_cleaned, use_container_width=True)

                    # Tab 4: Source B Raw
                    tab4.subheader("Source B Data")
                    tab4.dataframe(df_b_cleaned, use_container_width=True)

            except Exception as e:
                # The crucial 'except' block, aligned with 'try:'
                # Clear session state on error so download button disappears
                if 'report_bytes' in st.session_state:
                    del st.session_state.report_bytes
                if 'report_filename' in st.session_state:
                    del st.session_state.report_filename
                    
                st.exception(e) 
                status_message.error(f"An error occurred during processing. Please check the logs for details.")
                st.warning("Please ensure your files have exactly these 6 columns in order: **Transaction Date, Post Date, Description, Category, Type, Amount**.")
            # --- END PROCESSING ---
            
            # Use st.rerun() to immediately update the page and activate the download button
            # Note: This is an optional step but makes the download button immediately available.
            # If you prefer the button to only appear on the next manual click, you can remove this.
            st.rerun()

        else:
            # This runs if the button was clicked BUT one or both files are missing
            status_message.warning("Please upload both Source File A and Source File B.")


if __name__ == '__main__':
    # Initialize session state for report data
    if 'report_bytes' not in st.session_state:
        st.session_state.report_bytes = None
    if 'report_filename' not in st.session_state:
        st.session_state.report_filename = None
        
    main()
