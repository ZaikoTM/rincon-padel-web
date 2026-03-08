import streamlit as st
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

# Configuración de página con estética Rincón Padel
try:
    logo = Image.open("assets/logo_rincon.png")
    page_icon = logo
except FileNotFoundError:
    logo = None
    page_icon = "🎾"

st.set_page_config(
    page_title="Rincón Padel - Torneos", 
    layout="wide", 
    page_icon=page_icon,
    initial_sidebar_state="expanded"
)

# --- GESTIÓN DE TEMA (CLARO / OSCURO) ---
# Inicializar estado del tema si no existe (False = Oscuro por defecto)
if 'theme' not in st.session_state:
    st.session_state['theme'] = False

# Toggle en Sidebar (Lo colocamos al principio para que cargue antes que el resto)
with st.sidebar:
    is_light_mode = st.toggle('☀️ Modo Claro / 🌙 Modo Oscuro', value=st.session_state['theme'], key='theme')

# --- DEFINICIÓN DE ESTILOS CSS ---

css_dark_neon = """
    <style>
        /* Transición Suave General */
        .stApp, section[data-testid="stSidebar"], .stButton button, .stTextInput input, div[data-testid="stExpander"], .dashboard-card, .card {
            transition: all 0.5s ease !important;
        }

        /* Fondo General */
        .stApp {
            background-color: #000000;
            background-image: radial-gradient(circle at center, #111111 0%, #000000 100%);
            border-left: 2px solid #00FF41;
            border-right: 2px solid #00FF41;
        }
        
        /* Animación Pulso Neón */
        @keyframes neonPulse {
            0% { box-shadow: 0 0 5px #00FF41, inset 0 0 5px #00FF41; border-color: #00FF41; }
            50% { box-shadow: 0 0 20px #00FF41, inset 0 0 10px #00FF41; border-color: #39FF14; }
            100% { box-shadow: 0 0 5px #00FF41, inset 0 0 5px #00FF41; border-color: #00FF41; }
        }

        /* Animación Degradado Sidebar */
        @keyframes gradientSidebar {
            0% { background-position: 0% 0%; }
            50% { background-position: 0% 100%; }
            100% { background-position: 0% 0%; }
        }

        /* Animación Borde Respirando */
        @keyframes breatheBorder {
            0% { border-right-color: rgba(0, 255, 65, 0.5); box-shadow: 2px 0 10px rgba(0, 255, 65, 0.2); }
            100% { border-right-color: rgba(0, 255, 65, 1.0); box-shadow: 4px 0 20px rgba(0, 255, 65, 0.6); }
        }
        
        /* --- ESTILOS BARRA LATERAL (SIDEBAR) --- */
        
        /* Contenedor Principal Sidebar */
        section[data-testid="stSidebar"] {
            /* Fondo degradado animado sutil */
            background: linear-gradient(180deg, #050505, #111111, #050505);
            background-size: 100% 400%;
            animation: gradientSidebar 15s ease infinite, breatheBorder 3s infinite alternate;
            
            /* Borde derecho neón dinámico (definido en animación) */
            border-right: 2px solid #00FF41;
        }
        
        /* Inputs del Sidebar: Fondo negro, bordes redondeados, borde neón fino */
        section[data-testid="stSidebar"] .stTextInput input {
            background-color: #000000 !important;
            color: #ccffcc !important; /* Verde neón suave */
            border: 1px solid #00FF41 !important;
            border-radius: 10px !important;
            box-shadow: 0 0 5px rgba(0, 255, 65, 0.3); /* Glow constante */
        }
        
        /* Brillo al hacer foco en inputs */
        section[data-testid="stSidebar"] .stTextInput input:focus {
            box-shadow: 0 0 15px rgba(0, 255, 65, 0.4) !important;
            border-color: #39FF14 !important;
            color: #FFFFFF !important;
        }
        
        /* Botones del Sidebar (Ingresar): Verde neón sólido, resplandor inferior */
        section[data-testid="stSidebar"] .stButton button {
            background-color: #00FF41 !important;
            background-image: none !important;
            color: #000000 !important;
            font-weight: bold !important;
            border: none !important;
            border-radius: 10px !important;
            box-shadow: 0 0 15px rgba(0, 255, 65, 0.6) !important; /* Glow constante */
            transition: transform 0.2s ease, box-shadow 0.2s ease !important;
            animation: none !important;
        }
        section[data-testid="stSidebar"] .stButton button:hover {
            box-shadow: 0 0 25px #00FF41, 0 10px 25px rgba(0, 255, 65, 0.7) !important;
            transform: translateY(-2px);
        }
        
        /* Estilo Tarjeta Neón para el Login (Expander) */
        section[data-testid="stSidebar"] div[data-testid="stExpander"] {
            border: 1px solid rgba(0, 255, 65, 0.4) !important;
            border-radius: 12px !important;
            background-color: rgba(0, 0, 0, 0.5) !important; /* Fondo translúcido */
            backdrop-filter: blur(10px) !important; /* Efecto vidrio */
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5) !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stExpander"] summary {
            color: #00FF41 !important;
            font-weight: bold;
        }

        /* Tipografía */
        h1, h2, h3, h4, h5, h6, .rincon-header, .zona-header {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
            text-shadow: 0 0 10px #00FF41 !important;
            color: #FFFFFF !important;
        }
        
        /* Encabezados institucionales */
        .rincon-header { 
            background-color: #000000; 
            color: #FFFFFF; 
            text-align: center; 
            padding: 20px; 
            border-radius: 10px; 
            border: 4px double #00FF41; 
            text-transform: uppercase; 
            font-weight: 900; 
            font-size: 26px; 
            letter-spacing: 3px; 
            text-shadow: 0 0 10px #00FF41, 0 0 20px #00FF41, 0 0 40px #00FF41;
            animation: neonPulse 3s infinite alternate;
            margin-bottom: 25px;
        }
        .zona-header { background-color: #1E1E1E; color: #FFFFFF; padding: 12px; border-left: 6px solid #00FF41; margin-top: 25px; margin-bottom: 15px; font-weight: bold; font-size: 16px; text-transform: uppercase; border-radius: 0px 8px 8px 0px; }

        /* Botones Generales (No Sidebar) */
        .stButton button {
            animation: neonPulse 3s infinite alternate;
        }
        .stButton button:hover {
            box-shadow: 0 0 30px #00FF41, inset 0 0 15px #00FF41 !important;
        }
        
        /* Contenedores Principales (Cards y Bloques) */
        .dashboard-card, .card, .admin-card, .player-card, .h2h-card, .ranking-card, .match-card, div[data-testid="stForm"] {
            background-color: rgba(30, 30, 30, 0.8) !important;
            border: 1px solid #00FF41 !important;
            border-radius: 15px !important;
            box-shadow: 0 0 15px rgba(0, 255, 65, 0.2) !important;
            color: #E0E0E0 !important;
        }

        /* Ajustes específicos para textos dentro de cards */
        .card-title, .dash-title, .player-name, .team-name {
            color: #00FF41 !important;
            text-shadow: none !important;
        }
        
        /* --- TABS (Pestañas Estilo Botón) --- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: transparent;
            border-bottom: none !important;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: transparent !important;
            border: 1px solid #00FF41 !important;
            color: #FFFFFF !important;
            border-radius: 5px !important;
            padding: 10px 20px !important;
            font-weight: 500 !important;
        }
        .stTabs [aria-selected="true"] {
            background-color: #00FF41 !important;
            color: #000000 !important;
            font-weight: bold !important;
            box-shadow: 0 0 10px #00FF41 !important;
        }

        /* --- SELECTBOX & INPUTS (Diseño Neon Minimalista) --- */
        .stSelectbox div[data-baseweb="select"] > div, .stTextInput input, .stNumberInput input, .stDateInput input {
            background-color: #000000 !important;
            color: #FFFFFF !important;
            border: 1px solid #00FF41 !important;
            border-radius: 8px !important;
        }
        .stSelectbox div[data-baseweb="select"]:hover > div, .stTextInput input:hover {
            box-shadow: 0 0 10px rgba(0, 255, 65, 0.3) !important;
            border-color: #39FF14 !important;
        }
        .stSelectbox div[data-baseweb="select"]:focus-within > div, .stTextInput input:focus {
            box-shadow: 0 0 15px rgba(0, 255, 65, 0.6) !important;
            border-color: #39FF14 !important;
        }
        .stSelectbox div[data-baseweb="select"] span, .stSelectbox div[data-baseweb="select"] svg {
            color: #FFFFFF !important;
            fill: #FFFFFF !important;
        }

        /* --- DATAFRAME & TABLES (Estilo Tabla de Posiciones) --- */
        [data-testid="stDataFrame"] {
            border: 1px solid #00FF41 !important;
            border-radius: 10px !important;
            background-color: #121212 !important;
            padding: 5px !important;
            box-shadow: 0 0 10px rgba(0, 255, 65, 0.1) !important;
        }
        
        /* Estilos para tablas HTML (st.table o st.markdown) */
        table {
            border-collapse: collapse !important;
            width: 100% !important;
            border: 1px solid #333 !important;
        }
        th {
            background-color: #000000 !important;
            color: #00FF41 !important;
            border-bottom: 2px solid #00FF41 !important;
        }
        tr:nth-child(even) { background-color: #1E1E1E !important; }
        tr:nth-child(odd) { background-color: #121212 !important; }
        tr:hover { box-shadow: inset 0 0 10px rgba(0, 255, 65, 0.2) !important; }
        td { border-bottom: 1px solid #333 !important; color: #ddd !important; }

        /* --- SPINNER PERSONALIZADO (Pelota Padel Neón) --- */
        div[data-testid="stSpinner"] > div {
            border: none !important;
            animation: none !important;
            width: 0 !important; height: 0 !important; /* Ocultar spinner original */
        }
        div[data-testid="stSpinner"]::after {
            content: '';
            display: block;
            width: 25px;
            height: 25px;
            background-color: #39FF14;
            border-radius: 50%;
            box-shadow: 0 0 15px #39FF14, inset 0 0 5px #fff;
            animation: bounce 0.5s infinite alternate cubic-bezier(0.5, 0.05, 1, 0.5);
            margin: 0 auto;
        }
        @keyframes bounce {
            from { transform: translateY(0) scale(1.1); }
            to { transform: translateY(-50px) scale(0.9); }
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
    </style>
"""

# Inyección Condicional de CSS
if is_light_mode:
    st.markdown(css_light_forest, unsafe_allow_html=True)
else:
    st.markdown(css_dark_neon, unsafe_allow_html=True)

# Inicializar estado de administrador
if 'es_admin' not in st.session_state:
    st.session_state.es_admin = False

# --- CONFIGURACIÓN DE SEGURIDAD ---
# La configuración de seguridad se maneja mediante st.secrets

# --- BASE DE DATOS ---
def run_action(query, params=None, return_id=False):
    """Ejecuta una acción de modificación (INSERT, UPDATE, DELETE) en la DB."""
    conn = st.connection('postgresql', type='sql')
    with conn.engine.raw_connection() as raw_conn:
        with raw_conn.cursor() as cur:
            cur.execute(query, params)
            if return_id:
                # En Postgres usamos RETURNING id, así que hacemos fetch
                result = cur.fetchone()[0]
            else:
                result = None
        raw_conn.commit()
    return result

def init_db():
    # Tabla Inscripciones
    run_action('''CREATE TABLE IF NOT EXISTS inscripciones
                 (id SERIAL PRIMARY KEY, 
                  torneo_id INTEGER, jugador1 TEXT, jugador2 TEXT, localidad TEXT, 
                  categoria TEXT, pago_confirmado INTEGER, telefono1 TEXT, telefono2 TEXT)''')
    # Tabla Torneos
    run_action('''CREATE TABLE IF NOT EXISTS torneos
                 (id SERIAL PRIMARY KEY, 
                  nombre TEXT, fecha TEXT, categoria TEXT, estado TEXT)''')
    # Tabla Resultados / Partidos
    run_action('''CREATE TABLE IF NOT EXISTS partidos
                 (id SERIAL PRIMARY KEY, 
                  torneo_id INTEGER, pareja1 TEXT, pareja2 TEXT, 
                  resultado TEXT, instancia TEXT)''')
    # Tabla Zonas
    run_action('''CREATE TABLE IF NOT EXISTS zonas
                 (id SERIAL PRIMARY KEY, 
                  torneo_id INTEGER, nombre_zona TEXT, pareja TEXT)''')
    
    # Migración: Agregar columna bracket_pos si no existe (para lógica de llaves)
    run_action("ALTER TABLE partidos ADD COLUMN IF NOT EXISTS bracket_pos INTEGER")
    
    # Migración: Agregar columna estado_partido
    run_action("ALTER TABLE partidos ADD COLUMN IF NOT EXISTS estado_partido TEXT DEFAULT 'Próximo'")

    # Migración: Agregar columna ganador a partidos
    run_action("ALTER TABLE partidos ADD COLUMN IF NOT EXISTS ganador TEXT")

    # Migración: Agregar columnas de horario y cancha a partidos
    run_action("ALTER TABLE partidos ADD COLUMN IF NOT EXISTS horario TEXT")
    run_action("ALTER TABLE partidos ADD COLUMN IF NOT EXISTS cancha TEXT")

    # Tabla Fotos
    run_action('''CREATE TABLE IF NOT EXISTS fotos
                 (id SERIAL PRIMARY KEY, 
                  nombre TEXT, imagen BYTEA, fecha TEXT)''')
    
    # Migración: Agregar columnas de teléfono
    run_action("ALTER TABLE inscripciones ADD COLUMN IF NOT EXISTS telefono1 TEXT")
    run_action("ALTER TABLE inscripciones ADD COLUMN IF NOT EXISTS telefono2 TEXT")

    # Tabla Jugadores (Niveles)
    # Modificada para incluir credenciales y celular como ID lógico
    run_action('''CREATE TABLE IF NOT EXISTS jugadores
                 (id SERIAL PRIMARY KEY, 
                  dni TEXT UNIQUE, celular TEXT UNIQUE, password TEXT, nombre TEXT, apellido TEXT,
                  localidad TEXT, categoria_actual TEXT, categoria_anterior TEXT, foto BYTEA)''')
    
    # Migración: Agregar columna torneo_id a inscripciones si no existe
    run_action("ALTER TABLE inscripciones ADD COLUMN IF NOT EXISTS torneo_id INTEGER")

    # Migración: Agregar columnas nuevas a jugadores si no existen (para compatibilidad)
    run_action("ALTER TABLE jugadores ADD COLUMN IF NOT EXISTS celular TEXT UNIQUE")
    run_action("ALTER TABLE jugadores ADD COLUMN IF NOT EXISTS password TEXT")
    run_action("ALTER TABLE jugadores ADD COLUMN IF NOT EXISTS apellido TEXT")

    # Migración: Agregar columna estado_cuenta a jugadores
    run_action("ALTER TABLE jugadores ADD COLUMN IF NOT EXISTS estado_cuenta TEXT DEFAULT 'Pendiente'")

    # Migración: Agregar columna dni a jugadores
    run_action("ALTER TABLE jugadores ADD COLUMN IF NOT EXISTS dni TEXT")

    # Migración: Agregar columna es_puntuable a torneos
    run_action("ALTER TABLE torneos ADD COLUMN IF NOT EXISTS es_puntuable INTEGER DEFAULT 1")

    # Tabla Eventos (Afiches y Configuración Extra)
    run_action('''CREATE TABLE IF NOT EXISTS eventos
                 (id SERIAL PRIMARY KEY, 
                  torneo_id INTEGER, afiche TEXT)''')

    # Tabla Zonas Posiciones (Persistencia de tabla)
    run_action('''CREATE TABLE IF NOT EXISTS zonas_posiciones
                 (id SERIAL PRIMARY KEY, 
                  torneo_id INTEGER, nombre_zona TEXT, pareja TEXT,
                  pts INTEGER DEFAULT 0, pj INTEGER DEFAULT 0, 
                  pg INTEGER DEFAULT 0, pp INTEGER DEFAULT 0, 
                  sf INTEGER DEFAULT 0, sc INTEGER DEFAULT 0, ds INTEGER DEFAULT 0)''')

    # Tabla Ranking Puntos (Nueva para visualización de ranking global)
    run_action('''CREATE TABLE IF NOT EXISTS ranking_puntos
                 (id SERIAL PRIMARY KEY, 
                  torneo_id INTEGER, jugador TEXT, categoria TEXT, puntos INTEGER)''')

    # Tabla Partido en Vivo (Banner Home)
    run_action('''CREATE TABLE IF NOT EXISTS partido_en_vivo
                 (id SERIAL PRIMARY KEY, 
                  torneo TEXT, pareja1 TEXT, pareja2 TEXT, 
                  marcador TEXT)''')

def limpiar_cache():
    st.cache_data.clear()

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def guardar_inscripcion(torneo_id, j1, j2, loc, cat, pago, tel1, tel2):
    run_action("INSERT INTO inscripciones (torneo_id, jugador1, jugador2, localidad, categoria, pago_confirmado, telefono1, telefono2) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", 
              (torneo_id, j1, j2, loc, cat, 1 if pago else 0, tel1, tel2))
    limpiar_cache()

def crear_torneo(nombre, fecha, categoria, es_puntuable=True):
    if not st.session_state.get('es_admin', False): return None
    # Usamos RETURNING id para obtener el ID generado en Postgres
    new_id = run_action("INSERT INTO torneos (nombre, fecha, categoria, estado, es_puntuable) VALUES (%s, %s, %s, 'Abierto', %s) RETURNING id", 
              (nombre, str(fecha), categoria, 1 if es_puntuable else 0), return_id=True)
    limpiar_cache()
    return new_id

def registrar_resultado(torneo_id, p1, p2, resultado, instancia):
    if not st.session_state.get('es_admin', False): return
    run_action("INSERT INTO partidos (torneo_id, pareja1, pareja2, resultado, instancia) VALUES (%s, %s, %s, %s, %s)",
              (torneo_id, p1, p2, resultado, instancia))
    limpiar_cache()

@st.cache_data(ttl=600)
def get_data(query, params=None):
    conn = st.connection('postgresql', type='sql')
    # ttl=0 para evitar cacheo interno de st.connection y usar st.cache_data
    return conn.query(query, params=params, ttl=0)

def cargar_datos(query, params=None):
    """Función auxiliar para cargar datos directamente de la DB sin caché."""
    conn = st.connection('postgresql', type='sql')
    return conn.query(query, params=params, ttl=0)

def obtener_torneos_activos():
    """Obtiene la lista de torneos activos (estado 'Abierto')."""
    return cargar_datos("SELECT * FROM torneos WHERE estado = 'Abierto'")

def obtener_partido_en_vivo():
    """Obtiene el partido en vivo para el banner."""
    return cargar_datos("SELECT * FROM partido_en_vivo ORDER BY id DESC LIMIT 1")

def buscar_jugador_por_dni(dni):
    """Busca jugadores por DNI (Celular) en la tabla 'jugadores'."""
    return cargar_datos("SELECT * FROM jugadores WHERE celular = %s", params=(dni,))

def generar_fixture_automatico(torneo_id, programacion_dias):
    """Asigna horarios automáticamente a los partidos de zona dentro de rangos definidos."""
    if not st.session_state.get('es_admin', False):
        return False, "Acceso denegado. Debes ser administrador."

    # 1. Obtener partidos de zona para programar
    df_partidos = cargar_datos("SELECT id FROM partidos WHERE torneo_id = %s AND instancia = 'Zona' ORDER BY id ASC", (torneo_id,))
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
    run_action("UPDATE partidos SET horario = NULL, cancha = NULL WHERE torneo_id = %s AND instancia = 'Zona'", (torneo_id,))

    for idx, partido_id in enumerate(partidos_a_programar):
        horario_asignado = slots_disponibles[idx]
        horario_str = horario_asignado.strftime("%Y-%m-%d %H:%M")
        run_action("UPDATE partidos SET horario = %s, cancha = 'Cancha Central', estado_partido = 'Próximo' WHERE id = %s", (horario_str, int(partido_id)))
    
    limpiar_cache()
    return True, f"✅ Se programaron exitosamente {num_partidos} partidos en la Cancha Central."

def generar_zonas(torneo_id, categoria):
    if not st.session_state.get('es_admin', False): return False, "Acceso denegado"
    
    # 1. Obtener inscriptos confirmados de la categoría
    # Nota: Ahora filtramos por torneo_id
    df_insc = cargar_datos("SELECT jugador1, jugador2 FROM inscripciones WHERE torneo_id = %s AND pago_confirmado = 1", params=(torneo_id,))
    parejas = [f"{row['jugador1']} - {row['jugador2']}" for _, row in df_insc.iterrows()]
    
    if len(parejas) < 3:
        return False, f"Insuficientes inscriptos ({len(parejas)}) para armar zonas. Mínimo 3."

    random.shuffle(parejas)
    
    # 2. Lógica de distribución (Grupos de 3 o 4)
    n = len(parejas)
    q4 = 0
    q3 = 0
    found = False
    
    # Intentar maximizar grupos de 4
    for i in range(n // 4, -1, -1):
        rem = n - (i * 4)
        if rem % 3 == 0:
            q4 = i
            q3 = rem // 3
            found = True
            break
            
    if not found:
        return False, f"No se puede distribuir {n} parejas en grupos de 3 y 4 exactos."

    # 3. Guardar en DB
    run_action("DELETE FROM zonas WHERE torneo_id = %s", (torneo_id,)) # Limpiar zonas previas del torneo
    run_action("DELETE FROM zonas_posiciones WHERE torneo_id = %s", (torneo_id,)) # Limpiar tabla de posiciones
    run_action("DELETE FROM partidos WHERE torneo_id = %s AND instancia = 'Zona'", (torneo_id,)) # Limpiar fixture de zona previo
    
    idx = 0
    letras = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    zona_counter = 0
    
    # Insertar grupos de 4
    for _ in range(q4):
        nombre_z = f"Zona {letras[zona_counter]}"
        grupo = parejas[idx:idx+4]
        for p in grupo:
            run_action("INSERT INTO zonas (torneo_id, nombre_zona, pareja) VALUES (%s, %s, %s)", (torneo_id, nombre_z, p))
            # Inicializar tabla de posiciones
            run_action("INSERT INTO zonas_posiciones (torneo_id, nombre_zona, pareja) VALUES (%s, %s, %s)", (torneo_id, nombre_z, p))
        
        # Generar Partidos (Todos contra todos)
        # 0 vs 1, 2 vs 3, 0 vs 2, 1 vs 3, 0 vs 3, 1 vs 2
        cruces = [(0,1), (2,3), (0,2), (1,3), (0,3), (1,2)]
        for i1, i2 in cruces:
            run_action("INSERT INTO partidos (torneo_id, pareja1, pareja2, instancia, estado_partido) VALUES (%s, %s, %s, 'Zona', 'Próximo')", 
                      (torneo_id, grupo[i1], grupo[i2]))

        idx += 4
        zona_counter += 1
        
    # Insertar grupos de 3
    for _ in range(q3):
        nombre_z = f"Zona {letras[zona_counter]}"
        grupo = parejas[idx:idx+3]
        for p in grupo:
            run_action("INSERT INTO zonas (torneo_id, nombre_zona, pareja) VALUES (%s, %s, %s)", (torneo_id, nombre_z, p))
            # Inicializar tabla de posiciones
            run_action("INSERT INTO zonas_posiciones (torneo_id, nombre_zona, pareja) VALUES (%s, %s, %s)", (torneo_id, nombre_z, p))
        
        # Generar Partidos (Todos contra todos)
        # 0 vs 1, 0 vs 2, 1 vs 2
        cruces = [(0,1), (0,2), (1,2)]
        for i1, i2 in cruces:
            run_action("INSERT INTO partidos (torneo_id, pareja1, pareja2, instancia, estado_partido) VALUES (%s, %s, %s, 'Zona', 'Próximo')", 
                      (torneo_id, grupo[i1], grupo[i2]))

        idx += 3
        zona_counter += 1
        
    limpiar_cache()
    return True, f"Generadas {q4} zonas de 4 y {q3} zonas de 3, con sus respectivos partidos y tabla."

def actualizar_tabla_posiciones(torneo_id):
    """Recalcula los puntos de la tabla de posiciones basándose en los partidos jugados."""
    
    # Resetear valores
    run_action("UPDATE zonas_posiciones SET pts=0, pj=0, pg=0, pp=0, sf=0, sc=0, ds=0 WHERE torneo_id=%s", (torneo_id,))
    
    # Obtener partidos jugados
    df_partidos = cargar_datos("SELECT pareja1, pareja2, resultado, ganador FROM partidos WHERE torneo_id=%s AND instancia='Zona' AND resultado != ''", (torneo_id,))
    
    for _, row in df_partidos.iterrows():
        p1, p2, res, ganador = row['pareja1'], row['pareja2'], row['resultado'], row['ganador']
        # Lógica simplificada de sets (asumiendo formato "6-4 6-4")
        # Aquí se debería implementar un parser robusto de resultados
        # Por ahora, sumamos 1 PJ a cada uno.
        # Si hay ganador definido en la columna ganador (que deberíamos usar), sumamos PG.
        
        # Actualizar PJ
        run_action("UPDATE zonas_posiciones SET pj = pj + 1 WHERE torneo_id=%s AND pareja=%s", (torneo_id, p1))
        run_action("UPDATE zonas_posiciones SET pj = pj + 1 WHERE torneo_id=%s AND pareja=%s", (torneo_id, p2))
        
        # Intento básico de determinar ganador si no usamos la columna 'ganador'
        # Idealmente usar la columna 'ganador' de la tabla partidos
        if ganador:
            perdedor = p2 if ganador == p1 else p1
            run_action("UPDATE zonas_posiciones SET pts = pts + 3, pg = pg + 1 WHERE torneo_id=%s AND pareja=%s", (torneo_id, ganador))
            run_action("UPDATE zonas_posiciones SET pts = pts + 1, pp = pp + 1 WHERE torneo_id=%s AND pareja=%s", (torneo_id, perdedor))
            
    limpiar_cache()

def generar_bracket_inicial(torneo_id):
    if not st.session_state.get('es_admin', False): return False, "Acceso denegado"
    
    # Verificar si ya existe cuadro
    df_check = cargar_datos("SELECT count(*) as c FROM partidos WHERE torneo_id = %s AND bracket_pos IS NOT NULL", (torneo_id,))
    if df_check.iloc[0]['c'] > 0:
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
        run_action("INSERT INTO partidos (torneo_id, pareja1, pareja2, instancia, bracket_pos, resultado) VALUES (%s, %s, %s, %s, %s, '')",
                  (torneo_id, p1, p2, inst, pos))
    
    limpiar_cache()
    return True, "Cuadro generado correctamente."

def actualizar_bracket(partido_id, torneo_id, bracket_pos, resultado, ganador_nombre):
    if not st.session_state.get('es_admin', False): return
    
    # 1. Guardar resultado actual y el GANADOR
    run_action("UPDATE partidos SET resultado = %s, ganador = %s WHERE id = %s", (resultado, ganador_nombre, partido_id))
    
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
        run_action(f"UPDATE partidos SET {campo_destino} = %s WHERE torneo_id = %s AND bracket_pos = %s", 
                  (ganador_nombre, torneo_id, next_pos))
        
    limpiar_cache()

def actualizar_estado_partido(partido_id, nuevo_estado):
    if not st.session_state.get('es_admin', False): return
    run_action("UPDATE partidos SET estado_partido = %s WHERE id = %s", (nuevo_estado, partido_id))
    limpiar_cache()

def actualizar_marcador(partido_id, resultado):
    if not st.session_state.get('es_admin', False): return
    run_action("UPDATE partidos SET resultado = %s WHERE id = %s", (resultado, partido_id))
    limpiar_cache()

def guardar_foto(nombre, imagen):
    if not st.session_state.get('es_admin', False): return
    # Postgres usa BYTEA para binarios, pasamos los bytes directamente
    run_action("INSERT INTO fotos (nombre, imagen, fecha) VALUES (%s, %s, NOW())", 
              (nombre, imagen))
    limpiar_cache()

def guardar_jugador(celular, password, nombre, apellido, localidad, cat_actual, cat_anterior, foto_blob):
    if not st.session_state.get('es_admin', False): return
    # Usamos ON CONFLICT para emular INSERT OR REPLACE de SQLite
    sql = """
    INSERT INTO jugadores (celular, password, nombre, apellido, localidad, categoria_actual, categoria_anterior, foto, estado_cuenta) 
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Pendiente')
    ON CONFLICT (celular) DO UPDATE SET
    password = EXCLUDED.password,
    nombre = EXCLUDED.nombre,
    apellido = EXCLUDED.apellido,
    localidad = EXCLUDED.localidad,
    categoria_actual = EXCLUDED.categoria_actual,
    categoria_anterior = EXCLUDED.categoria_anterior,
    foto = EXCLUDED.foto;
    """
    run_action(sql, (celular, hash_password(password), nombre, apellido, localidad, cat_actual, cat_anterior, foto_blob if foto_blob else None))
    limpiar_cache()

def recategorizar_jugador(player_id, nueva_categoria):
    if not st.session_state.get('es_admin', False): return
    df = cargar_datos("SELECT categoria_actual FROM jugadores WHERE id = %s", (player_id,))
    if not df.empty:
        cat_anterior = df.iloc[0]['categoria_actual']
        run_action("UPDATE jugadores SET categoria_anterior = %s, categoria_actual = %s WHERE id = %s", 
                  (cat_anterior, nueva_categoria, player_id))
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
        # Validar DNI duplicado
        df = cargar_datos("SELECT * FROM jugadores WHERE dni = %s", (dni,))
        if not df.empty:
            return False, "El DNI ya está registrado."

        # Si no se provee password (registro manual admin), se usa el DNI como pass
        final_pass = password if password else dni

        run_action("INSERT INTO jugadores (dni, celular, password, nombre, apellido, categoria_actual, localidad, estado_cuenta) VALUES (%s, %s, %s, %s, %s, %s, %s, 'Pendiente')",
                  (dni, celular, hash_password(final_pass), nombre, apellido, categoria, localidad))
        limpiar_cache()
        return True, "Registro exitoso."
    except Exception as e:
        # Capturamos error genérico de DB (IntegrityError de sqlalchemy/psycopg2)
        return False, "El número de celular o DNI ya está registrado."

def eliminar_jugador(dni):
    if not st.session_state.get('es_admin', False): return
    run_action("DELETE FROM jugadores WHERE dni = %s", (dni,))
    limpiar_cache()

def autenticar_usuario(dni, password):
    df = cargar_datos("SELECT id, dni, nombre, apellido, localidad, categoria_actual, celular FROM jugadores WHERE dni = %s AND password = %s", (dni, hash_password(password)))
    if not df.empty:
        user = df.iloc[0]
        return {
            "id": user['id'], "dni": user['dni'], "nombre": user['nombre'], "apellido": user['apellido'],
            "localidad": user['localidad'], "categoria": user['categoria_actual'], "celular": user['celular']
        }
    return None

# Inicializar DB al arrancar
init_db()

# --- LOGO Y SIDEBAR ---
if logo:
    st.sidebar.image(logo, use_container_width=True)

# --- LOGIN / REGISTRO RÁPIDO (TOP SIDEBAR) ---
if 'usuario' in st.session_state:
    u = st.session_state['usuario']
    st.sidebar.markdown(f"""
    <div style='background-color: #1E1E1E; padding: 10px; border-radius: 8px; border-left: 4px solid #39FF14; margin-bottom: 10px;'>
        <div style='color: #fff; font-weight: bold;'>👤 {u['nombre']} {u['apellido']}</div>
        <div style='color: #aaa; font-size: 0.8rem;'>{u['categoria']} | {u['localidad']}</div>
    </div>
    """, unsafe_allow_html=True)
    if st.sidebar.button("Cerrar Sesión", key="logout_sidebar_top"):
        del st.session_state['usuario']
        st.rerun()
else:
    with st.sidebar.expander("🔐 Ingresar / Registrarse", expanded=True):
        l_dni = st.text_input("DNI", placeholder="Usuario", key="l_dni_side")
        l_pass = st.text_input("Contraseña", type="password", key="l_pass_side")
        if st.button("Entrar", key="btn_login_side", use_container_width=True):
            user = autenticar_usuario(l_dni, l_pass)
            if user:
                st.session_state['usuario'] = user
                st.rerun()
            else:
                st.error("Datos incorrectos")
        st.caption("¿No tienes cuenta? Ve a '👥 Jugadores' para registrarte.")

# --- LOGIN ADMIN ---
st.sidebar.markdown("---")
st.sidebar.subheader("🔐 Acceso Admin")
with st.sidebar.form("login_admin"):
    admin_user = st.text_input("Usuario")
    admin_pass = st.text_input("Contraseña", type="password")
    if st.form_submit_button("Ingresar"):
        if admin_user == st.secrets.get("USUARIO_ADMIN") and admin_pass == st.secrets.get("PASS_ADMIN"):
            st.session_state.es_admin = True
            st.success("Modo Admin Activo")
            st.rerun()
        else:
            st.error("Datos incorrectos")

if st.sidebar.button("Cerrar Sesión Admin") if st.session_state.es_admin else False:
    st.session_state.es_admin = False
    st.rerun()

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
                if r_dni and r_pass and r_nombre:
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

# --- CONTACTO Y REDES ---
st.sidebar.markdown("---")
st.sidebar.subheader("Contacto y Redes")
st.sidebar.link_button("📲 Consultas por WhatsApp", "https://wa.me/543455454907", type="primary", use_container_width=True)
st.sidebar.link_button("📸 Seguinos en Instagram", "https://www.instagram.com/rinconpadel.vg/", type="primary", use_container_width=True)

# --- NAVEGACIÓN PRINCIPAL ---
menu = ["📊 Torneos y Eventos", "👥 Jugadores", "📈 Ranking", "🏠 Mi Panel", "⚙️ Admin"]
choice = st.sidebar.radio("Navegación", menu)

if choice == "🏠 Mi Panel":
    if 'usuario' not in st.session_state:
        st.warning("Por favor inicia sesión para ver tu panel.")
        st.stop()
    
    u = st.session_state['usuario']
    
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
    
    st.title(f"🏠 Hola, {u['nombre']}!")
    
    # 1. Próximo Partido (Busca por apellido en partidos pendientes)
    search_term = u['apellido']
    df_next = get_data("SELECT * FROM partidos WHERE (pareja1 LIKE %s OR pareja2 LIKE %s) AND estado_partido != 'Finalizado' AND estado_partido != 'Disponible'", params=(f"%{search_term}%", f"%{search_term}%"))
    
    st.markdown("<div class='dashboard-card'><div class='dash-title'>🕒 Próximo Partido</div>", unsafe_allow_html=True)
    if not df_next.empty:
        match = df_next.iloc[0]
        st.markdown(f"""<div class='next-match'><h3 style='margin:0'>🎾 {match['pareja1']} vs {match['pareja2']}</h3><p style='color:#00E676; font-weight:bold; margin:5px 0'>{match['instancia']} | {match['estado_partido']}</p><p>📍 Cancha Central (Consultar Horario)</p></div>""", unsafe_allow_html=True)
    else:
        st.info("No tienes partidos programados próximamente.")
    st.markdown("</div>", unsafe_allow_html=True)
    
    # 2. Resumen Temporada & Ranking
    c1, c2 = st.columns(2)
    df_played = get_data("SELECT * FROM partidos WHERE (pareja1 LIKE %s OR pareja2 LIKE %s) AND estado_partido = 'Finalizado'", params=(f"%{search_term}%", f"%{search_term}%"))
    played = len(df_played)
    wins = sum(1 for _, r in df_played.iterrows() if r['ganador'] and search_term in r['ganador'])
    eff = (wins / played * 100) if played > 0 else 0
    
    with c1:
        st.markdown(f"""<div class='dashboard-card'><div class='dash-title'>📊 Resumen Temporada</div><div style='display:flex; justify-content:space-around; text-align:center'><div><div class='dash-stat'>{played}</div><div class='dash-sub'>Partidos</div></div><div><div class='dash-stat'>{wins}</div><div class='dash-sub'>Victorias</div></div><div><div class='dash-stat'>{int(eff)}%</div><div class='dash-sub'>Efectividad</div></div></div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class='dashboard-card'><div class='dash-title'>🏆 Ranking {u['categoria']}</div><div style='text-align:center'><div class='dash-stat'>#{random.randint(1, 15)}</div><div class='dash-sub'>Posición Actual</div><div style='margin-top:10px; font-size:0.8rem; color:#666'>Puntos: {wins * 100 + played * 50}</div></div></div>""", unsafe_allow_html=True)
        
    # 3. Accesos Rápidos
    st.markdown("### 🚀 Accesos Rápidos")
    b1, b2 = st.columns(2)
    if b1.button("📝 Inscribirme al próximo torneo", use_container_width=True):
        st.info("Ve a la pestaña Torneos > Inscripción")
    if b2.button("🤝 Buscar Pareja", use_container_width=True):
        st.info("Función próximamente disponible")

elif choice == "📊 Torneos y Eventos":
        # --- BANNER EN VIVO (COMPONENT) ---
        df_live = obtener_partido_en_vivo()
        if not df_live.empty:
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
        
        if df_torneos_all.empty:
            st.info("No hay eventos registrados en el sistema.")
        else:
            col_sel_evento, col_sel_cat = st.columns(2)
            
            with col_sel_evento:
                lista_eventos = df_torneos_all['nombre'].unique()
                evento_sel = st.selectbox("📅 Seleccionar Evento", lista_eventos)
            
            with col_sel_cat:
                # Filtrar categorías disponibles para el evento seleccionado
                df_eventos_filtrados = df_torneos_all[df_torneos_all['nombre'] == evento_sel]
                lista_categorias = df_eventos_filtrados['categoria'].unique()
                cat_sel = st.selectbox("🎾 Seleccionar Categoría", lista_categorias)
            
            # Obtener el ID del torneo específico (Evento + Categoría)
            torneo_data = df_eventos_filtrados[df_eventos_filtrados['categoria'] == cat_sel].iloc[0]
            torneo_id = int(torneo_data['id'])
            estado_torneo = torneo_data['estado']
            
            st.divider()
            
            # --- PESTAÑAS DINÁMICAS ---
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
                df_afiche = cargar_datos("SELECT afiche FROM eventos WHERE torneo_id = %s", params=(torneo_id,))
                if not df_afiche.empty and df_afiche.iloc[0]['afiche']:
                    ruta_afiche = df_afiche.iloc[0]['afiche']
                    if os.path.exists(ruta_afiche):
                        st.image(ruta_afiche, use_container_width=True)

                # Contar inscriptos
                cant_inscriptos = cargar_datos("SELECT count(*) as c FROM inscripciones WHERE torneo_id = %s", params=(torneo_id,)).iloc[0]['c']
                
                # Contar partidos jugados
                cant_partidos = cargar_datos("SELECT count(*) as c FROM partidos WHERE torneo_id = %s AND resultado != ''", params=(torneo_id,)).iloc[0]['c']

                # Cálculo de Duración
                fecha_texto = torneo_data['fecha']
                duracion_row = ""
                
                if " al " in str(fecha_texto):
                    try:
                        inicio_str, fin_str = fecha_texto.split(" al ")
                        anio_actual = datetime.now().year
                        f_ini = datetime.strptime(f"{inicio_str}/{anio_actual}", "%d/%m/%Y")
                        f_fin = datetime.strptime(f"{fin_str}/{anio_actual}", "%d/%m/%Y")
                        
                        # Manejo de cambio de año (ej: Dic a Ene)
                        if f_fin < f_ini:
                            f_fin = f_fin.replace(year=anio_actual + 1)
                            
                        dias = (f_fin - f_ini).days + 1
                        if dias > 1:
                            duracion_row = f"<tr><td>⏳ Duración</td><td>{dias} Jornadas</td></tr>"
                    except:
                        pass

                html_info_tabla = f"""
<table style="width:100%">
    <tr>
        <th style="width:40%">Concepto</th>
        <th>Detalle</th>
    </tr>
    <tr><td>📍 Estado</td><td>{estado_torneo}</td></tr>
    <tr><td>📅 Fechas</td><td>{fecha_texto}</td></tr>
    {duracion_row}
    <tr><td>🏷️ Categoría</td><td>{cat_sel}</td></tr>
    <tr><td>👥 Inscriptos</td><td>{cant_inscriptos} Parejas</td></tr>
    <tr><td>🎾 Partidos Jugados</td><td>{cant_partidos}</td></tr>
</table>
"""
                st.markdown(html_info_tabla, unsafe_allow_html=True)
                
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
                df_insc = cargar_datos("SELECT * FROM inscripciones WHERE torneo_id = %s", params=(torneo_id,))
                
                if df_insc.empty:
                    st.info("Aún no hay parejas inscriptas en este torneo.")
                else:
                    df_display = pd.DataFrame()
                    df_display['Pareja'] = df_insc['jugador1'] + ' - ' + df_insc['jugador2']
                    df_display['Localidad'] = df_insc['localidad']
                    df_display['Estado de Pago'] = df_insc['pago_confirmado'].apply(lambda x: '✅ Confirmado' if x == 1 else '⏳ Pendiente')
                    
                    st.dataframe(df_display, hide_index=True, use_container_width=True)

            # 3. CLASIFICACIÓN (ZONAS)
            with tab_clasificacion:
                st.markdown("<div class='zona-header'>FASE DE GRUPOS</div>", unsafe_allow_html=True)
                
                # Ahora leemos de zonas_posiciones que es persistente
                df_zonas = cargar_datos("SELECT * FROM zonas_posiciones WHERE torneo_id = %s ORDER BY nombre_zona, pts DESC, ds DESC", params=(torneo_id,))
                # También leemos los partidos de zona para mostrarlos en la tarjeta
                df_partidos_zona = cargar_datos("SELECT * FROM partidos WHERE torneo_id = %s AND instancia = 'Zona'", params=(torneo_id,))
                
                if df_zonas.empty:
                    st.warning("Aún no se han sorteado las zonas para este torneo.")
                else:
                    grupos = df_zonas.groupby('nombre_zona')
                    cols = st.columns(2)
                    idx = 0
                    
                    for nombre_zona, df_grupo in grupos:
                        with cols[idx % 2]:
                            # Tarjeta de Zona Estilizada
                            st.markdown(f"""
                            <div style='background-color: #121212; border: 1px solid #333; border-radius: 10px; padding: 15px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>
                                <h4 style='color: #39FF14; margin-top: 0; border-bottom: 1px solid #333; padding-bottom: 8px;'>{nombre_zona}</h4>
                            """, unsafe_allow_html=True)
                            
                            # Tabla de Posiciones
                            df_display = df_grupo[['pareja', 'pts', 'pj', 'pg', 'pp', 'ds']]
                            df_display.columns = ['Pareja', 'Pts', 'PJ', 'PG', 'PP', 'Dif']
                            st.dataframe(df_display, hide_index=True, use_container_width=True)
                            
                            # Enfrentamientos Internos (Mini Fixture)
                            st.markdown("<div style='margin-top: 15px; font-size: 0.85rem; color: #aaa; font-weight: bold; margin-bottom: 5px;'>⚔️ Enfrentamientos</div>", unsafe_allow_html=True)
                            
                            parejas_zona = df_grupo['pareja'].tolist()
                            matches_zona = df_partidos_zona[
                                (df_partidos_zona['pareja1'].isin(parejas_zona)) & 
                                (df_partidos_zona['pareja2'].isin(parejas_zona))
                            ]
                            
                            if not matches_zona.empty:
                                for _, m in matches_zona.iterrows():
                                    res = m['resultado'] if m['resultado'] else "vs"
                                    color_res = "#39FF14" if m['resultado'] else "#666"
                                    st.markdown(f"""
                                    <div style='display: flex; justify-content: space-between; align-items: center; background: #1E1E1E; padding: 8px; border-radius: 5px; margin-bottom: 4px; border-left: 3px solid #39FF14;'>
                                        <div style='font-size: 0.8rem; color: #eee;'>
                                            <div>{m['pareja1']}</div>
                                            <div>{m['pareja2']}</div>
                                        </div>
                                        <div style='font-weight: bold; color: {color_res}; font-size: 0.9rem;'>{res}</div>
                                    </div>
                                    """, unsafe_allow_html=True)
                            else:
                                st.caption("Sin partidos programados.")
                            
                            st.markdown("</div>", unsafe_allow_html=True)
                        idx += 1

            # 4. FIXTURE (Partidos de Zona)
            with tab_fixture:
                st.markdown("<div class='zona-header'>PARTIDOS PROGRAMADOS</div>", unsafe_allow_html=True)
                
                # Filtramos partidos que NO son de llave (bracket_pos IS NULL) o que tienen instancia de Zona
                df_fix = cargar_datos("SELECT * FROM partidos WHERE torneo_id = %s AND instancia = 'Zona' ORDER BY horario", params=(torneo_id,))
                
                if df_fix.empty:
                    st.info("No hay partidos de zona programados.")
                else:
                    st.dataframe(
                        df_fix[['horario', 'cancha', 'pareja1', 'pareja2', 'resultado', 'estado_partido']],
                        column_config={
                            "horario": "Horario",
                            "cancha": "Cancha",
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
                
                df_bracket = cargar_datos("SELECT * FROM partidos WHERE torneo_id = %s AND bracket_pos IS NOT NULL ORDER BY bracket_pos", params=(torneo_id,))
                
                if df_bracket.empty:
                    st.info("El cuadro de llaves aún no ha sido generado.")
                else:
                    # Reutilizamos estilos CSS del bracket
                    st.markdown("""
                    <style>
                        .bracket { display: flex; flex-direction: row; justify-content: space-between; overflow-x: auto; padding: 10px 0; }
                        .round { display: flex; flex-direction: column; justify-content: space-around; flex: 1; margin: 0 10px; min-width: 160px; }
                        .round-header { text-align: center; font-weight: bold; color: #00E676; margin-bottom: 10px; text-transform: uppercase; font-size: 0.8rem; border-bottom: 1px solid #333; }
                        .match-card { background: #121212; border: 1px solid #39FF14; border-radius: 8px; padding: 10px; margin: 5px 0; position: relative; box-shadow: 0 0 5px rgba(57, 255, 20, 0.2); }
                        .team-name { font-size: 0.8rem; color: #eee; margin-bottom: 2px; }
                        .match-result { font-size: 0.75rem; color: #00E676; text-align: right; font-weight: bold; }
                    </style>
                    """, unsafe_allow_html=True)

                    rounds = [
                        ("Octavos", df_bracket[df_bracket['bracket_pos'] <= 8]),
                        ("Cuartos", df_bracket[(df_bracket['bracket_pos'] > 8) & (df_bracket['bracket_pos'] <= 12)]),
                        ("Semis", df_bracket[(df_bracket['bracket_pos'] > 12) & (df_bracket['bracket_pos'] <= 14)]),
                        ("Final", df_bracket[df_bracket['bracket_pos'] == 15])
                    ]

                    html = "<div class='bracket'>"
                    for name, matches in rounds:
                        if not matches.empty:
                            html += f"<div class='round'><div class='round-header'>{name}</div>"
                            for _, row in matches.iterrows():
                                res = row['resultado'] if row['resultado'] else "vs"
                                p1 = row['pareja1'] if row['pareja1'] else "TBD"
                                p2 = row['pareja2'] if row['pareja2'] else "TBD"
                                html += f"""
                                <div class='match-card'>
                                    <div class='team-name'>{p1}</div>
                                    <div class='team-name'>{p2}</div>
                                    <div class='match-result'>{res}</div>
                                </div>"""
                            html += "</div>"
                    html += "</div>"
                    st.markdown(html, unsafe_allow_html=True)
    
    

elif choice == "👥 Jugadores":
    tab_jugadores, tab_h2h, tab_perfil = st.tabs(["👥 Listado de Jugadores", "🆚 H2H", "👤 Mi Perfil"])
    
    with tab_perfil:
        st.header("👤 Perfil de Jugador")
        if 'usuario' in st.session_state:
            u = st.session_state['usuario']
            st.success(f"Hola, {u['nombre']} {u['apellido']}!")
            st.info(f"Nivel Actual: {u['categoria']} | Localidad: {u['localidad']}")
            if st.button("Cerrar Sesión"):
                del st.session_state['usuario']
                st.rerun()
            
            st.markdown("---")
            with st.expander("⚙️ Configuración y Privacidad"):
                st.caption("Gestiona tus datos y privacidad.")
                if st.button("⚠️ Solicitar Eliminación de Cuenta (Derecho al Olvido)"):
                    run_action("DELETE FROM jugadores WHERE id = %s", (u['id'],))
                    del st.session_state['usuario']
                    st.success("Tu cuenta y datos han sido eliminados correctamente.")
                    st.rerun()
        else:
            tab1, tab2 = st.tabs(["Iniciar Sesión", "Registrarse"])
            
            with tab1:
                with st.form("login_form"):
                    l_dni = st.text_input("DNI")
                    l_pass = st.text_input("Contraseña", type="password")
                    if st.form_submit_button("Ingresar"):
                        user = autenticar_usuario(l_dni, l_pass)
                        if user:
                            st.session_state['usuario'] = user
                            st.success("Bienvenido!")
                            st.rerun()
                        else:
                            st.error("Credenciales incorrectas.")
            
            with tab2:
                with st.form("register_form"):
                    c1, c2 = st.columns(2)
                    r_nombre = c1.text_input("Nombre")
                    r_apellido = c2.text_input("Apellido")
                    r_dni = c1.text_input("DNI (Será tu usuario)")
                    r_cel = c2.text_input("Celular (Para notificaciones)")
                    r_pass = st.text_input("Contraseña", type="password")
                    r_loc = st.text_input("Localidad")
                    
                    cat_map = {1: "Libre", 2: "3ra", 3: "4ta", 4: "5ta", 5: "6ta", 6: "7ma", 7: "8va"}
                    r_cat_num = st.slider("Categoría Actual (1=Libre, 7=8va)", 1, 7, 5)
                    r_cat = cat_map[r_cat_num]
                    
                    if st.form_submit_button("Crear Cuenta"):
                        if r_dni and r_pass and r_nombre:
                            ok, msg = registrar_jugador_db(r_dni, r_nombre, r_apellido, r_cel, r_cat, r_loc, r_pass)
                            if ok: st.success(msg)
                            else: st.error(msg)
                        else:
                            st.warning("Completa todos los campos obligatorios.")

    with tab_jugadores:
        st.header("🎖️ Categorías y Niveles")
        
        # --- VISTA PÚBLICA ---
        st.subheader("Listado Oficial de Niveles")
        
        with st.expander("➕ Registrar Nuevo Jugador"):
            with st.form("form_alta_jugador_rapida"):
                c1, c2 = st.columns(2)
                n_nombre = c1.text_input("Nombre")
                n_apellido = c2.text_input("Apellido")
                n_dni = c1.text_input("DNI")
                n_cel = c2.text_input("Celular")
                n_cat = st.selectbox("Categoría", ["Libre", "3ra", "4ta", "5ta", "6ta", "7ma", "8va"])
                
                if st.form_submit_button("Registrar"):
                    if n_dni and n_nombre and n_apellido:
                        ok, msg = registrar_jugador_db(n_dni, n_nombre, n_apellido, n_cel, n_cat, "", n_dni)
                        if ok: st.success("Jugador registrado correctamente."); st.rerun()
                        else: st.error(msg)
                    else: st.warning("Completa los campos obligatorios.")

        # Buscador
        search_q = st.text_input("🔍 Buscar por Apellido", placeholder="Escribe el apellido del jugador...")
        
        df_jugadores = get_data("SELECT * FROM jugadores ORDER BY apellido, nombre")
        
        if search_q:
            # Filtrado insensible a mayúsculas/minúsculas
            mask = df_jugadores['apellido'].str.contains(search_q, case=False, na=False) | \
                   df_jugadores['nombre'].str.contains(search_q, case=False, na=False)
            df_jugadores = df_jugadores[mask]
        
        if not df_jugadores.empty:
            # Lógica de Badge de Movimiento
            def get_movement(row):
                cats = {"Libre": 1, "3ra": 3, "4ta": 4, "5ta": 5, "6ta": 6, "7ma": 7, "8va": 8}
                curr = cats.get(row['categoria_actual'], 99)
                prev = cats.get(row['categoria_anterior'], 99)
                
                if not row['categoria_anterior'] or row['categoria_anterior'] == "-":
                    return "➖ Neutro"
                
                if curr < prev: # Ej: Era 7ma (7) y ahora 6ta (6) -> Ascenso
                    return "▲ Ascenso"
                elif curr > prev:
                    return "▼ Descenso"
                else:
                    return "➖ Neutro"

            df_jugadores['Tendencia'] = df_jugadores.apply(get_movement, axis=1)
            df_jugadores['celular_oculto'] = df_jugadores['celular'].apply(mask_phone_number)
            
            # Estética de Tarjetas (Roca Padel Style)
            st.markdown("""
            <style>
            .player-card {
                background-color: #1E1E1E;
                border: 1px solid #333;
                border-radius: 12px;
                padding: 15px;
                margin-bottom: 15px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.2);
                transition: transform 0.2s, border-color 0.2s;
            }
            .player-card:hover {
                transform: translateY(-3px);
                border-color: #00E676;
            }
            .player-header {
                display: flex;
                align-items: center;
                gap: 12px;
                margin-bottom: 8px;
            }
            .player-avatar {
                width: 45px;
                height: 45px;
                background-color: #333;
                color: #fff;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.2rem;
                font-weight: bold;
            }
            .player-name {
                font-size: 1.1rem;
                font-weight: bold;
                color: #fff;
                line-height: 1.2;
            }
            .player-cat {
                font-size: 0.85rem;
                color: #00E676;
                font-weight: bold;
                text-transform: uppercase;
            }
            .player-body {
                font-size: 0.9rem;
                color: #aaa;
                margin-top: 8px;
            }
            .player-footer {
                margin-top: 10px;
                padding-top: 8px;
                border-top: 1px solid #333;
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 0.8rem;
            }
            </style>
            """, unsafe_allow_html=True)

            cols = st.columns(3)
            for i, (idx, row) in enumerate(df_jugadores.iterrows()):
                with cols[i % 3]:
                    trend_color = "#888"
                    if "Ascenso" in row['Tendencia']: trend_color = "#00E676"
                    elif "Descenso" in row['Tendencia']: trend_color = "#FF4B4B"
                    
                    initials = f"{row['nombre'][0]}{row['apellido'][0]}" if row['nombre'] and row['apellido'] else "👤"
                    
                    st.markdown(f"""
                    <div class="player-card">
                        <div class="player-header">
                            <div class="player-avatar">{initials}</div>
                            <div>
                                <div class="player-name">{row['nombre']} {row['apellido']}</div>
                                <div class="player-cat">{row['categoria_actual']}</div>
                            </div>
                        </div>
                        <div class="player-body">
                            📍 {row['localidad'] if row['localidad'] else 'Sin localidad'}<br>
                            📱 {mask_phone_number(row['celular'])}
                        </div>
                        <div class="player-footer">
                            <span style="color: {trend_color}; font-weight: bold;">{row['Tendencia']}</span>
                            <span style="color: #555;">ID: {row['id']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No se encontraron jugadores.")

    with tab_h2h:
        st.markdown("""
        <style>
            .h2h-card { background-color: #000000; border: 2px solid #39FF14; border-radius: 10px; padding: 20px; text-align: center; box-shadow: 0 0 15px rgba(57, 255, 20, 0.3); }
            .h2h-stat-val { font-size: 2rem; font-weight: 900; color: #fff; }
            .h2h-stat-label { font-size: 0.9rem; color: #39FF14; text-transform: uppercase; letter-spacing: 1px; }
            .vs-badge { font-size: 3rem; font-weight: bold; color: #39FF14; text-align: center; margin-top: 20px; }
        </style>
        """, unsafe_allow_html=True)
        
        st.header("🆚 Comparativa Head-to-Head")
        
        # Selectores de Jugadores
        all_players = get_data("SELECT nombre, apellido FROM jugadores ORDER BY apellido")
        if not all_players.empty:
            player_options = [f"{row['nombre']} {row['apellido']}" for _, row in all_players.iterrows()]
            
            c1, c2 = st.columns(2)
            p1_sel = c1.selectbox("Jugador 1", player_options, index=0)
            p2_sel = c2.selectbox("Jugador 2", player_options, index=1 if len(player_options) > 1 else 0)
            
            if p1_sel and p2_sel:
                # --- LÓGICA DE DATOS ---
                # 1. Historial Directo
                # Buscamos partidos donde ambos nombres aparezcan en las parejas
                # Nota: Esto busca por string, idealmente usar IDs en el futuro
                df_h2h = get_data("""
                    SELECT * FROM partidos 
                    WHERE (pareja1 LIKE %s OR pareja2 LIKE %s) 
                    AND (pareja1 LIKE %s OR pareja2 LIKE %s)
                    AND ganador IS NOT NULL
                """, params=(f"%{p1_sel}%", f"%{p1_sel}%", f"%{p2_sel}%", f"%{p2_sel}%"))
                
                p1_wins_h2h = 0
                p2_wins_h2h = 0
                
                for _, row in df_h2h.iterrows():
                    if row['ganador'] and p1_sel in row['ganador']:
                        p1_wins_h2h += 1
                    elif row['ganador'] and p2_sel in row['ganador']:
                        p2_wins_h2h += 1
                
                # 2. Estadísticas Individuales (Títulos y Efectividad Global)
                def get_stats(player_name):
                    # Títulos (Ganador en instancia Final)
                    titles = get_data("SELECT count(*) as c FROM partidos WHERE instancia = 'Final' AND ganador LIKE %s", params=(f"%{player_name}%",)).iloc[0]['c']
                    
                    # Efectividad (Partidos ganados / jugados)
                    matches = get_data("SELECT * FROM partidos WHERE (pareja1 LIKE %s OR pareja2 LIKE %s) AND ganador IS NOT NULL", params=(f"%{player_name}%", f"%{player_name}%"))
                    total = len(matches)
                    wins = sum(1 for _, r in matches.iterrows() if r['ganador'] and player_name in r['ganador'])
                    eff = (wins / total * 100) if total > 0 else 0
                    return titles, eff

                t1, eff1 = get_stats(p1_sel)
                t2, eff2 = get_stats(p2_sel)

                st.markdown("---")
                
                # --- VISUALIZACIÓN ---
                col_p1, col_vs, col_p2 = st.columns([2, 1, 2])
                
                with col_p1:
                    st.markdown(f"<div class='h2h-card'><h3>{p1_sel}</h3><div class='h2h-stat-val'>{p1_wins_h2h}</div><div class='h2h-stat-label'>Victorias Directas</div><hr style='border-color:#333'><div class='h2h-stat-val'>{t1}</div><div class='h2h-stat-label'>Títulos</div><div class='h2h-stat-val'>{eff1:.1f}%</div><div class='h2h-stat-label'>Efectividad</div></div>", unsafe_allow_html=True)
                
                with col_vs:
                    st.markdown("<div class='vs-badge'>VS</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='text-align:center; color:#888; margin-top:10px;'>{len(df_h2h)} Partidos<br>Jugados</div>", unsafe_allow_html=True)

                with col_p2:
                    st.markdown(f"<div class='h2h-card'><h3>{p2_sel}</h3><div class='h2h-stat-val'>{p2_wins_h2h}</div><div class='h2h-stat-label'>Victorias Directas</div><hr style='border-color:#333'><div class='h2h-stat-val'>{t2}</div><div class='h2h-stat-label'>Títulos</div><div class='h2h-stat-val'>{eff2:.1f}%</div><div class='h2h-stat-label'>Efectividad</div></div>", unsafe_allow_html=True)

        else:
            st.info("No hay suficientes jugadores para comparar.")

elif choice == "🎾 Torneos":
    tab_cal, tab_insc, tab_clasif, tab_cuadros, tab_horarios, tab_partidos = st.tabs(["🏆 Calendario", "📝 Inscripción", "🔢 Clasificación", "🏆 Llave Final", "📅 Horarios", "🎾 Partidos Jugados"])
    
    with tab_cal:
        st.header("🏆 Gestión de Torneos")
        if st.session_state.es_admin:
            with st.expander("➕ Crear Nuevo Torneo", expanded=False):
                with st.form("form_torneo"):
                    t_nombre = st.text_input("Nombre del Torneo")
                    col1, col2 = st.columns(2)
                    with col1:
                        t_fecha = st.date_input("Fecha de Inicio")
                    with col2:
                        t_cat = st.selectbox("Categoría Principal", ["Libre", "6ta", "7ma", "Suma 12"])
                    
                    if st.form_submit_button("Crear Torneo"):
                        crear_torneo(t_nombre, t_fecha, t_cat)
                        st.success("Torneo creado exitosamente")
    
        st.markdown("### 🗓️ Calendario de Torneos")
        df_torneos = get_data("SELECT * FROM torneos ORDER BY id DESC")
        if not df_torneos.empty:
            # Layout en grilla para torneos
            cols = st.columns(2)
            for _, row in df_torneos.iterrows():
                # Calcular cupo (simulado o real si tuvieramos max_cupo)
                inscritos = get_data("SELECT count(*) as c FROM inscripciones WHERE torneo_id=%s", params=(row['id'],)).iloc[0]['c']
                cupo_max = 16 # Ejemplo fijo
                progreso = min(inscritos / cupo_max, 1.0)
                
                with cols[_ % 2]:
                    st.markdown(f"""
                    <div class='card'>
                        <div class='card-title'>{row['nombre']}</div>
                        <div class='card-text'>
                            📅 {row['fecha']}<br>
                            🎾 Categoría: <b>{row['categoria']}</b><br>
                            📍 Estado: <span class='badge badge-en-juego'>{row['estado']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.caption(f"Inscriptos: {inscritos} / {cupo_max}")
                    st.progress(progreso)
        else:
            st.info("No hay torneos registrados.")
        
    # --- GESTIÓN DE ZONAS ---
        if st.session_state.es_admin:
            st.markdown("---")
            st.subheader("🔀 Generador de Zonas")
            
            lista_torneos = get_data("SELECT id, nombre, categoria FROM torneos")
            if not lista_torneos.empty:
                col_sel, col_btn = st.columns([3, 1])
                with col_sel:
                    t_selec = st.selectbox("Seleccionar Torneo para armar Zonas", lista_torneos['nombre'].unique())
                
                row_t = lista_torneos[lista_torneos['nombre'] == t_selec].iloc[0]
                t_id = int(row_t['id'])
                t_cat = row_t['categoria']
                
                with col_btn:
                    st.write("") # Spacer
                    st.write("") 
                    if st.button(f"Generar Zonas ({t_cat})"):
                        success, msg = generar_zonas(t_id, t_cat)
                        if success:
                            st.success(msg)
                        else:
                            st.error(msg)
                
                # Visualizar Zonas
                df_zonas = get_data("SELECT * FROM zonas WHERE torneo_id = %s ORDER BY nombre_zona", params=(t_id,))
                if not df_zonas.empty:
                    grupos = df_zonas.groupby('nombre_zona')
                    cols = st.columns(3)
                    for i, (nombre, grupo) in enumerate(grupos):
                        with cols[i % 3]:
                            st.markdown(f"<div class='card'><div class='card-title'>{nombre}</div>", unsafe_allow_html=True)
                            # Mostrar parejas del grupo
                            tabla = pd.DataFrame({"Pareja": grupo['pareja']})
                            st.dataframe(tabla, hide_index=True, use_container_width=True)
                            st.markdown("</div>", unsafe_allow_html=True)

    with tab_insc:
        st.header("📝 Inscripción de Parejas")
        
        # Seleccionar Torneo primero para validar categoría
        torneos_disp = get_data("SELECT id, nombre, categoria FROM torneos WHERE estado = 'Abierto'")
        
        if torneos_disp.empty:
            st.warning("No hay torneos abiertos para inscripción.")
        else:
            torneo_sel_nombre = st.selectbox("Selecciona el Torneo", torneos_disp['nombre'])
            torneo_data = torneos_disp[torneos_disp['nombre'] == torneo_sel_nombre].iloc[0]
            torneo_id = int(torneo_data['id'])
            cat_torneo = torneo_data['categoria']
            
            st.info(f"Estás inscribiéndote al torneo: **{torneo_sel_nombre}** (Categoría: {cat_torneo})")

            # --- FORMULARIO SUMA 13 ---
            if cat_torneo == "Suma 13" or st.checkbox("Mostrar Inscripción Suma 13"):
                st.markdown("---")
                st.markdown("""
                <style>
                    div[data-testid="stForm"] {
                        background-color: #121212;
                        border: 2px solid #00C853;
                        padding: 20px;
                        border-radius: 15px;
                        box-shadow: 0 0 15px rgba(0, 200, 83, 0.3);
                    }
                </style>
                """, unsafe_allow_html=True)
                
                with st.form("form_suma_13"):
                    st.markdown("<h3 style='color: #00C853; text-align: center;'>🎾 Inscripción Suma 13</h3>", unsafe_allow_html=True)
                    st.write(f"Inscribiéndote como: **{u['nombre']} {u['apellido']}** (Categoría: {u['categoria']})")
                    st.write("Ingrese el DNI (Celular) de tu compañero para validar la suma de categorías.")

                    c1, c2 = st.columns(2)
                    #dni1 = c1.text_input("DNI/Celular Jugador 1")
                    dni2 = c2.text_input("DNI/Celular Jugador 2")

                    submitted = st.form_submit_button("Inscribirse")

                    if submitted:
                        if dni2:
                            dni1 = u['dni'] # Usar el DNI del usuario logueado
                            # 1. Buscar jugadores en DB
                            p1 = buscar_jugador_por_dni(dni1)
                            p2 = buscar_jugador_por_dni(dni2)

                            if not p1.empty and not p2.empty:
                                cat1 = p1.iloc[0]['categoria_actual']
                                nombre1 = f"{p1.iloc[0]['nombre']} {p1.iloc[0]['apellido']}"
                                localidad = p1.iloc[0]['localidad']

                                cat2 = p2.iloc[0]['categoria_actual']
                                
                                # 2. Extraer nivel numérico
                                def get_nivel(cat_str):
                                    match = re.search(r'\d+', str(cat_str))
                                    return int(match.group()) if match else 8 # Default a 8va si no encuentra número
                                
                                n1 = get_nivel(cat1)
                                n2 = get_nivel(cat2)
                                suma = n1 + n2
                                
                                nombre2 = f"{p2.iloc[0]['nombre']} {p2.iloc[0]['apellido']}"
                                # 3. Validar Suma
                                if suma <= 13:
                                    guardar_inscripcion(torneo_id, nombre1, nombre2, localidad, "Suma 13", False, dni1, dni2)
                                    st.success(f"✅ Inscripción Exitosa. Suma: {suma} ({cat1} + {cat2}). Estado: Pendiente de Pago.")
                                else:
                                    st.markdown(f"<div style='color: #FF4B4B; font-weight: bold; font-size: 1.2rem; text-align: center; border: 1px solid #FF4B4B; padding: 10px; border-radius: 5px;'>❌ La suma de categorías ({suma}) excede el límite de 13</div>", unsafe_allow_html=True)
                            else:
                                st.error("Uno o ambos jugadores no fueron encontrados en la base de datos.")
                        else:
                            st.warning("Por favor ingrese el DNI/Celular de tu compañero.")
            # --- MODO ADMINISTRADOR ---
            if st.session_state.es_admin:
                st.subheader("Modo Admin: Inscripción Manual")
                with st.form("form_inscripcion_admin"):
                    c1, c2 = st.columns(2)
                    # Jugador 1
                    j1_nombre = c1.text_input("Jugador 1 (Nombre)")
                    j1_cat = c1.selectbox("Categoría J1", ["Libre", "3ra", "4ta", "5ta", "6ta", "7ma", "8va"], index=4)
                    j1_tel = c1.text_input("Teléfono J1")
                    
                    # Jugador 2
                    j2_nombre = c2.text_input("Jugador 2 (Nombre)")
                    j2_tel = c2.text_input("Teléfono J2")
                    localidad = st.text_input("Localidad Pareja")
                    
                    pago = st.checkbox("Pago Confirmado")
                    
                    if st.form_submit_button("Inscribir Pareja"):
                        # Validar Categoría J1
                        ok, msg = validar_nivel(j1_cat, cat_torneo)
                        if not ok:
                            st.error(f"Error J1: {msg}")
                        else:
                            guardar_inscripcion(torneo_id, j1_nombre, j2_nombre, localidad, cat_torneo, pago, j1_tel, j2_tel)
                            st.success(f"Pareja {j1_nombre} - {j2_nombre} inscripta correctamente.")

            # --- MODO JUGADOR ---
            elif 'usuario' in st.session_state:
                u = st.session_state['usuario']
                st.subheader(f"Inscribirme como: {u['nombre']} {u['apellido']}")
                
                # Validación automática de categoría
                ok_val, msg_val = validar_nivel(u['categoria'], cat_torneo)
                
                if not ok_val:
                    st.error(f"⛔ {msg_val}")
                    st.warning("No puedes inscribirte en este torneo debido a las reglas de nivel.")
                else:
                    with st.form("form_inscripcion_player"):
                        st.write("Datos de tu compañero:")
                        c1, c2 = st.columns(2)
                        p_nombre = c1.text_input("Nombre del Compañero")
                        p_tel = c2.text_input("Teléfono del Compañero")
                        
                        if st.form_submit_button("Confirmar Inscripción"):
                            if p_nombre and p_tel:
                                nombre_completo_j1 = f"{u['nombre']} {u['apellido']}"
                                guardar_inscripcion(torneo_id, nombre_completo_j1, p_nombre, u['localidad'], cat_torneo, False, u['celular'], p_tel) # Usamos celular para contacto
                                st.success("¡Inscripción enviada! Recuerda abonar la seña para confirmar tu lugar.")
                            else:
                                st.error("Faltan datos del compañero.")
            
            # --- MODO VISITANTE ---
            else:
                st.info("🔒 Debes iniciar sesión para inscribirte.")
                st.markdown("Ve a la sección **👤 Mi Perfil** para entrar o registrarte.")

        st.subheader("📋 Lista de Inscriptos")
        # Mostrar solo inscriptos del torneo seleccionado si hay uno, sino todos
        if not torneos_disp.empty:
            df_inscriptos = get_data("SELECT * FROM inscripciones WHERE torneo_id = %s ORDER BY id DESC", params=(torneo_id,))
        else:
            df_inscriptos = pd.DataFrame()
        
        if not df_inscriptos.empty:
            for _, row in df_inscriptos.iterrows():
                # Indicador visual de pago
                color_pago = "#00E676" if row['pago_confirmado'] else "#ff4b4b"
                texto_pago = "PAGO CONFIRMADO" if row['pago_confirmado'] else "PAGO PENDIENTE"
                
                st.markdown(f"""
                <div class='card' style='display: flex; align-items: center; justify-content: space-between;'>
                    <div style='display: flex; align-items: center; gap: 15px;'>
                        <div style='font-size: 2rem;'>👤</div>
                        <div>
                            <div style='font-weight: bold; color: #1E1E1E; font-size: 1.1rem;'>{row['jugador1']} & {row['jugador2']}</div>
                            <div style='color: #555; font-size: 0.9rem;'>📍 {row['localidad']} | 🏷️ {row['categoria']}</div>
                        </div>
                    </div>
                    <div style='border: 1px solid {color_pago}; color: {color_pago}; padding: 5px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: bold;'>
                        {texto_pago}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Aún no hay inscriptos.")

    with tab_clasif:
        st.header("🔢 Tabla de Posiciones")
        st.subheader("Grupo A")
        
        # Datos simulados de 4 parejas
        data_clasif = [
            ["Agustín Tapia - Arturo Coello", 9, 3, 3, 0, 6, 0, 6, 36, 12, 24],
            ["Ale Galán - Fede Chingotto", 6, 3, 2, 1, 4, 2, 2, 30, 20, 10],
            ["Juan Lebrón - Paquito Navarro", 3, 3, 1, 2, 2, 4, -2, 20, 30, -10],
            ["Franco Stupaczuk - Martín Di Nenno", 0, 3, 0, 3, 0, 6, -6, 12, 36, -24]
        ]
        
        columns_clasif = ["Participantes", "Pts", "PJ", "PG", "PP", "SF", "SC", "DS", "GF", "GC", "DG"]
        
        df_clasif = pd.DataFrame(data_clasif, columns=columns_clasif)
        
        st.dataframe(df_clasif, hide_index=True, use_container_width=True)

    with tab_cuadros:
        st.header("🏆 Llave Final")
        
        torneos = get_data("SELECT id, nombre FROM torneos")
        if not torneos.empty:
            torneo_sel = st.selectbox("Seleccionar Torneo", torneos['nombre'], key="sel_torneo_cuadros")
            torneo_id = torneos[torneos['nombre'] == torneo_sel]['id'].values[0]
            
            # Botón para generar estructura si no existe
            if st.session_state.es_admin:
                if st.button("Generar Cuadro (Octavos -> Final)"):
                    ok, msg = generar_bracket_inicial(torneo_id)
                    if ok: st.success(msg)
                    else: st.warning(msg)
            
            st.markdown("---")
            
            # Visualización del Bracket
            df_partidos = get_data("SELECT * FROM partidos WHERE torneo_id = %s AND bracket_pos IS NOT NULL ORDER BY bracket_pos", params=(torneo_id,))
            
            if not df_partidos.empty:
                # Estilos CSS para el Bracket
                st.markdown("""
                <style>
                    .bracket { display: flex; flex-direction: row; justify-content: space-between; overflow-x: auto; padding: 10px 0; }
                    .round { display: flex; flex-direction: column; justify-content: space-around; flex: 1; margin: 0 10px; min-width: 160px; }
                    .round-header { text-align: center; font-weight: bold; color: #00E676; margin-bottom: 10px; text-transform: uppercase; font-size: 0.9rem; border-bottom: 2px solid #eee; padding-bottom: 5px; }
                    .match-card { background: white; border: 1px solid #ddd; border-radius: 8px; padding: 10px; margin: 5px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); position: relative; }
                    .match-card::before { content: ""; position: absolute; top: 50%; left: -10px; width: 10px; height: 1px; background: #ddd; }
                    .match-card::after { content: ""; position: absolute; top: 50%; right: -10px; width: 10px; height: 1px; background: #ddd; }
                    .round:first-child .match-card::before { display: none; }
                    .round:last-child .match-card::after { display: none; }
                    .team-name { font-size: 0.85rem; font-weight: 600; color: #333; margin-bottom: 4px; }
                    .match-result { font-size: 0.8rem; color: #00E676; font-weight: bold; text-align: right; }
                </style>
                """, unsafe_allow_html=True)

                rounds = [
                    ("Octavos de Final", df_partidos[df_partidos['bracket_pos'] <= 8]),
                    ("Cuartos de Final", df_partidos[(df_partidos['bracket_pos'] > 8) & (df_partidos['bracket_pos'] <= 12)]),
                    ("Semifinal", df_partidos[(df_partidos['bracket_pos'] > 12) & (df_partidos['bracket_pos'] <= 14)]),
                    ("Final", df_partidos[df_partidos['bracket_pos'] == 15])
                ]

                html = "<div class='bracket'>"
                for name, matches in rounds:
                    html += f"<div class='round'><div class='round-header'>{name}</div>"
                    for _, row in matches.iterrows():
                        res = row['resultado'] if row['resultado'] else "vs"
                        html += f"""
                        <div class='match-card'>
                            <div class='team-name'>{row['pareja1']}</div>
                            <div class='team-name'>{row['pareja2']}</div>
                            <div class='match-result'>{res}</div>
                        </div>"""
                    html += "</div>"
                html += "</div>"
                st.markdown(html, unsafe_allow_html=True)

                # Admin Controls
                if st.session_state.es_admin:
                    st.markdown("### 📝 Cargar Resultados")
                    with st.expander("Abrir Panel de Carga"):
                        for _, row in df_partidos.iterrows():
                            c1, c2, c3 = st.columns([3, 2, 2])
                            with c1: st.write(f"**{row['instancia']}**: {row['pareja1']} vs {row['pareja2']}")
                            with c2: 
                                new_res = st.text_input("Resultado", value=row['resultado'], key=f"res_{row['id']}", label_visibility="collapsed")
                            with c3:
                                winner = st.selectbox("Ganador", [row['pareja1'], row['pareja2']], key=f"win_{row['id']}", index=None, placeholder="Ganador...")
                                if st.button("Guardar", key=f"btn_{row['id']}"):
                                    if winner and new_res:
                                        actualizar_bracket(row['id'], torneo_id, row['bracket_pos'], new_res, winner)
                                        st.success("Guardado")
                                        st.rerun()

        else:
            st.warning("Crea un torneo primero.")

    with tab_horarios:
        st.header("📅 Grilla de Horarios - Cancha Central")
        
        # Buscador con efecto en tiempo real
        col_search, _ = st.columns([1, 2])
        with col_search:
            search_query = st.text_input("🔍 Buscar Jugador", placeholder="Escribe un apellido...")

        # Configuración del Timeline (08:00 a 23:30)
        start_time = pd.Timestamp("2024-01-01 08:00")
        end_time = pd.Timestamp("2024-01-01 23:30")
        match_duration = pd.Timedelta(minutes=90) # 1h 30m por partido
        break_duration = pd.Timedelta(minutes=15) # 15m descanso
        
        # Obtenemos partidos reales con horario asignado
        df_partidos = get_data("SELECT * FROM partidos WHERE horario IS NOT NULL ORDER BY horario ASC")
        matches_list = df_partidos.to_dict('records') if not df_partidos.empty else []
        
        if not matches_list:
            st.info("No hay partidos programados con horario asignado.")
        
        st.markdown("---")
        
        for match in matches_list:
            # Parsear horario de DB
            try:
                match_time = datetime.strptime(match['horario'], "%Y-%m-%d %H:%M")
                time_label = match_time.strftime("%H:%M")
            except:
                continue
            
            # Lógica de Estilos Dinámicos
            bg_color = "#FFFFFF"
            text_color = "#333333"
            border_style = "border-left: 6px solid #00E676;"
            
            if match and search_query:
                q = search_query.lower()
                if q in match['pareja1'].lower() or q in match['pareja2'].lower():
                    bg_color = "#00E676"
                    text_color = "#1E1E1E"
                    border_style = "border: 2px solid #333;"

            # Determinar Badge de Estado
            def get_badge_html(estado):
                if not estado or estado == 'Disponible': return ""
                configs = {
                    'Próximo': {'emoji': '🕒', 'class': 'badge-proximo'},
                    'En Juego': {'emoji': '🎾', 'class': 'badge-en-juego'},
                    'Finalizado': {'emoji': '✅', 'class': 'badge-finalizado'},
                    'Retrasado': {'emoji': '⚠️', 'class': 'badge-retrasado'}
                }
                data = configs.get(estado, configs['Próximo'])
                return f"<span class='badge {data['class']}'>{data['emoji']} {estado}</span>"

            estado = match.get('estado_partido', 'Próximo')
            badge_html = get_badge_html(estado)

            # Contenedor del Partido
            with st.container():
                html_content = f"""
                <div class='card' style='background-color: {bg_color}; {border_style} transition: all 0.3s ease; margin-bottom: 10px;'>
                    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
                        <div style='color: {text_color if bg_color == "#00E676" else "#00E676"}; font-size: 1.1rem; font-weight: bold;'>
                            ⏰ {time_label} | {match.get('cancha', 'Cancha Central')} {badge_html}
                        </div>
                        <div style='background: {text_color if bg_color == "#00E676" else "#00E676"}; color: {bg_color if bg_color == "#00E676" else "#1E1E1E"}; padding: 2px 8px; border-radius: 12px; font-weight: bold; font-size: 0.7rem;'>ID: {match['id']}</div>
                    </div>
                    <div style='font-size: 1.2rem; font-weight: bold; color: {text_color};'>
                        {f"🎾 {match['pareja1']} vs {match['pareja2']}"}
                    </div>
                    <div style='color: {text_color if bg_color == "#00E676" else "#888"}; font-size: 0.85rem; margin-top: 4px;'>
                        {match['instancia']}
                    </div>
                </div>
                """
                st.markdown(html_content, unsafe_allow_html=True)

                # --- MARCADOR EN VIVO ---
                if estado == 'En Juego':
                    st.markdown(f"""
                    <div style='text-align: center; padding: 10px; background-color: rgba(0, 230, 118, 0.1); border-radius: 10px; margin-top: 5px; border: 1px dashed #00E676;'>
                        <div style='font-size: 0.8rem; color: #333; font-weight: bold; letter-spacing: 1px;'>🔴 MARCADOR EN VIVO</div>
                        <div style='font-size: 2rem; font-weight: bold; color: #1E1E1E;'>{match['resultado'] if match['resultado'] else '0-0'}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.session_state.es_admin:
                        col_score, col_btn_score = st.columns([3, 1])
                        new_score = col_score.text_input("Set 1 Set 2 Set 3", value=match['resultado'], key=f"live_{match['id']}", label_visibility="collapsed", placeholder="Ej: 6-4 2-1")
                        if col_btn_score.button("💾", key=f"save_live_{match['id']}"):
                            actualizar_marcador(match['id'], new_score)
                            actualizar_tabla_posiciones(match['torneo_id']) # Actualizar tabla al cambiar marcador
                            st.rerun()
                
                # Selector de Estado (Solo Admin)
                if match and st.session_state.es_admin:
                    new_status = st.selectbox("Actualizar Estado", ["Próximo", "En Juego", "Finalizado", "Retrasado"], key=f"status_{match['id']}", index=["Próximo", "En Juego", "Finalizado", "Retrasado"].index(estado))
                    if new_status != estado:
                        actualizar_estado_partido(match['id'], new_status)
                        st.rerun()
                
                # Botón WhatsApp (Solo Admin)
                if match and st.session_state.es_admin:
                    with st.popover("💬 WhatsApp"):
                        # Buscar datos de contacto
                        row_p1 = get_inscripcion_by_pareja(match['pareja1'])
                        row_p2 = get_inscripcion_by_pareja(match['pareja2'])
                        
                        targets = []
                        if row_p1 is not None: targets.append((row_p1['jugador1'], row_p1['telefono1'], match['pareja2']))
                        if row_p2 is not None: targets.append((row_p2['jugador1'], row_p2['telefono1'], match['pareja1']))
                        
                        for name, phone, rival in targets:
                            if phone:
                                msg = f"Hola {name}, tu partido en Rincón Padel contra {rival} es a las {time_label.split(' - ')[0]}.\n\n📊 Link al cuadro: https://rinconpadel.streamlit.app\n\n⚠️ Por favor llegar 15 min antes para entrar en calor."
                                url = create_wa_link(phone, msg)
                                st.markdown(f"📲 [Enviar a {name}]({url})")
                            else:
                                st.caption(f"Sin teléfono para {name}")

    with tab_partidos:
        st.header("🎾 Listado de Partidos")
        
        # Filtros
        c1, c2, c3, c4 = st.columns(4)
        c1.selectbox("Sedes", ["Todas", "Central", "Cancha 2", "Cancha 3"])
        c2.selectbox("Fecha", ["Todas", "Viernes 06/03", "Sábado 07/03", "Domingo 08/03"])
        c3.selectbox("Grupos / Zonas", ["Todos", "Zona A", "Zona B", "Zona C", "Octavos", "Cuartos"])
        c4.selectbox("Estado", ["Todos", "Jugados", "No Jugados"])
        
        # Datos simulados
        data_partidos = [
            ["CA501", "Viernes 06/03 20:00", "Central", "Zona A", "Tapia - Coello", "6 6", "Galán - Chingotto", "4 3"],
            ["CA502", "Viernes 06/03 21:30", "Cancha 2", "Zona B", "Lebrón - Navarro", "4 6 6", "Stupa - Di Nenno", "6 4 7"],
            ["CA503", "Sábado 07/03 10:00", "Central", "Zona A", "Tapia - Coello", "6 6", "Bela - Tello", "2 1"],
            ["CA504", "Sábado 07/03 11:30", "Cancha 3", "Zona C", "Momo - Sanyo", "-", "Chingotto - Paquito", "-"]
        ]
        
        cols_partidos = ["Código", "Horario", "Sede", "Zona", "Pareja A", "Resultado Pareja A (Sets)", "Pareja B", "Resultado Pareja B (Sets)"]
        df_partidos_jugados = pd.DataFrame(data_partidos, columns=cols_partidos)
        
        st.dataframe(df_partidos_jugados, hide_index=True, use_container_width=True)

elif choice == "⚙️ Admin":
    if not st.session_state.es_admin:
        st.error("Acceso denegado. Inicia sesión como administrador.")
    else:
        st.header("⚙️ Panel de Administración")
        
        tab_gestion_torneo, tab_admin_gral, tab_admin_fotos, tab_carga_puntos, tab_admin_socios, tab_control_vivo = st.tabs(["🏆 Gestión de Torneo", "🔧 Configuración General", "📷 Gestión de Fotos", "📊 Carga de Puntos", "👥 Administración de Socios", "⚡ Control en Vivo"])
        
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
            f_evento = st.date_input("Fecha del Evento")
            
            cats = ["Libre", "3ra", "4ta", "5ta", "6ta", "7ma", "8va", "Suma 12", "Suma 13", "Otra (Escribir nueva...)"]
            c_torneo_sel = st.selectbox("Categoría", cats)
            
            c_torneo_final = c_torneo_sel
            if c_torneo_sel == "Otra (Escribir nueva...)":
                c_torneo_final = st.text_input("Nombre de la Categoría Nueva", placeholder="Ej: Suma 15", key="admin_t_cat_custom")
            
            es_puntuable = st.checkbox("¿Asigna Puntos al Ranking?", value=True, key="check_puntuable_new")
            
            afiche_nuevo = st.file_uploader("Subir Afiche (Opcional)", type=['jpg', 'png', 'jpeg'], key=f"afiche_{st.session_state.uploader_key}")
            
            if st.button("🚀 ACTIVAR TORNEO"):
                if n_torneo and c_torneo_final:
                    new_id = crear_torneo(n_torneo, f_evento, c_torneo_final, es_puntuable)
                    
                    if new_id and afiche_nuevo:
                        if not os.path.exists("assets"):
                            os.makedirs("assets")
                        file_path = os.path.join("assets", afiche_nuevo.name)
                        with open(file_path, "wb") as f:
                            f.write(afiche_nuevo.getbuffer())
                        
                        run_action("INSERT INTO eventos (torneo_id, afiche) VALUES (%s, %s)", (new_id, file_path))

                    st.success("✅ Torneo creado y guardado exitosamente.")
                    # Limpiar inputs
                    st.session_state.uploader_key += 1
                    st.rerun()
                else:
                    st.warning("⚠️ El nombre del torneo y la categoría son obligatorios.")
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("<div class='admin-card'>", unsafe_allow_html=True)
            st.subheader("🏆 Configuración de Torneo Activo")
            
            active_tournaments = get_data("SELECT * FROM torneos WHERE estado = 'Abierto'")
            
            if not active_tournaments.empty:
                torneo_opts = {f"{row['nombre']} ({row['categoria']})": row['id'] for _, row in active_tournaments.iterrows()}
                sel_t_name = st.selectbox("Seleccionar Torneo Activo", list(torneo_opts.keys()))
                sel_t_id = torneo_opts[sel_t_name]
                t_data = active_tournaments[active_tournaments['id'] == sel_t_id].iloc[0]
                
                with st.form("edit_torneo_form"):
                    c1, c2 = st.columns(2)
                    new_name = c1.text_input("Nombre del Torneo", value=t_data['nombre'])
                    
                    # Configuración de fechas (Rango)
                    val_fechas = []
                    try:
                        # Intentar parsear si es formato ISO (YYYY-MM-DD)
                        d = datetime.strptime(t_data['fecha'], "%Y-%m-%d")
                        val_fechas = [d, d]
                    except:
                        # Si falla (ej: texto "DD/MM al..."), usar hoy
                        val_fechas = [datetime.now(), datetime.now()]

                    new_date = c2.date_input("Fecha (Seleccionar Rango)", value=val_fechas)
                    new_cat = st.selectbox("Categoría", ["Libre", "3ra", "4ta", "5ta", "6ta", "7ma", "8va", "Suma 12", "Suma 13"], index=["Libre", "3ra", "4ta", "5ta", "6ta", "7ma", "8va", "Suma 12", "Suma 13"].index(t_data['categoria']) if t_data['categoria'] in ["Libre", "3ra", "4ta", "5ta", "6ta", "7ma", "8va", "Suma 12", "Suma 13"] else 0)
                    
                    val_puntuable = True
                    if 'es_puntuable' in t_data and t_data['es_puntuable'] == 0:
                        val_puntuable = False
                    edit_es_puntuable = st.checkbox("¿Asigna Puntos al Ranking?", value=val_puntuable, key="check_puntuable_edit")
                    
                    st.markdown("---")
                    st.write("📸 **Afiche Promocional**")
                    afiche_file = st.file_uploader("Subir imagen (JPG/PNG)", type=['jpg', 'png', 'jpeg'])
                    
                    if st.form_submit_button("💾 Guardar Cambios"):
                        # Formatear fecha
                        fecha_str = t_data['fecha']
                        if isinstance(new_date, (list, tuple)):
                            if len(new_date) == 2:
                                ini, fin = new_date
                                fecha_str = f"{ini.strftime('%d/%m')} al {fin.strftime('%d/%m')}"
                            elif len(new_date) == 1:
                                ini = new_date[0]
                                fecha_str = f"{ini.strftime('%d/%m')} al {ini.strftime('%d/%m')}"

                        run_action("UPDATE torneos SET nombre=%s, fecha=%s, categoria=%s, es_puntuable=%s WHERE id=%s", (new_name, fecha_str, new_cat, 1 if edit_es_puntuable else 0, sel_t_id))
                        
                        if afiche_file:
                            if not os.path.exists("assets"):
                                os.makedirs("assets")
                            file_path = os.path.join("assets", afiche_file.name)
                            with open(file_path, "wb") as f:
                                f.write(afiche_file.getbuffer())
                            
                            df_ev = cargar_datos("SELECT id FROM eventos WHERE torneo_id=%s", (sel_t_id,))
                            if not df_ev.empty:
                                run_action("UPDATE eventos SET afiche=%s WHERE torneo_id=%s", (file_path, sel_t_id))
                            else:
                                run_action("INSERT INTO eventos (torneo_id, afiche) VALUES (%s, %s)", (sel_t_id, file_path))
                        
                        st.success("✅ Torneo actualizado correctamente.")
                        limpiar_cache()
                        st.rerun()
                
                st.markdown("---")
                st.subheader("🎲 Sorteo de Zonas")
                st.write("Generar zonas automáticamente para los inscriptos confirmados.")
                if st.button("🎲 Realizar Sorteo de Zonas", key="btn_sorteo_admin"):
                    success, msg = generar_zonas(sel_t_id, t_data['categoria'])
                    if success:
                        st.success("✅ Zonas sorteadas y publicadas automáticamente")
                    else:
                        st.error(msg)
                
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
                        success, msg = generar_fixture_automatico(sel_t_id, programacion_dias)
                        if success:
                            st.success(msg)
                        else:
                            st.error(msg)
                
                st.markdown("---")
                st.subheader("🛠️ Edición Manual de Horarios")
                
                # Obtener partidos del torneo seleccionado (Sin caché para ver cambios recientes)
                matches_edit = cargar_datos("SELECT id, pareja1, pareja2, instancia, horario FROM partidos WHERE torneo_id = %s", params=(sel_t_id,))
                
                if not matches_edit.empty:
                    # Crear lista de opciones para el selectbox
                    match_opts = {f"{row['instancia']}: {row['pareja1']} vs {row['pareja2']} ({row['horario'] if row['horario'] else 'Sin horario'})": row['id'] for _, row in matches_edit.iterrows()}
                    
                    sel_match_label = st.selectbox("Seleccionar Partido a Modificar", list(match_opts.keys()))
                    sel_match_id = match_opts[sel_match_label]
                    
                    # Obtener datos actuales del partido seleccionado
                    curr_match = matches_edit[matches_edit['id'] == sel_match_id].iloc[0]
                    
                    # Valores por defecto para los inputs
                    default_date = datetime.now().date()
                    default_time = datetime.now().time()
                    
                    if curr_match['horario']:
                        try:
                            dt_obj = datetime.strptime(curr_match['horario'], "%Y-%m-%d %H:%M")
                            default_date = dt_obj.date()
                            default_time = dt_obj.time()
                        except:
                            pass
                            
                    c_date, c_time = st.columns(2)
                    new_date = c_date.date_input("Nueva Fecha", value=default_date)
                    new_time = c_time.time_input("Nueva Hora", value=default_time)
                    
                    if st.button("💾 Confirmar Cambio de Horario"):
                        # Construir datetime nuevo
                        new_start = datetime.combine(new_date, new_time)
                        duration = timedelta(hours=1, minutes=15)
                        new_end = new_start + duration
                        
                        # Validación de superposición (Cancha Central única)
                        # Consultamos todos los partidos con horario asignado excepto el actual
                        all_scheduled = cargar_datos("SELECT id, horario FROM partidos WHERE horario IS NOT NULL AND id != %s", params=(sel_match_id,))
                        
                        overlap = False
                        conflict_info = ""
                        
                        for _, row in all_scheduled.iterrows():
                            try:
                                existing_start = datetime.strptime(row['horario'], "%Y-%m-%d %H:%M")
                                existing_end = existing_start + duration
                                
                                # Lógica de superposición: (StartA < EndB) and (EndA > StartB)
                                if new_start < existing_end and new_end > existing_start:
                                    overlap = True
                                    conflict_info = f"Partido ID {row['id']} ({row['horario']})"
                                    break
                            except:
                                continue
                        
                        if overlap:
                            st.error(f"❌ Conflicto de horario: El turno se superpone con {conflict_info}. La cancha está ocupada.")
                        else:
                            # Actualizar en DB
                            # Actualizamos horario, forzamos Cancha Central y estado Próximo si estaba sin definir
                            run_action("UPDATE partidos SET horario = %s, cancha = 'Cancha Central', estado_partido = 'Próximo' WHERE id = %s", (new_start.strftime("%Y-%m-%d %H:%M"), sel_match_id))
                            limpiar_cache()
                            st.success("✅ Horario actualizado. No olvides avisar a los jugadores por WhatsApp")
                            st.rerun()
                else:
                    st.info("No hay partidos generados para este torneo.")

            else:
                st.info("No hay torneos activos para configurar.")
            st.markdown("</div>", unsafe_allow_html=True)

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
                if not df_j_admin.empty:
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
            df_t_ranking = get_data("SELECT * FROM torneos ORDER BY id DESC")
            
            if not df_t_ranking.empty:
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
                    df_insc_r = get_data("SELECT * FROM inscripciones WHERE torneo_id = %s", params=(sel_t_id_r,))
                    
                    if not df_insc_r.empty:
                        # Crear lista de parejas
                        parejas_map = {f"{row['jugador1']} - {row['jugador2']}": (row['jugador1'], row['jugador2']) for _, row in df_insc_r.iterrows()}
                        sel_pareja_r = st.selectbox("Seleccionar Pareja", list(parejas_map.keys()), key="sel_pareja_ranking_pts")
                        
                        # 3. Input de Puntos
                        puntos_r = st.number_input("Puntos a asignar (por jugador)", min_value=0, step=10, value=100, help="Ej: 1000 Campeón, 600 Finalista, etc.")
                        
                        if st.button("💾 Actualizar Ranking", key="btn_update_ranking"):
                            j1, j2 = parejas_map[sel_pareja_r]
                            # Actualizar J1 y J2 (Borrar previos para este torneo y reinsertar)
                            for jug in [j1, j2]:
                                run_action("DELETE FROM ranking_puntos WHERE torneo_id = %s AND jugador = %s", (sel_t_id_r, jug))
                                run_action("INSERT INTO ranking_puntos (torneo_id, jugador, categoria, puntos) VALUES (%s, %s, %s, %s)", (sel_t_id_r, jug, cat_torneo_r, puntos_r))
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
            st.subheader("⚡ Control de Partido en Vivo (Banner)")
            
            # 1. Seleccionar Torneo y Partido
            df_t_live = get_data("SELECT * FROM torneos WHERE estado = 'Abierto'")
            if not df_t_live.empty:
                t_opts_live = {f"{row['nombre']}": row['id'] for _, row in df_t_live.iterrows()}
                sel_t_live = st.selectbox("Seleccionar Torneo", list(t_opts_live.keys()), key="sel_t_live")
                id_t_live = t_opts_live[sel_t_live]
                
                # Obtener partidos pendientes o en juego
                df_p_live = get_data("SELECT * FROM partidos WHERE torneo_id = %s AND estado_partido != 'Finalizado'", params=(id_t_live,))
                
                if not df_p_live.empty:
                    p_opts_live = {f"{row['instancia']}: {row['pareja1']} vs {row['pareja2']}": row['id'] for _, row in df_p_live.iterrows()}
                    sel_p_live_label = st.selectbox("Seleccionar Partido", list(p_opts_live.keys()), key="sel_p_live")
                    id_p_live = p_opts_live[sel_p_live_label]
                    
                    row_match = df_p_live[df_p_live['id'] == id_p_live].iloc[0]
                    p1_name = row_match['pareja1']
                    p2_name = row_match['pareja2']
                    
                    st.markdown("---")
                    
                    # 2. Gestión del Estado en Vivo
                    # Verificar si este partido ya está en vivo en la tabla partido_en_vivo
                    current_live = get_data("SELECT * FROM partido_en_vivo ORDER BY id DESC LIMIT 1")
                    
                    # Lógica de Parseo de Marcador (Formato esperado: "6-4 2-1")
                    def parse_sets(score_str):
                        sets = [[0,0], [0,0], [0,0]] # Set 1, Set 2, Set 3
                        if score_str:
                            parts = score_str.split(' ')
                            for i, part in enumerate(parts):
                                if i < 3 and '-' in part:
                                    try:
                                        s1, s2 = part.split('-')
                                        sets[i] = [int(s1), int(s2)]
                                    except: pass
                        return sets

                    # Estado inicial
                    sets_data = [[0,0], [0,0], [0,0]]
                    is_active = False
                    
                    if not current_live.empty:
                        # Si el partido en vivo coincide con el seleccionado, cargamos sus datos
                        if current_live.iloc[0]['pareja1'] == p1_name and current_live.iloc[0]['pareja2'] == p2_name:
                            sets_data = parse_sets(current_live.iloc[0]['marcador'])
                            is_active = True
                    
                    # Botón para ACTIVAR este partido en el banner
                    if not is_active:
                        if st.button("📡 TRANSMITIR ESTE PARTIDO (Tomar Control)"):
                            # Limpiamos tabla y ponemos el nuevo
                            run_action("DELETE FROM partido_en_vivo") 
                            run_action("INSERT INTO partido_en_vivo (torneo, pareja1, pareja2, marcador) VALUES (%s, %s, %s, '0-0')", 
                                      (sel_t_live, p1_name, p2_name))
                            # Actualizamos estado en partidos
                            run_action("UPDATE partidos SET estado_partido = 'En Juego' WHERE id = %s", (id_p_live,))
                            st.rerun()
                    else:
                        st.success("🔴 EN VIVO - Controlando Marcador")
                        
                        # --- PANEL DE CONTROL DE PUNTOS ---
                        # Función para actualizar DB
                        def update_score_db(new_sets):
                            # Construir string: "6-4 2-1" (ignorar 0-0 si no es el primero o si los anteriores tienen datos)
                            str_parts = []
                            for s in new_sets:
                                if s[0] != 0 or s[1] != 0 or len(str_parts) == 0:
                                    str_parts.append(f"{s[0]}-{s[1]}")
                            final_score = " ".join(str_parts)
                            
                            run_action("UPDATE partido_en_vivo SET marcador = %s", (final_score,))
                            run_action("UPDATE partidos SET resultado = %s WHERE id = %s", (final_score, id_p_live))
                        
                        # Renderizar Controles para 3 Sets
                        for i in range(3):
                            st.markdown(f"**SET {i+1}**")
                            c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 3])
                            
                            # Pareja 1
                            with c1: st.write(f"🎾 {p1_name}")
                            with c2: 
                                if st.button(f"➖", key=f"dec_p1_s{i}"):
                                    sets_data[i][0] = max(0, sets_data[i][0] - 1)
                                    update_score_db(sets_data)
                                    st.rerun()
                            with c3: 
                                st.markdown(f"<h2 style='text-align:center; margin:0;'>{sets_data[i][0]}</h2>", unsafe_allow_html=True)
                            with c4: 
                                if st.button(f"➕", key=f"inc_p1_s{i}"):
                                    sets_data[i][0] += 1
                                    update_score_db(sets_data)
                                    st.rerun()
                            
                            # Pareja 2 (Misma lógica, invertida visualmente o alineada)
                            # Para simplificar visualmente en filas:
                            c1b, c2b, c3b, c4b, c5b = st.columns([3, 1, 1, 1, 3])
                            with c1b: st.write(f"🔷 {p2_name}")
                            with c2b:
                                if st.button(f"➖", key=f"dec_p2_s{i}"):
                                    sets_data[i][1] = max(0, sets_data[i][1] - 1)
                                    update_score_db(sets_data)
                                    st.rerun()
                            with c3b:
                                st.markdown(f"<h2 style='text-align:center; margin:0;'>{sets_data[i][1]}</h2>", unsafe_allow_html=True)
                            with c4b:
                                if st.button(f"➕", key=f"inc_p2_s{i}"):
                                    sets_data[i][1] += 1
                                    update_score_db(sets_data)
                                    st.rerun()
                            st.divider()

                        # Botón Finalizar
                        if st.button("🏆 FINALIZAR PARTIDO", type="primary", use_container_width=True):
                            # 1. Determinar ganador (simple: quien ganó más sets)
                            sets_p1 = sum(1 for s in sets_data if s[0] > s[1])
                            sets_p2 = sum(1 for s in sets_data if s[1] > s[0])
                            ganador = p1_name if sets_p1 > sets_p2 else p2_name if sets_p2 > sets_p1 else None
                            
                            # 2. Actualizar partido final
                            final_score_str = " ".join([f"{s[0]}-{s[1]}" for s in sets_data if (s[0]!=0 or s[1]!=0)])
                            run_action("UPDATE partidos SET estado_partido = 'Finalizado', resultado = %s, ganador = %s WHERE id = %s", 
                                      (final_score_str, ganador, id_p_live))
                            
                            # 3. Limpiar Banner
                            run_action("DELETE FROM partido_en_vivo")
                            
                            # 4. Actualizar Posiciones y Bracket
                            actualizar_tabla_posiciones(id_t_live)
                            if row_match['bracket_pos']: # Si es de llave
                                actualizar_bracket(id_p_live, id_t_live, row_match['bracket_pos'], final_score_str, ganador)
                            
                            st.success("✅ Partido Finalizado. Marcador guardado y banner apagado.")
                            st.rerun()
                else:
                    st.info("No hay partidos pendientes en este torneo.")
            else:
                st.warning("No hay torneos activos.")

elif choice == "📈 Ranking":
    st.header("📈 Ranking Oficial Rincón Padel")

    # 1. Filtro Dinámico de Categoría
    # Leemos las categorías disponibles en la tabla torneos
    df_cats = get_data("SELECT DISTINCT categoria FROM torneos")
    opciones_cat = ["Todas"] + df_cats['categoria'].tolist() if not df_cats.empty else ["Todas"]
    
    cat_sel = st.selectbox("Filtrar por Categoría", opciones_cat)
    
    # 2. Consulta SQL
    if cat_sel == "Todas":
        query = """
            SELECT jugador, SUM(puntos) as total_puntos, COUNT(DISTINCT torneo_id) as torneos_jugados 
            FROM ranking_puntos 
            GROUP BY jugador 
            ORDER BY total_puntos DESC 
            LIMIT 10
        """
        params = ()
    else:
        query = """
            SELECT jugador, SUM(puntos) as total_puntos, COUNT(DISTINCT torneo_id) as torneos_jugados 
            FROM ranking_puntos 
            WHERE categoria = %s 
            GROUP BY jugador 
            ORDER BY total_puntos DESC 
            LIMIT 10
        """
        params = (cat_sel,)
        
    df_ranking = get_data(query, params=params)
    
    # 3. Visualización Estilizada
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

elif choice == "ℹ️ Información General":
    st.header("ℹ️ Información General")
    st.markdown("---")

    # Recuperar datos del torneo activo (o el próximo)
    df_torneo = get_data("SELECT * FROM torneos WHERE estado = 'Abierto' ORDER BY fecha ASC LIMIT 1")
    
    if not df_torneo.empty:
        t = df_torneo.iloc[0]
        nombre = t['nombre']
        fecha = t['fecha']
        categoria = t['categoria']
        estado = t['estado']
    else:
        nombre = "A confirmar"
        fecha = "Por definir"
        categoria = "Todas"
        estado = "Sin actividad"

    # Definir los datos de la tabla
    datos = [
        ("Nombre del Evento", "Circuito Rincón Padel 2024"),
        ("Nombre del Torneo", nombre),
        ("Fecha", fecha),
        ("Sistema de Competencia", "Fase de Grupos + Llave Final"),
        ("Modalidad", "Dobles (Masculino / Femenino)"),
        ("Categoría", categoria),
        ("Estado", estado),
        ("Costo de Inscripciones", "$ 15.000 por jugador"),
        ("Localidad", "Villaguay, Entre Ríos")
    ]

    # Construir tabla HTML limpia
    html_table = """
    <style>
        table {
            width: 100%;
            border-collapse: collapse;
            border: 1px solid #e0e0e0;
            font-family: 'Source Sans Pro', sans-serif;
        }
        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }
        tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        tr:hover {
            background-color: #f1f1f1;
        }
        .label-cell {
            font-weight: 600;
            color: #31333F;
            width: 40%;
            background-color: #ffffff;
            border-right: 1px solid #e0e0e0;
        }
        .value-cell {
            color: #555;
        }
    </style>
    <table>
    """
    
    for label, value in datos:
        html_table += f"""
        <tr>
            <td class="label-cell">{label}</td>
            <td class="value-cell">{value}</td>
        </tr>
        """
    html_table += "</table>"

    st.markdown(html_table, unsafe_allow_html=True)