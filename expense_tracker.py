import os
import pandas as pd
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

# Google Sheets API scope
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

class ExpenseTracker:
    def __init__(self, spreadsheet_id):
        """
        Initialize the expense tracker
        
        Args:
            spreadsheet_id: The ID from Google Sheets URL
                           (the long string between /d/ and /edit)
        """
        self.spreadsheet_id = spreadsheet_id
        self.service = None # Intentionally set to None until we authenticate
        
    def authenticate(self):
        """
        Authenticate with Google Sheets API
        
        This will:
        1. Check if we have saved credentials (token.pickle)
        2. If not, open a browser for login
        3. Save credentials for future use
        """
        creds = None
        
        # Check if existing credentials saved, State 1: load saved creds
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token) # State 1: load saved creds
        
        # If no valid credentials, get new ones 
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request()) # State 2: refresh or login
            else:
                # 'credentials.json' file from Google Cloud
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0) # State 3: browser login, port 0 allows all free ports
            
            # Save credentials for next time
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        
        # Build the service object for interacting with Google Sheets
        self.service = build('sheets', 'v4', credentials=creds)
        print(" Successfully authenticated with Google Sheets")
    
    def read_transactions(self, range_name='Sheet1!A:E'):
        """
        Read transaction data from Google Sheets
        
        Args:
            range_name: The range to read (e.g., 'Sheet1!A:E' means columns A-E)
        
        Returns:
            pandas DataFrame with transaction data
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
        df = pd.DataFrame(values[1:], columns=values[0]) # Header Row = column names, Data Rows = values[1:]
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
        
        print(f" Updated {result.get('updatedCells')} cells")
