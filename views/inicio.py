import streamlit as st
import os
import time
import urllib.parse
from datetime import datetime
from helpers import (
    cargar_datos, obtener_partido_en_vivo, mostrar_tabla_inscritos,
    guardar_inscripcion, custom_spinner, mostrar_consejo_padel
)

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