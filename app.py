from flask import Flask, render_template, request, send_file, redirect, session
import pickle
import mysql.connector
import sqlite3
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "spam_secret_key")

# Load ML Model
model = pickle.load(open("model/spam_model.pkl", "rb"))
cv = pickle.load(open("model/vectorizer.pkl", "rb"))

# Database Configuration (MySQL with SQLite fallback)
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "root123")
DB_NAME = os.environ.get("DB_NAME", "spam_detection")
DB_PORT = os.environ.get("DB_PORT", "3306")

DB_TYPE = "mysql"

def init_db(connection, cursor_obj, db_type):
    if db_type == "sqlite":
        cursor_obj.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        """)
        cursor_obj.execute("""
            CREATE TABLE IF NOT EXISTS email_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_text TEXT NOT NULL,
                result TEXT NOT NULL,
                spam_percentage REAL NOT NULL,
                ham_percentage REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cursor_obj.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL
            )
        """)
        cursor_obj.execute("""
            CREATE TABLE IF NOT EXISTS email_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email_text TEXT NOT NULL,
                result VARCHAR(255) NOT NULL,
                spam_percentage FLOAT NOT NULL,
                ham_percentage FLOAT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    connection.commit()

try:
    # Attempt MySQL connection
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=int(DB_PORT),
        connection_timeout=5
    )
    cursor = conn.cursor()
    init_db(conn, cursor, "mysql")
    print("Connected to MySQL database and initialized tables.")
except Exception as e:
    print(f"MySQL connection failed: {e}. Falling back to SQLite.")
    DB_TYPE = "sqlite"
    conn = sqlite3.connect("spam_detection.db", check_same_thread=False)
    cursor = conn.cursor()
    init_db(conn, cursor, "sqlite")

def db_execute(query, params=None):
    if DB_TYPE == "sqlite":
        query = query.replace("%s", "?")
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)

total_predictions = 0
history = []
last_result = {}

# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        db_execute(
            """
            INSERT INTO users (username, email, password)
            VALUES (%s, %s, %s)
            """,
            (username, email, password)
        )
        conn.commit()
        return redirect("/login")

    return render_template("register.html")

# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        db_execute(
            """
            SELECT * FROM users
            WHERE email=%s AND password=%s
            """,
            (email, password)
        )

        user = cursor.fetchone()

        if user:
            session["user"] = user[1]
            return redirect("/")

        return "Invalid Email or Password"

    return render_template("login.html")

# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")

# ---------------- HOME ----------------

@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")

    spam_count = sum(
        1 for item in history
        if "Spam" in item["result"]
    )

    ham_count = sum(
        1 for item in history
        if "Legitimate" in item["result"]
    )

    return render_template(
        "index.html",
        total_predictions=total_predictions,
        history=history,
        spam_count=spam_count,
        ham_count=ham_count
    )

# ---------------- PREDICT ----------------

@app.route("/predict", methods=["POST"])
def predict():
    global total_predictions
    global last_result

    email = request.form["email"]

    total_predictions += 1

    data = cv.transform([email])

    prediction = model.predict(data)
    probability = model.predict_proba(data)[0]

    spam_percentage = round(probability[1] * 100, 2)
    ham_percentage = round(probability[0] * 100, 2)

    if prediction[0] == 1:
        result = "🚨 Spam Email Detected"
    else:
        result = "✅ Legitimate Email"

    last_result = {
        "email": email,
        "result": result,
        "spam_percentage": spam_percentage,
        "ham_percentage": ham_percentage
    }

    history.append({
        "email": email[:70],
        "result": result
    })

    db_execute(
        """
        INSERT INTO email_history
        (email_text, result, spam_percentage, ham_percentage)
        VALUES (%s, %s, %s, %s)
        """,
        (
            email,
            result,
            spam_percentage,
            ham_percentage
        )
    )

    conn.commit()

    spam_count = sum(
        1 for item in history
        if "Spam" in item["result"]
    )

    ham_count = sum(
        1 for item in history
        if "Legitimate" in item["result"]
    )

    return render_template(
        "index.html",
        prediction=result,
        spam_percentage=spam_percentage,
        ham_percentage=ham_percentage,
        total_predictions=total_predictions,
        history=history,
        spam_count=spam_count,
        ham_count=ham_count
    )

# ---------------- HISTORY ----------------

@app.route("/history")
def database_history():
    db_execute(
        """
        SELECT id,
               email_text,
               result,
               spam_percentage,
               ham_percentage,
               created_at
        FROM email_history
        ORDER BY id DESC
        """
    )

    records = cursor.fetchall()

    return render_template(
        "history.html",
        records=records
    )

# ---------------- PDF ----------------

@app.route("/download_pdf")
def download_pdf():
    pdf_file = "Spam_Report.pdf"

    doc = SimpleDocTemplate(pdf_file)

    styles = getSampleStyleSheet()

    content = []

    content.append(
        Paragraph(
            "Spam Email Detection Report",
            styles["Title"]
        )
    )

    content.append(Spacer(1, 20))

    content.append(
        Paragraph(
            f"Email: {last_result.get('email', 'N/A')}",
            styles["BodyText"]
        )
    )

    content.append(
        Paragraph(
            f"Result: {last_result.get('result', 'N/A')}",
            styles["BodyText"]
        )
    )

    content.append(
        Paragraph(
            f"Spam Percentage: {last_result.get('spam_percentage', 0)}%",
            styles["BodyText"]
        )
    )

    content.append(
        Paragraph(
            f"Ham Percentage: {last_result.get('ham_percentage', 0)}%",
            styles["BodyText"]
        )
    )

    doc.build(content)

    return send_file(
        pdf_file,
        as_attachment=True
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1"))