import os
import pandas as pd
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

# Google Sheets API scope - what permissions we need
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

class ExpenseTracker:
    def __init__(self, spreadsheet_id):
        """
        Initialize the expense tracker
        
        Args:
            spreadsheet_id: The ID from your Google Sheets URL
                           (the long string between /d/ and /edit)
        """
        self.spreadsheet_id = spreadsheet_id
        self.service = None
        
    def authenticate(self):
        """
        Authenticate with Google Sheets API
        
        This will:
        1. Check if we have saved credentials (token.pickle)
        2. If not, open a browser for you to login
        3. Save credentials for future use
        """
        creds = None
        
        # Check if we already have credentials saved
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # This requires 'credentials.json' file from Google Cloud
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next time
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        
        # Build the service object for interacting with Google Sheets
        self.service = build('sheets', 'v4', credentials=creds)
        print("✓ Successfully authenticated with Google Sheets")
    
    def read_transactions(self, range_name='Sheet1!A:E'):
        """
        Read transaction data from Google Sheets
        
        Args:
            range_name: The range to read (e.g., 'Sheet1!A:E' means columns A-E)
        
        Returns:
            pandas DataFrame with your transaction data
        """
        if not self.service:
            raise Exception("Must authenticate first!")
        
        # Call the Sheets API
        sheet = self.service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range=range_name
        ).execute()
        
        # Get the values
        values = result.get('values', [])
        
        if not values:
            print('No data found.')
            return None
        
        # Convert to pandas DataFrame (easier to work with)
        # First row is headers, rest is data
        df = pd.DataFrame(values[1:], columns=values[0])
        print(f"✓ Read {len(df)} transactions from Google Sheets")
        
        return df
    
    def write_transactions(self, df, range_name='Sheet1!A1'):
        """
        Write transaction data back to Google Sheets
        
        Args:
            df: pandas DataFrame with your data
            range_name: Where to start writing
        """
        if not self.service:
            raise Exception("Must authenticate first!")
        
        # Convert DataFrame to list of lists (what Sheets API expects)
        values = [df.columns.tolist()] + df.values.tolist()
        
        body = {
            'values': values
        }
        
        # Update the sheet
        result = self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        print(f"✓ Updated {result.get('updatedCells')} cells")


# Example usage
if __name__ == "__main__":
    # STEP 1: Replace this with your actual spreadsheet ID
    # Find it in your Google Sheets URL:
    # https://docs.google.com/spreadsheets/d/YOUR_SPREADSHEET_ID/edit
    SPREADSHEET_ID = "1eedF-Y4fgOzbA3tpQaT3VT_W54iZbUjVLZXbyOwx_TU"
    
    # Create tracker instance
    tracker = ExpenseTracker(SPREADSHEET_ID)
    
    # Authenticate (first time will open browser)
    tracker.authenticate()
    
    # Read your existing data
    # Adjust the range to match your sheet structure
    # Format: 'SheetName!StartColumn:EndColumn'
    df = tracker.read_transactions('Transaction Log!A:D')
    
    if df is not None:
        print("\nFirst few rows of your data:")
        print(df.head())
        
        # Show what columns you have
        print("\nYour columns:", df.columns.tolist())