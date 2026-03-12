import sqlite3
import random

def reparar_y_cargar_test(torneo_id, categoria="Suma 13"):
    try:
        conn = sqlite3.connect('torneos_padel.db')
        cursor = conn.cursor()

        # 1. Recreamos la tabla con todas las columnas necesarias para que no falle nada
        print("🧹 Reestructurando tabla de inscripciones local...")
        cursor.execute("DROP TABLE IF EXISTS inscripciones")
        cursor.execute("""
            CREATE TABLE inscripciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                torneo_id INTEGER,
                jugador1 TEXT,
                jugador2 TEXT,
                categoria TEXT,
                localidad TEXT,
                estado_validacion TEXT DEFAULT 'Validado'
            )
        """)

        # 2. Datos aleatorios
        nombres = ["Juan", "Pedro", "Lucas", "Marcos", "Agustin", "Bautista", "Facundo", "Nicolas", "Matias", "Tomas", "Santi", "Fran", "Enzo", "Lolo", "Pepe"]
        apellidos = ["Gomez", "Perez", "Rodriguez", "Gonzalez", "Garcia", "Lopez", "Martinez", "Sanchez", "Romero", "Alvarez", "Torres", "Ruiz", "Diaz", "Vera"]

        print(f"🚀 Generando 18 parejas para el Torneo ID: {torneo_id}...")

        for i in range(18):
            j1 = f"{random.choice(nombres)} {random.choice(apellidos)}"
            j2 = f"{random.choice(nombres)} {random.choice(apellidos)}"
            
            cursor.execute("""
                INSERT INTO inscripciones (torneo_id, jugador1, jugador2, categoria, localidad, estado_validacion)
                VALUES (?, ?, ?, ?, 'Villaguay', 'Validado')
            """, (torneo_id, j1, j2, categoria))

        conn.commit()
        print(f"✅ ¡Éxito total! Tabla reparada y 18 parejas cargadas en el Torneo {torneo_id}.")
        
    except sqlite3.Error as e:
        print(f"❌ Error crítico: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # Asegurate de que el ID 5 sea el que estás viendo en la web
    reparar_y_cargar_test(torneo_id=5)