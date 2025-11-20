import pandas as pd
import numpy as np
import streamlit as st
import tempfile
import os
import re

# --- UI Configuration (New) ---
st.set_page_config(
    layout="wide", # <-- Sets the wide layout
    page_title="💰 Financial Report Tool",
    icon="📊"
)

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

# --- Core Data Processing Functions (NO CHANGES HERE) ---
# ... (The rest of your clean_data, calculate_metrics, create_pivot_summary, and generate_report functions remain the same)
# ----------------------------------------------------------------------------------------------------------------------


# --- Streamlit Web App Interface (Updated main function) ---

def main():
    st.title('💰 Financial Data Processing Assistant')
    st.markdown('### Generate Your Comprehensive Expense Report')
    
    # --- File Upload Section (NEW UI) ---
    st.subheader("📁 1. Upload Transaction Files")
    st.write("Please upload both source files with the **6 required columns**.")
    
    # Use columns to place uploaders side-by-side
    col1, col2 = st.columns(2)
    
    with col1:
        file_a = st.file_uploader("Source File A (.xlsx or .xls)", type=['xlsx', 'xls'], key='file_a_uploader')

    with col2:
        file_b = st.file_uploader("Source File B (.xlsx or .xls)", type=['xlsx', 'xls'], key='file_b_uploader')
        
    st.markdown("---") # Visual separator

    # Create the button ONCE and store its click state
    button_clicked = st.button('🚀 2. Generate Report', key='main_generate_button', type="primary")

    # Status Message Container
    status_message = st.empty()
    
    # ... (The rest of your main function's processing logic goes here)
    # --------------------------------------------------------------------


    # NOTE: You MUST paste the remaining part of your original main() function 
    #       here to complete the script. (The part that handles the button_clicked 
    #       logic, exceptions, and the st.download_button).
    
    # I will provide the rest of the main() function below to ensure completeness!

# --------------------------------------------------------------------
# PASTE THIS REMAINING SECTION OF THE ORIGINAL CODE BELOW THE PART ABOVE
# --------------------------------------------------------------------

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
                        label="⬇️ Download Report (.xlsx)",
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
    # This ensures the entire script is run when streamlit calls main()
    # You must include all your functions (clean_data, calculate_metrics, etc.)
    # above this line, followed by the rest of the main() function logic.
    main()