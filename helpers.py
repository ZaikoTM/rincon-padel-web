import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import random
from PIL import Image, ImageDraw, ImageFont
import os
import io
import urllib.parse
import re
import hashlib
from datetime import datetime, timedelta
import time
import requests
from streamlit_lottie import st_lottie
import plotly.express as px
import numpy as np

import sqlite3
from sqlalchemy.exc import OperationalError
from sqlalchemy import text
import contextlib

# --- URLS ASSETS ---
URL_LOTTIE_PLAYER = "https://assets9.lottiefiles.com/packages/lf20_vo0a1yca.json"
URL_LOTTIE_TROPHY = "https://assets10.lottiefiles.com/packages/lf20_touohxv0.json"
URL_LOTTIE_BALL = "https://lottie.host/8e2f644b-6101-447a-ba98-0c3f59518d6e/3rXo1O3vVv.json"
URL_LOTTIE_MATCH = "https://lottie.host/8e3d5b7a-6f4e-4b9a-9e1d-3c2b1a0f9e8d/padel_animation.json"

@st.cache_data
def load_local_image(path):
    """Carga imágenes locales con caché para evitar I/O repetitivo."""
    if os.path.exists(path):
        return Image.open(path)
    return None

@contextlib.contextmanager
def custom_spinner():
    with st.spinner("Procesando... 🎾"):
        yield

def normalize_params(params):
    """Convierte tipos de numpy a nativos de Python (int, float) recursivamente."""
    if isinstance(params, dict):
        return {k: normalize_params(v) for k, v in params.items()}
    if isinstance(params, (list, tuple)):
        return [normalize_params(v) for v in params]
    if isinstance(params, (np.int64, np.integer)):
        return int(params)
    if isinstance(params, (np.float64, np.floating)):
        return float(params)
    if hasattr(params, 'item'):
        return params.item()
    return params

def get_db_connection():
    """Obtiene la conexión a la DB con configuración de pool optimizada."""
    return st.connection(
        'postgresql',
        type='sql',
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        connect_args={'connect_timeout': 5}
    )

def run_action(query, params=None, return_id=False):
    """Ejecuta una acción de modificación (INSERT, UPDATE, DELETE) en la DB."""
    try:
        params = normalize_params(params)
        if params and isinstance(params, dict) and '%(' in query:
            query = re.sub(r'%\((\w+)\)s', r':\1', query)
            
        conn = get_db_connection()
        with conn.session as s:
            if return_id:
                result = s.execute(text(query), params)
                res_val = result.fetchone()[0]
                s.commit()
            else:
                s.execute(text(query), params)
                res_val = None
                s.commit()
                    
            if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
                st.cache_data.clear()
                
            return res_val
    except Exception as e:
        st.error(f'❌ Error de Conexión: {str(e)}')
        st.stop()

@st.cache_resource
def init_db():
    try:
        conn = get_db_connection()
        return conn
    except Exception as e:
        st.error(f"Error crítico al conectar a la base de datos: {e}")
        st.stop()

def limpiar_cache():
    st.cache_data.clear()

def inicializar_feed_mock():
    """Inicializa datos simulados para el Feed Social en session_state."""
    if 'feed_actividad' not in st.session_state:
        st.session_state['feed_actividad'] = [
            {"fecha_hora": (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M"), "tipo_evento": "victoria", "mensaje": "¡Juan y Nico ganaron su partido de 4ta 6-4, 6-2!"},
            {"fecha_hora": (datetime.now() - timedelta(minutes=25)).strftime("%Y-%m-%d %H:%M"), "tipo_evento": "inscripcion", "mensaje": "¡Nueva pareja inscrita: Martín y Lucas en 6ta!"},
            {"fecha_hora": (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"), "tipo_evento": "ranking", "mensaje": "Pedro subió al Top 5 del ranking de 5ta categoría."},
            {"fecha_hora": (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"), "tipo_evento": "aviso", "mensaje": "Los horarios del sábado ya están publicados en el Fixture."},
            {"fecha_hora": (datetime.now() - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M"), "tipo_evento": "victoria", "mensaje": "Sturla / Villagran avanzan a Semifinales tras un duro 7-6, 6-4."}
        ]

def agregar_evento_feed(tipo_evento, mensaje):
    """Agrega un evento al Feed Social. (Simulado en session_state por ahora)."""
    inicializar_feed_mock()
    nuevo_evento = {"fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M"), "tipo_evento": tipo_evento, "mensaje": mensaje}
    st.session_state['feed_actividad'].insert(0, nuevo_evento) 

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def guardar_inscripcion(torneo_id, j1, j2, loc, cat, pago, tel1, tel2):
    if st.session_state.get('id_torneo'):
        torneo_id = st.session_state['id_torneo']
        
    run_action("INSERT INTO inscripciones (torneo_id, jugador1, jugador2, localidad, categoria, pago_confirmado, telefono1, telefono2) VALUES (%(torneo_id)s, %(jugador1)s, %(jugador2)s, %(localidad)s, %(categoria)s, %(pago_confirmado)s, %(telefono1)s, %(telefono2)s)", 
              {"torneo_id": torneo_id, "jugador1": j1, "jugador2": j2, "localidad": loc, "categoria": cat, "pago_confirmado": 1 if pago else 0, "telefono1": tel1, "telefono2": tel2})
    limpiar_cache()

def eliminar_pareja_torneo(pareja_id, torneo_id):
    """Da de baja y elimina una pareja inscrita de un torneo en particular."""
    if not st.session_state.get('es_admin', False): return
    run_action("DELETE FROM inscripciones WHERE id = %(id)s AND torneo_id = %(torneo_id)s", 
              {"id": pareja_id, "torneo_id": torneo_id})
    limpiar_cache()

def crear_torneo(nombre, fecha, categoria, es_puntuable=True, super_tiebreak=False, puntos_tiebreak=10):
    if not st.session_state.get('es_admin', False): return None
    new_id = run_action("INSERT INTO torneos (nombre, fecha, categoria, estado, es_puntuable, super_tiebreak, puntos_tiebreak) VALUES (%(nombre)s, %(fecha)s, %(categoria)s, 'Abierto', %(es_puntuable)s, %(super_tiebreak)s, %(puntos_tiebreak)s) RETURNING id", 
              {"nombre": nombre, "fecha": str(fecha), "categoria": categoria, "es_puntuable": 1 if es_puntuable else 0, "super_tiebreak": 1 if super_tiebreak else 0, "puntos_tiebreak": puntos_tiebreak}, return_id=True)
    limpiar_cache()
    return new_id

def iniciar_torneo(torneo_id):
    if not st.session_state.get('es_admin', False): return
    run_action("UPDATE torneos SET estado = 'En Juego' WHERE id = %(id)s", {"id": torneo_id})
    limpiar_cache()

def detener_partido(partido_id):
    if not st.session_state.get('es_admin', False): return
    run_action("UPDATE partidos SET estado_partido = 'Detenido' WHERE id = %(id)s", {"id": partido_id})
    limpiar_cache()

@st.cache_data(ttl=600)
def get_data(query, params=None):
    return cargar_datos(query, params)

def cargar_datos(query, params=None):
    params = normalize_params(params)
    if params and isinstance(params, dict) and '%(' in query:
        query = re.sub(r'%\((\w+)\)s', r':\1', query)
    try:
        conn = get_db_connection()
        return conn.query(query, params=params, ttl=0)
    except Exception as e:
        error_msg = str(e)        
        if "MaxClientsInSessionMode" in error_msg or "too many clients" in error_msg.lower():
            st.warning("⚠️ Servidor saturado. Limpiando conexiones y reintentando...")
            st.cache_resource.clear() 
            time.sleep(1)
            try:
                conn = get_db_connection()
                return conn.query(query, params=params, ttl=0)
            except Exception as e_final:
                st.error(f"❌ No se pudo restablecer la conexión: {e_final}")
                return None
        else:
            st.warning("⚠️ Actualizando datos, por favor espera unos segundos...")
            return pd.DataFrame()

def obtener_torneos_activos():
    """Obtiene la lista de torneos activos (estado 'Abierto')."""
    return cargar_datos("SELECT * FROM torneos WHERE estado = 'Abierto'")

def obtener_partido_en_vivo():
    """Obtiene el partido en vivo para el banner."""
    return cargar_datos("SELECT * FROM partido_en_vivo ORDER BY id DESC LIMIT 1")

def obtener_inscritos_publicos(torneo_id):
    query = """
        SELECT jugador1, jugador2, localidad, categoria 
        FROM inscripciones 
        WHERE torneo_id = %(id)s AND estado_validacion = 'Validado'
    """
    return cargar_datos(query, {"id": torneo_id})

def mostrar_tabla_inscritos(torneo_id):
    inscritos = obtener_inscritos_publicos(torneo_id)
    st.markdown("<h3 style='color: #00FF00; text-shadow: 0 0 10px rgba(0, 255, 0, 0.3); margin-bottom: 15px;'>👥 Parejas Inscritas</h3>", unsafe_allow_html=True)
    if inscritos is not None and not inscritos.empty:
        html_table = """
        <style>
            .neon-table { width: 100%; border-collapse: collapse; margin-bottom: 25px; background-color: #1A1A1A; border-radius: 10px; overflow: hidden; border: 1px solid #333; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
            .neon-table th { background-color: #000000; color: #00FF00; text-align: left; padding: 12px; font-weight: bold; border-bottom: 2px solid #00FF00; text-transform: uppercase; font-size: 0.85rem; }
            .neon-table td { padding: 10px 12px; border-bottom: 1px solid #222; color: #E0E0E0; font-size: 0.9rem; }
            .neon-table tr:hover { background-color: rgba(0, 255, 0, 0.05); }
            .neon-text { color: #FFFFFF; font-weight: bold; text-shadow: 0 0 5px rgba(255,255,255,0.2); }
            @keyframes fadeInRow {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .neon-table tbody tr { opacity: 0; animation: fadeInRow 0.4s ease forwards; }
        </style>
        <table class="neon-table">
            <thead>
                <tr>
                    <th style="text-align: center; width: 50px;">Nro</th>
                    <th>Pareja</th>
                    <th>Localidad</th>
                    <th>Categoría</th>
                </tr>
            </thead>
            <tbody>
        """
        for idx, row in enumerate(inscritos.itertuples(), start=1):
            delay = idx * 0.05 
            html_table += f"""
            <tr style="animation-delay: {delay}s;">
                <td style="text-align: center; color: #888;">{idx}</td>
                <td class="neon-text">{row.jugador1} - {row.jugador2}</td>
                <td>{row.localidad}</td>
                <td style="color: #00E676;">{row.categoria}</td>
            </tr>
            """
        html_table += "</tbody></table>"
        html_table = " ".join(html_table.split())
        st.markdown(html_table, unsafe_allow_html=True)
    else:
        st.info("Aún no hay parejas inscritas en este torneo.")

def buscar_jugador_por_dni(dni):
    """Busca jugadores por DNI (Celular) en la tabla 'jugadores'."""
    return cargar_datos("SELECT * FROM jugadores WHERE celular = :dni", params={"dni": dni})

def generar_fixture_automatico(torneo_id, programacion_dias):
    if not st.session_state.get('es_admin', False):
        return False, "Acceso denegado. Debes ser administrador."
    df_partidos = cargar_datos("SELECT id FROM partidos WHERE torneo_id = :torneo_id AND instancia = 'Zona' ORDER BY id ASC", {"torneo_id": torneo_id})
    partidos_a_programar = df_partidos['id'].tolist()
    num_partidos = len(partidos_a_programar)
    if num_partidos == 0:
        return False, "No hay partidos de zona generados para este torneo."
    duracion_partido = timedelta(hours=1, minutes=15)
    slots_disponibles = []
    for dia in programacion_dias:
        fecha = dia['fecha']
        hora_inicio = dia['inicio']
        hora_fin = dia['fin']
        inicio_dt = datetime.combine(fecha, hora_inicio)
        fin_dt = datetime.combine(fecha, hora_fin)
        tiempo_actual = inicio_dt
        while tiempo_actual + duracion_partido <= fin_dt:
            slots_disponibles.append(tiempo_actual)
            tiempo_actual += duracion_partido
    if num_partidos > len(slots_disponibles):
        mensaje_alerta = f"⚠️ ¡Alerta de capacidad! Se necesitan {num_partidos} slots, pero solo hay {len(slots_disponibles)} disponibles en los rangos horarios definidos. Amplía los horarios o reduce el número de partidos."
        return False, mensaje_alerta
    run_action("UPDATE partidos SET horario = NULL, cancha = NULL WHERE torneo_id = %(torneo_id)s AND instancia = 'Zona'", {"torneo_id": torneo_id})
    for idx, partido_id in enumerate(partidos_a_programar):
        horario_asignado = slots_disponibles[idx]
        horario_str = horario_asignado.strftime("%Y-%m-%d %H:%M")
        run_action("UPDATE partidos SET horario = %(horario)s, cancha = 'Cancha Central', estado_partido = 'Próximo' WHERE id = %(id)s", {"horario": horario_str, "id": int(partido_id)})
    limpiar_cache()
    return True, f"✅ Se programaron exitosamente {num_partidos} partidos en la Cancha Central."

def generar_zonas(torneo_id, categoria, pref_tamano=4):
    if not st.session_state.get('es_admin', False): 
        return False, "Acceso denegado"
    try:
        torneo_id = int(torneo_id)
    except:
        return False, "ID de torneo inválido"
    query_insc = """
        SELECT jugador1, jugador2 FROM inscripciones 
        WHERE torneo_id = :t_id AND categoria = :cat AND estado_validacion = 'Validado'
    """
    df_insc = cargar_datos(query_insc, {"t_id": torneo_id, "cat": categoria})
    if df_insc is None or df_insc.empty:
        return False, f"No hay parejas validadas para {categoria} en el Torneo {torneo_id}."
    parejas = [f"{row['jugador1']} - {row['jugador2']}" for _, row in df_insc.iterrows()]
    n = len(parejas)
    if n < 3: return False, f"Mínimo 3 parejas (hay {n})."
    random.shuffle(parejas)
    q4, q3, found = 0, 0, False
    if pref_tamano == 4:
        range_q4 = range(n // 4, -1, -1) 
    else:
        range_q4 = range(0, (n // 4) + 1) 
    for i in range_q4:
        rem = n - (i * 4)
        if rem % 3 == 0:
            q4, q3, found = i, rem // 3, True
            break
    if not found: return False, "La cantidad de parejas no cierra para grupos de 3 y 4."
    run_action("""
        DELETE FROM zonas WHERE torneo_id = :t_id AND pareja IN 
        (SELECT jugador1 || ' - ' || jugador2 FROM inscripciones WHERE categoria = :cat)
    """, {"t_id": torneo_id, "cat": categoria})
    run_action("""
        DELETE FROM zonas_posiciones WHERE torneo_id = :t_id AND pareja IN 
        (SELECT jugador1 || ' - ' || jugador2 FROM inscripciones WHERE categoria = :cat)
    """, {"t_id": torneo_id, "cat": categoria})
    run_action("""
        DELETE FROM partidos WHERE torneo_id = :t_id AND instancia = 'Zona' AND pareja1 IN 
        (SELECT jugador1 || ' - ' || jugador2 FROM inscripciones WHERE categoria = :cat)
    """, {"t_id": torneo_id, "cat": categoria})
    idx, letras, zona_counter = 0, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", 0
    def procesar_grupo(tamano):
        nonlocal idx, zona_counter
        nombre_z = f"Zona {letras[zona_counter]}"
        grupo = parejas[idx:idx+tamano]
        for p in grupo:
            run_action("""
                INSERT INTO zonas (torneo_id, nombre_zona, pareja) 
                VALUES (:t_id, :nz, :pj)
            """, {"t_id": torneo_id, "nz": nombre_z, "pj": p})
            run_action("""
                INSERT INTO zonas_posiciones (torneo_id, nombre_zona, pareja) 
                VALUES (:t_id, :nz, :pj)
            """, {"t_id": torneo_id, "nz": nombre_z, "pj": p})
        cruces = [(0,1), (2,3), (0,2), (1,3), (0,3), (1,2)] if tamano == 4 else [(0,1), (0,2), (1,2)]
        for i1, i2 in cruces:
            run_action("""
                INSERT INTO partidos (torneo_id, pareja1, pareja2, instancia, estado_partido) 
                VALUES (:t_id, :p1, :p2, 'Zona', 'Próximo')
            """, {"t_id": torneo_id, "p1": grupo[i1], "p2": grupo[i2]})
        idx += tamano
        zona_counter += 1
    for _ in range(q4): procesar_grupo(4)
    for _ in range(q3): procesar_grupo(3)
    st.cache_data.clear()
    return True, f"✅ Éxito: Se crearon {zona_counter} zonas para {categoria}."

def generar_partidos_desde_zonas_existentes(torneo_id):
    if not st.session_state.get('es_admin', False): 
        return False, "Acceso denegado"
    try:
        t_id = int(torneo_id)
    except (ValueError, TypeError):
        return False, "ID de torneo inválido."
    run_action("DELETE FROM partidos WHERE torneo_id = :t_id AND instancia = 'Zona'", {"t_id": t_id})
    df_zonas = cargar_datos(
        "SELECT nombre_zona, pareja FROM zonas WHERE torneo_id = :t_id ORDER BY nombre_zona", 
        params={"t_id": t_id}
    )
    if df_zonas is None or df_zonas.empty:
        return False, "No se encontraron zonas definidas para este torneo."
    grupos = df_zonas.groupby('nombre_zona')
    count_partidos = 0
    for nombre_z, df_grupo in grupos:
        parejas = df_grupo['pareja'].tolist()
        n = len(parejas)
        cruces = []
        if n == 3: cruces = [(0,1), (0,2), (1,2)]
        elif n == 4: cruces = [(0,1), (2,3), (0,2), (1,3), (0,3), (1,2)]
        elif n == 5: cruces = [(0,1), (0,2), (0,3), (0,4), (1,2), (1,3), (1,4), (2,3), (2,4), (3,4)]
        for i1, i2 in cruces:
            if i1 < n and i2 < n:
                run_action(
                    """
                    INSERT INTO partidos (torneo_id, pareja1, pareja2, instancia, estado_partido) 
                    VALUES (:t_id, :p1, :p2, 'Zona', 'Próximo')
                    """, 
                    {"t_id": t_id, "p1": parejas[i1], "p2": parejas[i2]}
                )
                count_partidos += 1
    limpiar_cache()
    return True, f"✅ Éxito: Se generaron {count_partidos} partidos para las zonas de este torneo."

def cerrar_zonas_y_generar_playoffs(torneo_id):
    if not st.session_state.get('es_admin', False): return False, "Acceso denegado"
    t_id = int(torneo_id)
    df_check = cargar_datos("SELECT count(*) as c FROM partidos WHERE torneo_id = :t_id AND instancia IN ('Octavos', 'Cuartos', 'Semis', 'Final')", {"t_id": t_id})
    if df_check is not None and not df_check.empty and df_check.iloc[0]['c'] > 0:
        return False, "Ya se han generado cruces de playoff para este torneo."
    df = cargar_datos("""
        SELECT nombre_zona, pareja, pts, ds, dg, pg
        FROM zonas_posiciones 
        WHERE torneo_id = :t_id 
        ORDER BY pts DESC, ds DESC, dg DESC, pg DESC
    """, {"t_id": t_id})
    if df is None or df.empty: return False, "No hay zonas registradas con datos."
    zonas_dict = {}
    for _, row in df.iterrows():
        z = row['nombre_zona']
        if z not in zonas_dict: zonas_dict[z] = []
        zonas_dict[z].append(row) 
    clasificados = [] 
    terceros = []     
    for z, equipos in zonas_dict.items():
        equipos_sorted = sorted(equipos, key=lambda x: (x['pts'], x['ds'], x['dg'], x['pg']), reverse=True)
        z_letra = z.replace("Zona ", "").strip()
        if len(equipos_sorted) >= 1: clasificados.append( (f"1{z_letra} - {equipos_sorted[0]['pareja']}", 1, equipos_sorted[0]) )
        if len(equipos_sorted) >= 2: clasificados.append( (f"2{z_letra} - {equipos_sorted[1]['pareja']}", 2, equipos_sorted[1]) )
        if len(equipos_sorted) >= 3: terceros.append( (f"3{z_letra} - {equipos_sorted[2]['pareja']}", 3, equipos_sorted[2]) )
    num_clasificados_base = len(clasificados)
    target_size = 4
    if num_clasificados_base > 4: target_size = 8
    if num_clasificados_base > 8: target_size = 16
    if num_clasificados_base > 16: target_size = 32
    slots_needed = target_size - num_clasificados_base
    terceros.sort(key=lambda x: (x[2]['pts'], x[2]['ds'], x[2]['dg'], x[2]['pg']), reverse=True)
    while slots_needed > 0 and len(terceros) > 0:
        top_3ro = terceros.pop(0)
        clasificados.append(top_3ro) 
        slots_needed -= 1
    byes_added = 0
    while slots_needed > 0:
        clasificados.append( ("BYE", 4, None) ) 
        slots_needed -= 1
        byes_added += 1
    def sort_key(item):
        pareja, pos_zona, stats = item
        if pareja == "BYE": return (-1, -1, -1, -1, -1) 
        priority_group = 4 - pos_zona
        return (priority_group, stats['pts'], stats['ds'], stats['dg'], stats['pg'])
    clasificados.sort(key=sort_key, reverse=True)
    cruces_finales = []
    n = len(clasificados)
    for i in range(n // 2):
        p1 = clasificados[i][0]
        p2 = clasificados[n - 1 - i][0]
        cruces_finales.append((p1, p2))
    instancia = "Cuartos"
    start_pos = 9
    if target_size == 16:
        instancia = "Octavos"
        start_pos = 1
    elif target_size == 4:
        instancia = "Semis"
        start_pos = 13
    count = 0
    matches_ordered = []
    if len(cruces_finales) == 2: 
        matches_ordered = cruces_finales
    elif len(cruces_finales) == 4: 
        matches_ordered = [cruces_finales[0], cruces_finales[3], cruces_finales[2], cruces_finales[1]]
    elif len(cruces_finales) == 8: 
        matches_ordered = [
            cruces_finales[0], cruces_finales[7], 
            cruces_finales[4], cruces_finales[3], 
            cruces_finales[2], cruces_finales[5], 
            cruces_finales[6], cruces_finales[1]  
        ]
    else:
        matches_ordered = cruces_finales 
    for p1, p2 in matches_ordered:
        estado = 'Próximo'
        res = ''
        ganador = None
        if p1 == "BYE":
            estado = 'Finalizado'
            ganador = p2
            res = 'BYE'
        elif p2 == "BYE":
            estado = 'Finalizado'
            ganador = p1
            res = 'BYE'
        run_action("""
            INSERT INTO partidos (torneo_id, pareja1, pareja2, instancia, estado_partido, bracket_pos)
            VALUES (:tid, :p1, :p2, :inst, 'Próximo', :bp)
        """, {"tid": t_id, "p1": p1, "p2": p2, "inst": instancia, "bp": start_pos + count})
        if ganador:
            actualizar_bracket(None, t_id, start_pos + count, res, ganador)
            run_action("UPDATE partidos SET estado_partido = 'Finalizado', resultado = 'Pasa Directo', ganador = :g WHERE torneo_id = :tid AND bracket_pos = :bp",
                       {"g": ganador, "tid": t_id, "bp": start_pos + count})
        count += 1
    limpiar_cache()
    return True, f"✅ Se generaron {count} partidos de {instancia}. (Total: {num_clasificados_base} clasificados + {byes_added} BYEs)."

def mostrar_estadisticas_torneo(torneo_id):
    st.markdown("### 📊 Estadísticas del Torneo")
    df_insc = cargar_datos("SELECT jugador1, jugador2, localidad, categoria FROM inscripciones WHERE torneo_id = :tid", {"tid": int(torneo_id)})
    total_parejas = len(df_insc) if df_insc is not None and not df_insc.empty else 0
    df_matches = cargar_datos("SELECT resultado FROM partidos WHERE torneo_id = :tid AND estado_partido = 'Finalizado'", {"tid": int(torneo_id)})
    total_jugados = len(df_matches) if df_matches is not None else 0
    sets_2 = 0
    sets_3 = 0
    if df_matches is not None and not df_matches.empty:
        for res in df_matches['resultado']:
            if not res: continue
            parts = [p for p in res.split(' ') if '-' in p]
            if len(parts) == 2: sets_2 += 1
            elif len(parts) >= 3: sets_3 += 1
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Parejas Inscritas", total_parejas, border=True)
    c2.metric("Partidos Finalizados", total_jugados, border=True)
    c3.metric("Definidos en 2 Sets", sets_2, border=True)
    c4.metric("Definidos en 3 Sets", sets_3, border=True)
    st.divider()
    if total_parejas > 0:
        with st.expander("👥 Parejas Inscritas", expanded=False):
            html_table = """
            <style>
                .stats-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; background-color: #1A1A1A; border-radius: 8px; overflow: hidden; border: 1px solid #333; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
                .stats-table th { background-color: #000000; color: #00FF00; text-align: left; padding: 12px; border-bottom: 2px solid #00FF00; font-size: 0.9rem; text-transform: uppercase; }
                .stats-table td { padding: 10px 12px; border-bottom: 1px solid #222; color: #E0E0E0; font-size: 0.9rem; }
                .stats-table tr:hover { background-color: rgba(0, 255, 0, 0.05); }
            </style>
            <table class="stats-table">
                <thead>
                    <tr>
                        <th>Jugador 1</th>
                        <th>Jugador 2</th>
                        <th>Localidad</th>
                        <th>Categoría</th>
                    </tr>
                </thead>
                <tbody>
            """
            for _, row in df_insc.iterrows():
                html_table += f"""
                    <tr>
                        <td style="font-weight: bold; color: #FFF;">{row['jugador1']}</td>
                        <td style="font-weight: bold; color: #FFF;">{row['jugador2']}</td>
                        <td>{row['localidad']}</td>
                        <td style="color: #00E676;">{row['categoria']}</td>
                    </tr>
                """
            html_table += "</tbody></table>"
            st.markdown(" ".join(html_table.split()), unsafe_allow_html=True)

def mostrar_cuadro_playoff(torneo_id):
    df = cargar_datos("SELECT * FROM partidos WHERE torneo_id = :tid AND bracket_pos IS NOT NULL ORDER BY bracket_pos", {"tid": int(torneo_id)})
    if df is None or df.empty: return
    matches = df.set_index('bracket_pos').to_dict('index')
    def get_match_html(pos):
        m = matches.get(pos, {})
        p1 = m.get('pareja1', 'TBD') or 'TBD'
        p2 = m.get('pareja2', 'TBD') or 'TBD'
        ganador = m.get('ganador')
        def get_score(s_idx):
            res = []
            for k in ['set1', 'set2', 'set3']:
                val = m.get(k)
                if val and '-' in str(val):
                    try: res.append(str(val).split('-')[s_idx])
                    except: pass
            return " ".join(res)
        s_p1 = get_score(0)
        s_p2 = get_score(1)
        c1 = "team winner" if ganador and ganador == p1 and p1 != 'TBD' else "team"
        c2 = "team winner" if ganador and ganador == p2 and p2 != 'TBD' else "team"
        return f"""
        <div class="match">
            <div class="{c1}"><span>{p1}</span> <span class="score">{s_p1}</span></div>
            <div class="{c2}"><span>{p2}</span> <span class="score">{s_p2}</span></div>
        </div>
        """
    has_oct = any(k in matches for k in range(1, 9))
    has_4tos = any(k in matches for k in range(9, 13))
    has_semis = any(k in matches for k in range(13, 15))
    rounds_html = ""
    if has_oct: rounds_html += f'<div class="round"><div class="round-title">Octavos</div>{"".join([get_match_html(i) for i in range(1, 9)])}</div>'
    if has_4tos or has_oct: rounds_html += f'<div class="round"><div class="round-title">Cuartos</div>{"".join([get_match_html(i) for i in range(9, 13)])}</div>'
    if has_semis or has_4tos: rounds_html += f'<div class="round"><div class="round-title">Semis</div>{"".join([get_match_html(i) for i in range(13, 15)])}</div>'
    rounds_html += f'<div class="round"><div class="round-title">Final</div>{get_match_html(15)}</div>'
    campeon = matches.get(15, {}).get('ganador', '?')
    rounds_html += f"""
    <div class="round"><div class="round-title">Campeón</div>
    <div class="match campeon-card winner"><span style="font-size: 24px;">🏆</span><br><span style="font-size: 16px;">{campeon}</span></div></div>
    """
    html_code = f"""
    <!DOCTYPE html><html><head><style>
        body {{ background: transparent; color: white; font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; }}
        .bracket-wrapper {{ display: flex; flex-direction: row; overflow-x: auto; padding: 20px; gap: 40px; }}
        .round {{ display: flex; flex-direction: column; justify-content: space-around; min-width: 220px; }}
        .round-title {{ text-align: center; color: #888; font-size: 14px; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 1px; }}
        .match {{ background: #1A1A1A; border: 1px solid #333; border-radius: 6px; margin: 15px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.3); position: relative; }}
        .team {{ display: flex; justify-content: space-between; padding: 10px 15px; border-bottom: 1px solid #222; font-size: 14px; }}
        .team:last-child {{ border-bottom: none; }}
        .winner {{ color: #00FF00; background: rgba(0, 255, 0, 0.05); font-weight: bold; }}
        .score {{ font-weight: bold; color: #aaa; letter-spacing: 2px; }}
        .winner .score {{ color: #00FF00; }}
        .round:not(:last-child) .match::after {{ content: ''; position: absolute; right: -20px; top: 50%; width: 20px; border-top: 2px solid #444; }}
        .campeon-card {{ text-align: center; padding: 20px; border: 2px solid #00FF00; box-shadow: 0 0 15px rgba(0, 255, 0, 0.2); }}
        ::-webkit-scrollbar {{ height: 8px; }} ::-webkit-scrollbar-track {{ background: #111; }} ::-webkit-scrollbar-thumb {{ background: #333; border-radius: 4px; }}
    </style></head><body>
    <div class="bracket-wrapper">{rounds_html}</div>
    </body></html>
    """
    components.html(html_code, height=600, scrolling=True)

def mostrar_consejo_padel():
    consejos = [
        {"autor": "Ariana Sánchez", "texto": "La magia surge cuando el trabajo táctico se vuelve completamente automático."},
        {"autor": "Fernando Belasteguín", "texto": "El talento te hace ganar partidos, pero el trabajo duro, el compañero y la inteligencia te hacen ganar torneos."},
        {"autor": "Alejandro Galán", "texto": "La velocidad no es solo física, está en la cabeza. Anticípate a la jugada y dominarás la red."}
    ]
    consejo_del_dia = random.choice(consejos)
    html_consejo = f"""
    <div style="display: flex; justify-content: center; margin-bottom: 15px; margin-top: 15px;">
        <div style="background: linear-gradient(145deg, #111111, #1a1a1a); border: 1px solid #333; border-top: 3px solid #00FF00; border-radius: 12px; padding: 15px 20px; width: 100%; text-align: center; box-shadow: 0 4px 10px rgba(0,255,0,0.05);">
            <div style="font-size: 2rem; color: #00FF00; margin-bottom: -15px; font-family: Georgia, serif;">❝</div>
            <p style="color: #FFFFFF; font-size: 1.1rem; font-style: italic; font-weight: 300; line-height: 1.4; margin-bottom: 10px;">{consejo_del_dia['texto']}</p>
            <p style="color: #00FF00; font-weight: 700; margin: 0; font-size: 0.85rem; letter-spacing: 1.5px; text-transform: uppercase;">— {consejo_del_dia['autor']} —</p>
        </div>
    </div>
    """
    st.markdown(html_consejo, unsafe_allow_html=True)

def seccion_gestion_horarios(torneo_id):
    st.subheader("🛠️ Gestión de Horarios (Zona)")
    df = cargar_datos("SELECT id, pareja1, pareja2, horario, cancha FROM partidos WHERE torneo_id = :torneo_id AND instancia = 'Zona' ORDER BY id", params={"torneo_id": int(torneo_id)})
    if df is None or df.empty:
        st.info("No hay partidos de zona generados para este torneo.")
        return
    df['horario'] = pd.to_datetime(df['horario'], errors='coerce')
    edited_df = st.data_editor(
        df,
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "pareja1": st.column_config.TextColumn("Pareja 1", disabled=True),
            "pareja2": st.column_config.TextColumn("Pareja 2", disabled=True),
            "cancha": st.column_config.SelectboxColumn("Cancha", options=['Cancha Central', 'Cancha 2', 'Cancha 3'], required=False),
            "horario": st.column_config.DatetimeColumn("Horario", format="DD/MM/YYYY HH:mm", step=15*60)
        },
        hide_index=True,
        use_container_width=True,
        key=f"editor_horarios_zona_{torneo_id}"
    )
    if st.button("💾 Guardar Horarios", type="primary", key="btn_save_horarios_zona"):
        with custom_spinner():
            updated = 0
            for _, row in edited_df.iterrows():
                if pd.notna(row['horario']):
                    h_str = row['horario'].strftime("%Y-%m-%d %H:%M")
                    c_str = row['cancha'] if row['cancha'] else "Cancha Central"
                    run_action("UPDATE partidos SET horario = :h, cancha = :c WHERE id = :id", {"h": h_str, "c": c_str, "id": row['id']})
                    updated += 1
            if updated > 0:
                st.success(f"✅ Se actualizaron {updated} partidos.")
                limpiar_cache()
                time.sleep(1)
                st.rerun()

# --- TABLA DE PUNTOS POR INSTANCIA ---
# Ganador / Perdedor según instancia del partido
PUNTOS_RANKING = {
    "Final":    {"ganador": 200, "perdedor": 150},
    "Semis":    {"ganador": 150, "perdedor": 100},
    "Cuartos":  {"ganador": 100, "perdedor": 75},
    "Octavos":  {"ganador": 75,  "perdedor": 50},
    "16avos":   {"ganador": 50,  "perdedor": 37},
    "32avos":   {"ganador": 37,  "perdedor": 25},
    "Zona":     {"ganador": 25,  "perdedor": 25},
}

def _asignar_puntos_ranking(partido_id, torneo_id, ganador, perdedor):
    """
    Asigna puntos al ranking según la instancia del partido.
    Inserta o actualiza en la tabla ranking_puntos.
    Solo asigna si el torneo tiene es_puntuable = 1.
    """
    # 1. Verificar que el torneo sea puntuable
    df_t = cargar_datos(
        "SELECT es_puntuable, categoria FROM torneos WHERE id = :tid",
        {"tid": torneo_id}
    )
    if df_t is None or df_t.empty:
        return
    if not df_t.iloc[0]['es_puntuable']:
        return

    categoria = df_t.iloc[0]['categoria']

    # 2. Obtener instancia del partido
    df_p = cargar_datos(
        "SELECT instancia FROM partidos WHERE id = :pid",
        {"pid": partido_id}
    )
    if df_p is None or df_p.empty:
        return

    instancia = df_p.iloc[0]['instancia']
    pts_config = PUNTOS_RANKING.get(instancia, {"ganador": 25, "perdedor": 25})
    pts_ganador  = pts_config["ganador"]
    pts_perdedor = pts_config["perdedor"]

    # 3. Función interna para insertar o sumar puntos
    def _upsert_puntos(jugador, puntos):
        # Los jugadores en partidos son "Nombre1 - Nombre2" (parejas)
        # Separamos y asignamos a cada uno individualmente
        nombres = [n.strip() for n in jugador.split(" - ")] if " - " in jugador else [jugador.strip()]
        for nombre in nombres:
            # Verificar si ya existe entrada para este jugador en este torneo
            df_existe = cargar_datos(
                "SELECT id, puntos FROM ranking_puntos WHERE jugador = :j AND torneo_id = :tid",
                {"j": nombre, "tid": torneo_id}
            )
            if df_existe is not None and not df_existe.empty:
                # Sumar puntos a los existentes
                nuevos_pts = int(df_existe.iloc[0]['puntos']) + puntos
                run_action(
                    "UPDATE ranking_puntos SET puntos = :pts WHERE jugador = :j AND torneo_id = :tid",
                    {"pts": nuevos_pts, "j": nombre, "tid": torneo_id}
                )
            else:
                # Insertar nueva entrada
                run_action(
                    """INSERT INTO ranking_puntos (jugador, torneo_id, puntos, categoria)
                       VALUES (:j, :tid, :pts, :cat)""",
                    {"j": nombre, "tid": torneo_id, "pts": puntos, "cat": categoria}
                )

    # 4. Asignar puntos a ganador y perdedor
    _upsert_puntos(ganador, pts_ganador)
    _upsert_puntos(perdedor, pts_perdedor)


def procesar_resultado(partido_id, score_p1, score_p2, torneo_id):
    sets_p1 = 0
    sets_p2 = 0
    res_str_parts = []
    for i in range(3):
        g1 = score_p1[i]
        g2 = score_p2[i]
        if g1 == 0 and g2 == 0: continue
        res_str_parts.append(f"{g1}-{g2}")
        if g1 > g2: sets_p1 += 1
        elif g2 > g1: sets_p2 += 1
    resultado_final = " ".join(res_str_parts)
    df_partido = cargar_datos("SELECT pareja1, pareja2 FROM partidos WHERE id = :id", {"id": partido_id})
    if df_partido is None or df_partido.empty: return False
    pareja1 = df_partido.iloc[0]['pareja1']
    pareja2 = df_partido.iloc[0]['pareja2']
    ganador  = pareja1 if sets_p1 > sets_p2 else pareja2
    perdedor = pareja2 if sets_p1 > sets_p2 else pareja1
    query_update = """
        UPDATE partidos SET 
            resultado = :res, 
            ganador = :ganador, 
            estado_partido = 'Finalizado',
            set1 = :s1, set2 = :s2, set3 = :s3,
            hora_fin = :h_fin
        WHERE id = :id
    """
    params_update = {
        "res": resultado_final,
        "ganador": ganador,
        "s1": f"{score_p1[0]}-{score_p2[0]}" if (score_p1[0] > 0 or score_p2[0] > 0) else None,
        "s2": f"{score_p1[1]}-{score_p2[1]}" if (score_p1[1] > 0 or score_p2[1] > 0) else None,
        "s3": f"{score_p1[2]}-{score_p2[2]}" if (score_p1[2] > 0 or score_p2[2] > 0) else None,
        "h_fin": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "id": partido_id
    }
    run_action(query_update, params_update)
    # --- ASIGNAR PUNTOS AL RANKING AUTOMÁTICAMENTE ---
    _asignar_puntos_ranking(partido_id, torneo_id, ganador, perdedor)
    actualizar_tabla_posiciones(torneo_id)
    return True

def cronograma_visual(torneo_id):
    fig = generar_grafico_timeline(torneo_id)
    if fig: st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else: st.info("Aún no hay horarios asignados para graficar el cronograma.")

def seccion_carga_resultados(torneo_id):
    st.subheader("🎾 Carga de Resultados")
    df_matches = cargar_datos("""
        SELECT id, pareja1, pareja2, instancia, cancha, horario, estado_partido, set1, set2, set3 
        FROM partidos 
        WHERE torneo_id = :tid 
        AND estado_partido != 'Finalizado' 
        AND instancia = 'Zona'
        ORDER BY horario ASC, id ASC
    """, {"tid": torneo_id})
    if df_matches is None or df_matches.empty:
        st.info("No hay partidos de zona pendientes para cargar resultados.")
        return
    st.caption("⚡ Modo Rápido (Móvil): Usa 'Iniciar' para vivo. Edita los games y guarda para finalizar.")
    for idx, row in df_matches.iterrows():
        def parse_set(val):
            if val and '-' in str(val):
                try: return int(val.split('-')[0]), int(val.split('-')[1])
                except: return 0, 0
            return 0, 0
        s1_p1, s1_p2 = parse_set(row['set1'])
        s2_p1, s2_p2 = parse_set(row['set2'])
        s3_p1, s3_p2 = parse_set(row['set3'])
        with st.container(border=True):
            st.markdown(f"**{row['instancia']}** | {row['pareja1']} vs {row['pareja2']}")
            st.caption(f"Estado: {row['estado_partido']} | {row['horario']}")
            if row['estado_partido'] == 'Próximo':
                if st.button("⏱️ Iniciar (En Vivo)", key=f"btn_start_res_{row['id']}", use_container_width=True):
                    now = datetime.now().strftime("%H:%M")
                    run_action("UPDATE partidos SET estado_partido = 'En Juego', hora_inicio_real = :h WHERE id = :id", {"h": now, "id": row['id']})
                    st.toast("✅ Partido Iniciado", icon="🚀")
                    limpiar_cache()
                    time.sleep(0.5)
                    st.rerun()
            with st.form(key=f"form_res_{row['id']}"):
                c_null, c_head1, c_head2, c_head3 = st.columns([2, 1, 1, 1])
                c_head1.markdown("<div style='text-align:center; font-size:0.75rem; color:#888'>SET 1</div>", unsafe_allow_html=True)
                c_head2.markdown("<div style='text-align:center; font-size:0.75rem; color:#888'>SET 2</div>", unsafe_allow_html=True)
                c_head3.markdown("<div style='text-align:center; font-size:0.75rem; color:#888'>SET 3</div>", unsafe_allow_html=True)
                cp1_name, cp1_s1, cp1_s2, cp1_s3 = st.columns([2, 1, 1, 1])
                cp1_name.markdown(f"<div style='padding-top:10px; font-weight:bold; font-size:0.9rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>{row['pareja1']}</div>", unsafe_allow_html=True)
                v1_1 = cp1_s1.number_input("S1", 0, 7, value=s1_p1, key=f"s1p1_{row['id']}", label_visibility="collapsed")
                v1_2 = cp1_s2.number_input("S2", 0, 7, value=s2_p1, key=f"s2p1_{row['id']}", label_visibility="collapsed")
                v1_3 = cp1_s3.number_input("S3", 0, 15, value=s3_p1, key=f"s3p1_{row['id']}", label_visibility="collapsed")
                cp2_name, cp2_s1, cp2_s2, cp2_s3 = st.columns([2, 1, 1, 1])
                cp2_name.markdown(f"<div style='padding-top:10px; font-weight:bold; font-size:0.9rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>{row['pareja2']}</div>", unsafe_allow_html=True)
                v2_1 = cp2_s1.number_input("S1", 0, 7, value=s1_p2, key=f"s1p2_{row['id']}", label_visibility="collapsed")
                v2_2 = cp2_s2.number_input("S2", 0, 7, value=s2_p2, key=f"s2p2_{row['id']}", label_visibility="collapsed")
                v2_3 = cp2_s3.number_input("S3", 0, 15, value=s3_p2, key=f"s3p2_{row['id']}", label_visibility="collapsed")
                st.write("")
                if st.form_submit_button("💾 Guardar y Finalizar", type="primary", use_container_width=True):
                    score_p1 = [v1_1, v1_2, v1_3]
                    score_p2 = [v2_1, v2_2, v2_3]
                    if sum(score_p1) + sum(score_p2) == 0:
                         st.error("Carga al menos un game.")
                    else:
                        with custom_spinner():
                            procesar_resultado(row['id'], score_p1, score_p2, torneo_id)
                        st.success("✅ Guardado")
                        limpiar_cache()
                        time.sleep(1)
                        st.rerun()

def verificador_cupos():
    st.subheader("🚦 Semáforo de Inscripciones (Torneos Abiertos)")
    query = "SELECT t.id, t.nombre, i.categoria, COUNT(*) as cantidad FROM inscripciones i JOIN torneos t ON i.torneo_id = t.id WHERE t.estado = 'Abierto' GROUP BY t.id, t.nombre, i.categoria ORDER BY t.id DESC"
    df = cargar_datos(query)
    if df is None or df.empty:
        st.info("No hay inscripciones activas para monitorear.")
    else:
        cols = st.columns(4)
        for index, row in df.iterrows():
            count = row['cantidad']
            label = f"{row['nombre']}\n({row['categoria']})"
            with cols[index % 4]:
                if count < 3: st.error(f"**{label}**\n\n🚨 **{count}** Parejas\n\n*CRÍTICO: Insuficiente*")
                elif count == 3: st.warning(f"**{label}**\n\n⚠️ **{count}** Parejas\n\n*MÍNIMO: Zona Única*")
                else: st.success(f"**{label}**\n\n✅ **{count}** Parejas\n\n*LISTO: Cupo Completo*")
    st.divider()

def seccion_transferir_jugadores():
    st.subheader("🔄 Transferencia de Inscripciones")
    st.info("Herramienta para mover inscripciones entre torneos (útil para correcciones).")
    df_t = get_data("SELECT id, nombre, categoria FROM torneos ORDER BY id DESC")
    if df_t is None or df_t.empty:
        st.warning("No hay torneos registrados.")
        return
    opts_t = {row['id']: f"[{row['id']}] {row['nombre']} - {row['categoria']}" for _, row in df_t.iterrows()}
    col1, col2 = st.columns(2)
    with col1:
        id_origen = st.selectbox("Desde Torneo (Origen)", options=list(opts_t.keys()), format_func=lambda x: opts_t[x], key="t_origen_trans")
    with col2:
        id_destino = st.selectbox("Hacia Torneo (Destino)", options=list(opts_t.keys()), format_func=lambda x: opts_t[x], key="t_dest_trans")
    if id_origen == id_destino:
        st.error("El origen y el destino no pueden ser el mismo torneo.")
        return
    df_insc = get_data("SELECT id, jugador1, jugador2 FROM inscripciones WHERE torneo_id = :tid", params={"tid": id_origen})
    if df_insc is None or df_insc.empty:
        st.warning("El torneo de origen no tiene inscriptos.")
        return
    map_insc = {f"{row['jugador1']} - {row['jugador2']}": row['id'] for _, row in df_insc.iterrows()}
    sel_ids = st.multiselect("Seleccionar Parejas a Mover", options=list(map_insc.keys()))
    if st.button("🚀 Confirmar Transferencia", type="primary"):
        if not sel_ids:
            st.error("Debes seleccionar al menos una pareja.")
            return
        count_moved = 0
        count_skipped = 0
        df_dest = get_data("SELECT jugador1, jugador2 FROM inscripciones WHERE torneo_id = :tid", params={"tid": id_destino})
        parejas_dest = []
        if df_dest is not None and not df_dest.empty:
            for _, row in df_dest.iterrows():
                parejas_dest.append({row['jugador1'], row['jugador2']})
        for p_str in sel_ids:
            insc_id = map_insc[p_str]
            row_src = df_insc[df_insc['id'] == insc_id].iloc[0]
            p_src_set = {row_src['jugador1'], row_src['jugador2']}
            if p_src_set in parejas_dest:
                st.toast(f"⚠️ {p_str} ya existe en el destino. Omitido.", icon="🚫")
                count_skipped += 1
            else:
                run_action("UPDATE inscripciones SET torneo_id = %(dest)s WHERE id = %(id)s", {"dest": id_destino, "id": insc_id})
                count_moved += 1
        if count_moved > 0:
            st.success(f"✅ Se movieron {count_moved} parejas al Torneo [ID: {id_destino}].")
            if count_skipped > 0: st.warning(f"⚠️ Se omitieron {count_skipped} parejas por estar duplicadas en el destino.")
            st.cache_data.clear()
            time.sleep(2)
            st.rerun()
        elif count_skipped > 0:
             st.error("❌ Todas las parejas seleccionadas ya existen en el torneo de destino.")

def debug_base_datos():
    st.markdown("---")
    st.subheader("🕵️ Debug Base de Datos")
    with st.expander("🔍 Ver Datos Crudos (Torneos, Inscripciones, Zonas)"):
        st.write("### 🏆 Torneos")
        st.dataframe(cargar_datos("SELECT * FROM torneos"), use_container_width=True)
        st.write("### 📝 Inscripciones")
        st.dataframe(cargar_datos("SELECT * FROM inscripciones"), use_container_width=True)
        st.write("### 🔢 Zonas")
        st.dataframe(cargar_datos("SELECT * FROM zonas"), use_container_width=True)

def sincronizar_datos_nube_a_local():
    local_db_file = 'torneos_padel.db'
    tablas_a_sincronizar = ['torneos', 'inscripciones', 'jugadores', 'zonas', 'partidos', 'zonas_posiciones', 'eventos', 'ranking_puntos', 'fotos', 'partido_en_vivo']
    total_tablas = len(tablas_a_sincronizar)
    progress_bar = st.progress(0, text="Preparando entorno local...")
    try:
        with sqlite3.connect(local_db_file) as conn_local:
            cursor = conn_local.cursor()
            cursor.execute("PRAGMA foreign_keys = OFF;")
            for i, tabla in enumerate(tablas_a_sincronizar):
                progress_bar.progress(i / total_tablas, text=f"Descargando tabla: {tabla} ({i+1}/{total_tablas})...")
                df_nube = cargar_datos(f"SELECT * FROM {tabla}")
                if df_nube is not None: df_nube.to_sql(tabla, conn_local, if_exists='replace', index=False)
                else: st.write(f"  -> Tabla `{tabla}` vacía en la nube o no se pudo leer. Omitiendo.")
            progress_bar.progress(1.0, text="¡Sincronización finalizada!")
            time.sleep(0.5) # Pequeña pausa para que el usuario vea el 100%

            # Reactivar las claves foráneas
            cursor.execute("PRAGMA foreign_keys = ON;")
        return True, "Sincronización completada con éxito."
    except Exception as e:
        progress_bar.empty() # Limpiar la barra si ocurre un error catastrófico
        return False, f"Error durante la sincronización: {e}"

def actualizar_tabla_posiciones(torneo_id):
    """Recalcula los puntos de la tabla de posiciones basándose en los partidos jugados."""
    
    # 1. Resetear valores a 0 (Incluyendo las nuevas columnas Games)
    run_action("UPDATE zonas_posiciones SET pts=0, pj=0, pg=0, pp=0, sf=0, sc=0, ds=0, gf=0, gc=0, dg=0 WHERE torneo_id=%(torneo_id)s", {"torneo_id": torneo_id})
    
    # Obtener partidos jugados
    df_partidos = cargar_datos("SELECT id, pareja1, pareja2, resultado, ganador, set1, set2, set3 FROM partidos WHERE torneo_id=:torneo_id AND instancia='Zona' AND estado_partido='Finalizado' ORDER BY id ASC", {"torneo_id": torneo_id})
    
    if df_partidos is None or df_partidos.empty:
        return
    
    for _, row in df_partidos.iterrows():
        p1, p2, ganador = row['pareja1'], row['pareja2'], row['ganador']
        
        # Analizar sets para estadísticas detalladas
        sets_p1, sets_p2 = 0, 0
        games_p1, games_p2 = 0, 0
        
        sets_data = [row['set1'], row['set2'], row['set3']]
        for s in sets_data:
            if s and '-' in s:
                try:
                    g1 = int(s.split('-')[0])
                    g2 = int(s.split('-')[1])
                    
                    games_p1 += g1
                    games_p2 += g2
                    
                    if g1 > g2: sets_p1 += 1
                    elif g2 > g1: sets_p2 += 1
                except:
                    pass
        
        # Actualizar PJ
        for p in [p1, p2]:
             run_action("UPDATE zonas_posiciones SET pj = pj + 1 WHERE torneo_id=%(torneo_id)s AND pareja=%(pareja)s", {"torneo_id": torneo_id, "pareja": p})

        # Actualizar Estadísticas P1
        run_action("""
            UPDATE zonas_posiciones SET 
                sf = sf + :sf, sc = sc + :sc, ds = ds + :ds,
                gf = gf + :gf, gc = gc + :gc, dg = dg + :dg
            WHERE torneo_id = :tid AND pareja = :p
        """, {"sf": sets_p1, "sc": sets_p2, "ds": sets_p1 - sets_p2, "gf": games_p1, "gc": games_p2, "dg": games_p1 - games_p2, "tid": torneo_id, "p": p1})

        # Actualizar Estadísticas P2
        run_action("""
            UPDATE zonas_posiciones SET 
                sf = sf + :sf, sc = sc + :sc, ds = ds + :ds,
                gf = gf + :gf, gc = gc + :gc, dg = dg + :dg
            WHERE torneo_id = :tid AND pareja = :p
        """, {"sf": sets_p2, "sc": sets_p1, "ds": sets_p2 - sets_p1, "gf": games_p2, "gc": games_p1, "dg": games_p2 - games_p1, "tid": torneo_id, "p": p2})

        # Actualizar Puntos (3 Ganador, 1 Perdedor)
        if ganador:
            perdedor = p2 if ganador == p1 else p1
            # Sumar PG y Pts al Ganador
            run_action("UPDATE zonas_posiciones SET pts = pts + 3, pg = pg + 1 WHERE torneo_id=%(torneo_id)s AND pareja=%(pareja)s", {"torneo_id": torneo_id, "pareja": ganador})
            # Sumar PP y Pts al Perdedor
            run_action("UPDATE zonas_posiciones SET pts = pts + 1, pp = pp + 1 WHERE torneo_id=%(torneo_id)s AND pareja=%(pareja)s", {"torneo_id": torneo_id, "pareja": perdedor})
            
    # --- LÓGICA MODIFICADA PARA ZONAS DE 4 ---
    df_zonas = cargar_datos("SELECT nombre_zona, pareja FROM zonas WHERE torneo_id=:torneo_id", {"torneo_id": torneo_id})
    if df_zonas is not None and not df_zonas.empty:
        zonas_dict = {}
        for _, row in df_zonas.iterrows():
            z = row['nombre_zona']
            p = row['pareja']
            if z not in zonas_dict:
                zonas_dict[z] = []
            zonas_dict[z].append(p)
            
        for zona, parejas_en_zona in zonas_dict.items():
            if len(parejas_en_zona) == 4:
                partidos_zona = []
                for _, row in df_partidos.iterrows():
                    if row['pareja1'] in parejas_en_zona and row['pareja2'] in parejas_en_zona:
                        partidos_zona.append(row)
                
                cruce1 = None
                cruce2 = None
                for p in partidos_zona:
                    if cruce1 is None:
                        cruce1 = p
                    else:
                        if p['pareja1'] not in [cruce1['pareja1'], cruce1['pareja2']] and \
                           p['pareja2'] not in [cruce1['pareja1'], cruce1['pareja2']]:
                            cruce2 = p
                            break
                            
                if cruce1 and cruce2:
                    ganador_c1 = cruce1['ganador']
                    ganador_c2 = cruce2['ganador']
                    perdedor_c1 = cruce1['pareja2'] if ganador_c1 == cruce1['pareja1'] else cruce1['pareja1']
                    perdedor_c2 = cruce2['pareja2'] if ganador_c2 == cruce2['pareja1'] else cruce2['pareja1']
                    
                    partido_ganadores = None
                    partido_perdedores = None
                    for p in partidos_zona:
                        if p['id'] in [cruce1['id'], cruce2['id']]: continue
                        if ganador_c1 and ganador_c2 and ((p['pareja1'] == ganador_c1 and p['pareja2'] == ganador_c2) or (p['pareja1'] == ganador_c2 and p['pareja2'] == ganador_c1)):
                            partido_ganadores = p
                        if perdedor_c1 and perdedor_c2 and ((p['pareja1'] == perdedor_c1 and p['pareja2'] == perdedor_c2) or (p['pareja1'] == perdedor_c2 and p['pareja2'] == perdedor_c1)):
                            partido_perdedores = p
                            
                    posiciones_forzadas = {}
                    if partido_ganadores and partido_ganadores['ganador']:
                        posiciones_forzadas[partido_ganadores['ganador']] = 6
                        posiciones_forzadas[partido_ganadores['pareja2'] if partido_ganadores['ganador'] == partido_ganadores['pareja1'] else partido_ganadores['pareja1']] = 5
                    if partido_perdedores and partido_perdedores['ganador']:
                        posiciones_forzadas[partido_perdedores['ganador']] = 4
                        posiciones_forzadas[partido_perdedores['pareja2'] if partido_perdedores['ganador'] == partido_perdedores['pareja1'] else partido_perdedores['pareja1']] = 2
                    
                    for pareja, pts_forzados in posiciones_forzadas.items():
                        run_action("UPDATE zonas_posiciones SET pts = %(pts)s WHERE torneo_id=%(torneo_id)s AND pareja=%(pareja)s", {"torneo_id": torneo_id, "pareja": pareja, "pts": pts_forzados})
                        
    limpiar_cache()

def generar_bracket_inicial(torneo_id):
    if not st.session_state.get('es_admin', False): return False, "Acceso denegado"
    
    # Verificar si ya existe cuadro
    df_check = cargar_datos("SELECT count(*) as c FROM partidos WHERE torneo_id = :torneo_id AND bracket_pos IS NOT NULL", {"torneo_id": torneo_id})
    if df_check is not None and not df_check.empty and df_check.iloc[0]['c'] > 0:
        return False, "El cuadro ya existe para este torneo."

    # Estructura fija de 16 equipos (Octavos -> Final)
    # Posiciones: 1-8 (Octavos), 9-12 (Cuartos), 13-14 (Semis), 15 (Final)
    cruces = [
        (1, "1º Zona A", "2º Zona B", "Octavos"), (2, "1º Zona C", "2º Zona D", "Octavos"),
        (3, "1º Zona E", "2º Zona F", "Octavos"), (4, "1º Zona G", "2º Zona H", "Octavos"),
        (5, "2º Zona B", "1º Zona A", "Octavos"), (6, "2º Zona D", "1º Zona C", "Octavos"),
        (7, "2º Zona F", "1º Zona E", "Octavos"), (8, "2º Zona H", "1º Zona G", "Octavos"),
        (9, "Ganador O1", "Ganador O2", "Cuartos"), (10, "Ganador O3", "Ganador O4", "Cuartos"),
        (11, "Ganador O5", "Ganador O6", "Cuartos"), (12, "Ganador O7", "Ganador O8", "Cuartos"),
        (13, "Ganador C1", "Ganador C2", "Semis"), (14, "Ganador C3", "Ganador C4", "Semis"),
        (15, "Ganador S1", "Ganador S2", "Final")
    ]
    
    for pos, p1, p2, inst in cruces:
        run_action("INSERT INTO partidos (torneo_id, pareja1, pareja2, instancia, bracket_pos, resultado) VALUES (%(torneo_id)s, %(pareja1)s, %(pareja2)s, %(instancia)s, %(bracket_pos)s, '')",
                  {"torneo_id": torneo_id, "pareja1": p1, "pareja2": p2, "instancia": inst, "bracket_pos": pos})
    
    limpiar_cache()
    return True, "Cuadro generado correctamente."

def actualizar_bracket(partido_id, torneo_id, bracket_pos, resultado, ganador_nombre):
    if not st.session_state.get('es_admin', False): return
    
    # 1. Guardar resultado actual y el GANADOR
    run_action("UPDATE partidos SET resultado = %(resultado)s, ganador = %(ganador)s WHERE id = %(id)s", {"resultado": resultado, "ganador": ganador_nombre, "id": partido_id})
    
    # 2. Calcular siguiente partido
    next_pos = 0
    slot = 0 # 1 para pareja1, 2 para pareja2
    
    if bracket_pos <= 8: # Octavos -> Cuartos (9-12)
        next_pos = 9 + (bracket_pos - 1) // 2
        slot = 1 if bracket_pos % 2 != 0 else 2
    elif bracket_pos <= 12: # Cuartos -> Semis (13-14)
        next_pos = 13 + (bracket_pos - 9) // 2
        slot = 1 if bracket_pos % 2 != 0 else 2
    elif bracket_pos <= 14: # Semis -> Final (15)
        next_pos = 15
        slot = 1 if bracket_pos % 2 != 0 else 2
        
    # 3. Avanzar ganador si no es la final
    if next_pos > 0:
        campo_destino = "pareja1" if slot == 1 else "pareja2"
        run_action(f"UPDATE partidos SET {campo_destino} = %(ganador_nombre)s WHERE torneo_id = %(torneo_id)s AND bracket_pos = %(bracket_pos)s", 
                  {"ganador_nombre": ganador_nombre, "torneo_id": torneo_id, "bracket_pos": next_pos})
        
    limpiar_cache()

def actualizar_estado_partido(partido_id, nuevo_estado):
    if not st.session_state.get('es_admin', False): return
    run_action("UPDATE partidos SET estado_partido = %(estado_partido)s WHERE id = %(id)s", {"estado_partido": nuevo_estado, "id": partido_id})
    limpiar_cache()

def actualizar_marcador(partido_id, resultado):
    if not st.session_state.get('es_admin', False): return
    run_action("UPDATE partidos SET resultado = %(resultado)s WHERE id = %(id)s", {"resultado": resultado, "id": partido_id})
    limpiar_cache()

def guardar_foto(nombre, imagen):
    if not st.session_state.get('es_admin', False): return
    # Postgres usa BYTEA para binarios, pasamos los bytes directamente
    run_action("INSERT INTO fotos (nombre, imagen, fecha) VALUES (%(nombre)s, %(imagen)s, NOW())", 
              {"nombre": nombre, "imagen": imagen})
    limpiar_cache()

def guardar_jugador(celular, password, nombre, apellido, localidad, cat_actual, cat_anterior, foto_blob):
    if not st.session_state.get('es_admin', False): return
    # Usamos ON CONFLICT para emular INSERT OR REPLACE de SQLite
    sql = """
    INSERT INTO jugadores (celular, password, nombre, apellido, localidad, categoria_actual, categoria_anterior, foto, estado_cuenta) 
    VALUES (%(celular)s, %(password)s, %(nombre)s, %(apellido)s, %(localidad)s, %(categoria_actual)s, %(categoria_anterior)s, %(foto)s, 'Pendiente')
    ON CONFLICT (celular) DO UPDATE SET
    password = EXCLUDED.password,
    nombre = EXCLUDED.nombre,
    apellido = EXCLUDED.apellido,
    localidad = EXCLUDED.localidad,
    categoria_actual = EXCLUDED.categoria_actual,
    categoria_anterior = EXCLUDED.categoria_anterior,
    foto = EXCLUDED.foto;
    """
    run_action(sql, {"celular": celular, "password": hash_password(password), "nombre": nombre, "apellido": apellido, "localidad": localidad, "categoria_actual": cat_actual, "categoria_anterior": cat_anterior, "foto": foto_blob if foto_blob else None})
    limpiar_cache()

def recategorizar_jugador(player_id, nueva_categoria):
    if not st.session_state.get('es_admin', False): return
    df = cargar_datos("SELECT categoria_actual FROM jugadores WHERE id = :player_id", {"player_id": player_id})
    if df is not None and not df.empty:
        cat_anterior = df.iloc[0]['categoria_actual']
        run_action("UPDATE jugadores SET categoria_anterior = %(categoria_anterior)s, categoria_actual = %(categoria_actual)s WHERE id = %(id)s", 
                  {"categoria_anterior": cat_anterior, "categoria_actual": nueva_categoria, "id": player_id})
    limpiar_cache()

def apply_watermark(image):
    draw = ImageDraw.Draw(image)
    width, height = image.size
    text = "Rincón Padel"
    
    # Tamaño de fuente dinámico (5% de la altura de la imagen)
    font_size = int(height * 0.05)
    try:
        # Intenta usar Arial si está disponible, sino default
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()
    
    # Calcular tamaño del texto
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    x = width - text_w - 20
    y = height - text_h - 20
    
    # Dibujar texto con sombra para contraste
    draw.text((x+2, y+2), text, font=font, fill="black")
    draw.text((x, y), text, font=font, fill="#39FF14") # Verde Neón
    
    return image

# --- LOGICA DE SCORING (TENIS) ---
def obtener_puntos_display(pts):
    """Convierte el valor numérico interno (0-3) a string de tenis (0-40)."""
    mapping = {0: "0", 1: "15", 2: "30", 3: "40", 4: "AD"}
    return mapping.get(pts, str(pts))

def sumar_punto(match_id, player_idx, current_state):
    """
    Lógica de tenis para sumar puntos.
    player_idx: 1 (Pareja 1) o 2 (Pareja 2)
    current_state: dict con estado actual
    """
    p1 = current_state.get('p1_pts', 0)
    p2 = current_state.get('p2_pts', 0)
    g1 = current_state.get('p1_games', 0)
    g2 = current_state.get('p2_games', 0)
    
    # Lógica simplificada de puntos (0,1,2,3 -> 0,15,30,40)
    # 4 = Ventaja
    
    winner = 'p1' if player_idx == 1 else 'p2'
    
    game_won = False
    
    if winner == 'p1':
        if p1 == 3 and p2 < 3: # 40-0, 40-15, 40-30 -> Game
            game_won = True
        elif p1 == 3 and p2 == 3: # Deuce -> Ventaja P1
            p1 = 4
        elif p1 == 4: # Ventaja P1 -> Game
            game_won = True
        elif p1 == 3 and p2 == 4: # Ventaja P2 -> Deuce
            p2 = 3
        else:
            p1 += 1
    else: # winner p2
        if p2 == 3 and p1 < 3:
            game_won = True
        elif p2 == 3 and p1 == 3: # Deuce -> Ventaja P2
            p2 = 4
        elif p2 == 4: # Ventaja P2 -> Game
            game_won = True
        elif p2 == 3 and p1 == 4: # Ventaja P1 -> Deuce
            p1 = 3
        else:
            p2 += 1
            
    if game_won:
        if winner == 'p1': g1 += 1
        else: g2 += 1
        p1, p2 = 0, 0 # Reset puntos
    
    # Actualizar Estado
    st.session_state[f"live_{match_id}"] = {
        'p1_pts': p1, 'p2_pts': p2, 
        'p1_games': g1, 'p2_games': g2
    }
    
    # Construir Strings para DB
    pts_str = f"{obtener_puntos_display(p1)}-{obtener_puntos_display(p2)}"
    games_str = f"{g1}-{g2}"
    
    # Recuperar sets previos si existen (desde DB o session)
    sets_previos = current_state.get('sets_str', "")
    full_score_db = f"{sets_previos} {games_str}".strip()
    banner_score = f"{games_str} | {pts_str}"
    if sets_previos:
        banner_score = f"{sets_previos} | {games_str} ({pts_str})"

    # Actualizar DB
    run_action("UPDATE partidos SET resultado = %(res)s WHERE id = %(id)s", {"res": full_score_db, "id": match_id})
    run_action("UPDATE partido_en_vivo SET marcador = %(marc)s WHERE torneo = %(tid)s", 
              {"marc": banner_score, "tid": str(current_state.get('torneo_id', 0))})

def clean_phone(phone):
    if not phone: return ""
    # Eliminar todo lo que no sea dígito
    p = "".join(filter(str.isdigit, str(phone)))
    # Agregar código de país 54 si no lo tiene (asumiendo Argentina)
    if not p.startswith("54"):
        p = "54" + p
    return p

def create_wa_link(phone, message):
    base = "https://wa.me/"
    p = clean_phone(phone)
    msg = urllib.parse.quote(message)
    return f"{base}{p}?text={msg}"

def mask_phone_number(phone):
    if not phone: return "🔒 Privado"
    p = str(phone)
    if len(p) >= 4:
        return p[:4] + "-XXXXXX"
    return "🔒 Privado"

def mostrar_seccion_sede():
    # Encabezado
    st.markdown("""
        <h1 style="text-align: center;">📍 Rincón Padel Villaguay</h1>
        <p style="text-align: center; font-size: 1.1rem; color: #ccc;">
            Somos <span style="color: #00FF00; font-weight: bold;">Rincón Padel Villaguay</span>, nos ubicamos en la esquina de <span style="color: #00FF00; font-weight: bold;">Buenos Aires y Cinto</span>. 
            Vení a conocer nuestras instalaciones y a disfrutar del mejor pádel de la ciudad. ¡Te esperamos!
        </p>
    """, unsafe_allow_html=True)

    # Mapa
    mapa_html = """<div style="display: flex; justify-content: center; padding: 20px 0;"><iframe src="https://www.google.com/maps/embed?pb=!1m17!1m12!1m3!1d299.47519571623354!2d-59.02399176228754!3d-31.874656111865367!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m2!1m1!2zMzHCsDUyJzI5LjAiUyA1OcKwMDEnMjUuNCJX!5e0!3m2!1ses-419!2sar!4v1773343895058!5m2!1ses-419!2sar" width="100%" height="300" style="border: 1px solid #333; border-radius: 12px; box-shadow: 0 0 15px rgba(0, 255, 0, 0.1);" allowfullscreen="" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe></div>"""
    components.html(mapa_html, height=340)

    # Divisor
    st.divider()

    # Galería
    st.markdown("<h3>📸 Galería de Canchas</h3>", unsafe_allow_html=True)

    # Helper para estilo de imagen
    def img_card(path, caption):
        st.markdown("<div style='background-color: #1A1A1A; border: 1px solid #333; border-radius: 10px; padding: 10px;'>", unsafe_allow_html=True)
        
        # Optimización: Usamos load_local_image (con @st.cache_data) en lugar de leer directo del path
        img = load_local_image(path)
        
        if img:
            st.image(img, caption=caption, use_container_width=True)
        else:
            st.warning(f"Imagen no encontrada: {path}")
        st.markdown("</div>", unsafe_allow_html=True)

    # Fila 1
    col1, col2, col3 = st.columns(3)
    with col1: img_card("images/cancha1.jpg", "Cancha 1")
    with col2: img_card("images/cancha2.jpg", "Cancha 2")
    with col3: img_card("images/cancha3.jpg", "Cancha 3")

    st.write("") # Separador vertical

    # Fila 2
    col4, col5, col_vacia = st.columns(3)
    with col4: img_card("images/cancha4.jpg", "Cancha 4")
    with col5: img_card("images/cancha5.jpg", "Cancha 5")
    with col_vacia: st.write("")

def get_inscripcion_by_pareja(pareja_str):
    # Busca en inscripciones la pareja que coincida con el string "J1 - J2"
    df = get_data("SELECT * FROM inscripciones")
    for _, row in df.iterrows():
        if f"{row['jugador1']} - {row['jugador2']}" == pareja_str:
            return row
    return None

@st.cache_data(ttl=600)
def get_fotos():
    df = cargar_datos("SELECT nombre, imagen FROM fotos ORDER BY id DESC")
    # Convertir a lista de tuplas para compatibilidad
    return list(df.itertuples(index=False, name=None))

def validar_nivel(cat_jugador, cat_torneo):
    """
    Valida si un jugador puede anotarse en un torneo.
    Regla: Jugador (Nivel X) no puede jugar en Torneo (Nivel > X).
    Ej: Jugador 5ta (5) NO puede jugar en 6ta (6).
    Ej: Jugador 5ta (5) SI puede jugar en 4ta (4).
    """
    niveles = {
        "Libre": 1, "3ra": 3, "4ta": 4, "5ta": 5, "6ta": 6, "7ma": 7, "8va": 8, "Suma 12": 6 # Asumimos Suma 12 como nivel intermedio/bajo para validación simple
    }
    
    nivel_j = niveles.get(cat_jugador, 99)
    nivel_t = niveles.get(cat_torneo, 0)
    
    # Si el nivel del jugador es menor (mejor) que el del torneo, es trampa (bajar de categoría)
    if nivel_j < nivel_t:
        return False, f"Tu nivel ({cat_jugador}) es superior al permitido para este torneo ({cat_torneo})."
    return True, "OK"

def registrar_jugador_db(dni, nombre, apellido, celular, categoria, localidad="", password=None):
    try:
        # 1. Verificar si el usuario ya existe por DNI
        df = cargar_datos("SELECT id, password FROM jugadores WHERE dni = :dni", {"dni": dni})
        
        if df is not None and not df.empty:
            user_data = df.iloc[0]
            stored_pass = user_data['password']
            
            # Si el password es nulo o vacío, es una cuenta creada por Admin -> PERMITIR RECLAMO
            if pd.isna(stored_pass) or stored_pass == "":
                final_pass = password if password else dni
                
                # Ejecutamos UPDATE (Reclamo de cuenta)
                run_action("""
                    UPDATE jugadores SET 
                        password = :password, nombre = :nombre, apellido = :apellido, 
                        celular = :celular, categoria_actual = :categoria, 
                        localidad = :localidad, estado_cuenta = 'Activa' 
                    WHERE dni = :dni
                """, {"password": hash_password(final_pass), "nombre": nombre, "apellido": apellido, 
                      "celular": celular, "categoria": categoria, "localidad": localidad, "dni": dni})
                
                limpiar_cache()
                return True, "Cuenta reclamada y activada exitosamente."
            else:
                return False, "Este DNI ya está registrado. Por favor, inicia sesión."

        # 2. Si no existe, INSERT normal (Cuenta Nueva)
        final_pass = password if password else dni
        run_action("""
            INSERT INTO jugadores (dni, celular, password, nombre, apellido, categoria_actual, localidad, estado_cuenta) 
            VALUES (:dni, :celular, :password, :nombre, :apellido, :categoria, :localidad, 'Pendiente')
        """, {"dni": dni, "celular": celular, "password": hash_password(final_pass), 
              "nombre": nombre, "apellido": apellido, "categoria": categoria, "localidad": localidad})
              
        limpiar_cache()
        return True, "Registro exitoso."
    except Exception as e:
        # Capturamos error genérico de DB (IntegrityError de sqlalchemy/psycopg2)
        return False, f"Error al registrar: {str(e)}"

def eliminar_jugador(dni):
    if not st.session_state.get('es_admin', False): return
    run_action("DELETE FROM jugadores WHERE dni = %(dni)s", {"dni": dni})
    limpiar_cache()

def autenticar_usuario(dni, password):
    df = cargar_datos("SELECT id, dni, nombre, apellido, localidad, categoria_actual, celular FROM jugadores WHERE dni = :dni AND password = :password", {"dni": dni, "password": hash_password(password)})
    if df is not None and not df.empty:
        user = df.iloc[0]
        return {
            "id": user['id'], "dni": user['dni'], "nombre": user['nombre'], "apellido": user['apellido'],
            "localidad": user['localidad'], "categoria": user['categoria_actual'], "celular": user['celular']
        }
    return None

@st.fragment
def formulario_inscripcion_pareja(torneo_id, cat_torneo):
    """Muestra y procesa el formulario de inscripción para una pareja (Optimizado por pasos)."""
    st.markdown("<div class='zona-header'>FORMULARIO DE INSCRIPCIÓN</div>", unsafe_allow_html=True)
    
    # Inicializar estado del paso
    if 'form_step' not in st.session_state:
        st.session_state.form_step = 1

    # Persistencia Real: Inicializar variables de formulario si no existen
    for k in ['f_nombre_j1', 'f_nombre_j2', 'f_dni_j1', 'f_dni_j2', 'f_tel_j1', 'f_tel_j2', 'f_localidad']:
        if k not in st.session_state:
            st.session_state[k] = ""

    # Barra de progreso
    progress = 50 if st.session_state.form_step == 1 else 100
    st.progress(progress, text=f"Paso {st.session_state.form_step} de 2")

    with st.container(border=True):
        if st.session_state.form_step == 1:
            st.subheader("👥 Paso 1: Jugadores")
            st.info(f"Categoría: **{cat_torneo}**")
            
            is_admin = st.session_state.get('es_admin', False)
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Jugador 1**")
                if is_admin:
                    n1 = st.text_input("Nombre", key="adm_n_j1")
                    a1 = st.text_input("Apellido", key="adm_a_j1")
                    nombre_j1 = f"{n1} {a1}".strip()
                    tel_j1 = st.text_input("Celular", key="f_tel_j1")
                    dni_j1 = f"ADMIN-{tel_j1}" if tel_j1 else ""
                else:
                    nombre_j1 = st.text_input("Nombre Completo", key="f_nombre_j1")
                    dni_j1 = st.text_input("DNI", key="f_dni_j1", help="Sin puntos")
                    tel_j1 = st.text_input("Teléfono", key="f_tel_j1")
            
            with c2:
                st.markdown("**Jugador 2**")
                if is_admin:
                    n2 = st.text_input("Nombre", key="adm_n_j2")
                    a2 = st.text_input("Apellido", key="adm_a_j2")
                    nombre_j2 = f"{n2} {a2}".strip()
                    tel_j2 = st.text_input("Celular", key="f_tel_j2")
                    dni_j2 = f"ADMIN-{tel_j2}" if tel_j2 else ""
                else:
                    nombre_j2 = st.text_input("Nombre Completo", key="f_nombre_j2")
                    dni_j2 = st.text_input("DNI", key="f_dni_j2", help="Sin puntos")
                    tel_j2 = st.text_input("Teléfono", key="f_tel_j2")

            st.write("")
            if st.button("Siguiente ➡️", type="primary", use_container_width=True):
                if all([nombre_j1, dni_j1, tel_j1, nombre_j2, dni_j2, tel_j2]):
                    if dni_j1 != dni_j2:
                        # Solución de Persistencia (Manual) - Anclar variables
                        st.session_state['nombre_j1_final'] = nombre_j1
                        st.session_state['nombre_j2_final'] = nombre_j2
                        st.session_state['tel_j1_final'] = tel_j1
                        st.session_state['tel_j2_final'] = tel_j2
                        
                        st.session_state.form_step = 2
                        st.rerun()
                    else:
                        st.error("❌ Los DNI no pueden ser iguales.")
                else:
                    st.warning("⚠️ Completa todos los campos.")

        elif st.session_state.form_step == 2:
            st.subheader("📍 Paso 2: Confirmación")
            
            # Recuperar datos de variables 'ancladas'
            n1 = st.session_state.get('nombre_j1_final', '')
            n2 = st.session_state.get('nombre_j2_final', '')
            t1 = st.session_state.get('tel_j1_final', '')
            t2 = st.session_state.get('tel_j2_final', '')
            
            st.write(f"**Pareja:** {n1} & {n2}")
            
            localidad = st.text_input("Localidad de la Pareja", key="f_localidad")
            
            st.divider()
            c_back, c_conf = st.columns([1, 2])
            
            with c_back:
                if st.button("⬅️ Volver"):
                    st.session_state.form_step = 1
                    st.rerun()
            
            with c_conf:
                if st.button("✅ Confirmar Inscripción", type="primary", use_container_width=True):
                    if localidad:
                        with custom_spinner():
                            # Simular delay visual para la animación
                            time.sleep(1)
                            guardar_inscripcion(
                                torneo_id, 
                                n1, 
                                n2, 
                                localidad, 
                                cat_torneo, 
                                False, 
                                t1, 
                                t2
                            )
                        
                        st.success("¡Inscripción Exitosa!")
                        st.balloons()
                        st.session_state.form_step = 1
                        if 'mostrar_formulario' in st.session_state:
                            st.session_state['mostrar_formulario'] = False
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.warning("⚠️ Ingresa la localidad.")

# --- LOTTIE ANIMATIONS ---
@st.cache_data(show_spinner=False)
def load_lottieurl(url):
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

# --- GRÁFICO TIMELINE (PLOTLY) ---
def generar_grafico_timeline(torneo_id):
    # 1. Obtener datos de partidos con horario y cancha
    df = cargar_datos("SELECT id, pareja1, pareja2, instancia, horario, cancha FROM partidos WHERE torneo_id = :torneo_id AND horario IS NOT NULL ORDER BY horario", params={"torneo_id": torneo_id})
    
    if df is None or df.empty:
        return None
        
    # 2. Procesar datos para Plotly
    data = []
    for _, row in df.iterrows():
        try: # Usar try-except para evitar que un formato de fecha erróneo rompa el gráfico
            start = datetime.strptime(row['horario'], "%Y-%m-%d %H:%M")
            # Asumimos duración visual de 1h 15m para el bloque
            end = start + timedelta(hours=1, minutes=15)
            
            # Etiqueta compacta para móviles
            # Limpiamos prefijos de zona si existen (ej: "1A - ") para el gráfico
            p1_clean = row['pareja1'].split(' - ')[-1] if ' - ' in str(row['pareja1']) else row['pareja1']
            p2_clean = row['pareja2'].split(' - ')[-1] if ' - ' in str(row['pareja2']) else row['pareja2']
            
            # Intentar obtener apellidos cortos
            p1_short = p1_clean.split(' ')[0] if pd.notna(p1_clean) and p1_clean else "?"
            p2_short = p2_clean.split(' ')[0] if pd.notna(p2_clean) and p2_clean else "?"
            
            # Etiqueta Completa para dentro de la barra
            label = f"{p1_short} vs {p2_short}"
            # Etiqueta Detallada para Hover
            hover_lbl = f"Instancia: {row['instancia']}<br>{p1_clean} vs {p2_clean}"
            
            cancha = row.get('cancha') or "Cancha Central"
            
            data.append(dict(Cancha=cancha, Inicio=start, Fin=end, Partido=label, Detalle=hover_lbl))
        except (ValueError, TypeError):
            continue
            
    if not data: return None
    df_plot = pd.DataFrame(data)
    
    # 3. Crear Gráfico Timeline
    fig = px.timeline(df_plot, x_start="Inicio", x_end="Fin", y="Cancha", text="Partido", color="Cancha", hover_name="Detalle")
    
    # 4. Estilizado dinámico y adaptable a tema
    num_canchas = len(df_plot['Cancha'].unique())
    height = 100 + (num_canchas * 60)
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        showlegend=False, height=height, margin=dict(l=10, r=10, t=30, b=10),
        # Habilitar ZOOM y PAN en el eje X (Time), fijo en Y
        xaxis=dict(showgrid=True, tickformat="%H:%M", side="top", title=None, fixedrange=False),
        yaxis=dict(title=None, autorange="reversed")
    )
    fig.update_traces(textposition="inside", insidetextanchor="middle", textfont_size=12)

    # Aplicar colores según el tema
    if st.session_state.get('theme', False): # Modo Claro
        fig.update_layout(font_color="#2E7D32", xaxis_gridcolor='#ddd')
        fig.update_traces(textfont_color="white", marker_line_color='#2E7D32', marker_line_width=2)
    else: # Modo Oscuro
        fig.update_layout(font_color="white", xaxis_gridcolor='#333')
        fig.update_traces(textfont_color="white", marker_line_color='#00FF41', marker_line_width=2)

    return fig

# Definición de URLs de Assets (Sin carga bloqueante en scope global)
URL_LOTTIE_PLAYER = "https://assets9.lottiefiles.com/packages/lf20_vo0a1yca.json"
URL_LOTTIE_TROPHY = "https://assets10.lottiefiles.com/packages/lf20_touohxv0.json"
URL_LOTTIE_BALL = "https://lottie.host/8e2f644b-6101-447a-ba98-0c3f59518d6e/3rXo1O3vVv.json"
URL_LOTTIE_MATCH = "https://lottie.host/8e3d5b7a-6f4e-4b9a-9e1d-3c2b1a0f9e8d/padel_animation.json"

# Inicializar DB al arrancar
init_db()

# --- FRAGMENTOS DE UI (OPTIMIZACIÓN CLIENT-SIDE) ---

@st.fragment
def show_torneos_eventos_content():
    """Fragmento aislado para la gestión de torneos. Evita recargar toda la app al cambiar pestañas."""
    # --- BANNER EN VIVO (COMPONENT) ---
    df_live = obtener_partido_en_vivo()
    if df_live is not None and not df_live.empty:
        live = df_live.iloc[0]
        st.markdown(f"""
        <style>
            @keyframes pulse-neon-border {{
                0% {{ border-color: #00FF41; box-shadow: 0 0 10px #00FF41, inset 0 0 5px #00FF41; }}
                50% {{ border-color: #39FF14; box-shadow: 0 0 25px #00FF41, inset 0 0 15px #00FF41; }}
                100% {{ border-color: #00FF41; box-shadow: 0 0 10px #00FF41, inset 0 0 5px #00FF41; }}
            }}
            .live-banner-container {{
                background-color: #050505;
                border: 4px double #00FF41;
                border-radius: 15px;
                padding: 20px;
                text-align: center;
                margin-bottom: 30px;
                animation: pulse-neon-border 2s infinite ease-in-out;
                position: relative;
            }}
            .live-header-text {{
                color: #00FF41;
                font-family: 'Segoe UI', sans-serif;
                font-weight: 900;
                font-size: 1.4rem;
                text-transform: uppercase;
                letter-spacing: 2px;
                margin-bottom: 5px;
                text-shadow: 0 0 15px #00FF41;
            }}
            .live-sub-text {{
                color: #cccccc;
                font-size: 1rem;
                font-style: italic;
                margin-bottom: 15px;
            }}
            .live-match-row {{
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 30px;
                font-size: 1.5rem;
                font-weight: bold;
                color: #ffffff;
                flex-wrap: wrap;
            }}
            .live-score-box {{
                background-color: #111;
                border: 1px solid #333;
                padding: 10px 25px;
                border-radius: 8px;
                font-family: 'Courier New', monospace;
                font-size: 2.2rem;
                color: #39FF14;
                text-shadow: 0 0 5px #39FF14;
                margin-top: 10px;
            }}
            .live-vs-badge {{
                background-color: #333;
                color: #fff;
                padding: 5px 10px;
                border-radius: 50%;
                font-size: 0.8rem;
            }}
        </style>
        <div class="live-banner-container">
            <div class="live-header-text">⚡ EN VIVO - CANCHA CENTRAL ⚡</div>
            <div class="live-sub-text">{live['torneo']}</div>
            <div class="live-match-row">
                <div>{live['pareja1']}</div>
                <div class="live-vs-badge">VS</div>
                <div>{live['pareja2']}</div>
            </div>
            <div class="live-score-box">{live['marcador']}</div>
        </div>
        """, unsafe_allow_html=True)

    # 2. LOBBY PRINCIPAL LIMPIO
    st.markdown("<div class='rincon-header'>🏆 CIRCUITO RINCÓN PADEL - VILLAGUAY 🏆</div>", unsafe_allow_html=True)
    st.write("") 
    
    # --- LÓGICA DINÁMICA DE SELECCIÓN ---
    # 1. Cargar Eventos (Nombres únicos de torneos)
    df_torneos_all = cargar_datos("SELECT * FROM torneos ORDER BY id DESC")
    
    if df_torneos_all is None or df_torneos_all.empty:
        st.info("No hay eventos registrados en el sistema.")
    else:
        # Diccionario para mapear ID -> Nombre (Solución al problema de índice)
        # Usamos el ID como clave para asegurar unicidad y referencia directa a SQL
        dict_torneos = {row['id']: f"[ID: {row['id']}] {row['nombre']} - {row['categoria']}" for _, row in df_torneos_all.iterrows()}
        
        col_sel, col_ref = st.columns([3, 1])
        with col_sel:
            # Selector usando ID real de la DB
            sel_id_torneo = st.selectbox(
                "📅 Seleccionar Evento",
                options=list(dict_torneos.keys()),
                format_func=lambda x: dict_torneos.get(x, f"ID: {x}"),
                key="id_torneo" # Guarda el ID correcto en st.session_state['id_torneo']
            )
        with col_ref:
            st.write("")
            st.write("")
            if st.button("🔄 Refrescar Datos", help="Recargar información de la base de datos"):
                st.cache_data.clear()
                st.rerun()
        
        # Recuperar datos del torneo seleccionado usando el ID
        torneo_data = df_torneos_all[df_torneos_all['id'] == sel_id_torneo].iloc[0]
        
        # Asignar variables para compatibilidad con el resto del código
        torneo_id = int(torneo_data['id'])
        evento_sel = torneo_data['nombre']
        cat_sel = torneo_data['categoria']
        estado_torneo = torneo_data['estado']
        
        st.divider()
        
        # --- LÓGICA DE FORMULARIO DE INSCRIPCIÓN ---
        if st.session_state.get('mostrar_formulario', False):
            # Si se debe mostrar el formulario, lo renderizamos en lugar de las pestañas
            formulario_inscripcion_pareja(torneo_id, cat_sel)
            # Botón para volver
            if st.button("⬅️ Volver a la Info del Torneo"):
                st.session_state['mostrar_formulario'] = False
                st.rerun()
        else:
            # Si no, mostramos las pestañas normales del torneo
            tab_info, tab_inscriptos, tab_clasificacion, tab_fixture, tab_llaves = st.tabs([
                "📋 Info General", 
                "📝 Inscriptos",
                "📊 Clasificación", 
                "📅 Fixture", 
                "🏆 Llaves" 
            ])
        
            
            # 1. INFO GENERAL
            with tab_info:
                st.markdown(f"<div class='zona-header'>INFORMACIÓN: {evento_sel} ({cat_sel})</div>", unsafe_allow_html=True)
                
                # Mostrar Afiche si existe
                df_afiche = cargar_datos("SELECT afiche FROM eventos WHERE torneo_id = :torneo_id", params={"torneo_id": torneo_id})
                if df_afiche is not None and not df_afiche.empty and df_afiche.iloc[0]['afiche']:
                    ruta_afiche = df_afiche.iloc[0]['afiche']
                    if os.path.exists(ruta_afiche):
                        c_img1, c_img2, c_img3 = st.columns([1, 2, 1])
                        with c_img2:
                            st.image(ruta_afiche, width=400)

                # Contar inscriptos
                cant_inscriptos = cargar_datos("SELECT count(*) as c FROM inscripciones WHERE torneo_id = :torneo_id", params={"torneo_id": torneo_id}).iloc[0]['c']
                
                # Contar partidos jugados
                cant_partidos = cargar_datos("SELECT count(*) as c FROM partidos WHERE torneo_id = :torneo_id AND resultado != ''", params={"torneo_id": torneo_id}).iloc[0]['c']

                html_info_tabla = f"""
<table style="width:100%">
    <tr>
        <th style="width:40%">Concepto</th>
        <th>Detalle</th>
    </tr>
    <tr><td>📍 Estado</td><td>{estado_torneo}</td></tr>
    <tr><td>📅 Fechas</td><td>{torneo_data['fecha']}</td></tr>
    <tr><td>🏷️ Categoría</td><td>{cat_sel}</td></tr>
    <tr><td>👥 Inscriptos</td><td>{cant_inscriptos} Parejas</td></tr>
    <tr><td>🎾 Partidos Jugados</td><td>{cant_partidos}</td></tr>
</table>
"""
                st.markdown(html_info_tabla, unsafe_allow_html=True)
                
                if estado_torneo == 'Abierto':
                    st.write("")
                    if st.button("🎾 INSCRIBIR PAREJA", use_container_width=True, type="primary"):
                        st.session_state['mostrar_formulario'] = True
                        st.rerun()

                st.markdown("---")
                es_puntuable = torneo_data['es_puntuable'] if 'es_puntuable' in torneo_data else 1
                
                if es_puntuable:
                    st.subheader("🏆 Sistema de Puntuación")
                    st.markdown("""
                    <table style="width:100%; text-align:center; border: 1px solid #333;">
                        <tr style="background-color:#1E1E1E; color:#00E676;">
                            <th style="padding:10px;">Instancia</th>
                            <th style="padding:10px;">Puntos</th>
                        </tr>
                        <tr><td style="padding:8px;">🥇 Campeón</td><td style="font-weight:bold;">100</td></tr>
                        <tr><td style="padding:8px;">🥈 Subcampeón</td><td style="font-weight:bold;">70</td></tr>
                        <tr><td style="padding:8px;">🥉 Semifinal</td><td style="font-weight:bold;">40</td></tr>
                    </table>
                    """, unsafe_allow_html=True)
                else:
                    st.info("🚫 Torneo No Puntuable")

            # 2. INSCRIPTOS
            with tab_inscriptos:
                st.markdown("<div class='zona-header'>LISTA DE INSCRIPTOS</div>", unsafe_allow_html=True)
                
                # Lógica unificada de visualización
                # Admin ve todo, usuarios ven solo validados
                query_insc = "SELECT * FROM inscripciones WHERE torneo_id = :torneo_id"
                if not st.session_state.get('es_admin', False):
                    query_insc += " AND estado_validacion = 'Validado'"
                query_insc += " ORDER BY id"
                
                df_insc = cargar_datos(query_insc, params={"torneo_id": torneo_id})
                
                if df_insc is None or df_insc.empty:
                    st.info("Aún no hay parejas inscriptas en este torneo.")
                else:
                    for _, row in df_insc.iterrows():
                        # Validar nombres vacíos
                        j1_raw = row['jugador1'] if row['jugador1'] else ""
                        j2_raw = row['jugador2'] if row['jugador2'] else ""
                        
                        # Limpieza de UI: Mostrar error en rojo si está vacío
                        j1_disp = j1_raw if j1_raw.strip() else "<span style='color:red'>⚠️ Error de registro</span>"
                        j2_disp = j2_raw if j2_raw.strip() else "<span style='color:red'>⚠️ Error de registro</span>"
                        
                        with st.container():
                            col_layout = [4, 2, 2, 1] if st.session_state.get('es_admin', False) else [5, 3]
                            cols = st.columns(col_layout)
                            
                            with cols[0]:
                                st.markdown(f"**{j1_disp} - {j2_disp}**")
                                st.caption(f"📞 {row['telefono1']} / {row['telefono2']}")
                            
                            with cols[1]:
                                st.write(row['localidad'])

                            if st.session_state.get('es_admin', False):
                                # Controles de Admin
                                with cols[2]:
                                    estado_pago = row['estado_pago'] if row['estado_pago'] else ('Pagado' if row['pago_confirmado'] else 'Pendiente')
                                    new_status = st.selectbox(
                                        "Pago", 
                                        ["Pendiente", "Señado", "Pagado"], 
                                        key=f"pay_{row['id']}", 
                                        index=["Pendiente", "Señado", "Pagado"].index(estado_pago),
                                        label_visibility="collapsed"
                                    )
                                    if new_status != estado_pago:
                                        run_action("UPDATE inscripciones SET estado_pago = %(st)s, pago_confirmado = %(pc)s WHERE id = %(id)s", {"st": new_status, "pc": 1 if new_status in ['Señado', 'Pagado'] else 0, "id": row['id']})
                                        limpiar_cache()
                                        st.rerun()
                                    
                                    # Validación Status
                                    est_val = row['estado_validacion'] if 'estado_validacion' in row and row['estado_validacion'] else 'Pendiente'
                                    new_val = st.selectbox("Validación", ["Pendiente", "Validado", "Rechazado"], key=f"val_{row['id']}", index=["Pendiente", "Validado", "Rechazado"].index(est_val), label_visibility="collapsed")
                                    if new_val != est_val:
                                        run_action("UPDATE inscripciones SET estado_validacion = %(val)s WHERE id = %(id)s", {"val": new_val, "id": row['id']})
                                        # Forzar limpieza explícita de caché global
                                        st.cache_data.clear()
                                        st.toast(f"✅ Estado actualizado a: {new_val}", icon="🔄")
                                        st.rerun()
                            
                                with cols[3]:
                                    if st.button("🗑️", key=f"del_insc_{row['id']}", help="Eliminar Inscripción"):
                                        run_action("DELETE FROM inscripciones WHERE id = %(id)s", {"id": row['id']})
                                        st.warning(f"Inscripción eliminada.")
                                        limpiar_cache()
                                        st.rerun()
                            st.divider()

            # 3. CLASIFICACIÓN (ZONAS)
            with tab_clasificacion:
                st.markdown("<div class='zona-header'>FASE DE GRUPOS</div>", unsafe_allow_html=True)
                
                df_zonas = cargar_datos("SELECT * FROM zonas_posiciones WHERE torneo_id = :torneo_id ORDER BY nombre_zona, pts DESC, ds DESC, dg DESC, pg DESC", params={"torneo_id": torneo_id})
                
                if df_zonas is None or df_zonas.empty:
                    st.warning("Aún no se han sorteado las zonas.")
                else:
                    # CSS compacto
                    st.markdown("<style>.pc-zone-container{background-color:#050505;border:1px solid #1A1A1A;border-top:3px solid #39FF14;border-radius:12px;padding:15px;margin-bottom:30px}.pc-zone-title{color:#39FF14;font-size:1.1rem;font-weight:800;text-transform:uppercase;margin-bottom:10px;border-bottom:1px solid #333;padding-bottom:5px}.pc-table{width:100%;border-collapse:collapse;font-size:0.8rem;color:#EEE}.pc-table th{color:#AAA;text-align:center;padding:6px 2px;border-bottom:1px solid #333}.pc-table td{text-align:center;padding:8px 2px;border-bottom:1px solid #111}.pc-table .col-left{text-align:left;width:45%;padding-left:5px}.pc-table .col-pts{color:#39FF14;font-weight:900}.pc-row-qualified{background-color:rgba(57,255,20,0.05)!important}.pc-couple-name{font-weight:700;color:#FFF}</style>", unsafe_allow_html=True)

                    for nombre_zona, df_grupo in df_zonas.groupby('nombre_zona'):
                        z_html = f"<div class='pc-zone-container'><div class='pc-zone-title'>🏆 {nombre_zona}</div>"
                        z_html += '<table class="pc-table"><thead><tr><th class="col-left">PAREJA</th><th>PJ</th><th>PG</th><th>PP</th><th>SF</th><th>SC</th><th>DF</th><th>PTS</th></tr></thead><tbody>'
                        
                        for r_idx, row in enumerate(df_grupo.itertuples()):
                            r_cl = "pc-row-qualified" if r_idx < 2 else ""
                            bdg = "<span style='color:#39FF14;'>✅</span>" if r_idx < 2 else ""
                            
                            # Todo en una sola línea de concatenación
                            z_html += f'<tr class="{r_cl}"><td class="col-left"><span class="pc-couple-name">{row.pareja} {bdg}</span></td><td>{row.pj}</td><td>{row.pg}</td><td>{row.pp}</td><td>{row.sf}</td><td>{row.sc}</td><td>{row.dg}</td><td class="col-pts">{row.pts}</td></tr>'
                        
                        z_html += '</tbody></table></div>'
                        
                        # --- OPCIÓN NUCLEAR CONTRA LOS ESPACIOS ---
                        # Esto aplasta todo el string, quitando cualquier enter o tabulación rebelde
                        html_aplastado = " ".join(z_html.split())
                        
                        st.markdown(html_aplastado, unsafe_allow_html=True)

            # 4. FIXTURE (Partidos de Zona)
            with tab_fixture:
                st.markdown("<div class='zona-header'>PARTIDOS PROGRAMADOS</div>", unsafe_allow_html=True)

                # Cronograma Visual
                st.subheader("🗓️ Cronograma Visual")
                fig_timeline = generar_grafico_timeline(torneo_id)
                if fig_timeline:
                    st.plotly_chart(fig_timeline, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.info("Horarios disponibles próximamente")
                
                st.markdown("---")
                st.subheader("📋 Listado de Partidos")
                # Mostramos todos los partidos del torneo ordenados por horario
                df_fix = cargar_datos("SELECT * FROM partidos WHERE torneo_id = :torneo_id ORDER BY horario", params={"torneo_id": torneo_id})
                
                if df_fix is None or df_fix.empty:
                    st.info("No hay partidos programados para este torneo.")
                else:
                    st.dataframe(
                        df_fix[['horario', 'cancha', 'instancia', 'pareja1', 'pareja2', 'resultado', 'estado_partido']],
                        column_config={
                            "horario": "Horario",
                            "cancha": "Cancha",
                            "instancia": "Instancia",
                            "pareja1": "Pareja 1",
                            "pareja2": "Pareja 2",
                            "resultado": "Resultado",
                            "estado_partido": "Estado"
                        },
                        hide_index=True,
                        use_container_width=True
                    )

            # 5. LLAVES (Bracket)
            with tab_llaves:
                st.markdown("<div class='zona-header'>CUADRO FINAL</div>", unsafe_allow_html=True)
                mostrar_cuadro_playoff(torneo_id)
