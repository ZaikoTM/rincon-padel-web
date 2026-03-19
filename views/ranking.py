import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import get_data, cargar_datos

@st.fragment
def show_ranking_content():
    """Ranking oficial con filtro por categoría, estadísticas y gráfico de evolución."""

    st.header("📈 Ranking Oficial Rincón Padel")

    # --- CSS ---
    st.markdown("""
    <style>
        .ranking-card {
            background-color: #0a0a0a;
            border: 1px solid #222;
            border-radius: 14px;
            padding: 14px 18px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: border-color 0.2s, transform 0.2s;
            cursor: pointer;
        }
        .ranking-card:hover { border-color: #00C853; transform: translateX(4px); }
        .leader-card { border: 2px solid #00C853; box-shadow: 0 0 18px rgba(0,200,83,0.15); }
        .ranking-pos { width: 48px; text-align: center; font-size: 1.5rem; font-weight: 900; color: #fff; flex-shrink: 0; }
        .ranking-info { flex-grow: 1; padding-left: 14px; }
        .ranking-name { font-size: 1.1rem; font-weight: bold; color: #fff; }
        .ranking-meta { font-size: 0.8rem; color: #666; margin-top: 3px; }
        .ranking-right { text-align: right; min-width: 90px; }
        .ranking-pts { color: #00C853; font-size: 1.5rem; font-weight: 900; font-family: 'Courier New', monospace; }
        .ranking-sub { color: #555; font-size: 0.78rem; margin-top: 2px; }
        .eff-bar-bg { background: #1a1a1a; border-radius: 4px; height: 4px; width: 80px; margin-top: 4px; display: inline-block; vertical-align: middle; }
        .eff-bar-fill { background: #00C853; height: 4px; border-radius: 4px; }
        .stat-chip { display: inline-block; background: #111; border: 1px solid #333; border-radius: 6px; padding: 4px 10px; font-size: 0.78rem; color: #aaa; margin: 3px 3px 0 0; }
        .stat-chip span { color: #00C853; font-weight: bold; }
        .cat-pill { display: inline-block; background: rgba(0,200,83,0.12); color: #00C853; border: 1px solid rgba(0,200,83,0.3); border-radius: 99px; padding: 2px 10px; font-size: 0.75rem; font-weight: bold; margin-left: 8px; }
    </style>
    """, unsafe_allow_html=True)

    # --- 1. SELECTOR DE CATEGORÍA (pestañas) ---
    df_cats = get_data("SELECT DISTINCT categoria FROM torneos ORDER BY categoria")
    categorias = df_cats['categoria'].tolist() if (df_cats is not None and not df_cats.empty) else []
    todas_las_cats = ["Todas"] + categorias

    cat_sel = st.radio(
        "Categoría",
        todas_las_cats,
        horizontal=True,
        label_visibility="collapsed",
        key="ranking_cat_radio"
    )

    st.markdown("---")

    # --- 2. CONSULTA RANKING ---
    if cat_sel == "Todas":
        query_rank = """
            SELECT
                rp.jugador,
                SUM(rp.puntos) as total_puntos,
                COUNT(DISTINCT rp.torneo_id) as torneos_jugados,
                rp.categoria
            FROM ranking_puntos rp
            GROUP BY rp.jugador, rp.categoria
            ORDER BY total_puntos DESC
            LIMIT 20
        """
        params_rank = {}
    else:
        query_rank = """
            SELECT
                rp.jugador,
                SUM(rp.puntos) as total_puntos,
                COUNT(DISTINCT rp.torneo_id) as torneos_jugados,
                rp.categoria
            FROM ranking_puntos rp
            WHERE rp.categoria = :cat
            GROUP BY rp.jugador, rp.categoria
            ORDER BY total_puntos DESC
            LIMIT 20
        """
        params_rank = {"cat": cat_sel}

    df_ranking = get_data(query_rank, params=params_rank)

    if df_ranking is None or df_ranking.empty:
        st.info("No hay puntos registrados para esta categoría aún.")
        return

    # --- 3. MÉTRICAS RESUMEN ---
    total_jugadores = len(df_ranking)
    lider = df_ranking.iloc[0]['jugador']
    max_pts = int(df_ranking.iloc[0]['total_puntos'])
    avg_pts = int(df_ranking['total_puntos'].mean())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Jugadores", total_jugadores)
    m2.metric("Líder", lider)
    m3.metric("Puntaje máximo", f"{max_pts} pts")
    m4.metric("Promedio", f"{avg_pts} pts")

    st.markdown("---")

    col_lista, col_detalle = st.columns([1.2, 1], gap="large")

    with col_lista:
        st.subheader("🏆 Tabla de posiciones")

        # Estadísticas de partidos por jugador
        df_partidos = get_data("""
            SELECT
                jugador1 as jugador, COUNT(*) as pj,
                SUM(CASE WHEN ganador = jugador1 THEN 1 ELSE 0 END) as pg
            FROM (
                SELECT pareja1 as jugador1, ganador FROM partidos WHERE estado_partido = 'Finalizado'
                UNION ALL
                SELECT pareja2 as jugador1, ganador FROM partidos WHERE estado_partido = 'Finalizado'
            ) sub
            GROUP BY jugador1
        """)

        # Índice de stats para lookup rápido
        stats_idx = {}
        if df_partidos is not None and not df_partidos.empty:
            for _, r in df_partidos.iterrows():
                stats_idx[r['jugador']] = {
                    'pj': int(r['pj']),
                    'pg': int(r['pg']),
                    'eff': round(int(r['pg']) / int(r['pj']) * 100) if int(r['pj']) > 0 else 0
                }

        for i, (_, row) in enumerate(df_ranking.iterrows()):
            pos = i + 1
            is_leader = "leader-card" if pos == 1 else ""
            medal = "🥇" if pos == 1 else "🥈" if pos == 2 else "🥉" if pos == 3 else f"{pos}°"

            jugador = row['jugador']
            pts = int(row['total_puntos'])
            torneos = int(row['torneos_jugados'])
            cat = row.get('categoria', '')

            s = stats_idx.get(jugador, {'pj': 0, 'pg': 0, 'eff': 0})
            eff = s['eff']
            eff_bar_w = eff

            cat_pill = f"<span class='cat-pill'>{cat}</span>" if cat_sel == "Todas" and cat else ""

            st.markdown(f"""
            <div class='ranking-card {is_leader}'>
                <div class='ranking-pos'>{medal}</div>
                <div class='ranking-info'>
                    <div class='ranking-name'>{jugador}{cat_pill}</div>
                    <div class='ranking-meta'>
                        {torneos} torneo{'s' if torneos != 1 else ''} &nbsp;·&nbsp;
                        {s['pj']} partidos &nbsp;·&nbsp;
                        Efectividad: {eff}%
                        <div class='eff-bar-bg'><div class='eff-bar-fill' style='width:{eff_bar_w}%'></div></div>
                    </div>
                </div>
                <div class='ranking-right'>
                    <div class='ranking-pts'>{pts}</div>
                    <div class='ranking-sub'>puntos</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col_detalle:
        st.subheader("📊 Perfil de jugador")

        opciones_jugadores = df_ranking['jugador'].tolist()
        jugador_sel = st.selectbox(
            "Ver estadísticas de",
            opciones_jugadores,
            key="ranking_jugador_sel"
        )

        if jugador_sel:
            _mostrar_perfil_jugador(jugador_sel, stats_idx)

    # --- 4. GRÁFICO DE EVOLUCIÓN ---
    st.markdown("---")
    st.subheader("📈 Evolución de puntos por torneo")
    _mostrar_grafico_evolucion(cat_sel, df_ranking)


def _mostrar_perfil_jugador(jugador, stats_idx):
    """Muestra estadísticas detalladas e historial de un jugador."""

    s = stats_idx.get(jugador, {'pj': 0, 'pg': 0, 'eff': 0})
    pp = s['pj'] - s['pg']

    # Chips de stats
    st.markdown(f"""
    <div style='margin-bottom: 12px;'>
        <div class='stat-chip'>Partidos jugados <span>{s['pj']}</span></div>
        <div class='stat-chip'>Ganados <span>{s['pg']}</span></div>
        <div class='stat-chip'>Perdidos <span>{pp}</span></div>
        <div class='stat-chip'>Efectividad <span>{s['eff']}%</span></div>
    </div>
    """, unsafe_allow_html=True)

    # Historial de torneos con puntos
    df_hist = get_data("""
        SELECT t.nombre as torneo, rp.puntos, rp.categoria, t.fecha
        FROM ranking_puntos rp
        JOIN torneos t ON t.id = rp.torneo_id
        WHERE rp.jugador = :jugador
        ORDER BY t.fecha DESC
    """, params={"jugador": jugador})

    if df_hist is not None and not df_hist.empty:
        st.markdown("**Historial de puntos**")
        for _, r in df_hist.iterrows():
            st.markdown(f"""
            <div style='display:flex; justify-content:space-between; align-items:center;
                        padding: 8px 12px; background:#0a0a0a; border:1px solid #1a1a1a;
                        border-radius:8px; margin-bottom:6px;'>
                <div>
                    <div style='color:#fff; font-size:0.9rem; font-weight:bold;'>{r['torneo']}</div>
                    <div style='color:#555; font-size:0.75rem;'>{r['categoria']} · {r['fecha']}</div>
                </div>
                <div style='color:#00C853; font-weight:900; font-family:monospace; font-size:1.1rem;'>
                    +{int(r['puntos'])} pts
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("Sin historial de torneos registrado.")

    # Últimos partidos
    df_ultimos = get_data("""
        SELECT pareja1, pareja2, ganador, resultado, instancia
        FROM partidos
        WHERE (pareja1 LIKE :j OR pareja2 LIKE :j)
          AND estado_partido = 'Finalizado'
          AND ganador IS NOT NULL
        ORDER BY id DESC
        LIMIT 5
    """, params={"j": f"%{jugador}%"})

    if df_ultimos is not None and not df_ultimos.empty:
        st.markdown("**Últimos partidos**")
        for _, r in df_ultimos.iterrows():
            gano = jugador in str(r['ganador'])
            color = "#00C853" if gano else "#FF4B4B"
            resultado_txt = "Victoria" if gano else "Derrota"
            rival = r['pareja2'] if jugador in str(r['pareja1']) else r['pareja1']
            st.markdown(f"""
            <div style='display:flex; justify-content:space-between; align-items:center;
                        padding:7px 12px; background:#0a0a0a; border-left: 3px solid {color};
                        border-radius:0 8px 8px 0; margin-bottom:5px;'>
                <div>
                    <div style='color:#fff; font-size:0.85rem;'>vs {rival}</div>
                    <div style='color:#555; font-size:0.75rem;'>{r['instancia']} · {r['resultado'] or ""}</div>
                </div>
                <div style='color:{color}; font-size:0.8rem; font-weight:bold;'>{resultado_txt}</div>
            </div>
            """, unsafe_allow_html=True)


def _mostrar_grafico_evolucion(cat_sel, df_ranking):
    """Gráfico de línea con evolución de puntos acumulados por torneo — top 5."""

    top5 = df_ranking.head(5)['jugador'].tolist()

    if cat_sel == "Todas":
        query_evo = """
            SELECT rp.jugador, t.nombre as torneo, t.fecha, rp.puntos
            FROM ranking_puntos rp
            JOIN torneos t ON t.id = rp.torneo_id
            WHERE rp.jugador = ANY(:jugadores)
            ORDER BY rp.jugador, t.fecha ASC
        """
        params_evo = {"jugadores": top5}
    else:
        query_evo = """
            SELECT rp.jugador, t.nombre as torneo, t.fecha, rp.puntos
            FROM ranking_puntos rp
            JOIN torneos t ON t.id = rp.torneo_id
            WHERE rp.jugador = ANY(:jugadores) AND rp.categoria = :cat
            ORDER BY rp.jugador, t.fecha ASC
        """
        params_evo = {"jugadores": top5, "cat": cat_sel}

    df_evo = get_data(query_evo, params=params_evo)

    if df_evo is None or df_evo.empty:
        st.info("No hay suficientes datos para mostrar la evolución.")
        return

    # Calcular puntos acumulados por jugador
    df_evo = df_evo.sort_values(['jugador', 'fecha'])
    df_evo['puntos_acum'] = df_evo.groupby('jugador')['puntos'].cumsum()

    colores = ['#00C853', '#00B0FF', '#FF9100', '#FF4B4B', '#AA00FF']

    fig = go.Figure()
    for i, jugador in enumerate(top5):
        df_j = df_evo[df_evo['jugador'] == jugador]
        if df_j.empty:
            continue
        color = colores[i % len(colores)]
        fig.add_trace(go.Scatter(
            x=df_j['torneo'],
            y=df_j['puntos_acum'],
            mode='lines+markers',
            name=jugador,
            line=dict(color=color, width=2),
            marker=dict(size=8, color=color),
            hovertemplate=f"<b>{jugador}</b><br>Torneo: %{{x}}<br>Puntos acumulados: %{{y}}<extra></extra>"
        ))

    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='#aaa',
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="right", x=1,
            font=dict(color='#aaa', size=12)
        ),
        xaxis=dict(
            showgrid=False,
            tickfont=dict(color='#666'),
            title=None,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#1a1a1a',
            tickfont=dict(color='#666'),
            title="Puntos acumulados",
            titlefont=dict(color='#555')
        ),
        margin=dict(l=10, r=10, t=40, b=10),
        height=320,
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
