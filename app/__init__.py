from flask import Flask
from flask.cli import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
from flask_socketio import SocketIO
from flask_jwt_extended import JWTManager

load_dotenv()

db=SQLAlchemy()
socketio=SocketIO(cors_allowed_origins="*")

def create_app():
    load_dotenv()
    app=Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
    print("done")

    CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})

    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "your-default-secret-key")  # Default secret key fallback
    app.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET_KEY")

    jwt = JWTManager(app)
    CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})

    db.init_app(app)

    with app.app_context():
        db.create_all()

    from app.calculations.routes import cal_bp
    from app.user_managment.routes import user_management_bp
    app.register_blueprint(cal_bp)
    app.register_blueprint(user_management_bp)

    socketio.init_app(app)
    return app