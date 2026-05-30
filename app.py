from asyncio.windows_events import NULL

from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


app = Flask(__name__)
app.secret_key = 'clave_secreta_ganaderia_el_rosario_2026'

def get_db_connection():
    conn = sqlite3.connect('usuarios.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Verificar e inyectar 'costo_reparacion' en la tabla 'incidencias'
    try:
        cursor.execute("PRAGMA table_info(incidencias);")
        columnas_incidencias = [col[1] for col in cursor.fetchall()]
        if 'costo_reparacion' not in columnas_incidencias:
            cursor.execute("ALTER TABLE incidencias ADD COLUMN costo_reparacion REAL DEFAULT 0;")
            conn.commit()
            print("💡 Columna 'costo_reparacion' inyectada con éxito.")
    except sqlite3.OperationalError as e:
        print(f"Aviso en incidencias: {e}")

    # 2. Verificar e inyectar 'fecha_compra' en la tabla 'historial_bodega' (CORRECCIÓN DEL ERROR)
    try:
        cursor.execute("PRAGMA table_info(historial_bodega);")
        columnas_bodega = [col[1] for col in cursor.fetchall()]
        if 'fecha_compra' not in columnas_bodega:
            cursor.execute("ALTER TABLE historial_bodega ADD COLUMN fecha_compra TEXT DEFAULT CURRENT_TIMESTAMP;")
            conn.commit()
            print("💡 Columna 'fecha_compra' inyectada con éxito.")
    except sqlite3.OperationalError as e:
        print(f"Aviso en historial_bodega: {e}")
        
    return conn

# --- RUTAS DE ACCESO (LOGIN) ---

# Fórmulas de alimentación basadas en los porcentajes de la tabla (Suma 100%)
FORMULAS_DIETA = {
    'INICIO': {
        'MAIZ ROLADO': 50.5, 'SORGO MOLIDO': 0.0, 'MAIZ MOLIDO': 0.0,
        'PASTA SOYA': 5.0, 'SALVADO DE TRIGO': 5.0, 'ALFALFA': 35.0,
        'MINERALES': 1.5, 'MELAZA': 3.0, 'UREA': 0.0
    },
    'DESARROLLO': {
        'MAIZ ROLADO': 25.0, 'SORGO MOLIDO': 22.0, 'MAIZ MOLIDO': 0.0,
        'PASTA SOYA': 10.0, 'SALVADO DE TRIGO': 8.0, 'ALFALFA': 30.0,
        'MINERALES': 1.5, 'MELAZA': 3.0, 'UREA': 0.5
    },
    'ENGORDA': {
        'MAIZ ROLADO': 25.0, 'SORGO MOLIDO': 10.0, 'MAIZ MOLIDO': 25.0,
        'PASTA SOYA': 5.0, 'SALVADO DE TRIGO': 5.0, 'ALFALFA': 25.0,
        'MINERALES': 1.5, 'MELAZA': 3.0, 'UREA': 0.5
    }
}

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        password = request.form['password']
        db = get_db_connection()
        user = db.execute('SELECT * FROM usuarios WHERE correo = ?', (correo,)).fetchone()
        db.close()
        if user and check_password_hash(user['password'], password):
            session.update({'user_id': user['id'], 'rol': user['rol'], 'correo': user['correo']})
            return redirect(url_for('dashboard'))
        flash('Correo o contraseña incorrecta')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'rol' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', rol=session['rol'])

# --- GESTIÓN DE USUARIOS (SOLO DUEÑO) ---

@app.route('/empleados')
def lista_empleados():
    if session.get('rol') != 'dueño':
        return redirect(url_for('dashboard'))
    
    db = get_db_connection()
    empleados = db.execute('SELECT * FROM usuarios').fetchall()
    
    # Esta consulta une TAREAS con USUARIOS para sacar el nombre en el semáforo
    tareas_globales = db.execute('''
        SELECT t.*, u.correo as nombre_empleado 
        FROM tareas t 
        JOIN usuarios u ON t.empleado_id = u.id 
        ORDER BY t.fecha_creacion DESC
    ''').fetchall()
    
    db.close()
    return render_template('empleados.html', empleados=empleados, tareas_globales=tareas_globales)

# Cambia /empleados/nuevo por /empleados/agregar para sincronizarlo con el HTML
@app.route('/empleados/agregar', methods=['POST'])
def nuevo_empleado():
    if session.get('rol') != 'dueño': return redirect(url_for('dashboard'))
    correo = request.form['correo']
    password = generate_password_hash(request.form['password'])
    rol = request.form['rol']
    db = get_db_connection()
    try:
        db.execute('INSERT INTO usuarios (correo, password, rol) VALUES (?, ?, ?)', (correo, password, rol))
        db.commit()
        flash(f"Usuario {rol} creado con éxito.")
    except sqlite3.IntegrityError:
        flash("El correo ya existe.")
    db.close()
    return redirect(url_for('lista_empleados'))
# --- REGISTRO DE ARRIBO ---

# ==========================================
#        MÓDULO DE ARRIBO DE GANADO
# ==========================================

# ==========================================
#        MÓDULO DE ARRIBO DE GANADO
# ==========================================

@app.route('/arribo', methods=['GET', 'POST'])
def gestionar_modulo_arribo():
    if 'rol' not in session:
        return redirect(url_for('login'))
        
    db = get_db_connection()
    
    if request.method == 'POST':
        # === CASO 1: SI EL USUARIO DA CLIC EN FIJAR PRECIO ===
        if 'nuevo_precio' in request.form:
            corral_id = request.form.get('corral_id')
            nuevo_precio = request.form.get('nuevo_precio')
            try:
                # Actualizar el precio usando tu columna real
                db.execute('UPDATE corrales SET precio_actual = ? WHERE id = ?', (nuevo_precio, corral_id))
                db.commit()
                flash(f"💰 ¡Precio fijado con éxito para el Corral {corral_id}!", "success")
            except sqlite3.Error as e:
                db.rollback()
                flash(f"❌ Error al guardar precio: {str(e)}", "error")
            finally:
                db.close()
            # Cortamos la ejecución aquí mismo para que NO intente registrar ningún animal
            return redirect(url_for('gestionar_modulo_arribo'))

        # === CASO 2: REGISTRO DE ARRIBO ANIMAL (TU CÓDIGO ORIGINAL SIN TOCAR) ===
        arete = request.form.get('arete', '').strip().upper()
        peso_form = request.form.get('peso', '').strip()
        genero = request.form.get('genero')
        procedencia = request.form.get('procedencia', '').strip().upper()  # Protegido contra None con el ''
        tipo_venta = request.form.get('tipo_venta', 'ABASTO')
        
        peso = float(peso_form) if peso_form else 0.0
        
        if peso >= 400.0:
            etapa_calculada = 'ENGORDA'
        elif peso >= 300.0:
            etapa_calculada = 'DESARROLLO'
        else:
            etapa_calculada = 'INICIO'

        # Validar si el animal ya existe
        animal_activo = db.execute('SELECT arete FROM animales WHERE UPPER(arete) = ?', (arete,)).fetchone()
        if animal_activo:
            db.close()
            flash(f"⚠️ El arete {arete} ya está registrado en el inventario activo.", "error")
            return redirect(url_for('gestionar_modulo_arribo'))

        # Asignación de corral con espacio
        corral_destino = db.execute('''
            SELECT c.id FROM corrales c
            WHERE c.tipo_venta = ? AND (
                c.etapa_actual = 'VACIO' OR (
                    c.etapa_actual = ? AND 
                    c.genero_actual = ? AND 
                    c.procedencia_actual = ? AND
                    (SELECT COUNT(*) FROM animales WHERE corral_id = c.id) < c.capacidad_max
                )
            )
            ORDER BY c.id ASC LIMIT 1
        ''', (tipo_venta, etapa_calculada, genero, procedencia)).fetchone()

        if not corral_destino:
            db.close()
            flash(f"⚠️ Alerta: No hay espacio disponible para etapa {etapa_calculada}.", "error")
            return redirect(url_for('gestionar_modulo_arribo'))
            
        c_id = corral_destino['id']
        fecha_hoy = datetime.now().strftime('%Y-%m-%d')

        try:
            # Insertar animal vinculando su precio de compra al 'precio_actual' del corral
            db.execute('''
                INSERT INTO animales (arete, peso, genero, etapa, procedencia, corral_id, fecha_arribo, precio_compra)
                VALUES (?, ?, ?, ?, ?, ?, ?, (SELECT precio_actual FROM corrales WHERE id = ?))
            ''', (arete, peso, genero, etapa_calculada, procedencia, c_id, fecha_hoy, c_id))
            
            db.execute('''
                UPDATE corrales 
                SET genero_actual = ?, procedencia_actual = ?, etapa_actual = ?
                WHERE id = ?
            ''', (genero, procedencia, etapa_calculada, c_id))
            
            db.commit()
            flash(f"✅ ¡Arribo Exitoso! Animal {arete} asignado al Corral {c_id}.", "success")
            
        except sqlite3.Error as e:
            db.rollback()
            flash(f"❌ Error crítico: {str(e)}", "error")
            
        db.close()
        return redirect(url_for('gestionar_modulo_arribo'))

    # --- MÉTODO GET: TUS CONSULTAS ORIGINALES ---
    db.execute('CREATE TABLE IF NOT EXISTS proveedores (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE)')
    db.commit()

    proveedores = db.execute('SELECT * FROM proveedores ORDER BY nombre ASC').fetchall()
    
    corrales_info = db.execute('''
        SELECT c.id, c.capacidad_max, c.precio_actual, c.genero_actual, c.procedencia_actual, c.etapa_actual, c.tipo_venta, COUNT(a.arete) as ocupados 
        FROM corrales c
        LEFT JOIN animales a ON c.id = a.corral_id
        GROUP BY c.id
        ORDER BY c.id ASC
    ''').fetchall()
    
    corrales_activos = db.execute('''
        SELECT DISTINCT c.id, c.precio_actual, c.tipo_venta, COUNT(a.arete) as ocupados
        FROM corrales c
        INNER JOIN animales a ON c.id = a.corral_id
        GROUP BY c.id
        ORDER BY c.id ASC
    ''').fetchall()
    
    db.close()
    
    return render_template('arribo.html', 
                           proveedores=proveedores, 
                           corrales=corrales_info, 
                           corrales_activos=corrales_activos)

@app.route('/agregar_proveedor', methods=['POST'])
def agregar_proveedor():
    nombre = request.form.get('nombre_proveedor', '').strip().upper()
    if nombre:
        db = get_db_connection()
        db.execute('CREATE TABLE IF NOT EXISTS proveedores (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE)')
        db.execute('INSERT OR IGNORE INTO proveedores (nombre) VALUES (?)', (nombre,))
        db.commit()
        db.close()
    # CORREGIDO: Apunta a la función correcta que renderiza la vista de arribo
    return redirect(url_for('gestionar_modulo_arribo'))

@app.route('/inventario')
def ver_inventario():
    if 'rol' not in session: 
        return redirect(url_for('login'))
    
    db = get_db_connection()
    # Cambiamos a INNER JOIN para excluir automáticamente los corrales vacíos
    corrales_query = '''
        SELECT c.id, c.capacidad_max, c.genero_actual, c.etapa_actual, c.procedencia_actual, c.tipo_venta, c.precio_actual,
               COUNT(a.arete) as ocupados,
               (c.capacidad_max - COUNT(a.arete)) as disponible
        FROM corrales c 
        INNER JOIN animales a ON c.id = a.corral_id 
        GROUP BY c.id
        ORDER BY c.id ASC
    '''
    corrales = db.execute(corrales_query).fetchall()
    db.close()
    
    return render_template('inventario_corrales.html', corrales=corrales)

# --- RUTA PARA EL EMPLEADO: VER Y FINALIZAR ---

@app.route('/limpiar_seguro', methods=['POST'])
def limpiar_seguro():
    if 'rol' not in session or session.get('rol') != 'dueño':
        flash("❌ Acción no autorizada. Solo el dueño puede realizar esta limpieza.", "error")
        return redirect(url_for('dashboard'))
        
    correo_verificar = request.form.get('correo_verificar', '').strip()
    pass_verificar = request.form.get('pass_verificar', '').strip()
    
    db = get_db_connection()
    
    # 1. Verificar credenciales del usuario administrador por seguridad
    usuario_actual = db.execute('SELECT * FROM usuarios WHERE correo = ?', (correo_verificar,)).fetchone()
    
    if not usuario_actual or not check_password_hash(usuario_actual['password'], pass_verificar):
        db.close()
        flash("❌ Credenciales de administrador incorrectas. No se realizó ninguna acción.", "error")
        return redirect(url_for('ver_inventario'))
        
    try:
        # ========================================================
        #   TRANSTACCIÓN DE RESETEO TOTAL DE FÁBRICA (EL ROSARIO)
        # ========================================================
        
        # LOGÍSTICA DE GANADO Y LOGS OPERATIVOS
        db.execute('DELETE FROM animales') # Vacía el inventario físico de vacas
        db.execute('DELETE FROM ventas') # Borra el historial analítico de ventas pasadas
        db.execute('DELETE FROM incidencias') # Limpia el registro de alertas e imprevistos
        db.execute('DELETE FROM tareas') # Elimina las órdenes del semáforo de labores
        db.execute('DELETE FROM historial_bodega') # Borra el registro contable de compras de insumos
        db.execute('DELETE FROM historial_clinico') # Limpia el registro de inyecciones veterinarias

        # RESETEO DE LOS 25 CORRALES
        db.execute('''
            UPDATE corrales 
            SET precio_actual = 0.0, 
                etapa_actual = 'VACIO', 
                genero_actual = NULL, 
                procedencia_actual = NULL
        ''')
        
        # VACIADO Y REINICIO DE BODEGA DE ALIMENTOS (DIETAS)
        db.execute('DELETE FROM bodega') # Limpia cualquier stock residual acumulado
        # Opcional: Si deseas que la tabla 'bodega' inicialice con las materias primas listas en 0 kg:
        ingredientes_base = [
            'MAIZ ROLADO', 'SORGO MOLIDO', 'MAIZ MOLIDO', 'PASTA SOYA', 
            'SALVADO DE TRIGO', 'ALFALFA', 'MINERALES', 'MELAZA', 'UREA'
        ]
        for ing in ingredientes_base:
            db.execute('INSERT OR IGNORE INTO bodega (ingrediente, cantidad_kg) VALUES (?, 0.0)', (ing,))

        # RESETEO DE FARMACIA LÍQUIDA (MEDICAMENTOS)
        db.execute('DELETE FROM bodega_medicamentos') # Limpia el catálogo actual
        # Reinyectamos el catálogo clínico base con stock inicial en 0.0 ml
        medicamentos_defecto = [
            ('CEFTIOFUR 5%', 'Antibiótico para neumonías y piatín (gabarro).', 0.0, '1 ml por cada 50 kg de peso'),
            ('IVERMECTINA 1%', 'Desparasitante completo para limpiar ganado al arribo.', 0.0, '1 ml por cada 50 kg de peso'),
            ('FLUNIXIN MEGLUMINE', 'Antiinflamatorio y analgésico para bajar la fiebre.', 0.0, '2 ml por cada 45 kg de peso'),
            ('COMPLEJO B + HIERRO', 'Vitamínico para abrir el apetito y acelerar engorde.', 0.0, '5 a 10 ml totales por animal'),
            ('OTRO / NUEVO MEDICAMENTO', 'Opción para registrar una solución externa manual.', 0.0, 'Especificar dosis manualmente')
        ]
        for nombre, desc, cant, dosis in medicamentos_defecto:
            db.execute('''
                INSERT INTO bodega_medicamentos (nombre, descripcion, cantidad_ml, dosis_recomendada)
                VALUES (?, ?, ?, ?)
            ''', (nombre, desc, cant, dosis))

        # CONTROL DE ACCESOS: BORRADO Y ALTA DEL MAESTRO
        db.execute('DELETE FROM usuarios')
        
        usuario_maestro_correo = 'aj.martinez.gonzalez@ugto.mx'
        usuario_maestro_pass_encriptada = generate_password_hash('123456789')
        usuario_maestro_rol = 'dueño'
        
        db.execute('''
            INSERT INTO usuarios (correo, password, rol) 
            VALUES (?, ?, ?)
        ''', (usuario_maestro_correo, usuario_maestro_pass_encriptada, usuario_maestro_rol))
        
        # Guardar todos los cambios estructurales de forma atómica
        db.commit()
        
        # Destruir la sesión actual para obligar el re-ingreso con la cuenta limpia
        session.clear()
        flash("⚠️ Reinicio Completo: Inventarios, Bodegas, Historiales y Finanzas reestablecidos a cero. Cuenta maestra activa.", "success")
        return redirect(url_for('login'))
        
    except sqlite3.Error as e:
        db.rollback()
        flash(f"❌ Error crítico en purga de datos: {str(e)}", "error")
        db.close()
        return redirect(url_for('dashboard'))

# --- RUTA PARA EL DUEÑO: CREAR TAREA ---
@app.route('/tareas/crear', methods=['POST'])
def crear_tarea():
    if session.get('rol') != 'dueño': 
        return redirect(url_for('dashboard'))
    
    empleado_id = request.form.get('empleado_id')
    descripcion = request.form.get('descripcion')
    
    db = get_db_connection()
    # Usamos el estándar del semáforo: ROJO
    db.execute('INSERT INTO tareas (empleado_id, descripcion, estado) VALUES (?, ?, ?)', 
               (empleado_id, descripcion, 'ROJO'))
    db.commit()
    db.close()
    flash("✅ Labor asignada al semáforo")
    return redirect(url_for('mis_tareas'))

# --- RUTA PARA CAMBIO DE ESTADO (SEMÁFORO) ---
@app.route('/tareas/estado/<int:id>/<nuevo_estado>')
def cambiar_estado_tarea(id, nuevo_estado):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    db = get_db_connection()
    # El empleado actualiza a AMARILLO o VERDE
    db.execute('UPDATE tareas SET estado = ? WHERE id = ?', (nuevo_estado, id))
    db.commit()
    db.close()
    
    return redirect(url_for('mis_tareas'))

# --- VISTA DE TAREAS (Sincronizada) ---
@app.route('/mis_tareas')
def mis_tareas():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db_connection()
    hoy = datetime.now().strftime('%Y-%m-%d')

    if session['rol'] == 'dueño':
        # 1. Consulta el historial completo para el dueño
        tareas = db.execute('''
            SELECT t.id, t.descripcion, t.estado, t.fecha_creacion, u.correo 
            FROM tareas t 
            JOIN usuarios u ON t.empleado_id = u.id
            ORDER BY t.fecha_creacion DESC
        ''').fetchall()
        
        # NUEVO: Traemos la lista de empleados para el formulario de asignación
        empleados = db.execute('SELECT id, correo, rol FROM usuarios').fetchall()
        db.close()
        return render_template('mis_tareas.html', tareas=tareas, empleados=empleados)
        
    else:
        # El empleado sigue viendo únicamente sus labores del día[cite: 18]
        tareas = db.execute('''
            SELECT * FROM tareas 
            WHERE empleado_id = ? AND DATE(fecha_creacion) = ?
            ORDER BY fecha_creacion DESC
        ''', (session['user_id'], hoy)).fetchall()
        db.close()
        return render_template('mis_tareas.html', tareas=tareas)

@app.route('/ver_incidencias')
def ver_incidencias():
    if session.get('rol') != 'dueño': return redirect(url_for('dashboard'))
    
    db = get_db_connection()
    reportes = db.execute('''
        SELECT i.*, u.correo 
        FROM incidencias i 
        JOIN usuarios u ON i.empleado_id = u.id 
        ORDER BY i.fecha DESC
    ''').fetchall()
    db.close()
    return render_template('ver_incidencias.html', reportes=reportes)

@app.route('/incidencia/revisar/<int:id>')
def revisar_incidencia(id):
    if session.get('rol') != 'dueño': 
        return redirect(url_for('dashboard'))
    
    db = get_db_connection()
    db.execute('UPDATE incidencias SET estado = "REVISADO" WHERE id = ?', (id,))
    db.commit()
    db.close()
    
    flash("✅ Incidencia marcada como atendida")
    return redirect(url_for('ver_incidencias'))

@app.route('/reportar_incidencia', methods=['GET', 'POST'])
def reportar_incidencia():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    db = get_db_connection()
    
    if request.method == 'POST':
        tipo = request.form.get('tipo')
        
        # CORRECCIÓN DE BUG: Validamos si el campo viene vacío para evitar el truene de float
        costo_form = request.form.get('costo_reparacion', '').strip()
        costo_reparacion = float(costo_form) if costo_form else 0.0
        
        descripcion_adicional = request.form.get('descripcion', '')
        descripcion = descripcion_adicional
        
        if tipo == 'Faltante de Insumo':
            alimento = request.form.get('alimento_faltante')
            descripcion = f"FALTA: {alimento} | {descripcion_adicional}"
        elif tipo == 'OTRO':
            tipo = request.form.get('tipo_otro').strip().upper()
            descripcion = descripcion_adicional
        elif tipo == 'ANIMAL MUERTO' or tipo == 'Animal Enfermo':
            arete = request.form.get('arete')
            descripcion = f"ARETE: {arete} | {descripcion_adicional}" if arete else descripcion_adicional
            
            # AUTOMATIZACIÓN FINANCIERA: Si es animal muerto, calculamos su pérdida real
            if tipo == 'ANIMAL MUERTO' and arete:
                # Buscamos el peso del animal y el precio configurado en su corral
                datos_animal = db.execute('''
                    SELECT a.peso, c.precio_actual 
                    FROM animales a
                    INNER JOIN corrales c ON a.corral_id = c.id
                    WHERE a.arete = ?
                ''', (arete,)).fetchone()
                
                if datos_animal:
                    peso = datos_animal['peso'] or 0
                    precio_kilo = datos_animal['precio_actual'] or 0
                    # Si el precio del corral es 0 porque no se fijó, usamos 0 para evitar pérdidas infladas
                    costo_reparacion = peso * precio_kilo
                    descripcion += f" (Pérdida financiera calculada automáticamente: ${costo_reparacion:,.2f})"
        
        emp_id = session['user_id']
        
        # 1. Guardamos el reporte en la tabla de incidencias con su costo correspondiente
        db.execute('''
            INSERT INTO incidencias (empleado_id, tipo, descripcion, costo_reparacion) 
            VALUES (?, ?, ?, ?)
        ''', (emp_id, tipo, descripcion, costo_reparacion))
        
        # 2. Si fue un cadáver, lo removemos del inventario activo de los corrales
        if tipo == 'ANIMAL MUERTO' and request.form.get('arete'):
            db.execute('DELETE FROM animales WHERE arete = ?', (request.form.get('arete'),))
            
        db.commit()
        db.close()
        flash("✅ Reporte de incidencia procesado correctamente en el sistema.")
        return redirect(url_for('dashboard'))
    
    insumos = db.execute('SELECT ingrediente FROM bodega').fetchall()
    db.close()
    return render_template('reportar_incidencia.html', insumos=insumos)

@app.route('/inventario/buscar')
def buscar_inventario():
    query = request.args.get('q', '')
    db = get_db_connection()
    
    # Esta es la consulta corregida que hace el JOIN con la tabla corrales
    # para traer el 'precio_actual' que fijaste.
    resultados = db.execute('''
        SELECT a.*, c.precio_actual 
        FROM animales a
        JOIN corrales c ON a.corral_id = c.id
        WHERE a.arete LIKE ? OR a.procedencia LIKE ?
    ''', ('%' + query + '%', '%' + query + '%')).fetchall()
    
    db.close()
    return render_template('inventario_busqueda.html', animales=resultados, query=query)

@app.route('/actualizar_precio_corral', methods=['POST'])
def actualizar_precio_corral():
    if session.get('rol') != 'dueño':
        flash("Acceso denegado.")
        return redirect(url_for('gestionar_modulo_arribo'))  # ← Cambiado de 'registrar_arribo'

    corral_id = request.form.get('corral_id')
    nuevo_precio = request.form.get('nuevo_precio')
    
    db = get_db_connection()
    # Consultamos el precio actual en la base de datos
    corral = db.execute('SELECT precio_actual FROM corrales WHERE id = ?', (corral_id,)).fetchone()

    # Si el precio actual ya es mayor a 0, rechazamos cualquier intento de cambio
    if corral['precio_actual'] > 0:
        flash(f"❌ El precio del Corral {corral_id} ya está bloqueado.")
    else:
        db.execute('UPDATE corrales SET precio_actual = ? WHERE id = ?', (nuevo_precio, corral_id))
        db.commit()
        flash(f"✅ Precio fijado correctamente.")
    
    db.close()
    return redirect(url_for('gestionar_modulo_arribo'))  # ← Cambiado aquí también

@app.route('/inventario/corral/<int:id>')
def detalle_corral(id):
    if 'rol' not in session: 
        return redirect(url_for('login'))
        
    db = get_db_connection()
    
    # Esta consulta es la correcta: trae los datos del animal 
    # Y el precio_actual que pertenece a su corral
    animales = db.execute('''
        SELECT a.arete, a.peso, a.genero, a.etapa, a.procedencia, c.precio_actual 
        FROM animales a
        JOIN corrales c ON a.corral_id = c.id
        WHERE a.corral_id = ?
    ''', (id,)).fetchall()
    
    db.close()
    return render_template('detalle_corral.html', corral_id=id, animales=animales)

@app.route('/alimentacion')
def menu_alimentacion():
    if 'rol' not in session: return redirect(url_for('login'))
    
    db = get_db_connection()
    # Solo listamos corrales que tengan animales para alimentar
    corrales = db.execute('''
        SELECT c.*, COUNT(a.arete) as ocupados 
        FROM corrales c 
        INNER JOIN animales a ON c.id = a.corral_id 
        GROUP BY c.id ORDER BY c.id ASC
    ''').fetchall()
    db.close()
    return render_template('alimentacion_menu.html', corrales=corrales)

@app.route('/alimentacion/calcular/<int:corral_id>')
def calcular_racion(corral_id):
    if 'rol' not in session: return redirect(url_for('login'))
    
    db = get_db_connection()
    
    # 1. Obtener datos clave del corral y sus animales
    corral_info = db.execute('SELECT * FROM corrales WHERE id = ?', (corral_id,)).fetchone()
    animales = db.execute('SELECT peso FROM animales WHERE corral_id = ?', (corral_id,)).fetchall()
    
    if not animales:
        db.close()
        flash("❌ El corral está vacío.")
        return redirect(url_for('menu_alimentacion'))
        
    # 2. Calcular Peso Total y Consumo Total (3% del Peso Vivo)
    peso_total_corral = sum([animal['peso'] for animal in animales])
    consumo_total_kg = peso_total_corral * 0.03
    
    # 3. Obtener la etapa asignada al corral
    etapa = corral_info['etapa_actual']
    if etapa not in FORMULAS_DIETA:
        etapa = 'INICIO' # Salvaguarda por si acaso
        
    formula_aplicada = FORMULAS_DIETA[etapa]
    
    # 4. Calcular los kilos requeridos por cada ingrediente
    desglose_alimento = []
    for ingrediente, porcentaje in formula_aplicada.items():
        if porcentaje > 0:
            kilos_ingrediente = (porcentaje / 100.0) * consumo_total_kg
            desglose_alimento.append({
                'nombre': ingrediente,
                'porcentaje': porcentaje,
                'kilos': round(kilos_ingrediente, 2)
            })
            
    db.close()
    return render_template('alimentacion_calculo.html', 
                           corral_id=corral_id,
                           total_animales=len(animales),
                           peso_total=round(peso_total_corral, 2),
                           consumo_total=round(consumo_total_kg, 2),
                           etapa=etapa,
                           alimentos=desglose_alimento)

@app.route('/ventas', methods=['GET', 'POST'])
def gestionar_ventas():
    if 'rol' not in session:
        return redirect(url_for('login'))
        
    db = get_db_connection()
    
    if request.method == 'POST':
        # Sincronizado con name="selector_modalidad" de tu nuevo ventas.html
        modalidad = request.form.get('selector_modalidad')
        precio_kg = float(request.form.get('precio_kilo', 0))
        comprador = request.form.get('comprador', '').strip().upper()
        
        if modalidad == 'LOTE':
            corral_id = request.form.get('corral_id')
            peso_total = float(request.form.get('peso_total', 0))
            total_venta = peso_total * precio_kg
            
            # 1. Registrar la venta del lote completo incluyendo al comprador
            db.execute('''
                INSERT INTO ventas (modalidad, corral_id, peso_total, precio_kg, total_venta)
                VALUES (?, ?, ?, ?, ?)
            ''', ('LOTE', corral_id, peso_total, precio_kg, total_venta))
            
            # 2. Vaciar el corral eliminando físicamente los animales de la tabla activos
            db.execute('DELETE FROM animales WHERE corral_id = ?', (corral_id,))
            
            # 3. Resetear y liberar el corral para futuros arribos comerciales
            db.execute('''
                UPDATE corrales 
                SET precio_actual = 0, procedencia_actual = NULL, genero_actual = NULL, etapa_actual = 'VACIO' 
                WHERE id = ?
            ''', (corral_id,))
            
            db.commit()
            flash(f'✅ Venta por LOTE del Corral {corral_id} registrada con éxito por ${total_venta:,.2f}. Corral liberado.', 'success')
            
        elif modalidad == 'ABASTO':
            # Sincronizado con los checkboxes del HTML
            aretes_seleccionados = request.form.getlist('aretes_abasto')
            
            if not aretes_seleccionados:
                flash('❌ Error: Debe seleccionar al menos un arete usando los casilleros o el buscador.', 'error')
            else:
                placeholders = ','.join('?' for _ in aretes_seleccionados)
                
                query_peso = f'SELECT TOTAL(peso) FROM animales WHERE arete IN ({placeholders})'
                peso_total = db.execute(query_peso, aretes_seleccionados).fetchone()[0] or 0.0
                total_venta = peso_total * precio_kg
                
                # Convertimos la lista de aretes ['42552005', '42552006'] a una cadena de texto: "42552005, 42552006"
                lista_aretes_texto = ", ".join(aretes_seleccionados)
                
                query_corrales = f'SELECT DISTINCT corral_id FROM animales WHERE arete IN ({placeholders})'
                corrales_afectados = db.execute(query_corrales, aretes_seleccionados).fetchall()
                corrales_ids = [c['corral_id'] for c in corrales_afectados if c['corral_id'] is not None]

                # CORREGIDO: Ahora pasamos 'lista_aretes_texto' a la columna 'detalles' en el INSERT
                db.execute('''
                    INSERT INTO ventas (modalidad, corral_id, peso_total, precio_kg, total_venta, detalles)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', ('ABASTO', None, peso_total, precio_kg, total_venta, lista_aretes_texto))
                
                db.execute(f'DELETE FROM animales WHERE arete IN ({placeholders})', aretes_seleccionados)
                
                for c_id in corrales_ids:
                    conteo = db.execute('SELECT COUNT(*) FROM animales WHERE corral_id = ?', (c_id,)).fetchone()[0]
                    if conteo == 0:
                        db.execute('''
                            UPDATE corrales 
                            SET precio_actual = 0, procedencia_actual = NULL, genero_actual = NULL, etapa_actual = 'VACIO' 
                            WHERE id = ?
                        ''', (c_id,))
                
                db.commit()
                flash(f'✅ Venta de ABASTO procesada. Despachados {len(aretes_seleccionados)} animales.', 'success')
        return redirect(url_for('gestionar_ventas'))

    # --- MÉTODO GET: RENDERIZADO DE LA INTERFAZ AZUL ---
    # Traemos todos los animales vivos cuya modalidad de corral sea de venta al ABASTO
    animales_disponibles = db.execute('''
        SELECT a.arete, a.corral_id, a.peso 
        FROM animales a
        INNER JOIN corrales c ON a.corral_id = c.id
        WHERE c.tipo_venta = 'ABASTO'
        ORDER BY a.arete ASC
    ''').fetchall()
    
    # Traemos también los corrales activos configurados como LOTE para el llenado del selector superior
    corrales_lote = db.execute('''
        SELECT c.id, c.procedencia_actual, COUNT(a.arete) as ocupados
        FROM corrales c
        INNER JOIN animales a ON c.id = a.corral_id
        WHERE c.tipo_venta = 'LOTE'
        GROUP BY c.id
    ''').fetchall()
    
    # Historial analítico cronológico de transacciones para la tabla inferior
    # Cambiado SUM() por TOTAL() en concordancia con la optimización de la calculadora
    ventas = db.execute('''
        SELECT id, modalidad, corral_id, peso_total, precio_kg, total_venta, fecha_venta 
        FROM ventas 
        ORDER BY fecha_venta DESC
    ''').fetchall()
    
    db.close()
    
    # Enviamos las variables exactas que tu nuevo 'ventas.html' necesita ('animales' y 'corrales_lote')
    return render_template('ventas.html', 
                           animales=animales_disponibles, 
                           corrales_lote=corrales_lote, 
                           ventas=ventas)

# --- MÓDULO DE BODEGA DE MEDICAMENTOS ---
# --- MODIFICACIÓN DE LA RUTA BODEGA EXISTENTE ---

@app.route('/bodega', methods=['GET', 'POST'])
def gestionar_bodega():
    if 'rol' not in session: 
        return redirect(url_for('login'))
        
    db = get_db_connection()
    
    # Garantizar que existan las tablas básicas de control de stock
    db.execute('''
        CREATE TABLE IF NOT EXISTS bodega (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            ingrediente TEXT UNIQUE NOT NULL, 
            cantidad_kg REAL DEFAULT 0
        )
    ''')
    db.execute('''
        CREATE TABLE IF NOT EXISTS historial_bodega (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_insumo TEXT NOT NULL,
            nombre_articulo TEXT NOT NULL,
            cantidad_ingresada REAL NOT NULL,
            costo_total REAL NOT NULL,
            fecha_compra TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    if request.method == 'POST':
        tipo_insumo = request.form.get('tipo_insumo')
        
        if tipo_insumo == 'DIETA':
            ingrediente = request.form.get('ingrediente')
            cantidad = float(request.form.get('cantidad', 0))
            precio_kg = float(request.form.get('precio_por_kg', 0))
            
            # Cálculo de la erogación financiera de esta compra específica
            costo_total = cantidad * precio_kg
            
            # 1. Actualizar existencias actuales en el almacén de stock
            db.execute('UPDATE bodega SET cantidad_kg = cantidad_kg + ? WHERE ingrediente = ?', (cantidad, ingrediente))
            
            # 2. Registrar el gasto en el historial cronológico para las finanzas
            db.execute('''
                INSERT INTO historial_bodega (tipo_insumo, nombre_articulo, cantidad_ingresada, costo_total)
                VALUES ('DIETA', ?, ?, ?)
            ''', (ingrediente, cantidad, costo_total))
            
            db.commit()
            flash(f"✅ Stock de alimento actualizado. Costo total registrado: ${costo_total:,.2f}")
            
        elif tipo_insumo == 'MEDICAMENTO':
            med_id = request.form.get('medicamento_id')
            cantidad_ml = float(request.form.get('cantidad_ml', 0))
            precio_litro = float(request.form.get('precio_por_litro', 0))
            
            # Cálculo de la erogación (Mililitros convertidos a Litros para multiplicar por precio/L)
            costo_total = (cantidad_ml / 1000.0) * precio_litro
            nombre_articulo = ""
            
            # Si eligen registrar un medicamento nuevo/externo utilizando "OTRO"
            if med_id == "5" or request.form.get('nombre_nuevo_med'):
                nombre_nuevo = request.form.get('nombre_nuevo_med', '').strip().upper()
                if nombre_nuevo:
                    nombre_articulo = nombre_nuevo
                    try:
                        db.execute('''
                            INSERT INTO bodega_medicamentos (nombre, descripcion, cantidad_ml, dosis_recomendada)
                            VALUES (?, 'Medicamento personalizado agregado externamente.', ?, 'Especificar dosis')
                        ''', (nombre_nuevo, cantidad_ml))
                    except sqlite3.IntegrityError:
                        db.execute('UPDATE bodega_medicamentos SET cantidad_ml = cantidad_ml + ? WHERE nombre = ?', (cantidad_ml, nombre_nuevo))
            else:
                db.execute('UPDATE bodega_medicamentos SET cantidad_ml = cantidad_ml + ? WHERE id = ?', (cantidad_ml, med_id))
                row = db.execute('SELECT nombre FROM bodega_medicamentos WHERE id = ?', (med_id,)).fetchone()
                nombre_articulo = row['nombre'] if row else "MEDICAMENTO"
                
            # Registrar el gasto en el historial cronológico para las finanzas
            db.execute('''
                INSERT INTO historial_bodega (tipo_insumo, nombre_articulo, cantidad_ingresada, costo_total)
                VALUES ('MEDICAMENTO', ?, ?, ?)
            ''', (nombre_articulo, cantidad_ml, costo_total))
            
            db.commit()
            flash(f"✅ Farmacia actualizada. Costo total registrado: ${costo_total:,.2f}")
            
        db.close()
        return redirect(url_for('gestionar_bodega'))

    # --- MÉTODO GET: Renderizado Seguro de la Interfaz ---
    insumos = db.execute('SELECT * FROM bodega').fetchall()
    medicamentos = db.execute('SELECT * FROM bodega_medicamentos').fetchall()
    db.close()
    return render_template('bodega.html', insumos=insumos, medicamentos=medicamentos)
        
    # ... (Tu código actual para el método GET que renderiza la bodega) ...
# ==========================================
#       MÓDULO DE SALUD VETERINARIA
# ==========================================

@app.route('/salud', methods=['GET', 'POST'])
def modulo_salud():
    if 'rol' not in session: 
        return redirect(url_for('login'))
        
    db = get_db_connection()
    
    if request.method == 'POST':
        arete = request.form.get('arete')
        medicamento_id = request.form.get('medicamento_id')
        dosis_ml = float(request.form.get('dosis_ml', 0))
        nombre_extra = request.form.get('nombre_extra_salud', '').strip().upper() # Captura el texto si es "OTRO"
        
        # 1. Validar que el animal exista
        animal = db.execute('SELECT corral_id FROM animales WHERE arete = ?', (arete,)).fetchone()
        if not animal:
            flash(f"❌ Error: El arete '{arete}' no está registrado en el sistema.")
            db.close()
            return redirect(url_for('modulo_salud'))
            
        # 2. Buscar medicamento seleccionado
        med = db.execute('SELECT id, nombre, cantidad_ml FROM bodega_medicamentos WHERE id = ?', (medicamento_id,)).fetchone()
        if not med:
            flash("❌ Error: Medicamento no seleccionado o inválido.")
            db.close()
            return redirect(url_for('modulo_salud'))
            
        try:
            # 3. Descontar volumen consumido (Solo si NO es la opción "OTRO")
            # Si es de los de por defecto y no hay stock, le sumamos 500ml de emergencia para que te deje trabajar
            if med['id'] != 5: # Asumiendo que ID 5 es 'OTRO'
                if med['cantidad_ml'] < dosis_ml:
                    db.execute('UPDATE bodega_medicamentos SET cantidad_ml = cantidad_ml + 500 WHERE id = ?', (med['id'],))
                db.execute('UPDATE bodega_medicamentos SET cantidad_ml = cantidad_ml - ? WHERE id = ?', (dosis_ml, med['id']))
            
            # 4. Registrar la inyección en el historial clínico
            fecha_hoy = datetime.now().strftime('%Y-%m-%d %H:%M')
            db.execute('''
                INSERT INTO historial_clinico (arete, corral_id, medicamento_id, medicamento_nombre_extra, dosis_ml, fecha)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (arete, animal['corral_id'], med['id'], nombre_extra if nombre_extra else None, dosis_ml, fecha_hoy))
            
            db.commit()
            flash(f"💉 ¡Inyección Registrada! Aplicados {dosis_ml} ml al arete {arete}.")
            
        except Exception as e:
            flash(f"❌ Error interno al guardar: {str(e)}")
            
        db.close()
        return redirect(url_for('modulo_salud'))

    # --- MÉTODO GET: Cargar la página ---
    corrales_activos = db.execute('''
        SELECT c.id FROM corrales c
        INNER JOIN animales a ON c.id = a.corral_id
        GROUP BY c.id ORDER BY c.id ASC
    ''').fetchall()
    
    medicamentos = db.execute('SELECT * FROM bodega_medicamentos').fetchall()
    
    # Consulta corregida para el historial (Muestra el nombre extra si se usó "OTRO")
    historial = db.execute('''
        SELECT h.fecha, h.arete, h.corral_id, h.dosis_ml, h.medicamento_nombre_extra, m.nombre as medicamento_nombre
        FROM historial_clinico h
        INNER JOIN bodega_medicamentos m ON h.medicamento_id = m.id
        ORDER BY h.id DESC LIMIT 10
    ''').fetchall()
    
    db.close()
    return render_template('salud.html', corrales=corrales_activos, medicamentos=medicamentos, historial=historial)

# --- API DE SOPORTE PARA BUSCAR ANIMALES POR CORRAL VÍA AJAX ---
@app.route('/api/animales_por_corral/<int:corral_id>')
def api_animales_por_corral(corral_id):
    if 'rol' not in session: 
        return {'animales': []}, 403
    db = get_db_connection()
    animales = db.execute('SELECT arete, peso, etapa, genero FROM animales WHERE corral_id = ?', (corral_id,)).fetchall()
    db.close()
    return {'animales': [dict(a) for a in animales]}

@app.route('/finanzas')
def modulo_calculadora_finanzas():
    if 'rol' not in session:
        return redirect(url_for('login'))
        
    periodo = request.args.get('periodo', 'mes')
    db = get_db_connection()

    # Asegurar tablas analíticas
    db.execute('''
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            modalidad TEXT,
            corral_id INTEGER,
            peso_total REAL,
            precio_kg REAL,
            total_venta REAL,
            fecha_venta TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    db.execute('''
        CREATE TABLE IF NOT EXISTS historial_bodega (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_insumo TEXT NOT NULL,
            nombre_articulo TEXT NOT NULL,
            cantidad_ingresada REAL NOT NULL,
            costo_total REAL NOT NULL,
            fecha_compra TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    db.commit()

    # === CORRECCIÓN DE FILTROS TEMPORALES CRUZADOS ===
    # Formateamos las consultas para que comparen las fechas limpias de tus inserts (YYYY-MM-DD)
    if periodo == 'dia':
        filtro_incidencias = "date(i.fecha) = date('now', 'localtime')"
        filtro_bodega = "date(fecha_compra) = date('now', 'localtime')"
        filtro_animales = "date(a.fecha_arribo) = date('now', 'localtime')"
        filtro_ventas = "date(fecha_venta) = date('now', 'localtime')"
    elif periodo == 'semana':
        filtro_incidencias = "date(i.fecha) >= date('now', 'localtime', '-7 days')"
        filtro_bodega = "date(fecha_compra) >= date('now', 'localtime', '-7 days')"
        filtro_animales = "date(a.fecha_arribo) >= date('now', 'localtime', '-7 days')"
        filtro_ventas = "date(fecha_venta) >= date('now', 'localtime', '-7 days')"
    elif periodo == 'ano':
        filtro_incidencias = "strftime('%Y', i.fecha) = strftime('%Y', 'now', 'localtime')"
        filtro_bodega = "strftime('%Y', fecha_compra) = strftime('%Y', 'now', 'localtime')"
        filtro_animales = "strftime('%Y', a.fecha_arribo) = strftime('%Y', 'now', 'localtime')"
        filtro_ventas = "strftime('%Y', fecha_venta) = strftime('%Y', 'now', 'localtime')"
    else:  # 'mes' por defecto
        filtro_incidencias = "strftime('%Y-%m', i.fecha) = strftime('%Y-%m', 'now', 'localtime')"
        filtro_bodega = "strftime('%Y-%m', fecha_compra) = strftime('%Y-%m', 'now', 'localtime')"
        filtro_animales = "strftime('%Y-%m', a.fecha_arribo) = strftime('%Y-%m', 'now', 'localtime')"
        filtro_ventas = "strftime('%Y-%m', fecha_venta) = strftime('%Y-%m', 'now', 'localtime')"

    # 1. CUADRO ROJO CHICO: Bajas por Mortandad (Costo de incidencias acumulado)
    query_muertes = f"SELECT TOTAL(i.costo_reparacion) FROM incidencias i WHERE i.tipo = 'ANIMAL MUERTO' AND {filtro_incidencias}"
    gasto_muertes = db.execute(query_muertes).fetchone()[0] or 0.0

    # 2. CUADRO MORADO: INVERSIÓN GANADO (Multiplicación exacta de Peso * Precio de Corral Ocupado)
    query_inversion_ganado = f"""
        SELECT TOTAL(a.peso * c.precio_actual) 
        FROM animales a 
        JOIN corrales c ON a.corral_id = c.id
        WHERE {filtro_animales}
    """
    gasto_animales = db.execute(query_inversion_ganado).fetchone()[0] or 0.0

    # 3. GASTOS OPERATIVOS / INFRAESTRUCTURA
    query_infraestructura = f"SELECT TOTAL(i.costo_reparacion) FROM incidencias i WHERE i.tipo != 'ANIMAL MUERTO' AND {filtro_incidencias}"
    gasto_infraestructura = db.execute(query_infraestructura).fetchone()[0] or 0.0
    
    # 4. GASTOS DE BODEGA
    query_bodega = f"SELECT TOTAL(costo_total) FROM historial_bodega WHERE {filtro_bodega}"
    gasto_bodega = db.execute(query_bodega).fetchone()[0] or 0.0

    # 5. CUADRO VERDE: Ganancias en Bruto
    query_ventas = f"SELECT TOTAL(total_venta) FROM ventas WHERE {filtro_ventas}"
    ganancias_bruto = db.execute(query_ventas).fetchone()[0] or 0.0
    
    # 6. CUADRO AZUL: Ganancias Libres (Suma todo de forma exacta y reactiva)
    total_gastos = gasto_animales + gasto_infraestructura + gasto_muertes + gasto_bodega
    ganancias_libres = ganancias_bruto - total_gastos
    
    db.close()
    
    return render_template('finanzas.html', 
                           periodo=periodo,
                           filtro=periodo,
                           gasto_animales=gasto_animales, 
                           gasto_infraestructura=gasto_infraestructura,
                           gasto_muertes=gasto_muertes,
                           gasto_bodega=gasto_bodega,
                           ganancias_bruto=ganancias_bruto,
                           ganancias_libres=ganancias_libres,
                           total_gastos=total_gastos,
                           rol=session.get('rol'))

@app.route('/historial_ventas')
def historial_ventas():
    if 'rol' not in session:
        return redirect(url_for('login'))
        
    db = get_db_connection()
    
    # SALVAGUARDA: Forzamos la inyección de la columna 'detalles' por si no existe en tu base de datos actual
    try:
        db.execute("ALTER TABLE ventas ADD COLUMN detalles TEXT DEFAULT 'Sin especificar';")
        db.commit()
    except sqlite3.OperationalError:
        pass # Si ya existe la columna, ignora el aviso y continúa

    # CORRECCIÓN DEL BUG: Cambiado 'fecha' por 'fecha_venta' que es el nombre real en tu base de datos
    # También cambiamos la columna 'fecha' por 'fecha_venta' dentro del SELECT
    ventas_registradas = db.execute('''
        SELECT id, modalidad, corral_id, total_venta, fecha_venta AS fecha, detalles 
        FROM ventas 
        ORDER BY fecha_venta DESC
    ''').fetchall()
    
    db.close()
    return render_template('historial_ventas.html', ventas=ventas_registradas)

@app.route('/alimentacion/descontar/<int:corral_id>', methods=['POST'])
def descontar_racion_bodega(corral_id):
    if 'rol' not in session:
        return redirect(url_for('login'))
        
    db = get_db_connection()
    
    # Recorremos los nombres de los ingredientes que vienen del formulario enviado
    ingredientes = request.form.getlist('ingrediente_nombre[]')
    kilos_a_descontar = request.form.getlist('ingrediente_kilos[]')
    
    try:
        for ingrediente, kilos in zip(ingredientes, kilos_a_descontar):
            kilos_float = float(kilos)
            if kilos_float > 0:
                # Restar de la tabla bodega el alimento consumido
                db.execute('''
                    UPDATE bodega 
                    SET cantidad_kg = cantidad_kg - ? 
                    WHERE UPPER(ingrediente) = UPPER(?)
                ''', (kilos_float, ingrediente))
                
        db.commit()
        flash(f"🌾 ¡Servido confirmado! Se han descontado los insumos del Corral {corral_id} de la bodega general.", "success")
    except Exception as e:
        db.rollback()
        flash(f"❌ Error al procesar el descuento en bodega: {str(e)}", "error")
        
    db.close()
    return redirect(url_for('menu_alimentacion'))

if __name__ == '__main__':
    app.run(debug=True)