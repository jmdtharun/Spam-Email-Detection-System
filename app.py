from flask import Flask, render_template, request
import pickle
import mysql.connector

app = Flask(__name__)

# Load ML Model
model = pickle.load(open("model/spam_model.pkl", "rb"))
cv = pickle.load(open("model/vectorizer.pkl", "rb"))

# MySQL Connection
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root123",
    database="spam_detection"
)

cursor = conn.cursor()

total_predictions = 0
history = []

@app.route("/")
def home():

    spam_count = sum(1 for item in history if "Spam" in item["result"])
    ham_count = sum(1 for item in history if "Legitimate" in item["result"])

    return render_template(
        "index.html",
        total_predictions=total_predictions,
        history=history,
        spam_count=spam_count,
        ham_count=ham_count
    )

@app.route("/predict", methods=["POST"])
def predict():

    global total_predictions

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

    history.append({
        "email": email[:70],
        "result": result
    })

    # Save to MySQL
    cursor.execute(
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

    spam_count = sum(1 for item in history if "Spam" in item["result"])
    ham_count = sum(1 for item in history if "Legitimate" in item["result"])

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
@app.route("/history")
def database_history():

    cursor.execute("""
        SELECT id,
               email_text,
               result,
               spam_percentage,
               ham_percentage,
               created_at
        FROM email_history
        ORDER BY id DESC
    """)

    records = cursor.fetchall()

    return render_template(
        "history.html",
        records=records
    )

if __name__ == "__main__":
    app.run(debug=True)