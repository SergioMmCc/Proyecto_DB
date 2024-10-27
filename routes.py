from flask import render_template, request, redirect, url_for
from datetime import datetime
from . import app, db
from .models import Vehiculos, Dueños, Plazas, RegistroEstancias, Facturas, Empleados, Usuarios

# Ruta principal
@app.route('/')
def index():
    return render_template('index.html')

# Autenticación --------------------------------------------------------------------------------------------------------
# Ruta para acceder al panel de administración
@app.route('/admin')
def admin():
    if request.method == 'POST':
        usuario = request.form['usuario']
        contraseña = request.form['contraseña']

        # Buscar el usuario en la base de datos
        usuario = Usuarios.query.filter_by(usuario=usuario, contraseña=contraseña).first()

        if usuario:
            # Verificar el tipo de usuario
            empleado = Empleados.query.get(usuario.id_empleado)

            if empleado.cargo == 'admin':
                return render_template('menu_admin.html')
            else:
                return render_template('menu.html')
            
        else:
            return "Usuario no encontrado.", 404


# Registros -----------------------------------------------------------------------------------------------
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
            cedula_dueño = request.form['cedula_dueño']
            
            # Buscar el dueño por cedula
            dueño = Dueños.query.get(cedula_dueño)

            # Si no se encuentra el dueño, se crea uno nuevo
            if not dueño:
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


# Función para generar una factura
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

# Ruta para registrar la salida de un vehículo
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
  
# Ruta para agregar empleados
@app.route('/empleados', methods=['GET', 'POST'])
def empleados():
    if request.method == 'POST':
        cedula = request.form['cedula']
        nombre = request.form['nombre']
        cargo = request.form['cargo']
        telefono = request.form['telefono']
        salario = request.form['salario']

        empleado = Empleados(cedula=cedula, nombre=nombre, cargo=cargo, telefono=telefono, salario=salario)
        db.session.add(empleado)

        if cargo == 'admin' or cargo == 'usuario':
            id_usuario = request.form['id_usuario']
            contraseña = request.form['contraseña']
            
            usuario = Usuarios(id_usuario=id_usuario, id_empleado=empleado.id_empleado, contraseña=contraseña)
            db.session.add(usuario)

        db.session.commit()

# Ruta para registrar una plaza
@app.route('/plazas', methods=['GET', 'POST'])
def plazas():
    if request.method == 'POST':
        tipo_plaza = request.form['tipo_plaza']
        estado = request.form['estado']

        plaza = Plazas(tipo_plaza=tipo_plaza, estado=estado)
        db.session.add(plaza)
        db.session.commit()

    return render_template('plazas.html')

# Actualizaciones ------------------------------------------------------------------------------------------------------
# Ruta para actualizar los datos de un vehículo
@app.route('/vehiculos/<int:id_vehiculo>/editar', methods=['GET', 'POST'])
def actualizar_vehiculo(id_vehiculo):
    vehiculo = Vehiculos.query.get(id_vehiculo)

    if request.method == 'POST':
        placa = request.form['placa']
        marca = request.form['marca']
        modelo = request.form['modelo']
        color = request.form['color']
        cedula_dueño = request.form['cedula_dueño']
        
        # Buscar el dueño por cédula
        dueño = Dueños.query.filter_by(cedula=cedula_dueño).first()
        if not dueño:
            nombre = request.form['nombre']
            telefono = request.form['telefono']
            dueño = Dueños(cedula=cedula_dueño, nombre=nombre, telefono=telefono)
            db.session.add(dueño)

        tipo_vehiculo = request.form['tipo_vehiculo']

        vehiculo.placa = placa
        vehiculo.marca = marca
        vehiculo.modelo = modelo
        vehiculo.color = color
        vehiculo.id_dueño = dueño.id_dueño
        vehiculo.tipo_vehiculo = tipo_vehiculo

        db.session.commit()
        return redirect(url_for('vehiculos'))

    return render_template('editar_vehiculo.html', vehiculo=vehiculo)

# Ruta para actualizar los datos de un dueño
@app.route('/dueños/<int:id_dueño>/editar', methods=['GET', 'POST'])
def actualizar_dueño(id_dueño):
    dueño = Dueños.query.get(id_dueño)

    if request.method == 'POST':
        cedula = request.form['cedula']
        nombre = request.form['nombre']
        telefono = request.form['telefono']

        dueño.cedula = cedula
        dueño.nombre = nombre
        dueño.telefono = telefono

        db.session.commit()
        return redirect(url_for('dueños'))

    return render_template('editar_dueño.html', dueño=dueño)

# Ruta para actualizar los datos de un empleado
@app.route('/empleados/<int:id_empleado>/editar', methods=['GET', 'POST'])
def actualizar_empleado(id_empleado):
    empleado = Empleados.query.get(id_empleado)

    if request.method == 'POST':
        cedula = request.form['cedula']
        nombre = request.form['nombre']
        cargo = request.form['cargo']
        telefono = request.form['telefono']
        salario = request.form['salario']

        if (empleado.cargo == 'admin' or empleado.cargo == 'usuario') and cargo != 'admin' and cargo != 'usuario':
            usuario = Usuarios.query.filter_by(id_empleado=empleado.id_empleado).first()
            db.session.delete(usuario)

        if (cargo == 'admin' or cargo == 'usuario') and empleado.cargo != 'admin' and empleado.cargo != 'usuario':
            id_usuario = request.form['id_usuario']
            contraseña = request.form['contraseña']
            
            usuario = Usuarios(id_usuario=id_usuario, id_empleado=empleado.id_empleado, contraseña=contraseña)
            db.session.add(usuario)

        empleado.cedula = cedula
        empleado.nombre = nombre
        empleado.cargo = cargo
        empleado.telefono = telefono
        empleado.salario = salario

        db.session.commit()
        return redirect(url_for('empleados'))

    return render_template('editar_empleado.html', empleado=empleado)

# Ruta para actualizar la contraseña de un usuario
@app.route('/usuarios/<int:id_usuario>/editar', methods=['GET', 'POST'])
def actualizar_usuario(id_usuario):
    usuario = Usuarios.query.get(id_usuario)

    if request.method == 'POST':
        contraseña = request.form['contraseña']
        usuario.contraseña = contraseña

        db.session.commit()
        return redirect(url_for('empleados'))

    return render_template('editar_usuario.html', usuario=usuario)

# Ruta para actualizar el id_usuario de un usuario
@app.route('/usuarios/<int:id_usuario>/editar', methods=['GET', 'POST'])
def actualizar_usuario(id_usuario):
    usuario = Usuarios.query.get(id_usuario)

    if request.method == 'POST':
        id_usuario = request.form['id_usuario']
        usuario.id_usuario = id_usuario

        db.session.commit()
        return redirect(url_for('empleados'))

    return render_template('editar_usuario.html', usuario=usuario)

# Consultas ------------------------------------------------------------------------------------------------------------
# Ruta para mostrar los vehículos registrados
@app.route('/vehiculos', methods=['GET', 'POST'])
def vehiculos():
    vehiculos = Vehiculos.query.all()
    return render_template('vehiculos.html', vehiculos=vehiculos)

# Ruta para mostrar un vehículo en particular
@app.route('/vehiculos/<int:id_vehiculo>', methods=['GET', 'POST'])
def vehiculo(id_vehiculo):
    vehiculo = Vehiculos.query.get(id_vehiculo)
    return render_template('vehiculo.html', vehiculo=vehiculo)

# Ruta para consultar las facturas
@app.route('/facturas', methods=['GET', 'POST'])
def facturas():
    facturas = Facturas.query.all()
    return render_template('facturas.html', facturas=facturas)

# Ruta para mostrar una factura en particular
@app.route('/facturas/<int:id_factura>', methods=['GET', 'POST'])
def factura(id_factura):
    factura = Facturas.query.get(id_factura)
    return render_template('factura.html', factura=factura)
            
# Ruta para mostrar los dueños registrados
@app.route('/dueños', methods=['GET', 'POST'])
def dueños():
    dueños = Dueños.query.all()
    return render_template('dueños.html', dueños=dueños)

# Ruta para mostrar un dueño en particular
@app.route('/dueños/<int:id_dueño>', methods=['GET', 'POST'])
def dueño(id_dueño):
    dueño = Dueños.query.get(id_dueño)
    return render_template('dueño.html', dueño=dueño)

# Ruta para mostrar los empleados registrados
@app.route('/empleados', methods=['GET', 'POST'])
def empleados():
    empleados = Empleados.query.all()
    return render_template('empleados.html', empleados=empleados)

# Ruta para mostrar un empleado en particular
@app.route('/empleados/<int:id_empleado>', methods=['GET', 'POST'])
def empleado(id_empleado):
    empleado = Empleados.query.get(id_empleado)
    return render_template('empleado.html', empleado=empleado)

# Ruta para mostrar el estado de las plazas
@app.route('/plazas', methods=['GET', 'POST'])
def plazas():
    plazas = Plazas.query.all()
    return render_template('plazas.html', plazas=plazas)

# Eliminaciones --------------------------------------------------------------------------------------------------------
