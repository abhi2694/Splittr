from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager
from flask_mail import Mail
from config import Config
from models import db, User
from auth import auth, bcrypt
from extensions import bcrypt, mail, login_manager

app = Flask(__name__)
app.config.from_object(Config)

print(">>> THIS IS THE ACTIVE APP FILE <<<")

CORS(
    app,
    origins=["http://127.0.0.1:3000"],
    supports_credentials=True
)
print(">>> CORS INITIALIZED <<<")

db.init_app(app)
bcrypt.init_app(app)

# login_manager = LoginManager()
login_manager.init_app(app)

# mail = Mail(app)
mail.init_app(app)

from groups import groups
app.register_blueprint(groups)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

app.register_blueprint(auth)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
