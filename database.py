import mysql.connector
import sqlite3
import os

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "root123")
DB_NAME = os.environ.get("DB_NAME", "spam_detection")
DB_PORT = os.environ.get("DB_PORT", "3306")

try:
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=int(DB_PORT),
        connection_timeout=5
    )
    cursor = conn.cursor()
    print("MySQL Connected Successfully!")
except Exception as e:
    print(f"MySQL Connection Failed: {e}. Attempting SQLite fallback.")
    try:
        conn = sqlite3.connect("spam_detection.db")
        cursor = conn.cursor()
        print("SQLite Fallback Connected Successfully!")
    except Exception as sq_err:
        print(f"SQLite Fallback Connection Failed: {sq_err}")