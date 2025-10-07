import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier
from joblib import dump, load
import os
import random

MODEL_PATH = 'fraud_xgb_model.joblib'

def feature_engineer(data):
    """Converts raw transaction data into numerical features for the model."""
    
    method_map = {'vmb_transfer': 1, 'card_payment': 2, 'crypto': 3, 'digital_wallet': 4}
    
    # Ensure ALL output features are explicitly cast to float
    features = [
        float(data['account_number'][:4]), # Account prefix, cast to float
        float(data['amount']),             # Transaction amount, cast to float
        float(method_map.get(data['payment_method'], 0)), # Payment method ID, cast to float
        random.uniform(0.1, 0.9)           # SIMULATED: Device/Location Risk Score (already float)
    ]
    return features

def train_model(df):
    """Simulates training the fraud detection model."""
    
    X = df[['account_prefix', 'amount', 'method_id', 'device_risk']].values
    y = df['is_fraud'].values

    # Ensure X is of type float before passing to XGBoost
    if X.dtype != np.float32 and X.dtype != np.float64:
        X = X.astype(np.float32)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
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
        # Use floats for consistency
        'account_prefix': [float(random.randint(1000, 9999)) for _ in range(1000)],
        'amount': [random.uniform(10.0, 5000.0) for _ in range(1000)],
        'method_id': [float(random.randint(1, 4)) for _ in range(1000)],
        'device_risk': [random.uniform(0.1, 0.9) for _ in range(1000)],
        'is_fraud': [1 if random.random() < 0.05 else 0 for _ in range(1000)]
    }
    df = pd.DataFrame(data)
    
    return train_model(df)

def get_risk_score(transaction_data):
    """Predicts fraud risk using the loaded ML model."""
    model = initialize_or_load_model()
    
    features_list = feature_engineer(transaction_data)
    
    # Convert to NumPy array and explicitly set dtype to float32
    input_data = np.array([features_list], dtype=np.float32)

    # Predict the probability of the transaction being Fraud (class 1)
    risk_score = model.predict_proba(input_data)[:, 1][0]
    
    return float(risk_score)
