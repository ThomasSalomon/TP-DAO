# TP DAO 2026 — catálogo, compras, logística CD–locales y ventas en SQLite (F-04.2)

React + Vite y API Flask Python permiten registrar, consultar, modificar y desactivar lógicamente categorías, productos, proveedores y locales del catálogo POO, y configurar mínimos por producto/local. Las ubicaciones distinguen Locales y Centro de Distribución (CD). El CD se puede registrar, consultar y editar, pero su baja queda bloqueada hasta aprobar una política de reemplazo. `GET /api/health` sigue devolviendo HTTP 200 y `{"status":"ok"}` como comprobación técnica de disponibilidad.

Desde F-02.1 el catálogo, sus estados, los mínimos, las reservas de códigos y la restricción de un único CD se guardan en SQLite mediante `sqlite3` y SQL parametrizado, y se conservan al reiniciar Flask. Desde F-02.2 la API registra compras a proveedores que ingresan su stock como disponible en el CD, con movimientos trazables y costo de referencia por producto (sección F-02.2). Desde F-02.3 la pantalla React permite registrar esas compras y consultar el stock y los movimientos del CD. Los mínimos siguen siendo configuración administrativa: no hay alertas, reposición ni stock en los locales. No hay eliminación física, reactivación, relaciones producto–proveedor, logística, ventas, devoluciones, reportes, autenticación ni ORM. Las decisiones DN-03, DN-09 y DN-11 aprobadas para F-02 están en la sección L de `docs/DECISIONES_F00.md`.

## Estructura

```text
backend/
  __init__.py          fábrica Flask y servido del frontend compilado
  api.py               Blueprint /api y endpoint técnico de salud
  api_catalogo.py      HTTP/JSON de maestros y configuración de mínimos
  api_compras.py       HTTP/JSON de compras, existencias, saldos y movimientos
  api_logistica.py     HTTP/JSON de necesidades, órdenes, bultos y remitos
  api_ventas.py        HTTP/JSON de ventas, comprobante, medios de pago y caja por local
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
    caja.py            Caja y MovimientoCaja por local y medio de pago
  persistencia/
    __init__.py        funciones públicas de acceso a datos
    base_datos.py      conexión, esquema, ruta y transacciones SQLite
    catalogo_sqlite.py carga del catálogo y guardado de cada maestro
    compras_sqlite.py  carga y guardado de compras
    inventario_sqlite.py saldos y movimientos de stock
    logistica_sqlite.py necesidades, órdenes, bultos, eventos y remitos
    ventas_sqlite.py   ventas, líneas, cobros y movimientos de caja
  requirements.txt     dependencia de ejecución Python
  requirements-dev.txt dependencia de pruebas
frontend/
  src/
    App.jsx            datos consultados y coordinación de la pantalla
    SeccionCatalogo.jsx filtros, consulta, edición y confirmación de baja
    SeccionMinimos.jsx configuración activa y consulta histórica por producto/local
    SeccionCompras.jsx borrador de compra con líneas, confirmación y compras registradas
    SeccionLogistica.jsx carga de necesidades, órdenes, bultos y remitos y operaciones de a una
    PanelReposicion.jsx necesidades de los locales y consolidación de órdenes
    PanelBultos.jsx    preparación, acciones por estado, doble verificación e historial
    SeccionStock.jsx   saldos por condición, costo de referencia y movimientos por ubicación
    etiquetas.js       textos de estados y condiciones devueltos por Python
    FormularioCatalogo.jsx formularios y consultas de inactivos sin edición
    EstadoConexion.jsx estado técnico secundario
    api.js             cliente fetch, errores y cancelación
    styles.css         presentación responsive
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
tests/conftest.py      base temporal por aplicación; los tests nunca usan la base real
pytest.ini
docs/                  enunciado y planificación previa, conservados
```

La presentación HTTP vive en `backend/api.py` y `backend/api_catalogo.py`; la creación/configuración de Flask, en `backend/__init__.py`; el dominio, en `backend/dominio`; el acceso a SQLite, en `backend/persistencia`. El dominio no importa SQLite ni Flask. Los imports HTTP se ejecutan al llamar a `create_app`, por lo que importar y usar el dominio no requiere Flask instalado. React captura datos y presenta respuestas de Python. Node ejecuta herramientas frontend; no hay backend, SSR, BFF, reglas ni persistencia en Node.

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

Aplica las decisiones de la sección N de `docs/DECISIONES_F00.md`. F-04.2 agrega su persistencia y su API; la pantalla de ventas llega con F-04.3.

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

El cliente `fetch` tiene un límite de 10 segundos, cancela lecturas obsoletas y no reintenta escrituras automáticamente. Si no se pudo confirmar una escritura por un fallo de conexión, consultar el listado antes de reenviar. “Actualizar listados” y “Actualizar mínimos” permiten consultar cambios hechos desde otra pestaña; no hay actualización en tiempo real ni resolución de conflictos entre ediciones. Los `PUT` al mismo mínimo se serializan: queda el último procesado. El estado técnico de `/api/health` está disponible en una sección desplegable secundaria.

## Versiones utilizadas

| Componente | Versión verificada |
| --- | --- |
| Python | 3.11.2, disponible mediante `py -3.11` |
| Flask | 3.1.3 |
| pytest | 9.1.1 |
| Node.js | 22.14.0 |
| npm | 11.6.0 |
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

El comando `python` del entorno inspeccionado apunta al alias de Microsoft Store. Por eso se usa el lanzador `py` al crear el entorno y luego el ejecutable de `.venv`, sin depender de activar scripts de PowerShell. Para ejecutar sólo el backend se puede instalar `backend/requirements.txt`; el archivo de desarrollo incluye Flask y pytest.

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

Abrir [frontend de desarrollo](http://127.0.0.1:5173/). La pantalla permite administrar categorías, productos, proveedores, ubicaciones y mínimos por local. El estado de salud permanece accesible en “Estado técnico de conexión”. Los comandos de desarrollo se conservan en F-01.6.

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

Si Flask ya está ejecutándose, no iniciar otra instancia: alcanza con generar el build. Detener Vite y abrir [frontend compilado](http://127.0.0.1:5000/). Flask sirve `index.html`, los recursos de `/assets` y la API desde el mismo origen. Las solicitudes relativas `/api/health` siguen funcionando; Node no participa en la ejecución del backend ni del build ya servido.

La base predeterminada queda fuera de la carpeta del repositorio, que puede estar sincronizada con OneDrive: no sincronizar ni compartir un archivo SQLite abierto. Para empezar con datos vacíos, detener Flask y usar otra ruta en `TP_DAO_DB` o borrar ese archivo manualmente.

Antes de compilar, `/` devuelve 404 y `/api/health` funciona igualmente. No se implementó un router SPA: rutas no definidas y archivos inexistentes devuelven 404. Los errores bajo `/api` son JSON y nunca se reemplazan por HTML. Sólo se publican el índice y los recursos de `dist/assets`, no el repositorio ni archivos privados.

`npm run preview` está disponible para inspeccionar estáticos, pero no configura este proxy ni reemplaza la demostración con Python. Los servidores usados son de desarrollo local, no un despliegue de producción.

## Pruebas y resultados

Desde la raíz:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

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
12. Generar el build, detener Vite y repetir edición de un maestro activo, confirmación/filtros de baja y consulta histórica en `http://127.0.0.1:5000/`. Recargar y comprobar registros/estados mientras siga el mismo Flask. Abrir la sección técnica y comprobar salud.

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

Para repetir la prueba de caída: mantener Vite, detener Flask y pulsar “Volver a comprobar”; luego reiniciar Flask y reintentar. El error de red/proxy durante esta prueba negativa es esperado.

Las pruebas de API usan el cliente Flask y archivos temporales; la verificación de UI se hizo en un navegador real de la tarea, sin añadir otro framework de pruebas al proyecto. Las pruebas de dominio usan objetos independientes en memoria. No se afirma cobertura porcentual ni certificación completa de accesibilidad.

## Alcance actual frente a la planificación

F-01 (catálogo) y F-02 están completas. F-02.1 persiste el catálogo en SQLite, F-02.2 agrega compras, ingreso al CD, existencias, movimientos y costo de referencia por API y F-02.3 sus pantallas React, con las decisiones DN-03, DN-09 y DN-11 aprobadas el 21/10/2026. El detalle de lo aprobado está en la sección L de `docs/DECISIONES_F00.md`; los demás documentos de `docs/` conservan la planificación original.

F-02 queda completa con F-02.3: pantallas React de compras y de stock y movimientos del CD.

Siguen abiertas las aclaraciones docentes G-01 (si el ingreso manual de compras y el margen estimado alcanzan) y DN-08 (si se exige borrado físico además de la baja lógica).

F-03 está completa: F-03.1 (dominio con State y doble verificación), F-03.2 (SQLite y API) y F-03.3 (pantallas React del circuito). F-04 está en curso: F-04.1 (dominio de ventas, cobros, caja y comprobante) y F-04.2 (SQLite y API) están implementadas; falta F-04.3 (pantallas). Siguen abiertas las consultas docentes G-02 (orden multilocal) y G-03 (un remito por bulto). Fuera de F-04: devoluciones (F-05) y reportes con Strategy (F-06). No hay pagos a proveedores, recepciones parciales ni costo promedio o FIFO.
