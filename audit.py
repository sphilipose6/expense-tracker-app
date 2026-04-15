import pandas as pd
import os
from dotenv import load_dotenv
from simplefin_integration import SimpleFinConnector
from expense_tracker import ExpenseTracker

load_dotenv()

def find_ghosts():
    print("STARTING AUDIT...")
    
    # 1. Get data from the Bank
    print("   Fetching official bank records...")
    connector = SimpleFinConnector()
    # Fetch far enough back to cover whole sheet
    bank_df = connector.fetch_transactions(start_date_str='2025-09-16')
    
    # 2. Get the "Suspect" data from Google Sheets
    print("   Fetching Google Sheet records...")
    tracker = ExpenseTracker(os.getenv('SPREADSHEET_ID'))
    tracker.authenticate()
    sheet_df = tracker.read_transactions('Transaction Log!A:D')
    
    # 3. Standardize types for comparison
    # (Force amounts to be strings like '10.50' to avoid float rounding errors)
    bank_df['Amount_Str'] = bank_df['Amount'].round(2).astype(str)
    sheet_df['Amount_Str'] = pd.to_numeric(sheet_df['Amount'], errors='coerce').fillna(0.0).round(2).astype(str)
    
    # 4. Find rows in SHEET that are NOT in BANK
    # Merge with "indicator=True" to see where each row came from
    merged = sheet_df.merge(
        bank_df, 
        on=['Date', 'Amount_Str'], 
        how='left', 
        indicator=True,
        suffixes=('_Sheet', '_Bank')
    )
    
    # Filter for rows that are "Left_only" (In Sheet, but not in Bank)
    # Left dataframe is sheet_df, right dataframe is bank_df
    ghosts = merged[merged['_merge'] == 'left_only'] 
    
    print(f"\n FOUND {len(ghosts)} SUSPICIOUS TRANSACTIONS:")
    print("   (These exist in your Sheet, but the Bank doesn't have a matching Date+Amount)")
    print("-" * 60)
    
    if not ghosts.empty:
        print(ghosts[['Date', 'Description_Sheet', 'Amount_Str']])
        print("-" * 60)
        print("💡 TIP: These are likely duplicates with slightly different descriptions.")
        print("   Search for these dates in your sheet and delete the extra row.")
    else:
        print("No ghosts found! Your sheet matches the bank exactly by Date/Amount.")

if __name__ == "__main__":
    find_ghosts()