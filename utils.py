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
            
        # Auto-invalidación de caché al guardar/actualizar datos
        if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            st.cache_data.clear()
            
        return result
    except Exception as e:
        st.error(f'❌ Error de Conexión: {str(e)}')
        st.stop()

@st.cache_resource
def init_db():
    try:
        conn = st.connection('postgresql', type='sql', connect_args={'connect_timeout': 30}, pool_pre_ping=True, pool_recycle=300)
        return conn
    except Exception as e:
        st.error(f'Error crítico al conectar a la base de datos: {e}')
        st.stop()

def limpiar_cache():
    st.cache_data.clear()

def _ejecutar_select_seguro(query, params):
    """Manejo de conexión seguro y sin pantallas rojas."""
    try:
        params = normalize_params(params)
        conn = st.connection('postgresql', type='sql', connect_args={'connect_timeout': 30}, pool_pre_ping=True, pool_recycle=300)
        return conn.query(query, params=params, ttl=0)
    except Exception:
        st.cache_resource.clear()
        time.sleep(1)
        try:
            conn = st.connection('postgresql', type='sql')
            return conn.query(query, params=params, ttl=0)
        except Exception:
            return pd.DataFrame() # Retorna tabla vacía para no romper la app

@st.cache_data(ttl=300, show_spinner=False)
def get_data_lento(query, params=None):
    """Caché largo (5 min) para Ranking y Jugadores"""
    return _ejecutar_select_seguro(query, params)

@st.cache_data(ttl=60, show_spinner=False)
def get_data_rapido(query, params=None):
    """Caché corto (60s) para Vivo, Fixture y Posiciones"""
    return _ejecutar_select_seguro(query, params)

def cargar_datos(query, params=None):
    """Enrutador de Caché Inteligente"""
    q_upper = query.upper()
    if "RANKING" in q_upper or "JUGADORES" in q_upper:
        return get_data_lento(query, params)
    else:
        return get_data_rapido(query, params)

def get_data(query, params=None):
    """Alias para mantener compatibilidad."""
    return cargar_datos(query, params)

# --- MOTOR ELO (PADEL 2v2) ---
def calcular_elo_pareja(elo_j1, elo_j2):
    """
    Obtiene el nivel combinado del equipo.
    Para dobles, se suele usar un promedio, o un promedio ponderado 
    que favorezca ligeramente al mejor jugador (+20%). Aquí usamos promedio simple.
    """
    return (elo_j1 + elo_j2) / 2

def calcular_probabilidad_victoria(elo_pareja_a, elo_pareja_b):
    """Calcula la probabilidad matemática de victoria (Devuelve %)."""
    prob_a = 1 / (1 + 10 ** ((elo_pareja_b - elo_pareja_a) / 400))
    prob_b = 1 - prob_a
    return prob_a * 100, prob_b * 100

def actualizar_elos_post_partido(id_g1, id_g2, id_p1, id_p2, k=32):
    """
    Recalcula y asigna los nuevos ELOs a los 4 jugadores tras un partido.
    Se debe llamar a esta función cuando se guarda un resultado final.
    """
    # 1. Leer ELOs actuales
    jugadores = get_data(f"SELECT id, elo_rating FROM jugadores WHERE id IN ({id_g1}, {id_g2}, {id_p1}, {id_p2})")
    if jugadores is None or jugadores.empty: return False
    
    dict_elos = {row['id']: (row['elo_rating'] if pd.notna(row['elo_rating']) else 1500) for _, row in jugadores.iterrows()}
    
    elo_g1, elo_g2 = dict_elos.get(id_g1, 1500), dict_elos.get(id_g2, 1500)
    elo_p1, elo_p2 = dict_elos.get(id_p1, 1500), dict_elos.get(id_p2, 1500)
    
    # 2. Cálculos ELO
    elo_ganadores = calcular_elo_pareja(elo_g1, elo_g2)
    elo_perdedores = calcular_elo_pareja(elo_p1, elo_p2)
    
    prob_ganador, _ = calcular_probabilidad_victoria(elo_ganadores, elo_perdedores)
    
    # 3. Factor de ajuste (Delta)
    delta = k * (1 - (prob_ganador / 100.0))
    
    nuevos_elos = {
        id_g1: round(elo_g1 + delta),
        id_g2: round(elo_g2 + delta),
        id_p1: round(elo_p1 - delta),
        id_p2: round(elo_p2 - delta)
    }
    
    # 4. Impactar Base de Datos
    for j_id, nuevo_elo in nuevos_elos.items():
        run_action("UPDATE jugadores SET elo_rating = %(elo)s WHERE id = %(id)s", {"elo": nuevo_elo, "id": j_id})
    return True

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
        
        if not df.empty:
            user = df.iloc[0]
            stored_pass = user['password']
            # Lógica de Reclamo: Si no tiene pass, actualizamos
            if pd.isna(stored_pass) or stored_pass == "":
                final_pass = password if password else dni
                run_action("UPDATE jugadores SET password = %(password)s, nombre = %(nombre)s, apellido = %(apellido)s, celular = %(celular)s, categoria_actual = %(categoria)s, localidad = %(localidad)s, estado_cuenta = 'Activa' WHERE dni = %(dni)s",
                          {"password": hash_password(final_pass), "nombre": nombre, "apellido": apellido, "celular": celular, "categoria": categoria, "localidad": localidad, "dni": dni})
                limpiar_cache()
                return True, "Cuenta reclamada y activada exitosamente."
            else:
                return False, "Este DNI ya está registrado. Por favor, inicia sesión."

        # Insert Nuevo
        final_pass = password if password else dni
        run_action("INSERT INTO jugadores (dni, celular, password, nombre, apellido, categoria_actual, localidad, estado_cuenta) VALUES (%(dni)s, %(celular)s, %(password)s, %(nombre)s, %(apellido)s, %(categoria_actual)s, %(localidad)s, 'Pendiente')",
                  {"dni": dni, "celular": celular, "password": hash_password(final_pass), "nombre": nombre, "apellido": apellido, "categoria_actual": categoria, "localidad": localidad})
        limpiar_cache()
        return True, "Registro exitoso."
    except Exception as e:
        return False, f"Error al registrar: {str(e)}"

# --- URLS ASSETS ---
URL_LOTTIE_PLAYER = "https://assets9.lottiefiles.com/packages/lf20_vo0a1yca.json"
URL_LOTTIE_TROPHY = "https://assets10.lottiefiles.com/packages/lf20_touohxv0.json"
URL_LOTTIE_BALL = "https://lottie.host/8e2f644b-6101-447a-ba98-0c3f59518d6e/3rXo1O3vVv.json"