from flask_mail import Mail
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

bcrypt = Bcrypt()
mail = Mail()
login_manager = LoginManager()
