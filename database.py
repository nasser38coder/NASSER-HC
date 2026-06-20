import sqlite3
from datetime import datetime
import config
import os

class Database:
    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self.conn = sqlite3.connect(config.DATABASE_FILE, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                report_type TEXT,
                target_username TEXT,
                target_platform TEXT,
                description TEXT,
                media_url TEXT,
                status TEXT DEFAULT 'pending',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                registered_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()

    def add_report(self, data):
        self.cursor.execute('''
            INSERT INTO reports (user_id, username, report_type, target_username, 
                               target_platform, description, media_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (data['user_id'], data['username'], data['report_type'], 
              data['target_username'], data['target_platform'], 
              data['description'], data['media_url']))
        self.conn.commit()
        return self.cursor.lastrowid

    def add_user(self, data):
        self.cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (data['user_id'], data['username'], data['first_name'], data['last_name']))
        self.conn.commit()
