import pandas as pd
import numpy as np
import streamlit as st
import tempfile
import os
import re # Added for robust text matching

# --- Configuration ---
# 1. RECURRING KEYWORDS: FINAL list verified against all your provided samples.
RECURRING_KEYWORDS = [
    'SMALL WORL',
    'Goldfish Swim School',
    'SCHOOL OF MUSIC',      
    'T-MOBILE*AUTO PAY', 
    'NOETIC MATH',
    'FuboTV Inc',
    'OSRX',                 # Added OSRX
    'SIMPLISAFE',
    'APPLE.COM/BILL',
    'HULUPULS',             
    'AMAZON PRIME',         
    'AMAZON.COM RING PROTECT',
    'PANERA SIP CLUB',      
    'Supercuts',
    'BAY CLUB'              # Added BAY CLUB
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
        '%\ of Grand Total': summary_df['% of Grand Total'].sum()
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


# --- Streamlit Web App Interface ---

def main():
    st.title('💰 Financial Data Processing Assistant')
    st.markdown('### Upload Financial Transaction Files')
    st.markdown('This tool merges, filters, and analyzes two Excel transaction files to generate a comprehensive expense report.')

    # File Uploaders
    file_a = st.file_uploader("Upload Source File A (.xlsx or .xls)", type=['xlsx', 'xls'], key='file_a_uploader')
    file_b = st.file_uploader("Upload Source File B (.xlsx or .xls)", type=['xlsx', 'xls'], key='file_b_uploader')

    # Create the button ONCE and store its click state
    button_clicked = st.button('Generate Report', key='main_generate_button')

    # Status Message Container
    status_message = st.empty()

    # Conditional structure for processing
    if button_clicked:
        if file_a is not None and file_b is not None:
            # --- START PROCESSING ---
            try:
                status_message.info("Processing files... this may take a moment.")
                
                # Use tempfile to securely handle the uploaded files
                with tempfile.TemporaryDirectory() as temp_dir:
                    path_a = os.path.join(temp_dir, file_a.name)
                    path_b = os.path.join(temp_dir, file_b.name)
                    
                    # Write uploaded bytes to temp files
                    with open(path_a, "wb") as f:
                        f.write(file_a.getvalue())
                    with open(path_b, "wb") as f:
                        f.write(file_b.getvalue())

                    output_filename = 'Financial_Data_Report_Output.xlsx'
                    output_path = os.path.join(temp_dir, output_filename)
                    
                    # CALL THE CORE PROCESSING FUNCTION
                    generate_report(path_a, path_b, output_path)

                    # Read the generated report file into memory
                    with open(output_path, "rb") as f:
                        report_bytes = f.read()

                    status_message.success("Report generated successfully! Download below.")
                    
                    # Download button
                    st.download_button(
                        label="Download Report",
                        data=report_bytes,
                        file_name=output_filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key='download_report_button'
                    )

            except Exception as e:
                # Display user-friendly error and log details to console
                st.exception(e) 
                status_message.error(f"An error occurred during processing. Please check the logs (PowerShell window) for details.")
                st.warning("Please ensure your files have exactly these 6 columns in order: **Transaction Date, Post Date, Description, Category, Type, Amount**.")
            # --- END PROCESSING ---

        else:
            # This runs if the button was clicked BUT one or both files are missing
            status_message.warning("Please upload both Source File A and Source File B.")

    st.markdown('---')
    st.caption(f'**Recurring Keywords List (Edit in code):** {", ".join(RECURRING_KEYWORDS)}') 

if __name__ == '__main__':
    main()