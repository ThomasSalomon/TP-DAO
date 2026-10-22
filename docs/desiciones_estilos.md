# Decisiones de estilos del frontend

Registro de las decisiones visuales de la interfaz React (22/10/2026). Son decisiones de diseño del proyecto, no convenciones de la cátedra. Cualquier pantalla o componente nuevo debe seguirlas para que la aplicación se vea como una sola.

Los estilos viven en `frontend/src/styles.css`; la estructura de la aplicación (marco, navegación, barra superior), en `frontend/src/App.jsx`.

## 1. Estilo general: hoja enmarcada

Se adoptó el estilo **framed-sheet** de la skill de diseño frontend (`design-taste-frontend`, semilla 1091252334), pensado para pantallas de trabajo y no para páginas de presentación.

- La barra lateral y la barra superior comparten un mismo fondo tintado y forman una "L", sin línea divisoria entre ellas.
- El contenido de cada sección va sobre una **hoja blanca** separada 8 px de los bordes derecho e inferior de la ventana, con borde de 1 px, esquinas de 16 px y **sin sombra**.
- La profundidad se marca con un escalón de tono (marco → hoja), nunca con sombras ni degradados.

**Por qué:** es un back office de carga de datos, usado en sesiones largas y con nueve secciones. El marco separa con claridad la navegación del área de trabajo; el estilo "achromatic-ledger", la otra opción evaluada, está orientado a pantallas de finanzas personales.

## 2. Identidad

- **Marco verde grisáceo** (`#f2f5f3`), tomado del mundo del almacén, en lugar del gris neutro por defecto. La hoja sigue siendo blanca.
- **Marca** en la parte superior de la barra lateral: un ícono de caja (el bulto, objeto propio del dominio) en el color de acento, con el nombre `TP-DAO` y el alcance `Locales y CD`.
- **Elemento propio:** el recorrido de cada bulto (Preparado → Precintado → En tránsito → Recibido → Verificado) como barra de pasos. Es lo único que lleva el color de acento como dato. Un bulto rechazado termina en rojo; uno anulado, en gris. Se construye con el historial de eventos del bulto (`RecorridoBulto` en `PanelBultos.jsx`).

## 3. Colores

Todos se definen como variables en `:root`; ningún componente usa colores sueltos.

| Rol | Variable | Valor |
| --- | --- | --- |
| Marco (fondo) | `--ground` | `#f2f5f3` |
| Hoja y controles | `--surface` | `#ffffff` |
| Superficie elevada / hover | `--raised` | `#f4f6f5` |
| Ítem activo de navegación | `--active` | `#e3e8e5` |
| Borde de hoja, tarjetas y encabezado de tabla | `--border` | `#e6e9e7` |
| Reglas entre filas | `--rule` | `#eff1f0` |
| Borde de controles | `--control` | `#cdd1cf` |
| Texto principal | `--text` | `#131416` |
| Texto secundario | `--muted` | `#5b5f5d` |
| Botón principal | `--primary` | `#1d1f20` |
| Acento | `--accent` | `#1b6c80` |
| Positivo / negativo | `--positive` / `--negative` | `#1e7b4f` / `#c4242a` |

Reglas:

- **El color va en los datos, no en el cromo.** El acento aparece sólo en la marca, el foco de teclado y el recorrido de los bultos (menos del 3 % de la pantalla).
- El botón principal es **casi negro**, no del color de acento. Hay uno solo por formulario.
- Los estados usan **pares pálidos**: fondo claro con texto oscuro del mismo tono (éxito `#dcfae5`/`#04250e`, error `#ffedea`/`#831c1e`, neutro `#ebedee`/`#353736`, en tránsito `--accent-soft`/`--accent-ink`). Nunca fondo saturado con texto blanco.
- Todo texto alcanza contraste 4.5:1 sobre su fondo, incluidos los placeholders (`#6b6b6b`).
- Prohibido: degradados, sombras en elementos en reposo, brillos, efecto vidrio, violetas e índigos, crema con terracota, barra lateral oscura o saturada.

## 4. Tipografía

- **Una sola familia: IBM Plex Sans**, pesos 400, 500 y 600. Se sirve desde `frontend/src/fonts/` (licencia SIL OFL en `OFL.txt`), sin depender de internet ni de paquetes npm. Vite la incluye en `/assets`, así que funciona igual con Vite y con el build servido por Flask.
- Escala fija:

| Uso | Tamaño | Variable |
| --- | --- | --- |
| Título de sección (`h2`) | 22 px / 600 | `--fs-title` |
| Subtítulos (`h3`) y título de la barra superior (`h1`) | 16 px / 600 | `--fs-section` |
| Cuerpo, celdas, navegación, etiquetas | 14 px | `--fs-body` |
| Ayudas, encabezados de tabla, metadatos | 12 px | `--fs-small` |

- Nada por debajo de 11 px ni por encima de 32 px: es una aplicación, no una página de presentación.
- **Mayúscula inicial** (sentence case) en todo, sin mayúsculas espaciadas.
- `font-variant-numeric: tabular-nums` en tablas y cifras, para que los dígitos se alineen.
- El semibold (600) se reserva para títulos y el ítem activo; las etiquetas de campo van en 500.

## 5. Estructura de la pantalla

- **Barra lateral** de 228 px, fija al hacer scroll: marca arriba y tres grupos (Catálogo, Operaciones, Consultas) con títulos grises de 12 px. El ítem activo es una píldora gris neutra con el texto en tinta.
- **Barra superior** de 48 px sobre el marco: a la izquierda la ruta (`Grupo / Sección`), cuyo último elemento es el `h1` de la pantalla; a la derecha el estado del catálogo y "Actualizar listados".
- **Un borde izquierdo común:** la ruta de la barra superior, el título de la sección, los formularios y la primera columna de las tablas empiezan en la misma línea.
- Cada sección es una vista con su ruta en el hash (`#/productos`); las vistas ocultas siguen montadas para conservar borradores (ver la decisión de navegación en `App.jsx`).
- La nota sobre SQLite y los borradores queda al pie de la hoja, en gris y 12 px, sin recuadro.

## 6. Componentes

**Botones**

- Principal: fondo `--primary`, texto blanco, 36 px de alto, radio 6 px.
- Secundario: blanco con borde `--control` y texto en tinta.
- Compacto (acciones de fila): 28 px, texto de 12 px.
- Deshabilitado: opacidad 0.5, sigue siendo legible.
- Al presionar baja 1 px. Las transiciones duran 80–120 ms y sólo afectan color, borde y desplazamiento.

**Campos**

- Etiqueta arriba (14 px / 500, 6 px de separación); nunca un placeholder en lugar de la etiqueta.
- Alto mínimo de 38 px, borde `--control`, radio 6 px, fondo blanco incluso sobre superficies grises.
- Foco visible: contorno de 2 px en `--accent`.
- Error: borde `--negative` y mensaje de 12 px debajo.
- Los formularios no ocupan todo el ancho: grilla de dos columnas de hasta 760 px; líneas de compra o venta hasta 960 px; selects sueltos hasta 480 px.

**Tablas**

- Sin bandas de color, sin filas cebra y sin mayúsculas en los encabezados.
- Encabezado de 12 px gris, regular, con una regla `--border` debajo; filas separadas por reglas `--rule`.
- **Importes, precios y cantidades alineados a la derecha**: la celda lleva la clase `price` y su encabezado, la clase `num`. IDs, números de orden, códigos y fechas quedan a la izquierda porque son identificadores.
- Primera y última columna sin relleno lateral, para respetar el borde común de la hoja.
- Hover de fila muy suave (`#fafbfa`).
- Los botones de una misma celda llevan 6 px de separación.

**Listados del catálogo**

- El filtro "Estado de…" va **junto al título del listado** (`.list-toolbar`), no arriba del formulario. Los avisos de las acciones de fila (confirmación de baja, éxito, error) aparecen entre ese encabezado y la tabla.

**Avisos y estados vacíos**

- `notice error` / `notice success`: recuadro con el par pálido correspondiente.
- `notice` sin variante: fondo `--raised` con borde `--border`.
- Confirmación de baja (`.confirm`): borde rojizo suave.
- Vacío (`.empty`): recuadro punteado de 1 px, radio 8 px, texto gris. Una sección vacía conserva su título y su recuadro con una frase que indica el siguiente paso.

**Bultos y comprobantes**

- Tarjeta blanca con borde `--border` y radio 8 px, **sin franja lateral de color**: el estado lo indica una sola marca, la píldora (`.badge`), además del recorrido.
- El comprobante de venta sigue el mismo criterio; su impresión conserva la regla `@media print` existente.

## 7. Pantallas angostas

- **Hasta 860 px** desaparece el marco: arriba van la marca y un botón **"Secciones"** que despliega la lista de secciones (`aria-expanded`). El menú se cierra al elegir una sección. Debajo, la ruta y "Actualizar listados", y la hoja ocupa todo el ancho hasta el pie de la pantalla.
- **Hasta 640 px** las tablas tienen un ancho mínimo de 600 px y se desplazan **dentro de su propio marco** (`.table-scroll`); la página nunca se desplaza en horizontal y las palabras no se cortan letra por letra.
- **Hasta 520 px** los formularios pasan a una columna, los botones de acción ocupan el ancho completo y las áreas táctiles miden al menos 44 px (36 px las compactas).

## 8. Accesibilidad

- Foco visible en botones, campos, enlaces, `summary` y regiones de tabla desplazables.
- Al cambiar de sección, el foco pasa al contenido de la vista y el título de la pestaña del navegador cambia.
- El enlace activo usa `aria-current="page"`; el paso actual del recorrido de un bulto, `aria-current="step"`.
- Los títulos de grupo de la navegación etiquetan sus listas (`aria-labelledby`).

## 9. Cómo verificar cambios visuales

Con el frontend compilado (`npm.cmd run build`) y servido por Flask:

```powershell
node "$env:USERPROFILE\.claude\skills\design-taste-frontend\scripts\lint.mjs" --app frontend/src
node "$env:USERPROFILE\.claude\skills\design-taste-frontend\scripts\inspect.mjs" --app "http://127.0.0.1:5000/#/productos"
```

- El inspector revisa la pantalla a 1440, 768 y 390 px y guarda capturas. Debe terminar con **0 FAIL**.
- Avisos aceptados por decisión: alineación a la izquierda de IDs, N.º, códigos y fechas; el espacio libre de Ventas antes de elegir un local; el hueco bajo la barra lateral.
- Para revisar con datos sin tocar la base real, iniciar Flask con `TP_DAO_DB` apuntando a una base temporal (ver `docs/LEVANTAR_PROYECTO.md`).
- El aviso de `lint` sobre `padStart` en `importes.js` corresponde al formato de centavos y es correcto.
