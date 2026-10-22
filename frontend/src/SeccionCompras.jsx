import { useEffect, useRef, useState } from 'react';
import { ErrorAPI, comprasAPI, formatearInstante } from './api';

function lineaVacia(clave) {
  return { clave, productoId: '', cantidad: '', costo: '' };
}

export default function SeccionCompras({ productos, proveedores, ubicaciones, bloqueado, estadoCatalogo, onActividad, onRegistrada }) {
  const centro = ubicaciones.find((item) => item.tipo === 'CD');
  const proveedoresActivos = proveedores.filter((item) => item.activo);
  const productosActivos = productos.filter((item) => item.activo);
  const siguienteClave = useRef(2);
  const [proveedorId, setProveedorId] = useState('');
  const [lineas, setLineas] = useState([lineaVacia(1)]);
  const [consulta, setConsulta] = useState({ estado: 'cargando', compras: [] });
  const [revision, setRevision] = useState(0);
  const [error, setError] = useState(null);
  const [exito, setExito] = useState('');
  const [enviando, setEnviando] = useState(false);
  const pendiente = useRef(false);
  const puedeGuardar = Boolean(centro) && !bloqueado && !enviando;

  useEffect(() => {
    const controller = new AbortController();
    setConsulta((actual) => ({ ...actual, estado: 'cargando' }));
    comprasAPI.listar(controller.signal)
      .then((compras) => {
        if (!controller.signal.aborted) setConsulta({ estado: 'lista', compras });
      })
      .catch((fallo) => {
        if (!controller.signal.aborted) setConsulta({ estado: 'error', compras: [], mensaje: fallo.message });
      });
    return () => controller.abort();
  }, [revision, productos, proveedores]);

  function limpiarAvisos() {
    setError(null);
    setExito('');
  }

  function cambiarLinea(clave, campo, valor) {
    setLineas((actual) => actual.map((linea) => linea.clave === clave ? { ...linea, [campo]: valor } : linea));
    limpiarAvisos();
  }

  function nuevaClave() {
    const clave = siguienteClave.current;
    siguienteClave.current += 1;
    return clave;
  }

  function agregarLinea() {
    const clave = nuevaClave();
    setLineas((actual) => [...actual, lineaVacia(clave)]);
    limpiarAvisos();
  }

  function quitarLinea(clave) {
    setLineas((actual) => actual.filter((linea) => linea.clave !== clave));
    limpiarAvisos();
  }

  function validarBorrador() {
    const campos = {};
    lineas.forEach((linea, indice) => {
      const texto = linea.cantidad.trim();
      if (!/^[0-9]+$/.test(texto) || !Number.isSafeInteger(Number(texto)) || Number(texto) === 0) {
        campos[`lineas.${indice + 1}.cantidad`] = 'Ingresá un entero de unidades mayor que cero.';
      }
    });
    return campos;
  }

  async function registrar(evento) {
    evento.preventDefault();
    if (pendiente.current || !puedeGuardar) return;
    const campos = validarBorrador();
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
      // El costo viaja como texto: Python valida el importe exacto, sin redondeos en JavaScript.
      const compra = await comprasAPI.registrar({
        proveedor_id: Number(proveedorId),
        lineas: lineas.map((linea) => ({
          producto_id: Number(linea.productoId), cantidad: Number(linea.cantidad.trim()), costo_unitario: linea.costo.trim(),
        })),
      });
      setConsulta((actual) => ({ ...actual, compras: [...actual.compras, compra] }));
      setProveedorId('');
      setLineas([lineaVacia(nuevaClave())]);
      setExito(`Compra ${compra.id} registrada por $ ${compra.total}. Su stock ya está disponible en el CD.`);
      onRegistrada();
    } catch (fallo) {
      setError(fallo);
    } finally {
      pendiente.current = false;
      setEnviando(false);
      onActividad(false);
    }
  }

  const campoError = (clave) => error?.campos?.[clave];

  return (
    <section className="catalog-section compras" aria-labelledby="compras-title">
      <div className="section-heading">
        <h2 id="compras-title">Compras al Centro de Distribución</h2>
        <button className="secondary" type="button" disabled={bloqueado || consulta.estado === 'cargando'}
          onClick={() => setRevision((valor) => valor + 1)}>
          Actualizar compras
        </button>
      </div>
      <p className="detail">Cada compra confirmada ingresa todas sus cantidades como disponibles en el CD. No se modifica ni se anula después.</p>
      {estadoCatalogo === 'lista' && !centro && <p className="empty">Registrá el Centro de Distribución para cargar compras.</p>}
      {estadoCatalogo === 'lista' && !proveedoresActivos.length && <p className="empty">Registrá un proveedor activo para cargar compras.</p>}
      {estadoCatalogo === 'lista' && !productosActivos.length && <p className="empty">Registrá un producto activo para cargar compras.</p>}
      <form onSubmit={registrar} aria-labelledby="compras-form-title">
        <h3 id="compras-form-title">Nueva compra</h3>
        {error && <p id="compras-error" className="notice error" role="alert">{error.message}</p>}
        {exito && <p className="notice success" role="status">{exito}</p>}
        {enviando && <p role="status">Registrando compra…</p>}
        <fieldset disabled={bloqueado || enviando || !centro}>
          <legend className="sr-only">Proveedor y líneas de la compra</legend>
          <div className="form-fields">
            <div>
              <label htmlFor="compra-proveedor">Proveedor</label>
              <select id="compra-proveedor" required value={proveedorId}
                aria-invalid={Boolean(campoError('proveedor_id')) || undefined}
                onChange={(evento) => { setProveedorId(evento.target.value); limpiarAvisos(); }}>
                <option value="">Elegí un proveedor</option>
                {proveedoresActivos.map((item) => <option key={item.id} value={item.id}>{item.codigo} · {item.nombre}</option>)}
              </select>
              {campoError('proveedor_id') && <p className="field-error">{campoError('proveedor_id')}</p>}
            </div>
            <div>
              <p className="detail">Destino: {centro ? `${centro.codigo} · ${centro.nombre}` : 'sin CD registrado'}</p>
            </div>
          </div>
          {lineas.map((linea, indice) => {
            const numero = indice + 1;
            const prefijo = `compra-linea-${linea.clave}`;
            const errores = ['producto_id', 'cantidad', 'costo_unitario']
              .map((campo) => campoError(`lineas.${numero}.${campo}`)).filter(Boolean);
            return (
              <fieldset key={linea.clave} className="purchase-line">
                <legend>Línea {numero}</legend>
                <div className="line-fields">
                  <div>
                    <label htmlFor={`${prefijo}-producto`}>Producto<span className="sr-only"> de la línea {numero}</span></label>
                    <select id={`${prefijo}-producto`} required value={linea.productoId}
                      aria-invalid={Boolean(campoError(`lineas.${numero}.producto_id`)) || undefined}
                      onChange={(evento) => cambiarLinea(linea.clave, 'productoId', evento.target.value)}>
                      <option value="">Elegí un producto</option>
                      {productosActivos.map((item) => <option key={item.id} value={item.id}>{item.codigo} · {item.nombre}</option>)}
                    </select>
                  </div>
                  <div>
                    <label htmlFor={`${prefijo}-cantidad`}>Cantidad (unidades)<span className="sr-only"> de la línea {numero}</span></label>
                    <input id={`${prefijo}-cantidad`} type="text" inputMode="numeric" required value={linea.cantidad}
                      aria-invalid={Boolean(campoError(`lineas.${numero}.cantidad`)) || undefined}
                      onChange={(evento) => cambiarLinea(linea.clave, 'cantidad', evento.target.value)} />
                  </div>
                  <div>
                    <label htmlFor={`${prefijo}-costo`}>Costo unitario (ARS)<span className="sr-only"> de la línea {numero}</span></label>
                    <input id={`${prefijo}-costo`} type="text" inputMode="decimal" required value={linea.costo}
                      placeholder="1250.50" aria-invalid={Boolean(campoError(`lineas.${numero}.costo_unitario`)) || undefined}
                      onChange={(evento) => cambiarLinea(linea.clave, 'costo', evento.target.value)} />
                  </div>
                  <div className="line-action">
                    <button className="secondary compact" type="button" disabled={lineas.length === 1}
                      onClick={() => quitarLinea(linea.clave)}>
                      Quitar línea {numero}
                    </button>
                  </div>
                </div>
                {errores.map((mensaje) => <p key={mensaje} className="field-error">{mensaje}</p>)}
              </fieldset>
            );
          })}
          <p className="detail">Costo con punto decimal y hasta dos decimales. Un producto no puede repetirse en la misma compra.</p>
          <div className="actions">
            <button className="secondary" type="button" onClick={agregarLinea}>Agregar línea</button>
            <button type="submit" disabled={!puedeGuardar}>{enviando ? 'Registrando…' : 'Confirmar compra'}</button>
          </div>
        </fieldset>
      </form>
      <h3>Compras registradas</h3>
      {consulta.estado === 'cargando' && <p role="status">Cargando compras…</p>}
      {consulta.estado === 'error' && <p className="notice error" role="alert">{consulta.mensaje} El borrador se conserva.</p>}
      {consulta.estado !== 'error' && !consulta.compras.length && consulta.estado === 'lista' && (
        <p className="empty">Todavía no hay compras registradas.</p>
      )}
      {consulta.compras.length > 0 && (
        <div className="table-scroll" role="region" aria-label="Compras registradas" tabIndex="0">
          <table>
            <caption className="sr-only">Compras registradas</caption>
            <thead><tr><th scope="col">N.º</th><th scope="col">Fecha y hora</th><th scope="col">Proveedor</th><th scope="col">Líneas</th><th scope="col" className="num">Total</th></tr></thead>
            <tbody>{[...consulta.compras].reverse().map((compra) => (
              <tr key={compra.id}>
                <td>{compra.id}</td>
                <td>{formatearInstante(compra.instante)}</td>
                <td>{compra.proveedor.codigo} · {compra.proveedor.nombre}</td>
                <td><ul className="plain-list">{compra.lineas.map((linea) => (
                  <li key={linea.linea}>{linea.producto.codigo} · {linea.producto.nombre}: {linea.cantidad} u. × $ {linea.costo_unitario}</li>
                ))}</ul></td>
                <td className="price">$ {compra.total}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </section>
  );
}
