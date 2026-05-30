import sqlite3

def crear_tablas_salud():
    conn = sqlite3.connect('usuarios.db')
    cursor = conn.cursor()
    
    # 1. Tabla para control de medicamentos líquidos (ml)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bodega_medicamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            descripcion TEXT,
            cantidad_ml REAL DEFAULT 0,
            dosis_recomendada TEXT
        )
    ''')
    
    # 2. Tabla para el historial de inyecciones de los animales
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial_clinico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            arete TEXT NOT NULL,
            corral_id INTEGER NOT NULL,
            medicamento_id INTEGER NOT NULL,
            dosis_ml REAL NOT NULL,
            fecha DATE NOT NULL,
            FOREIGN KEY(arete) REFERENCES animales(arete),
            FOREIGN KEY(medicamento_id) REFERENCES bodega_medicamentos(id)
        )
    ''')
    
    # 3. Población inicial de medicamentos con su respectivo propósito veterinario
    medicamentos = [
        ('CEFTIOFUR 5%', 'Antibiótico inyectable para infecciones respiratorias graves y afecciones podales.', 1000.0, '1 ml por cada 50 kg de peso'),
        ('IVERMECTINA 1%', 'Desparasitante completo de amplio espectro contra parásitos internos y externos.', 500.0, '1 ml por cada 50 kg de peso'),
        ('FLUNIXIN MEGLUMINE', 'Potente antiinflamatorio, analgésico y antipirético para el control de la fiebre y dolor.', 250.0, '2 ml por cada 45 kg de peso'),
        ('COMPLEJO B + HIERRO', 'Vitamínico reconstituyente ideal para acelerar la recuperación y ganancia de peso.', 1000.0, '5 a 10 ml totales por animal')
    ]
    
    for nombre, desc, cant, dosis in medicamentos:
        try:
            # CORREGIDO AQUÍ: 'dosis_recomendada' en lugar de 'dosis_recommended'
            cursor.execute('''
                INSERT INTO bodega_medicamentos (nombre, descripcion, cantidad_ml, dosis_recomendada)
                VALUES (?, ?, ?, ?)
            ''', (nombre, desc, cant, dosis))
        except sqlite3.Error as e:
            # Si ya se ejecutó y existen, pasa al siguiente
            pass
            
    conn.commit()
    conn.close()
    print("🚀 Tablas de salud y catálogo inicial inyectados correctamente.")
    

if __name__ == "__main__":
    crear_tablas_salud()