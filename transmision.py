import streamlit as st
import streamlit.components.v1 as components
from helpers import obtener_partido_en_vivo, cargar_datos

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