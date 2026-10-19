# TP DAO 2026 — catálogo y mínimos por local React/API (F-01.5)

React + Vite y API Flask Python permiten registrar, consultar y modificar categorías, productos, proveedores y ubicaciones del catálogo POO, y configurar mínimos por producto/local. Las ubicaciones distinguen Locales y Centro de Distribución. `GET /api/health` sigue devolviendo HTTP 200 y `{"status":"ok"}` como comprobación técnica de disponibilidad.

Los datos se administran temporalmente en memoria desde Python. Los mínimos son configuración administrativa; no hay existencias reales, movimientos, alertas ni reposición. Tampoco hay bajas, compras, relaciones producto–proveedor, logística, ventas, devoluciones, reportes, autenticación, ORM ni esquema SQLite.

## Estructura

```text
backend/
  __init__.py          fábrica Flask y servido del frontend compilado
  api.py               Blueprint /api y endpoint técnico de salud
  api_catalogo.py      HTTP/JSON de maestros y configuración de mínimos
  dominio/
    __init__.py        clases del catálogo y excepción de código duplicado
    catalogo.py        objetos, registro en memoria y validaciones
  requirements.txt     dependencia de ejecución Python
  requirements-dev.txt dependencia de pruebas
frontend/
  src/
    App.jsx            datos consultados y coordinación de la pantalla
    SeccionCatalogo.jsx listados y consulta para edición
    SeccionMinimos.jsx configuración y consulta por producto/local
    FormularioCatalogo.jsx formularios del catálogo; tipo fijo al editar ubicación
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
pytest.ini
docs/                  enunciado y planificación previa, conservados
```

La presentación HTTP vive en `backend/api.py` y `backend/api_catalogo.py`; la creación/configuración de Flask, en `backend/__init__.py`; el dominio, en `backend/dominio`. Los imports HTTP se ejecutan al llamar a `create_app`, por lo que importar y usar el dominio no requiere Flask instalado. React captura datos y presenta respuestas de Python. Node ejecuta herramientas frontend; no hay backend, SSR, BFF, reglas ni persistencia en Node.

## F-01.1: contrato del catálogo en memoria

`Catalogo` registra objetos, asigna identificadores técnicos y permite consultar por identificador o código. `Categoria` mantiene código/nombre; `Producto` mantiene código/nombre, una referencia a categoría registrada y precio ARS. Los objetos colaboran con su catálogo para controlar unicidad también al modificarse directamente mediante sus métodos públicos.

Crear los registros mediante `Catalogo.crear_categoria` y `Catalogo.crear_producto`. Los identificadores son enteros positivos, secuenciales dentro de cada tipo y catálogo, y no se reasignan al editar. No son identificadores persistentes ni globales entre ejecuciones. La categoría debe ser la instancia registrada en ese mismo catálogo: una instancia externa con igual ID no es válida.

Los códigos y nombres son textos no vacíos, recortados en sus extremos. La comparación de códigos usa `casefold()`; conserva ceros iniciales y la escritura del código almacenado. La unicidad es por tipo, no por nombre. Los códigos pueden modificarse mediante las operaciones validadas; las búsquedas reflejan el código vigente.

Los precios de entrada son **textos en pesos ARS**: `"12"`, `"12.5"` o `"12.50"`. Se utiliza punto decimal, sin separadores de miles, signos ni notación científica. No se aceptan `float`, enteros u otros tipos como entrada para evitar ambigüedad entre pesos y centavos. Se rechazan cero, negativos y más de dos decimales, incluso `"1.230"`; no se redondea. `precio_centavos` devuelve un entero exacto y `precio` devuelve texto con dos decimales. Conversión y formato utilizan enteros y cadenas, sin punto flotante ni dependencias adicionales.

Las propiedades de los objetos son de lectura; las modificaciones pasan por `modificar` o `cambiar_precio`. `Catalogo.modificar_categoria` recibe ID, código y nombre; `Catalogo.modificar_producto` recibe ID, código, nombre, categoría y precio. Validan todos los datos antes de cambiar el estado y conservan la misma instancia. Renombrar una categoría se refleja en los productos que la referencian. No hay métodos de baja ni reactivación.

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

**Los códigos de proveedores no se reutilizan durante la vida del catálogo.** Se puede mantener el código vigente, incluso cambiar su capitalización, o sustituirlo por uno nunca registrado. El reemplazado queda reservado: no puede asignarse a otro proveedor ni recuperarse para el original. Las búsquedas por código consultan sólo el código vigente. Una operación inválida no reserva códigos ni consume IDs. El registro de códigos históricos pertenece a `Catalogo`, no al frontend ni al adaptador HTTP. No se modificó la política previa de códigos de categorías/productos.

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

- `establecer_minimo(local_id, producto_id, minimo)` valida ambos IDs contra este catálogo, exige ubicación `LOCAL` y entero no negativo, reemplaza el valor del par y devuelve el entero confirmado. Repetir la operación no agrega configuraciones.
- `obtener_minimo(local_id, producto_id)` valida las mismas referencias y devuelve `None` si no hay configuración, o el entero, incluido `0`.
- `listar_minimos(local_id)` valida el local y devuelve una tupla de pares `(producto registrado, minimo)` sólo de ese local, sin exponer el diccionario interno. Un local sin configuraciones devuelve `()`.

El mismo producto puede tener valores independientes en varios locales. Se rechazan negativos, `float` incluso como `1.0`, booleanos, textos y otros tipos. Una referencia inexistente produce `KeyError`; el CD se rechaza con `ValueError` tanto para consulta como para escritura. Validar todo antes de asignar evita cambios parciales. Los cambios administrativos de código/nombre no afectan la configuración porque se mantienen los IDs; las consultas muestran los datos actuales de los objetos.

```python
assert catalogo.obtener_minimo(local.identificador, producto.identificador) is None
catalogo.establecer_minimo(local.identificador, producto.identificador, 0)
assert catalogo.obtener_minimo(local.identificador, producto.identificador) == 0
catalogo.establecer_minimo(local.identificador, producto.identificador, 8)
assert catalogo.listar_minimos(local.identificador) == ((producto, 8),)
```

Convenciones confirmadas por el pedido para las fases que tengan existencias reales: **en el mínimo** significa disponible `<=` mínimo; **faltante**, disponible `<` mínimo; **déficit**, `max(mínimo - disponible, 0)`. Se aplicarán con mínimo configurado y existencia real. Hoy no se calculan ni se muestran esos indicadores, ni se toma ausencia de configuración como cero o un mínimo como cantidad disponible.

## API HTTP/JSON de F-01.2 a F-01.5

La API valida el formato del transporte y delega creación, modificación, unicidad, referencias y precios al dominio. Los cuerpos de escritura deben ser objetos JSON con todos los campos indicados y sin campos adicionales. `id` técnico y `codigo` comercial son conceptos distintos. `PUT` reemplaza los campos editables completos; no hay `PATCH` ni `DELETE` de catálogo.

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

Las dos rutas de mínimos siguen las ubicaciones/productos existentes y usan sus IDs. `GET` devuelve, por ejemplo:

```json
{
  "ubicacion": {"id": 1, "codigo": "L1", "nombre": "Centro", "tipo": "LOCAL"},
  "minimos": [
    {"producto": {"id": 1, "codigo": "001", "nombre": "Arroz"}, "minimo": 0}
  ]
}
```

Un producto registrado sin configuración **no tiene fila** en `minimos`; una lista vacía significa que ese local no tiene mínimos configurados. Un cero explícito sí tiene fila con `"minimo":0`. No se inventan configuraciones cero para completar productos ausentes. La UI cruza este listado con los productos del catálogo y muestra “Sin configurar” sólo después de una consulta exitosa.

`PUT` recibe `{"minimo":8}` y devuelve `{"ubicacion":{...},"producto":{"id":1,"codigo":"001","nombre":"Arroz"},"minimo":8}`. Devuelve 200 también al establecer por primera vez: es la asignación repetible de un recurso identificado por el par, no un alta con ID nuevo. No hay endpoint para borrar/desconfigurar el mínimo ni para consultar inventario.

El transporte HTTP admite mínimos entre `0` y `9007199254740991` (`2**53 - 1`), para conservar el entero exacto en JSON/JavaScript. Python mantiene enteros no negativos sin ese límite del cliente. El adaptador rechaza con 400 valores superiores, tanto al recibir como al serializar configuraciones creadas directamente desde Python, evitando redondeos silenciosos; el límite no cambia precios ni otros contratos. `true`, `1.0`, `"8"`, `null`, campos extra y JSON inválido producen 400. Un local/producto inexistente produce 404 y el CD produce 400. No se modifican configuraciones ante estos errores.

Para proveedores, alta y modificación reciben únicamente `{"codigo":"0001","nombre":"Distribuidora"}` y devuelven `{"id":1,"codigo":"0001","nombre":"Distribuidora"}`. Un código vigente duplicado o uno histórico reservado produce 409; no se serializan el catálogo, sus reservas ni atributos privados. Los campos faltantes, adicionales o de tipo incorrecto producen 400.

Ejemplo de alta de ubicación: `{"codigo":"0001","nombre":"Local Centro","tipo":"LOCAL"}`; respuesta: `{"id":1,"codigo":"0001","nombre":"Local Centro","tipo":"LOCAL"}`. Para el CD se usa `"tipo":"CD"`. El `PUT` recibe únicamente `{"codigo":"0002","nombre":"Local Norte"}`: enviar `tipo` o `id`, aunque sean los valores actuales, produce 400 por campo no editable. La respuesta siempre incluye el tipo confirmado por Python.

El intento de registrar un segundo CD produce 409 JSON con `error.fields.tipo`; un código de ubicación duplicado o reservado produce 409 con `error.fields.codigo`. La API usa las excepciones del dominio, sin repetir esas reglas. Todas las operaciones y su serialización usan el mismo catálogo y bloqueo existentes.

Una categoría se representa como `{"id":1,"codigo":"ALM","nombre":"Almacén"}`. Un producto incluye su categoría actual y el precio decimal como texto:

```json
{
  "id": 1,
  "codigo": "001",
  "nombre": "Arroz",
  "categoria": {"id": 1, "codigo": "ALM", "nombre": "Almacén"},
  "precio": "125.50",
  "moneda": "ARS"
}
```

Ejemplo de cuerpo para registrar o modificar un producto: `{"codigo":"001","nombre":"Arroz","categoria_id":1,"precio":"125.50"}`. No se recibe un objeto categoría inventado: Python busca la instancia registrada por ID. No se envían importes JSON numéricos ni atributos privados. Las respuestas se construyen desde el objeto realmente registrado, con código/nombre recortados y precio canónico.

| Estado | Significado |
| --- | --- |
| 400 | JSON mal formado, objeto/campos/tipos incorrectos o datos rechazados por el dominio. |
| 404 | Categoría/producto/proveedor/ubicación inexistente, incluida la categoría referida por un producto. |
| 409 | Código duplicado en el catálogo, código histórico de proveedor/ubicación o intento de registrar un segundo CD. |
| 415 | Cuerpo no enviado como `application/json`. |
| 405 | Método no disponible; se conserva la cabecera `Allow`. |
| 500 | Fallo inesperado; respuesta genérica sin detalle interno ni éxito falso. |

Los errores usan `{"error":{"code":400,"message":"..."}}`, con `fields` opcional para señalar campos del formulario. Ejemplo de conflicto: `{"error":{"code":409,"message":"Ya existe una categoría con ese código.","fields":{"codigo":"Ya existe una categoría con ese código."}}}`. Las trazas y objetos internos no se serializan al cliente.

Los IDs de ruta enteros pero inválidos, como `0`, producen 400 por validación de dominio. Un entero positivo inexistente produce 404; rutas con segmentos que no coinciden con el conversor entero de Flask también producen 404 JSON.

## Memoria, pantalla y límites actuales

`create_app` crea un `Catalogo` en `app.extensions["catalogo"]` y un `Lock` propio. La API utiliza esa misma instancia entre solicitudes; el bloqueo abarca las operaciones de dominio y la construcción de las respuestas para evitar carreras sobre códigos, IDs y referencias. No hay Singleton ni catálogo global compartido entre aplicaciones. Los tests crean aplicaciones aisladas.

**Reiniciar Flask elimina todos los registros, mínimos y reservas de códigos de proveedores/ubicaciones.** La no reutilización y el máximo de un CD están garantizados en esta memoria, no entre ejecuciones o procesos independientes. Recargar React conserva los registros del backend, pero descarta los borradores locales. Cada proceso/aplicación tiene su propia memoria; no se usa esta solución como almacenamiento compartido entre workers o instalaciones. SQLite se mantiene para F-02, donde deberán persistirse también mínimos, reservas y la restricción del CD.

La pantalla consulta categorías/productos/proveedores/ubicaciones, ofrece selectores de categorías registradas para productos y permite consultar por ID antes de editar. Proveedores y ubicaciones reutilizan `SeccionCatalogo`, `FormularioCatalogo`, `fetch` y estilos. En ubicaciones, el alta tiene selector de tipo y el listado diferencia Local/CD; al editar, el tipo aparece como texto fijo. El segundo CD se rechaza desde Python con un mensaje junto al selector; las opciones permanecen disponibles para que ese control siga siendo efectivo aun con información cliente desactualizada.

Conserva los campos ante un error, muestra carga/éxito/error/vacío y bloquea envíos mientras están pendientes. La ayuda del código de proveedor/ubicación explica su reserva al reemplazarlo. Los precios permanecen como texto; no se calculan ni redondean en JavaScript. Después de guardar se reconsultan los listados, incluyendo los nombres actuales de categorías referenciadas. Un fallo de esa lectura se informa por separado del guardado ya confirmado.

`SeccionMinimos` tiene selectores de locales registrados (excluye CD) y productos con código/nombre, muestra el mínimo vigente y el listado de configuraciones del local, y permite establecer o reemplazar un valor. Distingue ausencia, cero, carga y error; no afirma “Sin configurar” si falló la consulta. Conserva la entrada ante errores, cancela consultas obsoletas y bloquea los controles durante el guardado. Tras confirmar, usa la respuesta de Python para actualizar el par sin duplicarlo. “Actualizar mínimos” vuelve a consultar el local; las actualizaciones de maestros también reconsultan sus configuraciones sin borrar el borrador numérico. Cambiar manualmente de local o producto limpia ese borrador para trabajar sobre la nueva selección.

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

Abrir [frontend de desarrollo](http://127.0.0.1:5173/). La pantalla permite administrar categorías, productos, proveedores, ubicaciones y mínimos por local. El estado de salud permanece accesible en “Estado técnico de conexión”. Los comandos de desarrollo se conservan en F-01.5.

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

Antes de compilar, `/` devuelve 404 y `/api/health` funciona igualmente. No se implementó un router SPA: rutas no definidas y archivos inexistentes devuelven 404. Los errores bajo `/api` son JSON y nunca se reemplazan por HTML. Sólo se publican el índice y los recursos de `dist/assets`, no el repositorio ni archivos privados.

`npm run preview` está disponible para inspeccionar estáticos, pero no configura este proxy ni reemplaza la demostración con Python. Los servidores usados son de desarrollo local, no un despliegue de producción.

## Pruebas y resultados

Desde la raíz:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Verificación de F-01.5 el 19/10/2026: **335 casos aprobados**. Antes de editar se comprobaron los 271 de F-01.4. Se agregaron 30 casos de dominio y 34 de API de mínimos: ausencia/cero, independencia entre locales/productos, reemplazo repetido, tipos/valores inválidos, referencias inexistentes, rechazo del CD, ausencia de cambios parciales, precisión de enteros JSON, aislamiento y concurrencia. Se conservan las regresiones de categorías/productos/proveedores/ubicaciones y salud. La prueba con Python `-I -S` también consulta y establece mínimos sin paquetes externos ni carga de Flask/SQLite. No se instalaron dependencias nuevas.

Para ejecutar sólo el dominio:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_catalogo.py tests/test_proveedores.py tests/test_ubicaciones.py tests/test_minimos.py -q
```

Para ejecutar sólo los nuevos contratos: `.\.venv\Scripts\python.exe -m pytest tests/test_api_minimos.py -q`. Los demás archivos `test_api*.py` conservan los contratos previos.

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
9. Generar el build, detener Vite y repetir consulta/modificación de mínimos en `http://127.0.0.1:5000/`. Recargar, volver a seleccionar el par y comprobar el valor confirmado. Abrir la sección técnica y comprobar salud.

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

Los tres Markdown de `docs/` y los originales académicos se conservaron sin cambios. Sus frases “sin implementación” describen la planificación anterior; las instrucciones posteriores del usuario autorizaron la base técnica y F-01.1 a F-01.5. JavaScript fue elegido para el frontend. Este README registra el estado actual sin presentar las fases restantes como implementadas.

Para F-01.1 quedaron aprobados identificadores y normalización de categorías/productos, categoría registrada obligatoria, precio positivo exacto en ARS, alta/consulta/modificación y almacenamiento temporal. El pedido de F-01.3 confirmó identidad y datos de proveedores. F-01.4 autorizó `Ubicacion`, Local/CD, códigos con reservas, ID/tipo inmutables y máximo de un CD. F-01.5 confirmó DN-06 para mínimos: enteros no negativos, ausencia distinta de cero, ámbito producto/local sin CD y convenciones futuras de umbral/déficit. La representación HTTP usa el rango entero exacto documentado; es una decisión técnica de interoperabilidad. No se extrapoló la unidad a movimientos aún no definidos. DN-08, DN-09 (costos/fechas/economía), identificadores de documentos posteriores y DN-11 mantienen sus pendientes.

F-01.1 a F-01.5 están completos; F-01 completa aún no está terminada. Para preparar F-01.6, acordar DN-08: entidades alcanzadas por bajas, baja administrativa o borrado físico permitido, tratamiento de referencias y mínimos existentes, consultas/selecciones de inactivos y eventual reactivación. Conservar las identidades y reservas de códigos ya aprobadas; definir los casos de baja con referencias antes de implementar. No se inició F-01.6 ni se incorporó SQLite.
