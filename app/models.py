from app import db
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, DateTime, Boolean, Interval

# Tabla vehiculos
class Vehiculos(db.Model):
    __tablename__ = 'vehiculos'

    id_vehiculo = db.Column(db.Integer, primary_key=True)
    placa = db.Column(db.String(6), nullable=False, unique=True)
    marca = db.Column(db.String(20), nullable=False, index=True)
    modelo = db.Column(db.String(30), nullable=False, index=True)
    color = db.Column(db.String(15), nullable=False)
    id_duenio = db.Column(db.Integer, db.ForeignKey('duenios.id_duenio'), nullable=False, index=True)
    tipo = db.Column(db.Enum('carro', 'moto', name='tipo_enum'), nullable=False)
    id_plaza = db.Column(db.Integer, db.ForeignKey('plazas.id_plaza'), nullable=True, unique=True)
    activo = db.Column(Boolean, default=True)

# Tabla duenios
class Duenios(db.Model):
    __tablename__ = 'duenios'

    id_duenio = db.Column(db.Integer, primary_key=True)
    cedula = db.Column(db.Integer, nullable=False, unique=True)
    nombre = db.Column(db.String(30), nullable=False)
    telefono = db.Column(db.String(10), nullable=False, unique=True)
    activo = db.Column(Boolean, default=True)

# Tabla plazas
class Plazas(db.Model):
    __tablename__ = 'plazas'

    id_plaza = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.Enum('carro', 'moto', name='tipo_plaza_enum'), nullable=False)
    estado = db.Column(db.Enum('disponible', 'no disponible', name='estado_enum'), nullable=False)

# Tabla registro_estancias
class RegistroEstancias(db.Model):
    __tablename__ = 'registro_estancias'

    id_estancia = db.Column(db.Integer, primary_key=True)
    id_vehiculo = db.Column(db.Integer, db.ForeignKey('vehiculos.id_vehiculo'), nullable=False, unique=True)
    id_plaza = db.Column(db.Integer, db.ForeignKey('plazas.id_plaza'), nullable=False, unique=True)
    fecha_hora_entrada = db.Column(db.DateTime, nullable=False)
    fecha_hora_salida = db.Column(db.DateTime, nullable=True)
    estado = db.Column(db.Enum('en proceso', 'finalizada', name='estado_enum'), nullable=False)

    # Relaciones con otros modelos
    vehiculo = db.relationship('Vehiculos', backref='estancias')

# Tabla facturas
class Facturas(db.Model):
    __tablename__ = 'facturas'

    id_factura = db.Column(db.Integer, primary_key=True)
    id_estancia = db.Column(db.Integer, db.ForeignKey('registro_estancias.id_estancia'), nullable=False, unique=True)
    monto = db.Column(db.Integer, nullable=False)
    id_vehiculo = db.Column(db.Integer, db.ForeignKey('vehiculos.id_vehiculo'), nullable=False, index=True)
    id_duenio = db.Column(db.Integer, db.ForeignKey('duenios.id_duenio'), nullable=False, index=False)

    # Relaciones con otros modelos
    vehiculo = db.relationship('Vehiculos', backref='facturas')
    estancia = db.relationship('RegistroEstancias', backref='facturas')
    duenio = db.relationship('Duenios', backref='facturas')


# Tabla empleados
class Empleados(db.Model):
    __tablename__ = 'empleados'

    id_empleado = db.Column(db.Integer, primary_key=True)
    cedula = db.Column(db.Integer, nullable=False, unique=True)
    nombre = db.Column(db.String(30), nullable=False)
    cargo = db.Column(db.Enum('admin', 'usuario', 'vigilante', 'aseador', name='cargo_enum'), nullable=False)
    telefono = db.Column(db.String(20), nullable=False, unique=True)
    salario = db.Column(db.Integer, nullable=False)
    activo = db.Column(Boolean, default=True)

# Tabla usuarios
class Usuarios(db.Model):
    __tablename__ = 'usuarios'

    id_usuario = db.Column(db.Integer, primary_key=True)
    id_empleado = db.Column(db.Integer, db.ForeignKey('empleados.id_empleado'), nullable=False, unique=True)
    contrasenia = db.Column(db.String(128), nullable=False)
    activo = db.Column(Boolean, default=True)

    # Relaciones con otros modelos
    empleado = db.relationship('Empleados', backref='usuarios')