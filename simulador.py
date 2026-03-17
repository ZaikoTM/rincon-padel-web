import streamlit as st
import pandas as pd
import math
from utils import get_data

def limpiar_llaves():
    """Limpia dinámicamente cualquier variable de la llave en el session_state."""
    keys_to_delete = [k for k in st.session_state.keys() if k.startswith(('R', 'p1_', 'p2_', 'win_'))]
    for k in keys_to_delete:
        del st.session_state[k]

def renderizar_primera_ronda(match_id, titulo, clasificados_db):
    """Renderiza la primera fase con validación estricta de cruces (Zonas y Posiciones)."""
    st.markdown(f"<span style='color:#888; font-size:0.75rem;'>{titulo}</span>", unsafe_allow_html=True)
    
    nombres_base = ["(Esperando...)", "--- Libre ---"] + [p["nombre"] for p in clasificados_db]
    
    # --- Selector P1 ---
    clave_p1 = f"p1_{match_id}"
    val_p1 = st.session_state.get(clave_p1, "(Esperando...)")
    idx_p1 = nombres_base.index(val_p1) if val_p1 in nombres_base else 0
    p1 = st.selectbox("P1", options=nombres_base, index=idx_p1, key=clave_p1, label_visibility="collapsed")
    
    # --- Selector P2 (Con Filtro Estricto) ---
    opciones_p2 = ["(Esperando...)", "--- Libre ---"]
    if p1 not in ["(Esperando...)", "--- Libre ---"]:
        datos_p1 = next((p for p in clasificados_db if p["nombre"] == p1), None)
        if datos_p1:
            for p in clasificados_db:
                if p["nombre"] != p1:
                    # REGLA: Distinta Zona Y Distinta Posición (1º vs 2º)
                    if p["zona"] != datos_p1["zona"] and p["posicion"] != datos_p1["posicion"]:
                        opciones_p2.append(p["nombre"])
    else:
        opciones_p2 = nombres_base
        
    clave_p2 = f"p2_{match_id}"
    val_p2 = st.session_state.get(clave_p2, "(Esperando...)")
    idx_p2 = opciones_p2.index(val_p2) if val_p2 in opciones_p2 else 0
    p2 = st.selectbox("P2", options=opciones_p2, index=idx_p2, key=clave_p2, label_visibility="collapsed")
    
    # --- Selector Ganador ---
    opciones_win = ["(Ganador...)"]
    if p1 not in ["(Esperando...)", "--- Libre ---"]: opciones_win.append(p1)
    if p2 not in ["(Esperando...)", "--- Libre ---"]: opciones_win.append(p2)
    # Si hay un libre, el otro pasa automáticamente
    if p1 == "--- Libre ---" and p2 not in ["(Esperando...)", "--- Libre ---"]: opciones_win.append(p2)
    if p2 == "--- Libre ---" and p1 not in ["(Esperando...)", "--- Libre ---"]: opciones_win.append(p1)
    
    val_win = st.session_state.get(match_id)
    idx_win = opciones_win.index(val_win) if val_win in opciones_win else 0
    
    ganador = st.selectbox("Ganador", options=opciones_win, index=idx_win, key=f"win_{match_id}", label_visibility="collapsed")
    
    if ganador != "(Ganador...)":
        st.session_state[match_id] = ganador
        return ganador
    
    st.session_state[match_id] = None
    return None

def renderizar_partido(match_id, p1, p2, titulo):
    """Renderiza las rondas avanzadas, limitando las opciones solo a los rivales que llegan."""
    st.markdown(f"<span style='color:#888; font-size:0.75rem;'>{titulo}</span>", unsafe_allow_html=True)
    
    if not p1 and not p2:
        st.info("⏳")
        return None
    
    opciones = ["(Ganador...)"]
    if p1: opciones.append(p1)
    if p2: opciones.append(p2)
    
    val_actual = st.session_state.get(match_id)
    idx = opciones.index(val_actual) if val_actual in opciones else 0
        
    ganador = st.selectbox("Ganador", options=opciones, index=idx, key=f"win_{match_id}", label_visibility="collapsed")
    
    if ganador != "(Ganador...)":
        st.session_state[match_id] = ganador
        return ganador
    
    st.session_state[match_id] = None
    return None

def mostrar_simulador():
    st.markdown("<h2 style='color:#39FF14;'>🏆 Simulador de Torneo</h2>", unsafe_allow_html=True)
    st.caption("Gestiona la Fase de Zonas y proyecta la Llave Principal de Eliminación Directa.")

    # --- SELECTOR GENERAL DE TORNEO ---
    df_torneos = get_data("SELECT id, nombre, categoria FROM torneos ORDER BY id DESC")
    if df_torneos is None or df_torneos.empty:
        st.warning("⚠️ No hay torneos registrados para simular.")
        return

    torneos_dict = {row['id']: f"{row['nombre']} ({row['categoria']})" for _, row in df_torneos.iterrows()}
    torneo_sel_id = st.selectbox("🏆 Torneo Activo", options=list(torneos_dict.keys()), format_func=lambda x: torneos_dict[x])

    # Traer parejas reales validadas
    query_inscripciones = """
        SELECT jugador1, jugador2 
        FROM inscripciones 
        WHERE torneo_id = :tid AND estado_validacion = 'Validado'
    """
    df_parejas = get_data(query_inscripciones, {"tid": torneo_sel_id})

    parejas_totales = []
    if df_parejas is not None and not df_parejas.empty:
        for _, row in df_parejas.iterrows():
            j1 = str(row['jugador1']).strip()
            j2 = str(row['jugador2']).strip()
            ap1 = j1.split(" ")[-1] if " " in j1 else j1
            ap2 = j2.split(" ")[-1] if " " in j2 else j2
            parejas_totales.append(f"{ap1} / {ap2}")

    if not parejas_totales:
        st.info("No hay parejas validadas en este torneo todavía.")
        return

    # --- PESTAÑAS (TABS) ---
    tab_zonas, tab_llaves = st.tabs(["📊 Fase de Zonas", "🎾 Llave Principal"])

    # ==========================================
    # PESTAÑA 1: FASE DE ZONAS
    # ==========================================
    with tab_zonas:
        st.markdown("### Configuración de Zonas")
        tamano_zona = st.radio("Parejas por zona:", [3, 4], horizontal=True)
        
        num_zonas = math.ceil(len(parejas_totales) / tamano_zona)
        st.write(f"Se generarán **{num_zonas} zonas** para las {len(parejas_totales)} parejas inscritas.")
        st.markdown("---")

        zonas = []
        for i in range(0, len(parejas_totales), tamano_zona):
            zonas.append(parejas_totales[i:i+tamano_zona])

        cols_zonas = st.columns(3)
        for i, zona in enumerate(zonas):
            with cols_zonas[i % 3]:
                st.markdown(f"<div style='background:#111; padding:15px; border-radius:10px; border-top:3px solid #39FF14; margin-bottom:15px;'>", unsafe_allow_html=True)
                st.markdown(f"<h4 style='margin-top:0;'>Zona {i+1}</h4>", unsafe_allow_html=True)
                
                for p in zona:
                    st.markdown(f"- <small>{p}</small>", unsafe_allow_html=True)
                st.write("")
                
                opciones_zona = ["(Pendiente)"] + zona
                st.selectbox(f"1° Clasificado", options=opciones_zona, key=f"z{i}_1")
                st.selectbox(f"2° Clasificado", options=opciones_zona, key=f"z{i}_2")
                st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================
    # PESTAÑA 2: LLAVE PRINCIPAL DINÁMICA
    # ==========================================
    with tab_llaves:
        col_titulo, col_btn = st.columns([3, 1])
        with col_titulo:
            st.markdown("### Cuadro de Eliminación Directa")
        with col_btn:
            if st.button("🔄 Limpiar Llaves", use_container_width=True):
                limpiar_llaves()
                st.rerun()

        # Recolectar clasificados CON METADATOS (Zona y Posición)
        clasificados_db = []
        for i in range(num_zonas):
            c1 = st.session_state.get(f"z{i}_1", "(Pendiente)")
            c2 = st.session_state.get(f"z{i}_2", "(Pendiente)")
            if c1 != "(Pendiente)": clasificados_db.append({"nombre": c1, "zona": f"Zona {i+1}", "posicion": 1})
            if c2 != "(Pendiente)": clasificados_db.append({"nombre": c2, "zona": f"Zona {i+1}", "posicion": 2})

        num_clasificados = len(clasificados_db)
        if num_clasificados == 0:
            st.warning("👈 Ve a la pestaña 'Fase de Zonas' y selecciona los clasificados para armar la llave.")
            return

        # 1. Determinar dinámicamente el inicio de la llave
        if num_clasificados <= 8:
            rondas = ['Cuartos', 'Semis', 'Final']
            partidos_ini = 4
        elif num_clasificados <= 16:
            rondas = ['Octavos', 'Cuartos', 'Semis', 'Final']
            partidos_ini = 8
        else:
            rondas = ['16avos', 'Octavos', 'Cuartos', 'Semis', 'Final']
            partidos_ini = 16

        # Generar columnas (Rondas + 1 para el Campeón)
        columnas = st.columns(len(rondas) + 1)
        ganadores_ronda_anterior = []

        # 2. Dibujar el árbol de forma dinámica y alineada
        for i, ronda in enumerate(rondas):
            with columnas[i]:
                st.markdown(f"<h5 style='text-align:center; color:#AAA;'>{ronda}</h5>", unsafe_allow_html=True)
                
                num_partidos_ronda = partidos_ini // (2 ** i)
                ganadores_actuales = []
                
                # Espaciado superior para alinear verticalmente el árbol
                for _ in range((2 ** i) - 1): st.write("")

                for p in range(num_partidos_ronda):
                    match_id = f"R{i}_P{p}"
                    
                    if i == 0:
                        # La primera ronda contiene la lógica de selección y filtro
                        ganador = renderizar_primera_ronda(match_id, f"Llave {p+1}", clasificados_db)
                    else:
                        # Rondas siguientes solo muestran a los que avanzaron
                        idx_p1 = p * 2
                        idx_p2 = p * 2 + 1
                        p1 = ganadores_ronda_anterior[idx_p1] if idx_p1 < len(ganadores_ronda_anterior) else None
                        p2 = ganadores_ronda_anterior[idx_p2] if idx_p2 < len(ganadores_ronda_anterior) else None
                        
                        ganador = renderizar_partido(match_id, p1, p2, f"Partido {p+1}")
                    
                    ganadores_actuales.append(ganador)
                    
                    # Espaciado entre partidos de la misma columna
                    if p < num_partidos_ronda - 1:
                        for _ in range((2 ** (i + 1)) - 1): st.write("")

                ganadores_ronda_anterior = ganadores_actuales

        # 3. Mostrar al Campeón en la última columna
        with columnas[-1]:
            st.markdown("<h5 style='text-align:center; color:#FFD700;'>👑</h5>", unsafe_allow_html=True)
            for _ in range((2 ** len(rondas)) - 2): st.write("") # Alineación vertical final
            
            campeon = ganadores_ronda_anterior[0] if ganadores_ronda_anterior else None
            if campeon:
                st.success(f"🏆 {campeon}")
            else:
                st.info("Esperando...")