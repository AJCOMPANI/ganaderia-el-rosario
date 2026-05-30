import sqlite3
from werkzeug.security import generate_password_hash

def setup_complete_db():
    # Establecer conexión con el archivo de base de datos
    conn = sqlite3.connect('usuarios.db')
    cursor = conn.cursor()

    # 1. TABLA DE USUARIOS
    # Maneja el acceso al sistema con roles definidos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            correo TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL -- 'dueño' o 'empleado'
        )
    ''')

    # 2. TABLA DE CORRALES
    # Incluye lógica para evitar cruces de sexo y procedencia
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS corrales (
            id INTEGER PRIMARY KEY,
            capacidad_max INTEGER DEFAULT 100,
            genero_actual TEXT DEFAULT NULL,    -- 'M', 'H' o NULL
            procedencia_actual TEXT DEFAULT NULL -- Almacena la procedencia del grupo actual
        )
    ''')

    # 3. TABLA DE ANIMALES
    # El arete es único. El peso tiene una restricción de integridad de 700kg.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS animales (
            arete TEXT PRIMARY KEY,
            peso REAL CHECK(peso <= 700),
            genero TEXT NOT NULL,
            etapa TEXT NOT NULL,       -- Inicio, Desarrollo o Engorda
            procedencia TEXT NOT NULL, -- Lugar de origen del animal
            corral_id INTEGER,
            fecha_arribo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(corral_id) REFERENCES corrales(id)
        )
    ''')

    # --- DATOS INICIALES ---

    # Crear usuario administrador (Dueño)
    # Credenciales: aj.martinez.gonzalez@ugto.mx | 123456789
    correo_admin = "aj.martinez.gonzalez@ugto.mx"
    password_encriptada = generate_password_hash("123456789")
    
    try:
        cursor.execute("INSERT INTO usuarios (correo, password, rol) VALUES (?, ?, ?)",
                       (correo_admin, password_encriptada, 'dueño'))
    except sqlite3.IntegrityError:
        pass # El usuario ya existe

    # Inicializar los 25 corrales reglamentarios
    cursor.execute("SELECT COUNT(*) FROM corrales")
    if cursor.fetchone()[0] == 0:
        for i in range(1, 26):
            cursor.execute("INSERT INTO corrales (id) VALUES (?)", (i,))

    conn.commit()
    conn.close()
    print("Base de datos de 'El Rosario' inicializada con éxito.")

if __name__ == "__main__":
    setup_complete_db()