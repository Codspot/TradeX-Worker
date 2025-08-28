import os
from flask import Flask
from dotenv import load_dotenv
from socket_server import init_socketio

def create_app():
    env = os.getenv("ENV", "development")
    load_dotenv(dotenv_path=f".env.{env}")

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "fallback")

    from .routes import api
    app.register_blueprint(api, url_prefix="/api")

    init_socketio(app)
    return app
