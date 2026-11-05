import { useState } from 'react';
import { ErrorAPI, formatearInstante, logisticaAPI } from './api';
import { nombreUbicacion } from './etiquetas';

function esEnteroPositivo(texto) {
  return /^[0-9]+$/.test(texto) && Number.isSafeInteger(Number(texto)) && Number(texto) > 0;
}

export default function PanelReposicion({ datos, productos, ubicaciones, bloqueado, ejecutar }) {
  const locales = ubicaciones.filter((item) => item.tipo === 'LOCAL' && item.activo);
  const productosActivos = productos.filter((item) => item.activo);
  const [necesidad, setNecesidad] = useState({ localId: '', productoId: '', cantidad: '' });
  const [destinoId, setDestinoId] = useState('');
  const [elegidas, setElegidas] = useState([]);
  const [aviso, setAviso] = useState({ formulario: null, error: null, exito: '' });
  const pendientes = datos.necesidades.filter(
    (item) => item.estado === 'PENDIENTE' && String(item.local.id) === destinoId,
  );

  function avisar(formulario, resultado, exito) {
    setAviso(resultado.ok ? { formulario, error: null, exito } : { formulario, error: resultado.error, exito: '' });
  }

  async function registrar(evento) {
    evento.preventDefault();
    const cantidad = necesidad.cantidad.trim();
    if (!esEnteroPositivo(cantidad)) {
      const mensaje = 'Ingresá un entero de unidades mayor que cero.';
      setAviso({ formulario: 'necesidad', error: new ErrorAPI(mensaje, null, { cantidad: mensaje }), exito: '' });
      return;
    }
    const resultado = await ejecutar(() => logisticaAPI.registrarNecesidad({
      local_id: Number(necesidad.localId), producto_id: Number(necesidad.productoId), cantidad: Number(cantidad),
    }));
    if (resultado.ok) setNecesidad((actual) => ({ ...actual, cantidad: '' }));
    avisar('necesidad', resultado, resultado.ok && `Necesidad ${resultado.resultado.id} registrada para ${resultado.resultado.local.codigo}.`);
  }

  async function consolidar(evento) {
    evento.preventDefault();
    const resultado = await ejecutar(() => logisticaAPI.consolidar(Number(destinoId), elegidas));
    if (resultado.ok) setElegidas([]);
    avisar('orden', resultado, resultado.ok && `Orden ${resultado.resultado.id} creada hacia ${resultado.resultado.destino.codigo}.`);
  }

  function alternar(id) {
    setElegidas((actual) => actual.includes(id) ? actual.filter((item) => item !== id) : [...actual, id]);
    setAviso({ formulario: null, error: null, exito: '' });
  }

  const mensajes = (formulario) => aviso.formulario === formulario && (
    <>
      {aviso.error && <p className="notice error" role="alert">{aviso.error.message}</p>}
      {aviso.exito && <p className="notice success" role="status">{aviso.exito}</p>}
    </>
  );

  return (
    <div className="subsection">
      <h3>Necesidades y órdenes de reposición</h3>
      <div className="two-forms">
        <form onSubmit={registrar} aria-labelledby="necesidad-form-title">
          <h4 id="necesidad-form-title">Registrar necesidad de un local</h4>
          {mensajes('necesidad')}
          <fieldset disabled={bloqueado}>
            <legend className="sr-only">Local, producto y cantidad</legend>
            <label htmlFor="necesidad-local">Local que pide</label>
            <select id="necesidad-local" required value={necesidad.localId}
              onChange={(evento) => setNecesidad({ ...necesidad, localId: evento.target.value })}>
              <option value="">Elegí un local</option>
              {locales.map((item) => <option key={item.id} value={item.id}>{nombreUbicacion(item)}</option>)}
            </select>
            <label htmlFor="necesidad-producto">Producto</label>
            <select id="necesidad-producto" required value={necesidad.productoId}
              onChange={(evento) => setNecesidad({ ...necesidad, productoId: evento.target.value })}>
              <option value="">Elegí un producto</option>
              {productosActivos.map((item) => <option key={item.id} value={item.id}>{item.codigo} · {item.nombre}</option>)}
            </select>
            <label htmlFor="necesidad-cantidad">Cantidad (unidades)</label>
            <input id="necesidad-cantidad" type="text" inputMode="numeric" required value={necesidad.cantidad}
              aria-invalid={Boolean(aviso.formulario === 'necesidad' && aviso.error?.campos?.cantidad) || undefined}
              onChange={(evento) => setNecesidad({ ...necesidad, cantidad: evento.target.value })} />
            <div className="actions"><button type="submit">Registrar necesidad</button></div>
          </fieldset>
        </form>
        <form onSubmit={consolidar} aria-labelledby="orden-form-title">
          <h4 id="orden-form-title">Consolidar orden hacia un local</h4>
          {mensajes('orden')}
          <fieldset disabled={bloqueado}>
            <legend className="sr-only">Local destino y necesidades pendientes</legend>
            <label htmlFor="orden-destino">Local destino</label>
            <select id="orden-destino" required value={destinoId}
              onChange={(evento) => { setDestinoId(evento.target.value); setElegidas([]); }}>
              <option value="">Elegí un local</option>
              {locales.map((item) => <option key={item.id} value={item.id}>{nombreUbicacion(item)}</option>)}
            </select>
            {destinoId && !pendientes.length && <p className="empty">Este local no tiene necesidades pendientes.</p>}
            {pendientes.length > 0 && (
              <fieldset className="checklist">
                <legend>Necesidades pendientes a consolidar</legend>
                {pendientes.map((item) => (
                  <label key={item.id} className="check-option">
                    <input type="checkbox" checked={elegidas.includes(item.id)} onChange={() => alternar(item.id)} />
                    N.º {item.id}: {item.producto.codigo} · {item.producto.nombre}, {item.cantidad} u.
                  </label>
                ))}
              </fieldset>
            )}
            <div className="actions">
              <button type="submit" disabled={!elegidas.length}>
                Consolidar {elegidas.length ? `${elegidas.length} necesidad${elegidas.length > 1 ? 'es' : ''}` : 'orden'}
              </button>
            </div>
          </fieldset>
        </form>
      </div>
      <h4>Órdenes de reposición</h4>
      {!datos.ordenes.length ? <p className="empty">Todavía no hay órdenes.</p> : (
        <div className="table-scroll" role="region" aria-label="Órdenes de reposición" tabIndex="0">
          <table>
            <caption className="sr-only">Órdenes de reposición, de la más reciente a la más antigua</caption>
            <thead><tr><th scope="col">N.º</th><th scope="col">Fecha y hora</th><th scope="col">Origen</th><th scope="col">Destino</th><th scope="col">Estado</th><th scope="col">Productos (pedido · en bultos · pendiente)</th><th scope="col">Bultos</th></tr></thead>
            <tbody>{[...datos.ordenes].reverse().map((orden) => (
              <tr key={orden.id}>
                <td>{orden.id}</td>
                <td>{formatearInstante(orden.instante)}</td>
                <td>{orden.centro.codigo}</td>
                <td>{nombreUbicacion(orden.destino)}</td>
                <td>{orden.estado === 'COMPLETA' ? 'Completa' : 'Abierta'}</td>
                <td><ul className="plain-list">{orden.lineas.map((linea) => (
                  <li key={linea.producto.id}>{linea.producto.codigo} · {linea.producto.nombre}: {linea.solicitada} · {linea.asignada} · {linea.pendiente}</li>
                ))}</ul></td>
                <td>{orden.bultos.length ? orden.bultos.map((bulto) => bulto.codigo).join(', ') : 'Sin bultos'}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </div>
  );
}
