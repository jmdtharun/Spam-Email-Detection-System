import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root123",
    database="spam_detection"
)

cursor = conn.cursor()

print("MySQL Connected Successfully!")