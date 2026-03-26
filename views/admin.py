import streamlit as st
import os
import time
import io
from datetime import datetime, timedelta
from PIL import Image
from helpers import (
    run_action, verificador_cupos, crear_torneo, cargar_datos, limpiar_cache,
    eliminar_pareja_torneo, generar_zonas, generar_partidos_desde_zonas_existentes,
    iniciar_torneo, generar_fixture_automatico, cronograma_visual, seccion_gestion_horarios,
    seccion_carga_resultados, cerrar_zonas_y_generar_playoffs, mostrar_cuadro_playoff,
    get_data, create_wa_link, seccion_transferir_jugadores, recategorizar_jugador,
    sincronizar_datos_nube_a_local, guardar_foto, registrar_jugador_db, eliminar_jugador,
    detener_partido, actualizar_estado_partido, obtener_puntos_display, sumar_punto,
    actualizar_marcador, actualizar_tabla_posiciones, actualizar_bracket,
    get_inscripcion_by_pareja, debug_base_datos, generar_partidos_definicion
)

def mostrar_panel_admin():
    if not st.session_state.es_admin:
        st.error("Acceso denegado. Inicia sesión como administrador.")
    else:
        st.header("⚙️ Panel de Administración")
        
        # TAREA 1: Borrador de Emergencia
        with st.expander("🚨 Zona de Peligro (Fix Emergencia)"):
            st.warning("Usar solo si el Torneo ID 4 está causando conflictos.")
            if st.button("🗑️ ELIMINAR TORNEO ID 4 (Borrador de Emergencia)"):
                 run_action('DELETE FROM torneos WHERE id = 4')
                 run_action('DELETE FROM inscripciones WHERE torneo_id = 4')
                 st.success('Torneo 4 eliminado correctamente')
                 st.cache_data.clear()
                 time.sleep(1)
                 st.rerun()
        
        verificador_cupos()
        
        tab_gestion_torneo, tab_validaciones, tab_transferencias, tab_admin_gral, tab_admin_fotos, tab_carga_puntos, tab_admin_socios, tab_control_vivo = st.tabs(["🏆 Gestión de Torneo", "✅ Inscripciones por Validar", "🔄 Transferencias", "🔧 Configuración General", "📷 Gestión de Fotos", "📊 Carga de Puntos", "👥 Administración de Socios", "⚡ Control en Vivo"])
        
        with tab_gestion_torneo:
            st.markdown("""
            <style>
                .admin-card {
                    background-color: #000000;
                    border: 2px solid #00C853;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 0 10px rgba(0, 200, 83, 0.5);
                    margin-bottom: 20px;
                }
                .stTextInput input {
                    border: 1px solid #333;
                }
            </style>
            """, unsafe_allow_html=True)
            
            st.markdown("<div class='admin-card'>", unsafe_allow_html=True)
            st.subheader("🚀 Activar Nuevo Torneo")
            
            # Inicializar keys para limpieza de inputs
            if 'admin_t_nombre' not in st.session_state: st.session_state.admin_t_nombre = ""
            if 'admin_t_cat_custom' not in st.session_state: st.session_state.admin_t_cat_custom = ""
            if 'uploader_key' not in st.session_state: st.session_state.uploader_key = 0

            n_torneo = st.text_input("Nombre del Torneo", placeholder="Ej: Suma 13 - Apertura", key="admin_t_nombre")
            f_evento = st.date_input("Fecha del Evento", min_value=datetime.today())
            
            # Selector de rango horario
            c_hora1, c_hora2 = st.columns(2)
            h_inicio = c_hora1.time_input("Hora de Inicio", value=datetime.strptime("09:00", "%H:%M").time())
            h_fin = c_hora2.time_input("Hora de Fin", value=datetime.strptime("23:00", "%H:%M").time())
            # RECORDATORIO: El complejo tiene una sola cancha, por lo que la lógica futura de partidos deberá respetar ese bloque horario estricto
            
            cats = ["Libre", "3ra", "4ta", "5ta", "6ta", "7ma", "8va", "Suma 12", "Suma 13", "Otra (Escribir nueva...)"]
            c_torneo_sel = st.selectbox("Categoría", cats)
            
            c_torneo_final = c_torneo_sel
            if c_torneo_sel == "Otra (Escribir nueva...)":
                c_torneo_final = st.text_input("Nombre de la Categoría Nueva", placeholder="Ej: Suma 15", key="admin_t_cat_custom")
            
            es_puntuable = st.checkbox("¿Asigna Puntos al Ranking?", value=True, key="check_puntuable_new")
            
            # Configuración Tie-break
            use_stb = st.checkbox("Habilitar Super Tie-break (3er Set)", value=False)
            pts_stb = st.number_input("Puntos Super Tie-break", value=10, min_value=1) if use_stb else 10
            
            afiche_nuevo = st.file_uploader("Subir Afiche (Opcional)", type=['jpg', 'png', 'jpeg'], key=f"afiche_{st.session_state.uploader_key}")
            
            if st.button("🚀 ACTIVAR TORNEO"):
                if n_torneo and c_torneo_final:
                    new_id = crear_torneo(n_torneo, f_evento, c_torneo_final, es_puntuable, use_stb, pts_stb)
                    
                    if new_id and afiche_nuevo:
                        if not os.path.exists("assets"):
                            os.makedirs("assets")
                        file_path = os.path.join("assets", afiche_nuevo.name)
                        with open(file_path, "wb") as f:
                            f.write(afiche_nuevo.getbuffer())
                        
                        run_action("INSERT INTO eventos (torneo_id, afiche) VALUES (%(torneo_id)s, %(afiche)s)", {"torneo_id": new_id, "afiche": file_path})

                    st.success("✅ Torneo creado y guardado exitosamente.")
                    # Limpiar inputs
                    st.session_state.uploader_key += 1
                    st.rerun()
                else:
                    st.warning("⚠️ El nombre del torneo y la categoría son obligatorios.")
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("<div class='admin-card'>", unsafe_allow_html=True)
            st.subheader("🏆 Configuración de Torneo Activo")
            
            # Permitir gestionar torneos 'Abierto', 'En Juego' e 'Inactivo' (sin cache)
            # Usamos cargar_datos para evitar caché y asegurar que los IDs correspondan al estado real de la DB
            all_active_tournaments = cargar_datos("SELECT * FROM torneos WHERE estado IN ('Abierto', 'En Juego', 'Inactivo') ORDER BY id DESC")
            
            if all_active_tournaments is not None and not all_active_tournaments.empty:
                # Mapa de IDs a Nombres. Usamos int() explícito para las claves para evitar errores de tipo numpy/int
                torneo_dict = {int(row['id']): f"{row['nombre']} ({row['categoria']}) - {row['estado']}" for _, row in all_active_tournaments.iterrows()}

                # --- GESTIÓN DE ESTADO ROBUSTA ---
                # Si el ID guardado no existe (fue borrado) o no está inicializado, reseteamos al primero de la lista.
                if 'admin_id_torneo' not in st.session_state or st.session_state.admin_id_torneo not in torneo_dict:
                    st.session_state.admin_id_torneo = int(all_active_tournaments.iloc[0]['id'])

                # Selector vinculado directamente a la sesión. Streamlit maneja la actualización automáticamente.
                st.selectbox(
                    "Seleccionar Torneo Activo", 
                    options=list(torneo_dict.keys()),
                    format_func=lambda x: torneo_dict.get(x, f"ID: {x}"),
                    key="admin_id_torneo" # Vinculación directa
                )
                
                # Ahora, la fuente de verdad es siempre st.session_state.admin_id_torneo
                id_real = st.session_state.admin_id_torneo
                
                t_data = all_active_tournaments[all_active_tournaments['id'] == id_real].iloc[0]
                
                # Persistir categoría para filtros estables
                st.session_state.admin_cat_torneo = t_data['categoria']
                
                # --- FORMULARIO DE EDICIÓN ---
                c1, c2 = st.columns(2)
                new_name = c1.text_input("Nombre del Torneo", value=t_data['nombre'])
                
                # Configuración de fechas (Rango)
                val_fechas = []
                try:
                    d = datetime.strptime(t_data['fecha'], "%Y-%m-%d")
                    val_fechas = [d, d]
                except:
                    val_fechas = [datetime.now(), datetime.now()]

                new_date = c2.date_input("Fecha (Seleccionar Rango)", value=val_fechas)
                
                cat_options = ["Libre", "3ra", "4ta", "5ta", "6ta", "7ma", "8va", "Suma 12", "Suma 13"]
                curr_cat_idx = cat_options.index(t_data['categoria']) if t_data['categoria'] in cat_options else 0
                new_cat = st.selectbox("Categoría", cat_options, index=curr_cat_idx, key=f"edit_cat_{id_real}")
                
                val_puntuable = True
                if 'es_puntuable' in t_data and t_data['es_puntuable'] == 0:
                    val_puntuable = False
                edit_es_puntuable = st.checkbox("¿Asigna Puntos al Ranking?", value=val_puntuable, key="check_puntuable_edit")
                
                # Configuración Tie-break Edit
                val_stb = True if t_data.get('super_tiebreak', 0) == 1 else False
                edit_stb = st.checkbox("Habilitar Super Tie-break", value=val_stb, key="edit_stb")
                edit_pts_stb = st.number_input("Puntos STB", value=t_data.get('puntos_tiebreak', 10), key="edit_pts_stb") if edit_stb else 10
                
                st.markdown("---")
                st.write("📸 **Afiche Promocional**")
                afiche_file = st.file_uploader("Subir imagen (JPG/PNG)", type=['jpg', 'png', 'jpeg'])
                
                st.markdown("---")
                
                # --- BOTONES DE GESTIÓN ---
                c_save, c_state, c_del = st.columns(3)
                
                # 1. GUARDAR
                with c_save:
                    if st.button("💾 Guardar Cambios", type="primary", use_container_width=True):
                        fecha_str = t_data['fecha']
                        if isinstance(new_date, (list, tuple)):
                            if len(new_date) == 2:
                                ini, fin = new_date
                                fecha_str = f"{ini.strftime('%d/%m')} al {fin.strftime('%d/%m')}"
                            elif len(new_date) == 1:
                                ini = new_date[0]
                                fecha_str = f"{ini.strftime('%d/%m')} al {ini.strftime('%d/%m')}"

                        run_action("UPDATE torneos SET nombre=%(nombre)s, fecha=%(fecha)s, categoria=%(categoria)s, es_puntuable=%(es_puntuable)s, super_tiebreak=%(stb)s, puntos_tiebreak=%(ptb)s WHERE id=%(id)s", {"nombre": new_name, "fecha": fecha_str, "categoria": new_cat, "es_puntuable": 1 if edit_es_puntuable else 0, "stb": 1 if edit_stb else 0, "ptb": edit_pts_stb, "id": id_real})
                        
                        if afiche_file:
                            if not os.path.exists("assets"):
                                os.makedirs("assets")
                            file_path = os.path.join("assets", afiche_file.name)
                            with open(file_path, "wb") as f:
                                f.write(afiche_file.getbuffer())
                            
                            df_ev = cargar_datos("SELECT id FROM eventos WHERE torneo_id=:torneo_id", {"torneo_id": id_real})
                            if df_ev is not None and not df_ev.empty:
                                run_action("UPDATE eventos SET afiche=%(afiche)s WHERE torneo_id=%(torneo_id)s", {"afiche": file_path, "torneo_id": id_real})
                            else:
                                run_action("INSERT INTO eventos (torneo_id, afiche) VALUES (%(torneo_id)s, %(afiche)s)", {"torneo_id": id_real, "afiche": file_path})
                        
                        st.toast("✅ Cambios guardados correctamente", icon="💾")
                        limpiar_cache()
                        time.sleep(1)
                        st.rerun()

                # 2. ACTIVAR / DESACTIVAR
                with c_state:
                    if t_data['estado'] == 'Inactivo':
                        if st.button("▶️ Activar Torneo", use_container_width=True):
                            run_action("UPDATE torneos SET estado = 'Abierto' WHERE id = %(id)s", {"id": id_real})
                            st.toast("✅ Torneo Activado", icon="👁️")
                            limpiar_cache()
                            time.sleep(1)
                            st.rerun()
                    else:
                        if st.button("⏸️ Desactivar Torneo", use_container_width=True):
                            run_action("UPDATE torneos SET estado = 'Inactivo' WHERE id = %(id)s", {"id": id_real})
                            st.toast("⏸️ Torneo Desactivado", icon="🙈")
                            limpiar_cache()
                            time.sleep(1)
                            st.rerun()

                # 3. ELIMINAR
                with c_del:
                    confirm_del = st.checkbox("Confirmar Borrado", key="chk_del_torneo")
                    if st.button("🗑️ Eliminar Torneo", type="secondary", disabled=not confirm_del, use_container_width=True):
                        run_action("DELETE FROM partidos WHERE torneo_id = %(id)s", {"id": id_real})
                        run_action("DELETE FROM inscripciones WHERE torneo_id = %(id)s", {"id": id_real})
                        run_action("DELETE FROM zonas WHERE torneo_id = %(id)s", {"id": id_real})
                        run_action("DELETE FROM zonas_posiciones WHERE torneo_id = %(id)s", {"id": id_real})
                        run_action("DELETE FROM eventos WHERE torneo_id = %(id)s", {"id": id_real})
                        run_action("DELETE FROM ranking_puntos WHERE torneo_id = %(id)s", {"id": id_real})
                        run_action("DELETE FROM partido_en_vivo WHERE torneo = %(nombre)s", {"nombre": t_data['nombre']})
                        run_action("DELETE FROM torneos WHERE id = %(id)s", {"id": id_real})
                        
                        st.toast("🗑️ Torneo eliminado correctamente.", icon="🗑️")
                        limpiar_cache()
                        time.sleep(1)
                        st.rerun()

                st.markdown("---")
                
                # --- BAJA DE PAREJAS ---
                st.subheader("⬇️ Dar de Baja Pareja (Inscripciones Validadas)")
                st.write("Usa esta opción si una pareja abandona el torneo antes del sorteo de zonas.")
                
                # Obtenemos solo las parejas validadas del torneo actual
                df_bajas = cargar_datos("SELECT id, jugador1, jugador2 FROM inscripciones WHERE torneo_id = :tid AND estado_validacion = 'Validado'", {"tid": id_real})
                
                if df_bajas is not None and not df_bajas.empty:
                    opts_baja = {row['id']: f"{row['jugador1']} - {row['jugador2']}" for _, row in df_bajas.iterrows()}
                    
                    baja_sel = st.selectbox("Seleccionar pareja a dar de baja", options=list(opts_baja.keys()), format_func=lambda x: opts_baja[x])
                    
                    with st.expander("⚠️ Confirmar Borrado Definitivo", expanded=False):
                        st.write("Estás a punto de dar de baja y borrar de la base de datos a la pareja:")
                        st.markdown(f"<h3 style='color: #FF4B4B; text-align: center;'>{opts_baja[baja_sel]}</h3>", unsafe_allow_html=True)
                        st.warning("Esta acción es irreversible y liberará un cupo en el torneo. ¿Estás seguro de que deseas continuar?")
                        if st.button("Sí, eliminar definitivamente", type="primary", use_container_width=True):
                            eliminar_pareja_torneo(baja_sel, id_real)
                            st.cache_data.clear()
                            st.success("Pareja eliminada definitivamente del torneo.")
                            time.sleep(1.5)
                            st.rerun()
                else:
                    st.info("No hay parejas validadas para dar de baja en este torneo.")

                st.markdown("---")

                # --- FASE PREVIA: GESTIÓN DE ZONAS ---
                st.subheader("2. Fase Previa: Gestión de Zonas")
                if t_data['estado'] == 'Abierto':
                    # Obtener inscriptos validados para la categoría del torneo
                    df_insc_man = cargar_datos("SELECT jugador1, jugador2, estado_validacion, categoria FROM inscripciones WHERE torneo_id = :torneo_id", params={"torneo_id": int(id_real)})

                    if df_insc_man is not None and not df_insc_man.empty:
                        df_insc_man = df_insc_man[df_insc_man['estado_validacion'].astype(str).str.lower() == 'validado']
                        cat_torneo_norm = str(st.session_state.admin_cat_torneo).strip().lower()
                        df_insc_man = df_insc_man[df_insc_man['categoria'].astype(str).str.strip().str.lower() == cat_torneo_norm]
                    
                    parejas_total = [f"{row['jugador1']} - {row['jugador2']}" for _, row in df_insc_man.iterrows()]
                    
                    # Obtener parejas ya asignadas a una zona
                    df_asignados = cargar_datos("SELECT pareja FROM zonas WHERE torneo_id = :torneo_id", params={"torneo_id": int(id_real)})
                    asignados = df_asignados['pareja'].tolist() if (df_asignados is not None and not df_asignados.empty) else []
                    
                    # Filtrar para obtener solo las parejas disponibles para asignación manual
                    disponibles = [p for p in parejas_total if p not in asignados]


                    c_z1, c_z2 = st.columns(2)
                    with c_z1:
                        st.subheader("Opción A: Sorteo Automático")
                        
                        # --- SOLUCIÓN PROBLEMA 1: Selector de Preferencia ---
                        pref_zona = st.radio("Tamaño Preferido de Zona", [3, 4], index=1, horizontal=True, help="El sistema intentará armar la mayor cantidad de grupos de este tamaño.")
                        
                        if st.button("🎲 Generar Zonas Aleatorias", key="btn_sorteo_admin"):
                            # Usamos variables estables
                            success, msg = generar_zonas(id_real, st.session_state.admin_cat_torneo, pref_tamano=pref_zona)
                            
                            if success:
                                st.success("¡Zonas generadas con éxito!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(msg)
                    with c_z2:
                        st.subheader("Opción B: Asignación Manual")

                        # 3. Formulario de Asignación
                        with st.form("form_zona_manual"):
                            z_letras = [f"Zona {l}" for l in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]
                            sel_zona_man = st.selectbox("Seleccionar Zona", z_letras)
                            # Key dinámica basada en id_safe para limpiar al cambiar de torneo
                            sel_parejas_man = st.multiselect("Seleccionar Parejas Disponibles", disponibles, key=f"sel_parejas_{id_real}")
                            
                            if st.form_submit_button("💾 Asignar a Zona"):
                                if sel_parejas_man:
                                    for p in sel_parejas_man:
                                        # Insertar en Zonas y Posiciones
                                        run_action("INSERT INTO zonas (torneo_id, nombre_zona, pareja) VALUES (%(torneo_id)s, %(nombre_zona)s, %(pareja)s)", {"torneo_id": int(id_real), "nombre_zona": sel_zona_man, "pareja": p})
                                        run_action("INSERT INTO zonas_posiciones (torneo_id, nombre_zona, pareja) VALUES (%(torneo_id)s, %(nombre_zona)s, %(pareja)s)", {"torneo_id": int(id_real), "nombre_zona": sel_zona_man, "pareja": p})
                                    st.success(f"Asignados {len(sel_parejas_man)} parejas a {sel_zona_man}")
                                    limpiar_cache()
                                    st.rerun()
                                else:
                                    st.warning("Selecciona al menos una pareja.")
                        
                        # 4. Acciones Globales
                        c_conf, c_reset = st.columns(2)
                        if c_conf.button("✅ Confirmar Todas", help="Generar Fixture"):
                             if (df_asignados is not None and not df_asignados.empty) or len(asignados) > 0:
                                 ok, msg = generar_partidos_desde_zonas_existentes(int(id_real))
                                 if ok:
                                     st.success(msg)
                                     time.sleep(1)
                                     st.rerun()
                                 else:
                                     st.error(msg)
                             else:
                                 st.error("No hay zonas creadas.")
                        
                        if c_reset.button("🗑️ Resetear", help="Borrar todas las zonas"):
                            run_action("DELETE FROM zonas WHERE torneo_id = %(torneo_id)s", {"torneo_id": int(id_real)})
                            run_action("DELETE FROM zonas_posiciones WHERE torneo_id = %(torneo_id)s", {"torneo_id": int(id_real)})
                            run_action("DELETE FROM partidos WHERE torneo_id = %(torneo_id)s AND instancia = 'Zona'", {"torneo_id": int(id_real)})
                            limpiar_cache()
                            st.rerun()
                else:
                    st.info("El torneo ya está en juego. Las zonas no se pueden modificar.")
                
                # Visualización de Zonas Generadas
                df_zonas_admin = cargar_datos("SELECT * FROM zonas WHERE torneo_id = :torneo_id ORDER BY nombre_zona", params={"torneo_id": id_real})
                if df_zonas_admin is not None and not df_zonas_admin.empty:
                    st.markdown("##### 📋 Vista Previa de Zonas")
                    grupos = df_zonas_admin.groupby('nombre_zona')
                    cols_z = st.columns(3)
                    for i, (nombre, grupo) in enumerate(grupos):
                        with cols_z[i % 3]:
                            st.info(f"**{nombre}**")
                            for _, row in grupo.iterrows():
                                st.caption(f"• {row['pareja']}")
                                
                    st.markdown("---")
                    
                    st.markdown("##### ⚔️ Partidos de Definición (Zonas de 4)")
                    if st.button("Generar partidos de definición de Zona", type="primary", key="btn_def_zonas"):
                        ok, msg = generar_partidos_definicion(id_real)
                        if ok: st.success(msg)
                        else: st.error(msg)
                        time.sleep(2)
                        st.rerun()

                    st.markdown("##### 🗑️ Limpiar Partidos por Zona")
                    nombres_zonas = list(grupos.groups.keys())
                    zona_a_borrar = st.selectbox("Seleccionar Zona", nombres_zonas, key="sel_zona_borrar")
                    if st.button(f"Borrar Partidos de {zona_a_borrar}", type="primary"):
                        run_action("""
                            DELETE FROM partidos 
                            WHERE torneo_id = %(tid)s 
                            AND instancia = 'Zona'
                            AND pareja1 IN (SELECT pareja FROM zonas WHERE torneo_id = %(tid)s AND nombre_zona = %(zona)s)
                            AND pareja2 IN (SELECT pareja FROM zonas WHERE torneo_id = %(tid)s AND nombre_zona = %(zona)s)
                        """, {"tid": int(id_real), "zona": zona_a_borrar})
                        st.success(f"✅ Partidos de la {zona_a_borrar} eliminados con éxito.")
                        limpiar_cache()
                        time.sleep(1)
                        st.rerun()

                st.markdown("---")
                # --- BOTÓN INICIAR TORNEO ---
                st.subheader("3. Iniciar Competencia")
                if t_data['estado'] == 'Abierto':
                    st.warning("⚠️ Al iniciar el torneo se cerrarán las inscripciones y se habilitará la carga de resultados.")
                    if st.button("🚀 INICIAR TORNEO", type="primary", use_container_width=True):
                        iniciar_torneo(id_real)
                        st.success("¡Torneo Iniciado! Ahora puedes gestionar los partidos en 'Control en Vivo'.")
                        st.rerun()
                else:
                    st.success("✅ Torneo En Curso")
                
                st.markdown("---")
                st.subheader("📅 Generador de Fixture Automático")
                st.write("Define los rangos horarios para cada día del torneo. El sistema distribuirá los partidos de zona automáticamente.")
                
                # Parse tournament dates
                tournament_dates = []
                date_str = t_data['fecha']
                anio_actual = datetime.now().year
                
                if " al " in str(date_str):
                    try:
                        inicio_str, fin_str = date_str.split(" al ")
                        f_ini = datetime.strptime(f"{inicio_str}/{anio_actual}", "%d/%m/%Y").date()
                        f_fin = datetime.strptime(f"{fin_str}/{anio_actual}", "%d/%m/%Y").date()
                        
                        if f_fin < f_ini:
                            f_fin = f_fin.replace(year=anio_actual + 1)
                            
                        delta = f_fin - f_ini
                        for i in range(delta.days + 1):
                            tournament_dates.append(f_ini + timedelta(days=i))
                    except ValueError:
                        st.warning(f"No se pudo interpretar el rango de fechas '{date_str}'. Usando fecha de hoy.")
                        tournament_dates = [datetime.today().date()]
                else:
                    try:
                        tournament_dates = [datetime.strptime(date_str, "%Y-%m-%d").date()]
                    except ValueError:
                        st.warning(f"No se pudo interpretar la fecha '{date_str}'. Usando fecha de hoy.")
                        tournament_dates = [datetime.today().date()]

                # UI for time ranges
                programacion_dias = []
                for dia in tournament_dates:
                    st.markdown(f"**Día: {dia.strftime('%A, %d de %B')}**")
                    cols = st.columns(2)
                    h_inicio = cols[0].time_input("Hora de Inicio", value=datetime.strptime("14:00", "%H:%M").time(), key=f"start_{dia}")
                    h_fin = cols[1].time_input("Hora de Fin", value=datetime.strptime("23:00", "%H:%M").time(), key=f"end_{dia}")
                    if h_inicio >= h_fin:
                        st.error("La hora de fin debe ser posterior a la hora de inicio.")
                    programacion_dias.append({'fecha': dia, 'inicio': h_inicio, 'fin': h_fin})
                
                if st.button("🚀 Generar Horarios"):
                    if any(d['inicio'] >= d['fin'] for d in programacion_dias):
                        st.error("Corrige los rangos horarios inválidos (inicio debe ser antes que fin) antes de generar el fixture.")
                    else:
                        success, msg = generar_fixture_automatico(id_real, programacion_dias)
                        if success:
                            st.success(msg)
                        else:
                            st.error(msg)
                
                st.markdown("---")
                st.subheader("🛠️ Edición Manual de Horarios")
                
                # Nuevas funciones implementadas
                cronograma_visual(id_real)
                seccion_gestion_horarios(id_real)
                seccion_carga_resultados(id_real)
                
                st.markdown("---")
                st.subheader("4. Fase Final: Playoffs")
                
                tipo_cierre = st.radio("Modo de cierre", ["Cierre Automático", "Cierre Manual", "Armado Manual de Llaves"], horizontal=True)
                manual_positions = {}
                
                if tipo_cierre == "Cierre Manual":
                    st.info("Asigna manualmente las posiciones de cada zona. Los no seleccionados quedarán eliminados.")
                    df_z_admin = cargar_datos("SELECT nombre_zona, pareja FROM zonas WHERE torneo_id = :tid ORDER BY nombre_zona", {"tid": id_real})
                    if df_z_admin is not None and not df_z_admin.empty:
                        for z_name, df_g in df_z_admin.groupby('nombre_zona'):
                            parejas_zona = df_g['pareja'].tolist()
                            st.markdown(f"**{z_name}**")
                            c1, c2, c3 = st.columns(3)
                            p1 = c1.selectbox(f"1º {z_name}", ["(Ninguno)"] + parejas_zona, key=f"m1_{z_name}_{id_real}")
                            p2_opts = ["(Ninguno)"] + [p for p in parejas_zona if p != p1 or p1 == "(Ninguno)"]
                            p2 = c2.selectbox(f"2º {z_name}", p2_opts, key=f"m2_{z_name}_{id_real}")
                            p3_opts = ["(Ninguno)"] + [p for p in parejas_zona if p not in (p1, p2) or (p == "(Ninguno)")]
                            p3 = c3.selectbox(f"3º {z_name}", p3_opts, key=f"m3_{z_name}_{id_real}")
                            manual_positions[z_name] = [p1, p2, p3]
                elif tipo_cierre == "Armado Manual de Llaves":
                    st.info("Configura los cruces manualmente asignando parejas a cada posición del cuadro.")
                    
                    clasificados_base = []
                    df_z_pos = cargar_datos("SELECT nombre_zona, pareja, pts, ds, dg, pg FROM zonas_posiciones WHERE torneo_id = :t_id ORDER BY pts DESC, ds DESC, dg DESC, pg DESC", {"t_id": id_real})
                    if df_z_pos is not None and not df_z_pos.empty:
                        zonas_dict = {}
                        for _, row in df_z_pos.iterrows():
                            z = row['nombre_zona']
                            if z not in zonas_dict: zonas_dict[z] = []
                            zonas_dict[z].append(row)
                            
                        terceros = []
                        for z, equipos in zonas_dict.items():
                            z_letra = z.replace("Zona ", "").strip()
                            equipos_sorted = sorted(equipos, key=lambda x: (x['pts'], x['ds'], x['dg'], x['pg']), reverse=True)
                            if len(equipos_sorted) >= 1: clasificados_base.append(f"1{z_letra} - {equipos_sorted[0]['pareja']}")
                            if len(equipos_sorted) >= 2: clasificados_base.append(f"2{z_letra} - {equipos_sorted[1]['pareja']}")
                            if len(equipos_sorted) >= 3:
                                if len(equipos_sorted) == 4:
                                    clasificados_base.append(f"3{z_letra} - {equipos_sorted[2]['pareja']}")
                                else:
                                    terceros.append((f"3{z_letra} - {equipos_sorted[2]['pareja']}", equipos_sorted[2]))
                        
                        num_clasificados = len(clasificados_base)
                        target_size_calc = 4
                        if num_clasificados > 4: target_size_calc = 8
                        if num_clasificados > 8: target_size_calc = 16
                        if num_clasificados > 16: target_size_calc = 32
                        
                        slots_needed = target_size_calc - num_clasificados
                        terceros.sort(key=lambda x: (x[1]['pts'], x[1]['ds'], x[1]['dg'], x[1]['pg']), reverse=True)
                        while slots_needed > 0 and len(terceros) > 0:
                            clasificados_base.append(terceros.pop(0)[0])
                            slots_needed -= 1
                    else:
                        df_insc = cargar_datos("SELECT jugador1, jugador2 FROM inscripciones WHERE torneo_id = :tid", {"tid": id_real})
                        if df_insc is not None and not df_insc.empty:
                            clasificados_base = [f"{row['jugador1']} - {row['jugador2']}" for _, row in df_insc.iterrows()]
                        target_size_calc = 8
                        
                    opciones_size = [4, 8, 16, 32]
                    size_idx = opciones_size.index(target_size_calc) if target_size_calc in opciones_size else 1
                    target_size_sel = st.selectbox("Tamaño del Cuadro (Clasificados calculados: {})".format(len(clasificados_base)), opciones_size, index=size_idx)
                    
                    instancia = "Cuartos"
                    start_pos = 9
                    if target_size_sel == 16:
                        instancia = "Octavos"
                        start_pos = 1
                    elif target_size_sel == 4:
                        instancia = "Semis"
                        start_pos = 13
                    elif target_size_sel == 32:
                        instancia = "16avos"
                        start_pos = -15 
                        
                    st.markdown(f"#### Armado de {instancia}")
                    opciones_parejas = ["BYE", "Vacío"] + clasificados_base
                    
                    num_partidos = target_size_sel // 2
                    cruces_armados = []
                    
                    cols = st.columns(2)
                    for i in range(num_partidos):
                        with cols[i % 2]:
                            st.markdown(f"**Partido {i+1}**")
                            p1 = st.selectbox(f"Pareja 1 (P{i+1})", opciones_parejas, key=f"am_p1_{i}_{id_real}")
                            p2 = st.selectbox(f"Pareja 2 (P{i+1})", opciones_parejas, key=f"am_p2_{i}_{id_real}")
                            cruces_armados.append((p1, p2))
                            st.write("")
                            
                    if st.button("💾 Guardar Cuadro Manual", type="primary"):
                        df_check = cargar_datos("SELECT count(*) as c FROM partidos WHERE torneo_id = :t_id AND instancia IN ('Octavos', 'Cuartos', 'Semis', 'Final')", {"t_id": id_real})
                        if df_check is not None and not df_check.empty and df_check.iloc[0]['c'] > 0:
                            st.error("Ya existen partidos de playoff. Por favor limpia los partidos de zona/bracket antes de generar uno nuevo.")
                        else:
                            count = 0
                            for i, (p1, p2) in enumerate(cruces_armados):
                                bp = start_pos + i
                                estado = 'Próximo'
                                res = ''
                                ganador = None
                                
                                if p1 == "BYE" and p2 not in ["BYE", "Vacío"]:
                                    estado = 'Finalizado'
                                    ganador = p2
                                    res = 'BYE'
                                elif p2 == "BYE" and p1 not in ["BYE", "Vacío"]:
                                    estado = 'Finalizado'
                                    ganador = p1
                                    res = 'BYE'
                                elif p1 in ["BYE", "Vacío"] and p2 in ["BYE", "Vacío"]:
                                    estado = 'Finalizado'
                                    res = 'Vacío'
                                    ganador = 'Vacío'
                                
                                p1_db = "" if p1 == "Vacío" else p1
                                p2_db = "" if p2 == "Vacío" else p2
                                    
                                new_id = run_action('''
                                    INSERT INTO partidos (torneo_id, pareja1, pareja2, instancia, estado_partido, bracket_pos)
                                    VALUES (:tid, :p1, :p2, :inst, 'Próximo', :bp) RETURNING id
                                ''', {"tid": id_real, "p1": p1_db, "p2": p2_db, "inst": instancia, "bp": bp}, return_id=True)
                                
                                if ganador:
                                    actualizar_bracket(new_id, id_real, bp, res, ganador)
                                    run_action("UPDATE partidos SET estado_partido = 'Finalizado', resultado = 'Pasa Directo' WHERE id = :id",
                                               {"id": new_id})
                                count += 1
                            limpiar_cache()
                            st.success(f"Cuadro de {instancia} guardado exitosamente con {count} partidos.")
                            time.sleep(1.5)
                            st.rerun()

                # Botón con confirmación segura para lógicas Automáticas/Manual de Zonas
                if tipo_cierre in ["Cierre Automático", "Cierre Manual"]:
                    if 'confirm_playoff' not in st.session_state: st.session_state.confirm_playoff = False
    
                    if st.button("🏆 Finalizar Zonas y Armar Playoff"):
                        st.session_state.confirm_playoff = True
    
                    if st.session_state.confirm_playoff:
                        st.warning("⚠️ ¿Estás seguro? Esta acción generará los cruces eliminatorios.")
                        col_y, col_n = st.columns(2)
                        if col_y.button("✅ Sí, Generar"):
                            m_pos = manual_positions if tipo_cierre == "Cierre Manual" else None
                            ok, msg = cerrar_zonas_y_generar_playoffs(id_real, m_pos)
                            if ok:
                                st.success(msg)
                            else:
                                st.error(msg)
                            st.session_state.confirm_playoff = False
                            time.sleep(1.5)
                            st.rerun()
                        if col_n.button("❌ Cancelar"):
                            st.session_state.confirm_playoff = False
                            st.rerun()
                
                mostrar_cuadro_playoff(id_real)

            else:
                st.info("No hay torneos activos para configurar.")
            st.markdown("</div>", unsafe_allow_html=True)

        with tab_validaciones:
            st.subheader("📋 Inscripciones Pendientes de Validación")
            
            # Mensaje de éxito post-validación (Persistencia temporal)
            if 'val_success' in st.session_state:
                s_data = st.session_state['val_success']
                st.success(f"✅ ¡Pareja {s_data['pareja']} validada!")
                
                # Botón de WhatsApp
                wa_url = create_wa_link(s_data['tel'], s_data['msg'])
                st.markdown(f"""
                <a href="{wa_url}" target="_blank" style="text-decoration: none;">
                    <div style="background-color: #25D366; color: white; padding: 10px 20px; border-radius: 8px; display: inline-block; font-weight: bold; display: flex; align-items: center; gap: 10px; width: fit-content;">
                        <img src="https://upload.wikimedia.org/wikipedia/commons/6/6b/WhatsApp.svg" width="24" height="24">
                        Enviar Confirmación por WhatsApp
                    </div>
                </a>
                """, unsafe_allow_html=True)
                
                if st.button("Cerrar Aviso", key="close_val_msg"):
                    del st.session_state['val_success']
                    st.rerun()
                st.divider()

            df_pendientes = get_data("SELECT * FROM inscripciones WHERE estado_validacion = 'Pendiente' ORDER BY id ASC")
            
            if df_pendientes is None or df_pendientes.empty:
                st.info("✅ No hay inscripciones pendientes de validación.")
            else:
                for _, row in df_pendientes.iterrows():
                    with st.container():
                        c1, c2, c3, c4 = st.columns([3, 2, 1.5, 1.5])
                        disp_j1 = row['jugador1'] if row['jugador1'] else "Sin Nombre"
                        disp_j2 = row['jugador2'] if row['jugador2'] else "Sin Nombre"
                        c1.markdown(f"**{disp_j1} - {disp_j2}**")
                        c1.caption(f"Torneo ID: {row['torneo_id']} | Cat: {row['categoria']}")
                        c2.write(f"📞 {row['telefono1']}")
                        
                        if c3.button("✅ Validar Inscripción", key=f"btn_val_{row['id']}"):
                            run_action("UPDATE inscripciones SET estado_validacion = 'Validado' WHERE id = %(id)s", {"id": row['id']})
                            
                            # Obtener nombre del torneo para el mensaje
                            df_t = cargar_datos("SELECT nombre FROM torneos WHERE id = :tid", params={"tid": row['torneo_id']})
                            nombre_torneo = df_t.iloc[0]['nombre'] if (df_t is not None and not df_t.empty) else "el torneo"
                            
                            msg_wa = f"¡Hola! Soy Augusto de Rincón Padel. Tu inscripción para el torneo {nombre_torneo} ha sido VALIDADA. Pareja: {row['jugador1']} - {row['jugador2']}. ¡Te esperamos! Cualquier duda, escribinos a este número (3455454907)."
                            
                            st.session_state['val_success'] = {'pareja': f"{row['jugador1']} - {row['jugador2']}", 'tel': row['telefono1'], 'msg': msg_wa}
                            limpiar_cache()
                            st.rerun()
                        
                        if c4.button("❌ Rechazar", key=f"btn_rej_{row['id']}", type="secondary"):
                            run_action("DELETE FROM inscripciones WHERE id = %(id)s", {"id": row['id']})
                            st.warning(f"Inscripción de {row['jugador1']} rechazada.")
                            limpiar_cache()
                            st.rerun()

                        st.divider()

        with tab_transferencias:
            seccion_transferir_jugadores()

        with tab_admin_gral:
            st.subheader("Configuración de Puntaje")
            with st.expander("⚙️ Editar Puntos por Instancia"):
                c1, c2, c3, c4 = st.columns(4)
                pts_campeon = c1.number_input("Campeón", value=1000, step=100)
                pts_final = c2.number_input("Finalista", value=600, step=50)
                pts_semi = c3.number_input("Semifinal", value=360, step=40)
                pts_cuartos = c4.number_input("Cuartos", value=180, step=20)
                st.caption("Estos valores se usarán para el cálculo automático al cerrar torneos.")
            
            st.subheader("Gestión de Jugadores")
            with st.expander("⚙️ Recategorizar Jugador"):
                st.write("Selecciona un jugador para actualizar su nivel. El nivel actual pasará al historial.")
                
                # Obtener lista de jugadores para el dropdown
                df_j_admin = get_data("SELECT id, nombre, apellido, categoria_actual FROM jugadores ORDER BY apellido")
                if df_j_admin is not None and not df_j_admin.empty:
                    # Crear diccionario para mapear selección a ID
                    opciones = {f"{row['apellido']}, {row['nombre']} (Actual: {row['categoria_actual']})": row['id'] for _, row in df_j_admin.iterrows()}
                    
                    col_sel, col_cat = st.columns([2, 1])
                    sel_jugador = col_sel.selectbox("Buscar Jugador", options=list(opciones.keys()))
                    id_jugador = opciones[sel_jugador]
                    
                    nueva_cat = col_cat.selectbox("Nueva Categoría", ["Libre", "3ra", "4ta", "5ta", "6ta", "7ma", "8va"])
                    
                    if st.button("💾 Guardar Cambios"):
                        recategorizar_jugador(id_jugador, nueva_cat)
                        st.success(f"Categoría actualizada a {nueva_cat} correctamente.")
                        st.rerun()
                else:
                    st.info("No hay jugadores registrados para recategorizar.")
            
            st.markdown("---")
            st.subheader("🔄 Sincronización de Datos")
            st.warning(
                "**¡Atención!** Este proceso reemplazará completamente el contenido de la base de datos local "
                "(`torneos_padel.db`) con los datos actuales de la nube. "
                "Cualquier cambio local que no se haya subido a la nube se perderá."
            )
            if st.button("🔄 Sincronizar Nube -> Local", type="primary"):
                with st.spinner("Iniciando sincronización... Este proceso puede tardar unos momentos."):
                    success, message = sincronizar_datos_nube_a_local()
                if success:
                    st.success(f"✅ {message}")
                else:
                    st.error(f"❌ {message}")
                    
            st.markdown("---")
            st.write("📥 **Descargar Copia de Seguridad**")
            if os.path.exists('torneos_padel.db'):
                with open('torneos_padel.db', "rb") as f:
                    st.download_button(
                        label="💾 Descargar Base de Datos Local (.db)",
                        data=f,
                        file_name=f"torneos_padel_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.db",
                        mime="application/vnd.sqlite3"
                    )
            else:
                st.info("El archivo de base de datos local aún no existe. Ejecuta una sincronización primero.")

        with tab_admin_fotos:
            st.subheader("Subir Nueva Foto")
            st.warning('Para mantener la web rápida, el tamaño máximo por foto es de 2MB')
            uploaded_file = st.file_uploader("Seleccionar imagen", type=['jpg', 'png', 'jpeg'])
            
            if uploaded_file is not None:
                if uploaded_file.size > 2 * 1024 * 1024:
                    st.error("⚠️ El archivo supera los 2MB. Por favor, comprímelo antes de subirlo.")
                else:
                    if st.button("Subir Foto"):
                        # Optimización de imagen
                        image = Image.open(uploaded_file)
                        
                        # Convertir a RGB para asegurar compatibilidad JPEG
                        if image.mode in ("RGBA", "P"):
                            image = image.convert("RGB")
                            
                        # Redimensionar para web (Max 1024px)
                        image.thumbnail((1024, 1024))
                        
                        # Guardar en buffer con compresión
                        img_byte_arr = io.BytesIO()
                        image.save(img_byte_arr, format='JPEG', quality=85, optimize=True)
                        
                        guardar_foto(uploaded_file.name, img_byte_arr.getvalue())
                        st.success("Foto subida exitosamente.")
                        st.rerun()

        with tab_carga_puntos:
            st.subheader("📊 Carga de Puntos al Ranking")
            st.markdown("Asigna puntos a los jugadores según su desempeño en el torneo.")
            
            # 1. Seleccionar Torneo
            df_t_ranking = get_data("SELECT * FROM torneos WHERE es_puntuable = 1 ORDER BY id DESC")
            
            if df_t_ranking is not None and not df_t_ranking.empty:
                # Crear diccionario para selectbox: "Nombre (Categoria)" -> ID
                t_opts = {f"{row['nombre']} ({row['categoria']})": row['id'] for _, row in df_t_ranking.iterrows()}
                sel_t_name_r = st.selectbox("Seleccionar Torneo", list(t_opts.keys()), key="sel_t_ranking_pts")
                sel_t_id_r = t_opts[sel_t_name_r]
                
                # Obtener info del torneo
                row_torneo = df_t_ranking[df_t_ranking['id'] == sel_t_id_r].iloc[0]
                cat_torneo_r = row_torneo['categoria']
                
                es_puntuable_r = row_torneo['es_puntuable'] if 'es_puntuable' in row_torneo else 1
                
                if not es_puntuable_r:
                    st.error("🚫 Este torneo está configurado como NO PUNTUABLE. No se pueden cargar puntos.")
                else:
                    st.info(f"Categoría del Torneo: **{cat_torneo_r}** (Los puntos se sumarán a esta categoría)")
                    
                    # 2. Seleccionar Pareja
                    df_insc_r = get_data("SELECT * FROM inscripciones WHERE torneo_id = :torneo_id", params={"torneo_id": sel_t_id_r})
                    
                    if df_insc_r is not None and not df_insc_r.empty:
                        # Crear lista de parejas
                        parejas_map = {f"{row['jugador1']} - {row['jugador2']}": (row['jugador1'], row['jugador2']) for _, row in df_insc_r.iterrows()}
                        sel_pareja_r = st.selectbox("Seleccionar Pareja", list(parejas_map.keys()), key="sel_pareja_ranking_pts")
                        
                        # 3. Input de Puntos
                        puntos_r = st.number_input("Puntos a asignar (por jugador)", min_value=0, step=10, value=100, help="Ej: 1000 Campeón, 600 Finalista, etc.")
                        
                        if st.button("💾 Actualizar Ranking", key="btn_update_ranking"):
                            j1, j2 = parejas_map[sel_pareja_r]
                            # Actualizar J1 y J2 (Borrar previos para este torneo y reinsertar)
                            for jug in [j1, j2]:
                                run_action("DELETE FROM ranking_puntos WHERE torneo_id = %(torneo_id)s AND jugador = %(jugador)s", {"torneo_id": sel_t_id_r, "jugador": jug})
                                run_action("INSERT INTO ranking_puntos (torneo_id, jugador, categoria, puntos) VALUES (%(torneo_id)s, %(jugador)s, %(categoria)s, %(puntos)s)", {"torneo_id": sel_t_id_r, "jugador": jug, "categoria": cat_torneo_r, "puntos": puntos_r})
                            limpiar_cache()
                            st.success(f"✅ Se asignaron {puntos_r} puntos a {j1} y {j2} en la categoría {cat_torneo_r}.")
                    else:
                        st.warning("⚠️ No hay inscriptos en este torneo.")
            else:
                st.info("No hay torneos disponibles.")

        with tab_admin_socios:
            st.subheader("👥 Administración de Socios")
            
            # 1. Registro Manual
            with st.expander("➕ Registrar Nuevo Socio (Manual)", expanded=False):
                with st.form("form_admin_alta_socio"):
                    c1, c2 = st.columns(2)
                    a_nombre = c1.text_input("Nombre")
                    a_apellido = c2.text_input("Apellido")
                    a_dni = c1.text_input("DNI (Usuario)")
                    a_cel = c2.text_input("Celular")
                    a_cat = st.selectbox("Categoría", ["Libre", "3ra", "4ta", "5ta", "6ta", "7ma", "8va"])
                    a_loc = st.text_input("Localidad")
                    
                    if st.form_submit_button("💾 Guardar Socio"):
                        if a_dni and a_nombre and a_apellido:
                            # Password por defecto es el DNI
                            ok, msg = registrar_jugador_db(a_dni, a_nombre, a_apellido, a_cel, a_cat, a_loc, password=None)
                            if ok:
                                st.success(f"✅ {msg}")
                                st.rerun()
                            else:
                                st.error(f"❌ {msg}")
                        else:
                            st.warning("⚠️ Nombre, Apellido y DNI son obligatorios.")

            st.markdown("---")
            st.subheader("🗑️ Limpieza de Base de Datos")
            
            # Buscador para filtrar la lista
            search_socio = st.text_input("🔍 Buscar socio para eliminar (Nombre o DNI)", placeholder="Escribe aquí...")
            
            query_socios = "SELECT dni, nombre, apellido, categoria_actual, celular FROM jugadores ORDER BY apellido"
            df_socios = get_data(query_socios)
            
            if search_socio:
                df_socios = df_socios[df_socios.apply(lambda row: search_socio.lower() in str(row).lower(), axis=1)]
            
            # Renderizar lista con botones
            for idx, row in df_socios.iterrows():
                c_info, c_btn = st.columns([4, 1])
                with c_info:
                    st.markdown(f"**{row['apellido']}, {row['nombre']}** | 🏷️ {row['categoria_actual']} | 🆔 {row['dni']}")
                with c_btn:
                    if st.button("🗑️ Eliminar", key=f"del_{row['dni']}"):
                        eliminar_jugador(row['dni'])
                        st.warning(f"Socio {row['nombre']} {row['apellido']} eliminado.")
                        st.rerun()

        with tab_control_vivo:
            st.subheader("⚡ Control en Vivo (Gestión de Partidos)")
            
            # 1. Seleccionar Torneo y Partido
            df_t_live = get_data("SELECT * FROM torneos WHERE estado IN ('Abierto', 'En Juego')")
            if df_t_live is not None and not df_t_live.empty:
                t_opts_live = {f"{row['nombre']}": row['id'] for _, row in df_t_live.iterrows()}
                sel_t_live = st.selectbox("Seleccionar Torneo", list(t_opts_live.keys()), key="sel_t_live")
                id_t_live = t_opts_live[sel_t_live]
                
                # Obtener partidos pendientes o en juego
                df_p_live = get_data("SELECT * FROM partidos WHERE torneo_id = :torneo_id AND estado_partido != 'Finalizado' ORDER BY id ASC", params={"torneo_id": id_t_live})
                
                # Configuración del torneo para Tie-break
                t_conf = get_data("SELECT super_tiebreak, puntos_tiebreak FROM torneos WHERE id=:id", {"id": id_t_live}).iloc[0]
                is_stb = t_conf['super_tiebreak'] == 1
                pts_stb = t_conf['puntos_tiebreak']
                
                if df_p_live is not None and not df_p_live.empty:
                    # --- LISTADO DE PARTIDOS CON CONTROLES ---
                    for _, row in df_p_live.iterrows():
                        with st.expander(f"{row['instancia']}: {row['pareja1']} vs {row['pareja2']} ({row['estado_partido']})", expanded=(row['estado_partido'] == 'En Juego')):
                            c_ctrl, c_res = st.columns([1, 2])
                            
                            # Inicializar Estado Live si no existe
                            live_key = f"live_{row['id']}"
                            if live_key not in st.session_state:
                                # Intentar parsear resultado actual de la DB para inicializar games
                                curr_res = row['resultado'] if row['resultado'] else ""
                                parts = curr_res.split(' ')
                                g1, g2 = 0, 0
                                sets_previos = ""
                                if parts:
                                    last_set = parts[-1]
                                    if '-' in last_set:
                                        try:
                                            g1 = int(last_set.split('-')[0])
                                            g2 = int(last_set.split('-')[1])
                                            sets_previos = " ".join(parts[:-1])
                                        except: pass
                                st.session_state[live_key] = {'p1_pts': 0, 'p2_pts': 0, 'p1_games': g1, 'p2_games': g2, 'sets_str': sets_previos, 'torneo_id': id_t_live}
                            
                            with c_ctrl:
                                st.write("**Controles**")
                                if row['estado_partido'] == 'Próximo':
                                    if st.button("▶️ Iniciar Partido", key=f"start_{row['id']}"):
                                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        run_action("UPDATE partidos SET estado_partido = 'En Juego', hora_inicio_real = %(now)s WHERE id = %(id)s", {"now": now_str, "id": row['id']})
                                        # Activar en banner también
                                        run_action("DELETE FROM partido_en_vivo")
                                        run_action("INSERT INTO partido_en_vivo (torneo, pareja1, pareja2, marcador) VALUES (%(torneo)s, %(pareja1)s, %(pareja2)s, %(marcador)s)", 
                                                  {"torneo": sel_t_live, "pareja1": row['pareja1'], "pareja2": row['pareja2'], "marcador": row['resultado'] if row['resultado'] else "0-0"})
                                        st.rerun()
                                elif row['estado_partido'] == 'En Juego':
                                    if st.button("⏸️ Pausar/Detener", key=f"pause_{row['id']}"):
                                        detener_partido(row['id'])
                                        st.rerun()
                                elif row['estado_partido'] == 'Detenido':
                                    if st.button("▶️ Reanudar", key=f"resume_{row['id']}"):
                                        actualizar_estado_partido(row['id'], 'En Juego')
                                        st.rerun()
                            
                            with c_res:
                                if row['estado_partido'] == 'En Juego':
                                    # --- WIDGET LIVE SCOREBOARD ---
                                    state = st.session_state[live_key]
                                    
                                    # Contenedor Visual del Marcador
                                    st.markdown(f"""
                                    <div style="background-color:#000; border:2px solid #39FF14; border-radius:10px; padding:15px; margin-bottom:15px;">
                                        <div style="display:flex; justify-content:space-between; text-align:center; color:white;">
                                            <div style="flex:1;">
                                                <div style="font-size:0.9rem; font-weight:bold; color:#aaa;">{row['pareja1']}</div>
                                                <div style="font-size:2.5rem; font-weight:900; line-height:1;">{state['p1_games']}</div>
                                                <div style="font-size:1.8rem; color:#39FF14; font-family:'Courier New';">{obtener_puntos_display(state['p1_pts'])}</div>
                                            </div>
                                            <div style="flex:0.2; display:flex; align-items:center; justify-content:center; font-size:1.5rem; color:#444;">-</div>
                                            <div style="flex:1;">
                                                <div style="font-size:0.9rem; font-weight:bold; color:#aaa;">{row['pareja2']}</div>
                                                <div style="font-size:2.5rem; font-weight:900; line-height:1;">{state['p2_games']}</div>
                                                <div style="font-size:1.8rem; color:#39FF14; font-family:'Courier New';">{obtener_puntos_display(state['p2_pts'])}</div>
                                            </div>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    # Botones de Acción
                                    cb1, cb2 = st.columns(2)
                                    if cb1.button(f"🎾 Punto {row['pareja1'].split(' ')[0]}", key=f"btn_p1_{row['id']}", use_container_width=True):
                                        sumar_punto(row['id'], 1, state)
                                        st.rerun()
                                        
                                    if cb2.button(f"🎾 Punto {row['pareja2'].split(' ')[0]}", key=f"btn_p2_{row['id']}", use_container_width=True):
                                        sumar_punto(row['id'], 2, state)
                                        st.rerun()
                                        
                                    st.write("")
                                    if st.button("💾 Finalizar Set y Guardar", key=f"end_set_{row['id']}", type="primary", use_container_width=True):
                                        # Guardar set en columna correspondiente
                                        # Determinar qué set es en base a sets_previos
                                        sets_done = len(state['sets_str'].split(' ')) if state['sets_str'] else 0
                                        next_set_col = f"set{sets_done + 1}"
                                        games_final = f"{state['p1_games']}-{state['p2_games']}"
                                        
                                        if sets_done < 3:
                                            run_action(f"UPDATE partidos SET {next_set_col} = :val WHERE id = :id", {"val": games_final, "id": row['id']})
                                        
                                        # Actualizar sets previos en estado y resetear games
                                        new_sets_str = f"{state['sets_str']} {games_final}".strip()
                                        st.session_state[live_key] = {'p1_pts': 0, 'p2_pts': 0, 'p1_games': 0, 'p2_games': 0, 'sets_str': new_sets_str, 'torneo_id': id_t_live}
                                        
                                        # Update DB
                                        run_action("UPDATE partidos SET resultado = %(res)s WHERE id = %(id)s", {"res": new_sets_str, "id": row['id']})
                                        st.toast("✅ Set guardado exitosamente.", icon="💾")
                                        st.rerun()
                                        
                                    with st.expander("🛠️ Corrección Manual"):
                                        st.caption("Usa esto si hubo un error en el tanteador.")
                                        new_res_man = st.text_input("Resultado Completo", value=row['resultado'] if row['resultado'] else "", key=f"man_res_{row['id']}")
                                        if st.button("Forzar Actualización", key=f"force_{row['id']}"):
                                            actualizar_marcador(row['id'], new_res_man)
                                            st.session_state.pop(live_key, None) # Resetear estado live para recargar del manual
                                            st.rerun()

                                else:
                                    # MODO MANUAL (Próximo / Detenido)
                                    st.write("**Cargar Resultados (Manual)**")
                                    with st.form(key=f"res_form_{row['id']}"):
                                        # Parsear resultado actual si existe
                                        curr_res = row['resultado'] if row['resultado'] else ""
                                        sets_vals = curr_res.split(' ') if curr_res else []
                                        val_s1 = sets_vals[0] if len(sets_vals) > 0 else ""
                                        val_s2 = sets_vals[1] if len(sets_vals) > 1 else ""
                                        val_s3 = sets_vals[2] if len(sets_vals) > 2 else ""
                                        
                                        c_s1, c_s2, c_s3 = st.columns(3)
                                        in_s1 = c_s1.text_input("Set 1", value=val_s1, key=f"s1_{row['id']}")
                                        in_s2 = c_s2.text_input("Set 2", value=val_s2, key=f"s2_{row['id']}")
                                        if is_stb:
                                            in_s3 = c_s3.text_input(f"S. Tie-break ({pts_stb})", value=val_s3, key=f"s3_{row['id']}", placeholder="Ej: 10-8")
                                        else:
                                            in_s3 = c_s3.text_input("Set 3", value=val_s3, key=f"s3_{row['id']}")
                                        
                                        new_res = f"{in_s1} {in_s2} {in_s3}".strip()
                                        
                                        if st.form_submit_button("💾 Guardar Parcial"):
                                            actualizar_marcador(row['id'], new_res)
                                            st.success("Guardado")
                                            st.rerun()
                                
                                # Botón explícito de Finalizar fuera del form para evitar submits accidentales
                                if row['estado_partido'] in ['En Juego', 'Detenido', 'Próximo']:
                                    st.markdown("---")
                                    c_win, c_btn_fin = st.columns([2, 1])
                                    with c_win:
                                        winner_sel = st.selectbox("Ganador", [row['pareja1'], row['pareja2']], key=f"win_sel_{row['id']}")
                                    with c_btn_fin:
                                        st.write("")
                                        st.write("")
                                        if st.button("🏁 Finalizar y Avanzar", key=f"confirm_fin_{row['id']}"):
                                            if not row['resultado']:
                                                st.error("Carga el resultado primero.")
                                            else:
                                                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                                run_action("UPDATE partidos SET estado_partido = 'Finalizado', ganador = %(ganador)s, hora_fin = %(now)s WHERE id = %(id)s", 
                                                          {"ganador": winner_sel, "now": now_str, "id": row['id']})
                                                
                                                # Limpiar banner
                                                run_action("DELETE FROM partido_en_vivo")
                                                
                                                # Actualizar Tablas/Bracket
                                                actualizar_tabla_posiciones(id_t_live)
                                                if row['bracket_pos']:
                                                    actualizar_bracket(row['id'], id_t_live, row['bracket_pos'], row['resultado'], winner_sel)
                                                
                                                st.success("Partido finalizado y procesado.")
                                                st.rerun()
                            
                            # --- SECCIÓN WHATSAPP ---
                            st.markdown("---")
                            st.write("📢 **Avisar a Jugadores (WhatsApp)**")
                            
                            # Buscar datos de contacto
                            row_p1 = get_inscripcion_by_pareja(row['pareja1'])
                            row_p2 = get_inscripcion_by_pareja(row['pareja2'])
                            
                            msg_wa = "¡Hola! Te hablamos de Rincón Padel. Tu partido está próximo a comenzar, por favor acercate al complejo en los próximos 15 minutos. Admin: 3455454907"
                            
                            col_wa1, col_wa2 = st.columns(2)
                            
                            with col_wa1:
                                st.caption(f"Pareja 1: {row['pareja1']}")
                                if row_p1 is not None:
                                    if row_p1['telefono1']:
                                        url = create_wa_link(row_p1['telefono1'], msg_wa)
                                        st.markdown(f"📲 [Avisar a {row_p1['jugador1']}]({url})")
                                    if row_p1['telefono2']:
                                        url = create_wa_link(row_p1['telefono2'], msg_wa)
                                        st.markdown(f"📲 [Avisar a {row_p1['jugador2']}]({url})")
                                else:
                                    st.caption("Sin datos de contacto.")
                                    url_gen = create_wa_link("", msg_wa)
                                    st.markdown(f"📲 Chat Genérico")

                            with col_wa2:
                                st.caption(f"Pareja 2: {row['pareja2']}")
                                if row_p2 is not None:
                                    if row_p2['telefono1']:
                                        url = create_wa_link(row_p2['telefono1'], msg_wa)
                                        st.markdown(f"📲 [Avisar a {row_p2['jugador1']}]({url})")
                                    if row_p2['telefono2']:
                                        url = create_wa_link(row_p2['telefono2'], msg_wa)
                                        st.markdown(f"📲 [Avisar a {row_p2['jugador2']}]({url})")
                                else:
                                    st.caption("Sin datos de contacto.")
                                    url_gen = create_wa_link("", msg_wa)
                                    st.markdown(f"📲 Chat Genérico")

                else:
                    st.info("No hay partidos pendientes en este torneo.")
            else:
                st.warning("No hay torneos activos.")

        debug_base_datos()