import { useEffect, useRef, useState } from 'react';
import { categoriasAPI, productosAPI } from './api';
import FormularioCatalogo from './FormularioCatalogo';

export default function SeccionCatalogo({
  tipo, registros, categorias, bloqueado, estadoConsulta, onGuardar, onActividad,
}) {
  const esProducto = tipo === 'productos';
  const singular = esProducto ? 'producto' : 'categoría';
  const [edicion, setEdicion] = useState(null);
  const [consultando, setConsultando] = useState(false);
  const [errorConsulta, setErrorConsulta] = useState('');
  const consulta = useRef(null);

  useEffect(() => () => consulta.current?.abort(), []);

  async function editar(id) {
    const controller = new AbortController();
    consulta.current = controller;
    setConsultando(true);
    setErrorConsulta('');
    try {
      const api = esProducto ? productosAPI : categoriasAPI;
      const registro = await api.obtener(id, controller.signal);
      if (!controller.signal.aborted) setEdicion(registro);
    } catch (error) {
      if (!controller.signal.aborted) setErrorConsulta(error.message);
    } finally {
      if (!controller.signal.aborted) setConsultando(false);
    }
  }

  return (
    <section className="catalog-section" aria-labelledby={`${tipo}-title`}>
      <div className="section-heading">
        <h2 id={`${tipo}-title`}>{esProducto ? 'Productos' : 'Categorías'}</h2>
        <span className="count">{registros.length} registros</span>
      </div>
      {errorConsulta && <p className="notice error" role="alert">{errorConsulta}</p>}
      {consultando && <p role="status">Consultando {singular}…</p>}
      <FormularioCatalogo
        tipo={tipo} registro={edicion} categorias={categorias}
        bloqueado={bloqueado || consultando}
        onGuardar={(id, datos) => onGuardar(tipo, id, datos)}
        onCancelar={() => setEdicion(null)}
        onActividad={(valor) => onActividad(tipo, valor)}
      />
      <h3>{esProducto ? 'Productos registrados' : 'Categorías registradas'}</h3>
      {!registros.length ? (
        <p className="empty">
          {estadoConsulta === 'cargando' ? `Cargando ${tipo}…`
            : estadoConsulta === 'error' ? 'No se pudieron cargar los registros.'
              : `Todavía no hay ${esProducto ? 'productos registrados' : 'categorías registradas'}.`}
        </p>
      ) : (
        <div className="table-scroll" role="region" aria-label={`Listado de ${tipo}`} tabIndex="0">
          <table>
            <caption className="sr-only">{esProducto ? 'Productos' : 'Categorías'} del catálogo</caption>
            <thead>
              <tr>
                <th scope="col">ID</th><th scope="col">Código</th><th scope="col">Nombre</th>
                {esProducto && <><th scope="col">Categoría</th><th scope="col">Precio ARS</th></>}
                <th scope="col">Acción</th>
              </tr>
            </thead>
            <tbody>
              {registros.map((item) => (
                <tr key={item.id}>
                  <td>{item.id}</td><td>{item.codigo}</td><td>{item.nombre}</td>
                  {esProducto && <><td>{item.categoria.nombre}</td><td className="price">{item.precio}</td></>}
                  <td>
                    <button
                      className="secondary compact" type="button"
                      disabled={bloqueado || consultando}
                      onClick={() => editar(item.id)}
                      aria-label={`Consultar y editar ${singular} ${item.codigo}`}
                    >Consultar y editar</button>
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
