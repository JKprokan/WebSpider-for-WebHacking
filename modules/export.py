import sqlite3
import csv
import json
import os

DB_PATH = "data/crawl_links.db"
EXPORT_DIR = "data"
JSON_PATH = os.path.join(EXPORT_DIR, "result.json")
CSV_PATH = os.path.join(EXPORT_DIR, "result.csv")

def export_json():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM crawl_links")
    rows = cursor.fetchall()
    columns = [description[0] for description in cursor.description]

    results = [dict(zip(columns, row)) for row in rows]
    
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"[+] JSON 저장 완료: {JSON_PATH}")
    conn.close()

def export_csv():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM crawl_links")
    rows = cursor.fetchall()
    columns = [description[0] for description in cursor.description]

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)

    print(f"[+] CSV 저장 완료: {CSV_PATH}")
    conn.close()