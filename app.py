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
from streamlit_extras.metric_cards import style_metric_cards
import time
import requests
from streamlit_lottie import st_lottie
import plotly.express as px
import numpy as np

import sqlite3

from sqlalchemy.exc import OperationalError
from sqlalchemy import text
import contextlib

# --- IMPORTAR UTILIDADES CENTRALES ---
from utils import get_data, cargar_datos, run_action, init_db, limpiar_cache, normalize_params
from simulador import mostrar_simulador
from views.jugadores import mostrar_jugadores

# Configuración de página con estética Rincón Padel
# Configuración optimizada: Carga diferida de assets
page_icon = "assets/logo_rincon.png" if os.path.exists("assets/logo_rincon.png") else "🎾"

st.set_page_config(
    page_title="Rincón Padel - Torneos", 
    layout="wide", 
    page_icon=page_icon,
    initial_sidebar_state="expanded"
)

@st.cache_data
def load_local_image(path):
    """Carga imágenes locales con caché para evitar I/O repetitivo."""
    if os.path.exists(path):
        return Image.open(path)
    return None

logo = load_local_image("assets/logo_rincon.png")

# --- GESTIÓN DE TEMA (CLARO / OSCURO) ---
# Inicializar estado del tema si no existe (False = Oscuro por defecto)
if 'theme' not in st.session_state:
    st.session_state['theme'] = False

# Inicializar variables del formulario de inscripción para evitar AttributeError
keys_formulario = ['f_nombre_j1', 'f_nombre_j2', 'f_dni_j1', 'f_dni_j2', 'f_tel_j1', 'f_tel_j2', 'f_localidad']
for k in keys_formulario:
    if k not in st.session_state:
        st.session_state[k] = ""

# Inicializar selector de torneos para evitar AttributeError en callbacks
if "id_torneo_selector" not in st.session_state:
    st.session_state["id_torneo_selector"] = None

# Toggle en Sidebar (Lo colocamos al principio para que cargue antes que el resto)
with st.sidebar:
    is_light_mode = st.toggle('☀️ Modo Claro / 🌙 Modo Oscuro', value=st.session_state['theme'], key='theme')

# --- DEFINICIÓN DE ESTILOS CSS ---

css_dark_neon = """
    <style>
        /* Fondo General */
        .stApp {
            background-color: #0A0A0A !important;
            color: #FFFFFF !important;
        }

        /* Títulos (h1, h2, h3) */
        h1, h2, h3 {
            color: #00FF00 !important;
            font-family: 'Segoe UI', sans-serif !important;
        }
        h1 {
            text-shadow: 0 0 10px rgba(0, 255, 0, 0.5) !important;
        }

        /* Contenedores de Streamlit */
        div.stContainer, .dashboard-card, .card, .admin-card, .player-card, .h2h-card, .ranking-card, .match-card, div[data-testid="stForm"] {
            background-color: #1A1A1A !important;
            border: 1px solid #333 !important;
            border-radius: 10px !important;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3) !important;
        }

        /* Imágenes */
        img {
            border-radius: 8px !important;
            transition: transform 0.3s ease, box-shadow 0.3s ease !important;
        }
        img:hover {
            transform: scale(1.03) !important;
            box-shadow: 0 0 15px #00FF00 !important;
        }

        /* Botones (.stButton>button) */
        .stButton > button {
            background-color: #00FF00 !important;
            color: #000000 !important;
            font-weight: bold !important;
            text-transform: uppercase; 
            border: none !important;
            transition: all 0.3s ease !important;
        }
        .stButton > button:hover {
            background-color: #FFFFFF !important;
            color: black !important;
        }

        /* Ajustes adicionales para inputs en modo oscuro */
        .stTextInput input, .stSelectbox div[data-baseweb="select"] > div, .stNumberInput input {
            background-color: #1A1A1A !important; 
            color: white !important; 
            border: 1px solid #333 !important;
        }

        /* Estilos para el menú de navegación (Radio en Sidebar) */
        section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] p {
            color: #00FF41 !important;
            font-weight: 600 !important;
            font-size: 1.05rem !important;
            transition: all 0.3s ease !important;
        }
        section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover p {
            color: #FFFFFF !important;
            text-shadow: 0 0 10px #00FF41 !important;
            transform: translateX(5px);
        }
    </style>
"""

css_light_forest = """
    <style>
        /* Transición Suave General */
        .stApp, section[data-testid="stSidebar"], .stButton button, .stTextInput input, div[data-testid="stExpander"], .dashboard-card, .card {
            transition: all 0.5s ease !important;
        }

        /* Fondo General */
        .stApp {
            background-color: #FFFFFF;
            color: #333333;
        }
        
        /* Animación Degradado Sidebar Light */
        @keyframes gradientSidebarLight {
            0% { background-position: 0% 0%; }
            50% { background-position: 0% 100%; }
            100% { background-position: 0% 0%; }
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            /* Degradado sutil claro */
            background: linear-gradient(180deg, #F8F9FA, #E8F5E9, #F8F9FA);
            background-size: 100% 400%;
            animation: gradientSidebarLight 20s ease infinite;
            
            border-right: 2px solid #2E7D32; /* Verde Bosque Sólido */
            box-shadow: 2px 0 5px rgba(0,0,0,0.1);
        }
        
        /* Inputs */
        .stTextInput input, .stSelectbox div[data-baseweb="select"] > div, .stNumberInput input, .stDateInput input {
            background-color: #FFFFFF !important;
            color: #333333 !important;
            border: 1px solid #2E7D32 !important;
            border-radius: 8px !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05); /* Sombra suave */
        }
        
        /* Headers */
        h1, h2, h3, h4, h5, h6, .rincon-header, .zona-header {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
            text-shadow: none !important;
            color: #2E7D32 !important; /* Verde Bosque */
        }
        
        .rincon-header { 
            background-color: #FFFFFF; 
            color: #2E7D32; 
            border: 2px solid #2E7D32; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            animation: none;
            text-align: center; 
            padding: 20px; 
            border-radius: 10px; 
            text-transform: uppercase; 
            font-weight: 900; 
            font-size: 26px; 
            letter-spacing: 3px;
            margin-bottom: 25px;
        }
        
        .zona-header { 
            background-color: #E8F5E9; /* Verde muy claro */
            color: #1B5E20; 
            border-left: 6px solid #2E7D32; 
            padding: 12px;
            margin-top: 25px; 
            margin-bottom: 15px; 
            font-weight: bold; 
            font-size: 16px; 
            text-transform: uppercase; 
            border-radius: 0px 8px 8px 0px;
        }

        /* Cards */
        .dashboard-card, .card, .admin-card, .player-card, .h2h-card, .ranking-card, .match-card, div[data-testid="stForm"] {
            background-color: #FFFFFF !important;
            border: 1px solid #2E7D32 !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
            color: #333333 !important;
            border-radius: 15px !important;
        }
        
        /* Textos dentro de cards */
        .card-title, .dash-title, .player-name, .team-name {
            color: #2E7D32 !important;
            text-shadow: none !important;
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab"] {
            border: 1px solid #2E7D32 !important;
            color: #333333 !important;
            background-color: #FFFFFF !important;
            border-radius: 5px !important;
        }
        .stTabs [aria-selected="true"] {
            background-color: #2E7D32 !important;
            color: #FFFFFF !important;
            font-weight: bold !important;
        }
        
        /* Botones */
        .stButton button {
            background-color: #2E7D32 !important;
            color: #FFFFFF !important;
            border: none !important;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2) !important; /* Sombra suave */
            animation: none !important;
            border-radius: 10px !important;
        }
        .stButton button:hover {
            background-color: #1B5E20 !important;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3) !important;
        }

        /* Tablas */
        [data-testid="stDataFrame"] {
            background-color: #FFFFFF !important;
            border: 1px solid #ddd !important;
            border-radius: 10px !important;
        }
        th {
            background-color: #E8F5E9 !important;
            color: #1B5E20 !important;
            border-bottom: 2px solid #2E7D32 !important;
        }
        tr:nth-child(even) { background-color: #F1F8E9 !important; }
        tr:nth-child(odd) { background-color: #FFFFFF !important; }
        td { color: #333 !important; border-bottom: 1px solid #ddd !important; }
        
        /* Ajustes de texto general */
        p, label, span, div {
            color: inherit;
        }
        
        /* Estilos para el menú de navegación (Radio en Sidebar) */
        section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] p {
            color: #2E7D32 !important;
            font-weight: 600 !important;
            font-size: 1.05rem !important;
            transition: all 0.3s ease !important;
        }
        section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover p {
            color: #1B5E20 !important;
            transform: translateX(5px);
        }
    </style>
"""

# Inyección Condicional de CSS
if is_light_mode:
    st.markdown(css_light_forest, unsafe_allow_html=True)
else:
    st.markdown(css_dark_neon, unsafe_allow_html=True)

# --- UTILIDADES ---
@contextlib.contextmanager
def custom_spinner():
    with st.spinner("Procesando... 🎾"):
        yield

# Inicializar estado de administrador
if 'es_admin' not in st.session_state:
    st.session_state.es_admin = False

# --- CONFIGURACIÓN DE SEGURIDAD ---
# La configuración de seguridad se maneja mediante st.secrets

# --- HELPER DB ---
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

# --- BASE DE DATOS ---
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
        
        # Compatibilidad automática: Convertir sintaxis %(var)s (psycopg2) a :var (SQLAlchemy)
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
                    
            # 3. LÓGICA DE INVALIDACIÓN AUTOMÁTICA
            # Al detectar una escritura (INSERT/UPDATE), borramos el caché global.
            # Esto garantiza que los usuarios vean el nuevo resultado de inmediato.
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

# --- SISTEMA DE FEED SOCIAL (MOCK TEMPORAL) ---
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
    st.session_state['feed_actividad'].insert(0, nuevo_evento) # Insertar al principio para verlo arriba

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def guardar_inscripcion(torneo_id, j1, j2, loc, cat, pago, tel1, tel2):
    # FIX: Priorizar el ID seleccionado globalmente si existe (Sincronización Admin/Estado)
    if st.session_state.get('id_torneo'):
        torneo_id = st.session_state['id_torneo']
        
    run_action("INSERT INTO inscripciones (torneo_id, jugador1, jugador2, localidad, categoria, pago_confirmado, telefono1, telefono2) VALUES (%(torneo_id)s, %(jugador1)s, %(jugador2)s, %(localidad)s, %(categoria)s, %(pago_confirmado)s, %(telefono1)s, %(telefono2)s)", 
              {"torneo_id": torneo_id, "jugador1": j1, "jugador2": j2, "localidad": loc, "categoria": cat, "pago_confirmado": 1 if pago else 0, "telefono1": tel1, "telefono2": tel2})
    limpiar_cache()

def eliminar_pareja_torneo(pareja_id, torneo_id):
    """Da de baja y elimina una pareja inscrita de un torneo en particular."""
    if not st.session_state.get('es_admin', False): return
    # Ejecutamos el DELETE directamente sobre la tabla inscripciones
    run_action("DELETE FROM inscripciones WHERE id = %(id)s AND torneo_id = %(torneo_id)s", 
              {"id": pareja_id, "torneo_id": torneo_id})
    limpiar_cache()

def crear_torneo(nombre, fecha, categoria, es_puntuable=True, super_tiebreak=False, puntos_tiebreak=10):
    if not st.session_state.get('es_admin', False): return None
    # Usamos RETURNING id para obtener el ID generado en Postgres
    new_id = run_action("INSERT INTO torneos (nombre, fecha, categoria, estado, es_puntuable, super_tiebreak, puntos_tiebreak) VALUES (%(nombre)s, %(fecha)s, %(categoria)s, 'Abierto', %(es_puntuable)s, %(super_tiebreak)s, %(puntos_tiebreak)s) RETURNING id", 
              {"nombre": nombre, "fecha": str(fecha), "categoria": categoria, "es_puntuable": 1 if es_puntuable else 0, "super_tiebreak": 1 if super_tiebreak else 0, "puntos_tiebreak": puntos_tiebreak}, return_id=True)
    limpiar_cache()
    return new_id

def iniciar_torneo(torneo_id):
    if not st.session_state.get('es_admin', False):
        return
    run_action("UPDATE torneos SET estado = 'En Juego' WHERE id = %(id)s", {"id": torneo_id})
    limpiar_cache()

def detener_partido(partido_id):
    if not st.session_state.get('es_admin', False):
        return
    run_action("UPDATE partidos SET estado_partido = 'Detenido' WHERE id = %(id)s", {"id": partido_id})
    limpiar_cache()


@st.cache_data(ttl=600)
def get_data(query, params=None):
    # Utilizamos cargar_datos que ya implementa la lógica robusta, pero mantenemos el caché de Streamlit aquí
    return cargar_datos(query, params)

def cargar_datos(query, params=None):
    """
    Ejecuta consultas SQL de forma eficiente usando st.connection.
    Maneja el pool de conexiones y reintenta si el servidor está saturado.
    """
    params = normalize_params(params)
    
    # Compatibilidad automática: Convertir sintaxis %(var)s (PostgreSQL) a :var (SQLAlchemy)
    if params and isinstance(params, dict) and '%(' in query:
        query = re.sub(r'%\((\w+)\)s', r':\1', query)
    
    try:
        conn = get_db_connection()
        return conn.query(query, params=params, ttl=0)
        
    except Exception as e:
        error_msg = str(e)        
        
        # Manejo de saturación (Max Clients)
        if "MaxClientsInSessionMode" in error_msg or "too many clients" in error_msg.lower():
            st.warning("⚠️ Servidor saturado. Limpiando conexiones y reintentando...")
            
            # Limpia el recurso de conexión para forzar una nueva y pausa corta
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
    import streamlit as st
    
    inscritos = obtener_inscritos_publicos(torneo_id)
    
    st.markdown("<h3 style='color: #00FF00; text-shadow: 0 0 10px rgba(0, 255, 0, 0.3); margin-bottom: 15px;'>👥 Parejas Inscritas</h3>", unsafe_allow_html=True)
    
    # Verificamos correctamente el DataFrame de Pandas
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
            delay = idx * 0.05 # Retraso de 0.05s por cada fila
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
    """Asigna horarios automáticamente a los partidos de zona dentro de rangos definidos."""
    if not st.session_state.get('es_admin', False):
        return False, "Acceso denegado. Debes ser administrador."

    # 1. Obtener partidos de zona para programar
    df_partidos = cargar_datos("SELECT id FROM partidos WHERE torneo_id = :torneo_id AND instancia = 'Zona' ORDER BY id ASC", {"torneo_id": torneo_id})
    partidos_a_programar = df_partidos['id'].tolist()
    num_partidos = len(partidos_a_programar)
    
    if num_partidos == 0:
        return False, "No hay partidos de zona generados para este torneo."

    # 2. Calcular slots de tiempo disponibles
    duracion_partido = timedelta(hours=1, minutes=15)
    slots_disponibles = []
    
    for dia in programacion_dias:
        fecha = dia['fecha']
        hora_inicio = dia['inicio']
        hora_fin = dia['fin']
        
        # Combinar fecha y hora para crear objetos datetime
        inicio_dt = datetime.combine(fecha, hora_inicio)
        fin_dt = datetime.combine(fecha, hora_fin)
        
        # Generar slots dentro del rango del día
        tiempo_actual = inicio_dt
        while tiempo_actual + duracion_partido <= fin_dt:
            slots_disponibles.append(tiempo_actual)
            tiempo_actual += duracion_partido

    # 3. Validar capacidad: ¿caben todos los partidos en los slots disponibles?
    if num_partidos > len(slots_disponibles):
        mensaje_alerta = f"⚠️ ¡Alerta de capacidad! Se necesitan {num_partidos} slots, pero solo hay {len(slots_disponibles)} disponibles en los rangos horarios definidos. Amplía los horarios o reduce el número de partidos."
        return False, mensaje_alerta

    # 4. Asignar horarios a los partidos
    # Limpiar horarios previos para este torneo y zona, para evitar conflictos si se regenera
    run_action("UPDATE partidos SET horario = NULL, cancha = NULL WHERE torneo_id = %(torneo_id)s AND instancia = 'Zona'", {"torneo_id": torneo_id})

    for idx, partido_id in enumerate(partidos_a_programar):
        horario_asignado = slots_disponibles[idx]
        horario_str = horario_asignado.strftime("%Y-%m-%d %H:%M")
        run_action("UPDATE partidos SET horario = %(horario)s, cancha = 'Cancha Central', estado_partido = 'Próximo' WHERE id = %(id)s", {"horario": horario_str, "id": int(partido_id)})
    
    limpiar_cache()
    return True, f"✅ Se programaron exitosamente {num_partidos} partidos en la Cancha Central."

import random
import streamlit as st

def generar_zonas(torneo_id, categoria, pref_tamano=4):
    # 1. Seguridad y Validación
    if not st.session_state.get('es_admin', False): 
        return False, "Acceso denegado"
    
    try:
        torneo_id = int(torneo_id)
    except:
        return False, "ID de torneo inválido"

    # 2. Obtener inscriptos VALIDADOS (El filtro clave)
    query_insc = """
        SELECT jugador1, jugador2 FROM inscripciones 
        WHERE torneo_id = :t_id AND categoria = :cat AND estado_validacion = 'Validado'
    """
    df_insc = cargar_datos(query_insc, {"t_id": torneo_id, "cat": categoria})
    
    if df_insc is None or df_insc.empty:
        return False, f"No hay parejas validadas para {categoria} en el Torneo {torneo_id}."

    parejas = [f"{row['jugador1']} - {row['jugador2']}" for _, row in df_insc.iterrows()]
    n = len(parejas)
    if n < 3:
        return False, f"Mínimo 3 parejas (hay {n})."

    import random
    random.shuffle(parejas)
    
    # 3. Lógica de grupos (Matemática de zonas)
    # Si prefiere 4: Iteramos desde el máximo posible de grupos de 4 hacia abajo (Maximizar 4s)
    # Si prefiere 3: Iteramos desde 0 grupos de 4 hacia arriba (Minimizar 4s -> Maximizar 3s)
    q4, q3, found = 0, 0, False
    
    # Definir rango de iteración para grupos de 4
    if pref_tamano == 4:
        range_q4 = range(n // 4, -1, -1) # Descendente
    else:
        range_q4 = range(0, (n // 4) + 1) # Ascendente
        
    for i in range_q4:
        rem = n - (i * 4)
        if rem % 3 == 0:
            q4, q3, found = i, rem // 3, True
            break
            
    if not found: return False, "La cantidad de parejas no cierra para grupos de 3 y 4."

    # 4. LIMPIEZA QUIRÚRGICA (Protege otras categorías)
    # Solo borramos lo que pertenece a ESTA categoría y este torneo
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

    # 5. Generación de Zonas y Cruces
    idx, letras, zona_counter = 0, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", 0
    
    def procesar_grupo(tamano):
        nonlocal idx, zona_counter
        nombre_z = f"Zona {letras[zona_counter]}"
        grupo = parejas[idx:idx+tamano]
        
        for p in grupo:
            # Insertamos usando diccionarios para los parámetros (Fix del error de conexión)
            run_action("""
                INSERT INTO zonas (torneo_id, nombre_zona, pareja) 
                VALUES (:t_id, :nz, :pj)
            """, {"t_id": torneo_id, "nz": nombre_z, "pj": p})
            
            run_action("""
                INSERT INTO zonas_posiciones (torneo_id, nombre_zona, pareja) 
                VALUES (:t_id, :nz, :pj)
            """, {"t_id": torneo_id, "nz": nombre_z, "pj": p})
        
        # Generar Cruces "Todos contra Todos"
        cruces = [(0,3), (1,2)] if tamano == 4 else [(0,1), (0,2), (1,2)]
        for i1, i2 in cruces:
            run_action("""
                INSERT INTO partidos (torneo_id, pareja1, pareja2, instancia, estado_partido) 
                VALUES (:t_id, :p1, :p2, 'Zona', 'Próximo')
            """, {"t_id": torneo_id, "p1": grupo[i1], "p2": grupo[i2]})
            
        idx += tamano
        zona_counter += 1

    # Ejecutamos el reparto
    for _ in range(q4):
        procesar_grupo(4)
    for _ in range(q3):
        procesar_grupo(3)
        
    st.cache_data.clear()
    return True, f"✅ Éxito: Se crearon {zona_counter} zonas para {categoria}."

def generar_partidos_desde_zonas_existentes(torneo_id):
    """
    Genera el fixture de partidos basándose en las zonas ya creadas manualmente 
    en la base de datos.
    """
    if not st.session_state.get('es_admin', False):
        return False, "Acceso denegado"
    
    # 1. Aseguramos el tipo de dato para evitar el error de numpy.int64
    try:
        t_id = int(torneo_id)
    except (ValueError, TypeError):
        return False, "ID de torneo inválido."

    # 2. Limpiar partidos de zona previos (Estandarizamos placeholders a :t_id)
    run_action("DELETE FROM partidos WHERE torneo_id = :t_id AND instancia = 'Zona'", {"t_id": t_id})
    
    # 3. Obtener zonas y parejas
    df_zonas = cargar_datos(
        "SELECT nombre_zona, pareja FROM zonas WHERE torneo_id = :t_id ORDER BY nombre_zona", 
        params={"t_id": t_id}
    )
    
    # Verificación de seguridad
    if df_zonas is None or df_zonas.empty:
        return False, "No se encontraron zonas definidas para este torneo."
        
    grupos = df_zonas.groupby('nombre_zona')
    
    count_partidos = 0
    
    # 4. Generación de cruces Round-Robin (Todos contra todos por zona)
    for nombre_z, df_grupo in grupos:
        parejas = df_grupo['pareja'].tolist()
        n = len(parejas)
        
        cruces = []
        if n == 3:
            cruces = [(0,1), (0,2), (1,2)]
        elif n == 4:
            cruces = [(0,3), (1,2)]
        elif n == 5:
            # Round-robin completo para 5 (10 partidos)
            cruces = [(0,1), (0,2), (0,3), (0,4), (1,2), (1,3), (1,4), (2,3), (2,4), (3,4)]
        
        # 

        for i1, i2 in cruces:
            # Verificación de índice para evitar errores si la zona tiene un tamaño inesperado
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

def generar_partidos_definicion(torneo_id):
    if not st.session_state.get('es_admin', False): 
        return False, "Acceso denegado"
        
    try:
        t_id = int(torneo_id)
    except:
        return False, "ID de torneo inválido"

    df_zonas = cargar_datos("SELECT nombre_zona, pareja FROM zonas WHERE torneo_id = :t_id ORDER BY nombre_zona", {"t_id": t_id})
    if df_zonas is None or df_zonas.empty:
        return False, "No hay zonas definidas en este torneo."
        
    df_partidos = cargar_datos("SELECT id, pareja1, pareja2, ganador, estado_partido FROM partidos WHERE torneo_id = :t_id AND instancia = 'Zona' ORDER BY id ASC", {"t_id": t_id})
    
    count_nuevos = 0
    zonas_dict = {}
    for _, row in df_zonas.iterrows():
        z = row['nombre_zona']
        if z not in zonas_dict: zonas_dict[z] = []
        zonas_dict[z].append(row['pareja'])
        
    for z_name, parejas in zonas_dict.items():
        if len(parejas) == 4:
            partidos_zona = []
            if df_partidos is not None and not df_partidos.empty:
                for _, p in df_partidos.iterrows():
                    if p['pareja1'] in parejas and p['pareja2'] in parejas:
                        partidos_zona.append(p)
            
            if len(partidos_zona) == 2:
                if all(p['estado_partido'] == 'Finalizado' for p in partidos_zona):
                    ganador_c1 = partidos_zona[0]['ganador']
                    ganador_c2 = partidos_zona[1]['ganador']
                    perdedor_c1 = partidos_zona[0]['pareja2'] if ganador_c1 == partidos_zona[0]['pareja1'] else partidos_zona[0]['pareja1']
                    perdedor_c2 = partidos_zona[1]['pareja2'] if ganador_c2 == partidos_zona[1]['pareja1'] else partidos_zona[1]['pareja1']
                    
                    if ganador_c1 and ganador_c2 and perdedor_c1 and perdedor_c2:
                        run_action("INSERT INTO partidos (torneo_id, pareja1, pareja2, instancia, estado_partido) VALUES (:t_id, :p1, :p2, 'Zona', 'Próximo')", {"t_id": t_id, "p1": ganador_c1, "p2": ganador_c2})
                        run_action("INSERT INTO partidos (torneo_id, pareja1, pareja2, instancia, estado_partido) VALUES (:t_id, :p1, :p2, 'Zona', 'Próximo')", {"t_id": t_id, "p1": perdedor_c1, "p2": perdedor_c2})
                        count_nuevos += 2
                else:
                    return False, f"La {z_name} aún tiene partidos iniciales sin finalizar."
                 
    limpiar_cache()
    if count_nuevos > 0:
        return True, f"Se generaron {count_nuevos} partidos de definición."
    else:
        return False, "No se generaron partidos (asegúrate de que los iniciales estén finalizados y no se hayan generado ya)."


# ==========================================
# NUEVA FUNCIÓN: ARMADO MANUAL DE PLAYOFFS
# ==========================================
def interfaz_armado_manual_cuadro(torneo_id):
    """
    Genera una interfaz visual en Streamlit para armar los cruces a dedo.
    Debes llamar a esta función dentro de la pestaña/sección de administración de tu torneo.
    """
    t_id = int(torneo_id)
    
    # 1. Verificar si ya existen playoffs
    df_check = cargar_datos("SELECT count(*) as c FROM partidos WHERE torneo_id = :t_id AND instancia IN ('Octavos', 'Cuartos', 'Semis', 'Final')", {"t_id": t_id})
    if df_check is not None and not df_check.empty and df_check.iloc[0]['c'] > 0:
        st.warning("Ya se han generado cruces de playoff para este torneo. Elimínalos si deseas armar un nuevo cuadro manual.")
        return

    # 2. Obtener lista de parejas (ordenadas por puntos para facilitar la vista)
    df_pos = cargar_datos("""
        SELECT nombre_zona, pareja, pts 
        FROM zonas_posiciones 
        WHERE torneo_id = :t_id 
        ORDER BY nombre_zona ASC, pts DESC
    """, {"t_id": t_id})
    
    if df_pos is None or df_pos.empty:
        st.info("No hay parejas registradas o tabla de posiciones generada.")
        return

    # Crear lista de opciones para los selectbox (Agregamos la opción Vacío/BYE)
    # Formateamos el nombre para que el admin sepa de qué zona vienen
    lista_opciones = ["Vacío / BYE"] + [f"{row['pareja']} ({row['nombre_zona']} - {row['pts']}pts)" for _, row in df_pos.iterrows()]
    num_parejas_reales = len(df_pos)

    # 3. Calcular tamaño del cuadro
    target_size = 4
    instancia = "Semis"
    start_pos = 13
    if num_parejas_reales > 4:
        target_size = 8
        instancia = "Cuartos"
        start_pos = 9
    if num_parejas_reales > 8:
        target_size = 16
        instancia = "Octavos"
        start_pos = 1

    st.subheader(f"Armado Manual del Cuadro ({instancia} - {target_size} lugares)")
    st.write("Selecciona qué pareja juega en cada llave. Las posiciones están en el orden del bracket visual (Top a Bottom).")

    cantidad_partidos = target_size // 2
    
    # 4. Generar UI con columnas
    cruces_seleccionados = []
    
    # Usamos 2 columnas para no hacer la pantalla interminable hacia abajo
    cols = st.columns(2) 
    for i in range(cantidad_partidos):
        with cols[i % 2]:
            st.markdown(f"**Partido {i+1} (Posición Bracket: {start_pos + i})**")
            p1_val = st.selectbox(f"Pareja 1", options=lista_opciones, key=f"manual_p1_{i}")
            p2_val = st.selectbox(f"Pareja 2", options=lista_opciones, key=f"manual_p2_{i}")
            cruces_seleccionados.append((p1_val, p2_val))
            st.markdown("---")

    # 5. Botón para guardar
    if st.button("Guardar Cuadro Manualmente", type="primary"):
        count = 0
        for i, (sel1, sel2) in enumerate(cruces_seleccionados):
            # Limpiamos el texto para guardar solo el nombre de la pareja (quitamos zona y pts)
            real_p1 = "BYE" if sel1 == "Vacío / BYE" else sel1.split(" (")[0]
            real_p2 = "BYE" if sel2 == "Vacío / BYE" else sel2.split(" (")[0]
            
            estado = 'Próximo'
            res = ''
            ganador = None
            
            # Si ambos son BYE, no creamos partido
            if real_p1 == "BYE" and real_p2 == "BYE":
                continue 
                
            # Logica si uno es BYE (El otro pasa directo)
            if real_p1 == "BYE":
                estado = 'Finalizado'
                ganador = real_p2
                res = 'BYE'
            elif real_p2 == "BYE":
                estado = 'Finalizado'
                ganador = real_p1
                res = 'BYE'

            # Insertamos el partido
            bp = start_pos + i
            run_action("""
                INSERT INTO partidos (torneo_id, pareja1, pareja2, instancia, estado_partido, bracket_pos)
                VALUES (:tid, :p1, :p2, :inst, :est, :bp)
            """, {"tid": t_id, "p1": real_p1, "p2": real_p2, "inst": instancia, "est": 'Próximo' if not ganador else 'Finalizado', "bp": bp})
            
            # Si hubo un BYE, actualizamos directo
            if ganador:
                run_action("UPDATE partidos SET estado_partido = 'Finalizado', resultado = 'Pasa Directo', ganador = :g WHERE torneo_id = :tid AND bracket_pos = :bp",
                           {"g": ganador, "tid": t_id, "bp": bp})
                # Llamada a tu funcion de actualizar bracket
                try:
                    actualizar_bracket(None, t_id, bp, res, ganador)
                except Exception as e:
                    pass # Evitamos que falle si actualizar_bracket necesita un ID específico de partido
            
            count += 1
            
        limpiar_cache()
        st.success(f"✅ Se guardaron {count} partidos de {instancia} correctamente.")
        st.rerun()


# ==========================================
# GENERACIÓN AUTOMÁTICA ORIGINAL (CORREGIDA)
# ==========================================
def cerrar_zonas_y_generar_playoffs(torneo_id, manual_positions=None):
    """
    Cierra la fase de zonas, selecciona los 2 mejores de cada una y genera el bracket de playoffs de forma automática.
    """
    if not st.session_state.get('es_admin', False):
        return False, "Acceso denegado"
    
    t_id = int(torneo_id)
    
    # 1. Verificar si ya existen playoffs
    df_check = cargar_datos("SELECT count(*) as c FROM partidos WHERE torneo_id = :t_id AND instancia IN ('Octavos', 'Cuartos', 'Semis', 'Final')", {"t_id": t_id})
    if df_check is not None and not df_check.empty and df_check.iloc[0]['c'] > 0:
        return False, "Ya se han generado cruces de playoff para este torneo."

    # 2. Obtener Tabla General Ordenada
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
        z_letra = z.replace("Zona ", "").strip()
        
        if manual_positions and z in manual_positions:
            seleccionados = manual_positions[z]
            p1, p2, p3 = seleccionados
            
            def find_row(name):
                for e in equipos:
                    if e['pareja'] == name: return e
                return {"pareja": name, "pts": 0, "ds": 0, "dg": 0, "pg": 0}
            
            equipos_sorted = []
            if p1 and p1 != "(Ninguno)": equipos_sorted.append(find_row(p1))
            if p2 and p2 != "(Ninguno)": equipos_sorted.append(find_row(p2))
            if p3 and p3 != "(Ninguno)": equipos_sorted.append(find_row(p3))
            
            tamano_zona = len(equipos)
        else:
            equipos_sorted = sorted(equipos, key=lambda x: (x['pts'], x['ds'], x['dg']), reverse=True)
            tamano_zona = len(equipos_sorted)
            
        if len(equipos_sorted) >= 1:
            clasificados.append( (f"1{z_letra} - {equipos_sorted[0]['pareja']}", 1, equipos_sorted[0]) )
        if len(equipos_sorted) >= 2:
            clasificados.append( (f"2{z_letra} - {equipos_sorted[1]['pareja']}", 2, equipos_sorted[1]) )
        
        if len(equipos_sorted) >= 3:
            if tamano_zona == 4:
                clasificados.append( (f"3{z_letra} - {equipos_sorted[2]['pareja']}", 3, equipos_sorted[2]) )
            else:
                terceros.append( (f"3{z_letra} - {equipos_sorted[2]['pareja']}", 3, equipos_sorted[2]) )

    num_clasificados_base = len(clasificados)
    
    target_size = 4
    if num_clasificados_base > 4:
        target_size = 8
    if num_clasificados_base > 8:
        target_size = 16
    if num_clasificados_base > 16:
        target_size = 32
    
    slots_needed = target_size - num_clasificados_base
    
    terceros.sort(key=lambda x: (x[2]['pts'], x[2]['ds'], x[2]['dg']), reverse=True)
    
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
        if pareja == "BYE":
            return (-1, -1, -1, -1) 
        priority_group = 4 - pos_zona
        return (priority_group, stats['pts'], stats['ds'], stats['dg'])

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

    count = 0
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
    """Muestra un dashboard con estadísticas clave del torneo seleccionado."""
    st.markdown("### 📊 Estadísticas del Torneo")
    
    # 1. Total Participantes
    df_insc = cargar_datos("SELECT jugador1, jugador2, localidad, categoria FROM inscripciones WHERE torneo_id = :tid", {"tid": int(torneo_id)})
    total_parejas = len(df_insc) if df_insc is not None and not df_insc.empty else 0
    
    # 2. Total Partidos Jugados (Finalizados)
    df_matches = cargar_datos("SELECT resultado FROM partidos WHERE torneo_id = :tid AND estado_partido = 'Finalizado'", {"tid": int(torneo_id)})
    total_jugados = len(df_matches) if df_matches is not None else 0
    
    # 3. Desglose Sets (2 vs 3)
    sets_2 = 0
    sets_3 = 0
    if df_matches is not None and not df_matches.empty:
        for res in df_matches['resultado']:
            if not res: continue
            # Heurística: contar bloques separados por espacio que contengan guión (ej: "6-4 6-4" = 2 sets)
            parts = [p for p in res.split(' ') if '-' in p]
            if len(parts) == 2: sets_2 += 1
            elif len(parts) >= 3: sets_3 += 1
            
    # Renderizado Metric
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
    """Visualiza los cruces de playoff con Bracket HTML (Inyectado)."""
    df = cargar_datos("SELECT * FROM partidos WHERE torneo_id = :tid AND bracket_pos IS NOT NULL ORDER BY bracket_pos", {"tid": int(torneo_id)})
    
    if df is None or df.empty:
        return

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
                    try:
                        res.append(str(val).split('-')[s_idx])
                    except:
                        pass
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

    # Detectar rondas disponibles para evitar columnas vacías
    has_oct = any(k in matches for k in range(1, 9))
    has_4tos = any(k in matches for k in range(9, 13))
    has_semis = any(k in matches for k in range(13, 15))

    rounds_html = ""
    if has_oct:
        rounds_html += f'<div class="round"><div class="round-title">Octavos</div>{"".join([get_match_html(i) for i in range(1, 9)])}</div>'
    if has_4tos or has_oct:
        rounds_html += f'<div class="round"><div class="round-title">Cuartos</div>{"".join([get_match_html(i) for i in range(9, 13)])}</div>'
    if has_semis or has_4tos:
        rounds_html += f'<div class="round"><div class="round-title">Semis</div>{"".join([get_match_html(i) for i in range(13, 15)])}</div>'
    
    # Final y Campeón siempre visibles
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

def dibujar_bracket_fase_final(torneo_id):
    query = """
        SELECT id, instancia, pareja1, pareja2, ganador, resultado 
        FROM partidos 
        WHERE torneo_id = %(torneo_id)s AND instancia IN ('Semis', 'Final')
        ORDER BY id ASC
    """
    df_partidos = cargar_datos(query, {"torneo_id": torneo_id})
    
    if df_partidos is None or df_partidos.empty:
        st.info("Aún no hay partidos de fase final generados.")
        return

    semis = df_partidos[df_partidos['instancia'] == 'Semis']
    final = df_partidos[df_partidos['instancia'] == 'Final']

    c1, c2, c3 = st.columns([2, 1, 2])

    with c1:
        st.markdown("<h4 style='text-align: center; color: #00FF00;'>Semifinales</h4>", unsafe_allow_html=True)
        if not semis.empty:
            for _, row in semis.iterrows():
                with st.container(border=True):
                    p1 = row['pareja1'] if row['pareja1'] else "TBD"
                    p2 = row['pareja2'] if row['pareja2'] else "TBD"
                    ganador = row['ganador']
                    resultado = row['resultado']
                    st.markdown(f"🔵 **{p1}**")
                    st.markdown(f"🔴 **{p2}**")
                    if resultado:
                        st.caption(f"Marcador: {resultado}")
                    if ganador:
                        st.success(f"✔️ Avanza: {ganador}")
        else:
            st.write("Semis no definidas")

    with c2:
        st.markdown("<br><br><br><div style='text-align: center; font-size: 2rem; color: #39FF14;'>➡️</div><br><br><br><br><br><div style='text-align: center; font-size: 2rem; color: #39FF14;'>➡️</div>", unsafe_allow_html=True)

    with c3:
        st.markdown("<h4 style='text-align: center; color: #FFD700;'>Final</h4>", unsafe_allow_html=True)
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        if not final.empty:
            for _, row in final.iterrows():
                with st.container(border=True):
                    p1 = row['pareja1'] if row['pareja1'] else "TBD"
                    p2 = row['pareja2'] if row['pareja2'] else "TBD"
                    ganador = row['ganador']
                    resultado = row['resultado']
                    st.markdown(f"🔵 **{p1}**")
                    st.markdown(f"🔴 **{p2}**")
                    if resultado:
                        st.caption(f"Marcador: {resultado}")
                    if ganador:
                        st.warning(f"🏆 CAMPEÓN: {ganador}")
        else:
            with st.container(border=True):
                st.markdown("Esperando finalistas...")

import random
import streamlit as st

def mostrar_consejo_padel():
    consejos = [
        {"autor": "Ariana Sánchez", "texto": "La magia surge cuando el trabajo táctico se vuelve completamente automático."},
        {"autor": "Paula Josemaría", "texto": "La explosividad no sirve de nada si no sabes leer el espacio libre en la pista."},
        {"autor": "Gemma Triay", "texto": "El dominio aéreo te da el control de la red, pero la paciencia te da el punto."},
        {"autor": "Alejandra Salazar", "texto": "La bandeja no es solo un golpe, es el termómetro que mide tu confianza."},
        {"autor": "Delfi Brea", "texto": "Correr todas las pelotas no es un esfuerzo extra, es un compromiso innegociable."},
        {"autor": "Bea González", "texto": "La juventud te da piernas y velocidad, pero la experiencia te enseña cuándo usarlas."},
        {"autor": "Marta Ortega", "texto": "El control del ritmo del partido es mucho más letal que el remate más fuerte."},
        {"autor": "Tolito Aguirre", "texto": "Si vas a tirar una fantasía, que sea porque ya leíste el miedo en los ojos del rival."},
        {"autor": "Gonzalo Alfonso", "texto": "La potencia de tus piernas es lo que realmente define la agresividad de tu volea."},
        {"autor": "Leo Augsburger", "texto": "Cuando el físico te sobra, el verdadero desafío es aprender a usar los tiempos del partido."},
        {"autor": "Tino Libaak", "texto": "No respetes la historia o el ranking de los que están enfrente, respeta solamente a la pelota."},
        {"autor": "Mike Yanguas", "texto": "Jugar constantemente con las alturas y los ángulos desarma a la defensa más estática."},
        {"autor": "Ramiro Moyano", "texto": "La transición de defensa al ataque tiene que ser un bloque sólido, nunca un movimiento aislado."},
        {"autor": "Javi Leal", "texto": "Pegar fuerte es un recurso. Pegar fuerte y al lugar correcto es un talento."},
        {"autor": "Edu Alonso", "texto": "El pádel moderno premia al jugador que sabe sufrir atrás y acelerar sin dudar adelante."},
        {"autor": "Pincho Fernández", "texto": "Tu mejor golpe siempre será exactamente el que el rival menos espera en ese instante."},
        {"autor": "García Diestro", "texto": "Ser zurdo es una ventaja solamente si sabes cruzar la bola donde realmente duele."},
        {"autor": "Denis Perino", "texto": "Una movilidad extrema te permite estar siempre un segundo antes que la bola."},
        {"autor": "Alex Chozas", "texto": "El atrevimiento premia a los que no tienen ningún miedo de equivocarse en la red."},
        {"autor": "Juan Cruz Belluati", "texto": "Una víbora bien cortada y profunda es el principio del fin para los defensores."},
        {"autor": "Lucas Bergamini", "texto": "No subestimes jamás a un jugador defensivo; ellos te ganan por pura desesperación."},
        {"autor": "Víctor Ruiz", "texto": "Mantener la intensidad los tres sets requiere tanta fortaleza mental como preparación física."},
        {"autor": "Gonzalo Rubio", "texto": "El juego aéreo te impone el respeto, pero el juego raso y firme te da los puntos."},
        {"autor": "Salva Oria", "texto": "La anticipación es el arma silenciosa de los que leen el pádel antes de jugarlo."},
        {"autor": "Marc Quílez", "texto": "Trabaja la volea de bloqueo, es tu único salvavidas cuando el rival acelera a quemarropa."},
        {"autor": "Javi Ruiz", "texto": "La consistencia y no cometer errores no forzados es la llave maestra en los torneos largos."},
        {"autor": "Aranza Osoro", "texto": "La garra significa que el partido no se termina hasta que la última bola toque el piso."},
        {"autor": "Patty Llaguno", "texto": "La colocación milimétrica y la táctica siempre le ganarán a la fuerza descontrolada."},
        {"autor": "Lucía Sainz", "texto": "Un físico bien trabajado es lo único que te mantiene lúcido cuando llegas al tercer set."},
        {"autor": "Virginia Riera", "texto": "El orden táctico es tu armadura para los días en los que los golpes simplemente no entran."},
        {"autor": "Fernando Belasteguín", "texto": "El talento te hace ganar partidos, pero el trabajo duro, el compañero y la inteligencia te hacen ganar torneos."},
        {"autor": "Alejandro Galán", "texto": "La velocidad no es solo física, está en la cabeza. Anticípate a la jugada y dominarás la red."},
        {"autor": "Juan Martín Díaz", "texto": "La creatividad nace cuando dominas la técnica. Entrena los golpes aburridos para luego poder hacer magia."},
        {"autor": "Agustín Tapia", "texto": "Nunca dejes de atreverte. La magia ocurre cuando confías ciegamente en tus instintos y vuelas en la pista."},
        {"autor": "Sanyo Gutiérrez", "texto": "El partido se juega como una partida de ajedrez. Piensa dos tiros por delante de tu rival."},
        {"autor": "Miguel Lamperti", "texto": "Deja el alma en cada punto. La actitud te da ese 10% extra de energía cuando las piernas ya no responden."},
        {"autor": "Franco Stupaczuk", "texto": "El salto y la pegada se entrenan, pero el hambre de ganar se lleva adentro."},
        {"autor": "Maxi Sánchez", "texto": "La solidez desde el fondo de la pista es la base innegociable para construir cualquier victoria."},
        {"autor": "Juan Lebrón", "texto": "La potencia intimida, pero la agresividad constante y la presión asfixian al rival."},
        {"autor": "Pablo Lima", "texto": "El orden táctico, la disciplina y la paciencia son tus mejores aliados en los momentos de presión."},
        {"autor": "Paquito Navarro", "texto": "El pádel es pura pasión. Si no te diviertes sufriendo y peleando cada bola, no estás jugando de verdad."},
        {"autor": "Arturo Coello", "texto": "Aprovecha tu físico y tu pegada, pero nunca olvides que el pádel es, ante todo, un deporte de precisión."},
        {"autor": "Javier Garrido", "texto": "Pegarle duro es fácil, saber exactamente cuándo hacerlo es lo que te hace distinto."},
        {"autor": "Álex Ruiz", "texto": "La cabeza fría para pensar y el corazón caliente para competir. Esa es la fórmula."},
        {"autor": "Xisco Gil", "texto": "El trabajo invisible de todos los días es el que te da los resultados que todos ven los domingos."},
        {"autor": "Roby Gattiker", "texto": "En el pádel los básicos nunca mueren. Una volea firme y un globo profundo siempre serán tus mejores armas."},
        {"autor": "Alejandro Lasaigues", "texto": "La historia del pádel se escribió con muñeca, anticipación y estrategia, no solo con fuerza bruta."},
        {"autor": "Hernán Auguste", "texto": "Entender, respetar y potenciar a tu compañero es el 50% del éxito en este deporte."},
        {"autor": "Gaby Reca", "texto": "La técnica impecable te salva cuando el físico no llega. Pule tus golpes hasta que sean automáticos."},
        {"autor": "Seba Nerone", "texto": "En la pista, el coraje y la personalidad valen tanto como el mejor remate por tres metros."},
        {"autor": "Cristian Gutiérrez", "texto": "La magia sin control no sirve de nada. Dale sentido y dirección a cada toque que hagas."},
        {"autor": "Matías Díaz", "texto": "El instinto guerrero no nace, se hace entrenando cada día como si fuera la final de un mundial."},
        {"autor": "Martín Di Nenno", "texto": "No importa cuántas veces te hagan correr al rincón, la actitud y el sacrificio en defensa ganan los partidos más difíciles."},
        {"autor": "Fede Chingotto", "texto": "No hace falta ser el más alto ni el más fuerte si eres el más inteligente posicionándote en la cancha."},
        {"autor": "Jon Sanz", "texto": "La chispa, la velocidad y la energía contagiosa pueden cambiar el ritmo y el destino de cualquier partido."},
        {"autor": "Javi Rico", "texto": "Lo que realmente importa es que el rival sienta que no vas a dar ni una sola bola por perdida."},
        {"autor": "Momo González", "texto": "El talento espectacular arriba tiene que ir obligatoriamente acompañado de una defensa impecable abajo."},
        {"autor": "Coki Nieto", "texto": "El volumen de juego asfixia. Oblígate siempre a meter una bola más que los que están enfrente."},
        {"autor": "Lucas Campagnolo", "texto": "Siente la energía del partido, vívelo. El pádel es espectáculo y pura emoción en cada transición."},
        {"autor": "Alejandro Ruiz Granados", "texto": "Los obstáculos te enseñan que cada minuto compitiendo en el 20x10 es un privilegio. Disfruta el proceso."}
    ]

    consejo_del_dia = random.choice(consejos)

    # NUEVO DISEÑO: Tarjeta responsive (width 100%), padding reducido
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
    st.subheader("🛠️ Gestión Manual de Horarios")
    st.write("Asigna o edita individualmente el horario y la cancha para los partidos pendientes (Zonas y Playoffs).")
    
    # Traemos todos los partidos pendientes (sin importar si son de zona o playoff)
    df = cargar_datos("SELECT id, instancia, pareja1, pareja2, horario, cancha FROM partidos WHERE torneo_id = :torneo_id AND estado_partido != 'Finalizado' ORDER BY id", params={"torneo_id": int(torneo_id)})
    
    if df is None or df.empty:
        st.info("No hay partidos pendientes para gestionar horarios.")
        return

    opciones_canchas = ['Cancha Central', 'Cancha 2', 'Cancha 3']

    # Cabeceras de la tabla visual
    c_head1, c_head2, c_head3, c_head4 = st.columns([3, 2, 2, 1])
    c_head1.markdown("**Partido / Instancia**")
    c_head2.markdown("**Horario (YYYY-MM-DD HH:MM)**")
    c_head3.markdown("**Cancha**")
    c_head4.markdown("**Acción**")
    st.divider()

    for _, row in df.iterrows():
        with st.container():
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            
            c1.markdown(f"<span style='font-size:0.85rem; color:#888;'>{row['instancia']}</span><br><b>{row['pareja1']}</b> vs <b>{row['pareja2']}</b>", unsafe_allow_html=True)
            
            curr_horario = row['horario'] if row['horario'] else ""
            nuevo_horario = c2.text_input("Horario", value=curr_horario, key=f"h_{row['id']}", label_visibility="collapsed", placeholder="YYYY-MM-DD HH:MM")
            
            curr_cancha = row['cancha'] if row['cancha'] else 'Cancha Central'
            if curr_cancha not in opciones_canchas: opciones_canchas.append(curr_cancha)
            nueva_cancha = c3.selectbox("Cancha", options=opciones_canchas, index=opciones_canchas.index(curr_cancha), key=f"c_{row['id']}", label_visibility="collapsed")
            
            if c4.button("💾", key=f"btn_h_{row['id']}", help="Guardar horario para este partido"):
                h_val = nuevo_horario.strip() if nuevo_horario.strip() else None
                run_action(
                    "UPDATE partidos SET horario = :h, cancha = :c WHERE id = :id", 
                    {"h": h_val, "c": nueva_cancha, "id": row['id']}
                )
                st.toast(f"✅ Partido #{row['id']} actualizado", icon="💾")
                limpiar_cache()
                time.sleep(1)
                st.rerun()
        st.divider()

def procesar_resultado(partido_id, score_p1, score_p2, torneo_id):
    """
    Procesa los scores, determina el ganador, guarda en DB y actualiza la tabla de posiciones.
    score_p1 y score_p2 son listas/tuplas con los games de cada set [s1, s2, s3].
    """
    # 1. Determinar Ganador y Resultado String
    sets_p1 = 0
    sets_p2 = 0
    res_str_parts = []
    
    # Analizar sets
    for i in range(3):
        g1 = score_p1[i]
        g2 = score_p2[i]
        
        # Si ambos son 0, asumimos set no jugado
        if g1 == 0 and g2 == 0:
            continue
            
        res_str_parts.append(f"{g1}-{g2}")
        if g1 > g2:
            sets_p1 += 1
        elif g2 > g1:
            sets_p2 += 1

    resultado_final = " ".join(res_str_parts)
    
    # Obtener nombres de parejas para determinar ganador
    df_partido = cargar_datos("SELECT pareja1, pareja2 FROM partidos WHERE id = :id", {"id": partido_id})
    if df_partido is None or df_partido.empty: return False
    
    pareja1 = df_partido.iloc[0]['pareja1']
    pareja2 = df_partido.iloc[0]['pareja2']
    
    ganador = pareja1 if sets_p1 > sets_p2 else pareja2
    
    # 2. Actualizar Tabla Partidos
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
    
    # 3. Recalcular Tabla de Posiciones (Integral)
    actualizar_tabla_posiciones(torneo_id)
    
    return True

def cronograma_visual(torneo_id):
    """Muestra el gráfico timeline de los partidos programados."""
    fig = generar_grafico_timeline(torneo_id)
    if fig:
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.info("Aún no hay horarios asignados para graficar el cronograma.")

def seccion_carga_resultados(torneo_id):
    st.subheader("🎾 Carga de Resultados")
    
    # Obtener partidos pendientes de resultado (Próximo o En Juego)
    # Filtramos por estado != 'Finalizado' para permitir cargar los que están en juego también
    # MODIFICADO: Incluimos set1, set2, set3 para pre-visualizar si ya hay algo cargado
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

    # Iterar partidos
    for idx, row in df_matches.iterrows():
        # Helper para parsear sets guardados "6-4" -> (6, 4)
        def parse_set(val):
            if val and '-' in str(val):
                try:
                    return int(val.split('-')[0]), int(val.split('-')[1])
                except:
                    return 0, 0
            return 0, 0

        s1_p1, s1_p2 = parse_set(row['set1'])
        s2_p1, s2_p2 = parse_set(row['set2'])
        s3_p1, s3_p2 = parse_set(row['set3'])

        with st.container(border=True):
            # Cabecera Compacta
            st.markdown(f"**{row['instancia']}** | {row['pareja1']} vs {row['pareja2']}")
            st.caption(f"Estado: {row['estado_partido']} | {row['horario']}")

            # Botón Iniciar (Fuera del form para acción inmediata)
            if row['estado_partido'] == 'Próximo':
                if st.button("⏱️ Iniciar (En Vivo)", key=f"btn_start_res_{row['id']}", use_container_width=True):
                    now = datetime.now().strftime("%H:%M")
                    run_action("UPDATE partidos SET estado_partido = 'En Juego', hora_inicio_real = :h WHERE id = :id", {"h": now, "id": row['id']})
                    st.toast("✅ Partido Iniciado", icon="🚀")
                    limpiar_cache()
                    time.sleep(0.5)
                    st.rerun()

            # Formulario Optimizado (Grid Layout)
            with st.form(key=f"form_res_{row['id']}"):
                # Encabezados Sets
                c_null, c_head1, c_head2, c_head3 = st.columns([2, 1, 1, 1])
                c_head1.markdown("<div style='text-align:center; font-size:0.75rem; color:#888'>SET 1</div>", unsafe_allow_html=True)
                c_head2.markdown("<div style='text-align:center; font-size:0.75rem; color:#888'>SET 2</div>", unsafe_allow_html=True)
                c_head3.markdown("<div style='text-align:center; font-size:0.75rem; color:#888'>SET 3</div>", unsafe_allow_html=True)

                # Fila Pareja 1
                cp1_name, cp1_s1, cp1_s2, cp1_s3 = st.columns([2, 1, 1, 1])
                cp1_name.markdown(f"<div style='padding-top:10px; font-weight:bold; font-size:0.9rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>{row['pareja1']}</div>", unsafe_allow_html=True)
                v1_1 = cp1_s1.number_input("S1", 0, 7, value=s1_p1, key=f"s1p1_{row['id']}", label_visibility="collapsed")
                v1_2 = cp1_s2.number_input("S2", 0, 7, value=s2_p1, key=f"s2p1_{row['id']}", label_visibility="collapsed")
                v1_3 = cp1_s3.number_input("S3", 0, 15, value=s3_p1, key=f"s3p1_{row['id']}", label_visibility="collapsed")

                # Fila Pareja 2
                cp2_name, cp2_s1, cp2_s2, cp2_s3 = st.columns([2, 1, 1, 1])
                cp2_name.markdown(f"<div style='padding-top:10px; font-weight:bold; font-size:0.9rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>{row['pareja2']}</div>", unsafe_allow_html=True)
                v2_1 = cp2_s1.number_input("S1", 0, 7, value=s1_p2, key=f"s1p2_{row['id']}", label_visibility="collapsed")
                v2_2 = cp2_s2.number_input("S2", 0, 7, value=s2_p2, key=f"s2p2_{row['id']}", label_visibility="collapsed")
                v2_3 = cp2_s3.number_input("S3", 0, 15, value=s3_p2, key=f"s3p2_{row['id']}", label_visibility="collapsed")

                st.write("")
                if st.form_submit_button("💾 Guardar y Finalizar", type="primary", use_container_width=True):
                    score_p1 = [v1_1, v1_2, v1_3]
                    score_p2 = [v2_1, v2_2, v2_3]
                    
                    # Validación básica: Al menos un set jugado
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
    """Dashboard visual para controlar el estado de inscripción de las categorías."""
    st.subheader("🚦 Semáforo de Inscripciones (Torneos Abiertos)")
    
    # Consulta para contar parejas por Torneo y Categoría
    query = """
        SELECT t.id, t.nombre, i.categoria, COUNT(*) as cantidad 
        FROM inscripciones i 
        JOIN torneos t ON i.torneo_id = t.id 
        WHERE t.estado = 'Abierto' 
        GROUP BY t.id, t.nombre, i.categoria
        ORDER BY t.id DESC
    """
    # Usamos cargar_datos (sin caché larga) para tener datos frescos
    df = cargar_datos(query)
    
    if df is None or df.empty:
        st.info("No hay inscripciones activas para monitorear.")
    else:
        # Grid de 4 columnas para las tarjetas
        cols = st.columns(4)
        for index, row in df.iterrows():
            count = row['cantidad']
            label = f"{row['nombre']}\n({row['categoria']})"
            
            with cols[index % 4]:
                if count < 3:
                    st.error(f"**{label}**\n\n🚨 **{count}** Parejas\n\n*CRÍTICO: Insuficiente*")
                elif count == 3:
                    st.warning(f"**{label}**\n\n⚠️ **{count}** Parejas\n\n*MÍNIMO: Zona Única*")
                else:
                    st.success(f"**{label}**\n\n✅ **{count}** Parejas\n\n*LISTO: Cupo Completo*")
    st.divider()

def seccion_transferir_jugadores():
    st.subheader("🔄 Transferencia de Inscripciones")
    st.info("Herramienta para mover inscripciones entre torneos (útil para correcciones).")
    
    # 1. Selectores de Torneo
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

    # 2. Selección de Jugadores
    df_insc = get_data("SELECT id, jugador1, jugador2 FROM inscripciones WHERE torneo_id = :tid", params={"tid": id_origen})
    
    if df_insc is None or df_insc.empty:
        st.warning("El torneo de origen no tiene inscriptos.")
        return
        
    # Mapa para el multiselect
    map_insc = {f"{row['jugador1']} - {row['jugador2']}": row['id'] for _, row in df_insc.iterrows()}
    
    sel_ids = st.multiselect("Seleccionar Parejas a Mover", options=list(map_insc.keys()))
    
    if st.button("🚀 Confirmar Transferencia", type="primary"):
        if not sel_ids:
            st.error("Debes seleccionar al menos una pareja.")
            return
            
        count_moved = 0
        count_skipped = 0
        
        # Validar duplicados en destino (Normalización por conjunto para evitar error por orden J1-J2)
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
            if count_skipped > 0:
                st.warning(f"⚠️ Se omitieron {count_skipped} parejas por estar duplicadas en el destino.")
            st.cache_data.clear()
            time.sleep(2)
            st.rerun()
        elif count_skipped > 0:
             st.error("❌ Todas las parejas seleccionadas ya existen en el torneo de destino.")

def debug_base_datos():
    """Función de depuración para visualizar tablas clave."""
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
    """
    Sincroniza datos desde la base de datos en la nube (PostgreSQL)
    a una base de datos local (SQLite), sobreescribiendo los datos locales.
    """
    local_db_file = 'torneos_padel.db'
    tablas_a_sincronizar = [
        'torneos', 'inscripciones', 'jugadores', 'zonas', 
        'partidos', 'zonas_posiciones', 'eventos', 
        'ranking_puntos', 'fotos', 'partido_en_vivo'
    ]

    # Inicializar UI de la barra de progreso
    total_tablas = len(tablas_a_sincronizar)
    progress_bar = st.progress(0, text="Preparando entorno local...")

    try:
        # Conectar a la base de datos local SQLite
        with sqlite3.connect(local_db_file) as conn_local:
            cursor = conn_local.cursor()
            
            # Deshabilitar claves foráneas durante la carga masiva para evitar errores de orden
            cursor.execute("PRAGMA foreign_keys = OFF;")

            for i, tabla in enumerate(tablas_a_sincronizar):
                # Actualizar barra de progreso con el porcentaje y el nombre de la tabla
                progress_bar.progress(i / total_tablas, text=f"Descargando tabla: {tabla} ({i+1}/{total_tablas})...")
                
                # 1. Leer todos los datos de la tabla en la nube (PostgreSQL)
                df_nube = cargar_datos(f"SELECT * FROM {tabla}")
                
                if df_nube is not None:
                    # 2 y 3. Garantizar existencia de la tabla e insertar datos en SQLite
                    # Con if_exists='replace', Pandas INICIALIZA automáticamente la tabla 
                    # con las columnas correctas de la nube si esta no existía previamente, 
                    # o la borra y reemplaza si ya existía. Esto evita el error "no such table".
                    df_nube.to_sql(tabla, conn_local, if_exists='replace', index=False)
                else:
                    st.write(f"  -> Tabla `{tabla}` vacía en la nube o no se pudo leer. Omitiendo.")

            # Llenar la barra al 100% cuando termine el bucle
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
    df_partidos = cargar_datos("SELECT pareja1, pareja2, resultado, ganador, set1, set2, set3 FROM partidos WHERE torneo_id=:torneo_id AND instancia='Zona' AND estado_partido='Finalizado'", {"torneo_id": torneo_id})
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
                    
                    if g1 > g2:
                        sets_p1 += 1
                    elif g2 > g1:
                        sets_p2 += 1
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
    if not st.session_state.get('es_admin', False):
        return False, "Acceso denegado"
    
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
    if not st.session_state.get('es_admin', False):
        return
    
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
    if not st.session_state.get('es_admin', False):
        return
    run_action("UPDATE partidos SET estado_partido = %(estado_partido)s WHERE id = %(id)s", {"estado_partido": nuevo_estado, "id": partido_id})
    limpiar_cache()

def actualizar_marcador(partido_id, resultado):
    if not st.session_state.get('es_admin', False):
        return
    run_action("UPDATE partidos SET resultado = %(resultado)s WHERE id = %(id)s", {"resultado": resultado, "id": partido_id})
    limpiar_cache()

def guardar_foto(nombre, imagen):
    if not st.session_state.get('es_admin', False):
        return
    # Postgres usa BYTEA para binarios, pasamos los bytes directamente
    run_action("INSERT INTO fotos (nombre, imagen, fecha) VALUES (%(nombre)s, %(imagen)s, NOW())", 
              {"nombre": nombre, "imagen": imagen})
    limpiar_cache()

def guardar_jugador(celular, password, nombre, apellido, localidad, cat_actual, cat_anterior, foto_blob):
    if not st.session_state.get('es_admin', False):
        return
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
    if not st.session_state.get('es_admin', False):
        return
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

@st.fragment
def show_ranking_content():
    """Fragmento para filtrado y visualización del ranking sin recargar la página."""
    st.header("📈 Ranking Oficial Rincón Padel")

    # 1. Filtro Dinámico de Categoría
    # Leemos las categorías disponibles en la tabla torneos
    df_cats = get_data("SELECT DISTINCT categoria FROM torneos")
    opciones_cat = ["Todas"] + df_cats['categoria'].tolist() if (df_cats is not None and not df_cats.empty) else ["Todas"]
    
    cat_sel = st.selectbox("Filtrar por Categoría", opciones_cat)
    
    # 2. Consulta SQL (Corregida para PostgreSQL)
    if cat_sel == "Todas":
        query = """
            SELECT jugador, SUM(puntos) as total_puntos, COUNT(DISTINCT torneo_id) as torneos_jugados 
            FROM ranking_puntos 
            GROUP BY jugador 
            ORDER BY total_puntos DESC 
            LIMIT 10
        """
        params = {}
    else:
        # Usamos :categoria en lugar de % para evitar errores de sintaxis
        query = """
            SELECT jugador, SUM(puntos) as total_puntos, COUNT(DISTINCT torneo_id) as torneos_jugados 
            FROM ranking_puntos 
            WHERE categoria = :categoria 
            GROUP BY jugador 
            ORDER BY total_puntos DESC 
            LIMIT 10
        """
        params = {"categoria": cat_sel} 
        
    df_ranking = get_data(query, params=params)
    
    # 3. Visualización Estilizada
    if df_ranking is None:
        return
        
    if df_ranking.empty:
        st.info("No hay puntos registrados para esta categoría aún.")
    else:
        # Estilos CSS personalizados
        st.markdown("""
        <style>
            .ranking-card {
                background-color: #000000;
                border: 1px solid #333;
                border-radius: 12px;
                padding: 15px;
                margin-bottom: 12px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            }
            .ranking-pos-box {
                width: 50px;
                text-align: center;
                font-size: 1.5rem;
                font-weight: 900;
                color: #fff;
            }
            .ranking-details {
                flex-grow: 1;
                padding-left: 15px;
            }
            .ranking-name {
                font-size: 1.2rem;
                font-weight: bold;
                color: #fff;
            }
            .ranking-stats {
                text-align: right;
                min-width: 100px;
            }
            .ranking-points {
                color: #00C853;
                font-size: 1.4rem;
                font-weight: 900;
            }
            .ranking-sub {
                color: #888;
                font-size: 0.8rem;
            }
            .leader-card {
                border: 2px solid #00C853;
                box-shadow: 0 0 20px rgba(0, 200, 83, 0.2);
                transform: scale(1.02);
            }
        </style>
        """, unsafe_allow_html=True)
        
        for index, row in df_ranking.iterrows():
            pos = index + 1
            is_leader = "leader-card" if pos == 1 else ""
            medal = "🥇" if pos == 1 else "🥈" if pos == 2 else "🥉" if pos == 3 else f"{pos}°"
            
            st.markdown(f"""
            <div class='ranking-card {is_leader}'>
                <div class='ranking-pos-box'>{medal}</div>
                <div class='ranking-details'>
                    <div class='ranking-name'>{row['jugador']}</div>
                </div>
                <div class='ranking-stats'>
                    <div class='ranking-points'>{row['total_puntos']} pts</div>
                    <div class='ranking-sub'>{row['torneos_jugados']} Torneos</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# --- LOGO Y SIDEBAR ---
if logo:
    st.sidebar.image(logo, use_container_width=True)

# Animación Sidebar (Pelota sutil)
lottie_ball = load_lottieurl(URL_LOTTIE_BALL)
if lottie_ball:
    with st.sidebar:
        st_lottie(lottie_ball, height=180, key="sidebar_anim")

# --- LOGIN / REGISTRO RÁPIDO (TOP SIDEBAR) ---
if 'usuario_logueado' not in st.session_state:
    st.session_state['usuario_logueado'] = False
if 'datos_usuario' not in st.session_state:
    st.session_state['datos_usuario'] = None

with st.sidebar.expander("🔐 Acceso (Admin/Usuarios)"):
    if not st.session_state['usuario_logueado'] and not st.session_state.get('es_admin', False):
        tab_user, tab_admin = st.tabs(["Jugador", "Admin"])
        
        with tab_user:
            with st.form("login_form_sidebar"):
                l_dni = st.text_input("DNI", placeholder="DNI", label_visibility="collapsed")
                l_pass = st.text_input("Contraseña", placeholder="Contraseña", type="password", label_visibility="collapsed")
                if st.form_submit_button("Entrar"):
                    usuario = autenticar_usuario(l_dni, l_pass) 
                    if usuario:
                        st.session_state['usuario_logueado'] = True
                        st.session_state['datos_usuario'] = usuario
                        st.session_state['usuario'] = usuario
                        st.toast("¡Bienvenido al sistema! 🎾", icon="✅")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Credenciales incorrectas.")
        
        with tab_admin:
            with st.form("login_admin"):
                admin_user = st.text_input("Usuario", placeholder="Admin User", label_visibility="collapsed")
                admin_pass = st.text_input("Pass", placeholder="Admin Pass", type="password", label_visibility="collapsed")
                if st.form_submit_button("Acceder"):
                    if admin_user == st.secrets.get("USUARIO_ADMIN") and admin_pass == st.secrets.get("PASS_ADMIN"):
                        st.session_state.es_admin = True
                        st.success("Admin Activo")
                        st.rerun()
                    else:
                        st.error("Error de acceso")
    else:
        if st.session_state.get('es_admin', False):
            st.success("👮‍♂️ Modo Administrador")
            if st.button("Salir Admin"):
                st.session_state.es_admin = False
                st.rerun()
        
        if st.session_state['usuario_logueado']:
            st.success(f"👤 {st.session_state['datos_usuario']['nombre']}")
            if st.button("Cerrar Sesión"):
                st.session_state['usuario_logueado'] = False
                st.session_state['datos_usuario'] = None
                if 'usuario' in st.session_state: del st.session_state['usuario']
                st.rerun()

# --- SELECTOR DE TORNEO (GLOBAL SIDEBAR) ---
st.sidebar.markdown("---")
st.sidebar.subheader("📅 Torneo Activo")
df_torneos_sb = cargar_datos("SELECT id, nombre, categoria FROM torneos ORDER BY id DESC")

if df_torneos_sb is not None and not df_torneos_sb.empty:
    # TAREA 2: Format func con ID para evitar duplicados visuales
    opts_sb = {row['id']: f"ID {row['id']} | {row['nombre']} - {row['categoria']}" for _, row in df_torneos_sb.iterrows()}
    lista_ids = list(opts_sb.keys())
    
    # Usamos session_state para persistencia
    if 'id_torneo' not in st.session_state:
        st.session_state.id_torneo = int(df_torneos_sb.iloc[0]['id'])

    def update_torneo():
        st.session_state.id_torneo = st.session_state.selector_torneo

    # Sincronizar índice para que el selector refleje cambios externos (ej: botones del home)
    lista_ids = list(opts_sb.keys())
    # Sincronizar índice usando valor actual o por defecto (evita error de API)
    val_actual = st.session_state.get('id_torneo', lista_ids[0])
    try:
        idx_sel = lista_ids.index(st.session_state.id_torneo)
        idx_sel = lista_ids.index(val_actual)
    except ValueError:
        idx_sel = 0
        
    # Asegurar que id_torneo existe en session_state para el resto de la app
    if 'id_torneo' not in st.session_state:
        st.session_state.id_torneo = lista_ids[idx_sel]

    st.sidebar.selectbox(
        "Seleccionar Evento", 
        options=lista_ids, 
        format_func=lambda x: opts_sb.get(x, f"ID {x}"), 
        index=idx_sel,
        key="selector_torneo",
        on_change=update_torneo
    )
else:
    st.sidebar.warning("No hay torneos disponibles.")

# --- MODO MANTENIMIENTO (SI NO ES ADMIN) ---
if st.secrets.get("MODO_MANTENIMIENTO", False) and not st.session_state.get('es_admin', False):
    st.markdown("<h1 style='text-align: center; color: #333333;'>Rincón Padel - Torneos Villaguay</h1>", unsafe_allow_html=True)
    
    # Pantalla de Próximamente
    st.markdown("""
    <div style='text-align: center; padding: 50px;'>
        <h2 style='color: #00E676;'>🚧 PRÓXIMAMENTE 🚧</h2>
        <p style='font-size: 1.2rem;'>Estamos preparando la mejor experiencia de torneos para vos.</p>
        <p>Mientras tanto, puedes registrarte para validar tu categoría.</p>
    </div>
    """, unsafe_allow_html=True)

    # Pestaña de Registro Público
    with st.expander("📝 Registrarse como Jugador", expanded=True):
        with st.form("register_form_public"):
            st.write("Completa tus datos para crear tu perfil:")
            c1, c2 = st.columns(2)
            r_nombre = c1.text_input("Nombre")
            r_apellido = c1.text_input("Apellido")
            r_dni = c2.text_input("DNI (Usuario)", placeholder="Sin puntos")
            r_cel = c1.text_input("Celular (WhatsApp)", placeholder="Ej: 3455...")
            r_pass = c2.text_input("Contraseña", type="password")
            r_loc = st.text_input("Localidad")
            
            cat_map = {1: "Libre", 2: "3ra", 3: "4ta", 4: "5ta", 5: "6ta", 6: "7ma", 7: "8va"}
            r_cat_num = st.slider("Categoría Actual (Nivel)", 1, 7, 6)
            r_cat = cat_map[r_cat_num]
            st.caption(f"Nivel seleccionado: {r_cat}")
            
            if st.form_submit_button("Crear Cuenta"):
                if r_dni and r_pass and r_nombre and r_cel:
                    ok, msg = registrar_jugador_db(r_dni, r_nombre, r_apellido, r_cel, r_cat, r_loc, r_pass)
                    if ok:
                        st.success("¡Registro exitoso!")
                        # Botón de WhatsApp para validación
                        msg_wa = f"Hola Rincón Padel, soy {r_nombre} {r_apellido}. Me registré con el DNI {r_dni} en categoría {r_cat}. Solicito validación de cuenta."
                        link_wa = f"https://wa.me/5493455454907?text={urllib.parse.quote(msg_wa)}"
                        st.markdown(f"""
                        <a href="{link_wa}" target="_blank">
                            <button style="background-color:#25D366; color:white; border:none; padding:10px 20px; border-radius:5px; font-weight:bold; cursor:pointer;">
                                📲 Confirmar Identidad por WhatsApp
                            </button>
                        </a>
                        """, unsafe_allow_html=True)
                    else:
                        st.error(msg)
                else:
                    st.warning("Completa todos los campos obligatorios.")
    st.stop() # Detiene la ejecución aquí para no mostrar el resto de la app

# --- NAVEGACIÓN PRINCIPAL ---
menu = ["🏆 Inicio", "📅 Fixture y Horarios", "📊 Posiciones", "📈 Ranking", "👥 Jugadores", "📍 Sede", "📺 Pantalla TV","💻 Simulador"]

if st.session_state.get('usuario_logueado'):
    menu.append("🏠 Mi Panel")

if st.session_state.get('es_admin', False):
    menu.append("⚙️ Admin")

choice = st.sidebar.radio("Navegación", menu, key="menu_nav")

# --- CONTACTO Y REDES ---
st.sidebar.markdown("---")
st.sidebar.subheader("Contacto y Redes")
st.sidebar.markdown("""
    <div style="display: flex; flex-direction: column; gap: 15px; margin-top: 10px;">
        <a href="https://wa.me/543455454907" target="_blank" style="text-decoration: none; color: inherit;">
            <div style="display: flex; align-items: center; gap: 12px; padding: 10px; background-color: #1E1E1E; border: 1px solid #333; border-radius: 8px; transition: all 0.3s ease; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                <img src="https://upload.wikimedia.org/wikipedia/commons/6/6b/WhatsApp.svg" width="24" height="24">
                <span style="font-weight: 500; font-size: 0.95rem; color: #E0E0E0;">Consultas por WhatsApp</span>
            </div>
        </a>
        <a href="https://www.instagram.com/rinconpadel.vg/" target="_blank" style="text-decoration: none; color: inherit;">
            <div style="display: flex; align-items: center; gap: 12px; padding: 10px; background-color: #1E1E1E; border: 1px solid #333; border-radius: 8px; transition: all 0.3s ease; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                <img src="https://upload.wikimedia.org/wikipedia/commons/e/e7/Instagram_logo_2016.svg" width="24" height="24">
                <span style="font-weight: 500; font-size: 0.95rem; color: #E0E0E0;">Seguinos en Instagram</span>
            </div>
        </a>
            <a href="https://www.google.com/maps/search/?api=1&query=-31.874656,-59.023991" target="_blank" style="text-decoration: none; color: inherit;">
                <div style="display: flex; align-items: center; gap: 12px; padding: 10px; background-color: #1E1E1E; border: 1px solid #333; border-radius: 8px; transition: all 0.3s ease; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                    <img src="https://upload.wikimedia.org/wikipedia/commons/b/bd/Google_Maps_Logo_2020.svg" width="24" height="24">
                    <span style="font-weight: 500; font-size: 0.95rem; color: #E0E0E0;">Cómo llegar a la Sede</span>
                </div>
            </a>
    </div>
""", unsafe_allow_html=True)

def mostrar_sponsors_sidebar(torneo_id):
    sponsors = cargar_datos("SELECT nombre_sponsor, imagen_url FROM sponsors WHERE torneo_id = %(torneo_id)s", {"torneo_id": torneo_id})
    if sponsors is not None and not sponsors.empty:
        st.sidebar.markdown("---")
        st.sidebar.subheader("🤝 Sponsors del Torneo")
        for _, row in sponsors.iterrows():
            if row['imagen_url'] and row['imagen_url'].strip() != "":
                html_sponsor = f"""
                <div style="text-align: center; margin-bottom: 15px; padding: 10px; background-color: rgba(255,255,255,0.05); border-radius: 10px; border: 1px solid #333;">
                    <img src="{row['imagen_url']}" style="max-width: 100%; max-height: 80px; object-fit: contain; margin-bottom: 8px;">
                    <div style="font-size: 0.85rem; font-weight: bold; color: #ccc;">{row['nombre_sponsor']}</div>
                </div>
                """
                st.sidebar.markdown(html_sponsor, unsafe_allow_html=True)
            else:
                st.sidebar.markdown(f"🏢 **{row['nombre_sponsor']}**")

if 'id_torneo' in st.session_state:
    mostrar_sponsors_sidebar(st.session_state.id_torneo)

def gestionar_sponsors_admin(torneo_id):
    if not st.session_state.get('es_admin', False):
        return
        
    st.subheader("🤝 Gestión de Sponsors")
    
    with st.form("form_nuevo_sponsor"):
        nombre_sponsor = st.text_input("Nombre del Sponsor")
        imagen_url = st.text_input("URL de la Imagen (Logo)")
        
        if st.form_submit_button("💾 Guardar Sponsor"):
            if nombre_sponsor:
                query = "INSERT INTO sponsors (torneo_id, nombre_sponsor, imagen_url) VALUES (%(torneo_id)s, %(nombre)s, %(url)s)"
                params = {"torneo_id": torneo_id, "nombre": nombre_sponsor, "url": imagen_url}
                run_action(query, params)
                st.success(f"Sponsor {nombre_sponsor} agregado correctamente.")
                st.rerun()
            else:
                st.error("El nombre del sponsor es obligatorio.")
    
    st.markdown("#### Sponsors Actuales")
    sponsors = cargar_datos("SELECT id, nombre_sponsor, imagen_url FROM sponsors WHERE torneo_id = %(torneo_id)s", {"torneo_id": torneo_id})
    
    if sponsors is not None and not sponsors.empty:
        for _, row in sponsors.iterrows():
            col1, col2, col3 = st.columns([1, 3, 1])
            if row['imagen_url']:
                col1.image(row['imagen_url'], width=50)
            else:
                col1.write("🏢")
            col2.write(f"**{row['nombre_sponsor']}**")
            if col3.button("🗑️ Eliminar", key=f"del_sponsor_{row['id']}"):
                run_action("DELETE FROM sponsors WHERE id = %(id)s", {"id": row['id']})
                st.warning("Sponsor eliminado.")
                st.rerun()
    else:
        st.info("No hay sponsors registrados para este torneo.")

def mostrar_panel_usuario():
    if 'usuario' not in st.session_state:
        st.warning("Por favor inicia sesión para ver tu panel.")
        st.stop()
    
    # Estilos Dashboard
    st.markdown("""
    <style>
        .dashboard-card {
            background-color: #121212;
            border: 2px solid #39FF14;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 0 15px rgba(57, 255, 20, 0.15);
            margin-bottom: 20px;
        }
        .dash-title { color: #39FF14; font-size: 1.2rem; font-weight: bold; margin-bottom: 10px; display: flex; align-items: center; gap: 10px; }
        .dash-stat { font-size: 2.5rem; font-weight: 900; color: white; }
        .dash-sub { color: #888; font-size: 0.9rem; }
        .next-match { background: #1E1E1E; border-left: 5px solid #39FF14; padding: 15px; }
    </style>
    """, unsafe_allow_html=True)
    
    st.title(f"🏠 Hola, {st.session_state['usuario']['nombre']}!")
    
    # 1. Próximo Partido (Busca por apellido en partidos pendientes)
    search_term = st.session_state['usuario']['apellido']
    df_next = get_data("SELECT * FROM partidos WHERE (pareja1 LIKE :search_term OR pareja2 LIKE :search_term) AND estado_partido != 'Finalizado' AND estado_partido != 'Disponible'", params={"search_term": f"%{search_term}%"})
    
    st.markdown("<div class='dashboard-card'><div class='dash-title'>🕒 Próximo Partido</div>", unsafe_allow_html=True)
    if df_next is not None and not df_next.empty:
        match = df_next.iloc[0]
        st.markdown(f"""<div class='next-match'><h3 style='margin:0'>🎾 {match['pareja1']} vs {match['pareja2']}</h3><p style='color:#00E676; font-weight:bold; margin:5px 0'>{match['instancia']} | {match['estado_partido']}</p><p>📍 Cancha Central (Consultar Horario)</p></div>""", unsafe_allow_html=True)
    else:
        st.info("No tienes partidos programados próximamente.")
    st.markdown("</div>", unsafe_allow_html=True)
    
    # 2. Resumen Temporada & Ranking
    c1, c2 = st.columns(2)
    df_played = get_data("SELECT * FROM partidos WHERE (pareja1 LIKE :search_term OR pareja2 LIKE :search_term) AND estado_partido = 'Finalizado'", params={"search_term": f"%{search_term}%"})
    played = len(df_played)
    wins = sum(1 for _, r in df_played.iterrows() if r['ganador'] and search_term in r['ganador'])
    eff = (wins / played * 100) if played > 0 else 0
    
    with c1:
        st.markdown(f"""<div class='dashboard-card'><div class='dash-title'>📊 Resumen Temporada</div><div style='display:flex; justify-content:space-around; text-align:center'><div><div class='dash-stat'>{played}</div><div class='dash-sub'>Partidos</div></div><div><div class='dash-stat'>{wins}</div><div class='dash-sub'>Victorias</div></div><div><div class='dash-stat'>{int(eff)}%</div><div class='dash-sub'>Efectividad</div></div></div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class='dashboard-card'><div class='dash-title'>🏆 Ranking {st.session_state['usuario']['categoria']}</div><div style='text-align:center'><div class='dash-stat'>#{random.randint(1, 15)}</div><div class='dash-sub'>Posición Actual</div><div style='margin-top:10px; font-size:0.8rem; color:#666'>Puntos: {wins * 100 + played * 50}</div></div></div>""", unsafe_allow_html=True)
        
    # 3. Accesos Rápidos
    st.markdown("### 🚀 Accesos Rápidos")
    b1, b2 = st.columns(2)
    if b1.button("📝 Inscribirme al próximo torneo", use_container_width=True):
        st.info("Ve a la pestaña Torneos > Inscripción")
    if b2.button("🤝 Buscar Pareja", use_container_width=True):
        st.info("Función próximamente disponible")

def mostrar_inicio():
    # 1. TÍTULO PRINCIPAL CENTRADO
    st.markdown("""
        <div style="
            background-color: #39FF14;
            color: black;
            padding: 10px;
            border-radius: 8px;
            text-align: center;
            font-family: 'Segoe UI', sans-serif;
            font-weight: 900;
            font-size: 2.2rem;
            text-transform: uppercase;
            letter-spacing: 2px;
            box-shadow: 0 0 20px rgba(57, 255, 20, 0.5);
            margin-bottom: 25px;
        ">
            ESTÁS EN EL RINCÓN
        </div>
    """, unsafe_allow_html=True)

    # 2. LOGICA TORNEO ACTIVO
    # Priorizamos 'En Juego' para el destacado
    df_active = cargar_datos("SELECT * FROM torneos WHERE estado = 'En Juego' ORDER BY id DESC LIMIT 1")
    if df_active is None or df_active.empty:
        df_active = cargar_datos("SELECT * FROM torneos WHERE estado = 'Abierto' ORDER BY id DESC LIMIT 1")
        
    if df_active is not None and not df_active.empty:
        t_act = df_active.iloc[0]
        
        # Verificar si hay afiche cargado para este torneo
        df_afiche = cargar_datos("SELECT afiche FROM eventos WHERE torneo_id = :tid", params={"tid": int(t_act['id'])})
        afiche_path = None
        if df_afiche is not None and not df_afiche.empty and df_afiche.iloc[0]['afiche']:
            if os.path.exists(df_afiche.iloc[0]['afiche']):
                afiche_path = df_afiche.iloc[0]['afiche']

        # LAYOUT 2 COLUMNAS (1.2 - 1)
        c_izq, c_der = st.columns([1.2, 1], gap="large")

        with c_izq:
            if afiche_path:
                st.image(afiche_path, use_container_width=True)
            else:
                # Fallback elegante si no hay afiche
                st.markdown(f"""
                <div style="
                    height: 400px;
                    background: linear-gradient(135deg, #003300 0%, #000000 100%);
                    border: 2px solid #00FF00;
                    border-radius: 15px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    flex-direction: column;
                ">
                     <h1 style="font-size:5rem;">🎾</h1>
                     <h3 style="color:#00FF00;">{t_act['nombre']}</h3>
                </div>
                """, unsafe_allow_html=True)

        with c_der:
            st.markdown(f"""
            <div style="
                background: linear-gradient(145deg, #050505, #111);
                border-left: 5px solid #00FF00;
                padding: 25px;
                border-radius: 12px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.5);
                margin-bottom: 20px;
            ">
                <h2 style="color: #00FF00; margin: 0; text-transform: uppercase; font-size: 2rem; text-shadow: 0 0 10px rgba(0,255,0,0.3); font-weight: 900;">{t_act['nombre']}</h2>
                <h3 style="color: white; margin: 15px 0 10px 0;">Categoría <span style="color: #00FF00;">{t_act['categoria']}</span></h3>
                <p style="color: #ccc; font-size: 1.1rem; margin: 0;">📅 {t_act['fecha']}</p>
                <div style="margin-top: 15px;">
                    <span style="background-color: #00FF00; color: black; padding: 4px 10px; border-radius: 4px; font-size: 0.9rem; font-weight: bold;">{t_act['estado']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Botón de Acción
            def saltar_al_fixture(torneo_id):
                st.session_state.id_torneo = int(torneo_id)
                st.session_state.menu_nav = "📅 Fixture y Horarios"

            st.button("📅 IR AL TORNEO", key="btn_home_main", type="primary", use_container_width=True, on_click=saltar_al_fixture, args=(t_act['id'],))
            
            # Tarea 3: Crear el botón y formulario de "INSCRIBIRSE AHORA"
            if "mostrar_form_inscripcion" not in st.session_state:
                st.session_state.mostrar_form_inscripcion = False

            if st.button("✍️ INSCRIBIRSE AHORA", key="btn_insc", type="secondary", use_container_width=True):
                st.session_state.mostrar_form_inscripcion = not st.session_state.mostrar_form_inscripcion

            if st.session_state.mostrar_form_inscripcion:
                # Mostramos la tabla pública de inscritos antes del formulario
                mostrar_tabla_inscritos(int(t_act['id']))

                with st.container():
                    st.markdown("""<style>div[data-testid="stForm"] {background-color: #0E0E0E !important; border: 1px solid #333 !important;}</style>""", unsafe_allow_html=True)
                    with st.form(key="form_insc"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            jug1 = st.text_input("Jugador 1 (Nombre/DNI)", placeholder="Nombre Completo", key="home_j1")
                            tel1 = st.text_input("Teléfono Jugador 1", placeholder="WhatsApp", key="home_tel1")
                        
                        with col2:
                            jug2 = st.text_input("Jugador 2 (Nombre/DNI)", placeholder="Nombre Completo", key="home_j2")
                            tel2 = st.text_input("Teléfono Jugador 2", placeholder="WhatsApp", key="home_tel2")
                        
                        st.write("")
                        if st.form_submit_button("Enviar Inscripción", type="primary", use_container_width=True):
                            if jug1 and jug2 and tel1 and tel2:
                                with custom_spinner():
                                    guardar_inscripcion(
                                        t_act['id'], jug1, jug2, "A confirmar", 
                                        t_act['categoria'], False, tel1, tel2
                                    )
                                st.success("✅ Inscripción recibida. Estado: Pendiente de validación.")
                                time.sleep(1.5)
                                st.session_state.mostrar_form_inscripcion = False
                                st.rerun()
                            else:
                                st.error("❌ Faltan datos obligatorios: Asegúrate de ingresar Nombre y Teléfono de ambos jugadores.")

            # Consejo Motivacional (Justo debajo del botón)
            mostrar_consejo_padel()
    
    # 3. Próximos Torneos (Columnas)
    st.subheader("🗓️ Próximos Eventos")
    
    exclude_id = int(df_active.iloc[0]['id']) if (df_active is not None and not df_active.empty) else -1
    df_next = cargar_datos("SELECT * FROM torneos WHERE estado = 'Abierto' AND id != :eid ORDER BY id DESC", params={"eid": exclude_id})
    
    if df_next is not None and not df_next.empty:
        cols = st.columns(3)
        for i, (_, row) in enumerate(df_next.iterrows()):
            with cols[i % 3]:
                st.markdown(f"""
                <div style="
                    background-color: #1a1a1a;
                    border: 1px solid #333;
                    border-radius: 10px;
                    padding: 20px;
                    text-align: center;
                    height: 100%;
                ">
                    <div style="font-size: 2rem; margin-bottom: 10px;">📅</div>
                    <div style="color: white; font-weight: bold; font-size: 1.1rem;">{row['nombre']}</div>
                    <div style="color: #00E676;">{row['categoria']}</div>
                    <div style="color: #666; font-size: 0.85rem; margin-top: 5px;">{row['fecha']}</div>
                </div>
                """, unsafe_allow_html=True)
                st.write("")
    else:
        st.info("No hay otros eventos en agenda.")

    # --- 4. FEED SOCIAL / ACTIVIDAD RECIENTE ---
    st.markdown("---")
    st.subheader("⚡ Actividad Reciente")
    
    # Diccionario de Iconos Dinámicos
    iconos_feed = {
        "victoria": "🏆",
        "inscripcion": "🎾",
        "ranking": "📈",
        "aviso": "📣"
    }
    
    # CSS Inyectado para las tarjetas del Feed
    css_feed = """
    <style>
        .feed-card { background-color: #111; border-left: 4px solid #39FF14; border-radius: 8px; padding: 12px 15px; margin-bottom: 10px; display: flex; align-items: center; gap: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.3); transition: transform 0.2s; }
        .feed-card:hover { transform: translateX(5px); background-color: #1a1a1a; border-left: 4px solid #00E676; }
        .feed-icon { font-size: 1.8rem; background: #222; padding: 10px; border-radius: 50%; min-width: 50px; height: 50px; display: flex; align-items: center; justify-content: center; box-shadow: inset 0 0 10px rgba(0,0,0,0.5); }
        .feed-content { flex-grow: 1; }
        .feed-msg { color: #fff; font-size: 0.95rem; margin-bottom: 4px; line-height: 1.3; }
        .feed-time { color: #888; font-size: 0.75rem; font-family: monospace; }
        /* Ajustar scrollbar interno */
        div[data-testid="stVerticalBlock"] > div > div > div > div { scrollbar-width: thin; scrollbar-color: #39FF14 #111; }
        /* Ajustes Móviles */
        @media (max-width: 768px) {
            .feed-card { padding: 10px; gap: 10px; }
            .feed-msg { font-size: 0.85rem; }
            .feed-icon { font-size: 1.5rem; min-width: 40px; height: 40px; padding: 5px; }
        }
    </style>
    """
    st.markdown(css_feed, unsafe_allow_html=True)
    
    # Contenedor con altura fija y Scroll Vertical
    with st.container(height=500):
        if df_active is not None and not df_active.empty:
            tid_activo = int(df_active.iloc[0]['id'])
            # Consultar últimos partidos finalizados reales del torneo
            df_feed = cargar_datos("SELECT pareja1, pareja2, ganador, resultado, hora_fin FROM partidos WHERE torneo_id = :tid AND estado_partido = 'Finalizado' ORDER BY hora_fin DESC NULLS LAST, id DESC LIMIT 10", {"tid": tid_activo})
            
            if df_feed is not None and not df_feed.empty:
                for _, row in df_feed.iterrows():
                    ganador = row['ganador'] if row['ganador'] else "Una pareja"
                    perdedor = row['pareja2'] if ganador == row['pareja1'] else row['pareja1']
                    hora = row['hora_fin'] if row['hora_fin'] else "Recientemente"
                    
                    mensaje = f"¡{ganador} venció a {perdedor} por {row['resultado']}!"
                    
                    html_evento = f'''
                    <div class="feed-card">
                        <div class="feed-icon">🏆</div>
                        <div class="feed-content">
                            <div class="feed-msg">{mensaje}</div>
                            <div class="feed-time">{hora}</div>
                        </div>
                    </div>
                    '''
                    st.markdown(html_evento, unsafe_allow_html=True)
            else:
                st.info("Aún no hay partidos finalizados en este torneo.")
        else:
            st.info("No hay torneos activos para mostrar actividad.")

def mostrar_fixture():
    def ir_a_inicio():
        st.session_state.menu_nav = "🏆 Inicio"

    tid = st.session_state.get('id_torneo')
    if tid:
        col_titulo, col_btn = st.columns([3, 1])
        with col_titulo:
            st.header("📅 Cronograma de Partidos")
        with col_btn:
            st.write("") # Espaciador para alinear verticalmente con el título
            st.button("🔙 Volver al Inicio", use_container_width=True, on_click=ir_a_inicio, key="btn_volver_fixture")
        
        # NUEVO: Panel de Estadísticas
        mostrar_estadisticas_torneo(tid)
        
        # 1. Gráfico Visual (Timeline)
        with st.expander("🕒 Horarios Visuales", expanded=False):
            with custom_spinner():
                fig = generar_grafico_timeline(tid)
            
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            else:
                st.info("Aún no se han asignado horarios a los partidos.")
            
        st.markdown("---")
        
        # 2. Lista de Partidos
        with st.expander("📋 Lista de Encuentros", expanded=False):
            # Consulta ampliada para obtener sets individuales y ganador para la lógica visual
            df_fix = cargar_datos(
                "SELECT id, instancia, horario, cancha, pareja1, pareja2, resultado, estado_partido, ganador, set1, set2, set3 FROM partidos WHERE torneo_id = :id ORDER BY horario", 
                {"id": tid}
            )
            
            if df_fix is not None and not df_fix.empty:
                # --- CSS TARJETAS DE PARTIDO ---
                st.markdown("""
                <style>
                    .match-card {
                        background-color: #1A1A1A;
                        border: 1px solid #333;
                        border-radius: 12px;
                        margin-bottom: 15px;
                        overflow: hidden;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                        transition: transform 0.2s, border-color 0.2s;
                    }
                    .match-card:hover {
                        border-color: #39FF14; /* Hover Neón */
                        transform: translateY(-2px);
                    }
                    .match-header {
                        background-color: #000;
                        padding: 8px 15px;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        border-bottom: 1px solid #333;
                        font-size: 0.8rem;
                        color: #888;
                        font-weight: 600;
                        letter-spacing: 0.5px;
                        text-transform: uppercase;
                    }
                    .match-body {
                        padding: 12px;
                    }
                    .match-row {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        padding: 8px 10px;
                        border-radius: 8px;
                        margin-bottom: 4px;
                    }
                    .couple-name {
                        font-weight: 700;
                        font-size: 0.95rem;
                        color: #EEE;
                        white-space: nowrap;
                        overflow: hidden;
                        text-overflow: ellipsis;
                        max-width: 75%;
                    }
                    .scores-container {
                        display: flex;
                        gap: 6px;
                    }
                    .set-score {
                        width: 20px;
                        text-align: center;
                        font-family: 'Courier New', monospace;
                        font-weight: bold;
                        color: #AAA;
                        font-size: 1rem;
                    }
                    
                    /* --- ESTILOS GANADOR (NEÓN) --- */
                    .winner-row {
                        background-color: rgba(0, 255, 0, 0.15);
                    }
                    .winner-text {
                        color: #00FF00 !important;
                        text-shadow: 0 0 8px rgba(0, 255, 0, 0.4);
                    }
                    .winner-score {
                        color: #00FF00 !important;
                    }
                    
                    .time-badge {
                        color: #FF9100; 
                        font-weight: bold;
                        background: rgba(255, 145, 0, 0.1);
                        padding: 2px 6px;
                        border-radius: 4px;
                    }
                </style>
                """, unsafe_allow_html=True)
    
                # Grid de 2 columnas para las tarjetas
                cols = st.columns(2)
                
                for idx, row in df_fix.iterrows():
                    # Datos básicos
                    p1 = row['pareja1']
                    p2 = row['pareja2']
                    ganador = row['ganador']
                    
                    # Lógica de Estilos para Ganador
                    # Si hay ganador y coincide con P1, aplicamos estilos neón
                    p1_class = "winner-row" if (ganador and ganador == p1) else ""
                    p1_text = "winner-text" if (ganador and ganador == p1) else ""
                    p1_score_style = "winner-score" if (ganador and ganador == p1) else ""
    
                    p2_class = "winner-row" if (ganador and ganador == p2) else ""
                    p2_text = "winner-text" if (ganador and ganador == p2) else ""
                    p2_score_style = "winner-score" if (ganador and ganador == p2) else ""
    
                    # Procesar Sets (Desglosar "6-4" en columnas separadas)
                    sets_data = [row['set1'], row['set2'], row['set3']]
                    html_sets_p1 = ""
                    html_sets_p2 = ""
                    
                    for s in sets_data:
                        if s and '-' in str(s):
                            try:
                                parts = str(s).split('-')
                                s1, s2 = parts[0], parts[1]
                                html_sets_p1 += f'<div class="set-score {p1_score_style}">{s1}</div>'
                                html_sets_p2 += f'<div class="set-score {p2_score_style}">{s2}</div>'
                            except:
                                pass
                    
                    # Formateo de Hora (Destacado Naranja)
                    horario_full = "<span style='color:#555'>A conf.</span>"
                    if row['horario']:
                        try:
                            dt = datetime.strptime(row['horario'], "%Y-%m-%d %H:%M")
                            hora_str = dt.strftime("%H:%M")
                            dia_str = dt.strftime("%d/%m")
                            horario_full = f"{dia_str} <span class='time-badge'>{hora_str}</span>"
                        except:
                            horario_full = row['horario']
    
                    # Etiquetas
                    cancha_lbl = row['cancha'] if row['cancha'] else "Central"
                    instancia_lbl = row['instancia'][:15].upper() if row['instancia'] else "ZONA"
    
                    # Construcción de la Tarjeta HTML
                    html_card = f"""
                    <div class="match-card">
                        <div class="match-header">
                            <div>{instancia_lbl} • {cancha_lbl}</div>
                            <div>{horario_full}</div>
                        </div>
                        <div class="match-body">
                            <!-- Pareja 1 -->
                            <div class="match-row {p1_class}">
                                <div class="couple-name {p1_text}">{p1}</div>
                                <div class="scores-container">{html_sets_p1}</div>
                            </div>
                            <!-- Pareja 2 -->
                            <div class="match-row {p2_class}">
                                <div class="couple-name {p2_text}">{p2}</div>
                                <div class="scores-container">{html_sets_p2}</div>
                            </div>
                        </div>
                    </div>
                    """
                    
                    # Renderizado en columna correspondiente
                    with cols[idx % 2]:
                        st.markdown(html_card, unsafe_allow_html=True)
                        
            else:
                st.info("No hay fixture generado.")
            
        st.markdown("---")
        
        # 3. Llaves / Playoffs
        with st.expander("🏆 Cuadro Final", expanded=False):
            mostrar_cuadro_playoff(tid)
    else:
        st.warning("Selecciona un torneo para ver el fixture.")

def mostrar_posiciones():
        tid = st.session_state.get('id_torneo')
        if tid:
            st.header("📊 Tablas de Posiciones")
            
            # Cargar zonas persistentes
            df_zonas = cargar_datos(
                "SELECT * FROM zonas_posiciones WHERE torneo_id = :id ORDER BY nombre_zona ASC, pts DESC, ds DESC, dg DESC, pg DESC", 
                {"id": tid}
            )
            
            if df_zonas is None:
                st.error("Error al cargar datos de zonas.")
                st.stop()
                
            if df_zonas.empty:
                st.info("Las zonas no han sido sorteadas para este torneo.")
            else:
                css_pos = """
                <style>
                .pos-card{background-color:#1A1A1A;border:1px solid #333;border-radius:12px;padding:15px;margin-bottom:20px;box-shadow:0 4px 6px rgba(0,0,0,0.3); overflow-x:auto;}
                .pos-zone-header{color:#00FF00;font-family:'Segoe UI',sans-serif;font-size:1.1rem;font-weight:800;text-transform:uppercase;margin-bottom:12px;border-bottom:2px solid #333;padding-bottom:5px;display:flex;justify-content:space-between}
                .pos-table{width:100%;border-collapse:collapse;font-family:'Segoe UI',sans-serif;font-size:0.85rem;color:#E0E0E0}
                .pos-table th{text-align:center;color:#888;font-weight:600;padding:8px 2px;border-bottom:1px solid #444;font-size:0.75rem;text-transform:uppercase}
                .pos-table td{text-align:center;padding:10px 2px;border-bottom:1px solid #222}
                .col-left{text-align:left !important;width:35%}
                .qualified-row{background-color:rgba(144,238,144,0.05)}
                .qualified-name{color:#90EE90;font-weight:bold;text-shadow:0 0 5px rgba(144,238,144,0.2)}
                .pos-points{color:white;font-weight:900;font-size:1rem}
                @media (max-width: 768px) {
                    .hide-mob { display: none; }
                    .pos-table th, .pos-table td { padding: 6px 1px; font-size: 0.75rem; }
                    .col-left { width: 50%; }
                }
                </style>
                """
                st.markdown(css_pos, unsafe_allow_html=True)

                # Cargamos todos los partidos finalizados de la fase de zonas
                df_partidos_torneo = cargar_datos(
                    "SELECT pareja1, pareja2, ganador FROM partidos WHERE torneo_id = :id AND instancia = 'Zona' AND estado_partido = 'Finalizado' ORDER BY id ASC", 
                    {"id": tid}
                )

                grupos = df_zonas.groupby('nombre_zona')
                cols = st.columns(2)
                idx = 0
                
                for nombre, df_grupo in grupos:
                    # Reordenamiento explícito en Pandas
                    df_grupo = df_grupo.sort_values(by=['pts', 'ds', 'dg', 'pg'], ascending=[False, False, False, False])
                    
                    # --- SISTEMA DE ELIMINACIÓN MODIFICADA (ZONAS DE 4 CON 4 PARTIDOS JUGADOS) ---
                    if len(df_grupo) == 4 and df_partidos_torneo is not None and not df_partidos_torneo.empty:
                        parejas_zona = df_grupo['pareja'].tolist()
                        
                        # Filtramos los partidos donde ambos competidores pertenezcan a esta zona en particular
                        partidos_zona = df_partidos_torneo[
                            df_partidos_torneo['pareja1'].isin(parejas_zona) & 
                            df_partidos_torneo['pareja2'].isin(parejas_zona)
                        ]
                        
                        if len(partidos_zona) == 4:
                            cruce1 = partidos_zona.iloc[0]
                            cruce2 = None
                            for idx in range(1, 4):
                                p = partidos_zona.iloc[idx]
                                if p['pareja1'] not in [cruce1['pareja1'], cruce1['pareja2']] and p['pareja2'] not in [cruce1['pareja1'], cruce1['pareja2']]:
                                    cruce2 = p
                                    break
                            
                            if cruce1 is not None and cruce2 is not None:
                                ganador_c1 = cruce1['ganador']
                                ganador_c2 = cruce2['ganador']
                                perdedor_c1 = cruce1['pareja2'] if ganador_c1 == cruce1['pareja1'] else cruce1['pareja1']
                                perdedor_c2 = cruce2['pareja2'] if ganador_c2 == cruce2['pareja1'] else cruce2['pareja1']

                                partido_ganadores = None
                                partido_perdedores = None

                                for idx in range(4):
                                    p = partidos_zona.iloc[idx]
                                    if p.name in [cruce1.name, cruce2.name]: continue
                                    if p['pareja1'] in [ganador_c1, ganador_c2] and p['pareja2'] in [ganador_c1, ganador_c2]:
                                        partido_ganadores = p
                                    if p['pareja1'] in [perdedor_c1, perdedor_c2] and p['pareja2'] in [perdedor_c1, perdedor_c2]:
                                        partido_perdedores = p

                                if partido_ganadores is not None and partido_perdedores is not None:
                                    puesto_1 = partido_ganadores['ganador']
                                    puesto_2 = partido_ganadores['pareja1'] if partido_ganadores['pareja2'] == puesto_1 else partido_ganadores['pareja2']
                                    
                                    puesto_3 = partido_perdedores['ganador']
                                    puesto_4 = partido_perdedores['pareja1'] if partido_perdedores['pareja2'] == puesto_3 else partido_perdedores['pareja2']
                                    
                                    # Forzamos el orden exacto manteniendo intactas las demás columnas para no romper los playoffs
                                    orden_forzado = [puesto_1, puesto_2, puesto_3, puesto_4]
                                    # Creamos una columna temporal de índice basada en el orden, ordenamos y la eliminamos
                                    df_grupo['orden_especial'] = df_grupo['pareja'].map(lambda x: orden_forzado.index(x) if x in orden_forzado else 99)
                                    df_grupo = df_grupo.sort_values('orden_especial').drop(columns=['orden_especial'])
                    
                    with cols[idx % 2]:
                        # CONSTRUCCIÓN BLINDADA CON TODAS LAS COLUMNAS
                        html_table = f'<div class="pos-card"><div class="pos-zone-header"><span>{nombre}</span><span>🏆</span></div><table class="pos-table"><thead><tr><th class="col-left">PAREJA</th><th>PJ</th><th>PG</th><th class="hide-mob">PP</th><th class="hide-mob">SF</th><th class="hide-mob">SC</th><th>DS</th><th>DG</th><th>PTS</th></tr></thead><tbody>'
                        
                        for i, row in enumerate(df_grupo.itertuples()):
                            limite_clasificados = 3 if len(df_grupo) == 4 else 2
                            is_qualified = i < limite_clasificados
                            row_class = "qualified-row" if is_qualified else ""
                            name_class = "qualified-name" if is_qualified else ""
                            check = "✅" if is_qualified else ""
                            
                            # Fila en una sola línea agregando todas las estadísticas
                            fila = f'<tr class="{row_class}"><td class="col-left {name_class}">{row.pareja} <span style="font-size:0.7rem;">{check}</span></td><td>{row.pj}</td><td>{row.pg}</td><td class="hide-mob">{row.pp}</td><td class="hide-mob">{row.sf}</td><td class="hide-mob">{row.sc}</td><td>{row.ds}</td><td style="color:#666;">{row.dg}</td><td class="pos-points">{row.pts}</td></tr>'
                            html_table += fila
                            
                        html_table += '</tbody></table></div>'
                        
                        # APLASTAMIENTO FINAL (Opción Nuclear)
                        html_table = " ".join(html_table.split())
                        
                        st.markdown(html_table, unsafe_allow_html=True)
                    idx += 1
        else:
            st.warning("Selecciona un torneo para ver posiciones.")
    

def mostrar_sede():
    mostrar_seccion_sede()

def mostrar_panel_admin():
    if not st.session_state.es_admin:
        st.error("Acceso denegado. Inicia sesión como administrador.")
    else:
        st.header("⚙️ Panel de Administración")
        
        # TAREA 1: Borrador de Emergencia
        with st.expander("🚨 Zona de Peligro (Fix Emergencia)"):
            st.warning("Usar solo si el Torneo ID 4 está causando conflictos.")
            if st.button("🗑️ ELIMINAR TORNEO ID 4 (Borrador de Emergencia)"):
                 run_action('DELETE FROM torneos WHERE id = 4')
                 run_action('DELETE FROM inscripciones WHERE torneo_id = 4')
                 st.success('Torneo 4 eliminado correctamente')
                 st.cache_data.clear()
                 time.sleep(1)
                 st.rerun()
        
        verificador_cupos()
        
        tab_gestion_torneo, tab_validaciones, tab_transferencias, tab_admin_gral, tab_admin_fotos, tab_carga_puntos, tab_admin_socios, tab_control_vivo = st.tabs(["🏆 Gestión de Torneo", "✅ Inscripciones por Validar", "🔄 Transferencias", "🔧 Configuración General", "📷 Gestión de Fotos", "📊 Carga de Puntos", "👥 Administración de Socios", "⚡ Control en Vivo"])
        
        with tab_gestion_torneo:
            st.markdown("""
            <style>
                .admin-card {
                    background-color: #000000;
                    border: 2px solid #00C853;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 0 10px rgba(0, 200, 83, 0.5);
                    margin-bottom: 20px;
                }
                .stTextInput input {
                    border: 1px solid #333;
                }
            </style>
            """, unsafe_allow_html=True)
            
            st.markdown("<div class='admin-card'>", unsafe_allow_html=True)
            st.subheader("🚀 Activar Nuevo Torneo")
            
            # Inicializar keys para limpieza de inputs
            if 'admin_t_nombre' not in st.session_state: st.session_state.admin_t_nombre = ""
            if 'admin_t_cat_custom' not in st.session_state: st.session_state.admin_t_cat_custom = ""
            if 'uploader_key' not in st.session_state: st.session_state.uploader_key = 0

            n_torneo = st.text_input("Nombre del Torneo", placeholder="Ej: Suma 13 - Apertura", key="admin_t_nombre")
            f_evento = st.date_input("Fecha del Evento", min_value=datetime.today())
            
            # Selector de rango horario
            c_hora1, c_hora2 = st.columns(2)
            h_inicio = c_hora1.time_input("Hora de Inicio", value=datetime.strptime("09:00", "%H:%M").time())
            h_fin = c_hora2.time_input("Hora de Fin", value=datetime.strptime("23:00", "%H:%M").time())
            # RECORDATORIO: El complejo tiene una sola cancha, por lo que la lógica futura de partidos deberá respetar ese bloque horario estricto
            
            cats = ["Libre", "3ra", "4ta", "5ta", "6ta", "7ma", "8va", "Suma 12", "Suma 13", "Otra (Escribir nueva...)"]
            c_torneo_sel = st.selectbox("Categoría", cats)
            
            c_torneo_final = c_torneo_sel
            if c_torneo_sel == "Otra (Escribir nueva...)":
                c_torneo_final = st.text_input("Nombre de la Categoría Nueva", placeholder="Ej: Suma 15", key="admin_t_cat_custom")
            
            es_puntuable = st.checkbox("¿Asigna Puntos al Ranking?", value=True, key="check_puntuable_new")
            
            # Configuración Tie-break
            use_stb = st.checkbox("Habilitar Super Tie-break (3er Set)", value=False)
            pts_stb = st.number_input("Puntos Super Tie-break", value=10, min_value=1) if use_stb else 10
            
            afiche_nuevo = st.file_uploader("Subir Afiche (Opcional)", type=['jpg', 'png', 'jpeg'], key=f"afiche_{st.session_state.uploader_key}")
            
            if st.button("🚀 ACTIVAR TORNEO"):
                if n_torneo and c_torneo_final:
                    new_id = crear_torneo(n_torneo, f_evento, c_torneo_final, es_puntuable, use_stb, pts_stb)
                    
                    if new_id and afiche_nuevo:
                        if not os.path.exists("assets"):
                            os.makedirs("assets")
                        file_path = os.path.join("assets", afiche_nuevo.name)
                        with open(file_path, "wb") as f:
                            f.write(afiche_nuevo.getbuffer())
                        
                        run_action("INSERT INTO eventos (torneo_id, afiche) VALUES (%(torneo_id)s, %(afiche)s)", {"torneo_id": new_id, "afiche": file_path})

                    st.success("✅ Torneo creado y guardado exitosamente.")
                    # Limpiar inputs
                    st.session_state.uploader_key += 1
                    st.rerun()
                else:
                    st.warning("⚠️ El nombre del torneo y la categoría son obligatorios.")
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("<div class='admin-card'>", unsafe_allow_html=True)
            st.subheader("🏆 Configuración de Torneo Activo")
            
            # Permitir gestionar torneos 'Abierto', 'En Juego' e 'Inactivo' (sin cache)
            # Usamos cargar_datos para evitar caché y asegurar que los IDs correspondan al estado real de la DB
            all_active_tournaments = cargar_datos("SELECT * FROM torneos WHERE estado IN ('Abierto', 'En Juego', 'Inactivo') ORDER BY id DESC")
            
            if all_active_tournaments is not None and not all_active_tournaments.empty:
                # Mapa de IDs a Nombres. Usamos int() explícito para las claves para evitar errores de tipo numpy/int
                torneo_dict = {int(row['id']): f"{row['nombre']} ({row['categoria']}) - {row['estado']}" for _, row in all_active_tournaments.iterrows()}

                # --- GESTIÓN DE ESTADO ROBUSTA ---
                # Si el ID guardado no existe (fue borrado) o no está inicializado, reseteamos al primero de la lista.
                if 'admin_id_torneo' not in st.session_state or st.session_state.admin_id_torneo not in torneo_dict:
                    st.session_state.admin_id_torneo = int(all_active_tournaments.iloc[0]['id'])

                # Selector vinculado directamente a la sesión. Streamlit maneja la actualización automáticamente.
                st.selectbox(
                    "Seleccionar Torneo Activo", 
                    options=list(torneo_dict.keys()),
                    format_func=lambda x: torneo_dict.get(x, f"ID: {x}"),
                    key="admin_id_torneo" # Vinculación directa
                )
                
                # Ahora, la fuente de verdad es siempre st.session_state.admin_id_torneo
                id_real = st.session_state.admin_id_torneo
                
                t_data = all_active_tournaments[all_active_tournaments['id'] == id_real].iloc[0]
                
                # Persistir categoría para filtros estables
                st.session_state.admin_cat_torneo = t_data['categoria']
                
                # --- FORMULARIO DE EDICIÓN ---
                c1, c2 = st.columns(2)
                new_name = c1.text_input("Nombre del Torneo", value=t_data['nombre'])
                
                # Configuración de fechas (Rango)
                val_fechas = []
                try:
                    d = datetime.strptime(t_data['fecha'], "%Y-%m-%d")
                    val_fechas = [d, d]
                except:
                    val_fechas = [datetime.now(), datetime.now()]

                new_date = c2.date_input("Fecha (Seleccionar Rango)", value=val_fechas)
                
                cat_options = ["Libre", "3ra", "4ta", "5ta", "6ta", "7ma", "8va", "Suma 12", "Suma 13"]
                curr_cat_idx = cat_options.index(t_data['categoria']) if t_data['categoria'] in cat_options else 0
                new_cat = st.selectbox("Categoría", cat_options, index=curr_cat_idx, key=f"edit_cat_{id_real}")
                
                val_puntuable = True
                if 'es_puntuable' in t_data and t_data['es_puntuable'] == 0:
                    val_puntuable = False
                edit_es_puntuable = st.checkbox("¿Asigna Puntos al Ranking?", value=val_puntuable, key="check_puntuable_edit")
                
                # Configuración Tie-break Edit
                val_stb = True if t_data.get('super_tiebreak', 0) == 1 else False
                edit_stb = st.checkbox("Habilitar Super Tie-break", value=val_stb, key="edit_stb")
                edit_pts_stb = st.number_input("Puntos STB", value=t_data.get('puntos_tiebreak', 10), key="edit_pts_stb") if edit_stb else 10
                
                st.markdown("---")
                st.write("📸 **Afiche Promocional**")
                afiche_file = st.file_uploader("Subir imagen (JPG/PNG)", type=['jpg', 'png', 'jpeg'])
                
                st.markdown("---")
                
                # --- BOTONES DE GESTIÓN ---
                c_save, c_state, c_del = st.columns(3)
                
                # 1. GUARDAR
                with c_save:
                    if st.button("💾 Guardar Cambios", type="primary", use_container_width=True):
                        fecha_str = t_data['fecha']
                        if isinstance(new_date, (list, tuple)):
                            if len(new_date) == 2:
                                ini, fin = new_date
                                fecha_str = f"{ini.strftime('%d/%m')} al {fin.strftime('%d/%m')}"
                            elif len(new_date) == 1:
                                ini = new_date[0]
                                fecha_str = f"{ini.strftime('%d/%m')} al {ini.strftime('%d/%m')}"

                        run_action("UPDATE torneos SET nombre=%(nombre)s, fecha=%(fecha)s, categoria=%(categoria)s, es_puntuable=%(es_puntuable)s, super_tiebreak=%(stb)s, puntos_tiebreak=%(ptb)s WHERE id=%(id)s", {"nombre": new_name, "fecha": fecha_str, "categoria": new_cat, "es_puntuable": 1 if edit_es_puntuable else 0, "stb": 1 if edit_stb else 0, "ptb": edit_pts_stb, "id": id_real})
                        
                        if afiche_file:
                            if not os.path.exists("assets"):
                                os.makedirs("assets")
                            file_path = os.path.join("assets", afiche_file.name)
                            with open(file_path, "wb") as f:
                                f.write(afiche_file.getbuffer())
                            
                            df_ev = cargar_datos("SELECT id FROM eventos WHERE torneo_id=:torneo_id", {"torneo_id": id_real})
                            if df_ev is not None and not df_ev.empty:
                                run_action("UPDATE eventos SET afiche=%(afiche)s WHERE torneo_id=%(torneo_id)s", {"afiche": file_path, "torneo_id": id_real})
                            else:
                                run_action("INSERT INTO eventos (torneo_id, afiche) VALUES (%(torneo_id)s, %(afiche)s)", {"torneo_id": id_real, "afiche": file_path})
                        
                        st.toast("✅ Cambios guardados correctamente", icon="💾")
                        limpiar_cache()
                        time.sleep(1)
                        st.rerun()

                # 2. ACTIVAR / DESACTIVAR
                with c_state:
                    if t_data['estado'] == 'Inactivo':
                        if st.button("▶️ Activar Torneo", use_container_width=True):
                            run_action("UPDATE torneos SET estado = 'Abierto' WHERE id = %(id)s", {"id": id_real})
                            st.toast("✅ Torneo Activado", icon="👁️")
                            limpiar_cache()
                            time.sleep(1)
                            st.rerun()
                    else:
                        if st.button("⏸️ Desactivar Torneo", use_container_width=True):
                            run_action("UPDATE torneos SET estado = 'Inactivo' WHERE id = %(id)s", {"id": id_real})
                            st.toast("⏸️ Torneo Desactivado", icon="🙈")
                            limpiar_cache()
                            time.sleep(1)
                            st.rerun()

                # 3. ELIMINAR
                with c_del:
                    confirm_del = st.checkbox("Confirmar Borrado", key="chk_del_torneo")
                    if st.button("🗑️ Eliminar Torneo", type="secondary", disabled=not confirm_del, use_container_width=True):
                        run_action("DELETE FROM partidos WHERE torneo_id = %(id)s", {"id": id_real})
                        run_action("DELETE FROM inscripciones WHERE torneo_id = %(id)s", {"id": id_real})
                        run_action("DELETE FROM zonas WHERE torneo_id = %(id)s", {"id": id_real})
                        run_action("DELETE FROM zonas_posiciones WHERE torneo_id = %(id)s", {"id": id_real})
                        run_action("DELETE FROM eventos WHERE torneo_id = %(id)s", {"id": id_real})
                        run_action("DELETE FROM ranking_puntos WHERE torneo_id = %(id)s", {"id": id_real})
                        run_action("DELETE FROM partido_en_vivo WHERE torneo = %(nombre)s", {"nombre": t_data['nombre']})
                        run_action("DELETE FROM torneos WHERE id = %(id)s", {"id": id_real})
                        
                        st.toast("🗑️ Torneo eliminado correctamente.", icon="🗑️")
                        limpiar_cache()
                        time.sleep(1)
                        st.rerun()

                st.markdown("---")
                
                # --- GESTION DE SPONSORS ---
                gestionar_sponsors_admin(id_real)

                st.markdown("---")
                
                # --- BAJA DE PAREJAS ---
                st.subheader("⬇️ Dar de Baja Pareja (Inscripciones Validadas)")
                st.write("Usa esta opción si una pareja abandona el torneo antes del sorteo de zonas.")
                
                # Obtenemos solo las parejas validadas del torneo actual
                df_bajas = cargar_datos("SELECT id, jugador1, jugador2 FROM inscripciones WHERE torneo_id = :tid AND estado_validacion = 'Validado'", {"tid": id_real})
                
                if df_bajas is not None and not df_bajas.empty:
                    opts_baja = {row['id']: f"{row['jugador1']} - {row['jugador2']}" for _, row in df_bajas.iterrows()}
                    
                    baja_sel = st.selectbox("Seleccionar pareja a dar de baja", options=list(opts_baja.keys()), format_func=lambda x: opts_baja[x])
                    
                    with st.expander("⚠️ Confirmar Borrado Definitivo", expanded=False):
                        st.write("Estás a punto de dar de baja y borrar de la base de datos a la pareja:")
                        st.markdown(f"<h3 style='color: #FF4B4B; text-align: center;'>{opts_baja[baja_sel]}</h3>", unsafe_allow_html=True)
                        st.warning("Esta acción es irreversible y liberará un cupo en el torneo. ¿Estás seguro de que deseas continuar?")
                        if st.button("Sí, eliminar definitivamente", type="primary", use_container_width=True):
                            eliminar_pareja_torneo(baja_sel, id_real)
                            st.cache_data.clear()
                            st.success("Pareja eliminada definitivamente del torneo.")
                            time.sleep(1.5)
                            st.rerun()
                else:
                    st.info("No hay parejas validadas para dar de baja en este torneo.")

                st.markdown("---")

                # --- FASE PREVIA: GESTIÓN DE ZONAS ---
                st.subheader("2. Fase Previa: Gestión de Zonas")
                if t_data['estado'] == 'Abierto':
                    # Obtener inscriptos validados para la categoría del torneo
                    df_insc_man = cargar_datos("SELECT jugador1, jugador2, estado_validacion, categoria FROM inscripciones WHERE torneo_id = :torneo_id", params={"torneo_id": int(id_real)})

                    if df_insc_man is not None and not df_insc_man.empty:
                        df_insc_man = df_insc_man[df_insc_man['estado_validacion'].astype(str).str.lower() == 'validado']
                        cat_torneo_norm = str(st.session_state.admin_cat_torneo).strip().lower()
                        df_insc_man = df_insc_man[df_insc_man['categoria'].astype(str).str.strip().str.lower() == cat_torneo_norm]
                    
                    parejas_total = [f"{row['jugador1']} - {row['jugador2']}" for _, row in df_insc_man.iterrows()]
                    
                    # Obtener parejas ya asignadas a una zona
                    df_asignados = cargar_datos("SELECT pareja FROM zonas WHERE torneo_id = :torneo_id", params={"torneo_id": int(id_real)})
                    asignados = df_asignados['pareja'].tolist() if (df_asignados is not None and not df_asignados.empty) else []
                    
                    # Filtrar para obtener solo las parejas disponibles para asignación manual
                    disponibles = [p for p in parejas_total if p not in asignados]


                    c_z1, c_z2 = st.columns(2)
                    with c_z1:
                        st.subheader("Opción A: Sorteo Automático")
                        
                        # --- SOLUCIÓN PROBLEMA 1: Selector de Preferencia ---
                        pref_zona = st.radio("Tamaño Preferido de Zona", [3, 4], index=1, horizontal=True, help="El sistema intentará armar la mayor cantidad de grupos de este tamaño.")
                        
                        if st.button("🎲 Generar Zonas Aleatorias", key="btn_sorteo_admin"):
                            # Usamos variables estables
                            success, msg = generar_zonas(id_real, st.session_state.admin_cat_torneo, pref_tamano=pref_zona)
                            
                            if success:
                                st.success("¡Zonas generadas con éxito!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(msg)
                    with c_z2:
                        st.subheader("Opción B: Asignación Manual")

                        # 3. Formulario de Asignación
                        with st.form("form_zona_manual"):
                            z_letras = [f"Zona {l}" for l in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]
                            sel_zona_man = st.selectbox("Seleccionar Zona", z_letras)
                            # Key dinámica basada en id_safe para limpiar al cambiar de torneo
                            sel_parejas_man = st.multiselect("Seleccionar Parejas Disponibles", disponibles, key=f"sel_parejas_{id_real}")
                            
                            if st.form_submit_button("💾 Asignar a Zona"):
                                if sel_parejas_man:
                                    for p in sel_parejas_man:
                                        # Insertar en Zonas y Posiciones
                                        run_action("INSERT INTO zonas (torneo_id, nombre_zona, pareja) VALUES (%(torneo_id)s, %(nombre_zona)s, %(pareja)s)", {"torneo_id": int(id_real), "nombre_zona": sel_zona_man, "pareja": p})
                                        run_action("INSERT INTO zonas_posiciones (torneo_id, nombre_zona, pareja) VALUES (%(torneo_id)s, %(nombre_zona)s, %(pareja)s)", {"torneo_id": int(id_real), "nombre_zona": sel_zona_man, "pareja": p})
                                    st.success(f"Asignados {len(sel_parejas_man)} parejas a {sel_zona_man}")
                                    limpiar_cache()
                                    st.rerun()
                                else:
                                    st.warning("Selecciona al menos una pareja.")
                        
                        # 4. Acciones Globales
                        c_conf, c_reset = st.columns(2)
                        if c_conf.button("✅ Confirmar Todas", help="Generar Fixture"):
                             if (df_asignados is not None and not df_asignados.empty) or len(asignados) > 0:
                                 ok, msg = generar_partidos_desde_zonas_existentes(int(id_real))
                                 if ok:
                                     st.success(msg)
                                     time.sleep(1)
                                     st.rerun()
                                 else:
                                     st.error(msg)
                             else:
                                 st.error("No hay zonas creadas.")
                        
                        if c_reset.button("🗑️ Resetear", help="Borrar todas las zonas"):
                            run_action("DELETE FROM zonas WHERE torneo_id = %(torneo_id)s", {"torneo_id": int(id_real)})
                            run_action("DELETE FROM zonas_posiciones WHERE torneo_id = %(torneo_id)s", {"torneo_id": int(id_real)})
                            run_action("DELETE FROM partidos WHERE torneo_id = %(torneo_id)s AND instancia = 'Zona'", {"torneo_id": int(id_real)})
                            limpiar_cache()
                            st.rerun()
                else:
                    st.info("El torneo ya está en juego. Las zonas no se pueden modificar.")
                
                # Visualización de Zonas Generadas
                df_zonas_admin = cargar_datos("SELECT * FROM zonas WHERE torneo_id = :torneo_id ORDER BY nombre_zona", params={"torneo_id": id_real})
                if df_zonas_admin is not None and not df_zonas_admin.empty:
                    st.markdown("##### 📋 Vista Previa de Zonas")
                    grupos = df_zonas_admin.groupby('nombre_zona')
                    cols_z = st.columns(3)
                    for i, (nombre, grupo) in enumerate(grupos):
                        with cols_z[i % 3]:
                            st.info(f"**{nombre}**")
                            for _, row in grupo.iterrows():
                                st.caption(f"• {row['pareja']}")

                st.markdown("---")
                # --- BOTÓN INICIAR TORNEO ---
                st.subheader("3. Iniciar Competencia")
                if t_data['estado'] == 'Abierto':
                    st.warning("⚠️ Al iniciar el torneo se cerrarán las inscripciones y se habilitará la carga de resultados.")
                    if st.button("🚀 INICIAR TORNEO", type="primary", use_container_width=True):
                        iniciar_torneo(id_real)
                        st.success("¡Torneo Iniciado! Ahora puedes gestionar los partidos en 'Control en Vivo'.")
                        st.rerun()
                else:
                    st.success("✅ Torneo En Curso")
                
                st.markdown("---")
                st.subheader("📅 Generador de Fixture Automático")
                st.write("Define los rangos horarios para cada día del torneo. El sistema distribuirá los partidos de zona automáticamente.")
                
                # Parse tournament dates
                tournament_dates = []
                date_str = t_data['fecha']
                anio_actual = datetime.now().year
                
                if " al " in str(date_str):
                    try:
                        inicio_str, fin_str = date_str.split(" al ")
                        f_ini = datetime.strptime(f"{inicio_str}/{anio_actual}", "%d/%m/%Y").date()
                        f_fin = datetime.strptime(f"{fin_str}/{anio_actual}", "%d/%m/%Y").date()
                        
                        if f_fin < f_ini:
                            f_fin = f_fin.replace(year=anio_actual + 1)
                            
                        delta = f_fin - f_ini
                        for i in range(delta.days + 1):
                            tournament_dates.append(f_ini + timedelta(days=i))
                    except ValueError:
                        st.warning(f"No se pudo interpretar el rango de fechas '{date_str}'. Usando fecha de hoy.")
                        tournament_dates = [datetime.today().date()]
                else:
                    try:
                        tournament_dates = [datetime.strptime(date_str, "%Y-%m-%d").date()]
                    except ValueError:
                        st.warning(f"No se pudo interpretar la fecha '{date_str}'. Usando fecha de hoy.")
                        tournament_dates = [datetime.today().date()]

                # UI for time ranges
                programacion_dias = []
                for dia in tournament_dates:
                    st.markdown(f"**Día: {dia.strftime('%A, %d de %B')}**")
                    cols = st.columns(2)
                    h_inicio = cols[0].time_input("Hora de Inicio", value=datetime.strptime("14:00", "%H:%M").time(), key=f"start_{dia}")
                    h_fin = cols[1].time_input("Hora de Fin", value=datetime.strptime("23:00", "%H:%M").time(), key=f"end_{dia}")
                    if h_inicio >= h_fin:
                        st.error("La hora de fin debe ser posterior a la hora de inicio.")
                    programacion_dias.append({'fecha': dia, 'inicio': h_inicio, 'fin': h_fin})
                
                if st.button("🚀 Generar Horarios"):
                    if any(d['inicio'] >= d['fin'] for d in programacion_dias):
                        st.error("Corrige los rangos horarios inválidos (inicio debe ser antes que fin) antes de generar el fixture.")
                    else:
                        success, msg = generar_fixture_automatico(id_real, programacion_dias)
                        if success:
                            st.success(msg)
                        else:
                            st.error(msg)
                
                st.markdown("---")
                st.subheader("🛠️ Edición Manual de Horarios")
                
                # Nuevas funciones implementadas
                cronograma_visual(id_real)
                seccion_gestion_horarios(id_real)
                seccion_carga_resultados(id_real)
                
                st.markdown("---")
                st.subheader("4. Fase Final: Playoffs")
                
                tipo_cierre = st.radio("Modo de cierre", ["Cierre Automático", "Cierre Manual", "Armado Manual de Llaves"], horizontal=True)
                manual_positions = {}
                
                if tipo_cierre == "Cierre Manual":
                    st.info("Asigna manualmente las posiciones de cada zona. Los no seleccionados quedarán eliminados.")
                    df_z_admin = cargar_datos("SELECT nombre_zona, pareja FROM zonas WHERE torneo_id = :tid ORDER BY nombre_zona", {"tid": id_real})
                    if df_z_admin is not None and not df_z_admin.empty:
                        for z_name, df_g in df_z_admin.groupby('nombre_zona'):
                            parejas_zona = df_g['pareja'].tolist()
                            st.markdown(f"**{z_name}**")
                            c1, c2, c3 = st.columns(3)
                            p1 = c1.selectbox(f"1º {z_name}", ["(Ninguno)"] + parejas_zona, key=f"m1_{z_name}_{id_real}")
                            p2_opts = ["(Ninguno)"] + [p for p in parejas_zona if p != p1 or p1 == "(Ninguno)"]
                            p2 = c2.selectbox(f"2º {z_name}", p2_opts, key=f"m2_{z_name}_{id_real}")
                            p3_opts = ["(Ninguno)"] + [p for p in parejas_zona if p not in (p1, p2) or (p == "(Ninguno)")]
                            p3 = c3.selectbox(f"3º {z_name}", p3_opts, key=f"m3_{z_name}_{id_real}")
                            manual_positions[z_name] = [p1, p2, p3]
                elif tipo_cierre == "Armado Manual de Llaves":
                    st.info("Configura los cruces manualmente asignando parejas a cada posición del cuadro.")
                    
                    clasificados_base = []
                    df_z_pos = cargar_datos("SELECT nombre_zona, pareja, pts, ds, dg, pg FROM zonas_posiciones WHERE torneo_id = :t_id ORDER BY pts DESC, ds DESC, dg DESC, pg DESC", {"t_id": id_real})
                    if df_z_pos is not None and not df_z_pos.empty:
                        zonas_dict = {}
                        for _, row in df_z_pos.iterrows():
                            z = row['nombre_zona']
                            if z not in zonas_dict: zonas_dict[z] = []
                            zonas_dict[z].append(row)
                            
                        terceros = []
                        for z, equipos in zonas_dict.items():
                            z_letra = z.replace("Zona ", "").strip()
                            equipos_sorted = sorted(equipos, key=lambda x: (x['pts'], x['ds'], x['dg'], x['pg']), reverse=True)
                            if len(equipos_sorted) >= 1: clasificados_base.append(f"1{z_letra} - {equipos_sorted[0]['pareja']}")
                            if len(equipos_sorted) >= 2: clasificados_base.append(f"2{z_letra} - {equipos_sorted[1]['pareja']}")
                            if len(equipos_sorted) >= 3:
                                if len(equipos_sorted) == 4:
                                    clasificados_base.append(f"3{z_letra} - {equipos_sorted[2]['pareja']}")
                                else:
                                    terceros.append((f"3{z_letra} - {equipos_sorted[2]['pareja']}", equipos_sorted[2]))
                        
                        num_clasificados = len(clasificados_base)
                        target_size_calc = 4
                        if num_clasificados > 4: target_size_calc = 8
                        if num_clasificados > 8: target_size_calc = 16
                        if num_clasificados > 16: target_size_calc = 32
                        
                        slots_needed = target_size_calc - num_clasificados
                        terceros.sort(key=lambda x: (x[1]['pts'], x[1]['ds'], x[1]['dg'], x[1]['pg']), reverse=True)
                        while slots_needed > 0 and len(terceros) > 0:
                            clasificados_base.append(terceros.pop(0)[0])
                            slots_needed -= 1
                    else:
                        df_insc = cargar_datos("SELECT jugador1, jugador2 FROM inscripciones WHERE torneo_id = :tid", {"tid": id_real})
                        if df_insc is not None and not df_insc.empty:
                            clasificados_base = [f"{row['jugador1']} - {row['jugador2']}" for _, row in df_insc.iterrows()]
                        target_size_calc = 8
                        
                    opciones_size = [4, 8, 16, 32]
                    size_idx = opciones_size.index(target_size_calc) if target_size_calc in opciones_size else 1
                    target_size_sel = st.selectbox("Tamaño del Cuadro (Clasificados calculados: {})".format(len(clasificados_base)), opciones_size, index=size_idx)
                    
                    instancia = "Cuartos"
                    start_pos = 9
                    if target_size_sel == 16:
                        instancia = "Octavos"
                        start_pos = 1
                    elif target_size_sel == 4:
                        instancia = "Semis"
                        start_pos = 13
                    elif target_size_sel == 32:
                        instancia = "16avos"
                        start_pos = -15 
                        
                    st.markdown(f"#### Armado de {instancia}")
                    opciones_parejas = ["BYE", "Vacío"] + clasificados_base
                    
                    num_partidos = target_size_sel // 2
                    cruces_armados = []
                    
                    cols = st.columns(2)
                    for i in range(num_partidos):
                        with cols[i % 2]:
                            st.markdown(f"**Partido {i+1}**")
                            p1 = st.selectbox(f"Pareja 1 (P{i+1})", opciones_parejas, key=f"am_p1_{i}_{id_real}")
                            p2 = st.selectbox(f"Pareja 2 (P{i+1})", opciones_parejas, key=f"am_p2_{i}_{id_real}")
                            cruces_armados.append((p1, p2))
                            st.write("")
                            
                    if st.button("💾 Guardar Cuadro Manual", type="primary"):
                        df_check = cargar_datos("SELECT count(*) as c FROM partidos WHERE torneo_id = :t_id AND instancia IN ('Octavos', 'Cuartos', 'Semis', 'Final')", {"t_id": id_real})
                        if df_check is not None and not df_check.empty and df_check.iloc[0]['c'] > 0:
                            st.error("Ya existen partidos de playoff. Por favor limpia los partidos de zona/bracket antes de generar uno nuevo.")
                        else:
                            count = 0
                            for i, (p1, p2) in enumerate(cruces_armados):
                                bp = start_pos + i
                                estado = 'Próximo'
                                res = ''
                                ganador = None
                                
                                if p1 == "BYE" and p2 not in ["BYE", "Vacío"]:
                                    estado = 'Finalizado'
                                    ganador = p2
                                    res = 'BYE'
                                elif p2 == "BYE" and p1 not in ["BYE", "Vacío"]:
                                    estado = 'Finalizado'
                                    ganador = p1
                                    res = 'BYE'
                                elif p1 in ["BYE", "Vacío"] and p2 in ["BYE", "Vacío"]:
                                    estado = 'Finalizado'
                                    res = 'Vacío'
                                    ganador = 'Vacío'
                                
                                p1_db = "" if p1 == "Vacío" else p1
                                p2_db = "" if p2 == "Vacío" else p2
                                    
                                new_id = run_action('''
                                    INSERT INTO partidos (torneo_id, pareja1, pareja2, instancia, estado_partido, bracket_pos)
                                    VALUES (:tid, :p1, :p2, :inst, 'Próximo', :bp) RETURNING id
                                ''', {"tid": id_real, "p1": p1_db, "p2": p2_db, "inst": instancia, "bp": bp}, return_id=True)
                                
                                if ganador:
                                    actualizar_bracket(new_id, id_real, bp, res, ganador)
                                    run_action("UPDATE partidos SET estado_partido = 'Finalizado', resultado = 'Pasa Directo' WHERE id = :id",
                                               {"id": new_id})
                                count += 1
                            limpiar_cache()
                            st.success(f"Cuadro de {instancia} guardado exitosamente con {count} partidos.")
                            time.sleep(1.5)
                            st.rerun()

                # Botón con confirmación segura para lógicas Automáticas/Manual de Zonas
                if tipo_cierre in ["Cierre Automático", "Cierre Manual"]:
                    if 'confirm_playoff' not in st.session_state: st.session_state.confirm_playoff = False
    
                    if st.button("🏆 Finalizar Zonas y Armar Playoff"):
                        st.session_state.confirm_playoff = True
    
                    if st.session_state.confirm_playoff:
                        st.warning("⚠️ ¿Estás seguro? Esta acción generará los cruces eliminatorios.")
                        col_y, col_n = st.columns(2)
                        if col_y.button("✅ Sí, Generar"):
                            m_pos = manual_positions if tipo_cierre == "Cierre Manual" else None
                            ok, msg = cerrar_zonas_y_generar_playoffs(id_real, m_pos)
                            if ok:
                                st.success(msg)
                            else:
                                st.error(msg)
                            st.session_state.confirm_playoff = False
                            time.sleep(1.5)
                            st.rerun()
                        if col_n.button("❌ Cancelar"):
                            st.session_state.confirm_playoff = False
                            st.rerun()
                
                mostrar_cuadro_playoff(id_real)

            else:
                st.info("No hay torneos activos para configurar.")
            st.markdown("</div>", unsafe_allow_html=True)

        with tab_validaciones:
            st.subheader("📋 Inscripciones Pendientes de Validación")
            
            # Mensaje de éxito post-validación (Persistencia temporal)
            if 'val_success' in st.session_state:
                s_data = st.session_state['val_success']
                st.success(f"✅ ¡Pareja {s_data['pareja']} validada!")
                
                # Botón de WhatsApp
                wa_url = create_wa_link(s_data['tel'], s_data['msg'])
                st.markdown(f"""
                <a href="{wa_url}" target="_blank" style="text-decoration: none;">
                    <div style="background-color: #25D366; color: white; padding: 10px 20px; border-radius: 8px; display: inline-block; font-weight: bold; display: flex; align-items: center; gap: 10px; width: fit-content;">
                        <img src="https://upload.wikimedia.org/wikipedia/commons/6/6b/WhatsApp.svg" width="24" height="24">
                        Enviar Confirmación por WhatsApp
                    </div>
                </a>
                """, unsafe_allow_html=True)
                
                if st.button("Cerrar Aviso", key="close_val_msg"):
                    del st.session_state['val_success']
                    st.rerun()
                st.divider()

            df_pendientes = get_data("SELECT * FROM inscripciones WHERE estado_validacion = 'Pendiente' ORDER BY id ASC")
            
            if df_pendientes is None or df_pendientes.empty:
                st.info("✅ No hay inscripciones pendientes de validación.")
            else:
                for _, row in df_pendientes.iterrows():
                    with st.container():
                        c1, c2, c3, c4 = st.columns([3, 2, 1.5, 1.5])
                        disp_j1 = row['jugador1'] if row['jugador1'] else "Sin Nombre"
                        disp_j2 = row['jugador2'] if row['jugador2'] else "Sin Nombre"
                        c1.markdown(f"**{disp_j1} - {disp_j2}**")
                        c1.caption(f"Torneo ID: {row['torneo_id']} | Cat: {row['categoria']}")
                        c2.write(f"📞 {row['telefono1']}")
                        
                        if c3.button("✅ Validar Inscripción", key=f"btn_val_{row['id']}"):
                            run_action("UPDATE inscripciones SET estado_validacion = 'Validado' WHERE id = %(id)s", {"id": row['id']})
                            
                            # Obtener nombre del torneo para el mensaje
                            df_t = cargar_datos("SELECT nombre FROM torneos WHERE id = :tid", params={"tid": row['torneo_id']})
                            nombre_torneo = df_t.iloc[0]['nombre'] if (df_t is not None and not df_t.empty) else "el torneo"
                            
                            msg_wa = f"¡Hola! Soy Augusto de Rincón Padel. Tu inscripción para el torneo {nombre_torneo} ha sido VALIDADA. Pareja: {row['jugador1']} - {row['jugador2']}. ¡Te esperamos! Cualquier duda, escribinos a este número (3455454907)."
                            
                            st.session_state['val_success'] = {'pareja': f"{row['jugador1']} - {row['jugador2']}", 'tel': row['telefono1'], 'msg': msg_wa}
                            limpiar_cache()
                            st.rerun()
                        
                        if c4.button("❌ Rechazar", key=f"btn_rej_{row['id']}", type="secondary"):
                            run_action("DELETE FROM inscripciones WHERE id = %(id)s", {"id": row['id']})
                            st.warning(f"Inscripción de {row['jugador1']} rechazada.")
                            limpiar_cache()
                            st.rerun()

                        st.divider()

        with tab_transferencias:
            seccion_transferir_jugadores()

        with tab_admin_gral:
            st.subheader("Configuración de Puntaje")
            with st.expander("⚙️ Editar Puntos por Instancia"):
                c1, c2, c3, c4 = st.columns(4)
                pts_campeon = c1.number_input("Campeón", value=1000, step=100)
                pts_final = c2.number_input("Finalista", value=600, step=50)
                pts_semi = c3.number_input("Semifinal", value=360, step=40)
                pts_cuartos = c4.number_input("Cuartos", value=180, step=20)
                st.caption("Estos valores se usarán para el cálculo automático al cerrar torneos.")
            
            st.subheader("Gestión de Jugadores")
            with st.expander("⚙️ Recategorizar Jugador"):
                st.write("Selecciona un jugador para actualizar su nivel. El nivel actual pasará al historial.")
                
                # Obtener lista de jugadores para el dropdown
                df_j_admin = get_data("SELECT id, nombre, apellido, categoria_actual FROM jugadores ORDER BY apellido")
                if df_j_admin is not None and not df_j_admin.empty:
                    # Crear diccionario para mapear selección a ID
                    opciones = {f"{row['apellido']}, {row['nombre']} (Actual: {row['categoria_actual']})": row['id'] for _, row in df_j_admin.iterrows()}
                    
                    col_sel, col_cat = st.columns([2, 1])
                    sel_jugador = col_sel.selectbox("Buscar Jugador", options=list(opciones.keys()))
                    id_jugador = opciones[sel_jugador]
                    
                    nueva_cat = col_cat.selectbox("Nueva Categoría", ["Libre", "3ra", "4ta", "5ta", "6ta", "7ma", "8va"])
                    
                    if st.button("💾 Guardar Cambios"):
                        recategorizar_jugador(id_jugador, nueva_cat)
                        st.success(f"Categoría actualizada a {nueva_cat} correctamente.")
                        st.rerun()
                else:
                    st.info("No hay jugadores registrados para recategorizar.")
            
            st.markdown("---")
            st.subheader("🔄 Sincronización de Datos")
            st.warning(
                "**¡Atención!** Este proceso reemplazará completamente el contenido de la base de datos local "
                "(`torneos_padel.db`) con los datos actuales de la nube. "
                "Cualquier cambio local que no se haya subido a la nube se perderá."
            )
            if st.button("🔄 Sincronizar Nube -> Local", type="primary"):
                with st.spinner("Iniciando sincronización... Este proceso puede tardar unos momentos."):
                    success, message = sincronizar_datos_nube_a_local()
                if success:
                    st.success(f"✅ {message}")
                else:
                    st.error(f"❌ {message}")
                    
            st.markdown("---")
            st.write("📥 **Descargar Copia de Seguridad**")
            if os.path.exists('torneos_padel.db'):
                with open('torneos_padel.db', "rb") as f:
                    st.download_button(
                        label="💾 Descargar Base de Datos Local (.db)",
                        data=f,
                        file_name=f"torneos_padel_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.db",
                        mime="application/vnd.sqlite3"
                    )
            else:
                st.info("El archivo de base de datos local aún no existe. Ejecuta una sincronización primero.")

        with tab_admin_fotos:
            st.subheader("Subir Nueva Foto")
            st.warning('Para mantener la web rápida, el tamaño máximo por foto es de 2MB')
            uploaded_file = st.file_uploader("Seleccionar imagen", type=['jpg', 'png', 'jpeg'])
            
            if uploaded_file is not None:
                if uploaded_file.size > 2 * 1024 * 1024:
                    st.error("⚠️ El archivo supera los 2MB. Por favor, comprímelo antes de subirlo.")
                else:
                    if st.button("Subir Foto"):
                        # Optimización de imagen
                        image = Image.open(uploaded_file)
                        
                        # Convertir a RGB para asegurar compatibilidad JPEG
                        if image.mode in ("RGBA", "P"):
                            image = image.convert("RGB")
                            
                        # Redimensionar para web (Max 1024px)
                        image.thumbnail((1024, 1024))
                        
                        # Guardar en buffer con compresión
                        img_byte_arr = io.BytesIO()
                        image.save(img_byte_arr, format='JPEG', quality=85, optimize=True)
                        
                        guardar_foto(uploaded_file.name, img_byte_arr.getvalue())
                        st.success("Foto subida exitosamente.")
                        st.rerun()

        with tab_carga_puntos:
            st.subheader("📊 Carga de Puntos al Ranking")
            st.markdown("Asigna puntos a los jugadores según su desempeño en el torneo.")
            
            # 1. Seleccionar Torneo
            df_t_ranking = get_data("SELECT * FROM torneos WHERE es_puntuable = 1 ORDER BY id DESC")
            
            if df_t_ranking is not None and not df_t_ranking.empty:
                # Crear diccionario para selectbox: "Nombre (Categoria)" -> ID
                t_opts = {f"{row['nombre']} ({row['categoria']})": row['id'] for _, row in df_t_ranking.iterrows()}
                sel_t_name_r = st.selectbox("Seleccionar Torneo", list(t_opts.keys()), key="sel_t_ranking_pts")
                sel_t_id_r = t_opts[sel_t_name_r]
                
                # Obtener info del torneo
                row_torneo = df_t_ranking[df_t_ranking['id'] == sel_t_id_r].iloc[0]
                cat_torneo_r = row_torneo['categoria']
                
                es_puntuable_r = row_torneo['es_puntuable'] if 'es_puntuable' in row_torneo else 1
                
                if not es_puntuable_r:
                    st.error("🚫 Este torneo está configurado como NO PUNTUABLE. No se pueden cargar puntos.")
                else:
                    st.info(f"Categoría del Torneo: **{cat_torneo_r}** (Los puntos se sumarán a esta categoría)")
                    
                    # 2. Seleccionar Pareja
                    df_insc_r = get_data("SELECT * FROM inscripciones WHERE torneo_id = :torneo_id", params={"torneo_id": sel_t_id_r})
                    
                    if df_insc_r is not None and not df_insc_r.empty:
                        # Crear lista de parejas
                        parejas_map = {f"{row['jugador1']} - {row['jugador2']}": (row['jugador1'], row['jugador2']) for _, row in df_insc_r.iterrows()}
                        sel_pareja_r = st.selectbox("Seleccionar Pareja", list(parejas_map.keys()), key="sel_pareja_ranking_pts")
                        
                        # 3. Input de Puntos
                        puntos_r = st.number_input("Puntos a asignar (por jugador)", min_value=0, step=10, value=100, help="Ej: 1000 Campeón, 600 Finalista, etc.")
                        
                        if st.button("💾 Actualizar Ranking", key="btn_update_ranking"):
                            j1, j2 = parejas_map[sel_pareja_r]
                            # Actualizar J1 y J2 (Borrar previos para este torneo y reinsertar)
                            for jug in [j1, j2]:
                                run_action("DELETE FROM ranking_puntos WHERE torneo_id = %(torneo_id)s AND jugador = %(jugador)s", {"torneo_id": sel_t_id_r, "jugador": jug})
                                run_action("INSERT INTO ranking_puntos (torneo_id, jugador, categoria, puntos) VALUES (%(torneo_id)s, %(jugador)s, %(categoria)s, %(puntos)s)", {"torneo_id": sel_t_id_r, "jugador": jug, "categoria": cat_torneo_r, "puntos": puntos_r})
                            limpiar_cache()
                            st.success(f"✅ Se asignaron {puntos_r} puntos a {j1} y {j2} en la categoría {cat_torneo_r}.")
                    else:
                        st.warning("⚠️ No hay inscriptos en este torneo.")
            else:
                st.info("No hay torneos disponibles.")

        with tab_admin_socios:
            st.subheader("👥 Administración de Socios")
            
            # 1. Registro Manual
            with st.expander("➕ Registrar Nuevo Socio (Manual)", expanded=False):
                with st.form("form_admin_alta_socio"):
                    c1, c2 = st.columns(2)
                    a_nombre = c1.text_input("Nombre")
                    a_apellido = c2.text_input("Apellido")
                    a_dni = c1.text_input("DNI (Usuario)")
                    a_cel = c2.text_input("Celular")
                    a_cat = st.selectbox("Categoría", ["Libre", "3ra", "4ta", "5ta", "6ta", "7ma", "8va"])
                    a_loc = st.text_input("Localidad")
                    
                    if st.form_submit_button("💾 Guardar Socio"):
                        if a_dni and a_nombre and a_apellido:
                            # Password por defecto es el DNI
                            ok, msg = registrar_jugador_db(a_dni, a_nombre, a_apellido, a_cel, a_cat, a_loc, password=None)
                            if ok:
                                st.success(f"✅ {msg}")
                                st.rerun()
                            else:
                                st.error(f"❌ {msg}")
                        else:
                            st.warning("⚠️ Nombre, Apellido y DNI son obligatorios.")

            st.markdown("---")
            st.subheader("🗑️ Limpieza de Base de Datos")
            
            # Buscador para filtrar la lista
            search_socio = st.text_input("🔍 Buscar socio para eliminar (Nombre o DNI)", placeholder="Escribe aquí...")
            
            query_socios = "SELECT dni, nombre, apellido, categoria_actual, celular FROM jugadores ORDER BY apellido"
            df_socios = get_data(query_socios)
            
            if search_socio:
                df_socios = df_socios[df_socios.apply(lambda row: search_socio.lower() in str(row).lower(), axis=1)]
            
            # Renderizar lista con botones
            for idx, row in df_socios.iterrows():
                c_info, c_btn = st.columns([4, 1])
                with c_info:
                    st.markdown(f"**{row['apellido']}, {row['nombre']}** | 🏷️ {row['categoria_actual']} | 🆔 {row['dni']}")
                with c_btn:
                    if st.button("🗑️ Eliminar", key=f"del_{row['dni']}"):
                        eliminar_jugador(row['dni'])
                        st.warning(f"Socio {row['nombre']} {row['apellido']} eliminado.")
                        st.rerun()

        with tab_control_vivo:
            st.subheader("⚡ Control en Vivo (Gestión de Partidos)")
            
            # 1. Seleccionar Torneo y Partido
            df_t_live = get_data("SELECT * FROM torneos WHERE estado IN ('Abierto', 'En Juego')")
            if df_t_live is not None and not df_t_live.empty:
                t_opts_live = {f"{row['nombre']}": row['id'] for _, row in df_t_live.iterrows()}
                sel_t_live = st.selectbox("Seleccionar Torneo", list(t_opts_live.keys()), key="sel_t_live")
                id_t_live = t_opts_live[sel_t_live]
                
                # Obtener partidos pendientes o en juego
                df_p_live = get_data("SELECT * FROM partidos WHERE torneo_id = :torneo_id AND estado_partido != 'Finalizado' ORDER BY id ASC", params={"torneo_id": id_t_live})
                
                # Configuración del torneo para Tie-break
                t_conf = get_data("SELECT super_tiebreak, puntos_tiebreak FROM torneos WHERE id=:id", {"id": id_t_live}).iloc[0]
                is_stb = t_conf['super_tiebreak'] == 1
                pts_stb = t_conf['puntos_tiebreak']
                
                if df_p_live is not None and not df_p_live.empty:
                    # --- LISTADO DE PARTIDOS CON CONTROLES ---
                    for _, row in df_p_live.iterrows():
                        with st.expander(f"{row['instancia']}: {row['pareja1']} vs {row['pareja2']} ({row['estado_partido']})", expanded=(row['estado_partido'] == 'En Juego')):
                            c_ctrl, c_res = st.columns([1, 2])
                            
                            # Inicializar Estado Live si no existe
                            live_key = f"live_{row['id']}"
                            if live_key not in st.session_state:
                                # Intentar parsear resultado actual de la DB para inicializar games
                                curr_res = row['resultado'] if row['resultado'] else ""
                                parts = curr_res.split(' ')
                                g1, g2 = 0, 0
                                sets_previos = ""
                                if parts:
                                    last_set = parts[-1]
                                    if '-' in last_set:
                                        try:
                                            g1 = int(last_set.split('-')[0])
                                            g2 = int(last_set.split('-')[1])
                                            sets_previos = " ".join(parts[:-1])
                                        except: pass
                                st.session_state[live_key] = {'p1_pts': 0, 'p2_pts': 0, 'p1_games': g1, 'p2_games': g2, 'sets_str': sets_previos, 'torneo_id': id_t_live}
                            
                            with c_ctrl:
                                st.write("**Controles**")
                                if row['estado_partido'] == 'Próximo':
                                    if st.button("▶️ Iniciar Partido", key=f"start_{row['id']}"):
                                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        run_action("UPDATE partidos SET estado_partido = 'En Juego', hora_inicio_real = %(now)s WHERE id = %(id)s", {"now": now_str, "id": row['id']})
                                        # Activar en banner también
                                        run_action("DELETE FROM partido_en_vivo")
                                        run_action("INSERT INTO partido_en_vivo (torneo, pareja1, pareja2, marcador) VALUES (%(torneo)s, %(pareja1)s, %(pareja2)s, %(marcador)s)", 
                                                  {"torneo": sel_t_live, "pareja1": row['pareja1'], "pareja2": row['pareja2'], "marcador": row['resultado'] if row['resultado'] else "0-0"})
                                        st.rerun()
                                elif row['estado_partido'] == 'En Juego':
                                    if st.button("⏸️ Pausar/Detener", key=f"pause_{row['id']}"):
                                        detener_partido(row['id'])
                                        st.rerun()
                                elif row['estado_partido'] == 'Detenido':
                                    if st.button("▶️ Reanudar", key=f"resume_{row['id']}"):
                                        actualizar_estado_partido(row['id'], 'En Juego')
                                        st.rerun()
                            
                            with c_res:
                                if row['estado_partido'] == 'En Juego':
                                    # --- WIDGET LIVE SCOREBOARD ---
                                    state = st.session_state[live_key]
                                    
                                    # Contenedor Visual del Marcador
                                    st.markdown(f"""
                                    <div style="background-color:#000; border:2px solid #39FF14; border-radius:10px; padding:15px; margin-bottom:15px;">
                                        <div style="display:flex; justify-content:space-between; text-align:center; color:white;">
                                            <div style="flex:1;">
                                                <div style="font-size:0.9rem; font-weight:bold; color:#aaa;">{row['pareja1']}</div>
                                                <div style="font-size:2.5rem; font-weight:900; line-height:1;">{state['p1_games']}</div>
                                                <div style="font-size:1.8rem; color:#39FF14; font-family:'Courier New';">{obtener_puntos_display(state['p1_pts'])}</div>
                                            </div>
                                            <div style="flex:0.2; display:flex; align-items:center; justify-content:center; font-size:1.5rem; color:#444;">-</div>
                                            <div style="flex:1;">
                                                <div style="font-size:0.9rem; font-weight:bold; color:#aaa;">{row['pareja2']}</div>
                                                <div style="font-size:2.5rem; font-weight:900; line-height:1;">{state['p2_games']}</div>
                                                <div style="font-size:1.8rem; color:#39FF14; font-family:'Courier New';">{obtener_puntos_display(state['p2_pts'])}</div>
                                            </div>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    # Botones de Acción
                                    cb1, cb2 = st.columns(2)
                                    if cb1.button(f"🎾 Punto {row['pareja1'].split(' ')[0]}", key=f"btn_p1_{row['id']}", use_container_width=True):
                                        sumar_punto(row['id'], 1, state)
                                        st.rerun()
                                        
                                    if cb2.button(f"🎾 Punto {row['pareja2'].split(' ')[0]}", key=f"btn_p2_{row['id']}", use_container_width=True):
                                        sumar_punto(row['id'], 2, state)
                                        st.rerun()
                                        
                                    st.write("")
                                    if st.button("💾 Finalizar Set y Guardar", key=f"end_set_{row['id']}", type="primary", use_container_width=True):
                                        # Guardar set en columna correspondiente
                                        # Determinar qué set es en base a sets_previos
                                        sets_done = len(state['sets_str'].split(' ')) if state['sets_str'] else 0
                                        next_set_col = f"set{sets_done + 1}"
                                        games_final = f"{state['p1_games']}-{state['p2_games']}"
                                        
                                        if sets_done < 3:
                                            run_action(f"UPDATE partidos SET {next_set_col} = :val WHERE id = :id", {"val": games_final, "id": row['id']})
                                        
                                        # Actualizar sets previos en estado y resetear games
                                        new_sets_str = f"{state['sets_str']} {games_final}".strip()
                                        st.session_state[live_key] = {'p1_pts': 0, 'p2_pts': 0, 'p1_games': 0, 'p2_games': 0, 'sets_str': new_sets_str, 'torneo_id': id_t_live}
                                        
                                        # Update DB
                                        run_action("UPDATE partidos SET resultado = %(res)s WHERE id = %(id)s", {"res": new_sets_str, "id": row['id']})
                                        st.toast("✅ Set guardado exitosamente.", icon="💾")
                                        st.rerun()
                                        
                                    with st.expander("🛠️ Corrección Manual"):
                                        st.caption("Usa esto si hubo un error en el tanteador.")
                                        new_res_man = st.text_input("Resultado Completo", value=row['resultado'] if row['resultado'] else "", key=f"man_res_{row['id']}")
                                        if st.button("Forzar Actualización", key=f"force_{row['id']}"):
                                            actualizar_marcador(row['id'], new_res_man)
                                            st.session_state.pop(live_key, None) # Resetear estado live para recargar del manual
                                            st.rerun()

                                else:
                                    # MODO MANUAL (Próximo / Detenido)
                                    st.write("**Cargar Resultados (Manual)**")
                                    with st.form(key=f"res_form_{row['id']}"):
                                        # Parsear resultado actual si existe
                                        curr_res = row['resultado'] if row['resultado'] else ""
                                        sets_vals = curr_res.split(' ') if curr_res else []
                                        val_s1 = sets_vals[0] if len(sets_vals) > 0 else ""
                                        val_s2 = sets_vals[1] if len(sets_vals) > 1 else ""
                                        val_s3 = sets_vals[2] if len(sets_vals) > 2 else ""
                                        
                                        c_s1, c_s2, c_s3 = st.columns(3)
                                        in_s1 = c_s1.text_input("Set 1", value=val_s1, key=f"s1_{row['id']}")
                                        in_s2 = c_s2.text_input("Set 2", value=val_s2, key=f"s2_{row['id']}")
                                        if is_stb:
                                            in_s3 = c_s3.text_input(f"S. Tie-break ({pts_stb})", value=val_s3, key=f"s3_{row['id']}", placeholder="Ej: 10-8")
                                        else:
                                            in_s3 = c_s3.text_input("Set 3", value=val_s3, key=f"s3_{row['id']}")
                                        
                                        new_res = f"{in_s1} {in_s2} {in_s3}".strip()
                                        
                                        if st.form_submit_button("💾 Guardar Parcial"):
                                            actualizar_marcador(row['id'], new_res)
                                            st.success("Guardado")
                                            st.rerun()
                                
                                # Botón explícito de Finalizar fuera del form para evitar submits accidentales
                                if row['estado_partido'] in ['En Juego', 'Detenido', 'Próximo']:
                                    st.markdown("---")
                                    c_win, c_btn_fin = st.columns([2, 1])
                                    with c_win:
                                        winner_sel = st.selectbox("Ganador", [row['pareja1'], row['pareja2']], key=f"win_sel_{row['id']}")
                                    with c_btn_fin:
                                        st.write("")
                                        st.write("")
                                        if st.button("🏁 Finalizar y Avanzar", key=f"confirm_fin_{row['id']}"):
                                            if not row['resultado']:
                                                st.error("Carga el resultado primero.")
                                            else:
                                                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                                run_action("UPDATE partidos SET estado_partido = 'Finalizado', ganador = %(ganador)s, hora_fin = %(now)s WHERE id = %(id)s", 
                                                          {"ganador": winner_sel, "now": now_str, "id": row['id']})
                                                
                                                # Limpiar banner
                                                run_action("DELETE FROM partido_en_vivo")
                                                
                                                # Actualizar Tablas/Bracket
                                                actualizar_tabla_posiciones(id_t_live)
                                                if row['bracket_pos']:
                                                    actualizar_bracket(row['id'], id_t_live, row['bracket_pos'], row['resultado'], winner_sel)
                                                
                                                st.success("Partido finalizado y procesado.")
                                                st.rerun()
                            
                            # --- SECCIÓN WHATSAPP ---
                            st.markdown("---")
                            st.write("📢 **Avisar a Jugadores (WhatsApp)**")
                            
                            # Buscar datos de contacto
                            row_p1 = get_inscripcion_by_pareja(row['pareja1'])
                            row_p2 = get_inscripcion_by_pareja(row['pareja2'])
                            
                            msg_wa = "¡Hola! Te hablamos de Rincón Padel. Tu partido está próximo a comenzar, por favor acercate al complejo en los próximos 15 minutos. Admin: 3455454907"
                            
                            col_wa1, col_wa2 = st.columns(2)
                            
                            with col_wa1:
                                st.caption(f"Pareja 1: {row['pareja1']}")
                                if row_p1 is not None:
                                    if row_p1['telefono1']:
                                        url = create_wa_link(row_p1['telefono1'], msg_wa)
                                        st.markdown(f"📲 [Avisar a {row_p1['jugador1']}]({url})")
                                    if row_p1['telefono2']:
                                        url = create_wa_link(row_p1['telefono2'], msg_wa)
                                        st.markdown(f"📲 [Avisar a {row_p1['jugador2']}]({url})")
                                else:
                                    st.caption("Sin datos de contacto.")
                                    url_gen = create_wa_link("", msg_wa)
                                    st.markdown(f"📲 [Chat Genérico]({url_gen})")

                            with col_wa2:
                                st.caption(f"Pareja 2: {row['pareja2']}")
                                if row_p2 is not None:
                                    if row_p2['telefono1']:
                                        url = create_wa_link(row_p2['telefono1'], msg_wa)
                                        st.markdown(f"📲 [Avisar a {row_p2['jugador1']}]({url})")
                                    if row_p2['telefono2']:
                                        url = create_wa_link(row_p2['telefono2'], msg_wa)
                                        st.markdown(f"📲 [Avisar a {row_p2['jugador2']}]({url})")
                                else:
                                    st.caption("Sin datos de contacto.")
                                    url_gen = create_wa_link("", msg_wa)
                                    st.markdown(f"📲 [Chat Genérico]({url_gen})")

                else:
                    st.info("No hay partidos pendientes en este torneo.")
            else:
                st.warning("No hay torneos activos.")

        debug_base_datos()

def mostrar_transmision():
    def ir_a_inicio():
        st.session_state.menu_nav = "🏆 Inicio"

    # --- CONTROLES SUPERIORES (Admin / TV) ---
    col_btn1, col_btn2, col_vacio = st.columns([1, 1, 4])
    
    with col_btn1:
        st.button("🔙 Volver al Inicio", use_container_width=True, on_click=ir_a_inicio)
            
    with col_btn2:
        # Inyectamos el botón HTML/JS para el Fullscreen
        # Apuntamos a window.parent para afectar a la pestaña completa de Streamlit
        html_fullscreen = """
        <style>
            .btn-fullscreen {
                background-color: transparent;
                color: #FFFFFF;
                border: 1px solid #333;
                padding: 6px 15px;
                border-radius: 8px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 1rem;
                cursor: pointer;
                width: 100%;
                transition: all 0.3s ease;
            }
            .btn-fullscreen:hover {
                border-color: #39FF14;
                color: #39FF14;
            }
        </style>
        <button class="btn-fullscreen" onclick="goFullscreen()">🔲 Pantalla Completa</button>
        <script>
            function goFullscreen() {
                const doc = window.parent.document.documentElement;
                if (doc.requestFullscreen) { doc.requestFullscreen(); }
                else if (doc.mozRequestFullScreen) { doc.mozRequestFullScreen(); }
                else if (doc.webkitRequestFullscreen) { doc.webkitRequestFullscreen(); }
                else if (doc.msRequestFullscreen) { doc.msRequestFullscreen(); }
            }
        </script>
        """
        components.html(html_fullscreen, height=45)

    # 1. AUTO-RECARGA (30 segundos) usando inyección de JavaScript
    components.html(
        """
        <script>
        setTimeout(function(){
            window.parent.location.reload();
        }, 30000);
        </script>
        """, height=0, width=0
    )

    # 2. LIMPIEZA VISUAL EXTREMA (Ocultar Sidebar, Header, Footer y forzar Full Width real)
    st.markdown("""
        <style>
            /* Ocultar elementos de Streamlit */
            [data-testid="stSidebar"] {display: none !important;}
            [data-testid="collapsedControl"] {display: none !important;}
            header {display: none !important;}
            footer {display: none !important;}
            
            /* Eliminar paddings innecesarios */
            .block-container {
                padding-top: 1rem !important;
                padding-bottom: 0rem !important;
                padding-left: 2rem !important;
                padding-right: 2rem !important;
                max-width: 100% !important;
            }

            /* ESTÉTICA MODO TV */
            .tv-title { color: #39FF14; text-align: center; font-size: 3.5rem; font-weight: 900; letter-spacing: 4px; text-transform: uppercase; text-shadow: 0 0 20px rgba(57, 255, 20, 0.6); margin-bottom: 30px; }
            
            .tv-live-card { background: linear-gradient(145deg, #0a0a0a, #151515); border: 4px solid #39FF14; border-radius: 25px; padding: 40px; text-align: center; box-shadow: 0 0 40px rgba(57, 255, 20, 0.3); margin-bottom: 40px; }
            .tv-live-header { color: #fff; font-size: 2rem; font-weight: bold; letter-spacing: 2px; margin-bottom: 25px; }
            .tv-live-match { color: #fff; font-size: 5rem; font-weight: 900; line-height: 1.1; }
            .tv-live-vs { color: #555; font-size: 3rem; margin: 0 20px; }
            .tv-live-score { color: #39FF14; font-size: 7rem; font-family: 'Courier New', monospace; font-weight: bold; background: #000; padding: 10px 50px; border-radius: 20px; display: inline-block; margin-top: 30px; border: 3px solid #222; text-shadow: 0 0 15px #39FF14; }

            .tv-panel { background: #111; border: 2px solid #333; border-top: 6px solid #39FF14; border-radius: 20px; padding: 30px; height: 100%; }
            .tv-panel-title { color: #39FF14; font-size: 2.2rem; font-weight: bold; margin-bottom: 25px; text-align: center; border-bottom: 2px solid #333; padding-bottom: 15px; text-transform: uppercase; }
            
            .tv-match-row { font-size: 1.8rem; color: #fff; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed #222; padding-bottom: 15px; }
            .tv-time-badge { color: #FF9100; font-weight: bold; background: rgba(255, 145, 0, 0.15); padding: 5px 15px; border-radius: 10px; }
            
            .tv-rank-row { font-size: 2rem; color: #fff; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; }
            .tv-rank-pts { color: #00E676; font-weight: bold; font-family: 'Courier New', Courier, monospace; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='tv-title'>📺 TRANSMISIÓN EN VIVO</div>", unsafe_allow_html=True)

    # 3. SECCIÓN CENTRAL: PARTIDO EN VIVO
    df_live = obtener_partido_en_vivo()
    if df_live is not None and not df_live.empty:
        live = df_live.iloc[0]
        match_html = f"{live['pareja1']} <span class='tv-live-vs'>VS</span> {live['pareja2']}"
        score_html = live['marcador']
    else:
        # Sin partido activo
        match_html = "ESPERANDO PARTIDO <span class='tv-live-vs'>...</span>"
        score_html = "EN BREVE"

    st.markdown(f"""
        <div class="tv-live-card">
            <div class="tv-live-header">🔴 PARTIDO EN JUEGO - CANCHA CENTRAL</div>
            <div class="tv-live-match">{match_html}</div>
            <div class="tv-live-score">{score_html}</div>
        </div>
    """, unsafe_allow_html=True)

    # 4. PANELES INFERIORES: PRÓXIMOS PARTIDOS Y RANKING
    col_tv1, col_tv2 = st.columns(2, gap="large")

    with col_tv1:
        st.markdown("<div class='tv-panel'><div class='tv-panel-title'>🕒 Próximos Partidos</div>", unsafe_allow_html=True)
        df_next = cargar_datos("SELECT horario, pareja1, pareja2 FROM partidos WHERE estado_partido = 'Próximo' ORDER BY horario ASC LIMIT 3")
        if df_next is not None and not df_next.empty:
            for _, row in df_next.iterrows():
                hora = str(row['horario']).split(' ')[-1] if row['horario'] else "A conf."
                st.markdown(f"<div class='tv-match-row'><span>{row['pareja1']} vs {row['pareja2']}</span> <span class='tv-time-badge'>{hora}</span></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='tv-match-row'><span style='color: #888; font-size: 1.2rem; text-align: center; width: 100%;'>No hay partidos programados</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_tv2:
        st.markdown("<div class='tv-panel'><div class='tv-panel-title'>🏆 Top 5 Ranking</div>", unsafe_allow_html=True)
        df_rank = cargar_datos("SELECT jugador, SUM(puntos) as total FROM ranking_puntos GROUP BY jugador ORDER BY total DESC LIMIT 5")
        if df_rank is not None and not df_rank.empty:
            for i, row in df_rank.iterrows():
                medal = "🥇" if i==0 else "🥈" if i==1 else "🥉" if i==2 else f"#{i+1}"
                st.markdown(f"<div class='tv-rank-row'><span>{medal} {row['jugador']}</span> <span class='tv-rank-pts'>{row['total']}</span></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='tv-rank-row'><span style='color: #888; font-size: 1.2rem; text-align: center; width: 100%;'>Aún no hay puntos registrados</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# --- ENRUTADOR DE VISTAS (NAVEGACIÓN) ---
if choice == "🏆 Inicio":
    mostrar_inicio()
elif choice == "📅 Fixture y Horarios":
    mostrar_fixture()
elif choice == "📊 Posiciones":
    mostrar_posiciones()
elif choice == "📈 Ranking":
    # Función local existente
    show_ranking_content()
elif choice == "👥 Jugadores":
    mostrar_jugadores()
elif choice == "📍 Sede":
    mostrar_sede()
elif choice == "📺 Pantalla TV":
    mostrar_transmision()
elif choice == "🏠 Mi Panel":
    mostrar_panel_usuario()
elif choice == "⚙️ Admin":
    mostrar_panel_admin()
elif choice == "💻 Simulador":
    # Función externa/local
    mostrar_simulador()