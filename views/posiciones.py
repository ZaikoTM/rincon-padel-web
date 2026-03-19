import streamlit as st
from helpers import cargar_datos

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

                grupos = df_zonas.groupby('nombre_zona')
                cols = st.columns(2)
                idx = 0
                
                for nombre, df_grupo in grupos:
                    # Reordenamiento explícito en Pandas
                    df_grupo = df_grupo.sort_values(by=['pts', 'ds', 'dg', 'pg'], ascending=[False, False, False, False])
                    
                    with cols[idx % 2]:
                        # CONSTRUCCIÓN BLINDADA CON TODAS LAS COLUMNAS
                        html_table = f'<div class="pos-card"><div class="pos-zone-header"><span>{nombre}</span><span>🏆</span></div><table class="pos-table"><thead><tr><th class="col-left">PAREJA</th><th>PJ</th><th>PG</th><th class="hide-mob">PP</th><th class="hide-mob">SF</th><th class="hide-mob">SC</th><th>DS</th><th>DG</th><th>PTS</th></tr></thead><tbody>'
                        
                        for i, row in enumerate(df_grupo.itertuples()):
                            is_qualified = i < 2
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
        else:
            st.warning("Selecciona un torneo para ver posiciones.")