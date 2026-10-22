import { useEffect, useState } from 'react';
import { catalogoAPI } from './api';
import EstadoConexion from './EstadoConexion';
import SeccionCatalogo from './SeccionCatalogo';
import SeccionCompras from './SeccionCompras';
import SeccionMinimos from './SeccionMinimos';
import SeccionStockCD from './SeccionStockCD';

export default function App() {
  const [datos, setDatos] = useState({ categorias: [], productos: [], proveedores: [], ubicaciones: [] });
  const [revision, setRevision] = useState(0);
  const [revisionStock, setRevisionStock] = useState(0);
  const [carga, setCarga] = useState({ estado: 'cargando' });
  const [ocupados, setOcupados] = useState({
    categorias: false, productos: false, proveedores: false, ubicaciones: false, minimos: false, compras: false,
  });
  const bloqueado = carga.estado === 'cargando' || Object.values(ocupados).some(Boolean);

  useEffect(() => {
    const controller = new AbortController();
    setCarga({ estado: 'cargando' });
    Promise.all([
      catalogoAPI.categorias.listar(controller.signal, 'todos'),
      catalogoAPI.productos.listar(controller.signal, 'todos'),
      catalogoAPI.proveedores.listar(controller.signal, 'todos'),
      catalogoAPI.ubicaciones.listar(controller.signal, 'todos'),
    ])
      .then(([categorias, productos, proveedores, ubicaciones]) => {
        if (!controller.signal.aborted) {
          setDatos({ categorias, productos, proveedores, ubicaciones });
          setCarga({ estado: 'lista' });
        }
      })
      .catch((error) => {
        if (!controller.signal.aborted) setCarga({ estado: 'error', mensaje: error.message });
      });
    return () => controller.abort();
  }, [revision]);

  async function guardar(tipo, id, entrada) {
    const api = catalogoAPI[tipo];
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

  async function desactivar(tipo, id) {
    const resultado = await catalogoAPI[tipo].desactivar(id);
    setDatos((actual) => ({
      ...actual, [tipo]: actual[tipo].map((item) => item.id === id ? resultado : item),
    }));
    setRevision((valor) => valor + 1);
    return resultado;
  }

  return (
    <main className="app">
      <header className="page-header">
        <p className="eyebrow">DAO 2026 · F-02.3</p>
        <h1>Catálogo, compras y stock del CD</h1>
        <p>Administrá el catálogo, registrá compras a proveedores y consultá el stock del Centro de Distribución.</p>
      </header>
      <p className="memory-note">Los datos se guardan en SQLite y se conservan al reiniciar el backend. Los borradores de los formularios no se guardan hasta confirmarlos.</p>
      <div className="catalog-toolbar">
        <p role="status" aria-live="polite">
          {carga.estado === 'cargando' ? 'Cargando catálogo…' : 'Catálogo cargado'}
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
        {['categorias', 'productos', 'proveedores', 'ubicaciones'].map((tipo) => (
          <SeccionCatalogo
            key={tipo} tipo={tipo} registros={datos[tipo]}
            categorias={datos.categorias.filter((item) => item.activo)}
            bloqueado={bloqueado} estadoConsulta={carga.estado} onGuardar={guardar} onDesactivar={desactivar}
            onActividad={(recurso, valor) => setOcupados((actual) => ({ ...actual, [recurso]: valor }))}
          />
        ))}
        <SeccionMinimos
          productos={datos.productos} ubicaciones={datos.ubicaciones}
          bloqueado={bloqueado} estadoCatalogo={carga.estado}
          onActividad={(valor) => setOcupados((actual) => ({ ...actual, minimos: valor }))}
        />
        <SeccionCompras
          productos={datos.productos} proveedores={datos.proveedores} ubicaciones={datos.ubicaciones}
          bloqueado={bloqueado} estadoCatalogo={carga.estado}
          onActividad={(valor) => setOcupados((actual) => ({ ...actual, compras: valor }))}
          onRegistrada={() => setRevisionStock((valor) => valor + 1)}
        />
        <SeccionStockCD
          ubicaciones={datos.ubicaciones} productos={datos.productos}
          bloqueado={bloqueado} estadoCatalogo={carga.estado} revisionStock={revisionStock}
        />
      </div>
      <EstadoConexion />
    </main>
  );
}

