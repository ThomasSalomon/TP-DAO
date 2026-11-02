# Cierre de F-07 (02/11/2026)

Estado de cada punto del checklist L.2 y de cada criterio de la Definition of Done M de `PLANIFICACION_TP_POO.md`, con la evidencia que lo respalda. Al final, la matriz de las pruebas T-01 a T-31 del catálogo J.2 hacia las pruebas pytest reales.

Este documento sólo registra lo que ya existe: no agrega funcionalidad ni pruebas. Las decisiones citadas son del grupo (`DECISIONES_F00.md`) y no tienen aval docente salvo que se indique. Lo que depende de la cátedra queda como **Pendiente docente** y no se da por cumplido.

## 1. Evidencia de ejecución

- Suite completa: `.\.venv\Scripts\python.exe -m pytest -q` dio **835 aprobados** en 48 min 23 s el 02/11/2026, con Python 3.11.2, en este equipo (327 funciones `test_` en 25 archivos; el resto de los casos sale de la parametrización). En el equipo de F-07.2 la misma suite tarda entre 4 y 5 minutos (`LEVANTAR_PROYECTO.md`).
- Recorrido de `DEMOSTRACION.md` en el navegador, con el build servido por Flask sobre una base nueva y reinicio sobre la misma base: los valores coincidieron con el dataset J.3 (README, sección «F-07.3: modelo y demostración»).
- Los comandos de instalación y ejecución se comprobaron en F-07.2 (README, «F-07.2: ejecución y restricciones técnicas»).

## 2. Checklist L.2

Estados: **Cumplido** (hay evidencia en el repositorio), **Cumplido por el equipo** (la decisión la tomó el grupo y hay una consulta docente abierta que podría cambiarla), **Parcial** y **Pendiente docente**.

### 2.1 Alcance y acuerdos

| Punto | Estado | Evidencia |
| --- | --- | --- |
| Resolver/adoptar las políticas de K necesarias para cada fase y registrar su fuente. | Cumplido por el equipo | DN-01 a DN-11 en `DECISIONES_F00.md`, secciones C y L a Q, cada una con fecha y fase. Consultas docentes abiertas: G-01 a G-06 y el formato del comprobante (sección 5). |
| Registrar React + Vite y API Flask acordadas para planificación. | Cumplido | Ya marcado en la planificación; DN-10 y E.1 de `DECISIONES_F00.md`. |
| Confirmar modalidad operativa DN-11 y formato de entrega. | Parcial | Modalidad aprobada: una instalación local, un operador y la base en `TP_DAO_DB` (`DECISIONES_F00.md` L.3). Fecha, integrantes y formato de entrega: **Pendiente docente** (G-06). |
| Conservar los siete procesos E2 y cinco validaciones E4 en aceptación. | Cumplido | `tests/test_integracion.py` (cuatro escenarios de J.4) y la tabla de correspondencia de `DEMOSTRACION.md`, sección 9. |
| Acordar integración mínima de compras y significado del resultado económico. | Cumplido por el equipo | Compra manual con ingreso total al CD y último costo como referencia (L.1); margen estimado con costos históricos (L.2 y P.3). G-01 sigue abierta. |
| Seleccionar cuatro reportes distintos y justificar dos patrones. | Cumplido | R-01 a R-04 en `DECISIONES_F00.md` P; State y Strategy justificados en `MODELO_POO.md`, sección 7, incluidos los patrones que no se aplicaron. |

### 2.2 Funcionalidad e integración

| Punto | Estado | Evidencia (matriz T de la sección 4) |
| --- | --- | --- |
| Maestros y duplicados controlados; precios/mínimos válidos. | Cumplido | T-01, T-02, T-03 |
| Compra ingresada una sola vez y persistente en CD. | Cumplido | T-04, T-05 |
| Necesidades consolidadas conservando origen, destino y cantidades. | Cumplido por el equipo | T-06. Una orden por destino (DN-04, M.3); G-02 pregunta si se exige una orden multilocal. |
| Bultos con contenido, remito y precinto; reservas coherentes. | Cumplido | T-07, T-08 |
| Despacho/recepción registrados sin duplicar unidades. | Cumplido | T-09, T-10, T-25 |
| Remito y bulto verificados antes de disponibilidad. | Cumplido | T-11. Un remito por bulto (DN-01, M.1); G-03 pregunta si alcanza. |
| Precinto roto rechaza y bloquea venta. | Cumplido | T-12 |
| Historia inmutable consultable; estados sin saltos inválidos. | Cumplido | T-13, T-27 |
| Venta multilinea, cobro, caja y comprobante coherentes. | Cumplido | T-14 a T-17. El formato del comprobante es una consulta docente abierta. |
| Devolución válida con stock/caja y límites acumulados acordados. | Cumplido | T-18 a T-20 |
| Cuatro reportes con filtros, fórmulas, vacío y resultados reconciliables. | Cumplido | T-21 a T-24; `test_integracion.py::test_feliz_reportes_dan_los_resultados_esperados_de_j3` |

### 2.3 POO y restricciones técnicas

| Punto | Estado | Evidencia |
| --- | --- | --- |
| Estado protegido; colecciones propias gestionadas por su dueño. | Cumplido | T-26; `MODELO_POO.md`, sección 4. |
| Composición/asociación/cardinalidad justificadas; no borrar documentos auditados. | Cumplido por el equipo | `MODELO_POO.md`, sección 5; `test_modelo.py::test_cada_parte_compuesta_la_crea_solo_su_contenedor`; disparadores que impiden modificar o borrar eventos y caja (T-30). Baja lógica en lugar de borrado físico (DN-08); G-04 pregunta si se exige DELETE. |
| State delega de verdad; cada estado cumple el contrato. | Cumplido | T-27 |
| Strategy intercambia agrupaciones sin selección de tipos en el contexto. | Cumplido | T-28 |
| Clases abstractas e inicialización correctas; sin herencia artificial. | Cumplido | `test_modelo.py::test_las_unicas_jerarquias_son_los_contratos_abstractos_y_las_excepciones`, `test_los_contratos_abstractos_declaran_metodos_abstractos`; `MODELO_POO.md`, sección 6. |
| Backend y cualquier lógica servidor sólo Python; sin SSR/BFF ajeno. | Cumplido | T-29 |
| SQLite directo, parámetros, transacciones y recursos cerrados. | Cumplido, con una observación | T-30. `BaseDatos` cierra la conexión en `finally` (revisado leyendo `base_datos.py`); una conexión que no se puede abrir no tiene prueba propia. |
| Versiones/dependencias React/Vite/Flask verificadas y restricciones académicas concretas atendidas, sin permiso genérico inventado. | Cumplido | README, «Versiones utilizadas»; `test_restricciones.py::test_unica_dependencia_de_ejecucion_es_flask_y_pytest_solo_para_pruebas`. G-05 (instrucciones de interfaz no publicadas) sigue abierta. |

### 2.4 Pruebas, documentación y entrega

| Punto | Estado | Evidencia |
| --- | --- | --- |
| Ejecutar pruebas por fase, con comandos/resultados reales. | Cumplido | README, «Pruebas y resultados»: comando, cantidad de casos y fecha de cada fase. |
| Cubrir normal/límite/error, repetición, reinicio y rollback. | Cumplido | Pruebas de última unidad, exceso, claves repetidas, `reiniciar_*` y `fallo_al_guardar_*` de cada módulo (sección 4). |
| Completar T-01 a T-31 y escenarios integrales acordados. | Cumplido, con una observación | Sección 4; la única parte sin prueba propia es la conexión que no se puede abrir (T-30). |
| Usar base aislada; evitar datos reales y efectos externos en tests. | Cumplido | `tests/conftest.py` hace que cada `create_app()` sin ruta use una base temporal nueva; las demás pruebas con base usan `tmp_path`. `test_persistencia_catalogo.py::test_create_app_sin_ruta_no_usa_la_base_real`. |
| Verificar cuatro resultados con dataset de control manual. | Cumplido | `test_integracion.py::test_feliz_reportes_dan_los_resultados_esperados_de_j3` y el recorrido de `DEMOSTRACION.md`, sección 7. |
| Actualizar modelo/diagramas y decisiones contra implementación final. | Cumplido | `MODELO_POO.md` (diagrama de clases y diferencias con C.4), `DER.md` alineado con `base_datos.py`, `DECISIONES_F00.md` Q.3. |
| Documentar versión Python, instalación/ejecución y dependencia de tests verificadas. | Cumplido | README, «Versiones utilizadas» y «Preparación local en Windows / PowerShell»; `LEVANTAR_PROYECTO.md`. |
| Preparar demostración del rechazo, doble verificación, devolución y patrones. | Cumplido | `DEMOSTRACION.md`, secciones 4 a 7. |
| Inspeccionar rúbrica/instrucciones de entrega cuando estén disponibles. | Pendiente docente | G-06: la rúbrica no está disponible. |
| Revisar diff y cumplimiento integral, sin cambios ajenos. | Cumplido | Este cierre: sólo documentación, sin cambios en código ni pruebas. |

## 3. Definition of Done M

| Criterio | Estado | Evidencia |
| --- | --- | --- |
| 1. Siete procesos y cinco validaciones con casos normales, límites y errores, trazados a RF/RB. | Cumplido | Sección 4 (T-01 a T-20, cada una con sus RF/RB en J.2) y `test_integracion.py`. |
| 2. Integración de compras, inventario y resultado económico con política acordada y límites explícitos. | Cumplido por el equipo | DN-03 y DN-09 (L.1, L.2), reportes R-02 y R-04 (P.3, P.5); límites en el README: sin pagos a proveedores, recepciones parciales ni costo promedio. G-01 abierta. |
| 3. Stock destino no vendible antes de remito y contenedor Verificados; el rechazo conserva historia y bloquea venta. | Cumplido | T-11, T-12; `test_integracion.py::test_bloqueo_stock_no_vendible_hasta_la_doble_verificacion`, `test_rechazo_precinto_roto_no_habilita_venta_ni_caja_y_conserva_historia`. |
| 4. Modelo POO que protege invariantes, con responsabilidades y relaciones coherentes y ciclo del bulto explicable. | Cumplido | T-26; `MODELO_POO.md`. Las observaciones de su sección 10 no rompen invariantes y quedan registradas sin cambiar el código. |
| 5. Dos patrones implementados y probados, con delegación y polimorfismo demostrados. | Cumplido | T-27 (State), T-28 (Strategy). |
| 6. Cuatro reportes no triviales correctos para datos conocidos, vacíos y filtros, sin duplicar importes. | Cumplido por el equipo | T-21 a T-24. El enunciado no define «no trivial»; el criterio usado (A §16.4: varias entidades, agrupación o cálculo y filtros) está a confirmar con G-06. |
| 7. Ventas/devoluciones con referencia y valores históricos; stock, cobros, reintegros y caja correspondientes, sin cambios parciales. | Cumplido | T-15, T-17, T-20; `test_integracion.py::test_transaccional_fallos_de_guardado_no_dejan_cambios_parciales`. |
| 8. Lógica backend exclusivamente en Python; SQL sólo para acceso a datos. | Cumplido | T-29; `test_restricciones.py::test_sql_recibe_valores_como_parametros_y_solo_interpola_identificadores_fijos`. Los disparadores SQL sólo protegen integridad (historia inmutable, referencias); las reglas se validan en Python. |
| 9. Tecnologías y técnicas ajustadas a instrucciones académicas; decisiones no confirmadas acordadas antes de darse por satisfechas. | Parcial | Las decisiones están acordadas por el grupo y registradas (`DECISIONES_F00.md`). La confirmación docente de G-01 a G-05 y del formato del comprobante sigue **Pendiente docente**. |
| 10. Persistencia, unicidad, referencias, historia, reinicio y rollback verificados en datos aislados. | Cumplido, con una observación | T-05, T-13, T-30. Sin prueba propia de una conexión que no se puede abrir. No se afirma seguridad total ni exactitud contable fuera de DN-09. |
| 11. Suite y escenarios integrales aprobados, con comandos, resultados y comprobaciones omitidas registrados. | Cumplido | Sección 1. Omitido: automatización de la interfaz (los recorridos se hicieron a mano en el navegador), porcentaje de cobertura y la apertura fallida de la conexión. Ninguna omisión oculta un fallo conocido. |
| 12. Documentación para ejecutar y demostrar el sistema, coherente con código y comandos reales. | Cumplido | README, `LEVANTAR_PROYECTO.md`, `DEMOSTRACION.md`, `MODELO_POO.md`, `DER.md`, comprobados en F-07.2 y F-07.3. |
| 13. Artefactos y modalidad de entrega según las indicaciones docentes. | Pendiente docente | G-06. No se arma informe, presentación ni paquete de entrega hasta conocer la rúbrica (`DECISIONES_F00.md` Q.3). |

## 4. Matriz T-01 a T-31

Los archivos son de `tests/`. Se nombran las pruebas sin el prefijo `test_`; donde hay muchas, se citan las principales.

| ID | Estado | Pruebas |
| --- | --- | --- |
| T-01 | Cumplido | `test_ubicaciones.py` (todas); `test_api_ubicaciones.py` (todas); `test_bajas.py::cd_no_se_desactiva_y_no_se_libera_su_cardinalidad`; `test_api_bajas.py::cd_no_se_desactiva_y_no_permite_otro_cd`; `test_compras.py::las_compras_ingresan_al_cd_y_no_a_un_local` |
| T-02 | Cumplido | `test_catalogo.py::codigos_duplicados_se_rechazan_tras_normalizar`, `ceros_iniciales_unicidad_por_tipo_y_nombres_repetidos`; `test_proveedores.py::alta_consulta_normalizacion_ceros_y_nombre_no_unico`, `duplicado_normalizado_no_agrega_registros`; `test_api_catalogo.py::duplicados_en_alta_y_edicion_devuelven_409_sin_cambios`; `test_api_proveedores.py::conflictos_actuales_e_historicos_y_codigo_actual_con_otro_uso_de_mayusculas`; `test_bajas.py::codigos_original_y_reemplazado_no_se_reutilizan_ni_tras_baja` |
| T-03 | Cumplido | `test_catalogo.py::precios_se_convierten_exactamente_sin_float`, `importes_invalidos_no_crean_producto`, `precio_rechaza_tipos_ambiguos_o_inexactos`; `test_minimos.py::ausencia_cero_y_reemplazo_repetido_sin_duplicados`, `valores_invalidos_sin_alta_ni_modificacion_parcial`; `test_api_minimos.py::datos_invalidos_no_crean_ni_modifican_minimos`; `test_ventas.py::precio_y_costo_historicos_no_cambian_con_el_catalogo_ni_con_compras` |
| T-04 | Cumplido | `test_compras.py::registrar_compra_crea_detalles_e_ingresa_todo_al_cd`, `una_linea_invalida_impide_registrar_toda_la_compra`, `cantidad_debe_ser_entero_positivo`, `costo_unitario_es_importe_positivo_exacto`, `proveedor_o_producto_inactivo_no_admite_nuevas_compras`; `test_api_compras.py::contenido_invalido_devuelve_400_sin_efectos_parciales`. Con DN-03 la compra es el control de ingreso al CD (L.1). |
| T-05 | Cumplido | `test_api_compras.py::reiniciar_conserva_compras_saldos_movimientos_y_continua_ids`, `fallo_al_guardar_devuelve_500_sin_compra_ni_stock_en_memoria_o_base`, `compras_concurrentes_no_pierden_saldo_ni_repiten_ids`; `test_persistencia_catalogo.py::transaccion_revierte_todo_ante_una_excepcion` |
| T-06 | Cumplido | `test_logistica.py::consolidar_suma_por_producto_y_conserva_las_necesidades`, `consolidar_rechaza_mezclar_locales_repetir_o_reutilizar_necesidades`; `test_integracion.py::feliz_orden_consolidada_conserva_las_necesidades` |
| T-07 | Cumplido | `test_logistica.py::preparar_valida_contenido_y_productos_de_la_orden`, `no_se_reserva_mas_que_lo_disponible_en_el_cd`, `anular_un_preparado_libera_la_reserva_y_devuelve_el_pendiente`; `test_api_logistica.py::preparaciones_concurrentes_no_superan_lo_pendiente` |
| T-08 | Cumplido | `test_logistica.py::precinto_es_unico_sin_distinguir_mayusculas_y_no_consume_remito`; `test_api_logistica.py::precinto_repetido_sin_distinguir_mayusculas_es_409`. El contenido se fija al preparar el bulto y no tiene métodos para cambiarlo. |
| T-09 | Cumplido | `test_logistica.py::circuito_completo_habilita_stock_solo_con_bulto_y_remito_verificados`, `cada_estado_rechaza_las_operaciones_que_no_admite_sin_efectos`; `test_api_logistica.py::transiciones_invalidas_devuelven_409_sin_cambios` |
| T-10 | Cumplido | `test_logistica.py::recibir_en_otro_local_no_cambia_nada`; `test_api_logistica.py::recibir_en_otro_local_o_inexistente_no_cambia_nada` |
| T-11 | Cumplido | `test_logistica.py::circuito_completo_habilita_stock_solo_con_bulto_y_remito_verificados`, `remito_no_se_verifica_antes_que_su_bulto_ni_dos_veces`, `entregas_parciales_dejan_pendiente_hasta_completar_la_orden`; `test_ventas.py::solo_se_vende_lo_que_llego_con_bulto_y_remito_verificados`; `test_integracion.py::bloqueo_stock_no_vendible_hasta_la_doble_verificacion` |
| T-12 | Cumplido | `test_logistica.py::precinto_roto_o_distinto_rechaza_en_la_misma_recepcion`; `test_api_logistica.py::rechazo_por_precinto_persiste_y_bloquea_verificaciones`; `test_integracion.py::rechazo_precinto_roto_no_habilita_venta_ni_caja_y_conserva_historia` |
| T-13 | Cumplido | `test_logistica.py::cada_estado_rechaza_las_operaciones_que_no_admite_sin_efectos`, `historial_no_expone_modificaciones`; `test_api_logistica.py::reiniciar_en_cada_etapa_conserva_todo_y_permite_continuar`, `esquema_protege_historial_estados_y_referencias` |
| T-14 | Cumplido | `test_ventas.py::venta_con_varias_lineas_y_cobros_divididos`, `se_puede_vender_la_ultima_unidad`, `stock_pendiente_rechazado_o_en_transito_nunca_se_vende`; `test_api_ventas.py::stock_pendiente_de_verificar_no_se_vende` |
| T-15 | Cumplido | `test_ventas.py::una_linea_sin_stock_impide_toda_la_venta`; `test_api_ventas.py::una_linea_sin_stock_impide_toda_la_venta`, `fallo_al_guardar_no_deja_venta_stock_ni_caja`; `test_integracion.py::transaccional_fallos_de_guardado_no_dejan_cambios_parciales` |
| T-16 | Cumplido | `test_ventas.py::los_cobros_deben_cubrir_exactamente_el_total`, `importe_y_medio_de_tipo_invalido`, `medios_de_pago_fijos`; `test_api_ventas.py::venta_con_cobros_divididos_descuenta_stock_y_registra_caja` |
| T-17 | Cumplido | `test_ventas.py::comprobante_y_venta_son_de_solo_lectura`, `misma_clave_de_operacion_devuelve_la_venta_sin_repetir_efectos`; `test_api_ventas.py::clave_repetida_devuelve_la_venta_existente_sin_efectos`; `test_integracion.py::feliz_comprobantes_con_precio_historico_y_reconsulta_sin_efectos` |
| T-18 | Cumplido | `test_devoluciones.py::solo_se_devuelven_lineas_de_la_venta_indicada`, `lineas_invalidas_no_registran_la_devolucion`, `motivo_obligatorio_y_acotado`, `no_puede_ser_anterior_a_la_venta`; `test_api_devoluciones.py::referencias_inexistentes_devuelven_404_con_el_campo`, `reglas_del_dominio_se_informan_sin_efectos` |
| T-19 | Cumplido | `test_devoluciones.py::devoluciones_parciales_sucesivas_hasta_el_limite`, `un_exceso_acumulado_en_una_linea_impide_toda_la_devolucion`, `misma_clave_devuelve_la_devolucion_sin_repetir_efectos`; `test_api_devoluciones.py::devoluciones_concurrentes_no_superan_lo_vendido_ni_duplican_claves` |
| T-20 | Cumplido | `test_devoluciones.py::lo_no_apto_queda_bloqueado_y_no_se_vende`, `lo_apto_vuelve_a_venderse`, `reintegra_al_precio_historico_de_la_venta`, `cada_medio_reintegra_hasta_lo_cobrado_con_el`; `test_api_devoluciones.py::fallo_al_guardar_no_deja_devolucion_stock_ni_caja`. La aptitud por línea es el control del reingreso (O.2). |
| T-21 | Cumplido | `test_reportes.py::r01_por_medio_con_cobros_divididos_y_devolucion_del_periodo`, `r01_filtro_de_local_y_devolucion_en_otro_periodo`, `r01_periodo_sin_operaciones`, `periodo_incluye_el_inicio_y_excluye_el_fin`; `test_api_reportes.py::r01_*` |
| T-22 | Cumplido | `test_reportes.py::r02_ranking_y_margen_con_costos_historicos`, `r02_devolucion_en_otro_periodo_revierte_su_costo_original`, `r02_empate_por_identificador_de_producto`, `r02_costo_faltante_no_se_toma_como_cero`, `r02_importe_neto_concilia_con_la_venta_neta_de_r01`; `test_api_reportes.py::r02_*` |
| T-23 | Cumplido | `test_reportes.py::r03_minimo_exacto_deficit_y_producto_sin_existencia`, `r03_separa_disponible_de_bloqueado_y_rechazado`, `r03_filtros_de_categoria_y_productos_en_minimo`; `test_api_reportes.py::r03_*` |
| T-24 | Cumplido | `test_reportes.py::r04_un_bulto_con_varias_lineas_y_eventos_cuenta_una_vez`, `r04_una_compra_posterior_no_cambia_el_valor_bloqueado`, `r04_periodo_por_fecha_del_rechazo_y_vacio`, `r04_filtro_de_producto_cuenta_solo_sus_lineas`; `test_api_reportes.py::r04_*` |
| T-25 | Cumplido | `test_logistica.py::las_unidades_se_conservan_en_todo_el_circuito`; `test_devoluciones.py::las_unidades_del_local_se_conservan`; `test_integracion.py::feliz_stock_y_caja_del_dataset` |
| T-26 | Cumplido | `test_modelo.py` (todas); `test_catalogo.py::modificacion_directa_no_elude_unicidad_ni_encapsulamiento`; `test_proveedores.py::propiedades_sin_escritura_y_listado_sin_mutacion_de_la_coleccion`; `test_compras.py::compra_es_inmutable_y_no_expone_detalles_modificables`; `test_devoluciones.py::devolucion_de_solo_lectura`; `MODELO_POO.md` |
| T-27 | Cumplido | `test_logistica.py::cada_estado_rechaza_las_operaciones_que_no_admite_sin_efectos`, `estado_bulto_es_un_contrato_abstracto`; `test_modelo.py::el_bulto_delega_cada_operacion_en_su_estado_actual`, `solo_el_contexto_cambia_el_estado_del_bulto`, `los_contextos_no_eligen_comportamiento_por_clase_concreta` |
| T-28 | Cumplido | `test_reportes.py::r01_mismos_datos_con_estrategias_intercambiadas`, `r01_una_estrategia_nueva_no_cambia_el_contexto`, `estrategias_disponibles_y_contrato_abstracto`, `los_reportes_no_modifican_operaciones`; `test_api_reportes.py::r01_agrupa_por_dia_por_defecto` |
| T-29 | Cumplido | `test_restricciones.py` (las cinco primeras); `test_api.py::python_sirve_build_y_api_desde_el_mismo_origen`; recorrido con Vite apagado de F-07.2 |
| T-30 | Cumplido, con una observación | `test_restricciones.py::sql_recibe_valores_como_parametros_y_solo_interpola_identificadores_fijos`; `test_persistencia_catalogo.py::esquema_rechaza_datos_que_violan_restricciones`, `inicializar_dos_veces_conserva_los_datos`, `fallo_al_guardar_devuelve_500_y_no_deja_cambios_en_memoria_ni_en_base`; `test_api_logistica.py::esquema_protege_historial_estados_y_referencias` (UPDATE y DELETE sobre `eventos_bulto` rechazados); `test_api_ventas.py::esquema_protege_ventas_cobros_y_caja`; `test_api_reportes.py::reinicio_reproduce_los_mismos_reportes`. Los fallos se simulan con `sqlite3.OperationalError` durante la operación; la apertura fallida de la conexión no tiene prueba propia. |
| T-31 | Cumplido | `test_integracion.py` (las nueve: feliz, bloqueo, rechazo y transaccional) |

## 5. Pendientes que dependen de la cátedra

| ID | Consulta | Qué puede cambiar |
| --- | --- | --- |
| G-01 | Si alcanzan la compra manual con ingreso controlado y el margen estimado como resultado económico. | Alcance de compras y fórmulas de R-02 y R-04. |
| G-02 | Si se exige una orden de reposición multilocal. | Consolidación (hoy una orden por destino). |
| G-03 | Si alcanza un remito por bulto. | Cardinalidad remito–bulto y la doble verificación. |
| G-04 / DN-08 | Si se exige borrado físico además de la baja lógica. | Administración de maestros. |
| G-05 | Si hay instrucciones de interfaz, dependencias o separación de código no publicadas. | Presentación React + Vite. |
| G-06 | Rúbrica, artefactos, formato y fecha de entrega. | Criterios 9 y 13 de M; el criterio de «no trivial» de los reportes. |
| Comprobante | Formato exigido del comprobante de venta. | Pantalla e impresión del comprobante (hoy desde el navegador, sin PDF). |

Cuando lleguen las respuestas, actualizar este documento y `DECISIONES_F00.md` antes de cambiar código.
