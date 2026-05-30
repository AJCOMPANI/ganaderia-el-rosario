import sqlite3

def get_db_connection():
    conn = sqlite3.connect('usuarios.db')
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_base_datos_completa():
    """Crea todas las tablas desde cero con la estructura de logística inteligente"""
    db = get_db_connection()
    
    print("🧹 Limpiando y configurando tablas...")
    
# Dentro de tu script de inicialización, agrega o modifica la tabla:
    db.execute('''
        CREATE TABLE IF NOT EXISTS incidencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empleado_id INTEGER,
            tipo TEXT,
            descripcion TEXT,
            estado TEXT DEFAULT 'PENDIENTE',
            fecha TEXT DEFAULT CURRENT_TIMESTAMP,
            costo_reparacion REAL DEFAULT 0,
            FOREIGN KEY (empleado_id) REFERENCES usuarios(id)
        )
    ''')

    # 1. TABLA DE USUARIOS (Si no existe)
    db.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            correo TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL
        )
    ''')

    # 2. TABLA DE ANIMALES
    db.execute('DROP TABLE IF EXISTS animales')
    db.execute('''
        CREATE TABLE animales (
            arete TEXT PRIMARY KEY,
            peso REAL,
            genero TEXT,
            etapa TEXT,
            procedencia TEXT,
            corral_id INTEGER,
            fecha_arribo DATE,
            precio_compra REAL DEFAULT 0
        )
    ''')

    # 3. TABLA DE CORRALES (Con todas las columnas de bloqueo)
    db.execute('DROP TABLE IF EXISTS corrales')
    db.execute('''
        CREATE TABLE corrales (
            id INTEGER PRIMARY KEY,
            capacidad_max INTEGER DEFAULT 100,
            precio_actual REAL DEFAULT 0,
            genero_actual TEXT DEFAULT 'No Identificado',
            procedencia_actual TEXT DEFAULT 'Sin Asignar',
            etapa_actual TEXT DEFAULT 'VACIO',
            tipo_venta TEXT DEFAULT 'ABASTO'
        )
    ''')

    # === TABLA PARA REGISTRAR LAS COMPRAS E INVERSIONES DE BODEGA ===
    # Tabla para congelar el historial financiero de compras de insumos
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
    print("📦 Tabla 'historial_bodega' configurada correctamente.")

    # Insertar 25 corrales iniciales
    for i in range(1, 26):
        tipo = 'LOTE' if i > 10 else 'ABASTO'
        db.execute('''
            INSERT INTO corrales (id, tipo_venta) 
            VALUES (?, ?)
        ''', (i, tipo))

    # ========================================================
    #  ESTRUCTURA CORREGIDA PARA EL MÓDULO DE SALUD VETERINARIA
    # ========================================================
    
    # 1. Eliminar versiones viejas mal estructuradas para evitar conflictos
    # ========================================================
    #  ESTRUCTURA CORREGIDA PARA EL MÓDULO DE SALUD VETERINARIA
    # ========================================================
    
    # 1. Eliminar versiones viejas para evitar conflictos de columnas
    db.execute('DROP TABLE IF EXISTS historial_clinico')
    db.execute('DROP TABLE IF EXISTS bodega_medicamentos')

    # 2. Tabla de medicamentos (Farmacia líquida)
    db.execute('''
        CREATE TABLE bodega_medicamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            descripcion TEXT,
            cantidad_ml REAL DEFAULT 0,
            dosis_recomendada TEXT
        )
    ''')

    # 3. Tabla de historial clínico (Soporta nombres personalizados para "OTRO")
    db.execute('''
        CREATE TABLE historial_clinico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            arete TEXT NOT NULL,
            corral_id INTEGER NOT NULL,
            medicamento_id INTEGER NOT NULL,
            medicamento_nombre_extra TEXT DEFAULT NULL,
            dosis_ml REAL NOT NULL,
            fecha TEXT NOT NULL,
            FOREIGN KEY (arete) REFERENCES animales(arete),
            FOREIGN KEY (medicamento_id) REFERENCES bodega_medicamentos(id)
        )
    ''')

    # 4. Cargar medicamentos POR DEFECTO automáticamente
    medicamentos_defecto = [
        ('CEFTIOFUR 5%', 'Antibiótico para neumonías y piatín (gabarro).', 1000.0, '1 ml por cada 50 kg de peso'),
        ('IVERMECTINA 1%', 'Desparasitante completo para limpiar ganado al arribo.', 500.0, '1 ml por cada 50 kg de peso'),
        ('FLUNIXIN MEGLUMINE', 'Antiinflamatorio y analgésico para bajar la fiebre.', 250.0, '2 ml por cada 45 kg de peso'),
        ('COMPLEJO B + HIERRO', 'Vitamínico para abrir el apetito y acelerar engorde.', 1000.0, '5 a 10 ml totales por animal'),
        ('OTRO / NUEVO MEDICAMENTO', 'Opción para registrar una solución externa manual.', 0.0, 'Especificar dosis manualmente')
    ]

    

    for nombre, desc, cant, dosis in medicamentos_defecto:
        try:
            db.execute('''
                INSERT INTO bodega_medicamentos (nombre, descripcion, cantidad_ml, dosis_recomendada)
                VALUES (?, ?, ?, ?)
            ''', (nombre, desc, cant, dosis))
        except:
            pass
    db.commit()
    db.close()
    print("🚀 Base de datos 'usuarios.db' creada y configurada con éxito.")
    
    

if __name__ == "__main__":
    inicializar_base_datos_completa()