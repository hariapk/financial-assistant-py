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

# --- Custom CSS for Styling (Light Blue Header, Green Primary Button) ---
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
RECURRING_KEYWORDS = [
    'SMALL WORL', 'Goldfish Swim School', 'SCHOOL OF MUSIC', 'T-MOBILE*AUTO PAY', 
    'NOETIC MATH', 'FuboTV Inc', 'OSRX', 'SIMPLISAFE', 'APPLE.COM/BILL', 
    'HULUPULS', 'AMAZON PRIME', 'AMAZON.COM RING PROTECT', 'PANERA SIP CLUB',      
    'Supercuts', 'BAY CLUB'              
]

REQUIRED_COLUMNS = [
    'Transaction Date', 'Post Date', 'Description', 'Category', 'Type', 'Amount'
]

# --- Core Data Processing Functions ---

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans data types, standardizes date format, and ensures column integrity.
    """
    df.columns = REQUIRED_COLUMNS 
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')

    for col in ['Transaction Date', 'Post Date']:
        df[col] = pd.to_datetime(df[col], errors='coerce') 
        df[col] = df[col].dt.strftime('%m/%d/%y')
    
    return df

def calculate_metrics(df: pd.DataFrame, keywords: list) -> pd.DataFrame:
    """
    Filters for expenses, sorts, and calculates the four required metrics.
    """
    expenses_df = df[df['Amount'] <= 0].copy()

    if expenses_df.empty:
        return expenses_df.reindex(columns=REQUIRED_COLUMNS + ['Recurring Flag', 'Cumulative Sum', '% of total', 'Cumulative % of total'])

    expenses_df = expenses_df.sort_values(by='Amount', ascending=True)
    grand_total_abs = expenses_df['Amount'].abs().sum()

    def check_recurring(description):
        if pd.isna(description):
            return 0
        desc_lower = str(description).lower()
        for kw in keywords:
            pattern = re.escape(kw.lower()) 
            if re.search(pattern, desc_lower):
                return 1
        return 0

    expenses_df['Recurring Flag'] = expenses_df['Description'].apply(check_recurring)
    expenses_df['Cumulative Sum'] = expenses_df['Amount'].cumsum()
    expenses_df['% of total'] = expenses_df['Amount'].abs() / grand_total_abs
    expenses_df['Cumulative % of total'] = expenses_df['% of total'].cumsum()
    
    FINAL_COLUMNS = REQUIRED_COLUMNS + ['Recurring Flag', 'Cumulative Sum', '% of total', 'Cumulative % of total']
    
    return expenses_df[FINAL_COLUMNS]

def create_pivot_summary(expenses_df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates the Category-level roll-up summary (Sheet 4) and sorts it by spend.
    """
    if expenses_df.empty:
        return pd.DataFrame(columns=['Category', 'Total Amount', '% of Grand Total'])
        
    summary_df = expenses_df.groupby('Category')['Amount'].sum().reset_index()
    summary_df.columns = ['Category', 'Total Amount']

    # --- NEW: Sort by the magnitude (absolute value) of Total Amount (largest expense first) ---
    summary_df = summary_df.sort_values(by='Total Amount', ascending=True).reset_index(drop=True)
    # Note: Since expenses are negative, ascending=True means largest magnitude (most negative) comes first.

    grand_total_abs = summary_df['Total Amount'].abs().sum()
    summary_df['% of Grand Total'] = summary_df['Total Amount'].abs() / grand_total_abs

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
    df_a_raw = pd.read_excel(file_a_path)
    df_b_raw = pd.read_excel(file_b_path)
    
    df_a_cleaned = clean_data(df_a_raw.copy())
    df_b_cleaned = clean_data(df_b_raw.copy())
    
    combined_df = pd.concat([df_a_cleaned, df_b_cleaned], ignore_index=True)
    combined_expenses_df = calculate_metrics(combined_df, RECURRING_KEYWORDS)
    pivot_summary_df = create_pivot_summary(combined_expenses_df)
    
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        
        # --- Define Formats ---
        workbook = writer.book
        money_fmt = workbook.add_format({'num_format': '$#,##0.00'})
        percent_fmt = workbook.add_format({'num_format': '0.00%'})
        
        # NEW: Header Format (Black fill, White bold font)
        header_fmt = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#000000', # Black fill
            'font_color': '#FFFFFF', # White font
            'border': 1
        })
        
        sheet_data = {
            'Source A': df_a_cleaned[REQUIRED_COLUMNS],
            'Source B': df_b_cleaned[REQUIRED_COLUMNS],
            'Combined Expenses': combined_expenses_df,
            'Expense Pivot Summary': pivot_summary_df
        }

        # Write data and apply header format to all sheets
        for sheet_name, df in sheet_data.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False, header=False, startrow=1)
            worksheet = writer.sheets[sheet_name]
            
            # Write column headers with the custom format at row 0 (which is startrow=1 in Excel)
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_fmt)

        # Apply specific column formatting
        
        # Combined Expenses formatting 
        worksheet_ce = writer.sheets['Combined Expenses']
        worksheet_ce.set_column('F:F', 12, money_fmt) 
        worksheet_ce.set_column('H:H', 15, money_fmt)  
        worksheet_ce.set_column('I:I', 10, percent_fmt) 
        worksheet_ce.set_column('J:J', 18, percent_fmt) 

        # Expense Pivot Summary formatting
        worksheet_ps = writer.sheets['Expense Pivot Summary']
        worksheet_ps.set_column('B:B', 15, money_fmt)  
        worksheet_ps.set_column('C:C', 18, percent_fmt)

    return combined_expenses_df, pivot_summary_df, df_a_cleaned, df_b_cleaned, output_path


# --- Streamlit Web App Interface ---

def main():
    st.title('💰 Financial Assistant')
    st.markdown('### Generate Your Comprehensive Expense Report')
    
    # --- 1. Upload Section ---
    st.subheader("📁 1. Upload Transaction Files")

    with st.expander("Click for Required File Format (6 Columns)"):
        st.caption("Please ensure your uploaded files contain exactly these 6 columns:")
        st.markdown(f"**{', '.join(REQUIRED_COLUMNS)}**")
        
    col_a_label, col_a_status = st.columns([0.8, 0.2])
    with col_a_label:
        file_a = st.file_uploader("Source File A (.xlsx or .xls)", type=['xlsx', 'xls'], key='file_a_uploader')
    with col_a_status:
        status_a = '✅' if st.session_state.get('file_a_uploader') else '⚠️'
        st.markdown(f"<div style='padding-top: 25px;'>{status_a}</div>", unsafe_allow_html=True)

    col_b_label, col_b_status = st.columns([0.8, 0.2])
    with col_b_label:
        file_b = st.file_uploader("Source File B (.xlsx or .xls)", type=['xlsx', 'xls'], key='file_b_uploader')
    with col_b_status:
        status_b = '✅' if st.session_state.get('file_b_uploader') else '⚠️'
        st.markdown(f"<div style='padding-top: 25px;'>{status_b}</div>", unsafe_allow_html=True)
        
    st.markdown("---") 
    
    # --- 2. Generate and Download Buttons (Side-by-Side) ---
    st.subheader("🚀 2. Report Generation")
    
    col_generate, col_download = st.columns([1, 1])

    with col_generate:
        button_clicked = st.button('Generate 4-Sheet Expense Report', key='main_generate_button', type="primary")

    with col_download:
        if st.session_state.get('report_bytes'):
            col_download.download_button(
                label="⬇️ Download Report",
                data=st.session_state.report_bytes,
                file_name=st.session_state.report_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key='download_report_button'
            )
        else:
            col_download.button('Report Not Ready', disabled=True, key='placeholder_button')

    st.markdown("---") 

    output_container = st.container()
    status_message = st.empty()
    
    # --- SIDEBAR ---
    st.sidebar.title("⚙️ Configuration")
    st.sidebar.caption("Keywords used to flag recurring transactions.")
    st.sidebar.markdown(f'**Recurring Keywords List:**')
    for keyword in RECURRING_KEYWORDS:
        st.sidebar.caption(f'- {keyword}')


    # --- PROCESSING AND GENERATION LOGIC ---
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
                    
                    with open(final_path, "rb") as f:
                        report_bytes = f.read()
                        
                    # Store data in Session State
                    st.session_state.report_bytes = report_bytes
                    st.session_state.report_filename = output_filename
                    st.session_state.combined_expenses_df = combined_expenses_df
                    st.session_state.pivot_summary_df = pivot_summary_df
                    st.session_state.df_a_cleaned = df_a_cleaned
                    st.session_state.df_b_cleaned = df_b_cleaned
                    
                    # CRITICAL: Set flag to display analysis section
                    st.session_state.report_ready = True
                    
                    status_message.success("Report generated successfully! Scroll down for analysis. The download button is now active above.")
            
            except Exception as e:
                # Clear session state flags on error
                if 'report_bytes' in st.session_state: del st.session_state.report_bytes
                if 'report_ready' in st.session_state: del st.session_state.report_ready
                
                st.exception(e) 
                status_message.error(f"An error occurred during processing. Please check the logs for details.")
                st.warning("Please ensure your files have exactly these 6 columns in order: **Transaction Date, Post Date, Description, Category, Type, Amount**.")
            # --- END PROCESSING ---
            
            # Rerun the app to update the page and display the analysis section
            st.rerun()

        else:
            # This runs if the button was clicked BUT one or both files are missing
            status_message.warning("Please upload both Source File A and Source File B.")

    # --- ANALYSIS DISPLAY LOGIC (RUNS ON EVERY RERUN IF REPORT_READY IS TRUE) ---
    if st.session_state.report_ready:
        
        # Retrieve data from session state
        combined_expenses_df = st.session_state.combined_expenses_df
        pivot_summary_df = st.session_state.pivot_summary_df
        df_a_cleaned = st.session_state.df_a_cleaned
        df_b_cleaned = st.session_state.df_b_cleaned
        
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
        chart_data = pivot_summary_df[pivot_summary_df['Category'] != '**Grand Total**'].copy()
        chart_data['Amount (Absolute)'] = chart_data['Total Amount'].abs()
        chart_data = chart_data.sort_values('Amount (Absolute)', ascending=False).head(10)
        output_container.bar_chart(chart_data.set_index('Category')['Amount (Absolute)'])

        output_container.markdown("---")

        # Row 3: Tabs for detailed data (st.tabs)
        tab1, tab2, tab3, tab4 = output_container.tabs([
            "Combined Expenses (Final)", "Category Summary", "Source A Raw", "Source B Raw"
        ])

        # Tab 1: Combined Expenses (10 Columns)
        tab1.subheader("Combined Expenses Data (10 Columns)")
        styled_df = combined_expenses_df.style.format({
            'Amount': '${:,.2f}',
            'Cumulative Sum': '${:,.2f}',
            '% of total': '{:.2%}',
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


if __name__ == '__main__':
    # Initialize session state flags and data stores
    if 'report_ready' not in st.session_state:
        st.session_state.report_ready = False
    if 'report_bytes' not in st.session_state:
        st.session_state.report_bytes = None
    if 'report_filename' not in st.session_state:
        st.session_state.report_filename = None
        
    main()
