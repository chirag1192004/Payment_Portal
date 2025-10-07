import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier # Machine Learning Model
from joblib import dump, load
import os
import random

MODEL_PATH = 'fraud_xgb_model.joblib'
# --- DL Placeholder: For true DL, you would use TensorFlow/Keras here. ---
# from tensorflow.keras.models import Sequential
# from tensorflow.keras.layers import Dense

def feature_engineer(data):
    """Converts raw transaction data into numerical features for the model."""
    
    # 1. Feature Mapping (Convert categorical to numerical)
    method_map = {'vmb_transfer': 1, 'card_payment': 2, 'crypto': 3, 'digital_wallet': 4}
    
    # 2. Extract Features
    features = [
        int(data['account_number'][:4]), # Account prefix (first 4 digits)
        data['amount'],                  # Transaction amount
        method_map.get(data['payment_method'], 0), # Payment method ID
        random.uniform(0.1, 0.9)         # SIMULATED: Device/Location Risk Score
        # A real system adds 100s of features: time diff, velocity, merchant type, etc.
    ]
    return features

def train_model(df):
    """Trains the XGBoost model on historical data (simulated)."""
    
    # Features (X): 4 numerical features from feature_engineer
    # Label (y): is_fraud (0 or 1)
    X = df[['account_prefix', 'amount', 'method_id', 'device_risk']].values
    y = df['is_fraud'].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # ML Model: XGBoost for efficient classification
    model = XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42)
    model.fit(X_train, y_train)
    
    dump(model, MODEL_PATH)
    print("Model trained and saved.")
    return model

def initialize_or_load_model():
    """Initializes the model, creating dummy data if it doesn't exist."""
    if os.path.exists(MODEL_PATH):
        return load(MODEL_PATH)
    
    print("ML Model file not found. Generating dummy training data...")
    # Generate 1000 dummy transactions for training
    data = {
        'account_prefix': [random.randint(1000, 9999) for _ in range(1000)],
        'amount': [random.uniform(10, 5000) for _ in range(1000)],
        'method_id': [random.randint(1, 4) for _ in range(1000)],
        'device_risk': [random.uniform(0.1, 0.9) for _ in range(1000)],
        'is_fraud': [1 if random.random() < 0.05 else 0 for _ in range(1000)] # 5% fraud rate
    }
    df = pd.DataFrame(data)
    
    return train_model(df)

def get_risk_score(transaction_data):
    """Predicts fraud risk using the loaded ML model."""
    model = initialize_or_load_model()
    
    features_list = feature_engineer(transaction_data)
    
    # Convert to numpy array for model prediction
    input_data = np.array([features_list])

    # Predict the probability of the transaction being Fraud (class 1)
    risk_score = model.predict_proba(input_data)[:, 1][0]
    
    return float(risk_score)