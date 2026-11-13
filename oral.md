# Guía para el oral — TP Integrador 2026, Tema 3

Orden en que pregunta el profesor:

1. Dominio / entidades
2. Patrones de diseño (cómo están implementados en el código)
3. Transacción
4. Ciclo de vida del bulto
5. Reportes (código)
6. ¿Por qué usamos `@abstractmethod`?

Para cada tema: **respuesta corta** (lo que decimos primero), **dónde está en el código** (para abrirlo si lo pide) y **preguntas de repregunta** probables.

---

## 0. Mapa rápido del proyecto (por si arranca con "contame cómo está armado")

| Capa | Carpeta | Qué hace |
| --- | --- | --- |
| Dominio | `backend/dominio/` | Clases, reglas de negocio y patrones. **No importa Flask ni SQLite.** |
| Persistencia | `backend/persistencia/` | Esquema SQLite, SQL parametrizado (`?`), transacciones con `sqlite3`. |
| API (adaptadores HTTP) | `backend/api_*.py` | Reciben JSON, buscan los objetos, envían el mensaje al dominio y guardan con `guardar_cambio`. |
| Presentación | `frontend/src` (React) | Sólo muestra y captura. **No decide reglas**: la validación definitiva está en Python. |

Recorrido de **toda** operación:
`API valida el JSON` → `dominio valida y modifica la memoria` → `guardar_cambio` confirma en **una** transacción SQLite → si falla, `rollback` y se recarga la memoria desde la base.

---

## 1. Dominio / entidades

### Respuesta corta

> Un comercio con varios locales y un Centro de Distribución. Los locales piden reposición, el CD arma bultos precintados con remito, los despacha, el local los recibe y los verifica. Recién ahí el stock queda disponible para vender. Además hay compras a proveedores, ventas con cobros, caja y devoluciones.

### Entidades por módulo (`backend/dominio/`)

| Módulo | Clases | Responsabilidad |
| --- | --- | --- |
| `catalogo.py` | `Catalogo`, `Categoria`, `Producto`, `Proveedor`, `Ubicacion` | Maestros. Evita códigos duplicados (`CodigoDuplicadoError`), un único CD, mínimos por local. Baja lógica. |
| `compras.py` | `RegistroCompras`, `Compra`, `DetalleCompra` | Compra a proveedor con destino CD; ingresa stock y da el costo de referencia. |
| `inventario.py` | `Inventario`, `MovimientoStock` | **Único** que modifica saldos (por ubicación, producto y **condición**: DISPONIBLE, RESERVADO, EN_TRANSITO, PENDIENTE, RECHAZADO, BLOQUEADO). Cada cambio deja un movimiento. |
| `reposicion.py` | `RegistroReposicion`, `NecesidadReposicion`, `OrdenReposicion`, `DetalleReposicion` | Necesidades de cada local consolidadas en una orden CD → local (origen y destino). |
| `logistica.py` | `RegistroLogistica`, `Bulto`, `DetalleBulto`, `EventoEstadoBulto`, `Remito`, `EstadoBulto` + 7 estados | Ciclo de vida del bulto (**State**), precinto, remito, historial inmutable. |
| `ventas.py` | `RegistroVentas`, `Venta`, `DetalleVenta`, `Cobro`, `Comprobante`, `MedioPago` | Venta multilínea, cobros que suman el total, comprobante. |
| `caja.py` | `Caja`, `MovimientoCaja` | Único responsable del dinero: ingresos por cobro, egresos por reintegro. Saldo = suma de movimientos. |
| `devoluciones.py` | `RegistroDevoluciones`, `Devolucion`, `DetalleDevolucion`, `Reintegro` | Devolución parcial de una venta **registrada**, sin devolver más de lo vendido. |
| `reportes.py` | `ReporteVentas` + estrategias (**Strategy**), `Periodo`, funciones de R-02 a R-04 | Consultan, no modifican. |

Los `Registro…` actúan como "servicios": asignan identificadores y coordinan la operación (ej.: `RegistroVentas.registrar` crea la venta y le pide al `Inventario` que descuente y a la `Caja` que ingrese), sin quitarle reglas a las entidades.

### Relaciones (composición vs agregación) — preguntas de la cátedra

Criterio: *¿la parte puede pasar a otro contenedor? ¿tiene sentido sin contenedor?*

- **Composición** (no y no): `Venta` → `DetalleVenta`, `Cobro`, `Comprobante`; `Compra` → `DetalleCompra`; `Bulto` → `DetalleBulto`, `EventoEstadoBulto`; `Devolucion` → `DetalleDevolucion`, `Reintegro`; `Inventario` → `MovimientoStock`; `Caja` → `MovimientoCaja`. El todo crea sus partes en `__init__` y las guarda en **tuplas**; no hay método de remoción.
- **Agregación**: `DetalleReposicion` → `NecesidadReposicion` (la necesidad existe antes de la orden y queda pendiente si no se consolida); `Registro…` → documentos.
- **Asociación simple**: documentos con `Producto`, `Ubicacion`, `Proveedor`, `MedioPago`.

### Encapsulamiento

- Estado en atributos con `_` y lectura con `@property` **sin setter** → `bulto.estado = "VERIFICADO"` da `AttributeError`.
- Los cambios son mensajes con nombre de dominio (`precintar`, `verificar`, `cambiar_precio`, `desactivar`) que validan antes de modificar.
- Cada validación vive en el dueño del estado: `Producto` su precio, `Venta` que cobros = total, `Inventario` que ningún saldo quede negativo.

### Validaciones del enunciado → dónde están

| Validación | Dónde |
| --- | --- |
| Stock no disponible hasta Verificado (bulto **y** remito) | `Recibido.verificar` (no mueve stock) + `Remito.verificar` → `inventario.habilitar_bulto` (`logistica.py`) |
| Trazabilidad inmutable del bulto | `Bulto._cambiar_estado` agrega `EventoEstadoBulto`; triggers SQLite impiden `UPDATE`/`DELETE` en `eventos_bulto` (`persistencia/base_datos.py`) |
| No vender más que lo disponible y verificado | `Inventario.vender` → `_aplicar` comprueba **todos** los saldos antes de tocar alguno (`inventario.py`) |
| Sin productos/proveedores duplicados | `Catalogo` + `CodigoDuplicadoError`, y `UNIQUE` en la base |
| Devolución sólo de venta registrada y sin exceso | `RegistroDevoluciones` + triggers `detalles_devolucion_de_su_venta` y `detalles_devolucion_sin_exceso` |

### Repreguntas probables

- *¿Por qué `Ubicacion` no tiene subclases Local y CD?* Tienen los mismos datos y operaciones; sólo cambia qué aceptan (el CD no vende). Se usa un atributo `tipo`. Herencia sería "dos clases parecidas", que el material dice evitar.
- *¿Dónde está el stock?* No es un número en `Producto`: lo lleva `Inventario` por (ubicación, producto, condición), y cada cambio deja `MovimientoStock`.

---

## 2. Patrones de diseño

Aplicamos **dos**: **State** (ciclo de vida del bulto) y **Strategy** (agrupación del reporte de ventas R-01).

### 2.1 State — `backend/dominio/logistica.py`

**Problema:** lo que se puede hacer con un bulto depende de su estado (no se recibe sin despachar, no se verifica uno rechazado). Con `if estado == ...` en cada método las reglas quedarían dispersas.

**Participantes:**

| Rol del patrón | Clase |
| --- | --- |
| Contexto | `Bulto` (guarda `self._estado`, un **objeto**, no un string) |
| Estado abstracto | `EstadoBulto(ABC)` |
| Estados concretos | `Preparado`, `Precintado`, `EnTransito`, `Recibido`, `Verificado`, `Rechazado`, `Anulado` |

**Cómo está en el código:**

```python
# Contexto: cada operación es una sola línea que delega pasándose a sí mismo
class Bulto:
    def despachar(self, instante, inventario):
        return self._estado.despachar(self, instante, inventario)

    def _cambiar_estado(self, estado, instante, motivo):
        """Único punto que cambia el estado; siempre agrega un evento al historial."""
        self._eventos.append(EventoEstadoBulto(len(self._eventos) + 1,
                             self._estado.nombre, estado.nombre, instante, motivo))
        self._estado = estado
```

```python
class EstadoBulto(ABC):
    @property
    @abstractmethod
    def nombre(self): ...

    def _rechazar(self, bulto, accion):        # comportamiento por defecto
        raise TransicionBultoError(...)

    def despachar(self, bulto, instante, inventario):
        self._rechazar(bulto, "despachar")     # por defecto NO se permite

class Precintado(EstadoBulto):
    def despachar(self, bulto, instante, inventario):   # sobreescribe sólo lo que admite
        inventario.despachar_bulto(bulto, instante)
        bulto._cambiar_estado(EnTransito(), instante, "Despachado desde ...")
```

Puntos para decir:
- En `self._estado.despachar(self, ...)` el primer `self` es el **contexto**; dentro del estado, `self` es el estado y `bulto` es el contexto recibido.
- El estado recibe el bulto porque necesita pedirle el cambio (`bulto._cambiar_estado(...)`) y el efecto en inventario.
- La transición **reemplaza la referencia** `_estado`; el bulto sigue siendo el mismo objeto. No se devuelve el estado nuevo.
- Operación no permitida → `TransicionBultoError` (la API responde **409**) y no cambia nada.
- Estados finales (`Verificado`, `Rechazado`, `Anulado`) no sobreescriben ninguna operación.
- Polimorfismo: el `Bulto` envía el mismo mensaje sin preguntar `isinstance`.

**Consecuencias:** agregar un estado = agregar una clase; reglas de cada estado juntas. Costo: 7 clases chicas.

### 2.2 Strategy — `backend/dominio/reportes.py`

**Problema:** el reporte R-01 (ventas e ingresos) se agrupa por **día**, por **local** o por **medio de pago** sobre los mismos movimientos de caja. Son algoritmos intercambiables.

| Rol | Clase |
| --- | --- |
| Contexto | `ReporteVentas` |
| Estrategia abstracta | `EstrategiaAgrupacion(ABC)` con `nombre` y `clave(movimiento)` abstractos |
| Estrategias concretas | `PorDia`, `PorLocal`, `PorMedioPago` |

```python
class ReporteVentas:
    def __init__(self, estrategia):          # la estrategia viene de afuera
        self._estrategia = estrategia

    def cambiar_estrategia(self, estrategia):
        self._estrategia = estrategia

    def generar(self, periodo, ventas, devoluciones, caja, local=None):
        for movimiento in caja.movimientos(local):
            if periodo.contiene(movimiento.instante):
                orden, etiqueta = self._estrategia.clave(movimiento)   # ← delegación polimórfica
                ...
```

Quién elige la estrategia: **el cliente** (la API) según el parámetro `?agrupacion=dia|local|medio`:

```python
ESTRATEGIAS_AGRUPACION = {estrategia().nombre: estrategia for estrategia in (PorDia, PorLocal, PorMedioPago)}
# api_reportes.py
resultado = ReporteVentas(ESTRATEGIAS_AGRUPACION[nombre]()).generar(...)
```

- El contexto **no tiene** `if/elif` por agrupación. Nueva agrupación = nueva clase.
- La estrategia sólo calcula una clave; no modifica datos.

### 2.3 Diferencia State vs Strategy (pregunta clásica)

- **Strategy:** "¿qué algoritmo uso?" — lo elige el **cliente** desde afuera; las estrategias no cambian entre sí.
- **State:** "¿qué puede hacer el objeto ahora?" — la transición la decide el **propio estado**; el cliente no elige el estado.

### 2.4 ¿Por qué no otros?

- **Singleton:** no hay necesidad real de instancia única; cada `create_app` tiene sus registros, y así cada test usa una base aislada.
- **Factory / Observer / Iterator:** no apareció un problema del dominio que los pida (las colecciones ya se exponen como tuplas iterables y nadie necesita suscribirse a cambios).

---

## 3. Transacción

### Respuesta corta

> Toda operación que modifica datos se guarda en **una sola transacción SQLite**: o se guardan todos sus efectos (documento + movimientos de stock + movimientos de caja), o ninguno.

### Dónde está

`backend/persistencia/base_datos.py`:

```python
def ejecutar_transaccion(self, operacion, *argumentos):
    """Confirma todos los cambios de la operación o ninguno."""
    conexion = self.conectar()
    try:
        resultado = operacion(conexion, *argumentos)
        conexion.commit()          # todo OK → confirma
        return resultado
    except Exception:
        conexion.rollback()        # algo falló → deshace todo lo pendiente
        raise
    finally:
        conexion.close()           # siempre libera la conexión

def consultar(self, operacion, *argumentos):
    """Ejecuta una lectura; no confirma porque no modifica datos."""   # SELECT sin commit
```

`backend/api_comun.py`:

```python
def guardar_cambio(operacion, *argumentos):
    try:
        current_app.extensions["base_datos"].ejecutar_transaccion(operacion, *argumentos)
    except Exception as error:
        recargar_estado()          # la memoria vuelve al último estado confirmado
        if isinstance(error, sqlite3.Error):
            raise ErrorCatalogoAPI(500, "No se pudo guardar el cambio y no se aplicó...")
        raise
```

### Ejemplo concreto: registrar una venta

1. `api_ventas.registrar_venta` valida el JSON y busca local, productos y medios.
2. Dominio: `RegistroVentas.registrar` → crea la `Venta` (valida que cobros = total) → `inventario.vender(venta)` (si **una** línea no alcanza, falla toda la venta antes de tocar saldos) → `caja.ingresar_venta(venta)`.
3. `guardar_cambio(guardar_venta, venta, movimientos, movimientos_caja)`; `guardar_venta` (`persistencia/ventas_sqlite.py`) hace en la **misma conexión**:
   - `INSERT INTO ventas`
   - `executemany INSERT INTO detalles_venta`
   - `executemany INSERT INTO cobros`
   - movimientos de stock y de caja
4. Un único `commit()` al final. No hay commits intermedios → **no quedan efectos parciales** (invariante del TP: venta inválida no deja stock, caja ni comprobante a medias).

### Puntos para decir

- SQL **parametrizado con `?`**, nunca concatenado (evita inyección SQL).
- `rollback()` sólo deshace lo **no confirmado**.
- Cerrar la conexión **no** confirma: por eso `commit()` explícito.
- Un `SELECT` no lleva `commit()` (`consultar`).
- La `clave_operacion` evita duplicar una venta si el cliente reenvía (devuelve la existente con 200).
- Hay un `Lock` (`catalogo_lock`) para que dos pedidos simultáneos no modifiquen la memoria a la vez.

---

## 4. Ciclo de vida del bulto

### Diagrama de estados

```
             precintar              despachar             recibir (precinto OK)          verificar
PREPARADO ───────────► PRECINTADO ───────────► EN_TRANSITO ───────────────────► RECIBIDO ─────────► VERIFICADO
    │                                               │
    │ anular                                        │ recibir (precinto roto o distinto)
    ▼                                               ▼
 ANULADO                                  RECIBIDO → RECHAZADO   (en la misma operación)
```

### Qué pasa con el stock en cada paso (condiciones del `Inventario`)

| Paso | Estado del bulto | Stock |
| --- | --- | --- |
| Preparar | `PREPARADO` | CD: DISPONIBLE → RESERVADO |
| Anular | `ANULADO` | Se libera la reserva del CD |
| Precintar | `PRECINTADO` | Sin cambio; se fija precinto y se **emite el remito** |
| Despachar | `EN_TRANSITO` | Reserva CD → EN_TRANSITO |
| Recibir OK | `RECIBIDO` | EN_TRANSITO → **PENDIENTE** en el local (todavía **no vendible**) |
| Recibir con precinto roto | `RECIBIDO` → `RECHAZADO` | EN_TRANSITO → RECHAZADO (en custodia del local, no vendible); remito → RECHAZADO |
| Verificar bulto | `VERIFICADO` | **Sin cambio**: falta el remito |
| Verificar remito | (bulto ya `VERIFICADO`) | PENDIENTE → **DISPONIBLE** ✅ recién acá se puede vender |

### Doble verificación (la regla clave del enunciado)

```python
class Recibido(EstadoBulto):
    def verificar(self, bulto, instante):
        bulto._cambiar_estado(Verificado(), instante, "Contenedor verificado; falta verificar el remito.")

class Remito:
    def verificar(self, instante, inventario):
        if self._estado != "EMITIDO": raise ConflictoOperacionError(...)
        if self._bulto.estado != "VERIFICADO":
            raise ConflictoOperacionError("Verificá el bulto ... antes que su remito ...")
        movimientos = inventario.habilitar_bulto(self._bulto, instante)   # PENDIENTE → DISPONIBLE
        self._estado = "VERIFICADO"
```

Verificar sólo el bulto o sólo el remito **nunca** habilita la venta.

### Rechazo logístico (`EnTransito.recibir`)

Si `precinto_intacto` es falso o el precinto leído no coincide con el registrado: en la **misma** operación pasa a `RECIBIDO` y `RECHAZADO`, el stock va a la condición RECHAZADO y el remito a RECHAZADO. Nunca existe un momento con stock habilitado.

### Trazabilidad inmutable

- Cada transición pasa por `Bulto._cambiar_estado`, que **siempre** agrega un `EventoEstadoBulto` (secuencia, estado anterior, nuevo, instante, motivo).
- `eventos` se expone como **tupla** (no se puede modificar desde afuera).
- En SQLite, dos triggers: `eventos_bulto_sin_modificacion` (`BEFORE UPDATE`) y `eventos_bulto_sin_borrado` (`BEFORE DELETE`) hacen `RAISE(ABORT, ...)`.
- Al reconstruir desde la base, `_restaurar_historia` exige una cadena válida que empiece en `PREPARADO`.

### Repregunta: ¿por qué el remito no usa State?

Sólo tiene `EMITIDO` → `VERIFICADO` o `RECHAZADO`, una única vez. Un patrón ahí sería sobreingeniería.

---

## 5. Reportes (código)

Cuatro reportes, todos en `backend/dominio/reportes.py`, expuestos en `backend/api_reportes.py` (`GET /api/reportes/...`). **Sólo consultan**: no modifican stock ni caja. Devuelven objetos de resultado que la API convierte en JSON.

| # | Reporte | Endpoint | Código | Por qué es no trivial |
| --- | --- | --- | --- | --- |
| R-01 | Ventas e ingresos por período, local y medio de pago | `/api/reportes/ventas?desde&hasta&local_id&agrupacion` | `ReporteVentas` + **Strategy** | Cruza ventas, devoluciones y caja; agrupa y calcula cobros, reintegros e ingreso neto. |
| R-02 | Productos más vendidos y margen estimado | `/api/reportes/productos` | `productos_mas_vendidos()` → `FilaProducto`, `ResultadoProductos` | Unidades netas (vendido − devuelto), importe, costo y margen por producto. |
| R-03 | Existencias y productos en stock mínimo | `/api/reportes/existencias` | `existencias_y_minimos()` → `FilaExistencia` (`disponible`, `deficit`, `en_minimo`) | Combina inventario por condición con el mínimo del local; filtro por categoría y "sólo en mínimo". |
| R-04 | Bultos rechazados por rotura de precinto | `/api/reportes/rechazos` | `rechazos_logisticos()` → `BultoRechazado`, `RechazosLocal` | Recorre el historial de eventos del bulto; unidades y valor bloqueado por local. |

### Cómo explicar uno (R-01)

1. La API valida parámetros (`_periodo()`, `agrupacion` dentro de `ESTRATEGIAS_AGRUPACION`).
2. Crea `ReporteVentas(estrategia_elegida)` y llama `generar(periodo, ventas, devoluciones, caja, local)`.
3. `generar` filtra los movimientos de caja del período/local y los agrupa con `self._estrategia.clave(movimiento)` en objetos `GrupoCaja`.
4. Devuelve un `ResultadoVentas` con propiedades calculadas (`venta_neta_centavos`, `ingreso_neto_centavos`…).
5. La API arma el JSON; el frontend lo muestra.

### Puntos para decir

- Separación **cálculo (dominio) / presentación (API + React)**.
- Importes en **centavos enteros** para no tener errores de punto flotante.
- Los resultados (`FilaProducto`, `GrupoCaja`…) tienen atributos públicos a propósito: son la respuesta de una consulta, no estado del sistema.
- Probados en `tests/test_reportes.py` y `tests/test_api_reportes.py` contra datos conocidos y caso sin datos.

---

## 6. ¿Por qué usamos `@abstractmethod`?

### Respuesta corta

> Porque `EstadoBulto` y `EstrategiaAgrupacion` son **contratos**: definen qué mensajes debe entender cualquier estado o cualquier estrategia, pero no tiene sentido crear "un estado genérico" o "una estrategia genérica". Con `ABC` + `@abstractmethod`, Python **impide instanciar** la clase abstracta y **obliga** a cada subclase concreta a implementar esos métodos; si alguna se olvida, falla al crearla (`TypeError`), no más tarde en ejecución.

### Dónde

```python
from abc import ABC, abstractmethod

class EstadoBulto(ABC):              # logistica.py
    @property
    @abstractmethod
    def nombre(self): ...            # cada estado DEBE decir su nombre

    @property
    @abstractmethod
    def descripcion(self): ...

    # métodos concretos con comportamiento por defecto (rechazar)
    def precintar(self, bulto, ...): self._rechazar(bulto, "precintar")

class EstrategiaAgrupacion(ABC):     # reportes.py
    @property
    @abstractmethod
    def nombre(self): ...

    @abstractmethod
    def clave(self, movimiento): ... # cada estrategia DEBE saber agrupar
```

### Qué aporta, punto por punto

1. **No instanciable:** `EstadoBulto()` → `TypeError: Can't instantiate abstract class...`.
2. **Contrato obligatorio:** una subclase que no implemente `clave` o `nombre` tampoco se puede instanciar.
3. **Habilita el polimorfismo:** `Bulto` y `ReporteVentas` envían mensajes al tipo abstracto (`self._estado.verificar(...)`, `self._estrategia.clave(...)`) sin conocer la clase concreta y sin `isinstance`/`if`.
4. **Clase abstracta ≠ interfaz pura:** `EstadoBulto` mezcla métodos **abstractos** (`nombre`, `descripcion`) con métodos **concretos** por defecto (las operaciones llaman a `_rechazar`). Cada estado **sobreescribe sólo** lo que admite. `EstrategiaAgrupacion` es más parecida a una interfaz: sólo abstractos.

### Repregunta: ¿por qué las operaciones (`precintar`, `despachar`…) NO son abstractas?

Si fueran abstractas, cada uno de los 7 estados tendría que implementar las 5 operaciones, casi todas sólo para rechazar → código repetido. Dejándolas concretas con rechazo por defecto, cada estado redefine sólo las transiciones válidas, y lo "no permitido" queda garantizado por la base.

### Repregunta: ¿se usa `super()`?

En el dominio no hace falta: ninguna derivada redefine `__init__`. Se usa en `ErrorCatalogoAPI(Exception)` (`api_comun.py`), que extiende la inicialización de `Exception` con `super().__init__(mensaje)`.

---

## Chuleta final (30 segundos)

- **Dominio:** locales + CD; reposición → bulto precintado + remito → despacho → recepción → doble verificación → stock disponible → venta/caja/devolución.
- **Patrones:** State (`Bulto` + 7 `EstadoBulto`), Strategy (`ReporteVentas` + `PorDia`/`PorLocal`/`PorMedioPago`).
- **Transacción:** `ejecutar_transaccion` → `commit` o `rollback` + `close` en `finally`; una operación = una transacción; memoria se recarga si falla.
- **Ciclo de vida:** PREPARADO → PRECINTADO → EN_TRANSITO → RECIBIDO → VERIFICADO (o RECHAZADO / ANULADO); historial inmutable con eventos + triggers.
- **Reportes:** 4 (ventas, más vendidos/margen, existencias/mínimos, rechazos); sólo consultan.
- **`@abstractmethod`:** contrato obligatorio, clase no instanciable, polimorfismo sin `if`.
