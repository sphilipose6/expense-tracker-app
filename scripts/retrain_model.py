import sys
import os
import pickle
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB

# Add src/ to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from expense_tracker import ExpenseTracker

load_dotenv()

# Project root (one level up from scripts/)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(ROOT_DIR, 'models', 'categorizer_model.pkl')

def retrain():
    print(" STARTING MODEL RETRAINING...")

    # 1. Fetch data from Google Sheets
    SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
    tracker = ExpenseTracker(SPREADSHEET_ID)
    tracker.authenticate()

    print("   Downloading corrected data from Google Sheets...")
    df = tracker.read_transactions('Transaction Log!A:D')

    if df is None or df.empty:
        print(" No data found in sheet to train on.")
        return

    # Clean the data
    df = df.dropna(subset=['Description', 'Category'])
    df = df[df['Category'] != '']

    if len(df) < 5:
        print(f"⚠ Not enough data yet ({len(df)} rows). Categorize more items first!")
        return

    # 2. Prepare Training Data / ML Pipeline
    X = df['Description']
    y = df['Category']

    # --- GET THE LIST OF UNIQUE CATEGORIES ---
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
        'categories': unique_categories
    }

    with open(MODEL_PATH, 'wb') as f: # wb because Pickle uses bytes
        pickle.dump(model_data, f)

    print(f" SUCCESS! New model saved to '{MODEL_PATH}'")

if __name__ == "__main__":
    retrain()
