-- Accounts Table: Stores VMB user data (simplified)
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_number TEXT NOT NULL UNIQUE,
    current_balance REAL NOT NULL,
    customer_name TEXT NOT NULL
);

-- Transactions Table: Stores historical and new transaction data
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_number TEXT NOT NULL,
    amount REAL NOT NULL,
    payment_method TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    status TEXT NOT NULL, -- 'Approved', 'Denied', 'Flagged'
    risk_score REAL NOT NULL,
    is_fraud INTEGER NOT NULL DEFAULT 0, -- 0 for legitimate, 1 for actual fraud (used for model training)
    FOREIGN KEY(account_number) REFERENCES accounts(account_number)
);

-- Banker Portal Data (optional, for demo)
INSERT INTO accounts (account_number, current_balance, customer_name) VALUES ('1234567890123456', 5000.00, 'Alice Johnson');
INSERT INTO accounts (account_number, current_balance, customer_name) VALUES ('9876543210987654', 150.50, 'Bob Smith');