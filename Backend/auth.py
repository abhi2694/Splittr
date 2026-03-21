from flask import Blueprint, request, jsonify, session, current_app
from flask_login import login_user, logout_user, login_required
from datetime import datetime, timedelta

from models import db, User
from utils import validate_email, validate_password, generate_otp, otp_expiry

from flask_mail import Message
from extensions import bcrypt, mail
from itsdangerous import URLSafeTimedSerializer

auth = Blueprint("auth", __name__)
serializer = URLSafeTimedSerializer("dev-secret")  # Use app.secret_key if set
RESET_PASSWORD_EXPIRY = 3600  # 1 hour

@auth.route("/me", methods=["GET"])
def me():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    return jsonify({
        "message": "Authenticated",
        "user_id": user_id
    })


### SIGNUP
@auth.route("/signup", methods=["POST"])
def signup():
    data = request.json

    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not name or not email or not password:
        return jsonify({"error": "All fields required"}), 400

    if not validate_email(email):
        return jsonify({"error": "Invalid email format"}), 400

    if not validate_password(password):
        return jsonify({"error": "Password not strong enough"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 400

    hashed = bcrypt.generate_password_hash(password).decode("utf-8")

    otp = generate_otp()

    user = User(
        name=name,
        email=email,
        password_hash=hashed,
        otp=otp,
        otp_expiry=otp_expiry(10)
    )

    db.session.add(user)
    db.session.commit()

    msg = Message(
        subject="Your OTP Code",
        recipients=[email],
        body=f"Your OTP code is: {otp}",
        sender=('Abhinav Kumar', 'abhi2694@gmail.com')
    )
    mail.send(msg)

    return jsonify({"message": "Account created. Verify OTP sent to email."}), 201


### VERIFY OTP
@auth.route("/verify", methods=["POST"])
def verify():
    data = request.json
    email = data.get("email")
    otp = data.get("otp")

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"error": "Invalid user"}), 400

    if user.verified:
        return jsonify({"message": "Already verified"}), 200

    if user.otp != otp:
        return jsonify({"error": "Incorrect OTP"}), 400

    if datetime.utcnow() > user.otp_expiry:
        return jsonify({"error": "OTP expired"}), 400

    user.verified = True
    user.otp = None
    user.otp_expiry = None
    db.session.commit()

    return jsonify({"message": "Account verified successfully"})


### LOGIN
@auth.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    if user.locked_until and datetime.utcnow() < user.locked_until:
        return jsonify({"error": "Account temporarily locked"}), 403

    if not user.verified:
        return jsonify({"error": "Account not verified"}), 403

    if not bcrypt.check_password_hash(user.password_hash, password):
        user.failed_attempts += 1

        if user.failed_attempts >= 5:
            user.locked_until = datetime.utcnow() + timedelta(minutes=10)

        db.session.commit()
        return jsonify({"error": "Invalid credentials"}), 401

    user.failed_attempts = 0
    db.session.commit()

    login_user(user)
    session["user_id"] = user.id
    return jsonify({"message": "Login successful"})


### LOGOUT
@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out"})

###FORGOT PASSWORD
@auth.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.json
    email = data.get("email", "").strip()

    if not email:
        return jsonify({"error": "Email required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Generate token
    token = serializer.dumps(user.email, salt="password-reset-salt")

    # Construct reset URL (frontend handles actual reset)
    reset_url = f"http://127.0.0.1:3000/reset-password?token={token}"

    # Send email
    msg = Message(
        subject="Password Reset Request",
        recipients=[user.email],
        body=f"Click the link to reset your password: {reset_url}\n"
             f"This link expires in 1 hour.",
        sender=('Abhinav Kumar', 'abhi2694@gmail.com')
    )
    mail.send(msg)

    return jsonify({"message": "Password reset email sent"}), 200

###RESET PASSWORD
@auth.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.json
    token = data.get("token")
    new_password = data.get("password", "").strip()

    if not token or not new_password:
        return jsonify({"error": "Token and new password required"}), 400

    # Validate password
    if not validate_password(new_password):
        return jsonify({"error": "Password not strong enough"}), 400

    # Decode token
    try:
        email = serializer.loads(token, salt="password-reset-salt", max_age=RESET_PASSWORD_EXPIRY)
    except Exception:
        return jsonify({"error": "Invalid or expired token"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Update password
    hashed = bcrypt.generate_password_hash(new_password).decode("utf-8")
    user.password_hash = hashed
    db.session.commit()

    return jsonify({"message": "Password reset successfully"}), 200


### RESEND OTP
@auth.route("/resend-otp", methods=["POST"])
def resend_otp():
    data = request.json
    email = data.get("email", "").strip()

    if not email:
        return jsonify({"error": "Email required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.verified:
        return jsonify({"message": "User already verified"}), 200

    # Generate new OTP
    otp = generate_otp()
    user.otp = otp
    user.otp_expiry = otp_expiry(10)  # 10 mins expiry
    db.session.commit()

    # Send OTP email
    msg = Message(
        subject="Your OTP Code",
        recipients=[user.email],
        body=f"Your OTP code is: {otp}",
        sender=('Abhinav Kumar', 'abhi2694@gmail.com')
    )
    mail.send(msg)

    return jsonify({"message": "OTP resent successfully"}), 200

