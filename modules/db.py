import sqlite3
import os
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

# db_path는 이제 함수 인자로 전달됩니다.

def get_db_path(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.replace(":", "_").replace(".", "_") # 콜론과 점을 언더스코어로 대체
    os.makedirs("data", exist_ok=True)
    return os.path.join("data", f"{domain}.db")

def create_table(db_path):
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
            input_fields TEXT,
            collected_time TEXT
        );
        """)
        conn.commit()

def insert_link(db_path, link, parent, depth, host, query_params, input_fields_json):
    kst_now = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO crawl_links 
            (link, parent, depth, host, query_params, input_fields, collected_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (link, parent, depth, host, query_params, input_fields_json, kst_now))
        conn.commit()