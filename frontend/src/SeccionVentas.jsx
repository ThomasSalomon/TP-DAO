import { useEffect, useRef, useState } from 'react';
import { ErrorAPI, formatearInstante, stockAPI, ventasAPI } from './api';
import ComprobanteVenta from './ComprobanteVenta';
import { TIPOS_CAJA, nombreUbicacion, origenCaja } from './etiquetas';
import { aCentavos, aTexto } from './importes';

function lineaVacia(clave) {
  return { clave, productoId: '', cantidad: '' };
}

function cobroVacio(clave) {
  return { clave, medioId: '', importe: '' };
}

// Una clave por borrador: reenviarlo tras un fallo de red no registra otra venta (RB-10).
function nuevaClaveOperacion() {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function cantidadValida(texto) {
  const limpio = texto.trim();
  return /^[0-9]+$/.test(limpio) && Number.isSafeInteger(Number(limpio)) && Number(limpio) > 0;
}

const SIN_DATOS = { existencias: [], ventas: [], caja: null };

export default function SeccionVentas({
  productos, ubicaciones, bloqueado, estadoCatalogo, revisionStock, onActividad, onCambio,
}) {
  const locales = ubicaciones.filter((item) => item.tipo === 'LOCAL');
  const productosActivos = productos.filter((item) => item.activo);
  const siguienteClave = useRef(2);
  const claveOperacion = useRef(nuevaClaveOperacion());
  const pendiente = useRef(false);
  const [localId, setLocalId] = useState('');
  const [medios, setMedios] = useState([]);
  const [datos, setDatos] = useState(SIN_DATOS);
  const [consulta, setConsulta] = useState({ estado: 'lista' });
  const [revision, setRevision] = useState(0);
  const [lineas, setLineas] = useState([lineaVacia(1)]);
  const [cobros, setCobros] = useState([cobroVacio(1)]);
  const [error, setError] = useState(null);
  // Sin respuesta de Python no se sabe si la venta quedó registrada; la misma clave permite reenviar sin duplicarla.
  const [reenvioSeguro, setReenvioSeguro] = useState(false);
  const [exito, setExito] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [comprobante, setComprobante] = useState({ estado: 'cerrado' });
  const local = locales.find((item) => String(item.id) === localId);
  const puedeVender = Boolean(local?.activo) && !bloqueado && !enviando;

  useEffect(() => {
    const controller = new AbortController();
    ventasAPI.medios(controller.signal)
      .then((resultado) => { if (!controller.signal.aborted) setMedios(resultado); })
      .catch(() => {});
    return () => controller.abort();
  }, [revision]);

  useEffect(() => {
    if (!localId) {
      setDatos(SIN_DATOS);
      return undefined;
    }
    const controller = new AbortController();
    setConsulta({ estado: 'cargando' });
    Promise.all([
      stockAPI.existencias(localId, controller.signal),
      ventasAPI.listar(controller.signal),
      ventasAPI.caja(localId, controller.signal),
    ])
      .then(([existencias, ventas, caja]) => {
        if (!controller.signal.aborted) {
          setDatos({
            existencias: existencias.existencias,
            ventas: ventas.filter((venta) => String(venta.local.id) === localId),
            caja,
          });
          setConsulta({ estado: 'lista' });
        }
      })
      .catch((fallo) => {
        if (!controller.signal.aborted) setConsulta({ estado: 'error', mensaje: fallo.message });
      });
    return () => controller.abort();
    // revisionStock cambia también con las devoluciones, que modifican el stock y la caja del local.
  }, [localId, revision, productos, revisionStock]);

  const disponibles = new Map(datos.existencias.map((item) => [item.producto.id, item.disponible]));
  const precios = new Map(productos.map((item) => [item.id, item.precio]));

  // Estimación con el precio que muestra el catálogo; Python copia el vigente al confirmar.
  const total = lineas.reduce((suma, linea) => {
    const precio = precios.get(Number(linea.productoId));
    return precio && cantidadValida(linea.cantidad)
      ? suma + aCentavos(precio) * BigInt(linea.cantidad.trim()) : suma;
  }, 0n);
  const cobrado = cobros.reduce((suma, cobro) => suma + (aCentavos(cobro.importe) ?? 0n), 0n);

  function limpiarAvisos() {
    setError(null);
    setReenvioSeguro(false);
    setExito('');
  }

  function nuevaClave() {
    const clave = siguienteClave.current;
    siguienteClave.current += 1;
    return clave;
  }

  function cambiar(setter, clave, campo, valor) {
    setter((actual) => actual.map((item) => item.clave === clave ? { ...item, [campo]: valor } : item));
    limpiarAvisos();
  }

  function completarImporte(clave) {
    const otros = cobros.reduce(
      (suma, cobro) => cobro.clave === clave ? suma : suma + (aCentavos(cobro.importe) ?? 0n), 0n,
    );
    cambiar(setCobros, clave, 'importe', aTexto(total - otros));
  }

  async function abrirComprobante(ventaId) {
    setComprobante({ estado: 'cargando' });
    try {
      setComprobante({ estado: 'listo', datos: await ventasAPI.comprobante(ventaId) });
    } catch (fallo) {
      setComprobante({ estado: 'error', mensaje: fallo.message });
    }
  }

  async function registrar(evento) {
    evento.preventDefault();
    if (pendiente.current || !puedeVender) return;
    const campos = {};
    lineas.forEach((linea, indice) => {
      if (!cantidadValida(linea.cantidad)) {
        campos[`lineas.${indice + 1}.cantidad`] = 'Ingresá un entero de unidades mayor que cero.';
      }
    });
    if (Object.keys(campos).length) {
      setError(new ErrorAPI('Revisá las cantidades indicadas.', null, campos));
      setExito('');
      return;
    }
    pendiente.current = true;
    setEnviando(true);
    onActividad(true);
    limpiarAvisos();
    try {
      // Los importes viajan como texto: Python valida los centavos exactos y que sumen el total.
      const { venta, nueva } = await ventasAPI.registrar({
        local_id: Number(localId),
        clave_operacion: claveOperacion.current,
        lineas: lineas.map((linea) => ({ producto_id: Number(linea.productoId), cantidad: Number(linea.cantidad.trim()) })),
        cobros: cobros.map((cobro) => ({ medio_pago_id: Number(cobro.medioId), importe: cobro.importe.trim() })),
      });
      claveOperacion.current = nuevaClaveOperacion();
      setLineas([lineaVacia(nuevaClave())]);
      setCobros([cobroVacio(nuevaClave())]);
      setExito(nueva
        ? `Venta ${venta.comprobante} confirmada por $ ${venta.total}. El stock y la caja del local ya se actualizaron.`
        : `Este borrador ya se había registrado como ${venta.comprobante}. No se repitió la venta ni el cobro.`);
      setRevision((valor) => valor + 1);
      onCambio();
      abrirComprobante(venta.id);
    } catch (fallo) {
      setError(fallo);
      setReenvioSeguro(fallo.estado === null || fallo.estado >= 500);
    } finally {
      pendiente.current = false;
      setEnviando(false);
      onActividad(false);
    }
  }

  const campoError = (clave) => error?.campos?.[clave];

  return (
    <section className="catalog-section ventas" aria-labelledby="ventas-title">
      <div className="section-heading">
        <h2 id="ventas-title">Ventas, cobros y caja del local</h2>
        <button className="secondary" type="button" disabled={bloqueado || enviando || consulta.estado === 'cargando'}
          onClick={() => setRevision((valor) => valor + 1)}>
          Actualizar ventas
        </button>
      </div>
      <p className="detail">Sólo se vende stock disponible del local: lo pendiente de verificación, en tránsito o rechazado no se ofrece. Los cobros deben sumar exactamente el total y una venta confirmada no se modifica.</p>
      {estadoCatalogo === 'lista' && !locales.length && <p className="empty">Registrá un local para vender.</p>}
      <div className="stock-selector">
        <label htmlFor="venta-local">Local</label>
        <select id="venta-local" value={localId} disabled={bloqueado || enviando}
          onChange={(evento) => { setLocalId(evento.target.value); limpiarAvisos(); setComprobante({ estado: 'cerrado' }); }}>
          <option value="">Elegí un local</option>
          {locales.map((item) => (
            <option key={item.id} value={item.id}>{nombreUbicacion(item)}{item.activo ? '' : ' (inactivo)'}</option>
          ))}
        </select>
      </div>
      {!localId && locales.length > 0 && <p className="empty">Elegí un local para registrar una venta y consultar sus ventas y su caja.</p>}
      {local && !local.activo && <p className="empty">El local está inactivo: se pueden consultar sus ventas y su caja, pero no registrar ventas nuevas.</p>}
      {consulta.estado === 'cargando' && <p role="status">Cargando ventas y caja…</p>}
      {consulta.estado === 'error' && <p className="notice error" role="alert">{consulta.mensaje} El borrador se conserva.</p>}

      {local && (
        <form onSubmit={registrar} aria-labelledby="ventas-form-title">
          <h3 id="ventas-form-title">Nueva venta en {local.codigo}</h3>
          {error && (
            <div className="notice error" role="alert">
              <p>{error.message}</p>
              {reenvioSeguro && <p>Podés volver a confirmar este borrador: si la venta ya se había registrado, no se repetirá.</p>}
            </div>
          )}
          {exito && <p className="notice success" role="status">{exito}</p>}
          {enviando && <p role="status">Confirmando venta…</p>}
          <fieldset disabled={!puedeVender}>
            <legend className="sr-only">Productos y cobros de la venta</legend>
            {lineas.map((linea, indice) => {
              const numero = indice + 1;
              const prefijo = `venta-linea-${linea.clave}`;
              const producto = productos.find((item) => String(item.id) === linea.productoId);
              const errores = ['producto_id', 'cantidad']
                .map((campo) => campoError(`lineas.${numero}.${campo}`)).filter(Boolean);
              return (
                <fieldset key={linea.clave} className="purchase-line">
                  <legend>Línea {numero}</legend>
                  <div className="line-fields sale-fields">
                    <div>
                      <label htmlFor={`${prefijo}-producto`}>Producto<span className="sr-only"> de la línea {numero}</span></label>
                      <select id={`${prefijo}-producto`} required value={linea.productoId}
                        aria-invalid={Boolean(campoError(`lineas.${numero}.producto_id`)) || undefined}
                        onChange={(evento) => cambiar(setLineas, linea.clave, 'productoId', evento.target.value)}>
                        <option value="">Elegí un producto</option>
                        {productosActivos.map((item) => (
                          <option key={item.id} value={item.id}>
                            {item.codigo} · {item.nombre} — {disponibles.get(item.id) ?? 0} u. disponibles
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label htmlFor={`${prefijo}-cantidad`}>Cantidad (unidades)<span className="sr-only"> de la línea {numero}</span></label>
                      <input id={`${prefijo}-cantidad`} type="text" inputMode="numeric" required value={linea.cantidad}
                        aria-invalid={Boolean(campoError(`lineas.${numero}.cantidad`)) || undefined}
                        onChange={(evento) => cambiar(setLineas, linea.clave, 'cantidad', evento.target.value)} />
                    </div>
                    <div>
                      <p className="detail line-price">
                        {producto ? `Precio $ ${producto.precio}` : 'Sin producto'}
                        {producto && cantidadValida(linea.cantidad)
                          ? ` · Subtotal $ ${aTexto(aCentavos(producto.precio) * BigInt(linea.cantidad.trim()))}` : ''}
                      </p>
                    </div>
                    <div className="line-action">
                      <button className="secondary compact" type="button" disabled={lineas.length === 1}
                        onClick={() => { setLineas((actual) => actual.filter((item) => item.clave !== linea.clave)); limpiarAvisos(); }}>
                        Quitar línea {numero}
                      </button>
                    </div>
                  </div>
                  {errores.map((mensaje) => <p key={mensaje} className="field-error">{mensaje}</p>)}
                </fieldset>
              );
            })}
            <div className="actions">
              <button className="secondary" type="button"
                onClick={() => { setLineas((actual) => [...actual, lineaVacia(nuevaClave())]); limpiarAvisos(); }}>
                Agregar producto
              </button>
            </div>
            <p className="sale-total">Total estimado: <strong className="price">$ {aTexto(total)}</strong></p>
            <p className="detail">Python usa el precio vigente del catálogo al confirmar; si cambió, la venta se rechaza hasta ajustar los cobros.</p>

            <h4>Cobros</h4>
            {cobros.map((cobro, indice) => {
              const numero = indice + 1;
              const prefijo = `venta-cobro-${cobro.clave}`;
              const errores = ['medio_pago_id', 'importe']
                .map((campo) => campoError(`cobros.${numero}.${campo}`)).filter(Boolean);
              return (
                <fieldset key={cobro.clave} className="purchase-line">
                  <legend>Cobro {numero}</legend>
                  <div className="line-fields sale-fields">
                    <div>
                      <label htmlFor={`${prefijo}-medio`}>Medio de pago<span className="sr-only"> del cobro {numero}</span></label>
                      <select id={`${prefijo}-medio`} required value={cobro.medioId}
                        aria-invalid={Boolean(campoError(`cobros.${numero}.medio_pago_id`)) || undefined}
                        onChange={(evento) => cambiar(setCobros, cobro.clave, 'medioId', evento.target.value)}>
                        <option value="">Elegí un medio</option>
                        {medios.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}
                      </select>
                    </div>
                    <div>
                      <label htmlFor={`${prefijo}-importe`}>Importe (ARS)<span className="sr-only"> del cobro {numero}</span></label>
                      <input id={`${prefijo}-importe`} type="text" inputMode="decimal" required value={cobro.importe}
                        placeholder="1500.00" aria-invalid={Boolean(campoError(`cobros.${numero}.importe`)) || undefined}
                        onChange={(evento) => cambiar(setCobros, cobro.clave, 'importe', evento.target.value)} />
                    </div>
                    <div className="line-action">
                      <button className="secondary compact" type="button" disabled={total === 0n}
                        onClick={() => completarImporte(cobro.clave)}>
                        Completar con el saldo<span className="sr-only"> en el cobro {numero}</span>
                      </button>
                    </div>
                    <div className="line-action">
                      <button className="secondary compact" type="button" disabled={cobros.length === 1}
                        onClick={() => { setCobros((actual) => actual.filter((item) => item.clave !== cobro.clave)); limpiarAvisos(); }}>
                        Quitar cobro {numero}
                      </button>
                    </div>
                  </div>
                  {errores.map((mensaje) => <p key={mensaje} className="field-error">{mensaje}</p>)}
                </fieldset>
              );
            })}
            <p className={`sale-total ${cobrado === total ? 'success' : ''}`}>
              Cobrado: <span className="price">$ {aTexto(cobrado)}</span> · Falta: <span className="price">$ {aTexto(total - cobrado)}</span>
            </p>
            <p className="detail">Un medio por cobro, sin repetirlo. Sin vuelto: registrá el importe aplicado a la venta.</p>
            <div className="actions">
              <button className="secondary" type="button" disabled={cobros.length >= medios.length}
                onClick={() => { setCobros((actual) => [...actual, cobroVacio(nuevaClave())]); limpiarAvisos(); }}>
                Agregar cobro
              </button>
              <button type="submit" disabled={!puedeVender}>{enviando ? 'Confirmando…' : 'Confirmar venta'}</button>
            </div>
          </fieldset>
        </form>
      )}

      {comprobante.estado === 'cargando' && <p role="status">Consultando comprobante…</p>}
      {comprobante.estado === 'error' && <p className="notice error" role="alert">{comprobante.mensaje}</p>}
      {comprobante.estado === 'listo' && (
        <ComprobanteVenta comprobante={comprobante.datos} onCerrar={() => setComprobante({ estado: 'cerrado' })} />
      )}

      {local && consulta.estado === 'lista' && (
        <>
          <h3>Ventas de {local.codigo}</h3>
          {!datos.ventas.length ? <p className="empty">Todavía no hay ventas en este local.</p> : (
            <div className="table-scroll" role="region" aria-label={`Ventas de ${local.codigo}`} tabIndex="0">
              <table>
                <caption className="sr-only">Ventas, de la más reciente a la más antigua</caption>
                <thead><tr><th scope="col">Comprobante</th><th scope="col">Fecha y hora</th><th scope="col">Líneas</th><th scope="col">Cobros</th><th scope="col" className="num">Total</th><th scope="col"><span className="sr-only">Acciones</span></th></tr></thead>
                <tbody>{[...datos.ventas].reverse().map((venta) => (
                  <tr key={venta.id}>
                    <td>{venta.comprobante}</td>
                    <td>{formatearInstante(venta.instante)}</td>
                    <td><ul className="plain-list">{venta.lineas.map((linea) => (
                      <li key={linea.linea}>{linea.producto.codigo} · {linea.producto.nombre}: {linea.cantidad} u. × $ {linea.precio_unitario}</li>
                    ))}</ul></td>
                    <td><ul className="plain-list">{venta.cobros.map((cobro) => (
                      <li key={cobro.numero}>{cobro.medio.nombre}: $ {cobro.importe}</li>
                    ))}</ul></td>
                    <td className="price">$ {venta.total}</td>
                    <td>
                      <button className="secondary compact" type="button" onClick={() => abrirComprobante(venta.id)}>
                        Ver comprobante<span className="sr-only"> {venta.comprobante}</span>
                      </button>
                    </td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}

          <h3>Caja de {local.codigo}</h3>
          {datos.caja && (
            <>
              <div className="table-scroll cash-balances" role="region" aria-label={`Saldos de caja de ${local.codigo}`} tabIndex="0">
                <table>
                  <caption className="sr-only">Saldo por medio de pago, calculado desde los movimientos</caption>
                  <thead><tr>{datos.caja.saldos.map((item) => <th key={item.medio.id} scope="col" className="num">{item.medio.nombre}</th>)}</tr></thead>
                  <tbody><tr>{datos.caja.saldos.map((item) => <td key={item.medio.id} className="price">$ {item.saldo}</td>)}</tr></tbody>
                </table>
              </div>
              {!datos.caja.movimientos.length ? <p className="empty">Sin movimientos de caja.</p> : (
                <div className="table-scroll" role="region" aria-label={`Movimientos de caja de ${local.codigo}`} tabIndex="0">
                  <table>
                    <caption className="sr-only">Movimientos de caja, del más reciente al más antiguo</caption>
                    <thead><tr><th scope="col">N.º</th><th scope="col">Fecha y hora</th><th scope="col">Medio</th><th scope="col">Tipo</th><th scope="col" className="num">Importe</th><th scope="col">Origen</th></tr></thead>
                    <tbody>{[...datos.caja.movimientos].reverse().map((item) => (
                      <tr key={item.id}>
                        <td>{item.id}</td>
                        <td>{formatearInstante(item.instante)}</td>
                        <td>{item.medio.nombre}</td>
                        <td>{TIPOS_CAJA[item.tipo] ?? item.tipo}</td>
                        <td className="price">$ {item.importe}</td>
                        <td>{origenCaja(item)}</td>
                      </tr>
                    ))}</tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </>
      )}
    </section>
  );
}
