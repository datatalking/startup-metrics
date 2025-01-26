import sqlite3
from pathlib import Path
from typing import Optional
import csv

def setup_investor_database(db_path: str = 'data/investors.db', csv_path: str = 'data/VC_PE.csv') -> Optional[sqlite3.Connection]:
    """
    Creates SQLite database and ingests VC/PE investor data from CSV.
    """
    try:
        Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS investors (
                firm_name TEXT PRIMARY KEY,
                type TEXT,
                location TEXT,
                website TEXT,
                office_contact TEXT,
                portfolio_examples TEXT,
                investment_focus TEXT
            )
        ''')

        if not Path(csv_path).exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        with open(csv_path, 'r', encoding='utf-8') as f:
            csv_reader = csv.reader(f)
            next(csv_reader)  # Skip header
            cursor.execute('DELETE FROM investors')
            cursor.executemany('INSERT INTO investors VALUES (?,?,?,?,?,?,?)', csv_reader)

        conn.commit()
        return conn

    except Exception as e:
        print(f"Error setting up database: {str(e)}")
        if 'conn' in locals():
            conn.close()
        return None

if __name__ == '__main__':
    conn = setup_investor_database()
    if conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM investors')
        print(f"Successfully imported {cursor.fetchone()[0]} investors")
        conn.close()