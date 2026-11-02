# Guion de demostración (F-07.3)

Recorrido para mostrar el sistema en funcionamiento desde la pantalla, con el dataset de control J.3 de `PLANIFICACION_TP_POO.md`. Cubre los siete procesos obligatorios y las cinco validaciones de `tema3.pdf`, los dos patrones y los cuatro reportes. Los resultados esperados son los mismos que comprueba `tests/test_integracion.py` sobre la API.

No reemplaza la rúbrica ni el formato de entrega, que siguen pendientes de la cátedra (G-06). Si la rúbrica pide otra cosa, este guion se adapta.

## 1. Preparación

Desde la raíz del repositorio, con el entorno ya armado según `LEVANTAR_PROYECTO.md`, compilar el cliente y levantar Flask sobre una base nueva, para no mezclar la demostración con otros datos:

```powershell
cd frontend; npm.cmd run build; cd ..
$env:TP_DAO_DB = "$env:TEMP\tp_dao_demo.db"
.\.venv\Scripts\python.exe -m flask --app backend:create_app --no-debug run --host 127.0.0.1 --port 5000 --no-reload
```

Abrir http://127.0.0.1:5000/. Si el archivo ya existe de una demostración anterior, usar otro nombre en `TP_DAO_DB`: Flask conserva lo que encuentre. Todas las operaciones quedan con la fecha y hora del momento en que se hacen.

## 2. Catálogo (proceso 1 y 2)

| Vista | Acción | Qué mostrar |
| --- | --- | --- |
| Ubicaciones | Alta de `CD` «Centro de Distribución» con tipo CD, y de los locales `A` y `B`. | Intentar un segundo CD: Python lo rechaza. |
| Categorías | Alta de `ALM` «Almacén». | |
| Productos | Alta de `P` «Producto P», categoría Almacén, precio `100`. | Intentar otro producto con código `p`: rechazado por duplicado sin distinguir mayúsculas (validación 4). |
| Proveedores | Alta de `PRV` «Proveedor». | Mismo control de duplicados. |
| Mínimos por local | Local A, producto P: `2`. Local B, producto P: `3`. | El CD no aparece: sólo los locales tienen mínimos. |

## 3. Compra y stock del CD

| Vista | Acción | Qué mostrar |
| --- | --- | --- |
| Compras al CD | Proveedor PRV, una línea de P con cantidad `14` y costo unitario `60`; «Confirmar compra». | Número y total devueltos por Python (840.00). |
| Stock por ubicación | Elegir el CD. | 14 disponibles de P, costo de referencia 60.00 y el movimiento con su compra y línea. |

## 4. Reposición, bultos y doble verificación (procesos 3 a 6, patrón State)

En **Reposición y logística**:

1. «Registrar necesidad»: local A, P, `2`; otra vez local A, P, `1`; local B, P, `7`.
2. «Consolidar orden hacia un local»: destino A, marcar sus dos necesidades y consolidar. Repetir con B. Cada orden muestra el CD de origen y el local destino; las dos necesidades de A quedan en una sola orden de 3 unidades (proceso 3).
3. «Preparar bulto»: orden de A con 3 unidades de P; orden de B con 7. En el CD, esas unidades pasan a reservadas.
4. En cada bulto, «Precintar» con un número propio (`PR-A1`, `PR-B1`). Se emite el remito (proceso 4). Intentar reutilizar `PR-A1` en otro bulto: rechazado.
5. «Despachar desde el CD» los dos bultos (proceso 5). Ahora están en tránsito al local.
6. **Bloqueo antes de verificar.** En **Ventas y caja**, local A, intentar vender 1 unidad de P: Python la rechaza porque no hay stock disponible (validaciones 1 y 3).
7. Bulto de A: «Registrar recepción» en el local A, precinto leído `PR-A1`, «Intacto» (proceso 6). Queda Recibido, con las unidades pendientes. Intentar vender otra vez: sigue rechazado.
8. «Verificar contenedor»: el bulto queda Verificado y el remito todavía emitido. Intentar vender: sigue rechazado, porque falta el remito (RB-01).
9. «Verificar remito»: recién ahora las 3 unidades quedan disponibles en A. Repetir 7 a 9 con el bulto de B (`PR-B1`).
10. Mostrar el historial de un bulto verificado: Preparado → Precintado → En tránsito → Recibido → Verificado, con fecha y motivo de cada paso (validación 2). No hay forma de editarlo ni borrarlo.

**Rechazo por precinto roto.** Registrar otra necesidad de A por `4`, consolidarla, preparar un bulto de 4, precintarlo (`PR-A2`) y despacharlo. Al recibirlo, elegir «Roto»: el bulto queda Recibido y Rechazado en la misma operación y su remito también. En **Stock por ubicación** del local A, esas 4 unidades figuran como rechazadas, no disponibles; el bulto ya no ofrece verificar.

Para explicar State: cada estado ofrece sólo sus operaciones, y si se forzara otra por la API (por ejemplo despachar un bulto recibido), Python responde 409 sin cambiar nada. Ver `MODELO_POO.md`, sección 7.1.

## 5. Ventas, comprobante y caja (proceso 7)

En **Ventas y caja**:

1. Local A: vender 3 unidades de P (300.00) con dos cobros, `200` en Efectivo y `100` con Crédito. «Confirmar venta» y abrir el comprobante `CV-00000001`, con local, fecha, línea, precio y cobros.
2. Intentar en A una unidad más: rechazada, no queda stock disponible (validación 3). Los 4 rechazados no se venden.
3. En **Productos**, cambiar el precio de P a `90`. Volver al comprobante de la venta anterior: conserva el precio 100 (RB-12).
4. Local B: vender 2 unidades de P (180.00) por Transferencia.
5. La caja de cada local muestra lo cobrado por medio: A, efectivo 200 y crédito 100; B, transferencia 180.

## 6. Devolución

En **Devoluciones**, local A, elegir la venta `CV-00000001`: devolver 1 unidad «apta» con motivo, reintegrando `100` en Efectivo; «Confirmar devolución» (`DV-00000001`).

- El stock disponible de A pasa de 0 a 1 y la caja en efectivo de A, de 200 a 100.
- Volver a elegir la venta: la línea indica «quedan 2». Intentar devolver 3: Python lo rechaza con «Línea 1: quedan 2 unidades sin devolver de P y se intenta devolver 3.» y no registra nada (validación 5).
- La pantalla sólo ofrece reintegrar con los medios cobrados en la venta, cada uno con lo que todavía se puede reintegrar con él.

## 7. Reportes (patrón Strategy)

En **Reportes**, con el período que propone la pantalla (del primer día del mes hasta hoy, inclusive), que abarca todas las operaciones de la demostración; «Generar reporte» después de elegir cada uno:

| Reporte | Resultado esperado |
| --- | --- |
| R-01, agrupado por medio de pago | Venta bruta 480.00, devoluciones 100.00, venta neta 380.00. Ingreso neto 380.00: efectivo 100.00, crédito 100.00, transferencia 180.00. |
| R-01, por local y por día | Los mismos totales con otra agrupación: es la misma consulta con otra estrategia (`MODELO_POO.md`, sección 7.2). |
| R-02 | P: 4 unidades netas, importe 380.00, costo 240.00, margen estimado 140.00. |
| R-03, local A | P: 1 disponible y 4 rechazadas, mínimo 2, déficit 1, en mínimo. Local B: 5 disponibles, mínimo 3, déficit 0. |
| R-04 | 3 bultos recibidos y 1 rechazado: el del local A, con 4 unidades y 240.00 bloqueados por «Precinto roto.»; no es una pérdida registrada. |

Los reportes sólo consultan: después de generarlos, stock, caja y documentos no cambian.

## 8. Reinicio

Detener Flask con Ctrl+C y volver a iniciarlo con la misma `TP_DAO_DB`. Al recargar la página siguen las compras, bultos con su historial, ventas, devolución, caja y reportes con los mismos valores.

## 9. Correspondencia con el enunciado

| `tema3.pdf` | Dónde se muestra |
| --- | --- |
| Proceso 1: sucursales y CD | Sección 2 |
| Proceso 2: productos, categorías, precios, mínimos y proveedores | Secciones 2 y 3 |
| Proceso 3: consolidar necesidades en una orden con origen y destino | Sección 4, pasos 1 y 2 |
| Proceso 4: bultos con remito y precinto | Sección 4, pasos 3 y 4 |
| Proceso 5: despacho | Sección 4, paso 5 |
| Proceso 6: recepción y control del precinto | Sección 4, pasos 7 a 9 y rechazo |
| Proceso 7: ventas, cobros, comprobante y devoluciones | Secciones 5 y 6 |
| Validación 1: stock recién con remito y contenedor verificados | Sección 4, pasos 6 a 9 |
| Validación 2: trazabilidad inmutable del bulto | Sección 4, paso 10 |
| Validación 3: no vender más de lo disponible y verificado | Sección 4, paso 6, y sección 5, paso 2 |
| Validación 4: sin duplicados | Sección 2 |
| Validación 5: devoluciones válidas | Sección 6 |
| Dos patrones | State (sección 4) y Strategy (sección 7) |
| Cuatro reportes | Sección 7 |
