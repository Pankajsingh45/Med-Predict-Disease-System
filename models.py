# ================= IMPORTS =================
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# ================= USER MODEL =================
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)

    password_hash = db.Column(db.String(256), nullable=False)

    is_admin = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 🔐 Password methods
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # 👤 Representation (debugging ke liye)
    def __repr__(self):
        return f"<User {self.username}>"



# ================= PREDICTION MODEL =================
class Prediction(db.Model):
    __tablename__ = 'predictions'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # 🔹 Symptoms (input)
    input_features = db.Column(db.Text, nullable=False)

    # 🔹 Predicted disease
    predicted_label = db.Column(db.String(120), nullable=False, index=True)

    # 🔹 Probabilities (JSON string)
    probabilities = db.Column(db.Text, nullable=True)

    # 🔹 Medicines (NEW FIELD 🔥)
    medicines = db.Column(db.Text, nullable=True)

    # 🔹 Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationship
    user = db.relationship('User', backref=db.backref('predictions', lazy=True))

    def __repr__(self):
        return f"<Prediction {self.predicted_label}>"