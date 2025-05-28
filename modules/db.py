import sqlite3
import os
from datetime import datetime, timezone, timedelta

os.makedirs("data", exist_ok=True)
db_path = "data/crawl_links.db"

def create_table():
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS crawl_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link TEXT UNIQUE,
            parent TEXT,
            depth INTEGER,
            host TEXT,
            query_params TEXT,
            collected_time TEXT
        );
        """)
        conn.commit()

def insert_link(link, parent, depth, host, query_params):
    kst_now = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO crawl_links (link, parent, depth, host, query_params, collected_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (link, parent, depth, host, query_params, kst_now))
        conn.commit()
