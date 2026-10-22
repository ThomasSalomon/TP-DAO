import { useEffect, useState } from 'react';
import { formatearInstante, stockAPI } from './api';

const CONDICIONES = { DISPONIBLE: 'Disponible' };

export default function SeccionStockCD({ ubicaciones, productos, bloqueado, estadoCatalogo, revisionStock }) {
  const centro = ubicaciones.find((item) => item.tipo === 'CD');
  const [consulta, setConsulta] = useState({ estado: 'inicial' });
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    if (!centro) {
      setConsulta({ estado: 'inicial' });
      return;
    }
    const controller = new AbortController();
    setConsulta((actual) => ({ ...actual, estado: 'cargando' }));
    Promise.all([
      stockAPI.existencias(centro.id, controller.signal),
      stockAPI.movimientos(centro.id, controller.signal),
    ])
      .then(([existencias, movimientos]) => {
        if (!controller.signal.aborted) {
          setConsulta({ estado: 'lista', existencias: existencias.existencias, movimientos: movimientos.movimientos });
        }
      })
      .catch((fallo) => {
        if (!controller.signal.aborted) setConsulta({ estado: 'error', mensaje: fallo.message });
      });
    return () => controller.abort();
  }, [centro?.id, revision, revisionStock, productos]);

  const lista = consulta.estado === 'lista' || (consulta.estado === 'cargando' && consulta.existencias);

  return (
    <section className="catalog-section stock" aria-labelledby="stock-title">
      <div className="section-heading">
        <h2 id="stock-title">Stock del Centro de Distribución</h2>
        <button className="secondary" type="button" disabled={!centro || bloqueado || consulta.estado === 'cargando'}
          onClick={() => setRevision((valor) => valor + 1)}>
          Actualizar stock
        </button>
      </div>
      <p className="detail">Saldos confirmados en Python. El costo de referencia es el de la última compra del producto; es una estimación, no un costo por lote.</p>
      {estadoCatalogo === 'lista' && !centro && <p className="empty">Registrá el Centro de Distribución para consultar su stock.</p>}
      {consulta.estado === 'cargando' && <p role="status">Cargando stock…</p>}
      {consulta.estado === 'error' && <p className="notice error" role="alert">{consulta.mensaje} Actualizá el stock para volver a consultar.</p>}
      {centro && lista && (
        <>
          <h3>Existencias</h3>
          {!consulta.existencias.length ? <p className="empty">El CD todavía no tiene stock. Registrá una compra.</p> : (
            <div className="table-scroll" role="region" aria-label="Existencias del CD" tabIndex="0">
              <table>
                <caption className="sr-only">Existencias del CD</caption>
                <thead><tr><th scope="col">Código</th><th scope="col">Producto</th><th scope="col">Estado del producto</th><th scope="col">Disponible</th><th scope="col">Costo de referencia</th></tr></thead>
                <tbody>{consulta.existencias.map((item) => (
                  <tr key={item.producto.id}>
                    <td>{item.producto.codigo}</td>
                    <td>{item.producto.nombre}</td>
                    <td>{item.producto.activo ? 'Activo' : 'Inactivo'}</td>
                    <td className="price">{item.disponible} u.</td>
                    <td className="price">{item.costo_referencia === null ? 'Sin costo registrado' : `$ ${item.costo_referencia}`}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
          <h3>Movimientos</h3>
          {!consulta.movimientos.length ? <p className="empty">Sin movimientos registrados.</p> : (
            <div className="table-scroll" role="region" aria-label="Movimientos del CD" tabIndex="0">
              <table>
                <caption className="sr-only">Movimientos del CD, del más reciente al más antiguo</caption>
                <thead><tr><th scope="col">N.º</th><th scope="col">Fecha y hora</th><th scope="col">Producto</th><th scope="col">Cantidad</th><th scope="col">Ingresa a</th><th scope="col">Origen</th></tr></thead>
                <tbody>{[...consulta.movimientos].reverse().map((item) => (
                  <tr key={item.id}>
                    <td>{item.id}</td>
                    <td>{formatearInstante(item.instante)}</td>
                    <td>{item.producto.codigo} · {item.producto.nombre}</td>
                    <td className="price">+{item.cantidad} u.</td>
                    <td>{CONDICIONES[item.condicion_destino] ?? item.condicion_destino}</td>
                    <td>Compra {item.compra_id}, línea {item.linea}</td>
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
