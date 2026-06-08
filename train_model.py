import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
import pickle
import os

# Read dataset
data = pd.read_csv("spam.tsv", sep="\t", names=["label", "message"])

# Convert labels
data["label"] = data["label"].map({
    "ham": 0,
    "spam": 1
})

# Convert text to numbers
cv = CountVectorizer()

X = cv.fit_transform(data["message"])
y = data["label"]

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

# Train model
model = MultinomialNB()
model.fit(X_train, y_train)

# Create model folder if not exists
os.makedirs("model", exist_ok=True)

# Save model
pickle.dump(model, open("model/spam_model.pkl", "wb"))
pickle.dump(cv, open("model/vectorizer.pkl", "wb"))

print("Model Trained Successfully!")