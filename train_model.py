# ================= IMPORTS =================
import pandas as pd
import numpy as np
import os, json, joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

os.makedirs("models", exist_ok=True)

# ================= LOAD DATA =================
df = pd.read_csv("data/dataset.csv")

print("Columns:", df.columns.tolist())

target_col = "Disease"
symptom_cols = [c for c in df.columns if c != target_col]

# ================= CLEAN DATA =================
df[symptom_cols] = df[symptom_cols].fillna("None")

# Normalize symptoms (important)
for col in symptom_cols:
    df[col] = df[col].astype(str).str.strip().str.lower().str.replace(" ", "_")

# ================= BUILD SYMPTOM LIST =================
unique_symptoms = set()

for col in symptom_cols:
    unique_symptoms.update(df[col].unique())

unique_symptoms.discard("none")
unique_symptoms = sorted(unique_symptoms)

print(f"✅ Total unique symptoms: {len(unique_symptoms)}")

# ================= ENCODING =================
symptom_index = {s: i for i, s in enumerate(unique_symptoms)}

def encode_row(row):
    vector = np.zeros(len(unique_symptoms))
    for val in row:
        if val != "none" and val in symptom_index:
            vector[symptom_index[val]] = 1
    return vector

X = np.array(df[symptom_cols].apply(encode_row, axis=1).tolist())
y = df[target_col]

# ================= LABEL ENCODING =================
le = LabelEncoder()
y_encoded = le.fit_transform(y)

# ================= SPLIT =================
X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded, test_size=0.2, stratify=y_encoded, random_state=42
)

# ================= MODEL =================
model = RandomForestClassifier(
    n_estimators=300,
    max_depth=None,
    min_samples_split=2,
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)

# ================= EVALUATION =================
y_pred = model.predict(X_test)

print("\n🎯 Accuracy:", round(accuracy_score(y_test, y_pred), 4))
print("\n📊 Classification Report:\n")
print(classification_report(y_test, y_pred, target_names=le.classes_))

# ================= SAVE =================
joblib.dump(model, "models/model.pkl")
joblib.dump(le, "models/disease_encoder.pkl")

with open("models/symptom_list.json", "w") as f:
    json.dump(unique_symptoms, f)

print("\n✅ Model training completed & saved!")