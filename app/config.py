import os

class Config:
    # URI de la base de datos
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://gestion_parqueadero:1089380570@localhost/parqueadero'

    # Desactivar seguimiento para mejorar el redimiento
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Desactivar seguimiento para mejorar el redimiento
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave_super_secreta'