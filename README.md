# TP DAO 2026 — catálogo, compras, logística CD–locales, ventas, devoluciones y reportes en SQLite (F-07.2)

React + Vite y API Flask Python permiten registrar, consultar, modificar y desactivar lógicamente categorías, productos, proveedores y locales del catálogo POO, y configurar mínimos por producto/local. Las ubicaciones distinguen Locales y Centro de Distribución (CD). El CD se puede registrar, consultar y editar, pero su baja queda bloqueada hasta aprobar una política de reemplazo. `GET /api/health` sigue devolviendo HTTP 200 y `{"status":"ok"}` como comprobación técnica de disponibilidad.

Todo se guarda en SQLite mediante `sqlite3` y SQL parametrizado y se conserva al reiniciar Flask (F-02.1). Sobre ese catálogo están implementados:

- **Compras (F-02):** compras a proveedores que ingresan su stock como disponible en el CD, con movimientos trazables y costo de referencia por producto.
- **Reposición y logística (F-03):** necesidades de los locales consolidadas en órdenes por destino, bultos con patrón State, remito, precinto, despacho, recepción y doble verificación antes de habilitar stock en el local, o rechazo por precinto roto.
- **Ventas (F-04):** ventas multilínea en un local con cobros divididos por medio de pago, caja por local y medio, comprobante interno imprimible y protección contra envíos repetidos.
- **Devoluciones (F-05):** devoluciones parciales de una venta en su local, con aptitud por línea (lo apto vuelve a estar disponible y lo no apto queda bloqueado) y reintegro repartido entre los medios cobrados, que egresa de la caja.
- **Stock por ubicación:** saldos por condición y movimientos de cada ubicación, con su documento de origen.
- **Reportes (F-06.1 a F-06.3):** cálculo de los reportes R-01 a R-04 con el patrón Strategy para agrupar ventas y caja, consultables por la API y en la vista Reportes.

Los mínimos siguen siendo configuración administrativa: no generan reposición automática; sólo el reporte R-03 los compara con el stock. No hay eliminación física, reactivación, relaciones producto–proveedor, autenticación ni ORM. El estado frente a la planificación está en «Alcance actual frente a la planificación», al final de este archivo.

## Estructura

```text
backend/
  __init__.py          fábrica Flask y servido del frontend compilado
  api.py               Blueprint /api y endpoint técnico de salud
  api_catalogo.py      HTTP/JSON de maestros y configuración de mínimos
  api_compras.py       HTTP/JSON de compras, existencias, saldos y movimientos
  api_logistica.py     HTTP/JSON de necesidades, órdenes, bultos y remitos
  api_ventas.py        HTTP/JSON de ventas, comprobante, medios de pago y caja por local
  api_devoluciones.py  HTTP/JSON de devoluciones, reintegros y lo devolvible de una venta
  api_reportes.py      HTTP/JSON de sólo lectura de los reportes R-01 a R-04
  api_comun.py         errores, validación, JSON comunes, carga y guardado compartidos
  dominio/
    __init__.py        clases del catálogo y excepciones de dominio
    catalogo.py        objetos, registro en memoria y validaciones
    compras.py         Compra, DetalleCompra y RegistroCompras con costo de referencia
    inventario.py      Inventario, saldos por condición y MovimientoStock
    fechas.py          zona horaria acordada e instante actual
    errores.py         ConflictoOperacionError para estados de documentos y stock
    reposicion.py      necesidades, órdenes de reposición por destino y su registro
    logistica.py       Bulto con patrón State, estados, eventos, Remito y su registro
    ventas.py          Venta, DetalleVenta, Cobro, MedioPago, Comprobante y RegistroVentas
    caja.py            Caja y MovimientoCaja por local y medio de pago, con ingresos y egresos
    devoluciones.py    Devolucion, DetalleDevolucion, Reintegro y RegistroDevoluciones
    reportes.py        Periodo, R-01 con patrón Strategy (ReporteVentas y sus agrupaciones) y R-02 a R-04
  persistencia/
    __init__.py        funciones públicas de acceso a datos
    base_datos.py      conexión, esquema, ruta y transacciones SQLite
    catalogo_sqlite.py carga del catálogo y guardado de cada maestro
    compras_sqlite.py  carga y guardado de compras
    inventario_sqlite.py saldos y movimientos de stock
    logistica_sqlite.py necesidades, órdenes, bultos, eventos y remitos
    ventas_sqlite.py   ventas, líneas, cobros y movimientos de caja
    devoluciones_sqlite.py devoluciones, sus líneas y reintegros
  requirements.txt     dependencia de ejecución Python
  requirements-dev.txt dependencia de pruebas
frontend/
  index.html
  src/
    main.jsx           punto de entrada de React
    App.jsx            navegación por grupos con ruta en el hash, datos consultados y coordinación de las vistas
    SeccionCatalogo.jsx filtros, consulta, edición y confirmación de baja
    SeccionMinimos.jsx configuración activa y consulta histórica por producto/local
    SeccionCompras.jsx borrador de compra con líneas, confirmación y compras registradas
    SeccionLogistica.jsx carga de necesidades, órdenes, bultos y remitos y operaciones de a una
    PanelReposicion.jsx necesidades de los locales y consolidación de órdenes
    PanelBultos.jsx    preparación, acciones por estado, doble verificación e historial
    SeccionStock.jsx   saldos por condición, costo de referencia y movimientos por ubicación
    SeccionVentas.jsx  venta por local con cobros, ventas registradas y caja por medio
    SeccionDevoluciones.jsx devolución de una venta con aptitud, reintegros por medio y devoluciones del local
    SeccionReportes.jsx filtros y presentación de los reportes R-01 a R-04 calculados por Python
    ComprobanteVenta.jsx comprobante interno en pantalla y copia para imprimir
    importes.js        importes ARS en centavos con BigInt para las estimaciones del borrador
    etiquetas.js       textos de estados y condiciones devueltos por Python
    FormularioCatalogo.jsx formularios y consultas de inactivos sin edición
    api.js             cliente fetch, errores y cancelación
    styles.css         presentación responsive
    fonts/             IBM Plex Sans local (woff2) y su licencia OFL
  vite.config.js       proxy transparente y configuración de desarrollo
  .env.example         ejemplo público de configuración
  package.json
  package-lock.json
tests/test_api.py      pruebas HTTP y de estáticos con pytest
tests/test_catalogo.py pruebas de dominio e independencia de frameworks
tests/test_api_catalogo.py contratos HTTP, memoria y aislamiento
tests/test_proveedores.py invariantes y códigos históricos de proveedores
tests/test_api_proveedores.py contratos HTTP y concurrencia de proveedores
tests/test_ubicaciones.py invariantes de ubicaciones y cardinalidad del CD
tests/test_api_ubicaciones.py contratos HTTP, aislamiento y concurrencia de ubicaciones
tests/test_minimos.py  reglas y relación producto/local encapsulada
tests/test_api_minimos.py contratos, precisión JSON, aislamiento y concurrencia
tests/test_bajas.py    estados, referencias, mínimos e historial de códigos
tests/test_api_bajas.py contratos de baja, filtros, aislamiento y concurrencia
tests/test_persistencia_catalogo.py reinicio, restricciones SQL, rollback y fallos de guardado
tests/test_compras.py  dominio de compras, inventario y costo de referencia
tests/test_api_compras.py contratos, reinicio, fallos, concurrencia y esquema de compras
tests/test_logistica.py consolidación, ciclo del bulto, doble verificación y transiciones
tests/test_api_logistica.py contratos, reinicio por etapa, fallos, migración y esquema logístico
tests/test_ventas.py   ventas, cobros divididos, caja, comprobante y clave de operación
tests/test_api_ventas.py contratos, reinicio, clave repetida, fallos, concurrencia, esquema y migración de ventas
tests/test_api_devoluciones.py contratos, reinicio, clave repetida, fallos, concurrencia, esquema y migración de devoluciones
tests/test_devoluciones.py devoluciones parciales, aptitud, reintegros por medio y clave de operación
tests/test_reportes.py R-01 a R-04 sobre datos de control, intercambio de estrategias y reportes sin efectos
tests/test_api_reportes.py parámetros, JSON, importes negativos, reinicio y reportes sin efectos
tests/test_integracion.py escenarios integrales feliz, de bloqueo, de rechazo y transaccional con el dataset de control
tests/test_restricciones.py backend sólo Python, dependencias declaradas y SQL con parámetros
tests/conftest.py      base temporal por aplicación; los tests nunca usan la base real
pytest.ini
docs/                  enunciado y planificación previa, conservados
```

La presentación HTTP vive en `backend/api.py` y los módulos `backend/api_*.py`; la creación/configuración de Flask, en `backend/__init__.py`; el dominio, en `backend/dominio`; el acceso a SQLite, en `backend/persistencia`. El dominio no importa SQLite ni Flask. Los imports HTTP se ejecutan al llamar a `create_app`, por lo que importar y usar el dominio no requiere Flask instalado. React captura datos y presenta respuestas de Python. Node ejecuta herramientas frontend; no hay backend, SSR, BFF, reglas ni persistencia en Node.

## F-01.1: contrato del catálogo en memoria

`Catalogo` registra objetos, asigna identificadores técnicos y permite consultar por identificador o código. `Categoria` mantiene código/nombre; `Producto` mantiene código/nombre, una referencia a categoría registrada y precio ARS. Los objetos colaboran con su catálogo para controlar unicidad también al modificarse directamente mediante sus métodos públicos.

Crear los registros mediante `Catalogo.crear_categoria` y `Catalogo.crear_producto`. Los identificadores son enteros positivos, secuenciales dentro de cada tipo y catálogo, y no se reasignan al editar. Desde F-02.1 se conservan entre ejecuciones porque las filas nunca se borran; no son globales entre tipos. La categoría debe ser la instancia registrada en ese mismo catálogo: una instancia externa con igual ID no es válida.

Los códigos y nombres son textos no vacíos, recortados en sus extremos. La comparación de códigos usa `casefold()`; conserva ceros iniciales y la escritura del código almacenado. La unicidad es por tipo, no por nombre. Los códigos pueden modificarse mediante las operaciones validadas; las búsquedas reflejan el código vigente. Desde F-01.6, también en categorías y productos, todos los códigos originales y reemplazados quedan reservados durante la vida del catálogo, incluso después de la baja.

Los precios de entrada son **textos en pesos ARS**: `"12"`, `"12.5"` o `"12.50"`. Se utiliza punto decimal, sin separadores de miles, signos ni notación científica. No se aceptan `float`, enteros u otros tipos como entrada para evitar ambigüedad entre pesos y centavos. Se rechazan cero, negativos y más de dos decimales, incluso `"1.230"`; no se redondea. Desde F-02.1 el máximo es `92233720368547758.07` (2⁶³−1 centavos), el mayor entero que SQLite guarda exactamente; un valor mayor se rechaza con 400. `precio_centavos` devuelve un entero exacto y `precio` devuelve texto con dos decimales. Conversión y formato utilizan enteros y cadenas, sin punto flotante ni dependencias adicionales.

Las propiedades de los objetos son de lectura; las modificaciones pasan por `modificar` o `cambiar_precio`. `Catalogo.modificar_categoria` recibe ID, código y nombre; `Catalogo.modificar_producto` recibe ID, código, nombre, categoría y precio. Validan todos los datos antes de cambiar el estado y conservan la misma instancia. Renombrar una categoría se refleja en los productos que la referencian. F-01.6 agrega `desactivar` y la propiedad de lectura `activo`; no hay reactivación ni eliminación física.

`obtener_categoria` y `obtener_producto` buscan por ID y producen `KeyError` si no existe. `buscar_categoria_por_codigo` y `buscar_producto_por_codigo` devuelven el objeto o `None`. Un tipo incorrecto produce `TypeError`; datos inválidos o categorías ajenas producen `ValueError`. Los duplicados producen `CodigoDuplicadoError`, subclase de `ValueError`, para que HTTP los distinga sin repetir la regla. Los listados son tuplas que protegen la colección; contienen las mismas referencias a objetos, no copias editables sin validación.

Ejemplo desde Python, con la raíz del repositorio como directorio actual:

```python
from backend.dominio import Catalogo

catalogo = Catalogo()
categoria = catalogo.crear_categoria("ALM", "Almacén")
producto = catalogo.crear_producto("001", "Arroz", categoria, "125.50")
assert producto.precio_centavos == 12550
assert catalogo.buscar_producto_por_codigo(" 001 ") is producto

catalogo.modificar_categoria(categoria.identificador, "COM", "Comestibles")
assert producto.categoria.nombre == "Comestibles"
producto.cambiar_precio("140.25")
assert producto.precio_centavos == 14025
```

Cada instancia de `Catalogo` tiene sus propios registros. El dominio puede usarse con Python estándar, sin instalar dependencias; pytest sigue siendo necesario para ejecutar sus pruebas.

## F-01.3: proveedores en el mismo catálogo

`Proveedor` protege su ID técnico inmutable, código comercial y nombre. `Catalogo.crear_proveedor(codigo, nombre)` asigna el siguiente ID de proveedores; `obtener_proveedor(id)`, `buscar_proveedor_por_codigo(codigo)` y `listar_proveedores()` mantienen los mismos contratos de consulta que categorías/productos. `modificar_proveedor(id, codigo, nombre)` y `Proveedor.modificar(codigo, nombre)` conservan la misma instancia y validan todos los datos antes de cambiarla. Las propiedades son de lectura.

Código y nombre son textos obligatorios recortados en los extremos. La unicidad del código es exclusiva de proveedores y usa `casefold()`; se conservan ceros iniciales y escritura. Se permiten nombres iguales con códigos distintos. No se requieren CUIT, contacto, dirección ni datos bancarios.

**Los códigos de proveedores no se reutilizan durante la vida del catálogo.** Se puede mantener el código vigente, incluso cambiar su capitalización, o sustituirlo por uno nunca registrado. El reemplazado queda reservado: no puede asignarse a otro proveedor ni recuperarse para el original. Las búsquedas por código consultan sólo el código vigente. Una operación inválida no reserva códigos ni consume IDs. El registro de códigos históricos pertenece a `Catalogo`, no al frontend ni al adaptador HTTP. F-01.6 extiende esta política a categorías y productos; ubicaciones ya la aplicaban desde F-01.4.

```python
proveedor = catalogo.crear_proveedor("0001", "Distribuidora")
catalogo.modificar_proveedor(proveedor.identificador, "0002", "Distribuidora Norte")
assert catalogo.buscar_proveedor_por_codigo("0002") is proveedor
assert catalogo.buscar_proveedor_por_codigo("0001") is None
# Un nuevo intento de asignar "0001" produce CodigoDuplicadoError.
```

## F-01.4: Locales y Centro de Distribución

`Ubicacion` representa ambos tipos mediante un atributo validado, sin herencia ni Singleton. Tiene ID técnico inmutable, código comercial y nombre obligatorios, y tipo inmutable `LOCAL` o `CD`. El tipo se recibe como texto, se recorta en sus extremos y sólo admite esos dos valores en mayúsculas. Código y nombre usan la normalización existente: recorte de extremos y comparación del código con `casefold()`, preservando ceros iniciales. Se permiten nombres iguales con códigos distintos.

`Catalogo.crear_ubicacion(codigo, nombre, tipo)` registra y asigna el siguiente ID entre todas las ubicaciones. `obtener_ubicacion(id)`, `buscar_ubicacion_por_codigo(codigo)` y `listar_ubicaciones()` conservan los contratos de consulta del catálogo. `modificar_ubicacion(id, codigo, nombre)` y `Ubicacion.modificar(codigo, nombre)` sólo cambian código/nombre, conservando la misma instancia, ID y tipo. Las propiedades son de lectura y los listados son tuplas.

El catálogo puede estar vacío, admite múltiples locales y **como máximo un CD por catálogo/aplicación**. `Catalogo` controla esa cardinalidad y la unicidad del código entre todos los locales y el CD. Un segundo CD produce `CentroDistribucionDuplicadoError`, derivada de `ValueError`; un código ocupado o histórico produce `CodigoDuplicadoError`. Los códigos reemplazados quedan reservados como en proveedores, incluso frente al intento de recuperarlos para la ubicación original. Las búsquedas por código sólo consideran el vigente.

Los datos inválidos y los conflictos se rechazan antes de cambiar el objeto o reservar códigos. Un alta fallida no consume ID ni la posibilidad de registrar el CD. Se puede editar administrativamente el CD existente. No se puede convertir Local en CD ni a la inversa. No se agregaron direcciones, personas ni operaciones logísticas; la configuración de mínimos de F-01.5 se detalla a continuación.

```python
local = catalogo.crear_ubicacion("0001", "Local Centro", "LOCAL")
cd = catalogo.crear_ubicacion("CD01", "Depósito central", "CD")
catalogo.modificar_ubicacion(local.identificador, "0002", "Local Norte")
assert local.tipo == "LOCAL"
assert catalogo.buscar_ubicacion_por_codigo(" cd01 ") is cd
# Registrar otro CD produce CentroDistribucionDuplicadoError.
```

## F-01.5: mínimos por producto/local

`Catalogo` encapsula un diccionario cuya clave es `(local_id, producto_id)` y cuyo valor es un entero no negativo. La relación no necesita una clase con identidad o ciclo de vida propios: sus reglas y las referencias registradas son responsabilidad del catálogo. No se creó `Existencia` ni se agregaron campos de saldo a productos o ubicaciones.

- `establecer_minimo(local_id, producto_id, minimo)` valida ambos IDs contra este catálogo, exige ubicación `LOCAL`, producto/local activos y entero no negativo, reemplaza el valor del par y devuelve el entero confirmado. Repetir la operación no agrega configuraciones.
- `obtener_minimo(local_id, producto_id)` valida las mismas referencias y devuelve `None` si no hay configuración, o el entero, incluido `0`.
- `listar_minimos(local_id)` valida el local y devuelve una tupla de pares `(producto registrado, minimo)` sólo de ese local, sin exponer el diccionario interno. Un local sin configuraciones devuelve `()`.

El mismo producto puede tener valores independientes en varios locales. Se rechazan negativos, `float` incluso como `1.0`, booleanos, textos y otros tipos. Una referencia inexistente produce `KeyError`; el CD se rechaza con `ValueError` tanto para consulta como para escritura. Un producto/local inactivo produce `ConflictoCatalogoError` al escribir; sus mínimos siguen siendo consultables. Validar todo antes de asignar evita cambios parciales. Los cambios administrativos de código/nombre no afectan la configuración porque se mantienen los IDs; las consultas muestran los datos actuales de los objetos.

```python
assert catalogo.obtener_minimo(local.identificador, producto.identificador) is None
catalogo.establecer_minimo(local.identificador, producto.identificador, 0)
assert catalogo.obtener_minimo(local.identificador, producto.identificador) == 0
catalogo.establecer_minimo(local.identificador, producto.identificador, 8)
assert catalogo.listar_minimos(local.identificador) == ((producto, 8),)
```

Convenciones confirmadas por el pedido para las fases que tengan existencias reales: **en el mínimo** significa disponible `<=` mínimo; **faltante**, disponible `<` mínimo; **déficit**, `max(mínimo - disponible, 0)`. Se aplicarán con mínimo configurado y existencia real. Hoy no se calculan ni se muestran esos indicadores, ni se toma ausencia de configuración como cero o un mínimo como cantidad disponible.

## F-01.6: bajas administrativas y referencias

`Categoria`, `Producto`, `Proveedor` y `Ubicacion` nacen con `activo=True`. Su propiedad `activo` es de lectura y el método `desactivar()` aplica las reglas del objeto. `Catalogo.desactivar_categoria(id)`, `desactivar_producto(id)`, `desactivar_proveedor(id)` y `desactivar_ubicacion(id)` buscan y devuelven la misma instancia después de desactivarla. Repetir una baja permitida conserva el resultado sin efectos adicionales. No hay setters de estado, cascadas ni reactivación.

| Entidad | Regla de baja y conservación |
| --- | --- |
| Categoría | Bloqueada si tiene cualquier producto activo asociado. Después de desactivar esos productos, puede desactivarse; se conservan sus referencias. |
| Producto | Permitida; conserva categoría, precio, identidad y todos sus mínimos. |
| Proveedor | Permitida; conserva identidad y datos. No se incorporaron compras ni relaciones nuevas. |
| Local | Permitida; conserva identidad, tipo y todos sus mínimos. |
| CD | **Bloqueada hasta aprobar una política de reemplazo.** Sigue existiendo como máximo un CD registrado por catálogo, no uno activo. |

Las entidades inactivas siguen en el registro y pueden consultarse por ID o por su código vigente. No admiten modificaciones administrativas, ni siquiera conservar los mismos datos mediante `modificar`; en productos tampoco se permite `cambiar_precio`. Una categoría inactiva no admite nuevos productos ni reasociaciones. Los mínimos de locales/productos inactivos siguen disponibles para lectura, pero no se pueden crear ni actualizar. Estos conflictos producen `ConflictoCatalogoError`, derivada de `ValueError`; HTTP los presenta como 409.

Todos los listados de maestros admiten `estado="activos"`, `"inactivos"` o `"todos"`; por defecto devuelven activos. Conservan el resultado como tupla de referencias registradas. Las reservas de códigos cubren los cuatro tipos, incluidos códigos originales, reemplazados e inactivos. Un código retirado tampoco puede recuperarse para su entidad original. Ninguna baja borra datos ni libera códigos o IDs.

## API HTTP/JSON de F-01.2 a F-01.6

La API valida el formato del transporte y delega creación, modificación, bajas, unicidad, referencias y precios al dominio. Los cuerpos de escritura deben ser objetos JSON con todos los campos indicados y sin campos adicionales. `id` técnico y `codigo` comercial son conceptos distintos. `PUT` reemplaza los campos editables completos y no acepta `activo`; el estado se cambia exclusivamente mediante el `PATCH` de baja. No hay `DELETE` de catálogo.

| Método y ruta | Entrada | Respuesta exitosa |
| --- | --- | --- |
| `GET /api/categorias` | Sin cuerpo | 200, `{"categorias": [...]}`. |
| `POST /api/categorias` | `codigo`, `nombre`: textos | 201, categoría; cabecera `Location` con su consulta. |
| `GET /api/categorias/<id>` | ID técnico en ruta | 200, categoría. |
| `PUT /api/categorias/<id>` | `codigo`, `nombre`: textos | 200, categoría actualizada, mismo ID. |
| `GET /api/productos` | Sin cuerpo | 200, `{"productos": [...]}`. |
| `POST /api/productos` | `codigo`, `nombre`, `precio`: textos; `categoria_id`: entero | 201, producto; cabecera `Location` con su consulta. |
| `GET /api/productos/<id>` | ID técnico en ruta | 200, producto. |
| `PUT /api/productos/<id>` | Los mismos cuatro campos del alta | 200, producto actualizado, mismo ID. |
| `GET /api/proveedores` | Sin cuerpo | 200, `{"proveedores": [...]}`. |
| `POST /api/proveedores` | `codigo`, `nombre`: textos | 201, proveedor; cabecera `Location` con su consulta. |
| `GET /api/proveedores/<id>` | ID técnico en ruta | 200, proveedor. |
| `PUT /api/proveedores/<id>` | `codigo`, `nombre`: textos | 200, proveedor actualizado, mismo ID. |
| `GET /api/ubicaciones` | Sin cuerpo | 200, `{"ubicaciones": [...]}`. |
| `POST /api/ubicaciones` | `codigo`, `nombre`, `tipo`: textos | 201, ubicación; cabecera `Location` con su consulta. |
| `GET /api/ubicaciones/<id>` | ID técnico en ruta | 200, ubicación. |
| `PUT /api/ubicaciones/<id>` | Únicamente `codigo`, `nombre`: textos | 200, ubicación actualizada, mismo ID y tipo. |
| `GET /api/ubicaciones/<id>/minimos` | ID del local | 200, `ubicacion` y lista `minimos` de configuraciones existentes. |
| `PUT /api/ubicaciones/<id>/minimos/<producto_id>` | Únicamente `minimo`: entero JSON | 200, ubicación, producto y mínimo confirmado; establece o reemplaza el mismo par. |
| `PATCH /api/categorias/<id>/estado` | Exactamente `{"activo":false}` | 200, categoría inactiva; 409 si tiene productos activos. |
| `PATCH /api/productos/<id>/estado` | Exactamente `{"activo":false}` | 200, producto inactivo con referencias conservadas. |
| `PATCH /api/proveedores/<id>/estado` | Exactamente `{"activo":false}` | 200, proveedor inactivo. |
| `PATCH /api/ubicaciones/<id>/estado` | Exactamente `{"activo":false}` | 200, local inactivo; 409 para CD. |

Los cuatro `GET` de colección admiten `?estado=activos`, `?estado=inactivos` o `?estado=todos`. La omisión equivale a `activos`; el formato de respuesta mantiene la clave de colección existente. Un filtro vacío, desconocido o repetido produce 400. `GET /api/<recurso>/<id>` sigue devolviendo 200 también para inactivos; inexistente sigue siendo 404.

Cada DTO de maestro incluye `"activo":true` o `false`, también la categoría anidada de un producto y el producto resumido en mínimos. El `PATCH` no acepta `true`, `0`, `"false"`, campos faltantes ni adicionales: produce 400 y no cambia el estado. Una baja repetida permitida devuelve 200 y el mismo DTO inactivo. El CD permanece activo ante cualquier intento de baja. El cambio de estado tampoco puede introducirse mediante `POST` o `PUT`.

Las dos rutas de mínimos siguen las ubicaciones/productos existentes y usan sus IDs. `GET` devuelve, por ejemplo:

```json
{
  "ubicacion": {"id": 1, "codigo": "L1", "nombre": "Centro", "tipo": "LOCAL", "activo": true},
  "minimos": [
    {"producto": {"id": 1, "codigo": "001", "nombre": "Arroz", "activo": true}, "minimo": 0}
  ]
}
```

Un producto registrado sin configuración **no tiene fila** en `minimos`; una lista vacía significa que ese local no tiene mínimos configurados. Un cero explícito sí tiene fila con `"minimo":0`. No se inventan configuraciones cero para completar productos ausentes. La UI cruza este listado con los productos del catálogo y muestra “Sin configurar” sólo después de una consulta exitosa.

`PUT` recibe `{"minimo":8}` y devuelve `{"ubicacion":{...},"producto":{"id":1,"codigo":"001","nombre":"Arroz","activo":true},"minimo":8}`. Devuelve 200 también al establecer por primera vez: es la asignación repetible de un recurso identificado por el par, no un alta con ID nuevo. Si el local o producto está inactivo, devuelve 409 sin cambiar el mínimo; el `GET` histórico conserva 200 e informa sus estados. No hay endpoint para borrar/desconfigurar el mínimo ni para consultar inventario.

El transporte HTTP admite mínimos entre `0` y `9007199254740991` (`2**53 - 1`), para conservar el entero exacto en JSON/JavaScript. Python mantiene enteros no negativos sin ese límite del cliente. El adaptador rechaza con 400 valores superiores, tanto al recibir como al serializar configuraciones creadas directamente desde Python, evitando redondeos silenciosos; el límite no cambia precios ni otros contratos. `true`, `1.0`, `"8"`, `null`, campos extra y JSON inválido producen 400. Un local/producto inexistente produce 404 y el CD produce 400. No se modifican configuraciones ante estos errores.

Para proveedores, alta y modificación reciben únicamente `{"codigo":"0001","nombre":"Distribuidora"}` y devuelven `{"id":1,"codigo":"0001","nombre":"Distribuidora","activo":true}`. Un código vigente duplicado o uno histórico reservado produce 409; no se serializan el catálogo, sus reservas ni atributos privados. Los campos faltantes, adicionales o de tipo incorrecto producen 400.

Ejemplo de alta de ubicación: `{"codigo":"0001","nombre":"Local Centro","tipo":"LOCAL"}`; respuesta: `{"id":1,"codigo":"0001","nombre":"Local Centro","tipo":"LOCAL","activo":true}`. Para el CD se usa `"tipo":"CD"`. El `PUT` recibe únicamente `{"codigo":"0002","nombre":"Local Norte"}`: enviar `tipo`, `id` o `activo`, aunque sean los valores actuales, produce 400 por campo no editable. La respuesta siempre incluye el tipo confirmado por Python.

El intento de registrar un segundo CD produce 409 JSON con `error.fields.tipo`; un código de ubicación duplicado o reservado produce 409 con `error.fields.codigo`. La API usa las excepciones del dominio, sin repetir esas reglas. Todas las operaciones y su serialización usan el mismo catálogo y bloqueo existentes.

Una categoría se representa como `{"id":1,"codigo":"ALM","nombre":"Almacén","activo":true}`. Un producto incluye su categoría actual y el precio decimal como texto:

```json
{
  "id": 1,
  "codigo": "001",
  "nombre": "Arroz",
  "activo": true,
  "categoria": {"id": 1, "codigo": "ALM", "nombre": "Almacén", "activo": true},
  "precio": "125.50",
  "moneda": "ARS"
}
```

Ejemplo de cuerpo para registrar o modificar un producto: `{"codigo":"001","nombre":"Arroz","categoria_id":1,"precio":"125.50"}`. No se recibe un objeto categoría inventado: Python busca la instancia registrada por ID. No se envían importes JSON numéricos ni atributos privados. Las respuestas se construyen desde el objeto realmente registrado, con código/nombre recortados y precio canónico.

| Estado | Significado |
| --- | --- |
| 400 | JSON mal formado, objeto/campos/tipos incorrectos o datos rechazados por el dominio. |
| 404 | Categoría/producto/proveedor/ubicación inexistente, incluida la categoría referida por un producto. |
| 409 | Código vigente/histórico reservado de cualquier maestro, segundo CD, edición o nueva asociación/configuración con inactivos, baja de categoría con productos activos o baja del CD. |
| 415 | Cuerpo no enviado como `application/json`. |
| 405 | Método no disponible; se conserva la cabecera `Allow`. |
| 500 | Fallo inesperado; respuesta genérica sin detalle interno ni éxito falso. |

Los errores usan `{"error":{"code":400,"message":"..."}}`, con `fields` opcional para señalar campos del formulario. Ejemplo de conflicto: `{"error":{"code":409,"message":"Ya existe una categoría con ese código.","fields":{"codigo":"Ya existe una categoría con ese código."}}}`. Las trazas y objetos internos no se serializan al cliente.

Los IDs de ruta enteros pero inválidos, como `0`, producen 400 por validación de dominio. Un entero positivo inexistente produce 404; rutas con segmentos que no coinciden con el conversor entero de Flask también producen 404 JSON.

## F-02.2: compras e ingreso al CD

Aplica DN-03, DN-09 y DN-11 aprobadas (sección L de `docs/DECISIONES_F00.md`).

`Compra` es un documento confirmado: se construye completo con proveedor, CD, instante y líneas, y no tiene operaciones de modificación. Crea sus `DetalleCompra` (composición) y valida todas las líneas antes de existir: al menos una, producto sin repetir, cantidad entera positiva y costo unitario en texto ARS con la misma regla que el precio (positivo, hasta dos decimales, sin `float`, máximo 2⁶³−1 centavos). El destino debe ser una ubicación de tipo CD.

`RegistroCompras.registrar` exige además proveedor y productos activos, pide al `Inventario` el ingreso y recién entonces guarda la compra; ante cualquier error no cambia nada. `costo_referencia(producto)` devuelve el costo unitario en centavos de la última compra del producto, ordenando por instante y luego por identificador, o `None` si nunca se compró. Se calcula al consultar; los documentos históricos conservan su costo aunque después cambien precios o estados.

`Inventario` es el único que modifica saldos, por (ubicación, producto, condición). Cada ingreso deja un `MovimientoStock` inmutable con instante, cantidad, condición de origen (ninguna) y destino (`DISPONIBLE`), causa `COMPRA` y la línea de compra que lo originó. Comprueba todos los saldos resultantes antes de aplicar alguno. Las seis condiciones del modelo ya están definidas; F-02 sólo usa `DISPONIBLE`.

El instante lo asigna el backend al confirmar, con precisión de segundos y desplazamiento fijo `-03:00` (America/Buenos_Aires). Argentina no aplica horario de verano desde 2009; el desplazamiento fijo evita agregar la dependencia `tzdata`, que `zoneinfo` necesita en Windows.

| Método y ruta | Cuerpo / resultado |
| --- | --- |
| `POST /api/compras` | `{"proveedor_id":1,"lineas":[{"producto_id":1,"cantidad":10,"costo_unitario":"1000"}]}`. 201 con la compra y `Location`. |
| `GET /api/compras` | `{"compras":[...]}` en orden de registro. |
| `GET /api/compras/<id>` | 200 con la compra; 404 si no existe. |
| `GET /api/ubicaciones/<id>/existencias` | `{"ubicacion":{...},"existencias":[{"producto":{...},"disponible":10,"costo_referencia":"1000.00"}]}`; `costo_referencia` es `null` si no hay compras, nunca cero. |
| `GET /api/ubicaciones/<id>/movimientos` | `{"ubicacion":{...},"movimientos":[{"id":1,"instante":"...","producto":{...},"cantidad":10,"condicion_origen":null,"condicion_destino":"DISPONIBLE","causa":"COMPRA","compra_id":1,"linea":1}]}`. |

La compra responde `{"id","proveedor","centro","instante","lineas":[{"linea","producto","cantidad","costo_unitario","subtotal"}],"total","moneda":"ARS"}`, con importes como texto de dos decimales. El CD no se envía: es el único registrado.

| Código | Compras |
| --- | --- |
| 400 | Formato inválido, con `fields` por línea (`lineas.2.cantidad`), cantidad mayor que 2⁵³−1 o contenido inválido según el dominio. |
| 404 | Proveedor o producto inexistente, con `fields` (`proveedor_id`, `lineas.N.producto_id`); compra o ubicación consultada inexistente. |
| 409 | Proveedor o producto inactivo, o ningún CD registrado. |
| 500 | Fallo al guardar: ni la compra ni el stock quedan en memoria o en la base. |

## F-03.1: dominio de reposición y logística

Aplica DN-01, DN-02 y DN-04 aprobadas (sección M de `docs/DECISIONES_F00.md`). F-03.2 agrega su persistencia y su API, y F-03.3 sus pantallas React.

- **Reposición.** `RegistroReposicion` registra necesidades de un local activo (producto activo, entero positivo) y las consolida en una `OrdenReposicion` con origen en el CD y un solo local destino. La orden compone un `DetalleReposicion` por producto, que suma las cantidades y conserva qué necesidades lo originaron. Asignado y pendiente se calculan desde los bultos no anulados; la orden pasa de Abierta a Completa sin un atributo que pueda desincronizarse.
- **State.** `Bulto` es el contexto y `EstadoBulto` una ABC cuyas operaciones (`precintar`, `despachar`, `recibir`, `verificar`, `anular`) se rechazan por defecto. Cada estado concreto (`Preparado`, `Precintado`, `EnTransito`, `Recibido`, `Verificado`, `Rechazado`, `Anulado`) redefine sólo las que admite y decide la transición. El bulto delega el mismo mensaje en su estado actual; no hay condicionales por estado fuera de las clases de estado. Un único método interno cambia el estado y agrega un `EventoEstadoBulto` de sólo lectura.
- **Doble verificación.** La recepción en el local destino compara el precinto leído con el registrado: roto o distinto deja el bulto Recibido y Rechazado en la misma operación y el remito Rechazado. Conforme, queda Recibido con el stock PENDIENTE. «Verificar» lleva el bulto a Verificado, y sólo después `Remito.verificar` habilita el stock como DISPONIBLE.
- **Inventario.** `Inventario` aplica cada operación como cambios de condición comprobados antes de modificar ningún saldo; un stock insuficiente produce `ConflictoOperacionError` sin efectos. `MovimientoStock` guarda condición de origen y de destino (una de las dos puede faltar en entradas y salidas), la causa (`COMPRA`, `PREPARACION`, `ANULACION`, `DESPACHO`, `RECEPCION`, `VERIFICACION`, `RECHAZO`) y el documento: la línea de compra o la línea de bulto. El despacho registra la salida de la reserva del CD y la entrada en tránsito al local, así que el total de unidades se conserva.
- **Identificadores.** `RegistroLogistica` numera bultos `B-000001` y remitos `R-000001`, emitiendo el remito al precintar, y rechaza un precinto ya usado sin distinguir mayúsculas. Cada línea del bulto copia el costo de referencia vigente al prepararlo.
- **Rechazo.** El rechazo mueve EN_TRANSITO → RECHAZADO directamente, porque ocurre en la misma recepción: el stock nunca pasa por una condición vendible ni intermedia.

## F-03.2: persistencia y API de reposición y logística

Cada operación guarda en una sola transacción todo lo que cambió: la necesidad, la orden con la consolidación de sus necesidades, o el bulto con su estado actual, eventos nuevos, remito y movimientos. Al iniciar, `cargar_estado` reconstruye catálogo, compras, reposición, logística e inventario en ese orden; los bultos se restauran desde su historial, que debe ser una cadena continua desde PREPARADO, sin repetir reservas ni traslados. Los mismos registros usan el bloqueo único de la aplicación.

| Método y ruta | Cuerpo | Resultado |
| --- | --- | --- |
| `POST /api/necesidades` | `{"local_id":2,"producto_id":1,"cantidad":6}` | 201 con la necesidad pendiente. |
| `GET /api/necesidades`, `GET /api/necesidades/<id>` | — | Necesidades con local, producto, estado y `orden_id`. |
| `POST /api/ordenes` | `{"local_id":2,"necesidad_ids":[1,2]}` | 201 con la orden: CD de origen, local destino, líneas por producto (solicitada, asignada, pendiente, necesidades) y bultos. |
| `GET /api/ordenes`, `GET /api/ordenes/<id>` | — | Órdenes con estado ABIERTA o COMPLETA. |
| `POST /api/ordenes/<id>/bultos` | `{"lineas":[{"producto_id":1,"cantidad":6}]}` | 201 con el bulto PREPARADO y su costo de referencia por línea; reserva en el CD. |
| `GET /api/bultos`, `GET /api/bultos/<id>` | — | Bulto con estado, precinto, remito resumido, líneas y eventos. |
| `POST /api/bultos/<id>/precintar` | `{"precinto":"SELLO-77"}` | 200; emite el remito. |
| `POST /api/bultos/<id>/despachar` | `{}` | 200; reserva del CD a tránsito del local. |
| `POST /api/bultos/<id>/recibir` | `{"local_id":2,"precinto_leido":"SELLO-77","precinto_intacto":true}` | 200: RECIBIDO, o RECHAZADO si el precinto está roto o no coincide. |
| `POST /api/bultos/<id>/verificar` | `{}` | 200; bulto VERIFICADO, stock todavía pendiente. |
| `POST /api/bultos/<id>/anular` | `{}` | 200; sólo desde PREPARADO, libera la reserva. |
| `GET /api/remitos`, `GET /api/remitos/<id>` | — | Remito con número, bulto, origen, destino, estado e instantes. |
| `POST /api/remitos/<id>/verificar` | `{}` | 200; con el bulto verificado, habilita el stock del local. |
| `GET /api/ubicaciones/<id>/saldos` | — | Saldos no nulos por producto y condición (disponible, reservado, en tránsito, pendiente, rechazado). |

Las acciones sin datos reciben `{}`; un campo de más es 400. Una transición que el estado no admite, stock o pendiente insuficiente, precinto repetido, necesidad ya consolidada o recepción en otro local devuelven 409 sin cambios. Formato inválido o contenido rechazado por el dominio es 400; referencias inexistentes, 404 con el campo (`local_id`, `producto_id`, `necesidad_ids.N`, `lineas.N.producto_id`). Los movimientos de `/api/ubicaciones/<id>/movimientos` agregan `bulto_id` y `bulto_codigo` (nulos en compras); `compra_id` y `linea` quedan nulos en movimientos de bultos.

| Tabla | Contenido y restricciones |
| --- | --- |
| `necesidades` | Local, producto, `cantidad > 0`, instante y `orden_id` nulo mientras está pendiente; sólo se consolida una vez. Las líneas de la orden se derivan de ellas. |
| `ordenes_reposicion` | CD de origen, local destino e instante. |
| `bultos` | Orden, estado actual (siete valores) y precinto con `precinto_clave` única en `casefold()`. |
| `detalles_bulto` | Clave (bulto, producto), `cantidad > 0` y costo de referencia positivo o nulo. |
| `eventos_bulto` | Clave (bulto, secuencia); dos triggers rechazan `UPDATE` y `DELETE`. |
| `remitos` | Un remito por bulto (`UNIQUE`), estado y cierre coherentes. |
| `movimientos_stock` | Columna `bulto_id`; un índice único impide repetir una causa logística por bulto, producto y ubicación, y un trigger exige el bulto en todo movimiento que no sea de compra. |

Una base creada con F-02 recibe la columna `bulto_id` por `ALTER TABLE` al iniciar, porque `CREATE TABLE IF NOT EXISTS` no modifica tablas existentes; los datos previos se conservan. El índice y el trigger se crean después. La pantalla de stock del CD ya distingue el documento de cada movimiento (compra o bulto) y su cambio de condición.

## F-03.3: pantallas de reposición, bultos y remitos

`SeccionLogistica` consulta juntos necesidades, órdenes, bultos y remitos, ejecuta una operación por vez y, cuando Python la confirma, vuelve a consultarlos y avisa a la sección de stock. Mientras guarda, bloquea los controles de toda la pantalla.

- **Reposición** (`PanelReposicion`): registrar una necesidad (local y producto activos, cantidad entera positiva comprobada antes de enviar) y consolidar una orden marcando las necesidades pendientes del local elegido. La tabla de órdenes muestra, por producto, lo pedido, lo que ya está en bultos y lo pendiente.
- **Bultos** (`PanelBultos`): preparar un bulto de una orden abierta indicando cantidades por producto pendiente. Cada bulto se muestra como tarjeta con su estado, precinto, remito, contenido con costo de referencia e historial desplegable, y ofrece sólo la acción que admite su estado:

| Estado | Acción en pantalla |
| --- | --- |
| Preparado | Precintar con el número del sello; anular con confirmación explícita. |
| Precintado | Despachar desde el CD. |
| En tránsito | Recepción: local que recibe (el destino por defecto), precinto leído y estado del precinto (intacto o roto, sin opción preseleccionada). |
| Recibido | Verificar contenedor. |
| Verificado, remito emitido | Verificar remito; recién entonces el stock queda disponible. |
| Verificado, Rechazado o Anulado | Texto con el resultado; el rechazo muestra el motivo y que el contenido queda en custodia. |

  La pantalla no decide transiciones: si Python rechaza una acción (por ejemplo, recibir en otro local), se muestra el mensaje en la tarjeta y se conserva el borrador.
- **Stock** (`SeccionStock`, antes `SeccionStockCD`): permite elegir cualquier ubicación (el CD por defecto) y muestra una fila por producto con las condiciones que tienen saldo (disponible, reservado, en tránsito, pendiente de verificación, rechazado), el costo de referencia y los movimientos con su documento de origen.

## F-04.1: dominio de ventas, cobros y comprobante

Aplica las decisiones de la sección N de `docs/DECISIONES_F00.md`. F-04.2 agrega su persistencia y su API, y F-04.3 su pantalla React.

- **Venta.** `Venta` es un documento confirmado que se construye completo y no se modifica. Compone sus `DetalleVenta`, `Cobro` y `Comprobante`, y valida todo antes de existir: local (nunca el CD), al menos una línea y un cobro, productos sin repetir, cantidades enteras positivas, un medio distinto por cobro e importes ARS exactos. Los cobros deben sumar exactamente el total; si no, el mensaje informa ambos importes. Los errores de una línea o un cobro indican su número.
- **Registro.** `RegistroVentas.registrar` copia en cada línea el precio vigente del producto y su costo de referencia (última compra, o `None` si nunca se compró), exige local y productos activos, pide al `Inventario` la salida y a la `Caja` los ingresos, y recién entonces guarda la venta. Con una `clave_operacion` ya registrada devuelve la venta existente, sin efectos de stock ni de caja, e indica que no es nueva.
- **Stock.** `Inventario.vender` descuenta sólo la condición DISPONIBLE del local, con causa `VENTA` y la línea como documento; comprueba todas las líneas antes de modificar ninguna. El stock pendiente, en tránsito, reservado o rechazado nunca es vendible.
- **Caja.** `Caja` registra un `MovimientoCaja` de ingreso por cobro, con local, medio, importe y cobro de origen; el saldo por local y medio se calcula desde los movimientos. Los egresos por reintegro llegan con F-05.
- **Medios y comprobante.** `RegistroVentas` trae los cuatro medios fijos (Efectivo, Débito, Crédito, Transferencia). El comprobante se numera `CV-00000001` a partir del identificador de la venta.

## F-04.2: persistencia y API de ventas, cobros y caja

Cada venta se guarda en una sola transacción con sus líneas, cobros, la salida de stock de cada línea y un ingreso de caja por cobro. Al iniciar, `cargar_estado` reconstruye las ventas después de la logística y antes del inventario, porque los movimientos `VENTA` remiten a sus líneas, y por último la caja, cuyos movimientos remiten a sus cobros. Si el guardado falla, la memoria vuelve al último estado confirmado y la API responde 500, como en compras y logística.

| Método y ruta | Cuerpo | Resultado |
| --- | --- | --- |
| `GET /api/medios-pago` | — | `{"medios_pago":[{"id","codigo","nombre"}]}`: los cuatro medios fijos. |
| `POST /api/ventas` | `{"local_id":2,"clave_operacion":"…","lineas":[{"producto_id":1,"cantidad":2}],"cobros":[{"medio_pago_id":1,"importe":"2000"},{"medio_pago_id":2,"importe":"1000"}]}` | 201 con la venta y `Location`. Con una `clave_operacion` ya registrada, 200 con la venta existente y sin nuevos efectos. |
| `GET /api/ventas`, `GET /api/ventas/<id>` | — | Venta con `comprobante`, local, instante, clave, líneas (precio unitario, costo de referencia o `null`, subtotal), cobros por medio, total y moneda. |
| `GET /api/ventas/<id>/comprobante` | — | Comprobante interno `CV-00000001`: local, instante, líneas, cobros y total, sin costos ni clave. Reconsultarlo no registra otra venta. |
| `GET /api/ubicaciones/<id>/caja` | — | Saldo de cada medio calculado desde los movimientos (`"0.00"` si no hubo) y los movimientos con su venta, comprobante y número de cobro. |

El precio no viaja en la solicitud: Python copia el vigente del catálogo. Los importes de cobro son texto ARS, como los costos de compra. Formato inválido es 400 con `fields` por línea o cobro (`lineas.2.cantidad`, `cobros.1.importe`); local, producto o medio inexistentes son 404 con su campo (`local_id`, `lineas.N.producto_id`, `cobros.N.medio_pago_id`); cobros que no suman el total, medio o producto repetido, CD como local o clave vacía o de más de 64 caracteres son 400; stock disponible insuficiente o local/producto inactivo son 409. Ningún error deja venta, stock ni caja. Los movimientos de `/api/ubicaciones/<id>/movimientos` agregan `venta_id` y `comprobante`; `linea` es la línea de la compra o de la venta y queda nula en los bultos.

| Tabla | Contenido y restricciones |
| --- | --- |
| `medios_pago` | Los cuatro medios fijos, cargados al iniciar si faltan; código único. |
| `ventas` | Local, instante y `clave_operacion` única de 1 a 64 caracteres. El comprobante no tiene tabla: su número se deriva del ID, uno por venta. |
| `detalles_venta` | Clave (venta, línea), producto único por venta, `cantidad > 0`, precio positivo y costo de referencia positivo o nulo. |
| `cobros` | Clave (venta, número), medio único por venta e `importe_centavos > 0`. |
| `movimientos_caja` | Local, medio, tipo, importe positivo y el cobro que lo originó, que ingresa una sola vez. Un ingreso exige cobro; `EGRESO` queda admitido para los reintegros de F-05. Dos triggers rechazan `UPDATE` y `DELETE`. |
| `movimientos_stock` | Columnas `venta_id` y `venta_linea`; un índice único impide descontar dos veces la misma línea y un trigger exige que todo movimiento `VENTA` referencie una línea existente. |

Una base anterior recibe `venta_id` y `venta_linea` por `ALTER TABLE` al iniciar, igual que `bulto_id` en F-03. El trigger de F-03 que exigía bulto a toda causa distinta de `COMPRA` se reemplaza por uno que también exceptúa `VENTA`; los datos previos se conservan. La pantalla de stock ya muestra la venta y la línea como documento de esos movimientos.

## F-04.3: pantalla de ventas, comprobante y caja

La sección “Ventas, cobros y caja del local” trabaja sobre un local elegido:

- **Nueva venta:** líneas de producto activo y cantidad, con el disponible del local en cada opción, el precio del catálogo y el subtotal; uno o más cobros con medio e importe, y el botón “Completar con el saldo”. El total, lo cobrado y lo que falta son estimaciones en pantalla calculadas con BigInt sobre centavos, sin `Number` ni redondeos; Python copia el precio vigente, valida que los cobros sumen exactamente el total y confirma. La cantidad se valida como entero positivo antes de enviar; lo demás lo valida Python y sus errores se muestran sobre el formulario y junto a la línea o el cobro indicado.
- **Envío repetido (RB-10):** cada borrador tiene una `clave_operacion` (`crypto.randomUUID()`), que sólo se renueva después de una venta confirmada. Si se pierde la respuesta o Python responde 500, la pantalla avisa que se puede volver a confirmar; si la venta ya estaba registrada, Python devuelve 200 y se informa “ya se había registrado como CV-…”, sin otra venta ni otro cobro.
- **Comprobante:** después de confirmar se abre el comprobante (`GET /api/ventas/<id>/comprobante`), que también se puede reabrir desde la lista. “Imprimir comprobante” usa la impresión del navegador: una copia en un portal fuera de `#root` es lo único que se imprime mientras el comprobante está abierto. Reimprimir no registra otra venta.
- **Ventas y caja del local:** lista de ventas con líneas, cobros y total; saldo por medio calculado por Python y movimientos de caja con su venta y número de cobro.

Cada venta confirmada vuelve a consultar el stock, así que la sección de stock muestra la salida con “Venta CV-…, línea N” como documento. Un local inactivo se puede consultar pero no vender. `api.js` agrega `ventasAPI` y una opción `conEstado` de `solicitar` para distinguir 201 de 200.

## F-05.1: dominio de devoluciones y reintegros

Aplica las decisiones de la sección O de `docs/DECISIONES_F00.md`. En esta parte sólo existe el dominio con sus pruebas: todavía no hay tablas, API ni pantalla de devoluciones (F-05.2 y F-05.3).

- **Devolución.** `Devolucion` es un documento confirmado que se construye completo y no se modifica. Refiere a una `Venta`, se recibe en su mismo local y compone sus `DetalleDevolucion` y `Reintegro`. Valida todo antes de existir: al menos una línea y un reintegro, líneas de esa venta sin repetir, cantidad entera positiva que no supere la vendida, aptitud booleana, motivo de hasta 200 caracteres e instante no anterior a la venta. No hay plazo. Se muestra como `DV-00000001`.
- **Importe.** Cada línea reintegra cantidad × precio unitario histórico de la línea vendida, sea apta o no; un cambio de precio en el catálogo no lo altera. Los reintegros usan medios cobrados en la venta, uno distinto por reintegro, y deben sumar exactamente el total.
- **Registro.** `RegistroDevoluciones.registrar` exige local activo (un producto inactivo sí se puede devolver), controla la cantidad acumulada de cada línea (`devuelto`, `remanente`) y que cada medio no reintegre más de lo cobrado con él menos lo ya reintegrado (`reintegrable_centavos`). Recién entonces pide al `Inventario` el ingreso y a la `Caja` los egresos, y guarda la devolución. Con una `clave_operacion` ya registrada devuelve la devolución existente sin efectos.
- **Stock.** `Inventario.devolver` ingresa cada línea en el local con causa `DEVOLUCION`: lo apto como DISPONIBLE, vendible otra vez, y lo no apto como BLOQUEADO, en custodia y nunca vendible. La revisión del cajero es el control de RB-17; no interviene remito ni bulto.
- **Caja.** `Caja.egresar_devolucion` registra un `MovimientoCaja` de egreso por reintegro, en el local de la venta y el medio del reintegro. `MovimientoCaja` recibe ahora su `documento` (un `Cobro` para el ingreso, un `Reintegro` para el egreso) y expone `cobro` y `reintegro`, que valen `None` cuando no corresponden.
- **Venta intacta.** La devolución no modifica la venta ni su comprobante: queda como otro documento en su propio instante (DN-09).

## F-05.2: persistencia y API de devoluciones

Cada devolución se guarda en una sola transacción con sus líneas, reintegros, el ingreso de stock de cada línea y un egreso de caja por reintegro. Al iniciar, `cargar_estado` reconstruye las devoluciones después de las ventas y antes del inventario y la caja, cuyos movimientos remiten a sus líneas y reintegros; ahora devuelve también el registro de devoluciones. Si el guardado falla, la memoria vuelve al último estado confirmado y la API responde 500.

| Método y ruta | Cuerpo | Resultado |
| --- | --- | --- |
| `POST /api/devoluciones` | `{"venta_id":1,"clave_operacion":"…","motivo":"…","lineas":[{"linea":1,"cantidad":1,"apto":true}],"reintegros":[{"medio_pago_id":1,"importe":"1500"}]}` | 201 con la devolución y `Location`. Con una `clave_operacion` ya registrada, 200 con la devolución existente y sin nuevos efectos. |
| `GET /api/devoluciones`, `GET /api/devoluciones/<id>` | — | Devolución `DV-00000001` con venta y comprobante de origen, local, instante, motivo, clave, líneas (línea vendida, cantidad, aptitud, condición de destino, precio unitario histórico e importe), reintegros por medio, total y moneda. |
| `GET /api/ventas/<id>/devoluciones` | — | Lo que queda por devolver: por línea vendida, cantidad vendida, devuelta y remanente; por medio cobrado, el importe que todavía se puede reintegrar; y las devoluciones de la venta. |

`linea` es el número de línea de la venta, no el producto. Formato inválido es 400 con `fields` (`lineas.1.apto`, `reintegros.2.importe`); venta, línea de esa venta o medio inexistentes son 404 con su campo (`venta_id`, `lineas.N.linea`, `reintegros.N.medio_pago_id`); reintegros que no suman el total, medio no cobrado o repetido, línea repetida, cantidad mayor a la vendida y motivo o clave inválidos son 400; lo ya devuelto o reintegrado que deja sin remanente, y el local inactivo, son 409. Ningún error deja devolución, stock ni caja.

Los movimientos de `/api/ubicaciones/<id>/movimientos` agregan `devolucion_id` y `devolucion` (`DV-…`); en un movimiento `DEVOLUCION`, `linea` es la línea de la devolución. Los movimientos de `/api/ubicaciones/<id>/caja` agregan `devolucion_id`, `devolucion` y `reintegro`: un egreso informa la venta original, `cobro` nulo y su devolución y número de reintegro; un ingreso deja nulos los tres campos nuevos.

| Tabla | Contenido y restricciones |
| --- | --- |
| `devoluciones` | Venta, instante, motivo de 1 a 200 caracteres y `clave_operacion` única de 1 a 64. El local es el de la venta y no se repite. |
| `detalles_devolucion` | Clave (devolución, línea), referencia a la línea vendida, única por devolución, `cantidad > 0` y `apto` 0 o 1. Un trigger exige que la línea sea de la venta de la devolución y otro que lo devuelto acumulado no supere lo vendido (RB-11). El importe no se guarda: se deriva del precio histórico de la línea vendida. |
| `reintegros` | Clave (devolución, número), medio único por devolución e `importe_centavos > 0`. |
| `movimientos_stock` | Columnas `devolucion_id` y `devolucion_linea`; un índice único impide ingresar dos veces la misma línea y un trigger exige que todo movimiento `DEVOLUCION` sea una entrada a DISPONIBLE si la línea es apta o a BLOQUEADO si no lo es. |
| `movimientos_caja` | Columnas `reintegro_devolucion_id` y `reintegro_numero`; un índice único impide egresar dos veces el mismo reintegro y un trigger exige que todo egreso referencie un reintegro existente y que un ingreso no lo haga. |

Una base anterior recibe las columnas nuevas por `ALTER TABLE` al iniciar, igual que en F-03 y F-04. El trigger que exige bulto a los movimientos logísticos se reemplaza por uno que también exceptúa `DEVOLUCION`; los datos previos se conservan. `medio_json` pasó de `api_ventas.py` a `api_comun.py` porque ahora lo usan ventas y devoluciones.

## F-05.3: pantalla de devoluciones

La vista “Devoluciones” (grupo Operaciones, `#/devoluciones`) trabaja sobre un local y una de sus ventas:

- **Lo que queda por devolver:** al elegir la venta, la pantalla consulta `GET /api/ventas/<id>/devoluciones` y muestra por línea lo vendido, lo ya devuelto, lo que queda y el precio histórico; por medio cobrado, lo que todavía se puede reintegrar. Una línea sin remanente queda deshabilitada.
- **Borrador:** cantidad devuelta por línea (vacía si no se devuelve) y estado de la mercadería tras revisarla (“Apta: vuelve a estar disponible” o “No apta: queda bloqueada”), obligatorio si hay cantidad; un importe por medio con “Completar con el saldo”, limitado a lo reintegrable de ese medio; y el motivo, de hasta 200 caracteres. El reintegro estimado, lo reintegrado y lo que falta se calculan con BigInt sobre centavos. La pantalla sólo valida que haya alguna línea, que la cantidad sea un entero positivo y que se indique la aptitud; el remanente, que los reintegros sumen el total y el tope por medio los valida Python, y sus errores se muestran sobre el formulario y junto a la línea o el medio indicado.
- **Envío repetido (RB-10):** igual que en ventas, la `clave_operacion` sólo se renueva después de una devolución confirmada; tras un error de red o un 500 se avisa que se puede volver a confirmar, y si ya estaba registrada se informa “ya se había registrado como DV-…”.
- **Devoluciones del local:** número, fecha, venta de origen, líneas con aptitud y condición de destino, reintegros por medio, motivo y total.

Cada devolución confirmada incrementa la revisión de stock compartida, así que Stock por ubicación muestra el ingreso con “Devolución DV-…, línea N” y Ventas y caja vuelve a consultar la caja, cuyos egresos se presentan como “Devolución DV-… de la venta CV-…, reintegro N” (`origenCaja` en `etiquetas.js`). `api.js` agrega `devolucionesAPI`. En el dominio, el rechazo por exceso sobre lo que queda (409) ahora nombra la línea de la venta, que es la que ve la pantalla, en lugar de la posición en la devolución.

## F-06.1: dominio de reportes y patrón Strategy

Aplica las decisiones de la sección P de `docs/DECISIONES_F00.md`. En esta parte sólo existe el cálculo en `backend/dominio/reportes.py` con sus pruebas: todavía no hay API ni pantalla de reportes (F-06.2 y F-06.3). Los reportes leen los registros en memoria (ventas, devoluciones, caja, inventario, logística y mínimos del catálogo) y no modifican nada. Los importes son centavos exactos; las magnitudes netas pueden ser negativas cuando lo devuelto en un período supera lo vendido en él.

- **Período.** `Periodo(desde, hasta)` recibe fechas sin hora, con inicio incluido y fin excluido; la fecha de inicio debe ser anterior a la de fin. Cada operación cuenta en la fecha de su instante en la zona acordada: una devolución afecta su propio período, no el de la venta.
- **R-01 Ventas, cobros e ingresos netos (Strategy).** `ReporteVentas` es el contexto: filtra por período y local, calcula aparte el total de ventas, el de devoluciones y la venta neta desde los documentos, y delega en una `EstrategiaAgrupacion` la clave de cada movimiento de caja. `PorDia`, `PorLocal` y `PorMedioPago` reciben los mismos movimientos (cobros y reintegros), se eligen desde afuera (`ESTRATEGIAS_AGRUPACION` por nombre) y se intercambian con `cambiar_estrategia()`, sin `if` por tipo en el contexto. Cada grupo informa cobros, reintegros e ingreso neto; ventas y devoluciones no se reparten entre medios. Una venta con dos medios no se cuenta dos veces, y el ingreso neto total coincide con la venta neta.
- **R-02 Productos más vendidos y margen estimado.** Por producto: unidades vendidas, devueltas y netas, importe neto a precios históricos, costo neto con el costo de referencia guardado en cada línea (la devolución revierte el de la línea original) y margen = importe neto − costo neto. Se ordena por unidades netas descendentes y, ante empate, por identificador. Si a un producto le falta el costo, ni su margen ni el margen total se informan y el producto queda en `productos_sin_costo`. Su importe neto concilia con la venta neta de R-01 para el mismo período y local.
- **R-03 Existencias, mínimos y faltantes.** Para un local o el CD, con categoría opcional y opción de sólo productos en mínimo: saldo en cada condición, mínimo, déficit = máximo entre mínimo − disponible y cero, y alerta cuando el disponible es menor o igual que el mínimo. Incluye los productos con mínimo aunque nunca hayan tenido stock; sin mínimo no hay déficit ni alerta, y el CD no tiene mínimos.
- **R-04 Rechazos logísticos.** Por fecha del rechazo, con local destino y producto opcionales: cada bulto rechazado con remito, destino, motivo, unidades y valor bloqueado al costo guardado al preparar el bulto, y por local los bultos recibidos y rechazados del período. Un bulto cuenta una vez aunque tenga varias líneas y eventos; con filtro de producto sólo cuentan sus líneas. Una compra posterior no cambia el valor bloqueado, que no es una merma; si falta un costo, ese valor no se informa.

## F-06.2: API de reportes

`api_reportes.py` sólo consulta: toma el bloqueo compartido, arma los filtros, delega el cálculo en el dominio y devuelve JSON. No hay tablas nuevas ni escrituras; los reportes se calculan sobre la memoria reconstruida desde SQLite, así que dan lo mismo después de reiniciar.

| Método y ruta | Parámetros | Resultado |
| --- | --- | --- |
| `GET /api/reportes/ventas` | `desde`, `hasta`, `local_id` opcional, `agrupacion` (`dia` por defecto, `local` o `medio`) | R-01: cantidad e importe de ventas y devoluciones, venta neta, grupos con cobros, reintegros e ingreso neto, y sus totales. |
| `GET /api/reportes/agrupaciones` | — | Nombres de las estrategias disponibles: `["dia","local","medio"]`. |
| `GET /api/reportes/productos` | `desde`, `hasta`, `local_id` opcional | R-02: ranking con posición, unidades vendidas, devueltas y netas, importe neto, costo neto y margen; totales, margen del período y `productos_sin_costo`. |
| `GET /api/reportes/existencias` | `ubicacion_id`, `categoria_id` y `solo_en_minimo` (`true`/`false`) opcionales | R-03: por producto, su categoría, saldos en las seis condiciones, mínimo, déficit y alerta; totales por condición, productos en mínimo y déficit total. |
| `GET /api/reportes/rechazos` | `desde`, `hasta`, `local_id` y `producto_id` opcionales | R-04: bultos rechazados con remito, destino, instante, motivo, líneas con costo, unidades y valor bloqueado; por local, recibidos, rechazados, unidades y valor bloqueado; totales. |

Las fechas van como `AAAA-MM-DD`, con `desde` incluido y `hasta` excluido: octubre es `desde=2026-10-01&hasta=2026-11-01`. Los importes son texto con dos decimales y pueden ser negativos (`"-1500.00"`) cuando lo devuelto en el período supera lo vendido; para eso `importe_a_texto` ahora antepone el signo. Un costo faltante se informa como `null`, nunca como `"0.00"`. Un parámetro faltante, desconocido, repetido o con formato inválido, una fecha inexistente, el período invertido o vacío, una agrupación desconocida y el CD como `local_id` son 400 con el parámetro en `fields`; una ubicación, categoría o producto inexistentes son 404 con su parámetro. Las rutas sólo admiten `GET`: otro método es 405 JSON.

## F-06.3: pantalla de reportes

La vista “Reportes” (grupo Consultas, `#/reportes`) aplica la decisión P.6: los cuatro reportes se generan a pedido y se muestran en pantalla, sin exportar a PDF ni CSV.

- **Filtros.** Un selector elige R-01 a R-04 y muestra sólo sus filtros: período (por defecto, del primer día del mes actual a hoy), agrupación de R-01 (Día, Local o Medio de pago), local opcional, producto opcional en R-04, y en R-03 la ubicación obligatoria, la categoría y “Sólo productos en su mínimo”. El campo “Hasta (inclusive)” es el último día incluido; al consultar se envía el día siguiente porque la API mantiene el fin excluido. Las listas incluyen registros inactivos, que pueden tener operaciones en el período.
- **Validación.** La pantalla sólo exige completar las fechas (`required`); el orden del período, las referencias y el CD como local los valida Python, y sus errores 400 o 404 de Python se muestran sobre el formulario y junto al campo indicado, con `aria-invalid`. Cada reporte conserva su último resultado al cambiar de tipo, y una consulta nueva cancela la anterior del mismo tipo.
- **Presentación.** Cada resultado indica el período y el alcance consultados, un resumen y tablas con totales al pie. Los importes llegan como texto de Python; la pantalla sólo antepone `$` y marca los negativos (`−$ 1500.00`). Un costo faltante aparece como “Sin costo” o “Incompleto”, nunca como cero; el déficit sin mínimo configurado, como “—”, también en el total del CD. R-03 sólo muestra las condiciones con saldo además de Disponible. Cada reporte explica debajo sus fórmulas y lo que no incluye.

`api.js` agrega `reportesAPI.generar`, que omite los filtros vacíos. No hay cambios de backend.

## F-07.1: escenarios integrales de aceptación

Aplica la sección Q de `docs/DECISIONES_F00.md`. `tests/test_integracion.py` recorre la API como lo hace la pantalla, cada escenario sobre su propia base temporal, y simula el reinicio creando otra aplicación sobre la misma base. No agrega funcionalidad ni modifica el backend o la pantalla.

- **Feliz, con el dataset de control J.3.** Producto P a 100 con costo 60; compra de 14 unidades; el local A recibe 3 (dos necesidades consolidadas en una orden) y B 7, ambos con doble verificación; A recibe además un bulto de 4 con el precinto roto. A vende 3 a 100 con efectivo y crédito; P pasa a 90 y B vende 2 por transferencia; A devuelve 1 apta. Se comprueban stock y caja por local, la orden con sus necesidades, los comprobantes con el precio histórico y la reconsulta sin efectos, y los resultados de J.3 en los cuatro reportes: venta neta e ingreso neto 380, neto por medio 100 / 100 / 180, margen 140 sobre costo 240, déficit 1 en A y 0 en B, y 240 bloqueados por el rechazo. Después del reinicio, documentos, stock, caja, historia de bultos y reportes son idénticos, la numeración continúa (`CV-00000003`) y una clave repetida devuelve la devolución existente sin efectos.
- **Bloqueo.** Con el stock en tránsito, recibido y con el bulto verificado pero el remito pendiente, la venta se rechaza (409); al verificar el remito queda disponible y se vende, y una unidad más vuelve a rechazarse.
- **Rechazo.** El precinto roto deja el bulto Rechazado con sus cinco eventos, que no cambian; no se vende, no se puede verificar, no hay caja ni venta, y R-04 informa las 4 unidades y 240 bloqueados.
- **Transaccional.** Una compra, una venta y una devolución fallan después de guardar parte de sus filas; ni la aplicación en uso ni una reiniciada muestran el documento, el stock o la caja parciales, y el reintento posterior deja los saldos y R-01 correctos.

## F-07.2: ejecución y restricciones técnicas

`tests/test_restricciones.py` revisa el repositorio con `ast` y los archivos de dependencias, sin ejecutar Node ni levantar servidores (T-29 y parte de T-30):

- `backend/` contiene sólo módulos Python y sus dos archivos de requisitos; sus importaciones son de la biblioteca estándar, Flask o Werkzeug, y ninguna lanza procesos (`subprocess`).
- La única dependencia de ejecución es Flask; pytest sólo figura en los requisitos de desarrollo.
- En `frontend/package.json`, los scripts sólo ejecutan Vite (`dev`, `build`, `preview`) y las dependencias son React y React DOM; el cliente no importa otros paquetes. Node construye el cliente o lo sirve en desarrollo, pero no ejecuta reglas: la API y el build compilado los sirve Flask.
- El SQL de `backend/persistencia` recibe los valores como parámetros `?`. Los únicos f-strings insertan nombres de tabla o columna de tuplas fijas del código (`tabla`, `nombre`, `definicion`), porque SQLite no admite parámetros para identificadores; un SQL armado con `%`, `+` o `.format()` hace fallar la prueba.

La independencia del dominio respecto de Flask y SQLite ya la comprueba `tests/test_catalogo.py` con Python `-I -S`, y el build servido por Flask, `tests/test_api.py`. Los comandos de las secciones siguientes se ejecutaron tal como están escritos (ver la verificación de F-07.2).

## Memoria, persistencia, pantalla y límites actuales

`create_app` crea un `Catalogo` en `app.extensions["catalogo"]` y un `Lock` propio. La API utiliza esa misma instancia entre solicitudes; el bloqueo abarca las operaciones de dominio y la construcción de las respuestas para evitar carreras sobre códigos, IDs y referencias, incluida la comprobación de activos y su desactivación. No hay Singleton ni catálogo global compartido entre aplicaciones. Los tests crean aplicaciones aisladas. El dominio no añade sincronización para clientes Python externos: el adaptador HTTP es responsable de este bloqueo.

**Persistencia (F-02.1).** `create_app(frontend_dist=None, base_datos=None)` abre la base indicada o la ruta predeterminada, crea las tablas faltantes (`CREATE TABLE IF NOT EXISTS`, sin borrar datos) y reconstruye el `Catalogo`, el `RegistroCompras` y el `Inventario` con la API del dominio, que vuelve a validar cada fila. Las compras y los movimientos se restauran sin repetir su efecto: los saldos se leen de `existencias`. Las bajas se aplican al final de la carga para restablecer antes referencias y mínimos. En cada escritura, el dominio valida y modifica la memoria y luego `guardar_cambio` (`api_comun.py`) confirma la fila completa de esa entidad y su código, o la compra con sus detalles, movimientos y saldos, en una sola transacción: abre la conexión, ejecuta, hace `commit()` o `rollback()` y la cierra. Si el guardado falla, la memoria se reemplaza por el último estado confirmado y la API responde 500 JSON sin informar éxito; consultar antes de reintentar.

| Tabla | Contenido y restricciones |
| --- | --- |
| `categorias`, `proveedores` | ID, código vigente, nombre y `activo` (0/1). |
| `productos` | Además, `categoria_id` con clave foránea y `precio_centavos > 0`. |
| `ubicaciones` | Además, `tipo` LOCAL/CD; un índice único parcial impide un segundo CD. |
| `minimos` | Clave (local, producto) con claves foráneas y `minimo >= 0`. |
| `codigos_reservados` | Códigos vigentes e históricos por tipo, con clave `casefold()`; nunca se liberan. |
| `compras` | ID, proveedor, CD e instante ISO 8601 con desplazamiento. Sin actualizaciones ni bajas. |
| `detalles_compra` | Clave (compra, línea); producto único por compra, `cantidad > 0` y `costo_unitario_centavos > 0`. |
| `existencias` | Clave (ubicación, producto, condición) con las seis condiciones del modelo y `cantidad >= 0`. El saldo se incrementa en SQL desde el movimiento. |
| `movimientos_stock` | Cantidad positiva, condiciones válidas y causa; un ingreso `COMPRA` referencia su línea, y cada línea genera un único movimiento (`UNIQUE`). |

Las claves foráneas se activan en cada conexión (`PRAGMA foreign_keys = ON`). La base es la fuente entre ejecuciones; el dominio sigue siendo la autoridad de las reglas y las restricciones SQL son una segunda barrera. Un solo proceso Flask escribe la base (DN-11); el `Lock` serializa las solicitudes de ese proceso. No se usa la base como almacenamiento compartido entre instalaciones. Recargar React conserva los registros del backend, pero descarta los borradores locales.

La pantalla consulta los cuatro maestros con `estado=todos` y presenta un filtro independiente Activos/Inactivos/Todos por sección, con Activos por defecto y una columna de estado. Ofrece sólo categorías activas para asociar productos y consulta por ID antes de editar. Los inactivos tienen consulta de sólo lectura, sin Guardar; la categoría histórica de un producto inactivo sigue visible aunque también esté inactiva. Proveedores y ubicaciones reutilizan `SeccionCatalogo`, `FormularioCatalogo`, `fetch` y estilos. En ubicaciones, el alta tiene selector de tipo y el listado diferencia Local/CD; al editar, el tipo aparece como texto fijo. El segundo CD se rechaza desde Python con un mensaje junto al selector; las opciones permanecen disponibles para que ese control siga siendo efectivo aun con información cliente desactualizada.

“Desactivar” abre una confirmación explícita con código/nombre y aviso de que no hay reactivación; inicialmente enfoca Cancelar. No envía la baja hasta confirmar. Durante la solicitud se informa carga y se bloquean los controles para impedir dobles envíos. El rechazo de Python se muestra con su motivo y conserva el borrador. Tras éxito se reconsultan los listados y se devuelve el foco al filtro; cancelar también devuelve allí el foco. El CD presenta el motivo de bloqueo en lugar de la acción. Cambiar filtros o desactivar otro registro no limpia formularios.

Conserva los campos ante un error, muestra carga/éxito/error/vacío y bloquea envíos mientras están pendientes. La ayuda del código de los cuatro maestros explica su reserva al reemplazarlo. Los precios permanecen como texto; no se calculan ni redondean en JavaScript. Después de guardar se reconsultan los listados, incluyendo los nombres actuales de categorías referenciadas. Un fallo de esa lectura se informa por separado del guardado ya confirmado.

`SeccionCompras` (F-02.3) arma la compra como borrador del formulario: proveedor activo y una o más líneas con producto activo, cantidad y costo unitario, que se agregan o quitan sin consultar a Python. El destino es el CD registrado y se muestra como texto; sin CD, el formulario queda deshabilitado con aviso. Antes de enviar sólo se comprueba que cada cantidad sea un entero seguro mayor que cero; el costo viaja como texto y Python valida el importe exacto. Los errores de Python identifican la línea («Línea 2: …») y, si son de formato o de referencia, marcan el campo con `aria-invalid`. Ante un error el borrador se conserva; tras confirmar se limpia, se informa número y total devueltos por Python y se agrega la compra al listado, del más reciente al más antiguo. JavaScript no calcula subtotales ni totales. Cada campo de línea tiene un nombre accesible con su número.

`SeccionStockCD` (desde F-03.3, `SeccionStock`, con selector de ubicación) consultaba las existencias y los movimientos del CD cuando carga la pantalla, cuando cambia el catálogo, después de cada compra confirmada y con “Actualizar stock”. Muestra disponible y costo de referencia (“Sin costo registrado” si Python devuelve `null`) y los movimientos con su compra y línea de origen. Los instantes se presentan como `dd/mm/aaaa hh:mm:ss` tomando el texto que registró Python, sin conversiones de zona horaria en el navegador.

`SeccionMinimos` permite configurar usando únicamente locales y productos activos (siempre excluye CD). “Consultar mínimos históricos (sólo lectura)” incluye inactivos identificados y bloquea el guardado. La tabla conserva las configuraciones y muestra el estado de cada producto, aun si está inactivo. Una selección que acaba de quedar inactiva se conserva para no perder el borrador, como opción deshabilitada fuera del modo histórico; no habilita escrituras. Distingue ausencia, cero, carga y error; no afirma “Sin configurar” si falló la consulta. Conserva la entrada ante errores, cancela consultas obsoletas y bloquea los controles durante el guardado. Tras confirmar, usa la respuesta de Python para actualizar el par sin duplicarlo. “Actualizar mínimos” vuelve a consultar el local; las actualizaciones de maestros también reconsultan sus configuraciones sin borrar el borrador numérico. Cambiar manualmente de local o producto limpia ese borrador para trabajar sobre la nueva selección.

El cliente `fetch` tiene un límite de 10 segundos, cancela lecturas obsoletas y no reintenta escrituras automáticamente. Si no se pudo confirmar una escritura por un fallo de conexión, consultar el listado antes de reenviar. “Actualizar listados” y “Actualizar mínimos” permiten consultar cambios hechos desde otra pestaña; no hay actualización en tiempo real ni resolución de conflictos entre ediciones. Los `PUT` al mismo mínimo se serializan: queda el último procesado. La pantalla no consulta `/api/health`: si falla la lectura del catálogo, muestra el error sobre la vista y conserva los borradores.

Cada vista tiene su ruta en el hash (`#/categorias`, `#/compras`, `#/stock`, …), agrupada en Catálogo, Operaciones y Consultas, de modo que recargar o usar Atrás vuelve a la misma sección. Las vistas ocultas siguen montadas, así que cambiar de sección no descarta borradores ni operaciones en curso; el menú marca «guardando…» en la sección que tiene una escritura pendiente. Como el hash no llega al servidor, Flask siempre recibe `/` y no necesita un router SPA. En pantallas angostas las secciones se despliegan con el botón «Secciones».

## Versiones utilizadas

| Componente | Versión verificada |
| --- | --- |
| Python | 3.11.2 (`py -3.11`) en el equipo donde se armó el entorno; 3.13.5 (`py -3.13`) en la `.venv` usada para F-06 y F-07 |
| Flask | 3.1.3 |
| Werkzeug | 3.1.9, instalado con Flask |
| pytest | 9.1.1 |
| Node.js | 22.14.0 |
| npm | 11.6.0 en el equipo original; 10.9.2 en el equipo de F-06 y F-07 |
| React / React DOM | 19.3.1 |
| Vite | 8.3.4 |
| @vitejs/plugin-react | 6.1.2 |

Las dependencias directas están fijadas; `package-lock.json` registra la resolución completa de npm. Vite requiere Node `^20.19.0 || >=22.12.0`. No hace falta actualizar herramientas globales para reproducir este entorno.

## Preparación local en Windows / PowerShell

Desde la raíz del repositorio:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
```

El comando `python` del entorno inspeccionado apunta al alias de Microsoft Store. Por eso se usa el lanzador `py` al crear el entorno y luego el ejecutable de `.venv`, sin depender de activar scripts de PowerShell. `py -0` lista las versiones instaladas; si no está la 3.11, usar la disponible (por ejemplo `py -3.13`, con la que se verificaron F-06 y F-07). Para ejecutar sólo el backend se puede instalar `backend/requirements.txt`; el archivo de desarrollo incluye Flask y pytest.

Preparar el frontend:

```powershell
cd frontend
npm install
```

Si PowerShell impide ejecutar `npm.ps1`, usar `npm.cmd` con los mismos argumentos. La instalación y los scripts se verificaron con `npm.cmd` en este equipo. `.venv`, `node_modules`, `dist`, cachés y configuraciones `.env.local` están excluidos de Git.

## Desarrollo: dos terminales

Terminal 1, desde la raíz:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend:create_app --no-debug run --host 127.0.0.1 --port 5000 --no-reload
```

Terminal 2, desde la raíz:

```powershell
cd frontend
npm run dev
```

Abrir [frontend de desarrollo](http://127.0.0.1:5173/). La pantalla abre en Catálogo / Categorías y permite pasar a productos, proveedores, ubicaciones, mínimos, compras, reposición y logística, ventas y caja, devoluciones, stock por ubicación y reportes. El estado de salud se comprueba directamente sobre la API (ver más abajo). Los comandos de desarrollo se conservan en F-01.6.

Camino de la solicitud: navegador → `http://127.0.0.1:5173/api/health` → proxy Vite → `http://127.0.0.1:5000/api/health`. Se conserva `/api`, sin transformación ni lógica de aplicación en el proxy. No es necesario configurar CORS para este camino.

La API también responde sin React/Vite:

```powershell
Invoke-RestMethod http://127.0.0.1:5000/api/health
```

Para detener un servidor, usar Ctrl+C en su terminal. Si `npm.cmd` pregunta si debe terminar el trabajo por lotes, confirmar con `S`.

## Configuración mínima

| Valor | Predeterminado | Cómo cambiarlo |
| --- | --- | --- |
| Ruta de API | `/api`; salud en `/api/health` | Contrato común en Blueprint, proxy y cliente; no se cambia por entorno. |
| Puerto Python | 5000 | Opción `--port` del comando Flask. |
| Puerto Vite | 5173 | `FRONTEND_PORT` en `frontend/.env.local`. |
| Destino del proxy | `http://127.0.0.1:5000` | `API_PROXY_TARGET` en `frontend/.env.local`; debe coincidir con Flask. |
| Dirección de escucha | `127.0.0.1` | Configuración local deliberada; no se expone por LAN en este incremento. |
| Ruta del build | `frontend/dist` | Calculada desde la ubicación del backend, no desde el directorio de ejecución. |
| Base SQLite | `%LOCALAPPDATA%\TP-DAO\tp_dao.db` | Variable de entorno `TP_DAO_DB` antes de iniciar Flask, por ejemplo `$env:TP_DAO_DB = "C:\datos\tp.db"`. La carpeta se crea si falta. |

No se necesita ningún `.env` para los valores predeterminados. Para cambiar puertos, copiar `frontend/.env.example` a `frontend/.env.local`, modificarlo y reiniciar Vite. El puerto Vite es estricto: si está ocupado, el servidor falla visiblemente en vez de elegir otro. Las dos variables del ejemplo son configuración de Vite, no secretos ni variables `VITE_*` inyectadas en la aplicación cliente.

Ejemplo de cambio de puerto Python a 5001: usar `--port 5001` y establecer `API_PROXY_TARGET=http://127.0.0.1:5001` en el archivo local del frontend. No agregar credenciales ni rutas privadas al bundle.

## Build servido por Python, sin Vite

Desde la raíz:

```powershell
cd frontend
npm run build
cd ..
.\.venv\Scripts\python.exe -m flask --app backend:create_app --no-debug run --host 127.0.0.1 --port 5000 --no-reload
```

Si Flask ya está ejecutándose, no iniciar otra instancia: alcanza con generar el build. En Windows, una segunda instancia en el mismo puerto arranca sin ningún error (comprobado el 01/11/2026), y dos procesos con memoria propia sobre la misma base rompen el supuesto de un único proceso escritor (DN-11). Antes de iniciar, comprobar que no quede otra: `Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object CommandLine -like '*flask*'` no debe listar ninguna. Detener Vite y abrir [frontend compilado](http://127.0.0.1:5000/). Flask sirve `index.html`, los recursos de `/assets` y la API desde el mismo origen. Las solicitudes relativas `/api/health` siguen funcionando; Node no participa en la ejecución del backend ni del build ya servido.

La base predeterminada queda fuera de la carpeta del repositorio, que puede estar sincronizada con OneDrive: no sincronizar ni compartir un archivo SQLite abierto. Para empezar con datos vacíos, detener Flask y usar otra ruta en `TP_DAO_DB` o borrar ese archivo manualmente.

Antes de compilar, `/` devuelve 404 y `/api/health` funciona igualmente. No se implementó un router SPA: rutas no definidas y archivos inexistentes devuelven 404. Los errores bajo `/api` son JSON y nunca se reemplazan por HTML. Sólo se publican el índice y los recursos de `dist/assets`, no el repositorio ni archivos privados.

`npm run preview` está disponible para inspeccionar estáticos, pero no configura este proxy ni reemplaza la demostración con Python. Los servidores usados son de desarrollo local, no un despliegue de producción.

## Pruebas y resultados

Desde la raíz:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Verificación de F-07.2 el 01/11/2026: **823 casos aprobados** con la suite completa, en 5 minutos 14 segundos; los 817 previos siguen pasando. Se agregaron 6 casos en `tests/test_restricciones.py`; para confirmar que detectan una violación, se los ejecutó contra una copia falsa del backend con un archivo `.js`, `import subprocess` y `import requests`, y SQL armado con `%`: las tres pruebas correspondientes fallaron. Con Python 3.13.5 y npm 10.9.2, desde un `dist` borrado:

- `npm.cmd run build` terminó correctamente; con Vite apagado, el comando de “Build servido por Python” con `TP_DAO_DB` temporal sirvió `/` (200), el JavaScript de `/assets` (200), `/api/health` (`{"status":"ok"}`) y `/api/no-existe` como 404 JSON; `/reportes` dio 404, porque no hay router SPA. En el navegador cargó el catálogo con las once vistas y sin errores de consola.
- Reinicio controlado: una categoría creada por la API siguió presente después de detener Flask (sin respuesta en el puerto) e iniciarlo otra vez con la misma base.
- Modo de dos terminales: `/api/health` respondió en el 5000 y a través del proxy de Vite en el 5173, que sirvió el índice y conservó el 404 JSON de la API; al detenerlos, los dos puertos quedaron libres.
- En Windows, una segunda instancia de Flask en el puerto 5000 arrancó sin ningún error mientras la primera seguía activa; se documentó cómo comprobarlo antes de iniciar.
- Diferencias corregidas en la documentación: `py -3.11` no está disponible en este equipo (la `.venv` usa 3.13.5), npm es 10.9.2 y no 11.6.0, la lista de vistas omitía Devoluciones y Reportes, y `docs/LEVANTAR_PROYECTO.md` estimaba la suite en más de 20 minutos.

Verificación de F-07.1 el 01/11/2026: **817 casos aprobados** con la suite completa, en 3 minutos 59 segundos; los 808 previos siguen pasando. Se agregaron 9 casos en `tests/test_integracion.py` con los cuatro escenarios de J.4; los resultados esperados del escenario feliz son los de J.3, calculados antes de escribir las aserciones. No hubo cambios de backend ni de frontend, así que no se ejecutó `npm run build`.

Verificación de F-06.3 el 01/11/2026: no hubo cambios de backend, así que la suite sigue con los 808 casos aprobados de F-06.2 y no se volvió a ejecutar; `npm run build` terminó correctamente. Prueba manual en el navegador integrado con el build servido por Flask en el puerto 5050 y una base temporal cargada con el escenario de `tests/test_api_reportes.py` más una venta de 1 fideo con crédito (900.50) el 20/10:

- R-01 de octubre por día: ventas 7201.50, grupos 05/10 (6301.00) y 20/10 (900.50); noviembre por medio: venta neta `−$ 1500.00` en rojo; período invertido: “La fecha de inicio debe ser anterior a la de fin.” junto a “Hasta”, con `aria-invalid`;
- R-02 del 01/10 al 30/11: fideos 3 u. netas, 2701.50, costo 1200.00 y margen 1501.50; arroz 2 u. netas, 3000.00, 2000.00 y 1000.00; importe total 5701.50, igual a la venta neta de R-01;
- R-03 del CD: arroz 15 y fideos 5 disponibles, mínimo y déficit “—”, también en el total; de L1: arroz 3 con mínimo 2 y déficit 0, fideos 0 con mínimo 2, déficit 2 y “En mínimo”; con “Sólo productos en su mínimo”, sólo los fideos;
- R-04 del 01/10 al 30/11: B-000002 / R-000002 a L2, 02/10/2026 09:00:00, “Precinto roto.”, 2 u. de fideos y $ 800.00 bloqueados; por local, L1 con 1 recibido y 0 rechazados y L2 con 1 y 1;
- a 375 px de ancho, sin desplazamiento horizontal de la página (las tablas se desplazan dentro de su contenedor); en la consola, sólo el 400 esperado del período invertido.

Verificación de F-06.2 el 01/11/2026: **808 casos aprobados** con la suite completa, en 3 minutos 34 segundos; los 766 previos siguen pasando. Se agregaron 36 casos en `tests/test_api_reportes.py`, sobre un escenario armado por HTTP con el reloj de los adaptadores fijado en cada paso (compra y bulto verificado a L1 el 01/10, bulto rechazado a L2 el 02/10, venta con efectivo y débito el 05/10, devolución el 02/11 y mínimos en L1): el JSON completo de los cuatro reportes, importes negativos de la devolución de otro período, la agrupación por día por defecto, el período vacío, la conciliación entre R-02 y R-01, los filtros de R-03 y R-04, 22 parámetros inválidos con su campo y su código (400 o 404), 405 ante un `POST`, consultas de ventas, devoluciones, bultos, remitos, saldos, movimientos y caja idénticas antes y después de los reportes, y los mismos reportes después de reiniciar con la misma base. En `tests/test_reportes.py` se agregaron 6 casos de `importe_a_texto` con importes negativos. No hubo cambios de frontend, así que no se ejecutó `npm run build`.

Verificación de F-06.1 el 01/11/2026: **766 casos aprobados** con la suite completa, en 4 minutos 1 segundo; los 734 previos siguen pasando. Se agregaron 32 casos en `tests/test_reportes.py`, sobre datos de control armados con las operaciones reales (compra en el CD, cuatro bultos a dos locales con dos rechazos, una compra posterior que cambia el costo, tres ventas con cobros divididos y dos devoluciones en distintos períodos) y resultados calculados a mano. Cubren: los límites del período, la zona horaria y las fechas invertidas; R-01 por medio, día y local con los mismos datos, una estrategia nueva sin cambiar el contexto, la venta con dos medios sin contarla dos veces y el ingreso neto igual a la venta neta; R-02 con costos históricos distintos para el mismo producto, el costo faltante sin tomarlo como cero, la devolución de otro período que revierte su costo, el empate por identificador y la conciliación con R-01; R-03 con el mínimo exacto, el déficit, un producto con mínimo y sin stock, la separación entre disponible, bloqueado y rechazado, los filtros y el CD; R-04 con un bulto de varias líneas que cuenta una vez, el filtro de producto, el período por fecha del rechazo, el caso sin datos y el valor bloqueado que no cambia con una compra posterior; los filtros inválidos y que ningún reporte modifica las operaciones. Python `-I -S` confirma que el dominio sigue sin cargar Flask ni SQLite. No hubo cambios de frontend, así que no se ejecutó `npm run build`.

Verificación de F-05.3 el 29/10/2026: **734 casos aprobados** con la suite completa, en 2 minutos 59 segundos; los 733 previos siguen pasando y se agregó un caso en `tests/test_devoluciones.py` para el número de línea del rechazo por exceso. `npm run build` terminó correctamente. Prueba manual en el navegador integrado con el build servido por Flask en el puerto 5050 y `TP_DAO_DB` temporal, sobre la venta CV-00000001 de L1 (3 arroces y 2 fideos, 6301.00 cobrados con efectivo 4000 y débito 2301):

- sin reintegros: “La devolución debe tener al menos un reintegro.”; efectivo 2000 para un estimado de 2400.50: rechazo con la diferencia; aptitud o motivo vacíos: el navegador impide enviar;
- 1 arroz apto y 1 fideo no apto, efectivo 2000 y débito completado con el saldo (400.50): DV-00000001 confirmada, remanentes 2 y 1, reintegrable 2000.00 y 1900.50; stock de L1 con arroz 3 disponibles y fideos 1 disponible y 1 bloqueado, con “Devolución DV-00000001, línea N”; caja con los dos egresos y saldos 2000.00 y 1900.50;
- 2 fideos con 1 restante: 409 “Línea 2: quedan 1 unidades sin devolver de 002…”;
- respuesta perdida simulada: aviso de reenvío; al reenviar, “ya se había registrado como DV-00000002”, con 2 devoluciones y 5 movimientos de caja en total;
- a 375 px de ancho, sin desplazamiento horizontal.

Verificación de F-05.2 el 29/10/2026: **733 casos aprobados** con la suite completa, en 2 minutos 53 segundos; los 675 previos siguen pasando, con cuatro tests de F-02 a F-04 ajustados a las columnas nuevas (claves `devolucion_id`, `devolucion` y `reintegro` en el JSON de movimientos y caja, inserciones con columnas nombradas o `NULL` adicionales y la migración de `movimientos_stock`). Se agregaron 58 casos en `tests/test_api_devoluciones.py`, sobre una venta de L1 cobrada en efectivo y débito: devolución parcial con línea apta y no apta (JSON completo, saldos DISPONIBLE y BLOQUEADO, movimiento `DEVOLUCION`, egresos de caja y venta intacta), lo que queda por devolver y reintegrar de una venta, reinicio con clave repetida, numeración continua y exceso acumulado rechazado, clave repetida con otro contenido sin efectos, lo no apto no vendible y lo apto vendible otra vez, formato inválido (400 con campos), referencias inexistentes (404 con campo), reglas del dominio (400 o 409), local inactivo frente a producto inactivo, consultas inexistentes, fallo de guardado sin efectos y reintento, devoluciones concurrentes limitadas por lo cobrado sin duplicar claves, 22 restricciones del esquema (se comprobó que cada una falla por la restricción buscada) y migración de una base de F-04. No se modificó el frontend ni se ejecutó `npm run build`.

Verificación de F-05.1 el 29/10/2026: **675 casos aprobados** con la suite completa, en 89 segundos; los 641 previos siguen pasando. Se agregaron 34 casos en `tests/test_devoluciones.py`: devolución parcial con una línea apta y otra no apta (importes, condición de destino, movimientos `DEVOLUCION`, egresos de caja y saldos por medio), venta y comprobante intactos, lo no apto bloqueado y no vendible, lo apto vendible otra vez, devoluciones parciales sucesivas hasta el límite, un exceso acumulado en una línea que impide toda la devolución, líneas inválidas o de otra venta, reintegros que no cubren o exceden el total, medio repetido o no cobrado, límite de reintegro por medio, motivo y clave obligatorios, clave repetida sin efectos, instante anterior a la venta, ausencia de plazo, local inactivo frente a producto inactivo, precio histórico, conservación de unidades del local, sólo lectura, continuidad de identificadores y restauración. Python `-I -S` confirma que el dominio sigue sin cargar Flask ni SQLite.

Verificación de F-04.3 el 22/10/2026: no hubo cambios de backend, así que la suite sigue con los 641 casos aprobados de F-04.2 y no se volvió a ejecutar; `npm run build` terminó correctamente. Prueba manual en el navegador integrado con el build servido por Flask en el puerto 5050 y `TP_DAO_DB` temporal, con L1 abastecido por un bulto verificado (5 arroces y 3 fideos):

- venta de 2 arroces y 1 fideo con efectivo 2000 y débito completado con el saldo (1900.50): total estimado 3900.50, confirmación CV-00000001, comprobante abierto, stock de L1 en 3 y 2 y caja con efectivo 2000.00 y débito 1900.50;
- 4 arroces con 3 disponibles: 409 con “Stock insuficiente de 001 en L1”; cobros de 4000 para un total de 4500: 400 con la diferencia; cantidad 1.5: rechazada en el navegador sin enviar;
- respuesta perdida simulada (la venta llega a Python y el navegador recibe un error de red): aviso de reenvío; al reenviar, “ya se había registrado como CV-00000002”, con 2 ventas y 3 movimientos de caja en total;
- sección de stock de L1 con “Venta CV-…, línea N” como documento; a 375 px de ancho, sin desplazamiento horizontal.

La salida impresa no se comprobó en papel ni en vista previa de impresión: sólo que la regla `@media print` y la copia del comprobante estén presentes.

Verificación de F-04.2 el 22/10/2026: **641 casos aprobados** con la suite completa; los 583 previos siguen pasando, con dos tests de F-02/F-03 ajustados a las columnas nuevas de `movimientos_stock`. Se agregaron 58 casos en `tests/test_api_ventas.py`, sobre un local con stock habilitado por el circuito logístico completo: venta con cobros divididos, comprobante sin costos, movimientos `VENTA` y caja por medio; medios fijos; reinicio con clave repetida y numeración continua; clave repetida con otro contenido sin efectos; precio y costo históricos; línea sin stock y stock pendiente de verificar no vendibles; formato inválido (400 con campos), referencias inexistentes (404 con campo), reglas del dominio e inactivos; fallo de guardado sin efectos y reintento; ventas concurrentes sin sobreventa ni duplicar claves; 21 restricciones del esquema; migración de una base de F-03 con el trigger anterior. `npm run build` terminó correctamente con el cambio de la tabla de movimientos. En este equipo la suite completa tardó 25 minutos, no los dos que se registraron antes; el mayor costo son las bases SQLite temporales de los tests de API.

Verificación de F-04.1 el 21/10/2026: **583 casos aprobados** con la suite completa; los 555 previos siguen pasando. Se agregaron 28 casos en `tests/test_ventas.py`: venta de varias líneas con cobros divididos (subtotales, total, precios y costos copiados, comprobante, salida de stock y caja por medio), última unidad, una línea sin stock que impide toda la venta, stock pendiente, en tránsito, reservado o rechazado nunca vendible, venta de lo recibido sólo después de verificar bulto y remito, cobros que no cubren o exceden el total, medio repetido, importes y tipos inválidos, líneas inválidas, CD e inactivos, clave de operación repetida sin efectos y su validación, precio y costo históricos, costo faltante, sólo lectura, continuidad de identificadores, restauración y medios fijos. Python `-I -S` confirma que el dominio sigue sin cargar Flask ni SQLite. La suite completa tarda unos dos minutos por las bases SQLite temporales de los tests de API.

Verificación de F-03.3 el 21/10/2026: no hubo cambios de backend, así que la suite sigue con los 555 casos aprobados de F-03.2; `npm run build` terminó correctamente. Prueba manual en el navegador integrado con el build servido por Flask y `TP_DAO_DB` temporal:

- tres necesidades de L1 registradas y consolidadas en una orden (arroz 6 y fideos 3, sumados por producto);
- bulto con 7 de arroz rechazado por superar lo pendiente, con el borrador conservado; luego bulto de 6 y 3 preparado, con la reserva visible en el CD;
- precintado con remito R-000001 y despacho;
- recepción en L2 rechazada con el mensaje de local destino; recepción en L1 con precinto intacto;
- con el contenedor verificado, L1 mostraba 6 y 3 unidades pendientes de verificación y 0 disponibles; al verificar el remito pasaron a disponibles, y los movimientos de L1 mostraron cada cambio de condición con el bulto de origen;
- un segundo bulto hacia L2 recibido con precinto roto quedó rechazado, con el remito rechazado y el motivo visible;
- un tercer bulto anulado con confirmación liberó su reserva y la orden volvió a quedar abierta;
- a 390 px, sin desbordes horizontales fuera de las tablas desplazables.

La consola sólo registró los dos 409 provocados a propósito. No se probó con Vite en modo desarrollo ni se agregó un framework de pruebas frontend.

Verificación de F-03.2 el 21/10/2026: **555 casos aprobados** con la suite completa. Antes de editar se hizo commit de F-03.1. Se agregaron 37 casos en `tests/test_api_logistica.py`: circuito completo por API con doble verificación, reinicio después de cada etapa con comparación de todas las consultas y continuidad de IDs, rechazo persistido, transiciones inválidas con 409 sin efectos, recepción en otro local o inexistente, anulación, nueve formatos inválidos, 404, reglas del dominio como 400 o 409 sin efectos, falta de CD, precinto repetido, fallo de guardado de una transición con 500 sin cambios en memoria ni en la base, ocho preparaciones concurrentes sobre una orden de 10 (tres aceptadas), once violaciones del esquema y migración de una base de F-02. En `tests/test_api_compras.py` se actualizaron la forma del movimiento y los casos de esquema por la nueva columna; los que probaban `CHECK` pasaron a ser `UPDATE` para aislar cada restricción. Con procesos Flask reales y `TP_DAO_DB` temporal se recorrió el circuito reiniciando Flask después de cada paso logístico: el local terminó con 6 unidades disponibles, el CD con 4 y el historial con sus cinco estados. `npm run build` terminó correctamente.

Verificación de F-03.1 el 21/10/2026: **517 casos aprobados** con la suite completa; los 489 previos siguen pasando tras generalizar `MovimientoStock` (la propiedad `detalle` pasó a llamarse `documento`). Se agregaron 28 casos en `tests/test_logistica.py`: consolidación por producto con trazabilidad de necesidades, mezcla de locales, repetición y reutilización de necesidades, validaciones de necesidad, circuito completo con saldos por condición en cada paso, stock sin habilitar con el bulto verificado y el remito emitido, rechazo por precinto roto y por número distinto, recepción en otro local, todas las transiciones inválidas de los siete estados sin efectos, orden de las dos verificaciones, entregas parciales, stock insuficiente sin reservas parciales, contenido inválido, anulación con liberación de reserva, precinto único, costo de preparación histórico, conservación de unidades y la ABC no instanciable. Python `-I -S` confirma que el dominio sigue sin cargar Flask ni SQLite.

Verificación de F-02.3 el 21/10/2026: **489 casos aprobados** con la suite completa; antes de editar se hizo commit de F-02.2. En el dominio, los errores de una línea de compra ahora indican su número («Línea 2: La cantidad…»), con una aserción nueva en `tests/test_compras.py`. `npm ci` y `npm run build` terminaron correctamente. Prueba manual en el navegador integrado con el build servido por Flask y `TP_DAO_DB` temporal:

- cantidad 0 bloqueada en el cliente con el borrador conservado;
- costo con tres decimales y costo no numérico rechazados por Python, con mensaje que identifica la línea y el borrador conservado;
- compra de dos líneas confirmada con total 11356.50, stock y movimientos del CD actualizados sin recargar;
- reinicio de Flask sobre la misma base: compra, existencias y costos conservados en la pantalla;
- segunda compra con total 18803.00, saldo acumulado de 15 unidades y costo de referencia actualizado;
- a 390 px, sin desbordes horizontales fuera de las tablas desplazables.

La consola sólo registró las dos respuestas 400 provocadas a propósito. No se probó con Vite en modo desarrollo en esta etapa ni se agregó un framework de pruebas frontend.

Verificación de F-02.2 el 21/10/2026: **489 casos aprobados** con la suite completa. Antes de editar se hizo commit de F-02.1 con sus 412 casos aprobados. Se agregaron 35 casos de dominio en `tests/test_compras.py` (detalles y total, ingreso y acumulación de saldo, costo de referencia por instante e identificador, cantidades y costos inválidos, una línea inválida que bloquea toda la compra, producto repetido, destino local, instante sin zona, inactivos, saldo máximo sin cambios parciales, inmutabilidad y restauración histórica) y 42 de API y persistencia en `tests/test_api_compras.py` (contrato completo, acumulación, reinicio con inactivos y continuidad de IDs, formato y contenido inválidos sin efectos, referencias inexistentes, falta de CD, inactivos, 404, fallo de guardado con 500 sin compra ni stock en memoria o base, 16 compras concurrentes y 12 violaciones del esquema). Con un proceso Flask real y `TP_DAO_DB` temporal se registró una compra, se reinició Flask, se comprobó el stock conservado y una segunda compra acumuló 15 unidades con costo de referencia actualizado. La suite tarda unos 45 segundos porque cada escritura confirma sobre un archivo SQLite temporal. No se modificó el frontend.

Verificación de F-02.1 el 21/10/2026: **412 casos aprobados** con la suite completa (`.\.venv\Scripts\python.exe -m pytest -q`). Antes de editar se comprobaron los 396 de F-01.6 en una `.venv` nueva con las dependencias fijadas. Se agregaron 15 casos en `tests/test_persistencia_catalogo.py`: reinicio con maestros, estados, mínimos y referencias; códigos históricos y continuidad de IDs tras reiniciar; único CD y reglas de inactivos después de recargar; fallo de guardado con 500, sin cambios en memoria ni en la base; rollback de una transacción; siete violaciones del esquema; inicialización repetida; ruta predeterminada y aislamiento de la base real. El caso de precio grande de dominio y API pasó a usar el máximo representable, y se agregó el rechazo del primer valor que lo supera. `tests/conftest.py` asigna una base temporal nueva a cada `create_app()` sin ruta, de modo que las pruebas previas conservan su aislamiento. También se comprobó con un proceso Flask real y `TP_DAO_DB` temporal que un CD registrado persiste tras reiniciar y bloquea un segundo CD con 409. No se modificó el frontend.

Verificación de F-01.6 el 19/10/2026: **396 casos aprobados** con la suite completa. Antes de editar se comprobaron los 335 de F-01.5. Se agregaron 25 casos de dominio y 36 de API: bajas repetidas, consultas/filtros, identidad y referencias conservadas, códigos históricos de los cuatro tipos, modificaciones/asociaciones bloqueadas, categoría con productos activos, mínimos históricos, excepción del CD, entradas inválidas, ausencia de cambios parciales, aislamiento y concurrencia. Las carreras cubren baja repetida, alta de producto frente a baja de categoría y escritura de mínimo frente a baja de producto. Se actualizaron las expectativas exactas de DTOs anteriores para incorporar `activo`, conservando sus comprobaciones. La prueba con Python `-I -S` también desactiva entidades y consulta mínimos conservados sin paquetes externos ni carga de Flask/SQLite. No se instalaron dependencias nuevas.

Para ejecutar sólo el dominio:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_catalogo.py tests/test_proveedores.py tests/test_ubicaciones.py tests/test_minimos.py tests/test_bajas.py -q
```

Para ejecutar sólo los nuevos contratos: `.\.venv\Scripts\python.exe -m pytest tests/test_api_bajas.py -q`. Los demás archivos `test_api*.py` conservan las regresiones previas y el estado en sus respuestas.

Validación real de F-01.6 mediante el proxy Vite: confirmación y cancelación de baja, categoría bloqueada por producto activo con error visible, conservación de borradores y posterior alta, baja de producto seguida de su categoría, proveedores y local, filtros y consultas de sólo lectura. Las categorías/productos inactivos dejaron de ser opciones válidas para asociaciones/configuración. Se consultó el mínimo histórico cero de local/producto inactivos y se configuró un mínimo nuevo para otro par activo; la tabla conservó también los mínimos de productos inactivos. Las consultas HTTP directas confirmaron 200 para historia y baja repetida, 409 para edición/configuración inactiva, reutilización de código y baja del CD, 404 para inexistente y salud 200.

Se observó “Desactivando registro…” con controles deshabilitados mediante otra instancia Flask temporal en puerto 5001 con demora de un segundo sólo en los `PATCH` de estado. Se verificó el retorno del foco al filtro después del éxito. La demora y el destino de proxy de prueba sólo existieron en esos procesos; no se agregaron a la configuración del proyecto. Se detuvieron ambos servidores temporales.

`npm run build` terminó correctamente. Con Vite detenido y únicamente Flask en puerto 5000, el build permitió editar el precio de un producto activo, desactivar un proveedor, filtrarlo y consultarlo sin edición. Se comprobó el mínimo cero conservado de local/producto inactivos, con guardado bloqueado, y salud conectada. La consola de este recorrido no presentó errores ni advertencias. A 390 px se verificó mediante DOM que la página y los botones de confirmación no desbordan horizontalmente; Cancelar recibió el foco inicial y Enter canceló devolviendo el foco al filtro. Se obtuvo además una captura de la consulta histórica. La verificación de UI es manual en navegador real; no se afirma certificación completa de accesibilidad ni se agregó un framework de pruebas frontend.

Antecedente F-01.5: 335 casos aprobados, incluidos 30 de dominio y 34 de API de mínimos. Se mantienen las comprobaciones de ausencia/cero, independencia entre locales/productos, reemplazo, tipos inválidos, referencias inexistentes, rechazo del CD, precisión JSON, aislamiento y concurrencia.

Validación real de F-01.5: altas de categoría, producto, proveedor, dos locales y CD desde React mediante el proxy Vite; consulta inicial sin configurar, cero explícito, valor distinto para el mismo producto en otro local, fracción rechazada con entrada conservada y guardado con Enter. El selector excluyó al CD. Las consultas HTTP directas confirmaron valores independientes, salud 200 y CD rechazado con 400 JSON.

Se observaron “Cargando mínimos…” y “Guardando mínimo…” con controles deshabilitados durante la escritura, usando otra instancia Flask de prueba en puerto 5001 con demora de un segundo sólo para estas rutas. Se detuvo esa instancia: el proxy respondió 502 y React mantuvo local/producto/cantidad, sin mostrar éxito. Ese proceso, su configuración temporal de proxy y la demora no se incorporaron a archivos del proyecto; ambos servidores de prueba se detuvieron.

`npm run build` terminó correctamente. Con Vite y la instancia temporal detenidos, el build servido por Flask permitió consultar, modificar un mínimo a 5 y luego a 0, recargar y comprobar el cero conservado. Salud operativa y consola sin errores ni advertencias en ese recorrido. Se verificaron etiquetas, Enter/Tab y layout a 390 px mediante el DOM: campos apilados y sin desbordamiento horizontal de página. La captura de pantalla de esa comprobación móvil no estuvo disponible por un fallo de la herramienta; las verificaciones DOM y de teclado sí se ejecutaron. No se afirma certificación completa de accesibilidad ni se agregó un framework de pruebas de UI.

Validación real de F-01.4: alta de Local/CD mediante React y proxy Vite, tipos visibles en listado, segundo CD rechazado con formulario completo conservado, código duplicado entre tipos rechazado, consulta para edición con tipo fijo, nombre vacío rechazado sin alterar el listado y guardado válido con Enter manteniendo ID/tipo. Se observó carga con controles deshabilitados. También se registraron categoría, producto y proveedor desde la pantalla ampliada. Una solicitud HTTP directa a Flask para crear un segundo CD devolvió 409 JSON y conservó el catálogo.

`npm run build` terminó correctamente. Se comprobó que Vite dejó de escuchar y se abrió el build servido por Flask: alta de otro local, consulta y cambio de código/nombre del CD, recarga con registros conservados y salud conectada. La consola del recorrido del build no tuvo errores ni advertencias. A 390 px se verificaron campos apilados, etiquetas/ayuda asociadas, recorrido con Tab hasta el selector de tipo y ausencia de desbordamiento horizontal de la página. Se mantienen las limitaciones de la verificación manual de accesibilidad.

Validación real de F-01.3: alta, consulta y edición de proveedores desde React mediante el proxy Vite; alta con Enter, ceros iniciales, mismo nombre con distintos códigos, conflicto 409 al normalizar mayúsculas/espacios, nombre vacío rechazado sin perder borrador ni alterar el listado y código reemplazado reservado. Se observó “Guardando proveedor…” con controles deshabilitados. Categorías y productos se registraron correctamente desde la misma pantalla.

El build se generó correctamente con `npm run build`. Con Vite detenido, Flask sirvió el build y permitió alta/consulta/edición de un proveedor; la recarga conservó los datos. Salud directa y desde React: HTTP 200 / `{"status":"ok"}`. La consola del recorrido del build no presentó errores ni advertencias. Se verificaron etiquetas y ayuda asociadas, Enter/Tab y viewport de 390 px sin desbordamiento horizontal de la página. Las tablas conservan desplazamiento interno. La verificación de UI es manual en navegador real, sin nueva biblioteca ni certificación completa de accesibilidad.

Validación real de integración de F-01.2: creación y edición de categorías/productos desde React mediante Vite, precio de tres decimales rechazado sin perder el borrador, duplicado 409 visible, cambio de categoría y precio textual grande sin pérdida de precisión. Se comprobó la caída de Flask con error 502 y conservación del formulario, recuperación y catálogo vacío después de reiniciar. El estado de guardado y los controles deshabilitados se observaron con una demora temporal de prueba de un segundo, sólo en el proceso de verificación y sin modificar archivos del proyecto.

`npm run build` terminó correctamente. Con Vite detenido, el build servido por Flask permitió alta de categoría, consulta/edición de producto y cambio de categoría/precio; al recargar siguieron los registros. `/api/health` respondió correctamente y la consola de ese recorrido no tuvo errores ni advertencias. Se revisaron etiquetas, foco y operación con Enter/Tab, y un viewport móvil de 390 px: no hubo desbordamiento horizontal de la página; las tablas permiten desplazamiento interno. Esto no constituye una certificación completa de accesibilidad.

Guion manual reproducible, con una aplicación local de demostración:

1. Iniciar Flask y Vite con los comandos anteriores. Registrar categoría `ALM` / `Almacén` y otra `BEB` / `Bebidas`.
2. Registrar producto `001` / `Arroz`, seleccionar `ALM` e ingresar `1.230`: comprobar error y conservación del formulario. Cambiar a `125.50` y confirmar el alta.
3. Consultar/editar `ALM`, intentar cambiar el código a ` beb `: comprobar el conflicto y los datos conservados. Usar un código libre o conservar `ALM` y cambiar el nombre: comprobar el cambio en productos.
4. Consultar/editar el producto, seleccionar `BEB`, cambiar nombre/precio y guardar con Enter. Actualizar listados y recargar: los valores confirmados deben conservarse mientras siga el mismo backend.
5. Preparar un borrador y detener Flask. Intentar guardar: debe aparecer el error sin limpiar campos ni mostrar éxito. Reiniciar Flask y actualizar listados: el catálogo estará vacío; volver a registrar datos en esa nueva ejecución.
6. Registrar proveedor `0001` / `Distribuidora` y otro `ABC` con el mismo nombre. Intentar ` abc `: debe devolver conflicto conservando campos. Consultar/editar el primero; probar nombre con espacios, luego cambiar a código `0002` y nombre válido. Comprobar mismo ID y rechazo al volver a asignar `0001`.
7. Registrar ubicación `0001` / `Local Centro` de tipo Local y `CD01` / `Depósito central` de tipo CD. Intentar otro CD: comprobar error sin perder campos. Intentar un Local con código ` cd01 `: comprobar conflicto. Consultar el primer Local: el tipo debe ser fijo; probar nombre vacío y luego cambiar código/nombre válidos con Enter. El ID y el tipo deben mantenerse.
8. Registrar otro local. En mínimos, elegir el primero y un producto: comprobar “Sin configurar”. Guardar `0`: debe mostrar “0 unidades”. Elegir el segundo local y el mismo producto: sigue sin configurar; guardar `12` y volver al primero: debe conservar cero. Probar `1.5`: debe mostrar error conservando la entrada. El CD no debe figurar entre los locales seleccionables.
9. Con un borrador sin enviar, pulsar Desactivar en una categoría con producto activo. Cancelar con Enter y comprobar el borrador; volver a abrir y confirmar: debe informar conflicto sin modificar entidades ni borrar campos.
10. Desactivar primero el producto, luego su categoría; comprobar filtros Inactivos/Todos, consulta sin Guardar y referencia a la categoría conservada. Verificar que los códigos originales y reemplazados siguen rechazándose al crear otros registros. Repetir la baja por API: 200, mismo registro inactivo.
11. Desactivar un proveedor y un local con mínimo. Comprobar mínimos históricos de local/producto inactivos, incluido cero, con guardado deshabilitado. Los selectores normales deben ofrecer sólo activos y excluir siempre CD. El CD debe mostrar el motivo de bloqueo; un `PATCH` directo debe devolver 409 sin habilitar otro CD.
12. Generar el build, detener Vite y repetir edición de un maestro activo, confirmación/filtros de baja y consulta histórica en `http://127.0.0.1:5000/`. Recargar y comprobar registros/estados mientras siga el mismo Flask. Comprobar salud abriendo `http://127.0.0.1:5000/api/health`.

Resultados del incremento técnico inicial, conservados como antecedente:

| Comprobación | Resultado real |
| --- | --- |
| pytest: salud, 404 JSON, rechazo de POST, estáticos, build ausente y límites del directorio público | 8 pruebas aprobadas. |
| API directa, antes de iniciar React | HTTP 200, `application/json`, `{"status":"ok"}`. |
| React en navegador mediante proxy Vite | Conectada y JSON correcto; consola inicial sin errores ni advertencias. |
| Estado de carga | Se observó “Consultando la API…” y botón deshabilitado durante una solicitud. |
| Flask detenido | React mostró “Sin conexión con la API”; el proxy respondió HTTP 502 esperado. No se mostró éxito previo como resultado actual. |
| Recuperación | Reinicio de Flask y reintento con Enter: conexión y respuesta correctas. |
| `npm run build` | Build correcto de Vite 8.3.4. |
| Build con Vite detenido | HTML, JavaScript y salud HTTP 200 en puerto 5000; React conectado en navegador. `/api/no-existe` conservó 404 JSON. |

Esa tabla se obtuvo con el panel de estado técnico, retirado después de F-04.3. Para repetir hoy la prueba de caída: mantener Vite, detener Flask y pulsar “Actualizar listados”: debe aparecer “La última consulta del catálogo falló” con los borradores conservados; luego reiniciar Flask y volver a actualizar. El error de red/proxy durante esta prueba negativa es esperado.

Las pruebas de API usan el cliente Flask y archivos temporales; la verificación de UI se hizo en un navegador real de la tarea, sin añadir otro framework de pruebas al proyecto. Las pruebas de dominio usan objetos independientes en memoria. No se afirma cobertura porcentual ni certificación completa de accesibilidad.

## Alcance actual frente a la planificación

Estado al 01/11/2026 respecto de las fases F-00 a F-07 de `docs/PLANIFICACION_TP_POO.md` (sección I). Las decisiones aprobadas por fase están en las secciones L (F-02), M (F-03), N (F-04), O (F-05), P (F-06) y Q (F-07) de `docs/DECISIONES_F00.md`; el resto de `docs/` conserva la planificación original.

| Fase | Estado | Qué quedó implementado o qué falta |
| --- | --- | --- |
| F-00. Alcance y políticas | Parcial | DN-01 a DN-05, DN-07, DN-09, DN-10 y DN-11 aprobadas y las bases de DN-02, DN-06 y DN-08 aplicadas en F-01. Las fórmulas, períodos y costos de los reportes se adoptaron en la sección P con las propuestas de la planificación (DN-06 y DN-09), y su salida en pantalla en P.6. |
| F-01. Catálogo | Completa | Categorías, productos, proveedores, Locales/CD y mínimos por local, con baja lógica y códigos históricos (RF-01 a RF-04). |
| F-02. Persistencia, compras e inventario del CD | Completa | SQLite con `sqlite3`, compras con ingreso al CD, existencias, movimientos y costo de referencia; pantallas de compras y stock (RF-05, RF-21). |
| F-03. Circuito logístico con State | Completa | Necesidades, órdenes por destino, bultos con patrón State, remito, precinto, despacho, recepción, doble verificación y rechazo (RF-06 a RF-13). |
| F-04. Venta, cobro y comprobante | Completa | Ventas multilínea, cobros divididos, caja por medio, comprobante `CV-…` y clave contra envíos repetidos (RF-14 a RF-16; la parte de ventas de RF-18). |
| F-05. Devoluciones | Completa | Dominio (F-05.1), persistencia y API (F-05.2) y pantalla (F-05.3) de devoluciones parciales con aptitud por línea (apto a DISPONIBLE, no apto a `BLOQUEADO`), reintegro por medio cobrado y egresos de caja (RF-17 y la parte de devoluciones de RF-18). |
| F-06. Cuatro reportes y Strategy | Completa | F-06.1: cálculo de R-01 a R-04 en el dominio, con Strategy para agrupar R-01 (segundo patrón de RT-04) y margen estimado como resultado económico del período (RF-19, RF-20). F-06.2: API de sólo lectura de los cuatro reportes. F-06.3: vista Reportes en pantalla, sin exportación a PDF ni CSV (P.6). |
| F-07. Integración y entrega | En curso | F-07.1: escenarios integrales feliz, de bloqueo, de rechazo y transaccional con el dataset de control J.3 (T-31). F-07.2: backend sólo Python y SQL con parámetros comprobados sobre el repositorio (T-29, T-30), y comandos de ejecución, build servido por Flask y reinicio verificados. Falta la revisión del modelo y los artefactos de entrega (F-07.3), que dependen de la rúbrica (G-06). |

Después de F-04.3 se reorganizó la pantalla React sin cambiar el alcance: navegación por grupos (Catálogo, Operaciones, Consultas) con una ruta en el hash por vista (`#/productos`) y sin el panel de estado técnico de conexión; `GET /api/health` sigue disponible en la API.

Siguen abiertas las consultas docentes G-01 (si el ingreso manual de compras y el margen estimado alcanzan), G-02 (orden multilocal), G-03 (un remito por bulto), G-04 / DN-08 (si se exige borrado físico además de la baja lógica), G-06 (rúbrica y formato de entrega) y el formato del comprobante. No se implementan pagos a proveedores, recepciones parciales, costo promedio o FIFO, órdenes de compra sugeridas (OP-01, opcional), alertas por mínimos, autenticación ni ORM.
