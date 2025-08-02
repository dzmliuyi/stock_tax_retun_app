import streamlit as st
from data_processor import DataProcessor
from file_manager import FileManager

st.set_page_config(
    page_title="Stock Tax Return Calculator",
    page_icon="📊",
    layout="wide"
)

def main():
    st.title("Stock Tax Return Calculator")
    
    # Broker selection
    broker = st.selectbox(
        "Select your broker",
        ["stake", "webull"],
        help="Choose your broker to ensure correct processing of the CSV format"
    )
    
    # File upload section
    st.header("Upload Trading Data")
    uploaded_files = st.file_uploader(
        f"Upload your {broker} trading data (CSV files)",
        type=["csv"],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        file_manager = FileManager()
        data_processor = DataProcessor()
        
        # Process each uploaded file
        for uploaded_file in uploaded_files:
            if file_manager.validate_file(uploaded_file, broker):
                df = file_manager.read_file(uploaded_file, broker)
                if df is not None:
                    processed_data = data_processor.process_data(df)
                    
                    # Display summary
                    st.header(f"Summary for {uploaded_file.name}")
                    st.write(processed_data['summary'])
                    
                    # Display detailed breakdown
                    st.subheader("Detailed Breakdown by Stock")
                    st.write(processed_data['details'])
            else:
                st.error(f"Invalid file format: {uploaded_file.name}")
    
    else:
        st.info("Please upload your trading data Excel files to begin.")

if __name__ == "__main__":
    main()
