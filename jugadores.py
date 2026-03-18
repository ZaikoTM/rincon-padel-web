import streamlit as st
from helpers import (
    get_data, mask_phone_number, registrar_jugador_db, 
    eliminar_jugador, autenticar_usuario, load_lottieurl, 
    URL_LOTTIE_PLAYER, run_action
)

def mostrar_jugadores():
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
                    run_action("DELETE FROM jugadores WHERE id = %(id)s", {"id": u['id']})
                    del st.session_state['usuario']
                    st.success("Tu cuenta y datos han sido eliminados correctamente.")
                    st.rerun()
        else:
            tab1, tab2 = st.tabs(["Iniciar Sesión", "Registrarse"])
            
            with tab1:
                # Animación Login (Jugador)
                lottie_player = load_lottieurl(URL_LOTTIE_PLAYER)
                if lottie_player:
                    st.components.v1.html(lottie_player, height=200)
                with st.form("login_form_main"):
                    l_dni = st.text_input("DNI", placeholder="DNI", label_visibility="collapsed")
                    l_pass = st.text_input("Contraseña", placeholder="Contraseña", type="password", label_visibility="collapsed")
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
                        if r_dni and r_pass and r_nombre and r_cel:
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
                    if n_dni and n_nombre and n_apellido and n_cel:
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
        
        if df_jugadores is not None and not df_jugadores.empty:
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
        if all_players is not None and not all_players.empty:
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
                    WHERE (pareja1 LIKE :p1 OR pareja2 LIKE :p1) 
                    AND (pareja1 LIKE :p2 OR pareja2 LIKE :p2) AND ganador IS NOT NULL
                    """, params={"p1": f"%{p1_sel}%", "p2": f"%{p2_sel}%"})
                
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
                    titles = get_data("SELECT count(*) as c FROM partidos WHERE instancia = 'Final' AND ganador LIKE :player_name", params={"player_name": f"%{player_name}%"}).iloc[0]['c']
                    
                    # Efectividad (Partidos ganados / jugados)
                    matches = get_data("SELECT * FROM partidos WHERE (pareja1 LIKE :player_name OR pareja2 LIKE :player_name) AND ganador IS NOT NULL", params={"player_name": f"%{player_name}%"})
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