from flask import Flask
from flask_pymongo import PyMongo
import os

mongo = PyMongo()

def create_app():
    app = Flask(__name__)
    # Obtener URI de Mongo desde variable de entorno
    mongo_uri = os.environ.get("MONGO_URI")
    if not mongo_uri:
        raise RuntimeError("⚠️ No se encontró la variable de entorno MONGO_URI")

    app.config["MONGO_URI"] = mongo_uri
    mongo.init_app(app)

    from .routes import main
    app.register_blueprint(main)

    app.mongo = mongo

    return app