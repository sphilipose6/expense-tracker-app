import pandas as pd
import os
import pickle
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from expense_tracker import ExpenseTracker

# Load environment variables
load_dotenv()

def retrain():
    print("🧠 STARTING MODEL RETRAINING...")
    
    # 1. Fetch the "Ground Truth" from Google Sheets
    SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
    tracker = ExpenseTracker(SPREADSHEET_ID)
    tracker.authenticate()
    
    print("   Downloading corrected data from Google Sheets...")
    df = tracker.read_transactions('Transaction Log!A:D')
    
    if df is None or df.empty:
        print("❌ No data found in sheet to train on.")
        return

    # Clean the data
    df = df.dropna(subset=['Description', 'Category'])
    df = df[df['Category'] != ''] 
    
    if len(df) < 5:
        print(f"⚠ Not enough data yet ({len(df)} rows). Categorize more items first!")
        return

    # 2. Prepare Training Data
    X = df['Description']
    y = df['Category']
    
    # --- FIX: GET THE LIST OF UNIQUE CATEGORIES ---
    unique_categories = y.unique().tolist()
    
    print(f"   Training on {len(df)} examples with {len(unique_categories)} categories...")
    
    # 3. Train the parts SEPARATELY
    # Part A: The Translator (Text -> Numbers)
    vectorizer = TfidfVectorizer()
    X_vectors = vectorizer.fit_transform(X)
    
    # Part B: The Brain (Numbers -> Category)
    classifier = MultinomialNB()
    classifier.fit(X_vectors, y)
    
    # 4. Save as a DICTIONARY with ALL required keys
    model_data = {
        'vectorizer': vectorizer,
        'model': classifier,
        'categories': unique_categories  # <--- THIS WAS THE MISSING KEY
    }
    
    with open('categorizer_model.pkl', 'wb') as f:
        pickle.dump(model_data, f)
        
    print("✅ SUCCESS! New model saved to 'categorizer_model.pkl'")

if __name__ == "__main__":
    retrain()