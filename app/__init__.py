from flask import Flask
from flask_pymongo import PyMongo
from config import MONGO_URI

mongo = PyMongo()

def create_app():
    app = Flask(__name__)
    app.config["MONGO_URI"] = MONGO_URI
    mongo.init_app(app)

    from .routes import main
    app.register_blueprint(main)

    app.mongo = mongo

    return app