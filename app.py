from flask import Flask, request, jsonify, render_template, redirect, url_for
import sqlite3
import datetime
import uuid
from fraud_model import get_risk_score, feature_engineer, initialize_or_load_model
import random

app = Flask(__name__)
# Initialize the model on startup
initialize_or_load_model() 

RISK_THRESHOLD_DENY = 0.8  # Deny if risk is very high
RISK_THRESHOLD_FLAG = 0.4  # Flag for review if risk is medium

def get_db_connection():
    conn = sqlite3.connect('vmb_gateway.db')
    conn.row_factory = sqlite3.Row
    return conn

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
    amount = float(data['amount'])
    
    # 2. ML Integration: Get the risk score
    risk_score = get_risk_score(data)
    
    # 3. Decision Logic (ML/Risk-Based)
    transaction_status = "Approved"
    rejection_reason = None
    
    if risk_score >= RISK_THRESHOLD_DENY:
        transaction_status = "Denied"
        rejection_reason = "High Fraud Risk Detected (Score: {:.2f})".format(risk_score)
    elif risk_score >= RISK_THRESHOLD_FLAG:
        transaction_status = "Flagged"
        # Flagged transactions require manual banker review
        print(f"TRANSACTION FLAGGED: Risk {risk_score}. Requires Banker Review.")

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
            # Only debit if fully approved (Flagged transactions are typically held)
            new_balance = account['current_balance'] - amount
            cursor.execute('UPDATE accounts SET current_balance = ? WHERE account_number = ?', 
                           (new_balance, account_number))
        
        transaction_id = str(uuid.uuid4())
        
        # Log the transaction to the database (crucial for banker review and future ML retraining)
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
    # In a real app, this is a dedicated login page
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
    return render_template('banker_portal.html', 
                           flagged_txns=flagged_txns, 
                           high_risk_txns=high_risk_txns,
                           accounts=accounts)

if __name__ == '__main__':
    # Run database setup if schema.sql exists (should be done once manually)
    # import database; database.init_db() 
    app.run(debug=True, port=5000)