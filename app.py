from flask import Flask, request, jsonify, render_template, redirect, url_for, make_response
from flask_cors import CORS
import sqlite3
import datetime
import uuid
from fraud_model import get_risk_score, initialize_or_load_model
import numpy as np 

# --- FLASK SETUP ---
app = Flask(__name__)
CORS(app) # Enable CORS for development

RISK_THRESHOLD_DENY = 0.8  # Deny if risk is very high
RISK_THRESHOLD_FLAG = 0.4  # Flag for review if risk is medium

def get_db_connection():
    # Helper function to connect to SQLite DB
    conn = sqlite3.connect('vmb_gateway.db')
    conn.row_factory = sqlite3.Row
    return conn

# Initialize the model on startup
try:
    initialize_or_load_model()
except Exception as e:
    print(f"FATAL: Could not initialize ML model. Check dependencies and fraud_model.py. Error: {e}")

# --- USER PORTAL ENDPOINTS ---

@app.route('/')
def user_portal():
    return render_template('user_payment.html')

@app.route('/api/process_payment', methods=['POST'])
def process_payment():
    data = request.json
    
    # 1. Basic Validation
    required_fields = ['account_number', 'amount', 'security_pin', 'payment_method']
    if not all(field in data for field in required_fields):
        return jsonify({"status": "error", "message": "Missing required transaction data."}), 400

    account_number = data['account_number']
    
    # --- FIX: Ensure amount is a clean float immediately ---
    try:
        amount = float(data['amount'])
    except ValueError:
        return jsonify({"status": "error", "message": "Transaction amount must be a number."}), 400
    # --- End of FIX ---

    # 2. ML Integration: Get the risk score
    try:
        risk_score = get_risk_score(data)
    except Exception as e:
        # Catching the ML error here and logging it instead of crashing the API
        print(f"ML Model Error during scoring: {e}")
        return jsonify({"status": "error", "message": "Internal ML processing error. Cannot assess risk."}), 500
    
    # 3. Decision Logic (ML/Risk-Based)
    transaction_status = "Approved"
    rejection_reason = None
    
    if risk_score >= RISK_THRESHOLD_DENY:
        transaction_status = "Denied"
        rejection_reason = "High Fraud Risk Detected (Score: {:.2f})".format(risk_score)
    elif risk_score >= RISK_THRESHOLD_FLAG:
        transaction_status = "Flagged"
        print(f"TRANSACTION FLAGGED: Risk {risk_score:.4f}. Requires Banker Review.")

    # 4. Core Banking Simulation (Fund Check & Debit)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    account = cursor.execute('SELECT current_balance FROM accounts WHERE account_number = ?', 
                             (account_number,)).fetchone()
    
    if account is None:
        transaction_status = "Denied"
        rejection_reason = "Invalid VMB Account Number."
    elif transaction_status != "Denied" and account['current_balance'] < amount:
        transaction_status = "Denied"
        rejection_reason = "Insufficient Funds."
    
    # 5. Execute Debit & Finalize Status
    if transaction_status in ["Approved", "Flagged"]:
        if transaction_status == "Approved":
            # Only debit if fully approved
            new_balance = account['current_balance'] - amount
            cursor.execute('UPDATE accounts SET current_balance = ? WHERE account_number = ?', 
                           (new_balance, account_number))
        
        transaction_id = str(uuid.uuid4())
        
        # Log the transaction to the database
        is_fraud_label = 1 if risk_score > 0.9 else 0 # Simple label for demonstration
        cursor.execute('''INSERT INTO transactions 
                          (account_number, amount, payment_method, timestamp, status, risk_score, is_fraud) 
                          VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                       (account_number, amount, data['payment_method'], datetime.datetime.now().isoformat(), 
                        transaction_status, risk_score, is_fraud_label))
        conn.commit()
        conn.close()
        
        return jsonify({
            "status": transaction_status,
            "transaction_id": transaction_id,
            "risk_score": risk_score,
            "message": f"Transaction {transaction_status}. Risk Score: {risk_score:.2f}."
        }), 200

    # Handle Denial
    conn.close()
    return jsonify({
        "status": "denied",
        "risk_score": risk_score,
        "message": rejection_reason
    }), 403

# --- BANKER PORTAL ENDPOINTS ---

@app.route('/banker_login')
def banker_login():
    # Placeholder for a real login flow
    return redirect(url_for('banker_portal'))

@app.route('/banker_portal')
def banker_portal():
    conn = get_db_connection()
    # Fetch all flagged transactions and the top 10 highest-risk transactions
    flagged_txns = conn.execute('''SELECT * FROM transactions 
                                   WHERE status = 'Flagged' ORDER BY risk_score DESC''').fetchall()
                                   
    high_risk_txns = conn.execute('''SELECT * FROM transactions 
                                     ORDER BY risk_score DESC LIMIT 10''').fetchall()
                                     
    accounts = conn.execute('SELECT * FROM accounts').fetchall()

    conn.close()
    
    # Render the template
    response = make_response(render_template('banker_portal.html', 
                                             flagged_txns=flagged_txns, 
                                             high_risk_txns=high_risk_txns,
                                             accounts=accounts))
    
    # FIX: Add headers to prevent browser caching the page data
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

if __name__ == '__main__':
    app.run(debug=True, port=5000)
