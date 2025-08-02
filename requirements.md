# Stock Tax Return Calculator - Requirements Document

## Project Overview
A Streamlit application to calculate capital gains and losses for stock trades across different financial years.

## Data Input
- Excel files with naming convention: `stake_FY{YY}_{YY+1}.xlsx`
- Data located in "Wall St Equities" sheet
- Required columns:
  - Trade Date
  - Settlement Date
  - Symbol
  - Side (Buy/Sell)
  - Trade Identifier
  - Units
  - Avg. Price
  - Value
  - Fees
  - GST
  - Total Value
  - Currency
  - AUD/USD rate

## Functional Requirements

### 1. File Management
- Allow users to upload Excel files
- Support multiple files for different financial years
- Validate file naming convention and data structure

### 2. Data Processing
- Parse Excel files
- Group transactions by financial year
- Match buy and sell transactions for each stock
- Calculate holding period for CGT discount eligibility

### 3. Capital Gains/Losses Calculation
- Calculate cost base in AUD for purchases
  - Include purchase price
  - Include acquisition costs (fees)
  - Convert using AUD/USD rate at purchase date
- Calculate capital proceeds in AUD for sales
  - Include sale price
  - Include disposal costs (fees)
  - Convert using AUD/USD rate at sale date
- Apply CGT discount (50%) for assets held > 12 months
- Track capital losses for carry-forward calculations

### 4. Reporting Features
- Display summary by financial year
  - Total capital gains
  - Total capital losses
  - Net position
  - Available carried forward losses
- Provide detailed breakdown by stock
- Export capabilities for tax reporting

## Technical Requirements

### 1. Core Technologies
- Python
- Streamlit
- Pandas for data manipulation
- OpenPyXL for Excel file handling

### 2. Data Validation
- File format validation
- Data completeness checks
- Currency conversion verification

### 3. Error Handling
- Clear error messages for invalid files
- Handling of missing data
- Currency conversion failures

## Future Enhancements
- Support for additional brokers
- PDF report generation
- Historical exchange rate API integration
- Tax optimization suggestions
