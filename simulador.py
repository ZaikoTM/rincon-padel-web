import streamlit as st
import pandas as pd

def mostrar_simulador():
    st.header("💻 Simulador de Resultados (Pruebas)")
    st.info("Nota: Los cambios realizados aquí NO afectan la base de datos oficial del torneo.")

    # 1. DEFINICIÓN DE PAREJAS (Simuladas para probar la Zona F)
    # En un caso real, podrías traerlas con cargar_datos, pero aquí las definimos para probar
    parejas_test = ["Pareja A", "Pareja B", "Pareja C", "Pareja D"]
    
    st.subheader("🎾 Paso 1: Cargar resultados hipotéticos (Zona de 4)")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Cruces Iniciales**")
        res1 = st.number_input(f"{parejas_test[0]} vs {parejas_test[1]} (Ganador: 0=A, 1=B)", 0, 1, 0)
        res2 = st.number_input(f"{parejas_test[2]} vs {parejas_test[3]} (Ganador: 0=C, 1=D)", 0, 1, 0)
        
        g1 = parejas_test[0] if res1 == 0 else parejas_test[1]
        p1 = parejas_test[1] if res1 == 0 else parejas_test[0]
        g2 = parejas_test[2] if res2 == 0 else parejas_test[3]
        p2 = parejas_test[3] if res2 == 0 else parejas_test[2]

    with col2:
        st.markdown("**Cruces Definitorios**")
        res_g = st.number_input(f"Ganadores: {g1} vs {g2} (Ganador: 0={g1}, 1={g2})", 0, 1, 0)
        res_p = st.number_input(f"Perdedores: {p1} vs {p2} (Ganador: 0={p1}, 1={p2})", 0, 1, 0)

        puesto1 = g1 if res_g == 0 else g2
        puesto2 = g2 if res_g == 0 else g1
        puesto3 = p1 if res_p == 0 else p2
        puesto4 = p2 if res_p == 0 else p1

    # 2. CÁLCULO DE LA TABLA SIMULADA
    orden_simulado = [puesto1, puesto2, puesto3, puesto4]
    
    # Creamos un DataFrame visual para ver cómo quedaría la tabla
    df_simulacion = pd.DataFrame({
        "Posición": [1, 2, 3, 4],
        "Pareja": orden_simulado,
        "Estado": ["Clasifica (1°)", "Clasifica (2°)", "Clasifica (3°)", "Eliminado"]
    })

    st.markdown("---")
    st.subheader("📊 Tabla de Posiciones Resultante")
    
    # Aplicamos estilo para resaltar a los 3 que pasan
    def highlight_qualifiers(s):
        return ['background-color: #004d00' if i < 3 else '' for i in range(len(s))]

    st.table(df_simulacion.style.apply(highlight_qualifiers, axis=0))

    if st.button("Simular Cruce de Octavos"):
        st.write(f"Cruce sugerido: **{puesto1}** vs Clasificado de otra zona.")