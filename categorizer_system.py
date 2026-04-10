import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import train_test_split
import pickle
import re

class TransactionCategorizer:
    """
    Hybrid categorization system that combines rules and machine learning
    """
    
    def __init__(self):
        # Categories
        self.categories = [
            'Travel',
            'Hotels', 
            'Competition Fees',
            'Production Fees',
            'Miscellaneous',
            'Income'
        ]
        
        # ML components
        self.vectorizer = TfidfVectorizer(
            max_features=100,  # Use top 100 most important words
            ngram_range=(1, 2),  # Use single words and two-word phrases
            lowercase=True
        )
        self.model = MultinomialNB()
        self.is_trained = False
        
    def clean_description(self, description):
        """
        Clean up transaction descriptions for better matching
        
        Args:
            description: Raw merchant/transaction description
            
        Returns:
            Cleaned description string
        """
        if pd.isna(description):
            return ""
        
        # Convert to string and lowercase
        text = str(description).lower()
        
        # Remove special characters but keep spaces
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text
    
    def apply_rules(self, amount, description):
        """
        Apply rule-based categorization
        
        Rule 1: Positive amount = Income
        Rule 2-4: Keyword matching for Travel, Hotels, Production Fees
        
        Args:
            amount: Transaction amount
            description: Transaction description
            
        Returns:
            Category name if rule matches, None otherwise
        """
        # Convert amount to float, handling different formats
        try:
            amount_float = float(str(amount).replace('$', '').replace(',', ''))
        except:
            amount_float = 0
        
        # Rule 1: Positive amounts are income
        if amount_float > 0:
            return 'Income'
        
        # Convert description to lowercase for matching
        desc_lower = str(description).lower()
        
        # Rule 2: Travel keywords
        travel_keywords = [
            'airline', 'airlines', 'flight', 'airport', 'uber', 'lyft',
            'taxi', 'rental car', 'car rental', 'hertz', 'enterprise',
            'avis', 'budget', 'southwest', 'delta', 'united', 'american airlines',
            'jetblue', 'spirit', 'frontier', 'tsa', 'parking airport'
        ]
        if any(keyword in desc_lower for keyword in travel_keywords):
            return 'Travel'
        
        # Rule 3: Hotel keywords
        hotel_keywords = [
            'hotel', 'inn', 'resort', 'marriott', 'hilton', 'hyatt',
            'holiday inn', 'best western', 'comfort inn', 'motel',
            'airbnb', 'vrbo', 'booking.com', 'hotels.com', 'expedia hotel',
            'hampton inn', 'courtyard', 'residence inn', 'sheraton'
        ]
        if any(keyword in desc_lower for keyword in hotel_keywords):
            return 'Hotels'
        
        # Rule 4: Production Fee keywords
        production_keywords = [
            'production', 'studio', 'recording', 'mixing', 'mastering',
            'equipment rental', 'camera rental', 'lighting rental',
            'sound equipment', 'video production', 'editing service',
            'post production', 'film', 'filming'
        ]
        if any(keyword in desc_lower for keyword in production_keywords):
            return 'Production Fees'
        
        return None  # No rule matched
    
    def train(self, df):
        """
        Train the ML model on historical data
        
        Args:
            df: DataFrame with columns ['Description', 'Amount', 'Category']
        """
        # Make a copy to avoid modifying original
        train_data = df.copy()
        
        # Remove rows with missing categories or descriptions
        train_data = train_data.dropna(subset=['Description', 'Category'])
        
        # Only train on non-income transactions (since income is rule-based)
        train_data = train_data[train_data['Category'] != 'Income']
        
        if len(train_data) < 10:
            print("⚠ Warning: Less than 10 non-income transactions to learn from.")
            print("  The categorizer will rely mostly on rules.")
            return
        
        # Clean descriptions
        train_data['CleanDescription'] = train_data['Description'].apply(
            self.clean_description
        )
        
        # Prepare features (X) and labels (y)
        X = train_data['CleanDescription']
        y = train_data['Category']
        
        # Transform text to numbers using TF-IDF
        X_vectorized = self.vectorizer.fit_transform(X)
        
        # Train the model
        self.model.fit(X_vectorized, y)
        self.is_trained = True
        
        # Calculate and show accuracy
        predictions = self.model.predict(X_vectorized)
        accuracy = (predictions == y).sum() / len(y)
        
        print(f"✓ Model trained on {len(train_data)} transactions")
        print(f"✓ Training accuracy: {accuracy*100:.1f}%")
        
        # Show what the model learned
        self._show_learning_summary(train_data)
    
    def _show_learning_summary(self, train_data):
        """Show what patterns the model found"""
        print("\n Learning Summary:")
        print("-" * 50)
        
        category_counts = train_data['Category'].value_counts()
        for category, count in category_counts.items():
            print(f"  {category}: {count} examples")
        
        print("\n Top words learned for each category:")
        
        # Get feature names (words)
        feature_names = self.vectorizer.get_feature_names_out()
        
        for idx, category in enumerate(self.model.classes_):
            # Get word importance scores for this category
            feature_scores = self.model.feature_log_prob_[idx]
            
            # Get top 5 words
            top_indices = feature_scores.argsort()[-5:][::-1]
            top_words = [feature_names[i] for i in top_indices]
            
            print(f"  {category}: {', '.join(top_words)}")
    
    def predict(self, amount, description):
        """
        Predict category for a transaction
        
        Args:
            amount: Transaction amount
            description: Transaction description
            
        Returns:
            Predicted category name
        """
        # First, try rule-based categorization
        rule_category = self.apply_rules(amount, description)
        if rule_category:
            return rule_category
        
        # If no rule matched, use ML model
        if not self.is_trained:
            return 'Miscellaneous'  # Default if model not trained
        
        # Clean and vectorize the description
        clean_desc = self.clean_description(description)
        desc_vectorized = self.vectorizer.transform([clean_desc])
        
        # Get prediction and confidence
        prediction = self.model.predict(desc_vectorized)[0]
        probabilities = self.model.predict_proba(desc_vectorized)[0]
        confidence = probabilities.max()
        
        # If confidence is too low, mark as Miscellaneous
        if confidence < 0.3:  # Less than 30% confident
            return 'Miscellaneous'
        
        return prediction
    
    def categorize_transactions(self, df):
        """
        Categorize all transactions in a DataFrame
        
        Args:
            df: DataFrame with 'Description' and 'Amount' columns
            
        Returns:
            DataFrame with added 'PredictedCategory' and 'Confidence' columns
        """
        result = df.copy()
        
        predictions = []
        confidences = []
        
        for _, row in df.iterrows():
            # Get prediction
            pred = self.predict(row['Amount'], row['Description'])
            predictions.append(pred)
            
            # Calculate confidence
            if self.apply_rules(row['Amount'], row['Description']):
                confidences.append('Rule-based')
            else:
                clean_desc = self.clean_description(row['Description'])
                if self.is_trained and clean_desc:
                    desc_vectorized = self.vectorizer.transform([clean_desc])
                    probs = self.model.predict_proba(desc_vectorized)[0]
                    confidences.append(f"{probs.max()*100:.0f}%")
                else:
                    confidences.append('Default')
        
        result['PredictedCategory'] = predictions
        result['Confidence'] = confidences
        
        return result
    
    def save_model(self, filepath='categorizer_model.pkl'):
        """Save the trained model to disk"""
        if not self.is_trained:
            print("⚠ Model not trained yet, nothing to save")
            return
        
        model_data = {
            'vectorizer': self.vectorizer,
            'model': self.model,
            'categories': self.categories
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f" Model saved to {filepath}")
    
    def load_model(self, filepath='categorizer_model.pkl'):
        """Load a previously trained model"""
        try:
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
            
            self.vectorizer = model_data['vectorizer']
            self.model = model_data['model']
            self.categories = model_data['categories']
            self.is_trained = True
            
            print(f" Model loaded from {filepath}")
            return True
        except FileNotFoundError:
            print(f" No saved model found at {filepath}")
            return False