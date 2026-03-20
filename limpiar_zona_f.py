import sqlite3

# 1. Conexión a tu base de datos exacta
conexion = sqlite3.connect('torneo_padel.db')
cursor = conexion.cursor()

# === VARIABLES A REVISAR ANTES DE EJECUTAR ===
# Verifica que estos nombres coincidan con los de tus tablas en la base de datos.
# Por convención, asumo que la tabla se llama 'partidos'. Si se llama distinto (ej: 'matches', 'fixture'), cámbialo aquí.
nombre_tabla_partidos = 'partidos' 
nombre_columna_zona = 'zona'
nombre_columna_torneo = 'id_torneo'

# El ID del torneo actual según tu captura de pantalla
id_del_torneo_actual = 6  

try:
    # 2. Consulta de seguridad previa
    # Contamos cuántos partidos hay para no borrar a ciegas
    consulta_conteo = f"SELECT COUNT(*) FROM {nombre_tabla_partidos} WHERE {nombre_columna_zona} = 'Zona F' AND {nombre_columna_torneo} = ?"
    cursor.execute(consulta_conteo, (id_del_torneo_actual,))
    cantidad_actual = cursor.fetchone()[0]
    
    print(f"--- INICIANDO LIMPIEZA ---")
    print(f"Se encontraron {cantidad_actual} partidos programados en la Zona F para el torneo {id_del_torneo_actual}.")

    if cantidad_actual > 0:
        # 3. Borrado EXCLUSIVO de la Zona F
        consulta_borrado = f"DELETE FROM {nombre_tabla_partidos} WHERE {nombre_columna_zona} = 'Zona F' AND {nombre_columna_torneo} = ?"
        cursor.execute(consulta_borrado, (id_del_torneo_actual,))
        
        # Guardamos los cambios
        conexion.commit()
        
        print("\n✅ ÉXITO: Los partidos de la Zona F han sido eliminados correctamente de la base de datos.")
        print("Las zonas A, B, C, D, E y el resto del sistema están completamente intactos.")
    else:
        print("\n⚠️ No se borró nada. Es posible que los partidos ya estén borrados o que el nombre de la tabla/columnas deba ajustarse en este script.")

except sqlite3.Error as error:
    print(f"\n❌ ERROR SQL: {error}")
    print("Por favor, abre tu archivo db_manager.py, fíjate cómo se llama exactamente la tabla donde guardas los partidos y corrige la variable 'nombre_tabla_partidos' en este script.")

finally:
    # 4. Cierre seguro de la base de datos
    if conexion:
        conexion.close()