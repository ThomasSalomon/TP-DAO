import { useEffect, useRef, useState } from 'react';
import { ErrorAPI, minimosAPI } from './api';

export default function SeccionMinimos({ productos, ubicaciones, bloqueado, estadoCatalogo, onActividad }) {
  const locales = ubicaciones.filter((item) => item.tipo === 'LOCAL');
  const [localId, setLocalId] = useState('');
  const [productoId, setProductoId] = useState('');
  const [cantidad, setCantidad] = useState('');
  const [consulta, setConsulta] = useState({ estado: 'inicial', minimos: [] });
  const [revision, setRevision] = useState(0);
  const [error, setError] = useState(null);
  const [exito, setExito] = useState('');
  const [enviando, setEnviando] = useState(false);
  const pendiente = useRef(false);
  const local = locales.find((item) => String(item.id) === localId);
  const producto = productos.find((item) => String(item.id) === productoId);
  const lista = consulta.estado === 'lista' && consulta.localId === localId;
  const configuracion = lista && consulta.minimos.find((item) => String(item.producto.id) === productoId);
  const puedeGuardar = lista && local && producto && !bloqueado && !enviando;

  useEffect(() => {
    if (!localId) {
      setConsulta({ estado: 'inicial', minimos: [] });
      return;
    }
    const controller = new AbortController();
    setConsulta({ estado: 'cargando', localId, minimos: [] });
    minimosAPI.listar(Number(localId), controller.signal)
      .then((datos) => {
        if (!controller.signal.aborted) setConsulta({ estado: 'lista', localId, minimos: datos.minimos });
      })
      .catch((fallo) => {
        if (!controller.signal.aborted) setConsulta({ estado: 'error', localId, minimos: [], mensaje: fallo.message });
      });
    return () => controller.abort();
  }, [localId, revision, productos, ubicaciones]);

  function seleccionar(campo, valor) {
    if (campo === 'local') setLocalId(valor);
    else setProductoId(valor);
    setCantidad('');
    setError(null);
    setExito('');
  }

  async function guardar(evento) {
    evento.preventDefault();
    if (pendiente.current || !puedeGuardar) return;
    const texto = cantidad.trim();
    const minimo = Number(texto);
    if (!/^[0-9]+$/.test(texto) || !Number.isSafeInteger(minimo)) {
      const mensaje = 'Ingresá un entero de unidades mayor o igual a cero, dentro del rango admitido.';
      setError(new ErrorAPI(mensaje, null, { minimo: mensaje }));
      setExito('');
      return;
    }
    pendiente.current = true;
    setEnviando(true);
    onActividad(true);
    setError(null);
    setExito('');
    try {
      const resultado = await minimosAPI.establecer(local.id, producto.id, minimo);
      setConsulta((actual) => ({
        ...actual,
        minimos: [
          ...actual.minimos.filter((item) => item.producto.id !== resultado.producto.id),
          { producto: resultado.producto, minimo: resultado.minimo },
        ],
      }));
      setCantidad(String(resultado.minimo));
      setExito('Mínimo guardado.');
    } catch (fallo) {
      setError(fallo);
    } finally {
      pendiente.current = false;
      setEnviando(false);
      onActividad(false);
    }
  }

  return (
    <section className="catalog-section minimos" aria-labelledby="minimos-title">
      <div className="section-heading">
        <h2 id="minimos-title">Mínimos por producto y local</h2>
        <button className="secondary" type="button"
          disabled={!local || bloqueado || consulta.estado === 'cargando'}
          onClick={() => setRevision((valor) => valor + 1)}>
          Actualizar mínimos
        </button>
      </div>
      <p className="detail">Configuración administrativa en unidades enteras. No representa cantidades disponibles.</p>
      {estadoCatalogo === 'lista' && !locales.length && <p className="empty">Registrá un local para configurar mínimos.</p>}
      {estadoCatalogo === 'lista' && !productos.length && <p className="empty">Registrá un producto para configurar mínimos.</p>}
      <form onSubmit={guardar} aria-labelledby="minimos-form-title">
        <h3 id="minimos-form-title">Configurar mínimo</h3>
        {error && <p id="minimos-error" className="notice error" role="alert">{error.message}</p>}
        {exito && <p className="notice success" role="status">{exito}</p>}
        {enviando && <p role="status">Guardando mínimo…</p>}
        <fieldset disabled={bloqueado || enviando}>
          <legend className="sr-only">Producto, local y mínimo</legend>
          <div className="form-fields">
            <div>
              <label htmlFor="minimos-local">Local del mínimo</label>
              <select id="minimos-local" required value={localId}
                onChange={(evento) => seleccionar('local', evento.target.value)}>
                <option value="">Elegí un local</option>
                {locales.map((item) => <option key={item.id} value={item.id}>{item.codigo} · {item.nombre}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="minimos-producto">Producto del mínimo</label>
              <select id="minimos-producto" required value={productoId}
                onChange={(evento) => seleccionar('producto', evento.target.value)}>
                <option value="">Elegí un producto</option>
                {productos.map((item) => <option key={item.id} value={item.id}>{item.codigo} · {item.nombre}</option>)}
              </select>
            </div>
            <div>
              <p role="status">Mínimo vigente: {!local || !producto ? 'Seleccioná un local y un producto.'
                : consulta.estado === 'error' ? 'Consulta no disponible.'
                : !lista ? 'Pendiente de consulta.'
                  : configuracion ? `${configuracion.minimo} unidades` : 'Sin configurar'}</p>
              <label htmlFor="minimos-cantidad">Nuevo mínimo (unidades)</label>
              <input id="minimos-cantidad" type="text" inputMode="numeric" required
                disabled={!lista || !local || !producto} value={cantidad}
                aria-invalid={Boolean(error?.campos?.minimo) || undefined}
                aria-describedby={`minimos-ayuda${error ? ' minimos-error' : ''}`}
                onChange={(evento) => { setCantidad(evento.target.value); setError(null); setExito(''); }} />
              <p id="minimos-ayuda" className="detail">Usá un entero no negativo. Cero es un mínimo configurado.</p>
            </div>
          </div>
          <div className="actions"><button type="submit" disabled={!puedeGuardar}>
            {enviando ? 'Guardando…' : 'Guardar mínimo'}
          </button></div>
        </fieldset>
      </form>
      {consulta.estado === 'cargando' && <p role="status">Cargando mínimos…</p>}
      {consulta.estado === 'error' && <p className="notice error" role="alert">{consulta.mensaje} Los borradores se conservan.</p>}
      <h3>Configuraciones del local</h3>
      {!localId ? <p className="empty">Seleccioná un local para consultar sus configuraciones.</p>
        : lista && !consulta.minimos.length ? <p className="empty">Este local no tiene mínimos configurados.</p>
          : lista && (
            <div className="table-scroll" role="region" aria-label="Mínimos configurados del local" tabIndex="0">
              <table>
                <caption className="sr-only">Mínimos configurados del local</caption>
                <thead><tr><th scope="col">Código de producto</th><th scope="col">Producto</th><th scope="col">Mínimo</th></tr></thead>
                <tbody>{consulta.minimos.map((item) => (
                  <tr key={item.producto.id}><td>{item.producto.codigo}</td><td>{item.producto.nombre}</td><td>{item.minimo} unidades</td></tr>
                ))}</tbody>
              </table>
            </div>
          )}
    </section>
  );
}
