import streamlit as st
from helpers import get_data

def show_ranking_content():
    """Fragmento para filtrado y visualización del ranking sin recargar la página."""
    st.header("📈 Ranking Oficial Rincón Padel")

    # 1. Filtro Dinámico de Categoría
    # Leemos las categorías disponibles en la tabla torneos
    df_cats = get_data("SELECT DISTINCT categoria FROM torneos")
    opciones_cat = ["Todas"] + df_cats['categoria'].tolist() if (df_cats is not None and not df_cats.empty) else ["Todas"]
    
    cat_sel = st.selectbox("Filtrar por Categoría", opciones_cat)
    
    # 2. Consulta SQL (Corregida para PostgreSQL)
    if cat_sel == "Todas":
        query = """
            SELECT jugador, SUM(puntos) as total_puntos, COUNT(DISTINCT torneo_id) as torneos_jugados 
            FROM ranking_puntos 
            GROUP BY jugador 
            ORDER BY total_puntos DESC 
            LIMIT 10
        """
        params = {}
    else:
        # Usamos :categoria en lugar de % para evitar errores de sintaxis
        query = """
            SELECT jugador, SUM(puntos) as total_puntos, COUNT(DISTINCT torneo_id) as torneos_jugados 
            FROM ranking_puntos 
            WHERE categoria = :categoria 
            GROUP BY jugador 
            ORDER BY total_puntos DESC 
            LIMIT 10
        """
        params = {"categoria": cat_sel} 
        
    df_ranking = get_data(query, params=params)
    
    # 3. Visualización Estilizada
    if df_ranking is None:
        return
        
    if df_ranking.empty:
        st.info("No hay puntos registrados para esta categoría aún.")
    else:
        # Estilos CSS personalizados
        st.markdown("""
        <style>
            .ranking-card {
                background-color: #000000;
                border: 1px solid #333;
                border-radius: 12px;
                padding: 15px;
                margin-bottom: 12px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            }
            .ranking-pos-box {
                width: 50px;
                text-align: center;
                font-size: 1.5rem;
                font-weight: 900;
                color: #fff;
            }
            .ranking-details {
                flex-grow: 1;
                padding-left: 15px;
            }
            .ranking-name {
                font-size: 1.2rem;
                font-weight: bold;
                color: #fff;
            }
            .ranking-stats {
                text-align: right;
                min-width: 100px;
            }
            .ranking-points {
                color: #00C853;
                font-size: 1.4rem;
                font-weight: 900;
            }
            .ranking-sub {
                color: #888;
                font-size: 0.8rem;
            }
            .leader-card {
                border: 2px solid #00C853;
                box-shadow: 0 0 20px rgba(0, 200, 83, 0.2);
                transform: scale(1.02);
            }
        </style>
        """, unsafe_allow_html=True)
        
        for index, row in df_ranking.iterrows():
            pos = index + 1
            is_leader = "leader-card" if pos == 1 else ""
            medal = "🥇" if pos == 1 else "🥈" if pos == 2 else "🥉" if pos == 3 else f"{pos}°"
            
            st.markdown(f"""
            <div class='ranking-card {is_leader}'>
                <div class='ranking-pos-box'>{medal}</div>
                <div class='ranking-details'>
                    <div class='ranking-name'>{row['jugador']}</div>
                </div>
                <div class='ranking-stats'>
                    <div class='ranking-points'>{row['total_puntos']} pts</div>
                    <div class='ranking-sub'>{row['torneos_jugados']} Torneos</div>
                </div>
            </div>
            """, unsafe_allow_html=True)