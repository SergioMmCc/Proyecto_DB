from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from .config import Config

# Inicializar SQLAlchemy
db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Inicializar la base de datos con la app
    db.init_app(app)

    # Importar y registrar el Blueprint
    from .routes import main
    app.register_blueprint(main)

    return app
