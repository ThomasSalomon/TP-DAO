import { useEffect, useState } from 'react';
import { categoriasAPI, productosAPI } from './api';
import EstadoConexion from './EstadoConexion';
import SeccionCatalogo from './SeccionCatalogo';

export default function App() {
  const [datos, setDatos] = useState({ categorias: [], productos: [] });
  const [revision, setRevision] = useState(0);
  const [carga, setCarga] = useState({ estado: 'cargando' });
  const [ocupados, setOcupados] = useState({ categorias: false, productos: false });
  const bloqueado = carga.estado === 'cargando' || ocupados.categorias || ocupados.productos;

  useEffect(() => {
    const controller = new AbortController();
    setCarga({ estado: 'cargando' });
    Promise.all([categoriasAPI.listar(controller.signal), productosAPI.listar(controller.signal)])
      .then(([categorias, productos]) => {
        if (!controller.signal.aborted) {
          setDatos({ categorias, productos });
          setCarga({ estado: 'lista' });
        }
      })
      .catch((error) => {
        if (!controller.signal.aborted) setCarga({ estado: 'error', mensaje: error.message });
      });
    return () => controller.abort();
  }, [revision]);

  async function guardar(tipo, id, entrada) {
    const api = tipo === 'productos' ? productosAPI : categoriasAPI;
    const resultado = id ? await api.modificar(id, entrada) : await api.crear(entrada);
    setDatos((actual) => {
      const existe = actual[tipo].some((item) => item.id === resultado.id);
      const registros = existe
        ? actual[tipo].map((item) => item.id === resultado.id ? resultado : item)
        : [...actual[tipo], resultado];
      return { ...actual, [tipo]: registros };
    });
    // La reconsulta obtiene las referencias actuales; su fallo no desconfirma el guardado.
    setRevision((valor) => valor + 1);
    return resultado;
  }

  return (
    <main className="app">
      <header className="page-header">
        <p className="eyebrow">DAO 2026 · F-01.2</p>
        <h1>Catálogo de productos</h1>
        <p>Administrá categorías, productos y precios vigentes.</p>
      </header>
      <p className="memory-note">Datos temporales: reiniciar el backend vacía el catálogo.</p>
      <div className="catalog-toolbar">
        <p role="status" aria-live="polite">
          {carga.estado === 'cargando' ? 'Cargando catálogo…' : 'Catálogo en memoria'}
        </p>
        <button className="secondary" type="button" disabled={bloqueado} onClick={() => setRevision((valor) => valor + 1)}>
          Actualizar listados
        </button>
      </div>
      {carga.estado === 'error' && (
        <div className="notice error" role="alert">
          <p>La última consulta del catálogo falló.</p>
          <p>{carga.mensaje}</p>
          <p>Los borradores se conservan. Actualizá los listados para volver a consultar.</p>
        </div>
      )}
      <div className="catalog-grid">
        {['categorias', 'productos'].map((tipo) => (
          <SeccionCatalogo
            key={tipo} tipo={tipo} registros={datos[tipo]} categorias={datos.categorias}
            bloqueado={bloqueado} estadoConsulta={carga.estado} onGuardar={guardar}
            onActividad={(recurso, valor) => setOcupados((actual) => ({ ...actual, [recurso]: valor }))}
          />
        ))}
      </div>
      <EstadoConexion />
    </main>
  );
}

