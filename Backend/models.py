from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    verified = db.Column(db.Boolean, default=False)

    otp = db.Column(db.String(6))
    otp_expiry = db.Column(db.DateTime)

    failed_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
