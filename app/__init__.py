from flask import Flask, session
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

    # Agregar el context_processor para `tipo_usuario`
    @app.context_processor
    def inject_user_type():
        return {'tipo_usuario': session.get('usuario')}

    return app
