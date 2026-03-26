import streamlit as st
from helpers import cargar_datos
from PIL import Image, ImageDraw
import io

def generar_imagen_clasificados(torneo_id):
    query = "SELECT pareja, pts FROM zonas_posiciones WHERE torneo_id = :torneo_id ORDER BY pts DESC"
    df = cargar_datos(query, {"torneo_id": torneo_id})
    
    if df is None or df.empty:
        st.warning("No hay clasificados para este torneo.")
        return

    img = Image.new('RGB', (1080, 1080), color=(18, 18, 18))
    draw = ImageDraw.Draw(img)
    
    draw.text((100, 100), "Clasificados", fill=(57, 255, 20))
    
    y_offset = 200
    for _, row in df.iterrows():
        texto = f"{row['pareja']} - {row['pts']} pts"
        draw.text((100, y_offset), texto, fill=(255, 255, 255))
        y_offset += 50
        
        if y_offset > 1000:
            break

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    
    return st.download_button(
        label="📸 Descargar Imagen para Redes",
        data=buf.getvalue(),
        file_name="clasificados.png",
        mime="image/png"
    )

def mostrar_posiciones():
        tid = st.session_state.get('id_torneo')
        if tid:
            st.header("📊 Tablas de Posiciones")
            
            # Cargar zonas persistentes
            df_zonas = cargar_datos(
                "SELECT * FROM zonas_posiciones WHERE torneo_id = :id ORDER BY nombre_zona ASC, pts DESC, ds DESC, dg DESC, pg DESC", 
                {"id": tid}
            )
            
            if df_zonas is None:
                st.error("Error al cargar datos de zonas.")
                st.stop()
                
            if df_zonas.empty:
                st.info("Las zonas no han sido sorteadas para este torneo.")
            else:
                css_pos = """
                <style>
                .pos-card{background-color:#1A1A1A;border:1px solid #333;border-radius:12px;padding:15px;margin-bottom:20px;box-shadow:0 4px 6px rgba(0,0,0,0.3); overflow-x:auto;}
                .pos-zone-header{color:#00FF00;font-family:'Segoe UI',sans-serif;font-size:1.1rem;font-weight:800;text-transform:uppercase;margin-bottom:12px;border-bottom:2px solid #333;padding-bottom:5px;display:flex;justify-content:space-between}
                .pos-table{width:100%;border-collapse:collapse;font-family:'Segoe UI',sans-serif;font-size:0.85rem;color:#E0E0E0}
                .pos-table th{text-align:center;color:#888;font-weight:600;padding:8px 2px;border-bottom:1px solid #444;font-size:0.75rem;text-transform:uppercase}
                .pos-table td{text-align:center;padding:10px 2px;border-bottom:1px solid #222}
                .col-left{text-align:left !important;width:35%}
                .qualified-row{background-color:rgba(144,238,144,0.05)}
                .qualified-name{color:#90EE90;font-weight:bold;text-shadow:0 0 5px rgba(144,238,144,0.2)}
                .pos-points{color:white;font-weight:900;font-size:1rem}
                @media (max-width: 768px) {
                    .hide-mob { display: none; }
                    .pos-table th, .pos-table td { padding: 6px 1px; font-size: 0.75rem; }
                    .col-left { width: 50%; }
                }
                </style>
                """
                st.markdown(css_pos, unsafe_allow_html=True)
                
                # Cargamos todos los partidos finalizados de la fase de zonas para no saturar la BD iterando
                df_partidos_torneo = cargar_datos(
                    "SELECT pareja1, pareja2, ganador FROM partidos WHERE torneo_id = :id AND instancia = 'Zona' AND estado_partido = 'Finalizado' ORDER BY id ASC", 
                    {"id": tid}
                )

                grupos = df_zonas.groupby('nombre_zona')
                cols = st.columns(2)
                idx = 0
                
                for nombre, df_grupo in grupos:
                    # Reordenamiento por defecto en Pandas (Puntos y Diferencias)
                    df_grupo = df_grupo.sort_values(by=['pts', 'ds', 'dg', 'pg'], ascending=[False, False, False, False])
                    
                    # --- SISTEMA DE ELIMINACIÓN MODIFICADA (ZONAS DE 4 CON 4 PARTIDOS JUGADOS) ---
                    if len(df_grupo) == 4 and df_partidos_torneo is not None and not df_partidos_torneo.empty:
                        parejas_zona = df_grupo['pareja'].tolist()
                        
                        # Filtramos los partidos donde ambos competidores pertenezcan a esta zona en particular
                        partidos_zona = df_partidos_torneo[
                            df_partidos_torneo['pareja1'].isin(parejas_zona) & 
                            df_partidos_torneo['pareja2'].isin(parejas_zona)
                        ]
                        
                        if len(partidos_zona) == 4:
                            cruce1 = partidos_zona.iloc[0]
                            cruce2 = None
                            for idx in range(1, 4):
                                p = partidos_zona.iloc[idx]
                                if p['pareja1'] not in [cruce1['pareja1'], cruce1['pareja2']] and p['pareja2'] not in [cruce1['pareja1'], cruce1['pareja2']]:
                                    cruce2 = p
                                    break
                            if cruce1 is not None and cruce2 is not None:
                                ganador_c1 = cruce1['ganador']
                                ganador_c2 = cruce2['ganador']
                                perdedor_c1 = cruce1['pareja2'] if ganador_c1 == cruce1['pareja1'] else cruce1['pareja1']
                                perdedor_c2 = cruce2['pareja2'] if ganador_c2 == cruce2['pareja1'] else cruce2['pareja1']

                                partido_ganadores = None
                                partido_perdedores = None

                                for idx in range(4):
                                    p = partidos_zona.iloc[idx]
                                    if p.name in [cruce1.name, cruce2.name]: continue
                                    if p['pareja1'] in [ganador_c1, ganador_c2] and p['pareja2'] in [ganador_c1, ganador_c2]:
                                        partido_ganadores = p
                                    if p['pareja1'] in [perdedor_c1, perdedor_c2] and p['pareja2'] in [perdedor_c1, perdedor_c2]:
                                        partido_perdedores = p

                                if partido_ganadores is not None and partido_perdedores is not None:
                                    puesto_1 = partido_ganadores['ganador']
                                    puesto_2 = partido_ganadores['pareja1'] if partido_ganadores['pareja2'] == puesto_1 else partido_ganadores['pareja2']
                                    
                                    puesto_3 = partido_perdedores['ganador']
                                    puesto_4 = partido_perdedores['pareja1'] if partido_perdedores['pareja2'] == puesto_3 else partido_perdedores['pareja2']
                                    
                                    # Forzamos el orden exacto manteniendo intactas las demás columnas para no romper los playoffs
                                    orden_forzado = [puesto_1, puesto_2, puesto_3, puesto_4]
                                    # Creamos una columna temporal de índice basada en el orden, ordenamos y la eliminamos
                                    df_grupo['orden_especial'] = df_grupo['pareja'].map(lambda x: orden_forzado.index(x) if x in orden_forzado else 99)
                                    df_grupo = df_grupo.sort_values('orden_especial').drop(columns=['orden_especial'])
                    
                    with cols[idx % 2]:
                        # CONSTRUCCIÓN BLINDADA CON TODAS LAS COLUMNAS
                        html_table = f'<div class="pos-card"><div class="pos-zone-header"><span>{nombre}</span><span>🏆</span></div><table class="pos-table"><thead><tr><th class="col-left">PAREJA</th><th>PJ</th><th>PG</th><th class="hide-mob">PP</th><th class="hide-mob">SF</th><th class="hide-mob">SC</th><th>DS</th><th>DG</th><th>PTS</th></tr></thead><tbody>'
                        
                        # Lógica dinámica: Si la zona tiene 4 parejas, clasifican 3. Si tiene 3 (o menos), clasifican 2.
                        limite_clasificados = 3 if len(df_grupo) == 4 else 2
                        
                        for i, row in enumerate(df_grupo.itertuples()):
                            is_qualified = i < limite_clasificados
                            row_class = "qualified-row" if is_qualified else ""
                            name_class = "qualified-name" if is_qualified else ""
                            check = "✅" if is_qualified else ""
                            
                            # Fila en una sola línea agregando todas las estadísticas
                            fila = f'<tr class="{row_class}"><td class="col-left {name_class}">{row.pareja} <span style="font-size:0.7rem;">{check}</span></td><td>{row.pj}</td><td>{row.pg}</td><td class="hide-mob">{row.pp}</td><td class="hide-mob">{row.sf}</td><td class="hide-mob">{row.sc}</td><td>{row.ds}</td><td style="color:#666;">{row.dg}</td><td class="pos-points">{row.pts}</td></tr>'
                            html_table += fila
                            
                        html_table += '</tbody></table></div>'
                        
                        # APLASTAMIENTO FINAL (Opción Nuclear)
                        html_table = " ".join(html_table.split())
                        
                        st.markdown(html_table, unsafe_allow_html=True)
                    idx += 1
                    
            st.markdown("---")
            st.subheader("📲 Compartir Resultados")
            st.write("Genera una imagen lista para subir a Instagram o WhatsApp con los clasificados.")
            generar_imagen_clasificados(tid)
        else:
            st.warning("Selecciona un torneo para ver posiciones.")