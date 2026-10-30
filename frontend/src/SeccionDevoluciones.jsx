import { useEffect, useRef, useState } from 'react';
import { ErrorAPI, devolucionesAPI, formatearInstante, ventasAPI } from './api';
import { CONDICIONES, nombreUbicacion } from './etiquetas';
import { aCentavos, aTexto } from './importes';

// Una clave por borrador: reenviarlo tras un fallo de red no registra otra devolución (RB-10).
function nuevaClaveOperacion() {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function cantidadValida(texto) {
  const limpio = texto.trim();
  return /^[0-9]+$/.test(limpio) && Number.isSafeInteger(Number(limpio)) && Number(limpio) > 0;
}

const BORRADOR_VACIO = { cantidades: {}, aptitudes: {}, importes: {}, motivo: '' };
const MOTIVO_MAXIMO = 200;

// Python numera las líneas y reintegros enviados (lineas.1, reintegros.2); la pantalla los ubica
// por línea vendida y por medio, que son las filas del formulario.
function camposDelFormulario(campos, lineasEnviadas, mediosEnviados) {
  const resultado = {};
  Object.entries(campos).forEach(([clave, mensaje]) => {
    const [grupo, numero, campo] = clave.split('.');
    const indice = Number(numero) - 1;
    if (grupo === 'lineas' && lineasEnviadas[indice] !== undefined) {
      resultado[`linea.${lineasEnviadas[indice]}.${campo === 'apto' ? 'apto' : 'cantidad'}`] = mensaje;
    } else if (grupo === 'reintegros' && mediosEnviados[indice] !== undefined) {
      resultado[`medio.${mediosEnviados[indice]}`] = mensaje;
    } else {
      resultado[clave] = mensaje;
    }
  });
  return resultado;
}

export default function SeccionDevoluciones({ ubicaciones, bloqueado, estadoCatalogo, revisionStock, onActividad, onCambio }) {
  const locales = ubicaciones.filter((item) => item.tipo === 'LOCAL');
  const claveOperacion = useRef(nuevaClaveOperacion());
  const pendiente = useRef(false);
  const [localId, setLocalId] = useState('');
  const [ventaId, setVentaId] = useState('');
  const [listas, setListas] = useState({ ventas: [], devoluciones: [] });
  const [consulta, setConsulta] = useState({ estado: 'lista' });
  const [estadoVenta, setEstadoVenta] = useState({ estado: 'cerrado' });
  const [revision, setRevision] = useState(0);
  const [borrador, setBorrador] = useState(BORRADOR_VACIO);
  const [error, setError] = useState(null);
  // Sin respuesta de Python no se sabe si la devolución quedó registrada; la misma clave permite reenviar.
  const [reenvioSeguro, setReenvioSeguro] = useState(false);
  const [exito, setExito] = useState('');
  const [enviando, setEnviando] = useState(false);
  const local = locales.find((item) => String(item.id) === localId);
  const venta = estadoVenta.estado === 'lista' ? estadoVenta.datos : null;
  const puedeDevolver = Boolean(local?.activo) && !bloqueado && !enviando;

  useEffect(() => {
    if (!localId) {
      setListas({ ventas: [], devoluciones: [] });
      return undefined;
    }
    const controller = new AbortController();
    setConsulta({ estado: 'cargando' });
    Promise.all([ventasAPI.listar(controller.signal), devolucionesAPI.listar(controller.signal)])
      .then(([ventas, devoluciones]) => {
        if (!controller.signal.aborted) {
          setListas({
            ventas: ventas.filter((item) => String(item.local.id) === localId),
            devoluciones: devoluciones.filter((item) => String(item.local.id) === localId),
          });
          setConsulta({ estado: 'lista' });
        }
      })
      .catch((fallo) => {
        if (!controller.signal.aborted) setConsulta({ estado: 'error', mensaje: fallo.message });
      });
    return () => controller.abort();
  }, [localId, revision, revisionStock]);

  useEffect(() => {
    if (!ventaId) {
      setEstadoVenta({ estado: 'cerrado' });
      return undefined;
    }
    const controller = new AbortController();
    setEstadoVenta({ estado: 'cargando' });
    devolucionesAPI.deVenta(ventaId, controller.signal)
      .then((datos) => { if (!controller.signal.aborted) setEstadoVenta({ estado: 'lista', datos }); })
      .catch((fallo) => {
        if (!controller.signal.aborted) setEstadoVenta({ estado: 'error', mensaje: fallo.message });
      });
    return () => controller.abort();
  }, [ventaId, revision]);

  // Estimación con el precio histórico de cada línea; Python calcula el reintegro al confirmar.
  const total = (venta?.lineas ?? []).reduce((suma, linea) => {
    const cantidad = borrador.cantidades[linea.linea] ?? '';
    return cantidadValida(cantidad) ? suma + aCentavos(linea.precio_unitario) * BigInt(cantidad.trim()) : suma;
  }, 0n);
  const reintegrado = Object.values(borrador.importes).reduce((suma, importe) => suma + (aCentavos(importe) ?? 0n), 0n);

  function limpiarAvisos() {
    setError(null);
    setReenvioSeguro(false);
    setExito('');
  }

  function nuevoBorrador() {
    claveOperacion.current = nuevaClaveOperacion();
    setBorrador(BORRADOR_VACIO);
  }

  function cambiar(grupo, clave, valor) {
    setBorrador((actual) => ({ ...actual, [grupo]: { ...actual[grupo], [clave]: valor } }));
    limpiarAvisos();
  }

  function completarImporte(medioId, maximo) {
    const otros = Object.entries(borrador.importes).reduce(
      (suma, [clave, importe]) => clave === String(medioId) ? suma : suma + (aCentavos(importe) ?? 0n), 0n,
    );
    const saldo = total - otros;
    const tope = aCentavos(maximo);
    cambiar('importes', medioId, aTexto(saldo > tope ? tope : saldo < 0n ? 0n : saldo));
  }

  async function registrar(evento) {
    evento.preventDefault();
    if (pendiente.current || !puedeDevolver || !venta) return;
    const campos = {};
    const lineas = venta.lineas.filter((linea) => (borrador.cantidades[linea.linea] ?? '').trim());
    lineas.forEach((linea) => {
      if (!cantidadValida(borrador.cantidades[linea.linea])) {
        campos[`linea.${linea.linea}.cantidad`] = 'Ingresá un entero de unidades mayor que cero.';
      }
      if (!borrador.aptitudes[linea.linea]) {
        campos[`linea.${linea.linea}.apto`] = 'Indicá si la mercadería es apta para volver a venderse.';
      }
    });
    if (!lineas.length) {
      setError(new ErrorAPI('Indicá la cantidad devuelta de al menos una línea.'));
      setExito('');
      return;
    }
    if (Object.keys(campos).length) {
      setError(new ErrorAPI('Revisá las líneas indicadas.', null, campos));
      setExito('');
      return;
    }
    const reintegros = venta.reintegrable.filter((item) => (borrador.importes[item.medio.id] ?? '').trim());
    pendiente.current = true;
    setEnviando(true);
    onActividad(true);
    limpiarAvisos();
    try {
      // Los importes viajan como texto: Python valida los centavos exactos, que sumen el total
      // y que ningún medio reintegre más de lo cobrado con él.
      const { devolucion, nueva } = await devolucionesAPI.registrar({
        venta_id: venta.venta_id,
        clave_operacion: claveOperacion.current,
        motivo: borrador.motivo,
        lineas: lineas.map((linea) => ({
          linea: linea.linea,
          cantidad: Number(borrador.cantidades[linea.linea].trim()),
          apto: borrador.aptitudes[linea.linea] === 'apto',
        })),
        reintegros: reintegros.map((item) => ({
          medio_pago_id: item.medio.id, importe: borrador.importes[item.medio.id].trim(),
        })),
      });
      nuevoBorrador();
      setExito(nueva
        ? `Devolución ${devolucion.numero} confirmada: se reintegraron $ ${devolucion.total}. El stock y la caja del local ya se actualizaron.`
        : `Este borrador ya se había registrado como ${devolucion.numero}. No se repitió la devolución ni el reintegro.`);
      setRevision((valor) => valor + 1);
      onCambio();
    } catch (fallo) {
      setError(new ErrorAPI(
        fallo.message, fallo.estado,
        camposDelFormulario(fallo.campos ?? {}, lineas.map((linea) => linea.linea), reintegros.map((item) => item.medio.id)),
      ));
      setReenvioSeguro(fallo.estado === null || fallo.estado >= 500);
    } finally {
      pendiente.current = false;
      setEnviando(false);
      onActividad(false);
    }
  }

  const campoError = (clave) => error?.campos?.[clave];
  const sinRemanente = venta && venta.lineas.every((linea) => linea.remanente === 0);

  return (
    <section className="catalog-section devoluciones" aria-labelledby="devoluciones-title">
      <div className="section-heading">
        <h2 id="devoluciones-title">Devoluciones de ventas</h2>
        <button className="secondary" type="button" disabled={bloqueado || enviando || consulta.estado === 'cargando'}
          onClick={() => setRevision((valor) => valor + 1)}>
          Actualizar devoluciones
        </button>
      </div>
      <p className="detail">Se devuelve en el mismo local de la venta, sin plazo, hasta la cantidad vendida de cada línea. Lo apto vuelve a estar disponible; lo no apto queda bloqueado y no se vende. El reintegro es al precio de la venta y se reparte entre los medios cobrados.</p>
      {estadoCatalogo === 'lista' && !locales.length && <p className="empty">Registrá un local para operar devoluciones.</p>}
      <div className="form-fields return-selectors">
        <div>
          <label htmlFor="devolucion-local">Local</label>
          <select id="devolucion-local" value={localId} disabled={bloqueado || enviando}
            onChange={(evento) => { setLocalId(evento.target.value); setVentaId(''); nuevoBorrador(); limpiarAvisos(); }}>
            <option value="">Elegí un local</option>
            {locales.map((item) => (
              <option key={item.id} value={item.id}>{nombreUbicacion(item)}{item.activo ? '' : ' (inactivo)'}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="devolucion-venta">Venta</label>
          <select id="devolucion-venta" value={ventaId} disabled={!local || bloqueado || enviando || !listas.ventas.length}
            onChange={(evento) => { setVentaId(evento.target.value); nuevoBorrador(); limpiarAvisos(); }}>
            <option value="">{local && consulta.estado === 'lista' && !listas.ventas.length ? 'Sin ventas en el local' : 'Elegí una venta'}</option>
            {[...listas.ventas].reverse().map((item) => (
              <option key={item.id} value={item.id}>
                {item.comprobante} · {formatearInstante(item.instante)} · $ {item.total}
              </option>
            ))}
          </select>
        </div>
      </div>
      {!localId && locales.length > 0 && <p className="empty">Elegí un local para devolver una de sus ventas y consultar sus devoluciones.</p>}
      {local && !local.activo && <p className="empty">El local está inactivo: se pueden consultar sus devoluciones, pero no registrar nuevas.</p>}
      {consulta.estado === 'cargando' && <p role="status">Cargando ventas y devoluciones…</p>}
      {consulta.estado === 'error' && <p className="notice error" role="alert">{consulta.mensaje} El borrador se conserva.</p>}
      {estadoVenta.estado === 'cargando' && <p role="status">Consultando lo que queda por devolver…</p>}
      {estadoVenta.estado === 'error' && <p className="notice error" role="alert">{estadoVenta.mensaje}</p>}
      {exito && !venta && <p className="notice success" role="status">{exito}</p>}

      {venta && (
        <form onSubmit={registrar} aria-labelledby="devolucion-form-title">
          <h3 id="devolucion-form-title">Devolver de la venta {venta.comprobante}</h3>
          {error && (
            <div className="notice error" role="alert">
              <p>{error.message}</p>
              {reenvioSeguro && <p>Podés volver a confirmar este borrador: si la devolución ya se había registrado, no se repetirá.</p>}
            </div>
          )}
          {exito && <p className="notice success" role="status">{exito}</p>}
          {enviando && <p role="status">Confirmando devolución…</p>}
          {sinRemanente && <p className="empty">Todas las unidades de esta venta ya se devolvieron.</p>}
          <fieldset disabled={!puedeDevolver || sinRemanente}>
            <legend className="sr-only">Líneas y reintegros de la devolución</legend>
            <p className="detail">Dejá vacía la cantidad de las líneas que no se devuelven.</p>
            {venta.lineas.map((linea) => {
              const prefijo = `devolucion-linea-${linea.linea}`;
              const cantidad = borrador.cantidades[linea.linea] ?? '';
              const errores = ['cantidad', 'apto'].map((campo) => campoError(`linea.${linea.linea}.${campo}`)).filter(Boolean);
              return (
                <fieldset key={linea.linea} className="purchase-line">
                  <legend>Línea {linea.linea}: {linea.producto.codigo} · {linea.producto.nombre}</legend>
                  <p className="detail">
                    Vendidas {linea.vendida} · ya devueltas {linea.devuelta} · quedan {linea.remanente} · $ {linea.precio_unitario} c/u
                  </p>
                  <div className="line-fields return-fields">
                    <div>
                      <label htmlFor={`${prefijo}-cantidad`}>Cantidad devuelta<span className="sr-only"> de la línea {linea.linea}</span></label>
                      <input id={`${prefijo}-cantidad`} type="text" inputMode="numeric" value={cantidad}
                        disabled={linea.remanente === 0} placeholder={linea.remanente ? `Hasta ${linea.remanente}` : 'Sin remanente'}
                        aria-invalid={Boolean(campoError(`linea.${linea.linea}.cantidad`)) || undefined}
                        onChange={(evento) => cambiar('cantidades', linea.linea, evento.target.value)} />
                    </div>
                    <div>
                      <label htmlFor={`${prefijo}-apto`}>Estado de la mercadería<span className="sr-only"> de la línea {linea.linea}</span></label>
                      <select id={`${prefijo}-apto`} value={borrador.aptitudes[linea.linea] ?? ''}
                        disabled={linea.remanente === 0} required={Boolean(cantidad.trim())}
                        aria-invalid={Boolean(campoError(`linea.${linea.linea}.apto`)) || undefined}
                        onChange={(evento) => cambiar('aptitudes', linea.linea, evento.target.value)}>
                        <option value="">Elegí tras revisarla</option>
                        <option value="apto">Apta: vuelve a estar disponible</option>
                        <option value="no-apto">No apta: queda bloqueada</option>
                      </select>
                    </div>
                    <div>
                      <p className="detail line-price">
                        {cantidadValida(cantidad)
                          ? `Reintegro $ ${aTexto(aCentavos(linea.precio_unitario) * BigInt(cantidad.trim()))}` : 'Sin reintegro'}
                      </p>
                    </div>
                  </div>
                  {errores.map((mensaje) => <p key={mensaje} className="field-error">{mensaje}</p>)}
                </fieldset>
              );
            })}
            <p className="sale-total">Reintegro estimado: <strong className="price">$ {aTexto(total)}</strong></p>

            <h4>Reintegros por medio cobrado</h4>
            {venta.reintegrable.map((item) => {
              const prefijo = `devolucion-medio-${item.medio.id}`;
              const mensaje = campoError(`medio.${item.medio.id}`);
              return (
                <fieldset key={item.medio.id} className="purchase-line">
                  <legend>{item.medio.nombre}</legend>
                  <div className="line-fields return-fields">
                    <div>
                      <label htmlFor={`${prefijo}-importe`}>Importe a reintegrar (ARS)<span className="sr-only"> con {item.medio.nombre}</span></label>
                      <input id={`${prefijo}-importe`} type="text" inputMode="decimal" placeholder="0.00"
                        value={borrador.importes[item.medio.id] ?? ''} aria-invalid={Boolean(mensaje) || undefined}
                        onChange={(evento) => cambiar('importes', item.medio.id, evento.target.value)} />
                    </div>
                    <div>
                      <p className="detail line-price">Disponible para reintegrar: $ {item.importe}</p>
                    </div>
                    <div className="line-action">
                      <button className="secondary compact" type="button" disabled={total === 0n}
                        onClick={() => completarImporte(item.medio.id, item.importe)}>
                        Completar con el saldo<span className="sr-only"> en {item.medio.nombre}</span>
                      </button>
                    </div>
                  </div>
                  {mensaje && <p className="field-error">{mensaje}</p>}
                </fieldset>
              );
            })}
            <p className={`sale-total ${total > 0n && reintegrado === total ? 'success' : ''}`}>
              Reintegrado: <span className="price">$ {aTexto(reintegrado)}</span> · Falta: <span className="price">$ {aTexto(total - reintegrado)}</span>
            </p>
            <p className="detail">Dejá vacío el medio que no se usa. Ningún medio reintegra más de lo que se cobró con él en esta venta.</p>

            <div className="return-reason">
              <label htmlFor="devolucion-motivo">Motivo</label>
              <input id="devolucion-motivo" type="text" required maxLength={MOTIVO_MAXIMO} value={borrador.motivo}
                aria-invalid={Boolean(error && /motivo/i.test(error.message)) || undefined}
                onChange={(evento) => { setBorrador((actual) => ({ ...actual, motivo: evento.target.value })); limpiarAvisos(); }} />
              <p className="detail">Hasta {MOTIVO_MAXIMO} caracteres. Una devolución confirmada no se modifica.</p>
            </div>
            <div className="actions">
              <button type="submit" disabled={!puedeDevolver || sinRemanente}>{enviando ? 'Confirmando…' : 'Confirmar devolución'}</button>
            </div>
          </fieldset>
        </form>
      )}

      {local && consulta.estado === 'lista' && (
        <>
          <h3>Devoluciones de {local.codigo}</h3>
          {!listas.devoluciones.length ? <p className="empty">Todavía no hay devoluciones en este local.</p> : (
            <div className="table-scroll" role="region" aria-label={`Devoluciones de ${local.codigo}`} tabIndex="0">
              <table>
                <caption className="sr-only">Devoluciones, de la más reciente a la más antigua</caption>
                <thead><tr><th scope="col">Número</th><th scope="col">Fecha y hora</th><th scope="col">Venta</th><th scope="col">Líneas</th><th scope="col">Reintegros</th><th scope="col">Motivo</th><th scope="col" className="num">Total</th></tr></thead>
                <tbody>{[...listas.devoluciones].reverse().map((item) => (
                  <tr key={item.id}>
                    <td>{item.numero}</td>
                    <td>{formatearInstante(item.instante)}</td>
                    <td>{item.comprobante}</td>
                    <td><ul className="plain-list">{item.lineas.map((linea) => (
                      <li key={linea.linea}>
                        {linea.producto.codigo} · {linea.producto.nombre}: {linea.cantidad} u., {linea.apto ? 'apta' : 'no apta'} → {CONDICIONES[linea.condicion_destino]}
                      </li>
                    ))}</ul></td>
                    <td><ul className="plain-list">{item.reintegros.map((reintegro) => (
                      <li key={reintegro.numero}>{reintegro.medio.nombre}: $ {reintegro.importe}</li>
                    ))}</ul></td>
                    <td>{item.motivo}</td>
                    <td className="price">$ {item.total}</td>
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
