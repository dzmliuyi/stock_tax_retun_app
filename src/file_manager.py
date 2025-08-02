import pandas as pd
from datetime import datetime
import re
import streamlit as st

class FileManager:
    def __init__(self):
        # Standard column names (based on Stake format)
        self.standard_columns = [
            'Trade Date', 'Settlement Date', 'Symbol', 'Side',
            'Trade Identifier', 'Units', 'Avg. Price', 'Value',
            'Fees', 'GST', 'Total Value', 'Currency', 'AUD/USD rate'
        ]
        
        self.column_mappings = {
            'stake': {
                'required_columns': self.standard_columns,
                'column_map': {}  # No mapping needed as it's our standard format
            },
            'webull': {
                'required_columns': [
                    'Symbol&Name', 'Trade Date', 'Settlement Date', 'Buy/Sell',
                    'Quantity', 'Trade Price', 'Gross Amount', 'Net Amount',
                    'Comm/Fee/Tax', 'GST'
                ],
                'column_map': {
                    'Symbol&Name': 'Symbol',
                    'Buy/Sell': 'Side',
                    'Quantity': 'Units',
                    'Trade Price': 'Avg. Price',
                    'Gross Amount': 'Value',
                    'Net Amount': 'Total Value',
                    'Comm/Fee/Tax': 'Fees'
                }
            }
        }
    
    def validate_file(self, file, broker):
        """Validate the uploaded file name and structure."""
        try:
            # # Validate filename pattern
            # if broker == "stake":
            #     pattern = r'stake_FY\d{2}_\d{2}\.csv$'
            #     if not re.match(pattern, file.name):
            #         st.warning(f"File name {file.name} does not match the expected pattern stake_FYXX_YY.csv")
            #         return False
            # elif broker == "webull":
            #     pattern = r'Webull_EOFY_Statement_\d{4}_\d{4}\.csv$'
            #     if not re.match(pattern, file.name):
            #         st.warning(f"File name {file.name} does not match the expected pattern Webull_EOFY_Statement_XXXX_YYYY.csv")
            #         return False

            # Reset file pointer to beginning
            file.seek(0)
            
            # Read CSV file
            if broker == 'stake':
                df = pd.read_csv(file)
            elif broker == 'webull':
                df = pd.read_csv(file, encoding='cp1252')
            
            # Check if DataFrame is empty
            if df.empty:
                st.warning("The uploaded file is empty")
                return False
            
            # Get required columns for the specific broker
            required_columns = self.column_mappings.get(broker, {}).get('required_columns', [])
            if not required_columns:
                st.warning(f"Unsupported broker: {broker}")
                return False
                
            # Check if all required columns are present
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                st.warning(f"Missing required columns for {broker}: {', '.join(missing_columns)}")
                return False
            
            # Basic data validation
            st.write(f"Found {len(df)} rows of data")
            
            return True
            
        except pd.errors.EmptyDataError:
            st.warning("The uploaded file is empty")
            return False
        except Exception as e:
            st.warning(f"Error reading CSV file: {str(e)}")
            return False
    
    def read_file(self, file, broker):
        """Read and return the CSV file data as a pandas DataFrame."""
        try:
            # Reset file pointer to beginning
            file.seek(0)
            
            # Read CSV file
            if broker == 'stake':
                df = pd.read_csv(file)
            elif broker == 'webull':
                df = pd.read_csv(file, encoding='cp1252')

            # Apply column mapping based on broker
            column_map = self.column_mappings[broker]['column_map']
            if column_map:
                df = df.rename(columns=column_map)
            
            # Handle broker-specific data transformations
            if broker == 'stake':
                # Convert date columns to datetime (already in YYYY-MM-DD format)
                df['Trade Date'] = pd.to_datetime(df['Trade Date'])
                df['Settlement Date'] = pd.to_datetime(df['Settlement Date'])
                # Clean and convert AUD/USD rate (remove $ prefix)
                df['AUD/USD rate'] = df['AUD/USD rate'].str.replace('$', '').astype(float)
            elif broker == 'webull':
                # Convert date columns from DD/MM/YYYY to YYYY-MM-DD
                df['Trade Date'] = pd.to_datetime(df['Trade Date'], format='%d/%m/%Y')
                df['Settlement Date'] = pd.to_datetime(df['Settlement Date'], format='%d/%m/%Y')
                
                # Standardize Side values from BUY/SELL to Buy/Sell
                df['Side'] = df['Side'].str.title()

                # Fill NaN values in GST column with 0
                df['GST'] = df['GST'].fillna(0)
                
                # Add missing columns with default values
                if 'Currency' not in df:
                    df['Currency'] = 'USD'  # Assuming Webull trades are in USD
                if 'AUD/USD rate' not in df:
                    df['AUD/USD rate'] = 1.55  # Using constant exchange rate for Webull trades
                if 'Trade Identifier' not in df:
                    df['Trade Identifier'] = df.index  # Use index as Trade Identifier
            
            # Ensure numeric columns are properly typed
            numeric_columns = ['Units', 'Avg. Price', 'Value', 'Fees', 'GST', 'Total Value']
            for col in numeric_columns:
                if col in df.columns:
                    # Remove any currency symbols and spaces
                    if df[col].dtype == object:
                        # Remove commas, spaces, and handle negative values properly
                        df[col] = df[col].replace({',': '', ' ': ''}, regex=True)
                        # Convert to float and make absolute values to match Stake's format
                        df[col] = pd.to_numeric(df[col].str.replace('$', ''), errors='coerce').abs()
            
            # # Verify data conversion
            # st.write("\nData types after conversion:")
            # for col in df.columns:
            #     st.write(f"{col}: {df[col].dtype}")
            
            # Check for any NaN values
            nan_counts = df.isna().sum()
            if nan_counts.any():
                st.warning("Found NaN values in the following columns:")
                for col, count in nan_counts[nan_counts > 0].items():
                    st.warning(f"{col}: {count} NaN values")
            
            return df
            
        except Exception as e:
            st.error(f"Error reading file {file.name}: {str(e)}")
            st.error("Please ensure the file is a valid CSV file with the correct format")
            return None