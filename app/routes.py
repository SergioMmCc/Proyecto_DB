from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime
from app import db
from app.models import Vehiculos, Duenios, Plazas, RegistroEstancias, Facturas, Empleados, Usuarios

main = Blueprint('main', __name__)

@main.route('/test_db')
def test_db():
    try:
        result = db.session.execute('SELECT 1')
        return "Conexión exitosa a la base de datos: {}".format(result.fetchall())
    except Exception as e:
        return f"Error en la conexión: {str(e)}"

# Autenticación --------------------------------------------------------------------------------------------------------
# Ruta para acceder al panel de administración o de usuario
@main.route('/index', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        id_usuario = request.form['id_usuario']
        contrasenia = request.form['contrasenia']

        print(f"ID de Usuario: {id_usuario}, Contraseña: {contrasenia}")  # Log para depuración

        # Buscar el usuario en la base de datos
        usuario = Usuarios.query.filter_by(id_usuario=id_usuario, contrasenia=contrasenia).first()

        if usuario and usuario.activo==True:
            # Verificar el tipo de usuario
            empleado = Empleados.query.get(usuario.id_empleado)

            if empleado.cargo == 'admin':
                session['usuario'] = 'admin'
                return render_template('menu_admin.html')
            else:
                session['usuario'] = 'usuario'
                return render_template('menu.html')
            
        else:
            return "Usuario no encontrado.", 401
    return render_template('index.html')

# Registros -----------------------------------------------------------------------------------------------
# Ruta para registrar un vehículo
@main.route('/registrar_vehiculo', methods=['GET', 'POST'])
def registrar_vehiculo():
    placa = session.get('placa')  # Obtener placa de la URL, si existe
    tipo_usuario = session.get('usuario')
    if request.method == 'POST':
        marca = request.form['marca']
        modelo = request.form['modelo']
        color = request.form['color']
        tipo = request.form['tipo']
        cedula = request.form['cedula']
        
        # Buscar el duenio por cédula
        duenio = Duenios.query.filter_by(cedula=cedula).first()
        if not duenio:
            session['usuario'] = tipo_usuario
            session['placa'] = placa
            session['cedula'] = cedula
            session['marca'] = marca
            session['modelo'] = modelo
            session['color'] = color
            session['tipo'] = tipo
            return redirect(url_for('main.registrar_duenio'))
        if duenio.activo==False:
            duenio.activo=True
            db.session.commit()

        vehiculo = Vehiculos(placa=placa, marca=marca, modelo=modelo, color=color, id_duenio=duenio.id_duenio, tipo=tipo, activo=True)
        db.session.add(vehiculo)
        db.session.commit()

        asignar_plaza(vehiculo)

        if tipo_usuario == 'admin':
            return render_template('menu_admin.html')
        else:
            return render_template('menu.html')

    return render_template('registrar_vehiculo.html')

# Ruta para registrar un dueño
@main.route('/registrar_duenio', methods=['GET', 'POST'])
def registrar_duenio():
    cedula = session.get('cedula')  # Obtener cédula de la URL, si existe
    tipo_usuario = session.get('usuario')
    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']

        duenio = Duenios(cedula=cedula, nombre=nombre, telefono=telefono, activo=True)
        db.session.add(duenio)
        db.session.commit()

        # Obtener los datos del vehículo
        placa = session.get('placa')
        marca = session.get('marca')
        modelo = session.get('modelo')
        color = session.get('color')
        tipo = session.get('tipo')

        # Crear el vehículo
        vehiculo = Vehiculos(placa=placa, marca=marca, modelo=modelo, color=color, id_duenio=duenio.id_duenio, tipo=tipo, activo=True)
        db.session.add(vehiculo)
        db.session.commit()

        asignar_plaza(vehiculo)
        
        if tipo_usuario == 'admin':
            return render_template('menu_admin.html')
        else:
            return render_template('menu.html')

    return render_template('registrar_duenio.html')

# Ruta para registrar el ingreso de un vehículo
@main.route('/ingreso', methods=['GET', 'POST'])
def ingreso():
    tipo_usuario = session.get('usuario')
    if request.method == 'POST':
        placa = request.form['placa']

        # Buscar el vehículo por placa
        vehiculo = Vehiculos.query.filter_by(placa=placa).first()
        if not vehiculo:
            session['placa'] = placa
            session['usuario'] = tipo_usuario
            return redirect(url_for('main.registrar_vehiculo'))
        if vehiculo.activo==False:
            vehiculo.activo=True
            db.session.commit()
        if vehiculo.id_plaza is not None:
            return "El vehículo ya está estacionado.", 403

        asignar_plaza(vehiculo)
        
        if tipo_usuario == 'admin':
            return render_template('menu_admin.html')
        else:
            return render_template('menu.html')
    
    return render_template('ingreso.html')

# Funcion para asignar una plaza a un vehiculo
def asignar_plaza(vehiculo):
    if vehiculo.tipo == 'carro':
        plaza = Plazas.query.filter_by(tipo='carro', estado='disponible').first()
    else:
        plaza = Plazas.query.filter_by(tipo='moto', estado='disponible').first()
    if not plaza:
        return "No hay plazas disponibles.", 404
    plaza.estado = 'no disponible'
    vehiculo.id_plaza = plaza.id_plaza
    db.session.commit()

    # Crear un registro de estancia
    estancia = RegistroEstancias(id_vehiculo=vehiculo.id_vehiculo, id_plaza=plaza.id_plaza, fecha_hora_entrada=datetime.now(), estado='en proceso')
    db.session.add(estancia)
    db.session.commit()

# Función para calcular el monto a pagar por la estancia
def calcular_monto(tiempo_estancia):
    # Calcular el monto a pagar por la estancia
    monto = 0
    if tiempo_estancia.days > 0:
        monto += 20000 * tiempo_estancia.days
    hours = tiempo_estancia.seconds // 3600
    if hours >= 10:
        monto += 20000
    elif hours > 0:
        monto += 2000 * hours
        if tiempo_estancia.seconds % 3600 > 0:
            monto += 2000

    return monto


# Función para generar una factura
def generar_factura(vehiculo, duenio):
    # Buscar la estancia en proceso para el vehículo
    estancia = RegistroEstancias.query.filter_by(id_vehiculo=vehiculo.id_vehiculo, estado='en proceso').first()

    if estancia:
        # Calcular el tiempo de estancia
        tiempo_estancia = estancia.fecha_hora_salida - estancia.fecha_hora_entrada

        # Calcular el monto a pagar
        monto = calcular_monto(tiempo_estancia)

        # Crear la factura
        factura = Facturas(id_estancia=estancia.id_estancia, monto=monto,
                           id_vehiculo=vehiculo.id_vehiculo, id_duenio=duenio.id_duenio)

        # Guardar los cambios en la base de datos
        db.session.add(factura)
        db.session.commit()

        return factura
    else:
        return None

# Ruta para registrar la salida de un vehículo
@main.route('/salida', methods=['GET', 'POST'])
def salida():
    if request.method == 'POST':
        placa = request.form['placa']
        cedula = request.form['cedula']

        # Buscar el vehículo por placa
        vehiculo = Vehiculos.query.filter_by(placa=placa).first()

        if not vehiculo:
            return "La placa no coincide con ningún vehículo.", 404
        
        # Buscar el dueño por cedula
        duenio = Duenios.query.filter_by(cedula=cedula).first()

        if not duenio:
            return "La cedula no coincide con ningún dueño.", 404

        if vehiculo.id_duenio == duenio.id_duenio:  # Verificar que la cédula coincida
            if duenio.activo == False:
                duenio.activo=True
                db.session.commit()

            # Buscar la estancia en proceso para el vehículo
            estancia = RegistroEstancias.query.filter_by(id_vehiculo=vehiculo.id_vehiculo, estado='en proceso').first()

            if estancia:
                # Verificar actividad del vehículo
                if vehiculo.activo == False:
                    vehiculo.activo=True
                    db.session.commit()

                # Hora de salida
                estancia.fecha_hora_salida = datetime.now()

                # Generar la factura
                factura = generar_factura(vehiculo, duenio)

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

                if session.get('usuario') == 'admin':
                    return render_template('menu_admin.html')
                else:
                    return render_template('menu.html')
                # return render_template('factura.html', factura=factura)
            else:
                return "El vehiculo ya no se encuentra en el parqueadero.", 404
        else:
            return "La cédula no coincide con el duenio del vehículo.", 403

    return render_template('salida.html')

# Ruta para buscar empleados
@main.route('/cedula_empleado', methods=['GET', 'POST'])
def cedula_empleado():
    if request.method == 'POST':
        cedula = request.form['cedula']
        empleado = Empleados.query.filter_by(cedula=cedula).first()

        if empleado:
            if not empleado.activo:
                empleado.activo = True
                usuario = Usuarios.query.filter_by(id_empleado=empleado.id_empleado).first()
                if usuario:
                    usuario.activo = True
                db.session.commit()
                flash("Empleado activado correctamente.")
            else:
                flash("El empleado ya está registrado.")
        else:
            # Redirigir al formulario de registro con la cédula
            session['cedula'] = cedula
            return redirect(url_for('main.registrar_empleado'))
        return redirect(url_for('main.menu_admin'))

    return render_template('cedula_empleado.html')

# Ruta para agregar empleados
@main.route('/registrar_empleado', methods=['GET', 'POST'])
def registrar_empleado():
    nueva_cedula = session.get('cedula')  # Obtener cédula de la URL, si existe
    if request.method == 'POST':
        if not nueva_cedula:  # Si no hay cédula, debes manejar el caso de error
            flash("La cédula es requerida.")
            return redirect(url_for('main.cedula_empleado'))

        else:
            nombre = request.form['nombre']
            cargo = request.form['cargo']
            telefono = request.form['telefono']
            salario = request.form['salario']

            empleado = Empleados(cedula=nueva_cedula, nombre=nombre, cargo=cargo, telefono=telefono, salario=salario, activo=True)
            db.session.add(empleado)
            db.session.commit()

            if cargo in ['admin', 'usuario']:
                session['id_empleado'] = empleado.id_empleado
                return redirect(url_for('main.registrar_usuario'))
            
            flash("Empleado registrado correctamente.")
            return render_template('menu_admin.html')

    return render_template('registrar_empleado.html')

# Ruta para registrar un usuario
@main.route('/registrar_usuario', methods=['GET', 'POST'])
def registrar_usuario():
    id_empleado = session.get('id_empleado')  # Obtener id_empleado de la URL, si existe
    if request.method == 'POST':
        id_usuario = request.form['id_usuario']
        contrasenia = request.form['contrasenia']

        usuario = Usuarios(id_usuario=id_usuario, contrasenia=contrasenia, id_empleado=id_empleado)
        db.session.add(usuario)
        db.session.commit()

        flash("Empleado registrado correctamente.")
        return render_template('menu_admin.html')

    return render_template('registrar_usuario.html')

# Ruta para registrar una plaza
@main.route('/agregar_plaza', methods=['GET', 'POST'])
def agregar_plaza():
    if request.method == 'POST':
        tipo = request.form['tipo']

        plaza = Plazas(tipo=tipo, estado='disponible')
        db.session.add(plaza)
        db.session.commit()

        if session.get('usuario') == 'admin':
            return render_template('menu_admin.html')
        else:
            return render_template('menu.html')
    
    return render_template('agregar_plaza.html')

# # Actualizaciones ------------------------------------------------------------------------------------------------------
# # Ruta para actualizar los datos de un vehículo
# @main.route('/vehiculos/<int:id_vehiculo>/editar', methods=['GET', 'POST'])
# def actualizar_vehiculo(id_vehiculo):
#     vehiculo = Vehiculos.query.get(id_vehiculo)

#     if request.method == 'POST':
#         placa = request.form['placa']
#         marca = request.form['marca']
#         modelo = request.form['modelo']
#         color = request.form['color']
#         cedula_duenio = request.form['cedula_duenio']
        
#         # Buscar el duenio por cédula
#         duenio = Duenios.query.filter_by(cedula=cedula_duenio).first()
#         if not duenio:
#             nombre = request.form['nombre']
#             telefono = request.form['telefono']
#             duenio = Duenios(cedula=cedula_duenio, nombre=nombre, telefono=telefono)
#             db.session.add(duenio)

#         tipo_vehiculo = request.form['tipo_vehiculo']

#         vehiculo.placa = placa
#         vehiculo.marca = marca
#         vehiculo.modelo = modelo
#         vehiculo.color = color
#         vehiculo.id_duenio = duenio.id_duenio
#         vehiculo.tipo_vehiculo = tipo_vehiculo

#         db.session.commit()
#         return redirect(url_for('vehiculos'))

#     return render_template('editar_vehiculo.html', vehiculo=vehiculo)

# # Ruta para actualizar los datos de un duenio
# @main.route('/duenios/<int:id_duenio>/editar', methods=['GET', 'POST'])
# def actualizar_duenio(id_duenio):
#     duenio = Duenios.query.get(id_duenio)

#     if request.method == 'POST':
#         cedula = request.form['cedula']
#         nombre = request.form['nombre']
#         telefono = request.form['telefono']

#         duenio.cedula = cedula
#         duenio.nombre = nombre
#         duenio.telefono = telefono

#         db.session.commit()
#         return redirect(url_for('duenios'))

#     return render_template('editar_duenio.html', duenio=duenio)

# # Ruta para actualizar los datos de un empleado
# @main.route('/empleados/<int:id_empleado>/editar', methods=['GET', 'POST'])
# def actualizar_empleado(id_empleado):
#     empleado = Empleados.query.get(id_empleado)

#     if request.method == 'POST':
#         cedula = request.form['cedula']
#         nombre = request.form['nombre']
#         cargo = request.form['cargo']
#         telefono = request.form['telefono']
#         salario = request.form['salario']

#         if (empleado.cargo == 'admin' or empleado.cargo == 'usuario') and cargo != 'admin' and cargo != 'usuario':
#             usuario = Usuarios.query.filter_by(id_empleado=empleado.id_empleado).first()
#             db.session.delete(usuario)

#         if (cargo == 'admin' or cargo == 'usuario') and empleado.cargo != 'admin' and empleado.cargo != 'usuario':
#             id_usuario = request.form['id_usuario']
#             contrasenia = request.form['contrasenia']
            
#             usuario = Usuarios(id_usuario=id_usuario, id_empleado=empleado.id_empleado, contrasenia=contrasenia)
#             db.session.add(usuario)

#         empleado.cedula = cedula
#         empleado.nombre = nombre
#         empleado.cargo = cargo
#         empleado.telefono = telefono
#         empleado.salario = salario

#         db.session.commit()
#         return redirect(url_for('empleados'))

#     return render_template('editar_empleado.html', empleado=empleado)

# Ruta para actualizar las credenciales de un usuario
@main.route('/usuarios/<int:id_usuario>/editar', methods=['GET', 'POST'])
def actualizar_usuario(id_usuario):
    usuario = Usuarios.query.get(id_usuario)

    if request.method == 'POST':
        id_usuario = request.form['id_usuario']
        contrasenia = request.form['contrasenia']

        # Actualizar los datos del usuario
        usuario.id_usuario = id_usuario
        usuario.contrasenia = contrasenia

        db.session.commit()
        return redirect(url_for('empleados'))

    return render_template('registrar_usuario.html', usuario=usuario)

# Consultas ------------------------------------------------------------------------------------------------------------

# Vehículos ------------------------------------------------------------------------------------------------------------
# Ruta para mostrar los vehículos registrados
@main.route('/consultar_todos_vehiculos', methods=['GET'])
def consultar_todos_vehiculos():
    vehiculos = Vehiculos.query.all()
    return render_template('consultar_todos_vehiculos.html', vehiculos=vehiculos)

# Ruta para solicitar una placa
@main.route('/solicitar_placa', methods=['GET', 'POST'])
def solicitar_placa():
    if request.method == 'POST':
        placa = request.form['placa']

        vehiculo = Vehiculos.query.filter_by(placa=placa).first()
        if not vehiculo:
            return "El vehiculo no esta registrado.", 404

        session['placa'] = placa
        return redirect(url_for('main.consultar_un_vehiculo'))

    return render_template('solicitar_placa.html')

# Ruta para mostrar un vehículo en particular
@main.route('/consultar_un_vehiculo', methods=['GET'])
def consultar_un_vehiculo():
    placa = session.get('placa')
    vehiculo = Vehiculos.query.filter_by(placa=placa).first()
    return render_template('consultar_un_vehiculo.html', vehiculo=vehiculo)

# Dueños ---------------------------------------------------------------------------------------------------------------
# Ruta para mostrar los duenios registrados
@main.route('/consultar_todos_duenios', methods=['GET'])
def consultar_todos_duenios():
    duenios = Duenios.query.all()
    return render_template('consultar_todos_duenios.html', duenios=duenios)

# Ruta para solicitar una cedula de un dueño
@main.route('/solicitar_cedula_duenio', methods=['GET', 'POST'])
def solicitar_cedula_duenio():
    if request.method == 'POST':
        cedula = request.form['cedula']

        duenio = Duenios.query.filter_by(cedula=cedula).first()
        if not duenio:
            return "El dueño no esta registrado.", 404

        session['cedula'] = cedula
        return redirect(url_for('main.consultar_un_duenio'))

    return render_template('solicitar_cedula_duenio.html')

# Ruta para mostrar un duenio en particular
@main.route('/consultar_un_duenio', methods=['GET'])
def consultar_un_duenio():
    cedula = session.get('cedula')
    duenio = Duenios.query.filter_by(cedula=cedula).first()
    return render_template('consultar_un_duenio.html', duenio=duenio)

# Empleados ------------------------------------------------------------------------------------------------------------
# Ruta para mostrar los empleados registrados
@main.route('/consultar_todos_empleados', methods=['GET'])
def consultar_todos_empleados():
    empleados = Empleados.query.all()
    return render_template('consultar_todos_empleados.html', empleados=empleados)

# Ruta para solicitar una cedula de un empleado
@main.route('/solicitar_cedula_empleado', methods=['GET', 'POST'])
def solicitar_cedula_empleado():
    if request.method == 'POST':
        cedula = request.form['cedula']

        empleado = Empleados.query.filter_by(cedula=cedula).first()
        if not empleado:
            return "El empleado no esta registrado.", 404

        session['cedula'] = cedula
        return redirect(url_for('main.consultar_un_empleado'))

    return render_template('solicitar_cedula_empleado.html')

# Ruta para mostrar un empleado en particular
@main.route('/consultar_un_empleado', methods=['GET'])
def consultar_un_empleado():
    cedula = session.get('cedula')
    empleado = Empleados.query.filter_by(cedula=cedula).first()
    return render_template('consultar_un_empleado.html', empleado=empleado)

# Usuarios -------------------------------------------------------------------------------------------------------------
# Ruta para mostrar los usuarios registrados
@main.route('/consultar_todos_usuarios', methods=['GET'])
def consultar_todos_usuarios():
    usuarios = Usuarios.query.all()
    return render_template('consultar_todos_usuarios.html', usuarios=usuarios)

# Estancias ------------------------------------------------------------------------------------------------------------
# Ruta para consultar las estancias
@main.route('/consultar_estancias', methods=['GET'])
def consultar_estancias():
    estancias = RegistroEstancias.query.all()
    return render_template('consultar_estancias.html', estancias=estancias)

# Plazas ---------------------------------------------------------------------------------------------------------------
# Ruta para mostrar el estado de las plazas
@main.route('/consultar_plazas', methods=['GET'])
def consultar_plazas():
    plazas = Plazas.query.all()
    return render_template('consultar_plazas.html', plazas=plazas)

# Eliminaciones --------------------------------------------------------------------------------------------------------
# Ruta para eliminar un vehículo
@main.route('/eliminar_vehiculo', methods=['GET', 'POST'])
def eliminar_vehiculo():
    if request.method == 'POST':
        placa = request.form['placa']

        # Buscar el vehículo por placa
        vehiculo = Vehiculos.query.filter_by(placa=placa).first()
        if not vehiculo or vehiculo.activo==False:
            return "El vehiculo no fue encontrado.", 404
        if vehiculo.id_plaza is not None:
            return "El vehiculo no puede ser eliminado porque está estacionado.", 404
    
        vehiculo.activo=False
        db.session.commit()

        # Revisar si el dueño tiene más vehículos registrados
        vehiculo_duenio = Vehiculos.query.filter_by(id_duenio=vehiculo.id_duenio, activo=True).first()
        if not vehiculo_duenio:
            duenio = Duenios.query.get(vehiculo.id_duenio)
            duenio.activo=False
            db.session.commit()

        if session.get('usuario') == 'admin':
            return render_template('menu_admin.html')
        else:
            return render_template('menu.html')
    return render_template('eliminar_vehiculo.html')

# Ruta para eliminar un empleado
@main.route('/eliminar_empleado', methods=['GET', 'POST'])
def eliminar_empleado():
    if request.method == 'POST':
        cedula = request.form['cedula']

        # Buscar el empleado por cedula
        empleado = Empleados.query.filter_by(cedula=cedula).first()
        if not empleado or empleado.activo==False:
            return "El empleado no fue encontrado.", 404
        
        empleado.activo=False

        # Revisar si el empleado es usuario
        usuario = Usuarios.query.filter_by(id_empleado=empleado.id_empleado).first()
        if usuario:
            usuario.activo=False
        db.session.commit()

        return render_template('menu_admin.html')
    
    return render_template('eliminar_empleado.html')