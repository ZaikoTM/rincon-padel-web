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
import time
import requests
import contextlib

# --- CONFIGURACIÓN E INICIALIZACIÓN ---
def init_app():
    """Inicializa estado de sesión y base de datos compartido."""
    # Configuración de página si no se ha hecho (debe ser lo primero en cada página)
    # Nota: st.set_page_config debe llamarse en cada archivo individualmente al inicio.
    
    # Tema
    if 'theme' not in st.session_state:
        st.session_state['theme'] = False
    
    # Admin
    if 'es_admin' not in st.session_state:
        st.session_state.es_admin = False
        
    # Usuario
    if 'usuario_logueado' not in st.session_state:
        st.session_state['usuario_logueado'] = False
    if 'datos_usuario' not in st.session_state:
        st.session_state['datos_usuario'] = None

    init_db()

@st.cache_data
def load_local_image(path):
    if os.path.exists(path):
        return Image.open(path)
    return None

@st.cache_data(show_spinner=False)
def load_lottieurl(url):
    try:
        r = requests.get(url)
        if r.status_code != 200: return None
        return r.json()
    except:
        return None

# --- HELPER DB ---
def normalize_params(params):
    """Convierte tipos de numpy (int64, etc.) a nativos de Python para evitar errores de adaptador."""
    if isinstance(params, dict):
        return {k: (v.item() if hasattr(v, 'item') else v) for k, v in params.items()}
    if isinstance(params, (list, tuple)):
        return [(v.item() if hasattr(v, 'item') else v) for v in params]
    return params

# --- BASE DE DATOS ---
def run_action(query, params=None, return_id=False):
    try:
        params = normalize_params(params)
        conn = st.connection('postgresql', type='sql', connect_args={'connect_timeout': 30}, pool_pre_ping=True, pool_recycle=300)
        with conn.session as s:
            with s.connection().connection.cursor() as cur:
                cur.execute(query, params)
                if return_id:
                    result = cur.fetchone()[0]
                else:
                    result = None
            s.commit()
        return result
    except Exception as e:
        st.error(f'❌ Error de Conexión: {str(e)}')
        st.stop()

@st.cache_resource
def init_db():
    run_action('''CREATE TABLE IF NOT EXISTS inscripciones
                 (id SERIAL PRIMARY KEY, torneo_id INTEGER, jugador1 TEXT, jugador2 TEXT, localidad TEXT, 
                  categoria TEXT, pago_confirmado INTEGER, telefono1 TEXT, telefono2 TEXT,
                  estado_pago TEXT DEFAULT 'Pendiente', estado_validacion TEXT DEFAULT 'Pendiente')''')
    run_action('''CREATE TABLE IF NOT EXISTS torneos
                 (id SERIAL PRIMARY KEY, nombre TEXT, fecha TEXT, categoria TEXT, estado TEXT, es_puntuable INTEGER DEFAULT 1,
                  super_tiebreak INTEGER DEFAULT 0, puntos_tiebreak INTEGER DEFAULT 10, fecha_inicio DATE, fecha_fin DATE)''')
    run_action('''CREATE TABLE IF NOT EXISTS partidos
                 (id SERIAL PRIMARY KEY, torneo_id INTEGER, pareja1 TEXT, pareja2 TEXT, resultado TEXT, instancia TEXT,
                  bracket_pos INTEGER, estado_partido TEXT DEFAULT 'Próximo', ganador TEXT, horario TEXT, cancha TEXT,
                  hora_fin TEXT, set1 TEXT, set2 TEXT, set3 TEXT, hora_inicio_real TEXT)''')
    run_action('''CREATE TABLE IF NOT EXISTS zonas (id SERIAL PRIMARY KEY, torneo_id INTEGER, nombre_zona TEXT, pareja TEXT)''')
    run_action('''CREATE TABLE IF NOT EXISTS fotos (id SERIAL PRIMARY KEY, nombre TEXT, imagen BYTEA, fecha TEXT)''')
    run_action('''CREATE TABLE IF NOT EXISTS jugadores
                 (id SERIAL PRIMARY KEY, dni TEXT UNIQUE, celular TEXT UNIQUE, password TEXT, nombre TEXT, apellido TEXT,
                  localidad TEXT, categoria_actual TEXT, categoria_anterior TEXT, foto BYTEA, estado_cuenta TEXT DEFAULT 'Pendiente')''')
    run_action('''CREATE TABLE IF NOT EXISTS eventos (id SERIAL PRIMARY KEY, torneo_id INTEGER, afiche TEXT)''')
    run_action('''CREATE TABLE IF NOT EXISTS zonas_posiciones
                 (id SERIAL PRIMARY KEY, torneo_id INTEGER, nombre_zona TEXT, pareja TEXT,
                  pts INTEGER DEFAULT 0, pj INTEGER DEFAULT 0, pg INTEGER DEFAULT 0, pp INTEGER DEFAULT 0, 
                  sf INTEGER DEFAULT 0, sc INTEGER DEFAULT 0, ds INTEGER DEFAULT 0)''')
    run_action('''CREATE TABLE IF NOT EXISTS ranking_puntos (id SERIAL PRIMARY KEY, torneo_id INTEGER, jugador TEXT, categoria TEXT, puntos INTEGER)''')
    run_action('''CREATE TABLE IF NOT EXISTS partido_en_vivo (id SERIAL PRIMARY KEY, torneo TEXT, pareja1 TEXT, pareja2 TEXT, marcador TEXT)''')

def limpiar_cache():
    st.cache_data.clear()

@st.cache_data(ttl=60) # Caché optimizado de 60 segundos por defecto
def get_data(query, params=None):
    try:
        params = normalize_params(params)
        conn = st.connection('postgresql', type='sql', connect_args={'connect_timeout': 30}, pool_pre_ping=True, pool_recycle=300)
        return conn.query(query, params=params, ttl=60)
    except Exception:
        time.sleep(1)
        params = normalize_params(params)
        conn = st.connection('postgresql', type='sql', connect_args={'connect_timeout': 30}, pool_pre_ping=True, pool_recycle=300)
        return conn.query(query, params=params, ttl=0)

def cargar_datos(query, params=None):
    """Carga directa sin caché para datos en tiempo real (admin)."""
    return get_data(query, params)

# --- ESTILOS CSS ---
def cargar_estilos():
    css_dark_neon = """
    <style>
        .stApp, section[data-testid="stSidebar"], .stButton button, .stTextInput input, div[data-testid="stExpander"], .dashboard-card, .card { transition: all 0.5s ease !important; }
        .stApp { background-color: #000000; background-image: radial-gradient(circle at center, #111111 0%, #000000 100%); border-left: 2px solid #00FF41; border-right: 2px solid #00FF41; }
        @keyframes neonPulse { 0% { box-shadow: 0 0 5px #00FF41; border-color: #00FF41; } 50% { box-shadow: 0 0 20px #00FF41; border-color: #39FF14; } 100% { box-shadow: 0 0 5px #00FF41; border-color: #00FF41; } }
        section[data-testid="stSidebar"] { background: linear-gradient(180deg, #050505, #111111, #050505); border-right: 2px solid #00FF41; }
        section[data-testid="stSidebar"] .stTextInput input { background-color: #000000 !important; color: #ccffcc !important; border: 1px solid #00FF41 !important; border-radius: 10px !important; }
        section[data-testid="stSidebar"] .stButton button { background-color: #00FF41 !important; color: #000000 !important; font-weight: bold !important; border: none !important; border-radius: 10px !important; }
        h1, h2, h3, h4, h5, h6, .rincon-header, .zona-header { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important; text-shadow: 0 0 10px #00FF41 !important; color: #FFFFFF !important; }
        .rincon-header { background-color: #000000; color: #FFFFFF; text-align: center; padding: 20px; border-radius: 10px; border: 4px double #00FF41; text-transform: uppercase; font-weight: 900; font-size: 26px; letter-spacing: 3px; animation: neonPulse 3s infinite alternate; margin-bottom: 25px; }
        .zona-header { background-color: #1E1E1E; color: #FFFFFF; padding: 12px; border-left: 6px solid #00FF41; margin-top: 25px; margin-bottom: 15px; font-weight: bold; font-size: 16px; text-transform: uppercase; border-radius: 0px 8px 8px 0px; }
        .dashboard-card, .card, .admin-card, .player-card, .h2h-card, .ranking-card, .match-card, div[data-testid="stForm"] { background-color: rgba(30, 30, 30, 0.8) !important; border: 1px solid #00FF41 !important; border-radius: 15px !important; box-shadow: 0 0 15px rgba(0, 255, 65, 0.2) !important; color: #E0E0E0 !important; }
        .stTabs [data-baseweb="tab"] { background-color: transparent !important; border: 1px solid #00FF41 !important; color: #FFFFFF !important; border-radius: 5px !important; }
        .stTabs [aria-selected="true"] { background-color: #00FF41 !important; color: #000000 !important; font-weight: bold !important; }
        .stSelectbox div[data-baseweb="select"] > div, .stTextInput input, .stNumberInput input, .stDateInput input { background-color: #000000 !important; color: #FFFFFF !important; border: 1px solid #00FF41 !important; border-radius: 8px !important; }
        [data-testid="stDataFrame"] { border: 1px solid #00FF41 !important; border-radius: 10px !important; background-color: #121212 !important; }
    </style>
    """
    
    css_light_forest = """
    <style>
        .stApp { background-color: #FFFFFF; color: #333333; }
        section[data-testid="stSidebar"] { background: linear-gradient(180deg, #F8F9FA, #E8F5E9, #F8F9FA); border-right: 2px solid #2E7D32; }
        .stTextInput input, .stSelectbox div[data-baseweb="select"] > div { background-color: #FFFFFF !important; color: #333333 !important; border: 1px solid #2E7D32 !important; border-radius: 8px !important; }
        h1, h2, h3, h4, h5, h6, .rincon-header, .zona-header { color: #2E7D32 !important; }
        .rincon-header { background-color: #FFFFFF; color: #2E7D32; border: 2px solid #2E7D32; text-align: center; padding: 20px; border-radius: 10px; font-weight: 900; font-size: 26px; margin-bottom: 25px; }
        .zona-header { background-color: #E8F5E9; color: #1B5E20; border-left: 6px solid #2E7D32; padding: 12px; margin-top: 25px; font-weight: bold; }
        .dashboard-card, .card, div[data-testid="stForm"] { background-color: #FFFFFF !important; border: 1px solid #2E7D32 !important; box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important; color: #333333 !important; border-radius: 15px !important; }
        .stButton button { background-color: #2E7D32 !important; color: #FFFFFF !important; border-radius: 10px !important; }
        .stTabs [aria-selected="true"] { background-color: #2E7D32 !important; color: #FFFFFF !important; }
    </style>
    """
    if st.session_state.get('theme', False): # True = Light
        st.markdown(css_light_forest, unsafe_allow_html=True)
    else:
        st.markdown(css_dark_neon, unsafe_allow_html=True)

# --- HELPERS ---
@contextlib.contextmanager
def custom_spinner():
    with st.spinner("Procesando... 🎾"):
        yield

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def clean_phone(phone):
    if not phone: return ""
    p = "".join(filter(str.isdigit, str(phone)))
    if not p.startswith("54"): p = "54" + p
    return p

def create_wa_link(phone, message):
    base = "https://wa.me/"
    p = clean_phone(phone)
    msg = urllib.parse.quote(message)
    return f"{base}{p}?text={msg}"

def mask_phone_number(phone):
    if not phone: return "🔒 Privado"
    p = str(phone)
    if len(p) >= 4: return p[:4] + "-XXXXXX"
    return "🔒 Privado"

def autenticar_usuario(dni, password):
    df = get_data("SELECT id, dni, nombre, apellido, localidad, categoria_actual, celular FROM jugadores WHERE dni = :dni AND password = :password", {"dni": dni, "password": hash_password(password)})
    if not df.empty:
        user = df.iloc[0]
        return {
            "id": user['id'], "dni": user['dni'], "nombre": user['nombre'], "apellido": user['apellido'],
            "localidad": user['localidad'], "categoria": user['categoria_actual'], "celular": user['celular']
        }
    return None

def buscar_jugador_por_dni(dni):
    return get_data("SELECT * FROM jugadores WHERE celular = :dni OR dni = :dni", params={"dni": dni})

def guardar_inscripcion(torneo_id, j1, j2, loc, cat, pago, tel1, tel2):
    run_action("INSERT INTO inscripciones (torneo_id, jugador1, jugador2, localidad, categoria, pago_confirmado, telefono1, telefono2) VALUES (%(torneo_id)s, %(jugador1)s, %(jugador2)s, %(localidad)s, %(categoria)s, %(pago_confirmado)s, %(telefono1)s, %(telefono2)s)", 
              {"torneo_id": torneo_id, "jugador1": j1, "jugador2": j2, "localidad": loc, "categoria": cat, "pago_confirmado": 1 if pago else 0, "telefono1": tel1, "telefono2": tel2})
    limpiar_cache()

def registrar_jugador_db(dni, nombre, apellido, celular, categoria, localidad="", password=None):
    try:
        df = get_data("SELECT * FROM jugadores WHERE dni = :dni", {"dni": dni})
        if not df.empty: return False, "El DNI ya está registrado."
        final_pass = password if password else dni
        run_action("INSERT INTO jugadores (dni, celular, password, nombre, apellido, categoria_actual, localidad, estado_cuenta) VALUES (%(dni)s, %(celular)s, %(password)s, %(nombre)s, %(apellido)s, %(categoria_actual)s, %(localidad)s, 'Pendiente')",
                  {"dni": dni, "celular": celular, "password": hash_password(final_pass), "nombre": nombre, "apellido": apellido, "categoria_actual": categoria, "localidad": localidad})
        limpiar_cache()
        return True, "Registro exitoso."
    except Exception:
        return False, "Error al registrar. Verifica si el celular ya existe."

# --- URLS ASSETS ---
URL_LOTTIE_PLAYER = "https://assets9.lottiefiles.com/packages/lf20_vo0a1yca.json"
URL_LOTTIE_TROPHY = "https://assets10.lottiefiles.com/packages/lf20_touohxv0.json"
URL_LOTTIE_BALL = "https://lottie.host/8e2f644b-6101-447a-ba98-0c3f59518d6e/3rXo1O3vVv.json"