# Decisiones de F-00 — TP Integrador DAO 2026, Tema 3

Fecha de revisión: 19 de octubre de 2026. Audiencia: equipo del TP y docente.

**Estado actual:** documentación sincronizada el 19/10/2026 por pedido del usuario. DN-10 acordada para planificación: React + Vite, API Flask Python y SQLite/sqlite3. Políticas de dominio y DN-11 siguen pendientes; F-01 no está autorizado y no hay aplicación implementada.

## A. Resumen de cumplimiento del enunciado

### A.1 Fuentes, autoridad y límites de evidencia

| Referencia | Fuente leída | Localizador usado en esta revisión |
| --- | --- | --- |
| E1 | [tema3.pdf](<C:/Users/Tommy/Documents/cosas de la facultad/4to/DAO/TP-DAO/docs/tema3.pdf>) | Página 1, Contexto. |
| E2 | Mismo PDF | Página 1, Procesos de negocio obligatorios, puntos 1 a 7. |
| E3 | Mismo PDF | Página 1, Procesos de negocio opcionales. |
| E4 | Mismo PDF | Página 2, las cinco viñetas de Validaciones de negocio; el título comienza en página 1. |
| E5 | Mismo PDF | Página 2, Reportes sugeridos. |
| E6 | Mismo PDF | Página 2, Consideraciones particulares. |
| A | [AGENTS.md del TP](<C:/Users/Tommy/Documents/cosas de la facultad/4to/DAO/TP-DAO/AGENTS.md>) | Secciones numeradas; leído completo. |
| AP | [AGENTS.md del directorio DAO](<C:/Users/Tommy/Documents/cosas de la facultad/4to/DAO/AGENTS.md>) | Instrucción de ámbito superior, también leída. Su alcance introductorio se precisa para este TP mediante A §§3, 6 y 15 y E6. |
| P | [PLANIFICACION_TP_POO.md](<C:/Users/Tommy/Documents/cosas de la facultad/4to/DAO/TP-DAO/docs/PLANIFICACION_TP_POO.md>) | Leído completo, secciones 0 y A a N. Sus referencias E1 a E6 coinciden con las anteriores. |
| U | [Pedido inicial de revisión F-00](<C:/Users/Tommy/.codex/attachments/479212ff-a9d6-4cea-85c2-f00dc2bd4b45/Texto%20pegado.txt>) | Antecedente de esta revisión; no se confunde con instrucciones posteriores. |
| S | Pedidos posteriores del usuario en esta conversación | React + Vite/API Python/SQLite y posterior sincronización de las tres documentaciones. Autoriza su edición, sin implementación. |
| R | [PROPUESTA_ARQUITECTURA_REACT_PYTHON.md](<C:/Users/Tommy/Documents/cosas de la facultad/4to/DAO/TP-DAO/docs/PROPUESTA_ARQUITECTURA_REACT_PYTHON.md>) | Detalle técnico vigente de DN-10 y ADR-RP-01. |

Se extrajeron y revisaron visualmente las dos páginas del PDF, sin crear imágenes en disco. El repositorio contiene AGENTS.md y, bajo docs/, el enunciado y las tres documentaciones; carece de código, configuración de aplicación y pruebas. No se encontraron otros AGENTS.md dentro del TP. Los seis materiales enumerados en A §15 y una rúbrica adicional no están en este repositorio: se utiliza A como síntesis documentada, sin atribuirles una lectura directa.

Clasificación aplicada:

- **O — obligación explícita:** exigida por E1 a E6.
- **A — regla académica documentada:** indicada en AGENTS.md; se distinguen sus convenciones confirmadas, observadas y buenas prácticas generales (A §§6, 7, 9.1 y 13).
- **U/S — instrucciones del usuario:** backend exclusivamente Python; React + Vite y Flask adoptados para planificación al pedir sincronización; se editan P, D y R, sin implementar. Las restricciones de crear sólo un archivo pertenecían al encargo inicial y fueron sustituidas por S.
- **P — propuesta técnica o política del equipo:** recomendación sin aprobación todavía.
- **I/S — interpretación o supuesto:** evidencia incompleta; se identifica quién debe resolverla y cuándo.

El orden académico es el de A §2. U fija además límites de ejecución y tecnología. No se detectó conflicto explícito entre consigna y pedido actual. Una recomendación de este documento no altera ninguna de esas fuentes.

### A.2 Cobertura funcional contrastada

“Cubierto” significa **presente en la planificación**, nunca implementado o probado.

| Proceso obligatorio | Cobertura en P | Evaluación y decisión asociada |
| --- | --- | --- |
| 1. Administrar locales y CD | B.1 RF-01; G.1; I F-01 | Cubierto. Precisar bajas y modalidad operativa: DN-08 y DN-11. |
| 2. Administrar productos, categorías, precios, mínimos y proveedores | B.1 RF-02 a RF-04; G.1 | Cubierto. Identidad, unidades, mínimos e importes deben acordarse: DN-02, DN-06 y parte de DN-09. |
| 3. Consolidar necesidades de locales en orden hacia CD, con origen y destino | B.1 RF-06/RF-07; G.3 | Cubierto con interpretación pendiente: una orden por destino podría diferir de una consolidación global de varios locales. DN-04. |
| 4. Empaquetar con remito y precinto | B.1 RF-08/RF-09; C.3; G.4 | Cubierto. La cardinalidad remito/bulto no está fijada por E2.4: DN-01 y DN-02. |
| 5. Registrar despacho desde CD | B.1 RF-10; C.5; G.5 | Cubierto. Reservas y momento del descuento son propuestas coherentes, no texto literal de E2.5. DN-04. |
| 6. Registrar recepción en destino y revisar precinto | B.1 RF-11/RF-12; C.5; G.6 | Cubierto. Debe conservar la doble verificación y el rechazo; falta política multibulto. DN-01. |
| 7. Ventas de uno o más productos, cobros, comprobantes y devoluciones con stock/caja | B.1 RF-14 a RF-18; G.8/G.9 | Cubierto. Pagos divididos, plazos y tratamiento físico de devoluciones son elecciones: DN-05 y DN-07. |

Fuente de cada obligación: E2, punto homónimo. Compras e inventario también están exigidos por E1, aunque compras no sea un octavo proceso numerado. P B.1 RF-05 y F.6 los contempla; la generación de órdenes de compra sugeridas sigue siendo opcional (E3; P B.5 OP-01).

### A.3 Las cinco validaciones y los mínimos académicos

| Obligación | Correspondencia en P | Criterio que debe conservarse |
| --- | --- | --- |
| V1. Remito y contenedor Verificados; precinto roto implica Rechazado sin venta | RB-01/RB-02; C.5; T-11/T-12 | Recibir o verificar sólo uno nunca habilita el stock destino. Se trata de la primera viñeta de E4, con dos condiciones. |
| V2. Trazabilidad inmutable de los estados del bulto | RF-13/RB-03; C.5; F.5; T-13/T-30 | Conservar Preparado, Precintado, En tránsito, Recibido y Verificado/Rechazado; no sustituir historia por estado actual. |
| V3. No vender más del disponible y verificado | RF-14/RB-04; G.8; T-14/T-15 | Controlar el stock del local al confirmar y evitar efectos parciales de una venta inválida. |
| V4. Evitar productos/proveedores duplicados por identificadores definidos | RF-02/RF-04/RB-05; T-02 | Acordar identificadores; igualdad de nombre no constituye por sí sola duplicación. |
| V5. Devoluciones de venta registrada que cumplan reglas establecidas | RF-17/RB-06; G.9; T-18 a T-20 | Registrar política real del grupo, vínculo a venta y efectos en stock/caja; no inventar reglas docentes. |

Fuente: E4, viñetas 1 a 5; efectos de devoluciones también E2.7.

E6 exige al menos **dos patrones** y **cuatro reportes no triviales**, y evaluación crítica del ciclo del bulto. P C.5/C.6 propone State y Strategy; P G.11 define cuatro reportes distintos. Son candidatos razonables, sujetos a las precisiones de B.3. Las tres agrupaciones de R-01 cuentan como un reporte. E5 sugiere títulos; no obliga a implementar sus cinco familias completas. La POO se contrasta con A §§6.8 a 6.20, sin imponer herencia concreta ni una clase por tabla.

## B. Hallazgos de la revisión de planificación

### B.1 Correcciones y precisiones de alcance

Los hallazgos resueltos por esta sincronización se marcan como corregidos; las políticas de negocio no acordadas conservan su pendiente.

| ID / prioridad | Hallazgo con evidencia | Impacto recomendado |
| --- | --- | --- |
| H-01 / alta | La versión inicial de P trataba la ausencia de material GUI/framework como un permiso docente general. E1-E6 no fija interfaz; A §§3/4/8 exige pertinencia. | Corregido en P RT-05/D/E y DN-10: React + Vite/Flask acordados por S, sin aval académico atribuido; sólo revisar restricciones concretas si aparecen. |
| H-02 / alta | “Todos los bultos deben estar verificados antes del remito” es P C.5, no E4. Con un bulto rechazado podría bloquear permanentemente los íntegros. | Separar el invariante obligatorio de la política documental multibulto; DN-01 debe definir alcance, parciales y recuperación. |
| H-03 / alta | P G.3 sí distingue pedido local→CD y flujo físico CD→local, pero RF-07 y el modelo por destino no explicitan si existe consolidación de varios locales en una orden. E2.3 usa “necesidades de los locales en una orden”. | Conservar solicitante y trayecto físico; confirmar agrupación por destino frente a orden global antes de F-03. No afirmar que una variante es la única lectura. |
| H-04 / alta | E1 exige control antes de stock vendible; no define procedimientos de compra/devolución. P G.2/G.9 separa esos flujos del remito interno. | Clasificación precisada en P RB-17: principio obligatorio, procedimientos interpretados/propuestos y pendientes de DN-03/DN-07; no imponer ciclo completo del bulto a ambos. |
| H-05 / alta | Integrar compras es obligación contextual; generar órdenes sugeridas es opcional. P RF-05 y B.5 lo separa correctamente (E1, E3, E6). | Conservar la separación. Una compra manual con ingreso controlado puede ser el mínimo propuesto; recepción parcial y pagos a proveedores no están exigidos explícitamente. |
| H-06 / alta | Los plazos, locales permitidos, aptitud, reintegro y límite acumulado de devolución no están detallados en E4. P DN-07 los señala, pero deben pasar de preguntas a una política aceptada antes de F-05. | Proponer reglas mínimas verificables; no atribuirlas a la cátedra. Devolución comercial y rechazo logístico son procesos distintos. |
| H-07 / media | P F.6 usa último costo confirmado para estimar margen. Es una política, no costo real de las unidades trasladadas ni método contable exigido (E1, E5). | Conservar precio/costo histórico en venta, declarar la estimación y acordar costos faltantes. No restar compras de nuevo como gasto de las mismas unidades vendidas. |
| H-08 / media | La revisión detectó que decisiones compuestas debían separarse por fase consumidora (P I/K.1). | Aplicado en H/I y P I/K/L: DN-10 resuelta; catálogo primero y pagos/devoluciones/multibulto antes de sus fases, sin bloquear F-01 por todo F-00. |
| H-09 / media | La versión inicial de P F.5 afirmaba OneDrive sin evidencia; P 0.1 describía un inventario histórico. | Corregido: sincronización no verificada y precaución condicional; inventario actual y rutas docs/ alineados. |
| H-10 / media | La versión inicial mezclaba autoridad académica y alcance del agente, y conservaba el encargo de un único archivo. | Corregido en P 0/RT-07 y cabeceras: A §2 mantiene autoridad académica; S autoriza editar P/D/R, sin implementación ni cambios al enunciado/AGENTS.md. |

### B.2 Compras, devoluciones y cardinalidades: límite de lo explícito

| Tema | Exigido por la fuente | Política adicional que necesita acuerdo | Mínimo recomendado, todavía P |
| --- | --- | --- | --- |
| Ingreso de compra | Integrar compras e inventario y definir entidades/reglas necesarias (E1, E6). | Verificación de cantidades/costos, ingreso total/parcial, costo de referencia, tratamiento de diferencias y repetición (P G.2/F.6). | Un documento manual con líneas y una confirmación controlada total al CD. No asumir saldo vendible por cargar una compra sin confirmar. Recepciones parciales sólo si se eligen. |
| Devolución comercial | Venta registrada, reglas establecidas e impacto en stock/caja (E2.7, E4.5). | Plazo, local receptor, cantidades parciales, aptitud y forma de reintegro (P G.9/DN-07). | Vínculo a línea original, control acumulado y precio original; retorno apto verificado a disponible, no apto bloqueado. No inventar un plazo. |
| Un remito con varios bultos | Bultos con remito/precinto y doble verificación (E2.4, E4.1). | Verificación documental global/parcial, bultos pendientes/rechazados, destino de los conformes (P C.3/C.5). | Comenzar con 1:1 como incremento explícito. Si el equipo lo adopta para entrega, documentar su alcance y confirmar que cumple la expectativa académica; no reducirlo silenciosamente. |
| Un bulto con varios remitos, simultáneos o sucesivos | No se exige cardinalidad multirremito en E2/E4. P F.1 propone un único remito por bulto. | Vinculación por cantidades, criterio de documentos requeridos y correcciones sin sobrescribir vínculos originales. | Un remito de despacho por bulto. Un documento correctivo posterior, si se acuerda, se agrega con referencia al original y nunca borra trazabilidad. |

Ni la relación muchos a muchos ni el remito multibulto son requisitos expresos. Tampoco se justifica reservarlos como si fueran imposibles: la decisión pertenece al alcance acordado. Si se admite multirremito, “ambos verificados” necesita una interpretación explícita para todos los documentos pertinentes; no liberar por cualquiera de ellos (E4.1; U §3).

### B.3 Revisión del diseño orientado a objetos y los reportes

| Área | Evaluación de P | Ajuste proporcional propuesto y fuente |
| --- | --- | --- |
| Responsabilidades y encapsulamiento | Conservar C.1/C.2: entidades validan su estado; servicios coordinan varias entidades/transacciones; presentación no decide stock. | Propiedades sólo cuando validan/calculan; colecciones internas protegidas. A §§6.8/6.9. El servicio no debe convertirse en dueño de todas las reglas. |
| Composición | Correcta para detalles de compra, orden, bulto, venta y devolución; el documento crea y gestiona sus partes (P C.3). | No transferir líneas ni devolverlas al removerlas como objetos reutilizables. Conservar documentos auditados: composición no obliga a borrado físico. A §6.11. |
| Agregación y asociaciones | Producto/proveedor/ubicación tienen vida propia; asociación es suficiente. Remito/Bulto no implica composición (P C.3). | Sólo llamarlo agregación si hay semántica todo/parte con vida independiente; una referencia o FK no determina el tipo. A §6.11. |
| Herencia, ABC y polimorfismo | Ubicacion con tipo evita una jerarquía artificial. ABC de estados y estrategias tiene un contrato identificable (P C.1/C.4). | No exigir herencia CD/Local, múltiples interfaces o operadores mágicos para exhibir conceptos. Verificar implementaciones y mensajes comunes. A §§6.10, 6.12 a 6.14. |
| State | Justificado por seis estados y acciones permitidas según receptor (P C.5; E4/E6). | Bulto aplica la transición y agrega el evento; servicio persiste todo atómicamente. Remito conserva verificación independiente. No escribir un motor paralelo de estados en SQL ni en frontend. A §§6.20/6.23. |
| Historia | EventoEstadoBulto es evidencia, no otro controlador del ciclo (P C.2/F.5). | Operaciones de sólo agregado/lectura, sin setter público de estado ni edición de eventos; reconstruir desde DB no genera eventos nuevos. La protección ordinaria no equivale a invulnerabilidad del archivo. E4.2; P D.3/F.5. |
| Strategy | El cambio de agrupación puede ser un algoritmo intercambiable legítimo (P C.6), pero ventas y cobros no tienen igual granularidad (P G.11 R-01). | Definir un mismo conjunto de hechos para todas las estrategias, por ejemplo cobros/reintegros con fecha/local/medio; obtener ventas netas por separado antes de combinar resultados. Misma entrada y contrato, selección externa, sin duplicar ventas por líneas×cobros. A §6.20. |
| Clases propuestas | NecesidadReposicion está justificada si conserva origen y pendiente. MovimientoStock/MovimientoCaja aportan causa y trazabilidad; no son saldos editables (P C.2/F.3). | Categoria y MedioPago pueden ser catálogos simples. Comprobante puede representar la venta confirmada sin replicarla. ConsultasReportes puede empezar como funciones concretas de consulta. No imponer una clase por tabla ni una jerarquía por catálogo (A §9). |
| Existencia y movimientos | P F.3 distingue saldo operativo y evidencia. | Actualización única y atómica; evitar dos autoridades de saldo o reconstrucción integral por eventos. A §6.23; P F.4. |
| Cuatro reportes | R-01: agregados comerciales/caja; R-02: ranking/margen; R-03: existencias/mínimos; R-04: rechazos. Son distintos y calculan relaciones (P G.11). | Acordar fechas, faltantes, vacíos y costos; incluir productos con mínimo aunque aún no tengan saldo. R-04 cuenta bultos únicos y usa fecha del rechazo; valor bloqueado no es merma. E5/E6; DN-06/DN-09. |

**Conclusión de diseño:** conservar la base de P C/F, ajustar contratos y cardinalidades pendientes y materializar clases cuando tengan responsabilidad real. State y Strategy son propuestas justificadas; E6 exige dos patrones, sin fijar estos nombres. La revisión docente de su pertinencia es útil si la rúbrica define otro criterio, no una aprobación obligatoria inventada para cada clase.

## C. Decisiones DN-01 a DN-11

Todos los títulos y problemas provienen de P K.1. **DN-10 está resuelta para planificación por S.** DN-01 a DN-09 siguen como propuestas/políticas por acordar y DN-11 mantiene supuestos de operación/entrega; no se aprobaron por sincronizar arquitectura. “Resoluble técnicamente” clasifica decisiones de ingeniería; “equipo” define política/alcance; “docente” precisa una expectativa académica ambigua. Una misma DN puede contener subdecisiones de distinta autoridad.

Prioridades: **P0**, impacto inmediato en el inicio autorizado de F-01; **P1**, importante antes de la fase consumidora; **P2**, detalle que puede esperar sin perder datos necesarios. El límite es una dependencia, no una fecha inventada. Las alternativas listadas son viables sólo si conservan E4 y backend Python.

### DN-01. Verificación del remito y cardinalidad de bultos

- **Estado:** aprobada por el usuario el 21/10/2026 para F-03; política vigente en la sección M.

- **Problema y origen:** cómo verificar documentación cuando hay varios bultos o recepción incompleta/rechazada, sin liberar indebidamente unidades. E2.4/E4.1; P C.3/C.5, F.1, K.1.
- **Alternativas y balance:** (a) 1 remito–1 bulto: simple y demostrable; más documentos, no representa agrupaciones. (b) 1 remito–varios bultos, verificación global: conserva un criterio uniforme; un pendiente/rechazado bloquea todos y necesita resolución. (c) Multibulto con conformidades parciales documentadas: mayor flexibilidad; obliga a precisar qué significa remito Verificado y su alcance por bulto. Multirremito añade reconciliación de cantidades sin exigencia actual.
- **Recomendación técnica:** comenzar 1:1 para demostrar ambos controles; para entrega elegir explícitamente entre 1:1 y multibulto. Si se adopta verificación global, aceptar el bloqueo de íntegros o definir su resolución trazable; no reabrir un Rechazado ni editar historia. No implementar liberación parcial bajo un remito pendiente sin aclaración académica.
- **Impacto funcional/arquitectónico:** cardinalidades, estado documental independiente, habilitación única de stock y consulta de retenidos. No requiere un State para Remito por anticipado. Afecta modelo, esquema y casos de recepción.
- **Fases:** F-03, F-04 y R-04 de F-06; preparar diseño antes de esquema logístico de F-03.
- **Responsable:** **equipo** elige alcance/cardinalidad; **requiere aclaración del docente** si se pretende verificación parcial o si 1:1 no satisface la expectativa; **resoluble técnicamente** preservar el invariante y atomicidad.
- **Prioridad/límite:** P1, antes de F-03; no bloquea catálogo F-01. Cierre verificable: tabla de casos 1:1, pendiente, rechazo y multibulto si se admite, con disponibilidad esperada y destino de lo bloqueado.

### DN-02. Identificadores y duplicados

- **Estado:** aprobada por el usuario el 21/10/2026 para F-03 (identificadores logísticos); política vigente en la sección M.

- **Problema y origen:** definir identidad comercial y alcance de unicidad. E4.4; E2.2/E2.4/E2.7; P RF-02/RF-04, F.1, K.1.
- **Alternativas y balance:** (a) códigos internos ingresados por el equipo: simple y suficiente para catálogo; requiere disciplina de identificación. (b) identificadores externos como código de barras/CUIT: útiles si el dominio elegido los usa; agregan formatos/reglas no exigidos. (c) ID técnico más código comercial: referencias estables y control de duplicados; distingue dos identificadores. El nombre por sí solo no es una clave fiable.
- **Recomendación técnica:** ID interno para persistir y código comercial único para producto/proveedor. Acordar espacios, mayúsculas, ceros iniciales y reutilización tras baja; no normalizar destruyendo diferencias válidas. Mantener código como texto. Unicidad en dominio y DB, sin atribuir este mecanismo concreto a E4.
- **Impacto funcional/arquitectónico:** búsqueda, referencias, claves y errores de duplicados. Para remito, precinto y comprobante, definir si la unicidad es global o por emisor/local/serie; sus reglas no necesitan cerrarse junto al catálogo.
- **Fases:** catálogo F-01; restricciones persistentes F-02; documentos logísticos F-03 y comprobantes F-04.
- **Responsable:** **equipo** decide identificadores del negocio; **resoluble técnicamente** normalizar según política y proteger unicidad. Docente sólo si especifica formatos no disponibles.
- **Prioridad/límite:** P0 para producto/proveedor antes de F-01; P1 para remito/precinto antes de F-03 y comprobante antes de F-04. Cierre: ejemplos aceptados/rechazados, incluidos mismo nombre con distinto código y código repetido tras baja.

### DN-03. Compra, recepción y costo de referencia

- **Estado:** aprobada por el usuario el 21/10/2026 para F-02; política vigente en la sección L.

- **Problema y origen:** integrar abastecimiento y economía sin inventar un módulo contable. E1/E6; P RF-05, G.2, F.6, K.1. OP-01 de E3 no reemplaza la compra básica.
- **Alternativas y balance:** (a) compra manual e ingreso total controlado: pocas operaciones y efecto trazable; no gestiona entregas parciales. (b) compra con recepciones parciales separadas: sigue pendientes del proveedor; más documentos y límites acumulados. Para costo: último confirmado es simple pero estimativo; promedio ponderado requiere mantener valuación y reglas de devoluciones; FIFO exige asignación de consumos y más trazabilidad de costo.
- **Recomendación técnica:** mínimo manual con proveedor, líneas, cantidades/costos e ingreso total confirmado una vez. Verificación de ingreso integrada a esa acción, sin exigir bulto/remito interno al proveedor. Último costo confirmado como referencia estimada con fecha/orden estable; precio y costo quedan conservados por línea de venta. No introducir pagos a proveedores o recepción parcial sin necesidad acordada.
- **Impacto funcional/arquitectónico:** movimientos/saldo CD, datos históricos para margen y tratamiento de costo faltante. Recomendar que una compra sin costo no pueda confirmarse en el alcance mínimo; ante datos heredados incompletos, no fingir costo cero ni margen completo. Cambiar método antes de capturar los datos evita perder información de valuación.
- **Fases:** F-02, F-04, F-06; costo del bulto para R-04 se registra desde F-03 si se acepta ese indicador.
- **Responsable:** **equipo** define proceso/método; **requiere aclaración del docente** del mínimo académico de compras y si margen estimado satisface resultado económico; **resoluble técnicamente** atomicidad, parámetros y copia histórica.
- **Prioridad/límite:** P1 antes de F-02; elegir método antes de datos/costos que lo consumen. No bloquea F-01. Cierre: ejemplo de compra→saldo→venta→margen y caso de ingreso repetido o fallido sin duplicación.

### DN-04. Consolidación, asignación y reserva

- **Estado:** aprobada por el usuario el 21/10/2026 para F-03; política vigente en la sección M.

- **Problema y origen:** distinguir solicitante, flujo físico y agrupación de pedidos, además de impedir asignaciones repetidas. E2.3 a E2.5; P G.3/G.4, RB-09, K.1.
- **Alternativas y balance:** (a) orden por CD/destino que consolida varias necesidades: preparación simple; quizá no refleje una orden que reúna varios locales. (b) orden global al CD con líneas por destino: expresa consolidación conjunta; exige separar preparación/remitos por destino. Para disponibilidad: reservar al preparar evita doble asignación; descontar inmediatamente simplifica reservas pero debe distinguir mercadería aún físicamente en CD.
- **Recomendación técnica:** conservar necesidades y cantidades consolidadas por producto/destino, sin mezclar destinos. Preferir orden por destino si la interpretación académica lo admite; usar cabecera global con detalle por destino si se exige consolidar varios locales en una sola orden. Reservar al preparar y descontar físico CD al despachar. No reservar de nuevo al precintar.
- **Impacto funcional/arquitectónico:** cardinalidades de orden/detalle/bulto, pendientes y saldos. Asignación parcial puede conservar remanente en la necesidad; alternativa mínima es no confirmar lo que exceda stock. Cancelar un Preparado exige liberar reserva mediante operación explícita; cancelaciones posteriores no se agregan automáticamente.
- **Fases:** F-03; integridad de saldos definida desde F-02, ventas/reportes F-04/F-06.
- **Responsable:** **equipo** decide reservas, parciales y cancelaciones; **requiere aclaración del docente** si E2.3 exige orden multilocal; **resoluble técnicamente** suma, vínculos y conservación de unidades.
- **Prioridad/límite:** P1 antes de modelar reposición en F-03. No bloquea F-01. Cierre: consolidar al menos dos necesidades y mostrar qué ocurre con dos locales y con stock insuficiente.

### DN-05. Cobros, medios y comprobantes

- **Estado:** aprobada por el usuario el 21/10/2026 para F-04; política vigente en la sección N.

- **Problema y origen:** cerrar una venta y su impacto en caja con reglas de cobro claras. E2.7; E5; P G.8/G.11, DN-05.
- **Alternativas y balance:** (a) un medio por venta y cobro total: simple, satisface uso de varios medios entre ventas; no combina medios en una venta. (b) varios cobros cuya suma cubre la venta: flexible, más casos de reintegro y reportes. (c) crédito/cobro diferido: agrega deuda y seguimiento; se relaciona con cuentas corrientes opcionales de E3 y no se recomienda para el mínimo.
- **Recomendación técnica:** venta totalmente cobrada y comprobante interno consultable. Un medio por venta basta como base si el equipo lo acepta; pagos divididos se agregan sólo por una necesidad elegida. Catálogo de medios sin integración bancaria. Si se admite vuelto, distinguir entregado, vuelto y cobro neto; no ingresarlo entero como venta. Comprobante vinculado a la misma venta al reconsultar.
- **Impacto funcional/arquitectónico:** Venta/Cobro/MovimientoCaja, granularidad de R-01, documentación y reintegros. No duplicar una venta por cada cobro al agregar. Comprobante interno no implica facturación fiscal.
- **Fases:** F-04; F-05 para reintegro y F-06 para reportes. Adaptar P J.3 si se descartan pagos divididos: su caso A usa efectivo y tarjeta en la misma venta.
- **Responsable:** **equipo** fija medios, pagos múltiples, vuelto/formato; **resoluble técnicamente** sumas, transacción y representación. Docente sólo si se exige crédito o un comprobante específico.
- **Prioridad/límite:** P1 antes de F-04; definir devolución compatible antes de F-05. No bloquea F-01. Cierre: total, cobro neto, caja y comprobante coinciden, incluidos insuficiencia y reconsulta.

### DN-06. Unidades, mínimos y precios válidos

- **Problema y origen:** validar cantidades/precios y dar significado al mínimo sin inventar una unidad comercial. E2.2; E5; P RF-03/RB-07, G.11 R-03, DN-06.
- **Alternativas y balance:** (a) unidades enteras: fáciles de validar/explicar; excluyen venta por peso/volumen. (b) fracciones con escala acordada: más productos; afecta cálculos y redondeo. Mínimo global por producto simplifica configuración; mínimo por producto/local refleja necesidades distintas y requiere configuración adicional. Usar < o <= responde a políticas diferentes de alerta.
- **Recomendación técnica:** enteros positivos para movimientos y mínimos no negativos por producto/local. Proponer alerta disponible <= mínimo y déficit máximo entre mínimo−disponible y cero; en el mínimo exacto puede haber alerta con déficit cero. Precio de venta positivo en el mínimo propuesto; admitir precio cero sólo si el equipo define su sentido. El PDF no impone estos límites exactos.
- **Impacto funcional/arquitectónico:** atributos, validaciones, detalles de compra/venta y R-03. Evitar equiparar saldo ausente con producto inexistente; incluir productos con mínimo configurado sin movimientos. Separar mínimo de cantidad operativa.
- **Fases:** F-01, F-02 a F-05 y F-06.
- **Responsable:** **equipo** define unidades y política comercial; **resoluble técnicamente** representación y validaciones. Docente sólo si hay catálogo/unidad prescritos no aportados.
- **Prioridad/límite:** P0 para unidad, ámbito del mínimo y validez del precio antes de F-01. P1 para umbral/fórmula final antes de F-06, o antes si se incorpora alerta operativa. Cierre: cero, negativo, fracción, último disponible y mínimo exacto tienen resultados escritos.

### DN-07. Política de devoluciones

- **Problema y origen:** determinar qué retorno comercial se acepta y cómo afecta mercadería y dinero. E2.7/E4.5; P RB-06/RB-11/RB-17, G.9, K.1. La consigna encarga reglas adicionales al grupo (E6).
- **Alternativas y balance:** (a) mismo local de venta, devolución total/parcial por línea y reintegro a medio original: trazabilidad simple; menos flexibilidad. (b) devolución en otro local: útil operativamente; exige diferenciar caja receptora, stock receptor y venta de origen. (c) sólo producto apto o también no apto con stock bloqueado: lo primero reduce condiciones; lo segundo registra mejor la custodia pero necesita política de destino. Cambio por otro producto/nota de crédito añade otro proceso no obligatorio.
- **Recomendación técnica:** mismo local como mínimo propuesto, referencia a venta/línea, cantidad acumulada no superior a la vendida, reintegro al precio original y control de aptitud. Si se acepta producto no apto, registrar su entrada bloqueada; si se rechaza la devolución, no registrar reintegro ni ingreso ficticio. Definir expresamente si existe plazo; no asignar días sin decisión. Retorno apto controlado puede recuperar disponibilidad sin remito interno CD.
- **Impacto funcional/arquitectónico:** Devolucion y detalles referencian la línea; stock/caja se actualizan juntos. El precio/costo original evita alterar historia. Si se permiten pagos divididos, el equipo debe elegir reparto/restricción de reintegro y evitar devolver más de lo cobrado por medio sin regla explícita. Una devolución válida no equivale a revertir físicamente una venta borrándola.
- **Fases:** F-05 y F-06; las referencias y valores originales deben capturarse desde F-04.
- **Responsable:** **equipo** define política; **resoluble técnicamente** remanente, vínculo e integridad; docente sólo para una regla de evaluación o interpretación no disponible, no para sustituir toda decisión de negocio.
- **Prioridad/límite:** P1: datos originales necesarios antes de F-04 y política completa antes de F-05. No bloquea F-01. Cierre: venta inexistente, devolución parcial repetida, exceso, no apto, fallo y reintegro tienen resultados acordados.

### DN-08. Administración, edición y bajas

- **Problema y origen:** alcance de “administrar” y conservación de referencias. E2.1/E2.2; E4.2; P G.1/F.5, DN-08; A §§6.21/6.23 y 9.1.
- **Alternativas y balance:** (a) alta/consulta/modificación sin baja: menor alcance, posible insuficiencia frente a expectativa ABMC. (b) baja administrativa: conserva documentos e identidad; exige filtrar activos y definir uso de inactivos. (c) borrado físico sólo sin referencias: admite limpieza de errores; añade casos y no debe afectar historial. Borrado en cascada de documentos auditados no es una alternativa compatible.
- **Recomendación técnica:** alta, consulta, modificación de maestros y baja administrativa. Consultar un inactivo desde documentos históricos sigue permitido; proponer impedir nuevas operaciones con él. Mantener códigos únicos incluso tras baja y permitir reactivación si se acuerda. La unicidad de un código no debe cambiar por ocultar un registro. No eliminar eventos ni documentos confirmados.
- **Impacto funcional/arquitectónico:** estado administrativo, consultas y restricciones de referencias. POO no obliga a setters triviales. La inmutabilidad explícita se refiere a estados del bulto; conservar el resto de documentos es una decisión de integridad propuesta, no una cita literal de E4 para todo el sistema.
- **Fases:** F-01 y F-02; efectos en operaciones F-03 a F-05; validación final F-07.
- **Responsable:** **equipo** define comportamiento de activos/inactivos; **resoluble técnicamente** conservar referencias; **requiere aclaración del docente** si “administrar” debe demostrar un DELETE físico además de baja administrativa.
- **Prioridad/límite:** P0 para comportamiento mínimo de catálogo antes de F-01; P1 para alcance académico de baja antes de cerrar administración persistente F-02. La duda sobre DELETE no impide modelar alta/consulta/modificación. Cierre: baja de producto usado conserva su venta y no permite duplicar el código.

### DN-09. Importes, fechas y resultado económico

- **Estado:** aprobada por el usuario el 21/10/2026 para F-02; política vigente en la sección L.

- **Problema y origen:** representar dinero/tiempo y definir indicadores explicables. E1/E5; P E.1, F.6, G.11, K.1. Rechazo y merma no tienen equivalencia obligatoria en E4/E5.
- **Alternativas y balance:** (a) una moneda y enteros en su unidad mínima: sumas exactas y simples; exige escala/conversión acordada. (b) Decimal con redondeo explícito: admite fracciones y tasas; más reglas de conversión/almacenamiento. Fechas locales uniformes simplifican demostración; instantes con zona explícita facilitan acceso desde ubicaciones distintas. Para resultado: margen comercial estimado es proporcional; utilidad contable integral requiere gastos, impuestos y políticas ausentes.
- **Recomendación técnica:** una moneda, escala definida e importes exactos; proponer enteros si DN-06 mantiene unidades enteras. Acordar redondeo de cualquier cálculo que produzca fracciones. Instantes con criterio uniforme y períodos inicio incluido/fin excluido; registrar devolución en su fecha sin reescribir venta. La zona de esta revisión es America/Buenos_Aires; adoptarla para la aplicación sigue siendo decisión del equipo. Último costo y margen se vinculan a DN-03.
- **Impacto funcional/arquitectónico:** tipo de precio desde catálogo, almacenamiento de costos/fechas desde compras, comprobantes y filtros. Separar ventas netas, cobros/reintegros y margen; pagos a proveedores/gastos no pueden fingirse incluidos. Fecha de rechazo para R-04, no preparación. Rechazo bloquea custodia; sólo una baja definitiva acordada puede representar merma.
- **Fases:** F-01 para precio; F-02 para costos/fechas; F-03 para historia/costo de bulto; F-04/F-05 y F-06 para economía.
- **Responsable:** **equipo** elige moneda, escalas, períodos y significado; **resoluble técnicamente** representación exacta y filtros; **requiere aclaración del docente** si resultado económico exige más que margen estimado o alguna merma operativa.
- **Prioridad/límite:** P0 para representación/escala del precio antes de F-01; P1 para fechas/costo antes de F-02 y captura de R-04 antes de F-03; P2 para presentación final de reportes antes de F-06. Cierre: operación conocida, devolución en otro período y cambio de costo no alteran importes históricos.

### DN-10. Interfaz y arquitectura de presentación

- **Estado:** resuelta para planificación el 19/10/2026 por S; no implementada. P D.2, este documento E.1 y R §2 comparten AC-01 a AC-07.
- **Problema y origen:** ofrecer UI elegida sin desplazar POO ni negocio Python. E1-E6 no fija interfaz; S adopta la opción React + Vite de la evaluación solicitada. A §§4/8/9 exige pertinencia/simplicidad.
- **Alternativas y balance:** consola reduce herramientas; web renderizada reduce fronteras; React/API añade contrato y build con UI elegida; escritorio añade ventanas/distribución. Se conserva la comparación de D. Flask es el adaptador elegido por flujo síncrono simple; FastAPI aporta esquemas/OpenAPI con conceptos adicionales, como alternativa futura de reconsideración.
- **Decisión:** React + Vite en navegador, API Flask HTTP/JSON Python bajo /api, SQLite/sqlite3; desarrollo npm con proxy transparente y build estático servido por Python. Nada de backend/SSR/BFF/reglas/DB en Node.
- **Impacto funcional/arquitectónico:** entidades, casos de uso y persistencia Python conservados; rutas delgadas y React como presentación. Pruebas de API directa, errores, comunicación y build sin Vite. Ninguna variante cambia la doble verificación ni permite confiar en cliente.
- **Fases:** F-01 a F-07 con el impacto de R §10 ya reflejado en P I. No construir una consola paralela por anticipado.
- **Responsable:** usuario adopta la arquitectura al pedir alineación; equipo fija versiones, JS/TS y contratos por caso. Docente sólo para condiciones académicas concretas si existen; no se atribuye aprobación no recibida.
- **Prioridad/límite:** arquitectura P0 ya resuelta; detalles de entorno/transporte antes de implementar F-01 y cada contrato antes de su caso. La autorización de implementación sigue pendiente.
- **Cierre verificable:** decisiones y restricciones coinciden en los tres documentos; runtime, instalación y build se verificarán en fases futuras autorizadas.

### DN-11. Modalidad operativa, simultaneidad y entrega

- **Estado:** modalidad y simultaneidad aprobadas por el usuario el 21/10/2026 para F-02; política vigente en la sección L. Fecha, integrantes y formato de entrega siguen pendientes.

- **Problema y origen:** saber si “varios locales” son entidades en una demostración o usuarios reales en distintas máquinas. E1/E2.1 describe negocio, no topología. P A.3/D.3/K.1 usa instalación local/un escritor como supuesto. No hay rúbrica, integrantes ni fecha de entrega aportados.
- **Alternativas y balance:** (a) una computadora, ubicaciones lógicas: menor operación y suficiente para simular flujos; no demuestra acceso remoto. (b) servidor Python central y navegadores de locales: datos centrales reales; requiere concurrencia, acceso y seguridad adecuados. (c) instalaciones con sincronización: complejidad de consistencia sin obligación confirmada; no recomendada. Las primeras dos son opciones proporcionadas si responden a la modalidad real.
- **Recomendación técnica:** proponer demostración en un equipo, con un CD y varios locales lógicos, sin cuentas informáticas hasta confirmar necesidad. Una web local sigue siendo local. Si se requiere acceso simultáneo por red, mantener un backend Python central, revalidar escrituras, definir controles y evaluar SQLite con la carga real antes de cambiar de motor. No compartir el archivo DB entre equipos como sustituto de servidor.
- **Impacto funcional/arquitectónico:** transacciones y conflictos, atribución de operaciones, autenticación si se necesita, comando/entorno de ejecución y distribución. Un actor del dominio no implica usuario informático. Fecha, integrantes y formato de entrega no determinan las entidades del catálogo.
- **Fases:** F-00/F-01 para límites operativos; F-02 para persistencia/concurrencia; F-07 para entrega. Capturar fechas y artefactos exigidos cuando se obtengan, no esperar al último momento si afectan alcance.
- **Responsable:** **equipo** decide la modalidad deseada y capacidades; **requiere aclaración del docente** sobre topología y artefactos exigidos si no hay instrucciones; **resoluble técnicamente** ejecución y consistencia para modalidad aceptada.
- **Prioridad/límite:** P0 para hipótesis operativa antes de interfaz F-01; confirmar concurrencia antes de F-02. P1 para rúbrica/fechas al planificar entrega y antes de F-07. No bloquear catálogo por desconocer formato de presentación. Cierre: lugar de ejecución, usuarios simultáneos y límites de demostración escritos.

## D. Comparación arquitectónica

### D.1 Drivers y condiciones comunes

Prioridad alta: obligaciones E1/E2/E4/E6, POO explicable (A §14), backend sólo Python y arquitectura React + Vite/API Flask acordada por S. Prioridad media: demostrar operaciones/reportes con claridad, desarrollo y ejecución comprensibles, aislamiento para pruebas y separación de responsabilidades. No hay carga, plazo, experiencia del equipo ni número de usuarios simultáneos confirmados; no se puntúan productividad o rendimiento con números inventados.

Las cuatro alternativas se conservan como comparación técnica; **la opción vigente es C con React + Vite y Flask**, acordada por S. Las otras no son líneas paralelas de implementación. Todas son técnicamente viables, con la distinción de D.3 para escritorio. La aceptación académica depende de las reglas concretas que se obtengan y de que la UI no sustituya la POO. No se encontró una obligación de GUI ni una prohibición. La consola tiene mayor cercanía al material disponible; eso no le da preferencia automática frente al objetivo de demostración.

### D.2 Comparación de las cuatro opciones

| Criterio | A. Consola Python | B. Web renderizada por Python | C. API Python + frontend independiente | D. GUI de escritorio |
| --- | --- | --- | --- | --- |
| Compatibilidad académica | Cercana a ejemplos; interfaz no fijada por consigna. | POO/SQLite aplicables; HTTP/plantillas son contenido adicional que debe poder explicarse. | Igual base POO; contratos HTTP y estado cliente amplían superficie. | POO aplicable; ventanas/eventos no cubiertos en A. No equivale a prohibición. |
| Complejidad | Menor infraestructura; menús largos para flujos ricos. | Intermedia: servidor, rutas, formularios, plantillas y estáticos. | Mayor: API, serialización, errores y coordinación cliente/servidor. | Intermedia: vistas, eventos, navegación y actualización del estado visual. |
| Aplicación de POO | Directa si los menús llaman objetos/casos de uso. | Directa si las rutas delegan en el modelo Python. | Directa en servidor; riesgo de duplicar reglas en navegador. | Directa si callbacks delegan, evitando mezclar widgets y negocio. |
| Separación de responsabilidades | Posible sin framework; no queda garantizada por ser consola. | Presentación web y dominio separados dentro de una aplicación. | Límite explícito por API, con costo de contrato; no exige despliegues separados. | Presentación por eventos separable del dominio. |
| Experiencia de usuario | Entrada secuencial; peor comparación de tablas/documentos. | Formularios, tablas, filtros y estados visibles con poca lógica cliente. | Interacción más rica si se necesita, a costo de más estado/validación visual. | Interacción local visual, sin navegador; depende del toolkit. |
| Facilidad de demostración | Reproducible con datos/guion; menos visual. | Navegador facilita mostrar historia, bloqueo de stock y reportes. | Buena UI, pero debe comprobarse que frontend/API funcionen juntos. | Visual en una máquina; requiere entorno de escritorio compatible. |
| Mantenimiento | Pocas dependencias; menús pueden crecer. | Un proyecto y reglas servidor; actualizar framework/plantillas. | Dos superficies y cambios de contrato coordinados. | Un cliente local; cambios de vistas y distribución por equipo. |
| Dependencias/herramientas | Python y sqlite3; pytest de desarrollo ya abordado. | Python, framework/plantillas por elegir y navegador; npm no es necesario para HTML/CSS simple. | Framework API Python; frontend y posible build npm; runtime servidor siempre Python. | Toolkit por elegir; verificar sus runtimes si se exige toda operación backend en Python. |
| Desarrollo | Un entorno; validaciones de entrada manuales. | Enlaces/formularios y respuestas HTTP; negocio permanece Python. | Contratos y estados de red; posible servidor de desarrollo frontend sólo para interfaz. | Ciclo de eventos y tratamiento de acciones sobre ventanas. |
| Pruebas | Dominio, SQLite y flujos de consola. | Mismos tests de dominio/datos, más formularios/rutas y recorrido de navegador. | Mismos tests, más contrato API, cliente y flujos integrados. | Mismos tests, más callbacks y recorrido visual del escritorio. |
| Ejecución/distribución | Python y archivo DB local; terminal. | Backend Python más navegador; local o servidor central según DN-11. | API Python y cliente estático compilado; durante desarrollo puede haber dos procesos. | Python/toolkit o empaquetado por plataforma; DB local en mínimo propuesto. |
| Reversibilidad | Dominio se conserva al cambiar UI si está separado. | Puede sustituirse presentación; no requiere una API pública anticipada. | Dominio reusable; contrato externo encarece cambios posteriores. | Dominio reusable; widgets/callbacks se rehacen al migrar a web. |

Son comparaciones técnicas cualitativas, no obligaciones docentes. Fuentes del encaje local: P C/D/E/J; A §§6.8 a 6.23 y 8/9; U §§2/5. Referencias primarias verificadas el 19/10/2026 para capacidades concretas: [Flask, formularios, archivos estáticos y plantillas](https://flask.palletsprojects.com/en/stable/quickstart/), [sqlite3, acceso y transacciones](https://docs.python.org/3/library/sqlite3.html), [tkinter y su relación con Tcl/Tk](https://docs.python.org/3/library/tkinter.html). No se fijan versiones ni se considera instalada una dependencia porque su documentación exista.

### D.3 Backend Python garantizado en cada alternativa

| Superficie | Condición de cumplimiento de U §2 |
| --- | --- |
| A | Entrada y presentación de consola invocan negocio, validaciones, persistencia y operaciones escritas en Python. |
| B | HTML se renderiza desde Python. Plantillas sólo presentan datos; no contienen reglas de stock, estados, precios ni reintegros. JavaScript, si se elige, se ejecuta en navegador para interacción. |
| C | API, validaciones definitivas, cálculo, acceso a datos y procesos en Python. Cliente estático/navegador; npm puede construir o servir la interfaz durante desarrollo. No se admite Node para BFF, SSR, server actions, rutas de aplicación o procesamiento backend. Puede servirse el build estático desde Python, evitando otro servidor de aplicación. |
| D | Presentación llama casos de uso Python. Un toolkit puede usar un runtime gráfico como soporte de UI; toda regla, acceso a datos y procesamiento backend queda en Python. Tkinter es una interfaz Python sobre Tcl/Tk: no se propone un servidor ni reglas de negocio en Tcl. Si se elige frontend de otro lenguaje, sólo UI y comunicación con backend Python. |
| Datos y tareas | SQL permitido para consultas, restricciones y transacciones. El motor de estados y políticas permanecen Python. Ningún servicio externo, ORM o automatización no Python debe ejecutar reglas backend en su lugar. Las verificaciones cliente no son autoridad. |

## E. Recomendación técnica

### E.1 Acuerdo vigente de F-00: React + Vite y API Flask Python

Estado: **acordado para planificación por S el 19/10/2026; sin implementación**. Responsable: usuario. El detalle técnico reside en R, ADR-RP-01; P D.4 (ADR-001) resume el mismo acuerdo. Sustituye las preferencias anteriores por consola y web renderizada. No se convierte en aceptación docente ni en cierre de todas las políticas F-00.

| ID | Decisión vigente |
| --- | --- |
| AC-01 | Frontend React + Vite ejecutado en navegador; `npm run dev` durante desarrollo. |
| AC-02 | API HTTP/JSON con Flask y backend exclusivamente Python; prefijo `/api`. |
| AC-03 | Persistencia SQLite mediante `sqlite3` y SQL directo parametrizado. |
| AC-04 | Desarrollo con proxy transparente de Vite hacia Python, conservando `/api` y sin lógica de aplicación en Node. |
| AC-05 | `npm run build` genera estáticos; para demostración local Python sirve frontend compilado y API desde el mismo origen. |
| AC-06 | Prohibidos backend, SSR, BFF, reglas de negocio y acceso a DB desde Node.js; Node se limita a herramientas/frontend. |
| AC-07 | Dominio POO, cálculos definitivos, validaciones y transacciones en Python; React presenta e informa la intención del usuario. |

La opción C asume el costo de contrato HTTP, dos entornos durante desarrollo y verificación del build a cambio de la UI elegida. Flask mantiene el flujo síncrono con sqlite3; FastAPI sólo se reconsiderará por experiencia o esquemas/OpenAPI que lo justifiquen, no como framework pendiente de elegir.

Desarrollo con npm run dev y proxy sin lógica; demostración con estáticos compilados y API servidos por Python. Puertos/loopback siguen como configuración propuesta, JavaScript/TypeScript y versiones por fijar. Modalidad real/concurrencia DN-11 y políticas DN-01 a DN-09 conservan sus plazos.

No hay aplicación/datos que migrar. Cambiar adaptador requiere pruebas de contrato aunque preserve dominio. Validación futura: flujo completo, API directa, rollback/reinicio y build con Vite apagado. Reconsiderar sólo por restricción concreta, cambio de topología o necesidad demostrada. Adoptar estas decisiones documentales no autoriza F-01.

### E.2 Límites, datos y consistencia recomendados

Conservar la separación lógica de P D.2/D.3 y F.3/F.4:

| Responsabilidad | Autoridad y colaboración propuesta |
| --- | --- |
| React + adaptador API Flask | React recoge entradas; Flask valida transporte/traduce errores y llama casos de uso. Ninguno sustituye invariantes del dominio Python. |
| Casos de uso Python | Coordinan entidades y acceso concreto, revalidan datos y son dueños de la transacción. Cada acción confirma o revierte sus cambios vinculados. |
| Dominio Python | Mantiene invariantes, contenido, cantidades y estados; State/Strategy con contratos justificados. No importa consola, HTTP, toolkit ni sqlite3. |
| Persistencia Python/SQL | Traduce filas/objetos, parametriza y guarda. SQLite es fuente persistente; saldos y movimientos se guardan en la misma transacción. |
| Reportes | Leen operaciones confirmadas; agrupan sin modificar stock/caja. Cada indicador identifica su fuente, período y limitación de costo. |

Comunicación React/API mediante HTTP/JSON; comunicación interna mediante llamadas Python síncronas. Una única base permite atomicidad de ingreso, despacho, verificación, venta y devolución, sin transacciones distribuidas. Registrar estado, evento y efectos de inventario conjuntamente; si falla la persistencia, descartar/recargar objetos mutados. No mantener transacciones abiertas mientras se espera entrada humana (P D.3/F.4; A §6.23).

Operación propuesta: ejecución local para demostración hasta resolver DN-11; manejo visible de errores e historial para diagnóstico, sin plataforma de monitoreo. En la UI React/API acordada, escapar datos presentados y proteger acciones que escriben; controles de acceso, sesiones y exposición se ajustarán a la modalidad aprobada. No se inventa una exigencia de cuentas ni se promete seguridad de producción. Mantener SQL parametrizado y tests aislados (A §§6.22, 9.1).

El criterio de datos inmutables protege operaciones ordinarias. Controles SQL contra modificación/baja de eventos son una defensa posible; no son por sí mismos el modelo de estados ni un requisito de usar triggers. Respaldo consistente y evitar sincronizar la DB abierta son precauciones operativas condicionales, no prueba de que el directorio actual use OneDrive (P F.5; H-09).

## F. Preguntas pendientes para el equipo

Son preguntas para aprobar políticas concretas. El pedido S resuelve la arquitectura de DN-10; no registra respuesta sobre las políticas de negocio restantes.

| Orden | Pregunta y propuesta a evaluar | Autoridad / límite |
| --- | --- | --- |
| 1 | Con React + Vite y Flask ya acordados, ¿JavaScript o TypeScript y qué versiones compatibles usará el equipo? ¿Qué herramientas de prueba UI aportan valor? | Equipo/técnico, detalles de DN-10 antes de implementación F-01; no reabrir frontend/framework. |
| 2 | ¿La demostración será en una computadora con varios locales lógicos o necesitamos usuarios desde varios equipos? Propuesta: una instalación para demostración. | Equipo, DN-11; límite inicial antes de F-01, concurrencia antes de F-02. |
| 3 | ¿Aceptamos ID interno y códigos comerciales únicos, texto normalizado sin perder ceros, también únicos tras baja? ¿Qué ejemplos de códigos usaremos? | Equipo, DN-02; producto/proveedor antes de F-01. |
| 4 | ¿Unidades enteras, mínimo por producto/local y precio positivo? ¿Qué moneda/escala monetaria usaremos? ¿Aceptamos baja administrativa, consulta histórica y bloqueo de nuevas operaciones con inactivos? | Equipo, DN-06/DN-08/DN-09; parte mínima antes de F-01. |
| 5 | ¿Compra manual con ingreso total controlado y último costo como estimación? ¿Confirmamos que no habrá recepción parcial ni pagos a proveedores en el mínimo? | Equipo, DN-03/DN-09; F-02. Ajustar si docente exige mayor alcance. |
| 6 | ¿1:1 de remito/bulto para entrega o multibulto? Si es multibulto global, ¿aceptamos bloqueo de todos ante un rechazo y cómo se resuelve? ¿Orden por destino o global multilocal? | Equipo, DN-01/DN-04; F-03 y aclaraciones de G. |
| 7 | ¿Un medio por venta o pagos divididos? ¿Hay vuelto? Para devoluciones: ¿mismo local, parciales, plazo o sin plazo, aptos/no aptos, medio e importe del reintegro? | Equipo, DN-05/DN-07; F-04/F-05. Los datos históricos se preservan desde F-04. |
| 8 | ¿Aceptamos R-01 a R-04 y State/Strategy con las precisiones de B.3? ¿Qué convenciones de períodos y faltantes de costo adoptamos? ¿Quién confirma instrucciones, artefactos y fecha de entrega? | Equipo, DN-03/DN-06/DN-09/DN-11; capturar datos antes de F-02/F-03 y cerrar reportes antes de F-06. |

Estas preguntas concretan E6, no trasladan decisiones técnicas rutinarias al docente. No se solicita aprobar una implementación inexistente; se entrega la base para decidir antes de autorizarla.

## G. Cuestiones que requieren confirmación docente

No se contactó al docente ni se enviaron mensajes a terceros. Distinguir aclaración de evaluación y permiso tecnológico: las fuentes no establecen un trámite general de autorización para usar web.

| ID | Consulta concreta y motivo | Estado / momento límite |
| --- | --- | --- |
| G-01 | ¿La integración mínima de compras puede ser registro manual con ingreso controlado al CD? ¿“Resultado económico” admite margen estimado con último costo declarado o exige otra valuación/gastos? E1/E6 no detalla el proceso; E5 sí habla de margen estimado. | Aclaración académica relevante, DN-03/DN-09. Antes de F-02 para capturar datos correctos; no bloquea catálogo. |
| G-02 | ¿E2.3 exige una orden que reúna varios locales o admite una orden por destino que consolide varias necesidades? Mostrar ambos ejemplos para evitar confundir origen del pedido y origen físico. | Interpretación del alcance, DN-04. Antes de F-03. |
| G-03 | Si se busca multibulto: ¿qué significa remito Verificado con recepciones parciales/rechazadas? Si se elige 1:1 para entrega: ¿es suficiente para el ciclo evaluado? E4.1 no fija cardinalidad ni verificación parcial. | Consulta condicionada al alcance escogido, DN-01. Antes de F-03. No habilita a omitir ninguna de las dos verificaciones mientras se espera. |
| G-04 | ¿“Administrar” debe demostrar baja física SQL o se acepta baja administrativa preservando referencias? A aborda ABMC; E2 no define bajas. | Expectativa de evaluación, DN-08. Antes del cierre de administración persistente en F-02; no bloquea alta/consulta/modificación F-01. |
| G-05 | ¿Existe una instrucción de interfaz, dependencias o separación de código que no esté en el PDF? Presentar opción elegida y cómo quedan POO/Python visibles. | Verificación de instrucciones, DN-10. Sin regla concreta, no afirmar que GUI/framework está prohibido ni exigir permiso por ausencia de material. Si aparece restricción incompatible, resolver antes de implementar esa presentación. |
| G-06 | ¿Hay rúbrica de patrones/reportes, documentación, formato/fecha de entrega o demostración desde distintos locales que no esté disponible? | Obtener instrucciones, DN-11. Topología antes de F-02 si afecta acceso; rúbrica cuanto antes, entrega antes de F-07. State/Strategy y los cuatro reportes ya tienen justificación; no se paralizan por una aprobación genérica inventada. |

La política detallada de devoluciones, identificadores comerciales y medios de pago corresponde al equipo salvo instrucción docente específica. E6 pide al grupo identificar reglas adicionales; E4 obliga a cumplir las que se establezcan. No hay evidencia para atribuir al docente una política particular de plazos o reintegros.

## H. Decisiones imprescindibles antes de F-01

**F-01 aún no está autorizado.** Este documento satisface la revisión solicitada, no reemplaza la autorización posterior de implementación (U §§8/10; P I F-00).

| Prioridad | Acuerdo mínimo para comenzar | Criterio observable de cierre |
| --- | --- | --- |
| 1 | Registrar aceptación de límites: backend exclusivamente Python, siete procesos, cinco validaciones, dos patrones y cuatro reportes; conservar base POO y pendientes por fase. | Equipo acepta el alcance; no se incorpora opción que requiera backend/SSR/BFF no Python. E1/E2/E4/E6; U §2. |
| 2 | DN-10 acordada; cerrar detalles de entorno y modalidad DN-11. | Registrar React + Vite, Flask y SQLite; fijar JS/TS/versiones y modalidad antes de crear entorno. Dominio independiente; implementación aún por autorizar. |
| 3 | Parte catálogo de DN-02: identidad producto/proveedor y normalización. | Tabla de códigos válidos/duplicados, alcance de unicidad y regla tras baja. |
| 4 | Parte base de DN-06 y DN-09: unidad, ubicación del mínimo, precio válido, moneda/escala y representación. | Atributos/validaciones de catálogo tienen reglas verificables sin suponer políticas de F-04/F-06. |
| 5 | Parte base de DN-08: operaciones iniciales e inactivos. | Alta/consulta/modificación y baja administrativa aceptadas como propuesta, o alcance F-01 limitado explícitamente mientras se confirma baja académica. |
| 6 | Autorizar implementación del incremento acordado, con decisiones anteriores registradas. | Nueva instrucción del usuario. No se deduce autorización por terminar F-00 ni por transcurso del tiempo. |

La aclaración docente es bloqueante de F-01 **sólo** si aparece una regla concreta que afecte sus decisiones. Multibulto, devolución, pagos y fórmulas finales no son bloqueantes de catálogo. Definir mínimos/identidad ahora no obliga a implementar reposición ni reportes ahora.

P I F-01 ya está alineada: catálogo Python, API Flask y vistas React, con persistencia en F-02. Una postergación de UI requeriría modificar expresamente ese incremento; no se construye consola como elección tácita.

## I. Decisiones diferibles

| Decisión | Parte que puede esperar | Último momento seguro y evidencia de salida |
| --- | --- | --- |
| DN-01 | Cardinalidad final, parciales, bloqueo y resolución de rechazos. | Antes del modelo/esquema logístico F-03; casos de doble verificación y multibulto aceptados. |
| DN-02 | Identificadores de remito/precinto/comprobante. | Antes de F-03/F-04 respectivamente; alcance de unicidad documentado. La identidad de catálogo no se difiere. |
| DN-03 | Compra/recepción y método de costo. | Antes de F-02; conservar datos que demandará el método económico. |
| DN-04 | Orden multilocal/por destino, reservas y parciales. | Antes de F-03; ejemplo multilocal y conservación de cantidades. |
| DN-05 | Medios, pagos divididos, vuelto y comprobante. | Antes de F-04; ajustar dataset y casos; no exigir un medio definitivo en F-01. |
| DN-06 | Umbral < o <= y alerta/déficit del reporte. | Antes de F-06 o de mostrar alertas si ocurre antes. Unidad y ámbito del mínimo ya definidos en F-01. |
| DN-07 | Plazo, aptitud, local y reintegro de devolución. | Capturar referencias/precio/costo originales antes de F-04; política completa antes de F-05. |
| DN-08 | Si se exige DELETE físico y reglas complementarias de reactivación. | Antes de cerrar F-02 o antes de ofrecer reactivación; no postergar integridad de referencias. |
| DN-09 | Fórmulas finales, empates y presentación de reportes. | Fechas/costos base antes de F-02; costo de preparación para R-04 antes de F-03; fórmulas y períodos antes de F-06. Moneda/escala del precio no se difiere. |
| DN-10 | Sólo JS/TS, versiones, contratos concretos y pruebas UI; arquitectura ya resuelta. | Entorno antes de F-01; contrato antes de su caso; no diferir ni reabrir frontend/framework ya acordados. |
| DN-11 | Formato de entrega y distribución final. | Concurrencia antes de F-02; artefactos/fecha al organizar entrega y antes de F-07. Obtener rúbrica temprano si cambia alcance. |

Ruta mínima recomendada tras aprobación: catálogo F-01 → compras/persistencia F-02 → logística y primer circuito F-03 → venta F-04 → devolución F-05 → reportes F-06 → integración F-07, manteniendo el orden de P I/L. Los acuerdos se cierran antes de la fase que los consume; no se permite diferir una decisión después de capturar datos indispensables.

Riesgos prioritarios para esa ruta:

| Riesgo / fuente | Probabilidad cualitativa, impacto y detección | Mitigación y reversibilidad |
| --- | --- | --- |
| Liberación sin doble verificación (E4.1; P K.2) | Media; crítico; se detecta intentando vender en cada combinación de estados. | Mantener el control conjunto en Python/transacción; T-11/T-12 futuros. Corregir después de vender puede exigir operación compensatoria. |
| Bloqueo indefinido de íntegros multibulto (P C.5) | Posible por política aún abierta; alto; escenario con un bulto íntegro y otro roto. | DN-01 antes de F-03, sin cambiar estados históricos. Reversible en diseño antes de datos. |
| Menor alcance de consolidación/compras/economía (E1/E2.3; P K.1) | Incertidumbre confirmada, probabilidad de rechazo no estimada; alto; contrastar ejemplos con docente. | G-01/G-02 antes de F-02/F-03. Corregir esquema temprano; no esperar a reporte final. |
| UI consume esfuerzo o oculta POO (A §§4/9; P E.2) | No estimable sin capacidades/plazo del equipo; alto para entrega; revisar responsabilidades e incremento. | Selección explícita y alcance visual acotado; mantener dominio independiente. Puede cambiar adaptador, con costo de rehacer presentación. |
| Doble fuente de saldo o importes multiplicados (P F.3, G.11) | Media; alto; reconciliar documentos y dataset. | Atomicidad, unidad de datos definida en Strategy y agregados separados. No añadir event sourcing. |
| Costo/historia faltante (E4.2; P F.6) | Media si se posponen datos; alto; cambiar precio/costo y volver a consultar. | Capturar valores/instantes antes de fase consumidora. Datos históricos nunca capturados pueden ser irrecuperables. |

No se asignan horas, fechas de entrega ni porcentajes de cobertura porque no constan en las fuentes.

## J. Estado de sincronización con PLANIFICACION_TP_POO.md

La edición documental fue autorizada por S y aplicada a P, D y R. Esta tabla distingue correcciones efectuadas y políticas que permanecen pendientes; no describe cambios futuros ya implementados en una aplicación.

| Área de P | Estado | Alcance |
| --- | --- | --- |
| Cabecera/0, RT-07 y N | Aplicado | Fuentes actuales, autoridad académica separada del alcance del agente y sincronización de los tres documentos, sin implementación. |
| RT-05, D/E, DN-10 y ADR-001 | Aplicado | React + Vite/API Flask Python/SQLite, mismos AC-01 a AC-07 que R/D. Sin permiso académico general inventado ni aval atribuido. |
| G.12/H, I F-01 a F-07, J y L | Aplicado | Vistas React/API, pruebas de contrato y navegador, proxy de desarrollo y build servido por Python. No consola como base. |
| C.6/G.11 | Precisión de diseño aplicada | Strategy usa un conjunto definido de cobros/reintegros; ventas netas calculadas aparte para evitar multiplicación líneas×cobros. Patrón sigue propuesto. |
| F.5/K.2 | Aplicado | OneDrive/sincronización no verificados; precaución condicional. |
| RB-17/G.2/G.9 | Clasificación precisada | Principio genérico de control es explícito; procedimientos de compra/devolución siguen en DN-03/DN-07, sin remito logístico obligatorio para ambos. |
| Cardinalidades, consolidación y políticas | Pendiente de acuerdo | DN-01 a DN-09 conservan alternativas, recomendaciones y fases. No elegir 1:1, pagos divididos, costos/plazos por sincronizar arquitectura. |
| DN-11 y entrega | Pendiente | Modalidad, concurrencia, cuentas si fueran necesarias y rúbrica/artefactos. |

Se conservan RF-01 a RF-21, siete procesos, cinco validaciones, modelo base y roadmap. No se implementó ningún caso ni se instaló herramienta.

## K. Checklist de cierre de F-00

### K.1 Entregable de análisis solicitado

- [x] Leídos completamente tema3.pdf, AGENTS.md y PLANIFICACION_TP_POO.md; contrastadas las dos páginas del original visualmente y por extracción.
- [x] Separadas obligaciones E, reglas académicas A, restricciones U, propuestas e interpretaciones/supuestos.
- [x] Contrastados siete procesos, cinco validaciones, integración de compras/inventario, doble verificación e historia inmutable.
- [x] Revisados POO, State/Strategy y cuatro reportes distintos, sin reemplazar el modelo coherente.
- [x] Evaluadas A consola, B web renderizada en Python, C API Python + frontend independiente y D escritorio con los criterios pedidos.
- [x] DN-10 acordada: React + Vite, API Flask Python y SQLite; AC-01 a AC-07 sincronizados.
- [x] DN-01 a DN-11 analizadas con problema/origen, alternativas y balance, recomendación, impacto, fases, responsable y prioridad/límite.
- [x] Identificadas políticas adicionales de compras, devoluciones, multibulto y multirremito, sin atribuirlas al docente.
- [x] Preguntas humanas y aclaraciones docentes documentadas; cortes antes de F-01 diferenciados de decisiones posteriores.
- [x] Sincronización autorizada de P/D/R aplicada; políticas no acordadas siguen pendientes.
- [x] Verificados al cierre enlaces locales, tablas Markdown, once DN y secciones A a K.
- [x] Control final de las tres documentaciones y preservación de AGENTS.md/tema3.pdf registrado.

### K.2 Acuerdos para habilitar implementación

- [ ] Equipo/usuario acepta límites y decisiones de H, con responsables identificados.
- [x] Interfaz React + Vite/API Flask/SQLite acordada para planificación por S.
- [ ] Se fijan JS/TS, versiones compatibles y modalidad inicial DN-11 antes de implementar.
- [ ] Se registran políticas mínimas de catálogo y representación monetaria.
- [ ] Si aparece restricción académica concreta, se resuelve su impacto antes de implementar lo afectado.
- [ ] Usuario autoriza iniciar F-01. Esta revisión no contiene tal autorización.

**Cierre diferenciado:** el trabajo documental puede terminar con acuerdos pendientes visibles. El cierre operativo de F-00 y el inicio de F-01 dependen de los ítems aún pendientes de K.2; sólo DN-10 fue resuelta por S. Las preguntas de G y decisiones de I conservan sus propios límites y no bloquean fases ajenas.

### K.3 Evidencia de verificación de la sincronización

Los controles de elaboración inicial son históricos. En esta edición se contrastan P/D/R, acuerdos AC-01 a AC-07, DN-10, ADR y pendientes por fase; se revisan enlaces actuales, tablas, secciones y diff. Se editan únicamente las tres documentaciones.

Fuentes protegidas: AGENTS.md (SHA-256 85D78E7F375CDD38228EC8DE3B86741BB3C63732DB23ACA03F9A1D3D0EEAE3C7) y docs/tema3.pdf (6D0C46624D97402BE7A7B9CC59F7C11BD96741D4D63885E4B6855755904FABC6). Sus huellas deben permanecer intactas. No se registran huellas cruzadas de documentos editados como si siguieran siendo originales inmutables.

Control documental ejecutado mediante Python de lectura: 7 acuerdos AC idénticos en los tres documentos, 11 DN, 8 fases y catálogo completo RF/RB/RT/RNF/T preservado. Verificados 51 tablas y 14 enlaces locales; sin espacios finales ni cercos desbalanceados. Revisado diff y git diff --check sin errores de formato. Inventario limitado a las tres documentaciones y las dos fuentes protegidas; huellas de AGENTS.md/tema3.pdf intactas. No se ejecutaron aplicación, suite, build o instalaciones ni se afirma renderizado Markdown/Mermaid. No se atribuye aceptación docente.

## L. Decisiones aprobadas para F-02 (21/10/2026)

El usuario aprobó las propuestas concretas de DN-03, DN-09 y DN-11. Reemplazan las alternativas abiertas de esas tres decisiones; el resto de las DN conserva su estado. Las consultas docentes G-01 y G-06 siguen abiertas y pueden ampliar el alcance.

### L.1 DN-03. Compra, ingreso al CD y costo de referencia

- Compra manual: proveedor activo, el CD, al menos una línea y, por línea, producto activo sin repetir, cantidad entera positiva y costo unitario positivo en centavos.
- El borrador se arma en el formulario; Python registra la compra sólo al confirmarla. No hay borradores persistidos ni borrado físico de compras.
- La confirmación ingresa todas las cantidades como disponibles en el CD en una única transacción: compra, detalles, existencias y movimientos. No hay recepciones parciales. Para compras externas no se usan remito ni bulto.
- Una compra confirmada no se modifica ni se vuelve a confirmar; un fallo revierte todo.
- Costo de referencia: costo unitario de la última compra confirmada del producto, ordenada por instante de confirmación e identificador. Se calcula al consultar y se copia en los documentos que lo usan. Un producto sin compras no tiene costo: se informa, nunca se asume cero.
- Fuera de alcance: pagos a proveedores, notas de crédito, devoluciones a proveedor, costo promedio, FIFO y fecha de factura del proveedor.

### L.2 DN-09. Importes, fechas y resultado económico

- Una moneda (ARS), importes enteros en centavos; la API intercambia texto decimal con hasta dos decimales.
- Redondeo sólo de presentación, a dos decimales, con `ROUND_HALF_EVEN` de `Decimal`, si un cálculo produce fracciones.
- Instantes ISO 8601 con desplazamiento, en America/Buenos_Aires, asignados por el backend al confirmar.
- Períodos con inicio incluido y fin excluido en esa zona; período invertido o vacío es un error de datos.
- La devolución afecta su propio período sin reescribir la venta.
- Margen comercial estimado = venta neta − costo de referencia de las unidades netas vendidas. Compras y caja se informan aparte; no incluye gastos, impuestos ni pagos a proveedores.
- Un rechazo logístico se informa como valor bloqueado, no como merma.

### L.3 DN-11. Modalidad operativa y simultaneidad

- Una instalación local: un proceso Flask, un archivo SQLite y el navegador en `127.0.0.1`. CD y locales son ubicaciones lógicas; sin cuentas, red, despliegue ni sincronización.
- Un operador, posiblemente con varias pestañas. Cada escritura se valida y confirma dentro de una transacción; un conflicto se rechaza sin efectos parciales.
- Ruta de la base configurable con la variable de entorno `TP_DAO_DB`. Por defecto `%LOCALAPPDATA%\TP-DAO\tp_dao.db`, fuera de la carpeta sincronizada; el archivo no se versiona.
- Las pruebas usan bases temporales y nunca la base real.
- Entrega: build servido por Flask en `http://127.0.0.1:5000/` con instrucciones verificadas. Fecha, integrantes y formato quedan pendientes.

## M. Decisiones aprobadas para F-03 (21/10/2026)

El usuario aprobó las propuestas concretas de DN-01, DN-02 (identificadores logísticos) y DN-04, incluida la anulación de un bulto Preparado (opción recomendada). Las consultas docentes G-02 (orden multilocal) y G-03 (suficiencia de un remito por bulto) siguen abiertas y pueden ampliar el alcance.

### M.1 DN-01. Remito, bulto y doble verificación

- Un remito por bulto; una orden puede generar varios bultos.
- Ciclo con State: Preparado → Precintado → En tránsito → Recibido → Verificado o Rechazado, más Anulado sólo desde Preparado. `Bulto` es el contexto, `EstadoBulto` una ABC y cada estado concreto acepta o rechaza `precintar`, `despachar`, `recibir`, `verificar` y `anular`. Verificado, Rechazado y Anulado son finales.
- Recepción en el local destino: el receptor informa el precinto leído y si está intacto. Precinto roto o número distinto del registrado: Recibido y Rechazado en la misma operación, sin habilitar stock.
- Doble verificación: «verificar bulto» (Recibido conforme → Verificado) y luego «verificar remito» (Emitido → Verificado, sólo con su bulto Verificado). Recién entonces el stock pasa a disponible en el local. El remito tiene estados simples Emitido, Verificado y Rechazado, sin State.
- Historial inmutable de eventos (secuencia, estado anterior y nuevo, instante, motivo), protegido también en SQLite.
- Diferencias de contenido entre remito y recepción quedan fuera de F-03.

### M.2 DN-02. Identificadores logísticos

- Bulto `B-000001` y remito `R-000001`, generados por el sistema, secuenciales y únicos.
- Precinto: número del sello físico ingresado al precintar; texto único en todo el sistema sin distinguir mayúsculas y nunca reutilizable.
- Orden de reposición: identificador numérico.

### M.3 DN-04. Necesidades, consolidación y reserva

- Necesidad de un local activo, producto activo y cantidad entera positiva; estados Pendiente y Consolidada. Sin generación automática desde mínimos.
- Orden por destino: un CD origen y un local destino; consolida necesidades pendientes completas de ese local, suma por producto y conserva qué necesidad aportó cada cantidad.
- La reserva se hace al preparar el bulto: DISPONIBLE → RESERVADO en el CD, sin superar lo pendiente de la orden ni lo disponible. Una línea puede repartirse en varios bultos; la orden queda Completa cuando no hay pendientes. Anular un bulto Preparado libera su reserva y su cantidad vuelve a quedar pendiente.
- Recorrido: despacho RESERVADO (CD) → EN_TRANSITO (local destino); recepción EN_TRANSITO → PENDIENTE; verificación del remito PENDIENTE → DISPONIBLE; rechazo EN_TRANSITO → RECHAZADO en custodia, sin merma automática. Cada paso deja movimientos con el bulto como origen.
- Cada línea del bulto copia el costo de referencia al preparar (DN-09, para R-04); si no hay costo, queda informado como faltante.

## N. Decisiones aprobadas para F-04 (21/10/2026)

El usuario aprobó la propuesta de F-04 completa: DN-05, la numeración del comprobante (DN-02), la clave de operación contra envíos repetidos (RB-10) y los datos que F-04 debe guardar para DN-07. La consulta docente sobre el formato del comprobante sigue abierta.

### N.1 Venta

- La registra un local activo (nunca el CD), con una o más líneas de producto activo, cantidad entera positiva y sin productos repetidos.
- Sólo descuenta stock DISPONIBLE del local; una línea insuficiente impide confirmar toda la venta.
- Borrador en el formulario; Python confirma en una única transacción venta, líneas, salida de stock, cobros, caja y comprobante.
- Precio unitario: el vigente del catálogo al confirmar, sin modificación manual. Promociones y listas de precios quedan fuera.
- Una venta confirmada no se modifica ni se anula; su reversión es la devolución (F-05).

### N.2 Cobros y medios (DN-05)

- Uno o más cobros por venta, un medio distinto por cobro, cuya suma debe ser exactamente el total. Sin ventas pendientes, crédito ni cuentas corrientes.
- Sin vuelto: se registra el importe aplicado a la venta.
- Medios fijos precargados: Efectivo, Débito, Crédito y Transferencia; consultables, sin administración desde la pantalla ni integración bancaria.
- Cada cobro genera un movimiento de caja de ingreso por local y medio; los reintegros de F-05 serán egresos.

### N.3 Comprobante (DN-02)

- Comprobante interno no fiscal, uno por venta, con número global secuencial `CV-00000001`.
- Contiene número, local, instante, líneas con precio unitario y subtotal, total, cobros por medio y moneda.
- Reconsultarlo o reimprimirlo no registra otra venta; se imprime desde el navegador, sin PDF.

### N.4 Envío repetido (RB-10)

- El formulario genera una clave única por borrador (`clave_operacion`). Si Python recibe una clave ya registrada, devuelve la venta existente sin crear otra; la base la guarda con `UNIQUE`.

### N.5 Datos para devoluciones (DN-07)

- Cada línea guarda su número, precio unitario y costo de referencia del momento de la venta (DN-03); los cambios posteriores no los alteran (RB-12).
- Los cobros conservan su medio. El reparto de un reintegro entre medios de una venta con cobros divididos se define en DN-07 antes de F-05.

## O. Decisiones aprobadas para F-05 (29/10/2026)

El usuario aprobó la política DN-07 con las opciones recomendadas: sin plazo, aptitud por línea, reparto del reintegro elegido por el cajero y reintegro al precio completo. Reemplaza las alternativas abiertas de DN-07; la devolución comercial sigue siendo un proceso distinto del rechazo logístico.

### O.1 Devolución

- Refiere a una venta registrada y se recibe en el mismo local de esa venta, que debe estar activo. No hay plazo: se acepta mientras la línea tenga cantidad sin devolver.
- Una o más líneas de la venta, sin repetir, con cantidad entera positiva y un motivo escrito. La cantidad devuelta acumulada de cada línea no supera la vendida (RB-11); se admiten devoluciones parciales sucesivas.
- Una devolución confirmada no se modifica ni se anula. La venta original no se reescribe: la devolución queda en su propio instante (DN-09).
- Python confirma en una única transacción la devolución, sus líneas, los ingresos de stock, los reintegros y los egresos de caja. Una devolución inválida no cambia datos.

### O.2 Aptitud y stock

- El cajero indica por línea si la mercadería es apta. Esa revisión en el mostrador es el control exigido por RB-17 y no requiere remito ni bulto.
- Apta: ingresa como DISPONIBLE en el local. No apta: ingresa como BLOQUEADO, en custodia y no vendible; no hay un proceso posterior para esas unidades en F-05.
- Cada línea deja un movimiento de stock con causa DEVOLUCION y la línea de la devolución como documento.

### O.3 Reintegro y caja

- Importe por línea = cantidad × precio unitario histórico de la línea vendida, sea apta o no (RB-12).
- El cajero reparte el total entre los medios cobrados en la venta: un medio distinto por reintegro, suma exacta igual al total, y en cada medio no más que lo cobrado con él menos lo ya reintegrado. Así la caja de un local y medio no queda negativa por reintegros.
- Cada reintegro genera un movimiento de caja de egreso en el local y medio del reintegro.

### O.4 Identificación y envío repetido

- Identificador numérico secuencial; se muestra como `DV-00000001`.
- Igual que la venta, el formulario envía una `clave_operacion` única por borrador; una clave ya registrada devuelve la devolución existente sin efectos nuevos (RB-10).

## P. Decisiones adoptadas para F-06 (01/11/2026)

El usuario pidió empezar F-06 sin otra ronda de decisiones. Se adoptan las propuestas de la planificación (P G.11, F.6 y C.6) y las recomendaciones de DN-06 y DN-09; pueden revisarse antes de cerrar la fase. El formato de salida (sólo pantalla, PDF o CSV) se decide antes de la pantalla de F-06.3. La consulta docente G-01 sobre el margen estimado sigue abierta.

### P.1 Criterios comunes

- Los reportes consultan operaciones confirmadas en memoria y no modifican stock, caja ni documentos.
- Período: fechas con inicio incluido y fin excluido en la zona acordada; la fecha de inicio debe ser anterior a la de fin. Cada operación cuenta en la fecha de su instante: una devolución afecta su propio período, no el de la venta.
- Importes exactos en centavos; las magnitudes netas pueden ser negativas cuando lo devuelto en un período supera lo vendido en él.
- Un costo faltante se informa: nunca se toma como cero.

### P.2 R-01 Ventas, cobros e ingresos netos (Strategy)

- Total de ventas, de devoluciones y venta neta del período y local, calculados aparte desde los documentos.
- La agrupación trabaja siempre sobre el mismo conjunto de hechos: los movimientos de caja (cobros y reintegros) con fecha, local y medio. `ReporteVentas` delega la clave del grupo en una `EstrategiaAgrupacion` elegida desde afuera: por día, por local o por medio de pago.
- Ventas y devoluciones no se reparten entre medios. Como toda venta se cobra completa y todo reintegro cubre su devolución en el mismo instante y local, el ingreso neto total coincide con la venta neta.

### P.3 R-02 Productos más vendidos y margen estimado

- Por producto: unidades vendidas menos devueltas, importe neto a precios históricos, costo neto con el costo de referencia histórico de cada línea (la devolución revierte el costo de la línea original) y margen estimado = importe neto − costo neto.
- Ranking por unidades netas descendentes y, ante empate, por identificador de producto ascendente.
- Si a un producto le falta el costo en alguna línea, su costo y su margen no se informan y el margen total tampoco; el reporte lista esos productos.

### P.4 R-03 Existencias, mínimos y faltantes (DN-06)

- Por ubicación (local o CD) y categoría opcional: saldo en cada condición, mínimo configurado, déficit = máximo entre mínimo − disponible y cero, y alerta cuando el disponible es menor o igual que el mínimo.
- Incluye los productos con saldo en la ubicación y los que tienen mínimo configurado aunque nunca tuvieron stock. Sin mínimo configurado no hay déficit ni alerta; el CD no tiene mínimos.

### P.5 R-04 Rechazos logísticos

- Período por la fecha del rechazo, con filtros opcionales de local destino y producto.
- Por bulto rechazado: remito, destino, fecha, motivo, unidades y valor bloqueado con el costo de referencia guardado al preparar el bulto. Por local: bultos recibidos y rechazados en el período, unidades y valor bloqueado. Un bulto cuenta una sola vez aunque tenga varias líneas o eventos.
- El valor bloqueado no es una merma ni una pérdida definitiva. Si falta un costo, ese valor no se informa.
