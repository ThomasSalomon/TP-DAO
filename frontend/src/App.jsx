import { useEffect, useRef, useState } from 'react';
import { catalogoAPI } from './api';
import SeccionCatalogo from './SeccionCatalogo';
import SeccionCompras from './SeccionCompras';
import SeccionDevoluciones from './SeccionDevoluciones';
import SeccionLogistica from './SeccionLogistica';
import SeccionMinimos from './SeccionMinimos';
import SeccionStock from './SeccionStock';
import SeccionVentas from './SeccionVentas';

// Cada vista tiene su ruta en el hash (#/productos) para poder recargarla y usar Atrás del navegador.
const GRUPOS = [
  { id: 'catalogo', titulo: 'Catálogo', vistas: [
    { id: 'categorias', titulo: 'Categorías' },
    { id: 'productos', titulo: 'Productos' },
    { id: 'proveedores', titulo: 'Proveedores' },
    { id: 'ubicaciones', titulo: 'Ubicaciones' },
    { id: 'minimos', titulo: 'Mínimos por local' },
  ] },
  { id: 'operaciones', titulo: 'Operaciones', vistas: [
    { id: 'compras', titulo: 'Compras al CD' },
    { id: 'logistica', titulo: 'Reposición y logística' },
    { id: 'ventas', titulo: 'Ventas y caja' },
    { id: 'devoluciones', titulo: 'Devoluciones' },
  ] },
  { id: 'consultas', titulo: 'Consultas', vistas: [
    { id: 'stock', titulo: 'Stock por ubicación' },
  ] },
];
const VISTAS = GRUPOS.flatMap((grupo) => grupo.vistas);

function vistaDelHash() {
  const id = window.location.hash.replace(/^#\/?/, '');
  return VISTAS.some((vista) => vista.id === id) ? id : VISTAS[0].id;
}

export default function App() {
  const [activa, setActiva] = useState(vistaDelHash);
  // En pantallas angostas las secciones se despliegan con un botón de menú.
  const [menuAbierto, setMenuAbierto] = useState(false);
  const navegado = useRef(false);
  const [datos, setDatos] = useState({ categorias: [], productos: [], proveedores: [], ubicaciones: [] });
  const [revision, setRevision] = useState(0);
  const [revisionStock, setRevisionStock] = useState(0);
  const [carga, setCarga] = useState({ estado: 'cargando' });
  const [ocupados, setOcupados] = useState({
    categorias: false, productos: false, proveedores: false, ubicaciones: false, minimos: false, compras: false, logistica: false, ventas: false,
    devoluciones: false,
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

  useEffect(() => {
    function cambiarVista() {
      navegado.current = true;
      setActiva(vistaDelHash());
      setMenuAbierto(false);
    }
    window.addEventListener('hashchange', cambiarVista);
    return () => window.removeEventListener('hashchange', cambiarVista);
  }, []);

  // Al cambiar de vista el foco pasa a su contenido; en la carga inicial no se mueve.
  useEffect(() => {
    const titulo = VISTAS.find((vista) => vista.id === activa).titulo;
    document.title = `${titulo} · DAO`;
    if (!navegado.current) return;
    const contenedor = document.getElementById(`vista-${activa}`);
    contenedor?.focus({ preventScroll: true });
    const { top } = contenedor?.getBoundingClientRect() ?? { top: 0 };
    if (top < 0 || top > window.innerHeight * 0.6) contenedor?.scrollIntoView({ block: 'start' });
  }, [activa]);

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

  function seccionCatalogo(tipo) {
    return (
      <SeccionCatalogo
        tipo={tipo} registros={datos[tipo]}
        categorias={datos.categorias.filter((item) => item.activo)}
        bloqueado={bloqueado} estadoConsulta={carga.estado} onGuardar={guardar} onDesactivar={desactivar}
        onActividad={(recurso, valor) => setOcupados((actual) => ({ ...actual, [recurso]: valor }))}
      />
    );
  }

  const contenido = {
    categorias: seccionCatalogo('categorias'),
    productos: seccionCatalogo('productos'),
    proveedores: seccionCatalogo('proveedores'),
    ubicaciones: seccionCatalogo('ubicaciones'),
    minimos: (
      <SeccionMinimos
        productos={datos.productos} ubicaciones={datos.ubicaciones}
        bloqueado={bloqueado} estadoCatalogo={carga.estado}
        onActividad={(valor) => setOcupados((actual) => ({ ...actual, minimos: valor }))}
      />
    ),
    compras: (
      <SeccionCompras
        productos={datos.productos} proveedores={datos.proveedores} ubicaciones={datos.ubicaciones}
        bloqueado={bloqueado} estadoCatalogo={carga.estado}
        onActividad={(valor) => setOcupados((actual) => ({ ...actual, compras: valor }))}
        onRegistrada={() => setRevisionStock((valor) => valor + 1)}
      />
    ),
    logistica: (
      <SeccionLogistica
        productos={datos.productos} ubicaciones={datos.ubicaciones}
        bloqueado={bloqueado} estadoCatalogo={carga.estado}
        onActividad={(valor) => setOcupados((actual) => ({ ...actual, logistica: valor }))}
        onCambio={() => setRevisionStock((valor) => valor + 1)}
      />
    ),
    ventas: (
      <SeccionVentas
        productos={datos.productos} ubicaciones={datos.ubicaciones}
        bloqueado={bloqueado} estadoCatalogo={carga.estado} revisionStock={revisionStock}
        onActividad={(valor) => setOcupados((actual) => ({ ...actual, ventas: valor }))}
        onCambio={() => setRevisionStock((valor) => valor + 1)}
      />
    ),
    devoluciones: (
      <SeccionDevoluciones
        ubicaciones={datos.ubicaciones}
        bloqueado={bloqueado} estadoCatalogo={carga.estado} revisionStock={revisionStock}
        onActividad={(valor) => setOcupados((actual) => ({ ...actual, devoluciones: valor }))}
        onCambio={() => setRevisionStock((valor) => valor + 1)}
      />
    ),
    stock: (
      <SeccionStock
        ubicaciones={datos.ubicaciones} productos={datos.productos}
        bloqueado={bloqueado} estadoCatalogo={carga.estado} revisionStock={revisionStock}
      />
    ),
  };

  const grupoActivo = GRUPOS.find((grupo) => grupo.vistas.some((vista) => vista.id === activa));
  const vistaActiva = VISTAS.find((vista) => vista.id === activa);

  return (
    <div className="app">
      <nav className="sidebar" aria-label="Secciones">
        <div className="brand">
          <svg className="brand-mark" viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">
            <path d="M3.5 7.5 12 3l8.5 4.5v9L12 21l-8.5-4.5z" />
            <path d="M3.5 7.5 12 12l8.5-4.5M12 12v9" />
          </svg>
          <div>
            <p className="brand-name">TP-DAO</p>
            <p className="brand-scope">Locales y CD</p>
          </div>
          <button className="secondary compact menu-toggle" type="button" aria-expanded={menuAbierto}
            aria-controls="nav-secciones" onClick={() => setMenuAbierto((valor) => !valor)}>
            {menuAbierto ? 'Cerrar menú' : 'Secciones'}
          </button>
        </div>
        <div className={`nav-groups${menuAbierto ? ' abierto' : ''}`} id="nav-secciones">
          {GRUPOS.map((grupo) => (
            <div className="nav-group" key={grupo.id}>
              <p className="nav-title" id={`nav-${grupo.id}`}>{grupo.titulo}</p>
              <ul aria-labelledby={`nav-${grupo.id}`}>
                {grupo.vistas.map((vista) => (
                  <li key={vista.id}>
                    <a href={`#/${vista.id}`} aria-current={vista.id === activa ? 'page' : undefined}
                      onClick={() => setMenuAbierto(false)}>
                      {vista.titulo}
                      {ocupados[vista.id] && <span className="nav-busy"> · guardando…</span>}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </nav>
      <header className="topbar">
        <div className="breadcrumb">
          <span>{grupoActivo.titulo}</span>
          <span aria-hidden="true">/</span>
          <h1>{vistaActiva.titulo}</h1>
        </div>
        <div className="catalog-toolbar">
          <p role="status" aria-live="polite">
            {carga.estado === 'cargando' ? 'Cargando catálogo…' : 'Catálogo cargado'}
          </p>
          <button className="secondary" type="button" disabled={bloqueado} onClick={() => setRevision((valor) => valor + 1)}>
            Actualizar listados
          </button>
        </div>
      </header>
      <main className="workspace">
        {carga.estado === 'error' && (
          <div className="notice error" role="alert">
            <p>La última consulta del catálogo falló.</p>
            <p>{carga.mensaje}</p>
            <p>Los borradores se conservan. Actualizá los listados para volver a consultar.</p>
          </div>
        )}
        {/* Las vistas ocultas siguen montadas: cambiar de sección no descarta borradores ni operaciones en curso. */}
        {VISTAS.map((vista) => (
          <div key={vista.id} id={`vista-${vista.id}`} className="vista" tabIndex="-1" hidden={vista.id !== activa}>
            {contenido[vista.id]}
          </div>
        ))}
        <p className="memory-note">Los datos se guardan en SQLite y se conservan al reiniciar el backend. Los borradores de los formularios no se guardan hasta confirmarlos y se conservan al cambiar de sección.</p>
      </main>
    </div>
  );
}

