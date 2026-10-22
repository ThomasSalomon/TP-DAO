import { useEffect, useRef, useState } from 'react';
import { catalogoAPI } from './api';
import FormularioCatalogo from './FormularioCatalogo';

export default function SeccionCatalogo({
  tipo, registros, categorias, bloqueado, estadoConsulta, onGuardar, onDesactivar, onActividad,
}) {
  const esProducto = tipo === 'productos';
  const esUbicacion = tipo === 'ubicaciones';
  const singular = {
    categorias: 'categoría', productos: 'producto', proveedores: 'proveedor', ubicaciones: 'ubicación',
  }[tipo];
  const titulo = {
    categorias: 'Categorías', productos: 'Productos', proveedores: 'Proveedores', ubicaciones: 'Ubicaciones',
  }[tipo];
  const listado = `${titulo} ${tipo === 'categorias' || esUbicacion ? 'registradas' : 'registrados'}`;
  const [edicion, setEdicion] = useState(null);
  const [consultando, setConsultando] = useState(false);
  const [errorConsulta, setErrorConsulta] = useState('');
  const [estado, setEstado] = useState('activos');
  const [confirmacion, setConfirmacion] = useState(null);
  const [enviandoBaja, setEnviandoBaja] = useState(false);
  const [mensajeBaja, setMensajeBaja] = useState('');
  const pendienteBaja = useRef(false);
  const focoPendiente = useRef(false);
  const filtro = useRef(null);
  const consulta = useRef(null);
  const visibles = registros.filter((item) => estado === 'todos' || item.activo === (estado === 'activos'));
  const soloLectura = edicion && (edicion.activo === false || registros.find((item) => item.id === edicion.id)?.activo === false);

  useEffect(() => () => consulta.current?.abort(), []);
  useEffect(() => {
    if (focoPendiente.current && !bloqueado && !enviandoBaja && !confirmacion) {
      filtro.current?.focus();
      focoPendiente.current = false;
    }
  }, [bloqueado, enviandoBaja, confirmacion]);

  async function editar(id) {
    const controller = new AbortController();
    consulta.current = controller;
    setConsultando(true);
    setErrorConsulta('');
    try {
      const api = catalogoAPI[tipo];
      const registro = await api.obtener(id, controller.signal);
      if (!controller.signal.aborted) setEdicion(registro);
    } catch (error) {
      if (!controller.signal.aborted) setErrorConsulta(error.message);
    } finally {
      if (!controller.signal.aborted) setConsultando(false);
    }
  }

  async function confirmarBaja() {
    if (pendienteBaja.current || bloqueado || !confirmacion) return;
    pendienteBaja.current = true;
    setEnviandoBaja(true);
    onActividad(tipo, true);
    setErrorConsulta('');
    setMensajeBaja('');
    try {
      await onDesactivar(tipo, confirmacion.id);
      focoPendiente.current = true;
      setConfirmacion(null);
      setMensajeBaja('Registro desactivado.');
    } catch (error) {
      setErrorConsulta(error.message);
    } finally {
      pendienteBaja.current = false;
      setEnviandoBaja(false);
      onActividad(tipo, false);
    }
  }

  return (
    <section className={`catalog-section ${tipo}`} aria-labelledby={`${tipo}-title`}>
      <div className="section-heading">
        <h2 id={`${tipo}-title`}>{titulo}</h2>
        <span className="count">{visibles.length} registros</span>
      </div>
      <FormularioCatalogo
        tipo={tipo} registro={edicion} categorias={categorias}
        bloqueado={bloqueado || consultando}
        soloLectura={Boolean(soloLectura)}
        onGuardar={(id, datos) => onGuardar(tipo, id, datos)}
        onCancelar={() => setEdicion(null)}
        onActividad={(valor) => onActividad(tipo, valor)}
      />
      {/* El filtro y los avisos de las acciones de fila quedan junto al listado que afectan. */}
      <div className="list-toolbar">
        <h3>{listado}</h3>
        <div className="list-filter">
          <label htmlFor={`${tipo}-estado`}>Estado de {titulo.toLowerCase()}</label>
          <select id={`${tipo}-estado`} ref={filtro} value={estado} disabled={bloqueado || consultando}
            onChange={(evento) => setEstado(evento.target.value)}>
            <option value="activos">Activos</option><option value="inactivos">Inactivos</option><option value="todos">Todos</option>
          </select>
        </div>
      </div>
      {errorConsulta && <p className="notice error" role="alert">{errorConsulta}</p>}
      {mensajeBaja && <p className="notice success" role="status">{mensajeBaja}</p>}
      {confirmacion && (
        <div className="notice" role="group" aria-label={`Confirmar desactivación de ${singular} ${confirmacion.codigo}`}>
          <p>¿Desactivar {singular} {confirmacion.codigo} · {confirmacion.nombre}? Se conservan sus datos. No hay reactivación.</p>
          {enviandoBaja && <p role="status">Desactivando registro…</p>}
          <div className="actions">
            <button type="button" disabled={bloqueado || enviandoBaja} onClick={confirmarBaja}>Confirmar desactivación</button>
            <button type="button" className="secondary" autoFocus disabled={bloqueado || enviandoBaja}
              onClick={() => { setConfirmacion(null); filtro.current?.focus(); }}>Cancelar baja</button>
          </div>
        </div>
      )}
      {consultando && <p role="status">Consultando {singular}…</p>}
      {!visibles.length ? (
        <p className="empty">
          {estadoConsulta === 'cargando' ? `Cargando ${tipo}…`
            : estadoConsulta === 'error' ? 'No se pudieron cargar los registros.'
              : `No hay ${titulo.toLowerCase()} en este filtro.`}
        </p>
      ) : (
        <div className="table-scroll" role="region" aria-label={`Listado de ${tipo}`} tabIndex="0">
          <table>
            <caption className="sr-only">{titulo} del catálogo</caption>
            <thead>
              <tr>
                <th scope="col">ID</th><th scope="col">Código</th><th scope="col">Nombre</th>
                {esProducto && <><th scope="col">Categoría</th><th scope="col" className="num">Precio ARS</th></>}
                {esUbicacion && <th scope="col">Tipo</th>}
                <th scope="col">Estado</th>
                <th scope="col">Acción</th>
              </tr>
            </thead>
            <tbody>
              {visibles.map((item) => (
                <tr key={item.id}>
                  <td>{item.id}</td><td>{item.codigo}</td><td>{item.nombre}</td>
                  {esProducto && <><td>{item.categoria.nombre}</td><td className="price">{item.precio}</td></>}
                  {esUbicacion && <td>{item.tipo === 'CD' ? <strong>Centro de Distribución (CD)</strong> : 'Local'}</td>}
                  <td>{item.activo ? 'Activo' : <strong>Inactivo</strong>}</td>
                  <td>
                    <button
                      className="secondary compact" type="button"
                      disabled={bloqueado || consultando}
                      onClick={() => editar(item.id)}
                      aria-label={`${item.activo ? 'Consultar y editar' : 'Consultar'} ${singular} ${item.codigo}`}
                    >{item.activo ? 'Consultar y editar' : 'Consultar'}</button>
                    {item.activo && (item.tipo === 'CD'
                      ? <p className="detail">La baja del CD requiere una política de reemplazo aprobada.</p>
                      : <button className="secondary compact" type="button" disabled={bloqueado || consultando}
                        aria-label={`Desactivar ${singular} ${item.codigo}`}
                        onClick={() => { setConfirmacion(item); setMensajeBaja(''); setErrorConsulta(''); }}>Desactivar</button>)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
