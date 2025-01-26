import sqlite3
from contextlib import contextmanager
from datetime import datetime

class MetricsDB:
    def __init__(self, db_path="startup_metrics.db"):
        self.db_path = db_path
        self.initialize_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def initialize_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY,
                    date TEXT NOT NULL,
                    cash_balance REAL,
                    monthly_revenue REAL,
                    monthly_expenses REAL,
                    b2b_total INTEGER,
                    b2b_new INTEGER,
                    b2b_cac REAL,
                    b2b_churn_rate REAL,
                    b2c_total INTEGER,
                    b2c_new INTEGER,
                    b2c_cac REAL,
                    b2c_churn_rate REAL
                )
            ''')
            conn.commit()

    def save_metrics(self, **metrics):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO metrics (
                    date, cash_balance, monthly_revenue, monthly_expenses,
                    b2b_total, b2b_new, b2b_cac, b2b_churn_rate,
                    b2c_total, b2c_new, b2c_cac, b2c_churn_rate
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().strftime("%Y-%m-%d"),
                metrics.get('cash_balance'),
                metrics.get('monthly_revenue'),
                metrics.get('monthly_expenses'),
                metrics.get('b2b_total'),
                metrics.get('b2b_new'),
                metrics.get('b2b_cac'),
                metrics.get('b2b_churn_rate'),
                metrics.get('b2c_total'),
                metrics.get('b2c_new'),
                metrics.get('b2c_cac'),
                metrics.get('b2c_churn_rate')
            ))
            conn.commit()

    def get_latest_metrics(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM metrics ORDER BY date DESC LIMIT 1')
            row = cursor.fetchone()
            if row:
                return {
                    'cash_balance': row[2],
                    'monthly_revenue': row[3],
                    'monthly_expenses': row[4],
                    'b2b_total': row[5],
                    'b2b_new': row[6],
                    'b2b_cac': row[7],
                    'b2b_churn_rate': row[8],
                    'b2c_total': row[9],
                    'b2c_new': row[10],
                    'b2c_cac': row[11],
                    'b2c_churn_rate': row[12]
                }
            return None