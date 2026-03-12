import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Rincón Padel - Bracket", layout="wide", initial_sidebar_state="collapsed")

st.markdown("<h2 style='text-align: center; color: #00FF00;'>Fase Final: Playoff</h2>", unsafe_allow_html=True)

# Aquí defines tus partidos. En tu app real, esto vendrá de tu base de datos.
# Formato: [ [Cuartos], [Semis], [Final], [Campeón] ]
html_code = """
<!DOCTYPE html>
<html>
<head>
<style>
    body {
        background-color: transparent;
        color: white;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        margin: 0;
        padding: 0;
    }
    .bracket-wrapper {
        display: flex;
        flex-direction: row;
        overflow-x: auto; /* Permite deslizar en celulares */
        padding: 20px;
        gap: 40px; /* Espacio entre rondas */
    }
    .round {
        display: flex;
        flex-direction: column;
        justify-content: space-around;
        min-width: 220px;
    }
    .round-title {
        text-align: center;
        color: #888;
        font-size: 14px;
        margin-bottom: 20px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .match {
        background-color: #1A1A1A;
        border: 1px solid #333;
        border-radius: 6px;
        margin: 15px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        position: relative;
    }
    .team {
        display: flex;
        justify-content: space-between;
        padding: 10px 15px;
        border-bottom: 1px solid #222;
        font-size: 14px;
    }
    .team:last-child {
        border-bottom: none;
    }
    .winner {
        color: #00FF00;
        font-weight: bold;
        background-color: rgba(0, 255, 0, 0.05);
    }
    .score {
        font-weight: bold;
        color: #aaa;
        letter-spacing: 2px;
    }
    .winner .score {
        color: #00FF00;
    }
    
    /* Líneas conectoras básicas */
    .round:not(:last-child) .match::after {
        content: '';
        position: absolute;
        right: -20px;
        top: 50%;
        width: 20px;
        border-top: 2px solid #444;
    }
    
    .campeon-card {
        text-align: center;
        padding: 20px;
        border: 2px solid #00FF00;
        box-shadow: 0 0 15px rgba(0, 255, 0, 0.2);
    }
    
    /* Scrollbar estilizada */
    ::-webkit-scrollbar { height: 8px; }
    ::-webkit-scrollbar-track { background: #111; }
    ::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #00FF00; }
</style>
</head>
<body>

<div class="bracket-wrapper">
    <div class="round">
        <div class="round-title">Cuartos de Final</div>
        
        <div class="match">
            <div class="team winner"><span>Sturla / Villagran</span> <span class="score">6 6</span></div>
            <div class="team"><span>Larrroza / Piazza</span> <span class="score">3 2</span></div>
        </div>
        
        <div class="match">
            <div class="team"><span>Bultrych / Druetta</span> <span class="score">4 3</span></div>
            <div class="team winner"><span>Fernández / Crauford</span> <span class="score">6 6</span></div>
        </div>
        
        <div class="match">
            <div class="team winner"><span>Pareja 5 / Pareja 6</span> <span class="score">7 6</span></div>
            <div class="team"><span>Pareja 7 / Pareja 8</span> <span class="score">5 4</span></div>
        </div>
        
        <div class="match">
            <div class="team"><span>Pareja 9 / Pareja 10</span> <span class="score">1 2</span></div>
            <div class="team winner"><span>Pareja 11 / Pareja 12</span> <span class="score">6 6</span></div>
        </div>
    </div>

    <div class="round">
        <div class="round-title">Semifinales</div>
        
        <div class="match">
            <div class="team"><span>Sturla / Villagran</span> <span class="score">4 6 6</span></div>
            <div class="team winner"><span>Fernández / Crauford</span> <span class="score">6 3 7</span></div>
        </div>
        
        <div class="match">
            <div class="team winner"><span>Pareja 5 / Pareja 6</span> <span class="score">6 6</span></div>
            <div class="team"><span>Pareja 11 / Pareja 12</span> <span class="score">2 3</span></div>
        </div>
    </div>

    <div class="round">
        <div class="round-title">Final</div>
        
        <div class="match">
            <div class="team winner"><span>Fernández / Crauford</span> <span class="score">6 6</span></div>
            <div class="team"><span>Pareja 5 / Pareja 6</span> <span class="score">4 3</span></div>
        </div>
    </div>
    
    <div class="round">
        <div class="round-title">¡Campeones!</div>
        <div class="match campeon-card winner">
            <span style="font-size: 24px;">🏆</span><br>
            <span style="font-size: 18px; margin-top: 10px; display: inline-block;">Fernández / Crauford</span>
        </div>
    </div>

</div>

</body>
</html>
"""

# Inyectamos el HTML en Streamlit. 
# Le damos una altura generosa para que no se corte hacia abajo.
components.html(html_code, height=600, scrolling=True)