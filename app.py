# ================= IMPORTS =================
import os
import json
import pandas as pd
import requests
import numpy as np
import joblib

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from dotenv import load_dotenv
from difflib import get_close_matches

from models import db, User, Prediction

# ================= INIT =================
load_dotenv()

app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev-secret")
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URI", "sqlite:///medpredict.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

# ================= PATH =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")

# ================= LOAD ML =================
model = joblib.load(os.path.join(MODEL_DIR, "model.pkl"))
le_disease = joblib.load(os.path.join(MODEL_DIR, "disease_encoder.pkl"))

with open(os.path.join(MODEL_DIR, "symptom_list.json")) as f:
    all_symptoms = json.load(f)

symptom_index = {s: i for i, s in enumerate(all_symptoms)}

# ================= DATASET =================
df = pd.read_csv(os.path.join(BASE_DIR, "data", "dataset.csv"))
df["Disease"] = df["Disease"].astype(str).str.strip().str.lower()

# ================= USER =================
def current_user():
    uid = session.get("user_id")
    return User.query.get(uid) if uid else None

# ================= HOME =================
@app.route("/")
def index():
    return redirect(url_for("dashboard") if current_user() else url_for("login"))

# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("User already exists", "danger")
            return redirect(url_for("register"))

        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("Registration successful", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()

        if user and user.check_password(request.form["password"]):
            session["user_id"] = user.id
            flash("Login successful", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid credentials", "danger")

    return render_template("login.html")

# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for("login"))

# ================= DASHBOARD (CLEAN) =================
@app.route("/dashboard")
def dashboard():
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    return render_template("dashboard.html")

# ================= PREDICT API =================
@app.route("/api/predict", methods=["POST"])
def api_predict():

    data = request.json
    symptoms = data.get("symptoms", [])

    if not symptoms:
        return jsonify({"error": "Enter at least one symptom"}), 400

    input_vector = [0] * len(all_symptoms)
    recognized, unrecognized = [], []

    for s in symptoms:
        s = s.strip().lower().replace(" ", "_")
        match = get_close_matches(s, all_symptoms, n=1, cutoff=0.7)

        if match:
            idx = symptom_index[match[0]]
            input_vector[idx] = 1
            recognized.append(match[0])
        else:
            unrecognized.append(s)

    if sum(input_vector) == 0:
        return jsonify({"error": "No valid symptoms found"}), 400

    X = np.array(input_vector).reshape(1, -1)
    probs = model.predict_proba(X)[0]

    pred_idx = int(np.argmax(probs))
    predicted_disease = le_disease.inverse_transform([pred_idx])[0]

    top3_idx = probs.argsort()[-3:][::-1]
    top3 = [
        (le_disease.inverse_transform([i])[0], round(float(probs[i]) * 100, 2))
        for i in top3_idx
    ]

    disease_key = predicted_disease.strip().lower()
    row = df[df["Disease"] == disease_key]

    medicines = row.iloc[0]["Medicines"] if not row.empty else "Not Available"

    user_id = session.get("user_id")

    if user_id:
        p = Prediction(
            user_id=user_id,
            input_features=json.dumps(symptoms),
            predicted_label=predicted_disease,
            probabilities=json.dumps(top3),
            medicines=medicines
        )
        db.session.add(p)
        db.session.commit()

    return jsonify({
        "predicted_disease": predicted_disease,
        "top3": top3,
        "recognized_symptoms": recognized,
        "unrecognized_symptoms": unrecognized,
        "medicines": medicines
    })

# ================= HOSPITAL API (FIXED) =================
@app.route("/hospitals")
def hospitals():

    lat = request.args.get("lat")
    lng = request.args.get("lng")

    if not lat or not lng:
        return jsonify({"error": "Location required"}), 400

    try:
        url = "https://overpass-api.de/api/interpreter"

        query = f"""
        [out:json][timeout:25];
        (
          node["amenity"="hospital"](around:5000,{lat},{lng});
          node["healthcare"="hospital"](around:5000,{lat},{lng});
          way["amenity"="hospital"](around:5000,{lat},{lng});
        );
        out center;
        """

        headers = {
            "Content-Type": "text/plain",
            "User-Agent": "MedPredictApp/1.0"
        }

        res = requests.post(url, data=query.strip(), headers=headers, timeout=30)
        data = res.json()

        hospitals = []

        for el in data.get("elements", []):
            tags = el.get("tags", {})

            hospitals.append({
                "name": tags.get("name", "Unknown Hospital"),
                "address": tags.get("addr:full") or tags.get("addr:street") or "Nearby area",
                "rating": "N/A"
            })

        if not hospitals:
            return jsonify([{
                "name": "Local Hospital Nearby",
                "address": "Search Google Maps for nearest hospital",
                "rating": "N/A"
            }])

        return jsonify(hospitals[:10])

    except Exception as e:
        return jsonify({
            "error": "Hospital fetch failed",
            "details": str(e)
        }), 500

# ================= HISTORY PAGE =================
@app.route("/history")
def history():
    user = current_user()

    if not user:
        return redirect(url_for("login"))

    records = Prediction.query.filter_by(user_id=user.id)\
        .order_by(Prediction.created_at.desc()).all()

    return render_template("history.html", records=records)

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)