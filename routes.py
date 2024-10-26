from flask import render_template, request, redirect, url_for
from datetime import datetime
from . import app, db
from .models import Vehiculos, Dueños, Plazas, RegistroEstancias, Facturas

# Ruta principal
@app.route('/')
def index():
    return render_template('index.html')

# Ruta para mostrar los vehículos registrados
@app.route('/vehiculos', methods=['GET', 'POST'])
def vehiculos():
    if(request.method == 'POST'): # Procesar datos
        placa = request.form['placa']
        marca = request.form['marca']
        modelo = request.form['modelo']
        color = request.form['color']
        id_dueño = request.form['id_dueño']
        tipo_vehiculo = request.form['tipo_vehiculo']

        nuevo_vehiculo = Vehiculos(placa=placa, marca=marca, modelo=modelo, color=color, id_dueño=id_dueño, tipo_vehiculo=tipo_vehiculo)
        db.session.add(nuevo_vehiculo)
        db.session.commit()

        return redirect(url_for('vehiculos'))
    
    vehiculos = Vehiculos.query.all() # Mostrar datos
    return render_template('vehiculos.html', vehiculos=vehiculos)

# Ruta para registrar el ingreso de un vehículo
@app.route('/ingreso', methods=['GET', 'POST'])
def ingreso():
    if request.method == 'POST':
        placa = request.form['placa']
        # Buscar el vehículo por placa
        vehiculo = Vehiculos.query.filter_by(placa=placa).first()
        if not vehiculo:
            marca = request.form['marca']
            modelo = request.form['modelo']
            color = request.form['color']
            id_dueño = request.form['id_dueño']
            
            # Buscar el dueño por id
            dueño = Dueños.query.get(id_dueño)

            # Si no se encuentra el dueño, se crea uno nuevo
            if not dueño:
                cedula = request.form['cedula']
                nombre = request.form['nombre']
                telefono = request.form['telefono']
                dueño = Dueños(cedula=cedula, nombre=nombre, telefono=telefono)
                db.session.add(dueño)

            tipo_vehiculo = request.form['tipo_vehiculo']
            vehiculo = Vehiculos(placa=placa, marca=marca, modelo=modelo, color=color, id_dueño=id_dueño, tipo_vehiculo=tipo_vehiculo)
            db.session.add(vehiculo)

        # Buscar una plaza disponible
        if vehiculo.tipo_vehiculo == 'carro':
            plaza = Plazas.query.filter_by(tipo_plaza='carro', estado='disponible').first()
        else:
            plaza = Plazas.query.filter_by(tipo_plaza='moto', estado='disponible').first()
        if not plaza:
            return "No hay plazas disponibles.", 404
        
        # Marcar la plaza como no disponible
        plaza.estado = 'no disponible'

        # Asignar la plaza al vehículo
        vehiculo.id_plaza = plaza.id_plaza

        # Crear un registro de estancia
        estancia = RegistroEstancias(id_vehiculo=vehiculo.id_vehiculo, id_plaza=plaza.id_plaza, fecha_hora_entrada=datetime.now(), estado='en proceso')
        db.session.add(estancia)

        db.session.commit()
        return redirect(url_for('vehiculos'))
    
    return render_template('ingreso.html')

def calcular_monto(tiempo_estancia):
    # Calcular el monto a pagar por la estancia
    monto = 0
    if tiempo_estancia.days > 0:
        monto += 20000 * tiempo_estancia.days
    if tiempo_estancia.hours > 0:
        monto += 20000

    return monto

def generar_factura(vehiculo, dueño):
    # Buscar la estancia en proceso para el vehículo
    estancia = RegistroEstancias.query.filter_by(id_vehiculo=vehiculo.id_vehiculo, estado='en proceso').first()

    if estancia:
        # Calcular el tiempo de estancia
        tiempo_estancia = estancia.fecha_hora_salida - estancia.fecha_hora_entrada

        # Calcular el monto a pagar
        monto = calcular_monto(tiempo_estancia)

        # Crear la factura
        factura = Facturas(id_estancia=estancia.id_estancia, fecha_hora_entrada=estancia.fecha_hora_entrada,
                           fecha_hora_salida=estancia.fecha_hora_salida, tiempo_estancia=tiempo_estancia, monto=monto,
                           id_vehiculo=vehiculo.id_vehiculo, placa=vehiculo.placa, id_dueño=dueño.id_dueño,
                           cedula_dueño=dueño.cedula)

        # Guardar los cambios en la base de datos
        db.session.add(factura)
        db.session.commit()

        return factura
    else:
        return None


@app.route('/salida', methods=['GET', 'POST'])
def salida():
    if request.method == 'POST':
        placa = request.form['placa']
        cedula = request.form['cedula']

        # Buscar el vehículo por placa
        vehiculo = Vehiculos.query.filter_by(placa=placa).first()

        if vehiculo:
            # Obtener el dueño del vehículo
            dueño = Dueños.query.get(vehiculo.id_dueño)

            if dueño and dueño.cedula == cedula:  # Verificar que la cédula coincida
                # Buscar la estancia en proceso para el vehículo
                estancia = RegistroEstancias.query.filter_by(id_vehiculo=vehiculo.id_vehiculo, estado='en proceso').first()

                if estancia:
                    # Hora de salida
                    estancia.fecha_hora_salida = datetime.now()

                    # Generar la factura
                    factura = generar_factura(vehiculo, dueño)

                    # Actualizar estado de la estancia a 'finalizada'
                    estancia.estado = 'finalizada'

                    # Actualizar estado de la plaza a 'disponible'
                    plaza = Plazas.query.get(estancia.id_plaza)
                    if plaza:
                        plaza.estado = 'disponible'

                    # Actualizar id_plaza del vehículo a NULL
                    vehiculo.id_plaza = None

                    # Guardar los cambios en la base de datos
                    db.session.commit()

                    return redirect(url_for('vehiculos'))
                else:
                    return "No hay estancia en proceso para este vehículo.", 404
            else:
                return "La cédula no coincide con el dueño del vehículo.", 403
        else:
            return "Vehículo no encontrado.", 404

    return render_template('salida.html')


@app.route()