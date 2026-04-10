import os
import requests
import pandas as pd
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import traceback

# Load other modules
from categorizer_system import TransactionCategorizer
from expense_tracker import ExpenseTracker

# Load environment variables
load_dotenv()

class SimpleFinConnector:
    def __init__(self):
        self.access_url = os.getenv('SIMPLEFIN_URL')
        if not self.access_url:
            raise Exception(" Missing SIMPLEFIN_URL in .env file")
        
        # AUTO-FIX: Ensure URL ends in /accounts
        if not self.access_url.endswith('/accounts'):
            self.access_url = self.access_url.rstrip('/') + '/accounts'
            
    def fetch_transactions(self, start_date_str=None):
        """
        Fetches transactions from SimpleFin.
        start_date_str: 'YYYY-MM-DD' (Defaults to 90 days ago if None)
        """
        print(f" Fetching data from SimpleFin...")
        
        # 1. Prepare Parameters
        params = {}
        
        if start_date_str:
            dt = datetime.strptime(start_date_str, '%Y-%m-%d')
        else:
            # Default to 90 days ago if no date provided
            dt = datetime.now() - timedelta(days=90)
            
        # SimpleFin expects a Unix Timestamp (integer)
        params['start-date'] = int(dt.timestamp())
        print(f"   Requesting data starting from: {dt.strftime('%Y-%m-%d')}")

        # 2. Make Request
        try:
            response = requests.get(self.access_url, params=params)
            response.raise_for_status()
        except Exception as e:
            print(f" Error connecting to SimpleFin: {e}")
            return pd.DataFrame()

        data = response.json()
        
        # 3. Process the JSON
        all_txns = []
        
        # Check for empty accounts
        if not data.get('accounts'):
            print(" Connected, but no accounts returned. Check SimpleFin portal.")
            return pd.DataFrame()

        for account in data.get('accounts', []):
            bank_name = account.get('org', {}).get('name', 'Unknown Bank')
            acct_name = f"{bank_name} {account.get('name', 'Account')}"
            
            # Loop through transactions
            txns = account.get('transactions', [])
            print(f"  Found account: {acct_name} ({len(txns)} transactions)")
            
            for txn in txns:
                # Convert Unix timestamp to YYYY-MM-DD
                txn_date = datetime.fromtimestamp(int(txn['posted'])).strftime('%Y-%m-%d')
                
                all_txns.append({
                    'Date': txn_date,
                    'Description': txn['description'],
                    'Amount': float(txn['amount']), 
                    'Category': '',  # To be filled by ML
                    'Bank': acct_name
                })
        
        if not all_txns:
            print("ℹ No transactions found in the specified date range.")
            return pd.DataFrame(columns=['Date', 'Description', 'Amount', 'Category', 'Bank'])
            
        # Create DataFrame
        df = pd.DataFrame(all_txns)
        # Sort by date (newest first)
        df = df.sort_values('Date', ascending=False)
        
        print(f" Retrieved {len(df)} transactions total")
        return df

# Main Execution Flow
if __name__ == "__main__":
    print("="*60)
    print("EXPENSE TRACKER - SIMPLEFIN INTEGRATION")
    print("="*60)
    
    # --- STEP 1: FETCH DATA ---
    connector = SimpleFinConnector()
    # Fetch data starting from Fincance Chair Induction Date
    transactions = connector.fetch_transactions(start_date_str='2025-09-16')
    
    if transactions.empty:
        print("Exiting...")
        exit()
        
    print("\nFirst few transactions found:")
    print(transactions[['Date', 'Description', 'Amount']].head())
    
    # --- STEP 2: CATEGORIZE ---
    print("\n" + "="*60)
    print("CATEGORIZING TRANSACTIONS")
    print("="*60)
    
    categorizer = TransactionCategorizer()
    if not categorizer.load_model():
        print(" No trained model found. Running simple rules only.")
    
    for idx, row in transactions.iterrows():
        category = categorizer.predict(row['Amount'], row['Description'])
        transactions.at[idx, 'Category'] = category
        
    print(f" Categorized {len(transactions)} items")
    
    # --- STEP 3: UPDATE GOOGLE SHEETS ---
    print("\n" + "="*60)
    print("UPDATING GOOGLE SHEETS")
    print("="*60)
    
    SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
    if not SPREADSHEET_ID:
        print(" Error: SPREADSHEET_ID not found in .env")
        exit()
        
    tracker = ExpenseTracker(SPREADSHEET_ID)
    
    try:
        tracker.authenticate()
        
        # 1. Read existing data
        existing = tracker.read_transactions('Transaction Log!A:D')
        
        # --- HELPER FUNCTION: CLEAN & STANDARDIZE ---
        def clean_data(df):
            if df is None or df.empty:
                return pd.DataFrame(columns=['Date', 'Description', 'Amount', 'Category'])
            
            df = df.copy()
            
            # A. Standardize Date to String "YYYY-MM-DD"
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
            
            # B. Standardize Amount (Round to 2 decimals)
            df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0.0)
            df['Amount'] = df['Amount'].round(2)
            
            # C. Clean Description (Remove trailing spaces)
            df['Description'] = df['Description'].astype(str).str.strip()
            
            return df

        # Clean both datasets
        existing_clean = clean_data(existing)
        new_data_clean = clean_data(transactions[['Date', 'Description', 'Amount', 'Category']])
        
        # 3. Combine and Deduplicate
        if not existing_clean.empty:
            combined = pd.concat([existing_clean, new_data_clean], ignore_index=True)
            # Deduplicate based on Date, Description, Amount
            combined = combined.drop_duplicates(subset=['Date', 'Description', 'Amount'], keep='first')
        else:
            combined = new_data_clean
            
        # 4. Final Formatting for Upload
        # Remove any invalid dates
        combined = combined.dropna(subset=['Date'])
        
        # Ensure correct column order
        combined = combined[['Date', 'Description', 'Amount', 'Category']]
        
        # Replace NaN with empty string to prevent JSON errors
        combined = combined.fillna('')
        
        print(f"\nWriting {len(combined)} rows to Google Sheets...")
        
        # Write to sheets
        tracker.write_transactions(combined, 'Transaction Log!A1')
        print(" Google Sheet Updated Successfully!")
            
    except Exception as e:
        print(f" UPDATE FAILED: {e}")
        traceback.print_exc()