import { useEffect, useState } from 'react';
import { formatearInstante, stockAPI } from './api';
import { CONDICIONES, nombreCondicion, nombreUbicacion } from './etiquetas';

const COLUMNAS = ['DISPONIBLE', 'RESERVADO', 'EN_TRANSITO', 'PENDIENTE', 'RECHAZADO', 'BLOQUEADO'];

function cantidadMovimiento(item) {
  if (item.condicion_origen === null) return `+${item.cantidad} u.`;
  if (item.condicion_destino === null) return `−${item.cantidad} u.`;
  return `${item.cantidad} u.`;
}

function documentoMovimiento(item) {
  if (item.compra_id !== null) return `Compra ${item.compra_id}, línea ${item.linea}`;
  if (item.venta_id !== null) return `Venta ${item.comprobante}, línea ${item.linea}`;
  return `Bulto ${item.bulto_codigo}`;
}

// Una fila por producto con la cantidad de cada condición informada por Python.
function porProducto(saldos, existencias) {
  const costos = new Map(existencias.map((item) => [item.producto.id, item.costo_referencia]));
  const filas = new Map();
  for (const saldo of saldos) {
    const fila = filas.get(saldo.producto.id) ?? { producto: saldo.producto, cantidades: {} };
    fila.cantidades[saldo.condicion] = saldo.cantidad;
    filas.set(saldo.producto.id, fila);
  }
  return [...filas.values()].map((fila) => ({ ...fila, costo: costos.get(fila.producto.id) }));
}

export default function SeccionStock({ ubicaciones, productos, bloqueado, estadoCatalogo, revisionStock }) {
  const centro = ubicaciones.find((item) => item.tipo === 'CD');
  const [elegidaId, setElegidaId] = useState('');
  const ubicacion = ubicaciones.find((item) => String(item.id) === elegidaId) ?? centro;
  const [consulta, setConsulta] = useState({ estado: 'inicial' });
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    if (!ubicacion) {
      setConsulta({ estado: 'inicial' });
      return;
    }
    const controller = new AbortController();
    setConsulta((actual) => ({ ...actual, estado: 'cargando' }));
    Promise.all([
      stockAPI.saldos(ubicacion.id, controller.signal),
      stockAPI.existencias(ubicacion.id, controller.signal),
      stockAPI.movimientos(ubicacion.id, controller.signal),
    ])
      .then(([saldos, existencias, movimientos]) => {
        if (!controller.signal.aborted) {
          setConsulta({
            estado: 'lista', ubicacionId: ubicacion.id,
            filas: porProducto(saldos.saldos, existencias.existencias), movimientos: movimientos.movimientos,
          });
        }
      })
      .catch((fallo) => {
        if (!controller.signal.aborted) setConsulta({ estado: 'error', mensaje: fallo.message });
      });
    return () => controller.abort();
  }, [ubicacion?.id, revision, revisionStock, productos]);

  const lista = consulta.filas && consulta.ubicacionId === ubicacion?.id;
  const columnas = lista ? COLUMNAS.filter((condicion) => condicion === 'DISPONIBLE'
    || consulta.filas.some((fila) => fila.cantidades[condicion])) : [];

  return (
    <section className="catalog-section stock" aria-labelledby="stock-title">
      <div className="section-heading">
        <h2 id="stock-title">Stock por ubicación</h2>
        <button className="secondary" type="button" disabled={!ubicacion || bloqueado || consulta.estado === 'cargando'}
          onClick={() => setRevision((valor) => valor + 1)}>
          Actualizar stock
        </button>
      </div>
      <p className="detail">Saldos confirmados en Python, por condición. Sólo el disponible se puede vender. El costo de referencia es el de la última compra del producto; es una estimación, no un costo por lote.</p>
      {estadoCatalogo === 'lista' && !centro && <p className="empty">Registrá el Centro de Distribución para consultar el stock.</p>}
      {ubicacion && (
        <div className="stock-selector">
          <label htmlFor="stock-ubicacion">Ubicación</label>
          <select id="stock-ubicacion" value={ubicacion.id} onChange={(evento) => setElegidaId(evento.target.value)}>
            {ubicaciones.map((item) => (
              <option key={item.id} value={item.id}>{nombreUbicacion(item)}{item.tipo === 'CD' ? ' (CD)' : ''}{!item.activo ? ' (inactivo)' : ''}</option>
            ))}
          </select>
        </div>
      )}
      {consulta.estado === 'cargando' && <p role="status">Cargando stock…</p>}
      {consulta.estado === 'error' && <p className="notice error" role="alert">{consulta.mensaje} Actualizá el stock para volver a consultar.</p>}
      {lista && (
        <>
          <h3>Saldos de {ubicacion.codigo}</h3>
          {!consulta.filas.length ? <p className="empty">Esta ubicación todavía no tiene stock.</p> : (
            <div className="table-scroll" role="region" aria-label={`Saldos de ${ubicacion.codigo}`} tabIndex="0">
              <table>
                <caption className="sr-only">Saldos por producto y condición</caption>
                <thead><tr>
                  <th scope="col">Código</th><th scope="col">Producto</th>
                  {columnas.map((condicion) => <th key={condicion} scope="col" className="num">{CONDICIONES[condicion]}</th>)}
                  <th scope="col" className="num">Costo de referencia</th>
                </tr></thead>
                <tbody>{consulta.filas.map((fila) => (
                  <tr key={fila.producto.id}>
                    <td>{fila.producto.codigo}</td>
                    <td>{fila.producto.nombre}{!fila.producto.activo ? ' (inactivo)' : ''}</td>
                    {columnas.map((condicion) => <td key={condicion} className="price">{fila.cantidades[condicion] ?? 0} u.</td>)}
                    <td className="price">{fila.costo ? `$ ${fila.costo}` : '—'}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
          <h3>Movimientos de {ubicacion.codigo}</h3>
          {!consulta.movimientos.length ? <p className="empty">Sin movimientos registrados.</p> : (
            <div className="table-scroll" role="region" aria-label={`Movimientos de ${ubicacion.codigo}`} tabIndex="0">
              <table>
                <caption className="sr-only">Movimientos, del más reciente al más antiguo</caption>
                <thead><tr><th scope="col">N.º</th><th scope="col">Fecha y hora</th><th scope="col">Producto</th><th scope="col" className="num">Cantidad</th><th scope="col">Cambio de condición</th><th scope="col">Documento</th></tr></thead>
                <tbody>{[...consulta.movimientos].reverse().map((item) => (
                  <tr key={item.id}>
                    <td>{item.id}</td>
                    <td>{formatearInstante(item.instante)}</td>
                    <td>{item.producto.codigo} · {item.producto.nombre}</td>
                    <td className="price">{cantidadMovimiento(item)}</td>
                    <td>{nombreCondicion(item.condicion_origen)} → {nombreCondicion(item.condicion_destino)}</td>
                    <td>{documentoMovimiento(item)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}
