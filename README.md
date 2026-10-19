# TP DAO 2026 — base técnica y dominio F-01.1

Base ejecutable de React + Vite y API Flask Python. La única operación de la API es `GET /api/health`, que devuelve HTTP 200 y `{"status":"ok"}`. Es una comprobación de disponibilidad HTTP; no consulta bases de datos ni comprueba procesos comerciales.

F-01.1 incorpora categorías y productos de dominio, administrados en memoria desde Python. Todavía no hay endpoints ni pantallas de catálogo. No contiene proveedores, ubicaciones, mínimos, compras, inventario, logística, ventas, devoluciones, reportes, autenticación, ORM ni esquema SQLite.

## Estructura

```text
backend/
  __init__.py          fábrica Flask y servido del frontend compilado
  api.py               Blueprint /api y endpoint técnico de salud
  dominio/
    __init__.py        exportación de Catalogo, Categoria y Producto
    catalogo.py        objetos, registro en memoria y validaciones
  requirements.txt     dependencia de ejecución Python
  requirements-dev.txt dependencia de pruebas
frontend/
  src/                 vista React, cliente fetch y estilos mínimos
  vite.config.js       proxy transparente y configuración de desarrollo
  .env.example         ejemplo público de configuración
  package.json
  package-lock.json
tests/test_api.py      pruebas HTTP y de estáticos con pytest
tests/test_catalogo.py pruebas de dominio e independencia de frameworks
pytest.ini
docs/                  enunciado y planificación previa, conservados
```

La presentación HTTP vive en `backend/api.py`; la creación/configuración de Flask, en `backend/__init__.py`; el dominio, en `backend/dominio`. Los imports HTTP se ejecutan al llamar a `create_app`, por lo que importar y usar el dominio no requiere Flask instalado. React sólo muestra el estado técnico y la respuesta del servidor. Node ejecuta herramientas frontend; no hay backend, SSR, BFF, reglas ni persistencia en Node.

## F-01.1: contrato del catálogo en memoria

`Catalogo` registra objetos, asigna identificadores técnicos y permite consultar por identificador o código. `Categoria` mantiene código/nombre; `Producto` mantiene código/nombre, una referencia a categoría registrada y precio ARS. Los objetos colaboran con su catálogo para controlar unicidad también al modificarse directamente mediante sus métodos públicos.

Crear los registros mediante `Catalogo.crear_categoria` y `Catalogo.crear_producto`. Los identificadores son enteros positivos, secuenciales dentro de cada tipo y catálogo, y no se reasignan al editar. No son identificadores persistentes ni globales entre ejecuciones. La categoría debe ser la instancia registrada en ese mismo catálogo: una instancia externa con igual ID no es válida.

Los códigos y nombres son textos no vacíos, recortados en sus extremos. La comparación de códigos usa `casefold()`; conserva ceros iniciales y la escritura del código almacenado. La unicidad es por tipo, no por nombre. Los códigos pueden modificarse mediante las operaciones validadas; las búsquedas reflejan el código vigente.

Los precios de entrada son **textos en pesos ARS**: `"12"`, `"12.5"` o `"12.50"`. Se utiliza punto decimal, sin separadores de miles, signos ni notación científica. No se aceptan `float`, enteros u otros tipos como entrada para evitar ambigüedad entre pesos y centavos. Se rechazan cero, negativos y más de dos decimales, incluso `"1.230"`; no se redondea. `precio_centavos` devuelve un entero exacto y `precio` devuelve texto con dos decimales. Conversión y formato utilizan enteros y cadenas, sin punto flotante ni dependencias adicionales.

Las propiedades de los objetos son de lectura; las modificaciones pasan por `modificar` o `cambiar_precio`. `Catalogo.modificar_categoria` recibe ID, código y nombre; `Catalogo.modificar_producto` recibe ID, código, nombre, categoría y precio. Validan todos los datos antes de cambiar el estado y conservan la misma instancia. Renombrar una categoría se refleja en los productos que la referencian. No hay métodos de baja ni reactivación.

`obtener_categoria` y `obtener_producto` buscan por ID y producen `KeyError` si no existe. `buscar_categoria_por_codigo` y `buscar_producto_por_codigo` devuelven el objeto o `None`. Un tipo incorrecto produce `TypeError`; datos inválidos, duplicados o categorías ajenas producen `ValueError`. Los listados son tuplas que protegen la colección; contienen las mismas referencias a objetos, no copias editables sin validación.

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

Cada instancia de `Catalogo` tiene sus propios registros. Los datos sólo viven en memoria: reiniciar Python o crear otro catálogo no los recupera. No se implementaron almacenamiento, concurrencia HTTP ni integración con la fábrica Flask. El dominio puede usarse con Python estándar, sin instalar dependencias; pytest sigue siendo necesario para ejecutar sus pruebas.

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

Abrir [frontend de desarrollo](http://127.0.0.1:5173/). La vista consulta automáticamente la API y permite volver a comprobarla. Muestra carga, respuesta JSON o error recuperable. El límite de espera es de 10 segundos; al desmontarse la vista se cancela la solicitud pendiente.

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

Verificación de F-01.1 el 19/10/2026: **90 casos aprobados**, correspondientes a 82 casos nuevos de catálogo y las 8 pruebas existentes. Se cubren normalización/duplicados, ceros, identidad, tipos, precios exactos, referencias, altas y modificaciones fallidas sin cambios parciales. Una prueba ejecuta un proceso Python con `-I -S`, sin paquetes externos, y comprueba que el dominio funciona sin cargar Flask ni `sqlite3`.

Para ejecutar sólo el dominio:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_catalogo.py -q
```

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

Los tres Markdown de `docs/` y los originales académicos se conservaron sin cambios. Sus frases “sin implementación” describen la planificación anterior; las instrucciones posteriores del usuario autorizaron primero la base técnica y después F-01.1. JavaScript fue elegido para el frontend. Este README registra el estado actual sin presentar las fases restantes como implementadas.

Para F-01.1 quedaron aprobados identificadores y normalización de categorías/productos, categoría registrada obligatoria, precio positivo exacto en ARS, alta/consulta/modificación y almacenamiento temporal. El resto de DN-02 (otros maestros), DN-06 (unidades/mínimos), DN-08 (bajas de F-01.6), DN-09 (costos/fechas/economía) y DN-11 mantiene sus pendientes.

F-01.1 está completo como subincremento de dominio; F-01 completa aún no está terminada. F-01.2 requiere nueva autorización y definir las rutas/datos/errores HTTP de categorías/productos, la vida del catálogo en memoria dentro de cada aplicación y los formularios React mínimos. Se conserva `/api/health`; no se incorpora SQLite, compra ni otra fase automáticamente.
