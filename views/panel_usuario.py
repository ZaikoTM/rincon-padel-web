import streamlit as st
import random
from helpers import get_data

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