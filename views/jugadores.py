import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import plotly.graph_objects as go
from streamlit_lottie import st_lottie
from helpers import (
    get_data, mask_phone_number, registrar_jugador_db,
    eliminar_jugador, autenticar_usuario, load_lottieurl,
    URL_LOTTIE_PLAYER, run_action, cargar_datos
)

# --- CSS GLOBAL DE LA SECCIÓN ---
CSS_JUGADORES = """
<style>
.player-card {
    background: linear-gradient(145deg, #141414, #1a1a1a);
    border: 1px solid #2a2a2a;
    border-radius: 16px;
    padding: 16px;
    margin-bottom: 10px;
    transition: all 0.25s ease;
    cursor: pointer;
    position: relative;
    overflow: hidden;
}
.player-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, #00E676, transparent);
    opacity: 0;
    transition: opacity 0.3s;
}
.player-card:hover { transform: translateY(-4px); border-color: #333; box-shadow: 0 8px 24px rgba(0,0,0,0.4); }
.player-card:hover::before { opacity: 1; }
.player-header { display: flex; align-items: center; gap: 14px; margin-bottom: 10px; }
.player-avatar {
    width: 52px; height: 52px; background: #0d0d0d;
    color: #00E676; border-radius: 50%; display: flex;
    align-items: center; justify-content: center;
    font-size: 1.25rem; font-weight: 900; flex-shrink: 0;
    border: 2px solid #333; letter-spacing: -1px;
}
.player-name { font-size: 1rem; font-weight: 700; color: #f0f0f0; line-height: 1.2; }
.player-cat { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; margin-top: 3px; letter-spacing: 1px; }
.player-body { font-size: 0.82rem; color: #666; margin-top: 8px; line-height: 1.6; }
.player-footer {
    margin-top: 10px; padding-top: 10px; border-top: 1px solid #1e1e1e;
    display: flex; justify-content: space-between; align-items: center; font-size: 0.75rem;
}
.admin-del-btn {
    background: rgba(255,75,75,0.08); border: 1px solid rgba(255,75,75,0.25);
    color: #FF4B4B; border-radius: 6px; padding: 3px 10px;
    font-size: 0.72rem; cursor: pointer; transition: all 0.2s;
    font-weight: 600; letter-spacing: 0.5px;
}
.admin-del-btn:hover { background: rgba(255,75,75,0.2); }
.profile-section {
    background: #0d0d0d; border: 1px solid #1a1a1a;
    border-radius: 16px; padding: 20px; margin-top: 8px;
}
.profile-header {
    display: flex; align-items: center; gap: 20px;
    padding-bottom: 16px; border-bottom: 1px solid #1a1a1a; margin-bottom: 16px;
}
.profile-avatar {
    width: 70px; height: 70px; background: #1a1a1a;
    border: 3px solid #00E676; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.8rem; font-weight: bold; color: #00E676; flex-shrink: 0;
}
.profile-name { font-size: 1.4rem; font-weight: 900; color: #fff; }
.profile-cat { font-size: 0.9rem; color: #00E676; font-weight: bold; margin-top: 4px; }
.profile-loc { font-size: 0.85rem; color: #555; margin-top: 2px; }
.stat-box {
    background: #111; border: 1px solid #1a1a1a; border-radius: 10px;
    padding: 12px 16px; text-align: center;
}
.stat-val { font-size: 1.8rem; font-weight: 900; color: #fff; font-family: 'Courier New', monospace; }
.stat-lbl { font-size: 0.72rem; color: #555; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }
.stat-val-green { color: #00E676; }
.stat-val-red { color: #FF4B4B; }
.history-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 8px 12px; border-radius: 8px; margin-bottom: 5px;
    background: #111; border: 1px solid #1a1a1a;
}
.match-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 7px 12px; margin-bottom: 5px;
    border-radius: 0 8px 8px 0;
}
.cat-badge {
    display: inline-block; background: rgba(0,230,118,0.1);
    color: #00E676; border: 1px solid rgba(0,230,118,0.3);
    border-radius: 99px; padding: 1px 8px; font-size: 0.72rem; font-weight: bold;
}
.h2h-card {
    background-color: #000; border: 2px solid #39FF14; border-radius: 10px;
    padding: 20px; text-align: center; box-shadow: 0 0 15px rgba(57,255,20,0.15);
}
.h2h-stat-val { font-size: 2rem; font-weight: 900; color: #fff; }
.h2h-stat-label { font-size: 0.85rem; color: #39FF14; text-transform: uppercase; letter-spacing: 1px; }
.vs-badge { font-size: 3rem; font-weight: bold; color: #39FF14; text-align: center; margin-top: 20px; }
</style>
"""



# --- CONSTANTES DE CATEGORÍAS ---
CATS_ORDEN = ["Libre", "3ra", "4ta", "5ta", "6ta", "7ma", "8va"]
CATS_COLORES = {
    "Libre": "#FFD700",
    "3ra":   "#FF6B6B",
    "4ta":   "#FF9F43",
    "5ta":   "#00E676",
    "6ta":   "#00B0FF",
    "7ma":   "#AA00FF",
    "8va":   "#888888",
}

def mostrar_jugadores():
    st.markdown(CSS_JUGADORES, unsafe_allow_html=True)

    tab_jugadores, tab_h2h, tab_perfil = st.tabs([
        "👥 Listado de Jugadores", "🆚 H2H", "👤 Mi Perfil"
    ])

    with tab_jugadores:
        _mostrar_listado()

    with tab_h2h:
        _mostrar_h2h()

    with tab_perfil:
        _mostrar_mi_perfil()


# ─────────────────────────────────────────
# LISTADO DE JUGADORES CON PERFIL EXPANDIBLE
# ─────────────────────────────────────────
def _mostrar_listado():
    st.header("🎖️ Jugadores")

    if "jugador_perfil_sel" not in st.session_state:
        st.session_state["jugador_perfil_sel"] = None

    col_search, col_reg = st.columns([3, 1])
    with col_search:
        search_q = st.text_input("Buscar", placeholder="Nombre o apellido...", label_visibility="collapsed")
    with col_reg:
        with st.expander("Registrar"):
            with st.form("form_alta_rapida"):
                c1, c2 = st.columns(2)
                n_nombre   = c1.text_input("Nombre")
                n_apellido = c2.text_input("Apellido")
                n_dni      = c1.text_input("DNI")
                n_cel      = c2.text_input("Celular")
                n_cat      = st.selectbox("Categoria", CATS_ORDEN)
                if st.form_submit_button("Registrar"):
                    if n_dni and n_nombre and n_apellido and n_cel:
                        ok, msg = registrar_jugador_db(n_dni, n_nombre, n_apellido, n_cel, n_cat, "", n_dni)
                        if ok: st.success("Registrado"); st.rerun()
                        else:  st.error(msg)
                    else:
                        st.warning("Completa los campos obligatorios.")

    cat_filter = st.radio(
        "Categoria",
        ["Todas"] + CATS_ORDEN,
        horizontal=True,
        label_visibility="collapsed",
        key="cat_filter_jugadores"
    )

    st.markdown("---")

    df_jug = get_data("SELECT * FROM jugadores ORDER BY apellido, nombre")
    if df_jug is None or df_jug.empty:
        st.info("No hay jugadores registrados.")
        return

    if search_q:
        mask = (
            df_jug['apellido'].str.contains(search_q, case=False, na=False) |
            df_jug['nombre'].str.contains(search_q, case=False, na=False)
        )
        df_jug = df_jug[mask]

    if cat_filter != "Todas":
        df_jug = df_jug[df_jug['categoria_actual'] == cat_filter]

    if df_jug.empty:
        st.info("No se encontraron jugadores.")
        return

    cats_num = {"Libre":1,"3ra":3,"4ta":4,"5ta":5,"6ta":6,"7ma":7,"8va":8}
    def get_trend(row):
        c = cats_num.get(row['categoria_actual'], 99)
        p = cats_num.get(row['categoria_anterior'], 99)
        if not row['categoria_anterior'] or row['categoria_anterior'] == "-": return "Neutro", "#888"
        if c < p: return "Ascenso", "#00E676"
        if c > p: return "Descenso", "#FF4B4B"
        return "Neutro", "#888"

    cats_a_mostrar = [c for c in CATS_ORDEN if c in df_jug['categoria_actual'].values] if cat_filter == "Todas" else [cat_filter]

    for cat in cats_a_mostrar:
        df_cat = df_jug[df_jug['categoria_actual'] == cat]
        if df_cat.empty:
            continue

        color_cat = CATS_COLORES.get(cat, "#00E676")
        n_jug = len(df_cat)
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:12px;margin:20px 0 10px 0;
                    border-left:4px solid {color_cat};padding-left:12px;">
            <span style="font-size:1.15rem;font-weight:900;color:{color_cat};">{cat}</span>
            <span style="font-size:0.8rem;color:#555;background:#111;padding:2px 8px;
                         border-radius:99px;border:1px solid #222;">{n_jug} jugador{"es" if n_jug != 1 else ""}</span>
        </div>
        """, unsafe_allow_html=True)

        cols = st.columns(3)
        for i, (_, row) in enumerate(df_cat.iterrows()):
            trend_txt, trend_color = get_trend(row)
            initials = f"{row['nombre'][0]}{row['apellido'][0]}" if row['nombre'] and row['apellido'] else "?"
            nombre_completo = f"{row['nombre']} {row['apellido']}"
            is_sel = st.session_state["jugador_perfil_sel"] == nombre_completo
            border = "border-color:#00E676;" if is_sel else ""

            with cols[i % 3]:
                es_admin = st.session_state.get('es_admin', False)

                st.markdown(f"""
                <div class="player-card" style="{'border-color:'+color_cat+';box-shadow:0 0 12px '+color_cat+'22;' if is_sel else ''}">
                    <div class="player-header">
                        <div class="player-avatar" style="border-color:{color_cat};color:{color_cat};background:linear-gradient(135deg,#0d0d0d,#1a1a1a);">{initials}</div>
                        <div style="flex:1;min-width:0;">
                            <div class="player-name">{nombre_completo}</div>
                            <div class="player-cat" style="color:{color_cat};">{row['categoria_actual']}</div>
                        </div>
                    </div>
                    <div class="player-body">
                        <span style="color:#555;">📍</span> {row['localidad'] or 'Sin localidad'}<br>
                        <span style="color:#555;">📱</span> {mask_phone_number(row['celular'])}
                    </div>
                    <div class="player-footer">
                        <span style="color:{trend_color};font-weight:700;font-size:0.78rem;">
                            {'▲' if trend_txt=='Ascenso' else '▼' if trend_txt=='Descenso' else '—'} {trend_txt}
                        </span>
                        <span style="color:#333;font-size:0.72rem;">#{row['id']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Botones de acción
                if es_admin:
                    btn_col1, btn_col2 = st.columns([2, 1])
                    with btn_col1:
                        lbl = "✓ Cerrar" if is_sel else "📊 Ver perfil"
                        if st.button(lbl, key=f"btn_perfil_{row['id']}", use_container_width=True):
                            st.session_state["jugador_perfil_sel"] = None if is_sel else nombre_completo
                            st.session_state["jugador_perfil_row"] = row.to_dict()
                            st.rerun()
                    with btn_col2:
                        if st.button("🗑️", key=f"btn_del_{row['id']}", use_container_width=True, help=f"Eliminar a {nombre_completo}"):
                            st.session_state[f"confirm_del_{row['id']}"] = True

                    # Confirmación de eliminación
                    if st.session_state.get(f"confirm_del_{row['id']}", False):
                        st.warning(f"¿Eliminar a **{nombre_completo}**? Esta acción no se puede deshacer.")
                        cc1, cc2 = st.columns(2)
                        with cc1:
                            if st.button("Sí, eliminar", key=f"confirm_yes_{row['id']}", type="primary", use_container_width=True):
                                eliminar_jugador(row['dni'] if 'dni' in row else row['id'])
                                st.session_state.pop(f"confirm_del_{row['id']}", None)
                                st.session_state["jugador_perfil_sel"] = None
                                st.success(f"Jugador eliminado.")
                                st.rerun()
                        with cc2:
                            if st.button("Cancelar", key=f"confirm_no_{row['id']}", use_container_width=True):
                                st.session_state.pop(f"confirm_del_{row['id']}", None)
                                st.rerun()
                else:
                    lbl = "✓ Cerrar" if is_sel else "📊 Ver perfil"
                    if st.button(lbl, key=f"btn_perfil_{row['id']}", use_container_width=True):
                        st.session_state["jugador_perfil_sel"] = None if is_sel else nombre_completo
                        st.session_state["jugador_perfil_row"] = row.to_dict()
                        st.rerun()

    if st.session_state["jugador_perfil_sel"]:
        st.markdown("---")
        nombre_sel = st.session_state["jugador_perfil_sel"]
        row_sel = st.session_state.get("jugador_perfil_row", {})
        st.markdown(f"### Perfil de {nombre_sel}")
        _mostrar_perfil_publico(nombre_sel, row_sel)

# ─────────────────────────────────────────
# PERFIL PÚBLICO EXPANDIBLE
# ─────────────────────────────────────────
def _mostrar_perfil_publico(nombre_completo, row_jugador):
    initials = f"{row_jugador['nombre'][0]}{row_jugador['apellido'][0]}"

    # Encabezado del perfil
    st.markdown(f"""
    <div class="profile-header">
        <div class="profile-avatar">{initials}</div>
        <div>
            <div class="profile-name">{nombre_completo}</div>
            <div class="profile-cat">{row_jugador['categoria_actual']}
                <span class="cat-badge" style="margin-left:8px;">
                    {row_jugador.get('categoria_anterior','') or 'Sin anterior'}
                </span>
            </div>
            <div class="profile-loc">📍 {row_jugador['localidad'] or 'Sin localidad'}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Estadísticas globales
    df_partidos = get_data("""
        SELECT ganador, pareja1, pareja2, resultado, instancia
        FROM partidos
        WHERE (pareja1 LIKE :j OR pareja2 LIKE :j)
          AND estado_partido = 'Finalizado'
    """, params={"j": f"%{nombre_completo}%"})

    total = len(df_partidos) if df_partidos is not None else 0
    wins  = sum(1 for _, r in df_partidos.iterrows() if r['ganador'] and nombre_completo in str(r['ganador'])) if total > 0 else 0
    losses = total - wins
    eff   = round(wins / total * 100) if total > 0 else 0

    df_titulos = get_data("""
        SELECT COUNT(*) as c FROM partidos
        WHERE instancia = 'Final' AND ganador LIKE :j
    """, params={"j": f"%{nombre_completo}%"})
    titulos = int(df_titulos.iloc[0]['c']) if df_titulos is not None and not df_titulos.empty else 0

    s1, s2, s3, s4, s5 = st.columns(5)
    s1.markdown(f"<div class='stat-box'><div class='stat-val'>{total}</div><div class='stat-lbl'>Partidos</div></div>", unsafe_allow_html=True)
    s2.markdown(f"<div class='stat-box'><div class='stat-val stat-val-green'>{wins}</div><div class='stat-lbl'>Victorias</div></div>", unsafe_allow_html=True)
    s3.markdown(f"<div class='stat-box'><div class='stat-val stat-val-red'>{losses}</div><div class='stat-lbl'>Derrotas</div></div>", unsafe_allow_html=True)
    s4.markdown(f"<div class='stat-box'><div class='stat-val'>{eff}%</div><div class='stat-lbl'>Efectividad</div></div>", unsafe_allow_html=True)
    s5.markdown(f"<div class='stat-box'><div class='stat-val' style='color:#FFD700'>🏆{titulos}</div><div class='stat-lbl'>Títulos</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_hist, col_matches = st.columns(2)

    # Historial de torneos con puntos
    with col_hist:
        st.markdown("**🏆 Torneos y puntos**")
        df_pts = get_data("""
            SELECT t.nombre, rp.puntos, rp.categoria, t.fecha
            FROM ranking_puntos rp
            JOIN torneos t ON t.id = rp.torneo_id
            WHERE rp.jugador LIKE :j
            ORDER BY t.fecha DESC
        """, params={"j": f"%{nombre_completo}%"})

        if df_pts is not None and not df_pts.empty:
            total_pts = int(df_pts['puntos'].sum())
            st.caption(f"Total acumulado: **{total_pts} pts**")
            for _, r in df_pts.iterrows():
                st.markdown(f"""
                <div class="history-row">
                    <div>
                        <div style="color:#fff;font-size:0.85rem;font-weight:bold;">{r['nombre']}</div>
                        <div style="color:#555;font-size:0.75rem;">{r['categoria']} · {r['fecha']}</div>
                    </div>
                    <div style="color:#00E676;font-weight:900;font-family:monospace;">+{int(r['puntos'])}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("Sin puntos registrados.")

    # Últimos partidos
    with col_matches:
        st.markdown("**🎾 Últimos partidos**")
        if df_partidos is not None and not df_partidos.empty:
            for _, r in df_partidos.head(6).iterrows():
                gano  = nombre_completo in str(r['ganador'])
                color = "#00E676" if gano else "#FF4B4B"
                label = "Victoria" if gano else "Derrota"
                rival = r['pareja2'] if nombre_completo in str(r['pareja1']) else r['pareja1']
                st.markdown(f"""
                <div class="match-row" style="border-left:3px solid {color}; background:#111;">
                    <div>
                        <div style="color:#fff;font-size:0.85rem;">vs {rival}</div>
                        <div style="color:#555;font-size:0.75rem;">{r['instancia']} · {r['resultado'] or ''}</div>
                    </div>
                    <div style="color:{color};font-size:0.8rem;font-weight:bold;">{label}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("Sin partidos registrados.")

    # Evolución de categoría
    st.markdown("**📈 Evolución de categoría**")
    cats_orden = {"Libre":1,"3ra":2,"4ta":3,"5ta":4,"6ta":5,"7ma":6,"8va":7}
    cat_actual  = row_jugador.get('categoria_actual','')
    cat_anterior= row_jugador.get('categoria_anterior','')

    if cat_actual and cat_anterior and cat_anterior != "-":
        fig = go.Figure()
        puntos_evo = []
        if cat_anterior: puntos_evo.append(("Anterior", cats_orden.get(cat_anterior, 0), cat_anterior))
        if cat_actual:   puntos_evo.append(("Actual",   cats_orden.get(cat_actual, 0),   cat_actual))

        fig.add_trace(go.Scatter(
            x=[p[0] for p in puntos_evo],
            y=[p[1] for p in puntos_evo],
            mode="lines+markers+text",
            text=[p[2] for p in puntos_evo],
            textposition="top center",
            line=dict(color="#00E676", width=3),
            marker=dict(size=12, color="#00E676"),
            textfont=dict(color="#00E676", size=12)
        ))
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#aaa", height=160,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(showgrid=False, tickfont=dict(color="#555")),
            yaxis=dict(showgrid=False, visible=False),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.caption("Sin datos de evolución de categoría.")


# ─────────────────────────────────────────
# H2H
# ─────────────────────────────────────────
def _mostrar_h2h():
    st.header("🆚 Head-to-Head")

    all_players = get_data("SELECT nombre, apellido FROM jugadores ORDER BY apellido")
    if all_players is None or all_players.empty:
        st.info("No hay jugadores para comparar.")
        return

    player_options = [f"{r['nombre']} {r['apellido']}" for _, r in all_players.iterrows()]

    c1, c2 = st.columns(2)
    p1_sel = c1.selectbox("Jugador 1", player_options, index=0, key="h2h_p1")
    p2_sel = c2.selectbox("Jugador 2", player_options, index=min(1, len(player_options)-1), key="h2h_p2")

    if p1_sel == p2_sel:
        st.warning("Seleccioná dos jugadores distintos.")
        return

    # Partidos directos
    df_h2h = get_data("""
        SELECT * FROM partidos
        WHERE (pareja1 LIKE :p1 OR pareja2 LIKE :p1)
          AND (pareja1 LIKE :p2 OR pareja2 LIKE :p2)
          AND ganador IS NOT NULL
    """, params={"p1": f"%{p1_sel}%", "p2": f"%{p2_sel}%"})

    p1_wins = sum(1 for _, r in df_h2h.iterrows() if r['ganador'] and p1_sel in r['ganador']) if df_h2h is not None else 0
    p2_wins = sum(1 for _, r in df_h2h.iterrows() if r['ganador'] and p2_sel in r['ganador']) if df_h2h is not None else 0
    total_h2h = len(df_h2h) if df_h2h is not None else 0

    def get_stats(name):
        df_t = get_data("SELECT count(*) as c FROM partidos WHERE instancia='Final' AND ganador LIKE :n", params={"n": f"%{name}%"})
        titulos = int(df_t.iloc[0]['c']) if df_t is not None and not df_t.empty else 0
        df_m = get_data("SELECT ganador FROM partidos WHERE (pareja1 LIKE :n OR pareja2 LIKE :n) AND ganador IS NOT NULL", params={"n": f"%{name}%"})
        total = len(df_m) if df_m is not None else 0
        wins  = sum(1 for _, r in df_m.iterrows() if name in str(r['ganador'])) if total > 0 else 0
        eff   = round(wins / total * 100, 1) if total > 0 else 0
        return titulos, eff, total, wins

    t1, eff1, tot1, w1 = get_stats(p1_sel)
    t2, eff2, tot2, w2 = get_stats(p2_sel)

    st.markdown("---")

    col_p1, col_vs, col_p2 = st.columns([2, 1, 2])

    with col_p1:
        st.markdown(f"""
        <div class='h2h-card'>
            <h3 style='color:#fff'>{p1_sel}</h3>
            <div class='h2h-stat-val'>{p1_wins}</div>
            <div class='h2h-stat-label'>Victorias directas</div>
            <hr style='border-color:#1a1a1a; margin:12px 0'>
            <div class='h2h-stat-val'>🏆 {t1}</div>
            <div class='h2h-stat-label'>Títulos</div>
            <div class='h2h-stat-val'>{eff1}%</div>
            <div class='h2h-stat-label'>Efectividad global</div>
            <div class='h2h-stat-val' style='font-size:1.2rem;color:#aaa'>{w1}/{tot1}</div>
            <div class='h2h-stat-label'>Victorias / Jugados</div>
        </div>
        """, unsafe_allow_html=True)

    with col_vs:
        st.markdown(f"<div class='vs-badge'>VS</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align:center;color:#555;margin-top:12px;font-size:0.9rem;'>{total_h2h} partidos<br>directos</div>", unsafe_allow_html=True)

    with col_p2:
        st.markdown(f"""
        <div class='h2h-card'>
            <h3 style='color:#fff'>{p2_sel}</h3>
            <div class='h2h-stat-val'>{p2_wins}</div>
            <div class='h2h-stat-label'>Victorias directas</div>
            <hr style='border-color:#1a1a1a; margin:12px 0'>
            <div class='h2h-stat-val'>🏆 {t2}</div>
            <div class='h2h-stat-label'>Títulos</div>
            <div class='h2h-stat-val'>{eff2}%</div>
            <div class='h2h-stat-label'>Efectividad global</div>
            <div class='h2h-stat-val' style='font-size:1.2rem;color:#aaa'>{w2}/{tot2}</div>
            <div class='h2h-stat-label'>Victorias / Jugados</div>
        </div>
        """, unsafe_allow_html=True)

    # Historial de partidos directos
    if df_h2h is not None and not df_h2h.empty:
        st.markdown("---")
        st.markdown("**📋 Historial de enfrentamientos**")
        for _, r in df_h2h.iterrows():
            ganador = r['ganador'] or "?"
            color   = "#00E676" if p1_sel in ganador else "#FF4B4B"
            st.markdown(f"""
            <div style='display:flex;justify-content:space-between;align-items:center;
                        padding:8px 14px;background:#0d0d0d;border:1px solid #1a1a1a;
                        border-radius:8px;margin-bottom:5px;'>
                <span style='color:#aaa;font-size:0.85rem;'>{r['instancia']}</span>
                <span style='color:#fff;font-size:0.85rem;font-weight:bold;'>{r['pareja1']} vs {r['pareja2']}</span>
                <span style='color:{color};font-size:0.85rem;font-weight:bold;'>🏆 {ganador}</span>
                <span style='color:#444;font-size:0.8rem;'>{r['resultado'] or ''}</span>
            </div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────
# MI PERFIL (SESIÓN)
# ─────────────────────────────────────────
def _mostrar_mi_perfil():
    st.header("👤 Mi Perfil")

    if 'usuario' in st.session_state:
        u = st.session_state['usuario']
        nombre_completo = f"{u['nombre']} {u['apellido']}"

        st.success(f"Bienvenido, {u['nombre']}!")
        _mostrar_perfil_publico(nombre_completo, {
            'nombre': u['nombre'],
            'apellido': u['apellido'],
            'categoria_actual': u.get('categoria', ''),
            'categoria_anterior': u.get('categoria_anterior', '-'),
            'localidad': u.get('localidad', '')
        })

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚪 Cerrar Sesión", use_container_width=True):
                del st.session_state['usuario']
                st.rerun()
        with col2:
            with st.expander("⚠️ Zona peligrosa"):
                st.caption("Esta acción es irreversible.")
                if st.button("🗑️ Eliminar mi cuenta", type="secondary", use_container_width=True):
                    run_action("DELETE FROM jugadores WHERE id = %(id)s", {"id": u['id']})
                    del st.session_state['usuario']
                    st.success("Cuenta eliminada.")
                    st.rerun()
    else:
        tab_login, tab_reg = st.tabs(["Iniciar Sesión", "Registrarse"])

        with tab_login:
            lottie_data = load_lottieurl(URL_LOTTIE_PLAYER)
            if lottie_data:
                st_lottie(lottie_data, height=150, key="login_anim")
            with st.form("login_form_main"):
                l_dni  = st.text_input("DNI", placeholder="Tu DNI", label_visibility="collapsed")
                l_pass = st.text_input("Contraseña", placeholder="Contraseña", type="password", label_visibility="collapsed")
                if st.form_submit_button("Entrar", use_container_width=True):
                    user = autenticar_usuario(l_dni, l_pass)
                    if user:
                        st.session_state['usuario'] = user
                        st.success("¡Bienvenido!")
                        st.rerun()
                    else:
                        st.error("Credenciales incorrectas.")

        with tab_reg:
            with st.form("register_form"):
                c1, c2 = st.columns(2)
                r_nombre   = c1.text_input("Nombre")
                r_apellido = c2.text_input("Apellido")
                r_dni      = c1.text_input("DNI (usuario)")
                r_cel      = c2.text_input("Celular")
                r_pass     = st.text_input("Contraseña", type="password")
                r_loc      = st.text_input("Localidad")
                cat_map    = {1:"Libre",2:"3ra",3:"4ta",4:"5ta",5:"6ta",6:"7ma",7:"8va"}
                r_cat_num  = st.slider("Categoría", 1, 7, 5)
                r_cat      = cat_map[r_cat_num]
                st.caption(f"Nivel seleccionado: **{r_cat}**")
                if st.form_submit_button("Crear cuenta", use_container_width=True):
                    if r_dni and r_pass and r_nombre and r_cel:
                        ok, msg = registrar_jugador_db(r_dni, r_nombre, r_apellido, r_cel, r_cat, r_loc, r_pass)
                        if ok: st.success(msg)
                        else:  st.error(msg)
                    else:
                        st.warning("Completá todos los campos obligatorios.")
