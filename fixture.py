import streamlit as st
from datetime import datetime
from helpers import (
    cargar_datos, mostrar_estadisticas_torneo, generar_grafico_timeline,
    mostrar_cuadro_playoff, custom_spinner
)

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