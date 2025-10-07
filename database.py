import sqlite3

def init_db():
    conn = sqlite3.connect('vmb_gateway.db')
    cursor = conn.cursor()

    with open('schema.sql', 'r') as f:
        sql_script = f.read()

    cursor.executescript(sql_script)
    conn.commit()
    conn.close()
    print("Database 'vmb_gateway.db' created and initialized with sample data.")

if __name__ == '__main__':
    init_db()