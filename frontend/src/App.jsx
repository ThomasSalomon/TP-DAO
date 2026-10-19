import { useEffect, useState } from 'react';
import { consultarSalud, HEALTH_PATH } from './api';

export default function App() {
  const [intento, setIntento] = useState(0);
  const [conexion, setConexion] = useState({ estado: 'cargando' });

  useEffect(() => {
    const controller = new AbortController();
    let vigente = true;
    let agotado = false;
    setConexion({ estado: 'cargando' });

    const timeout = setTimeout(() => {
      agotado = true;
      controller.abort();
    }, 10000);

    consultarSalud(controller.signal)
      .then((respuesta) => {
        if (vigente) setConexion({ estado: 'conectada', respuesta });
      })
      .catch((error) => {
        if (vigente) {
          setConexion({
            estado: 'error',
            detalle: agotado ? 'La consulta superó los 10 segundos.' : error.message,
          });
        }
      })
      .finally(() => clearTimeout(timeout));

    return () => {
      vigente = false;
      clearTimeout(timeout);
      controller.abort();
    };
  }, [intento]);

  const cargando = conexion.estado === 'cargando';

  return (
    <main className="panel">
      <p className="eyebrow">DAO 2026 · Incremento técnico</p>
      <h1>Conexión con la API</h1>
      <p>Comprobación de comunicación entre React y Flask.</p>

      <section className="connection" aria-labelledby="connection-title">
        <h2 id="connection-title">Estado de conexión</h2>
        <div role="status" aria-live="polite" aria-atomic="true">
          {cargando && <p className="status">Consultando la API…</p>}
          {conexion.estado === 'conectada' && (
            <p className="status success">Conectada · La API está disponible.</p>
          )}
          {conexion.estado === 'error' && (
            <>
              <p className="status error">Sin conexión con la API.</p>
              <p>Comprobá que Flask esté ejecutándose y volvé a intentar.</p>
              <p className="detail">{conexion.detalle}</p>
            </>
          )}
        </div>

        {conexion.estado === 'conectada' && (
          <div>
            <p className="detail">Respuesta de GET {HEALTH_PATH}</p>
            <pre>{JSON.stringify(conexion.respuesta, null, 2)}</pre>
          </div>
        )}

        <button disabled={cargando} onClick={() => setIntento((actual) => actual + 1)}>
          {cargando ? 'Consultando…' : 'Volver a comprobar'}
        </button>
      </section>

      <p className="footnote">Prueba técnica de conexión. Aún no hay funciones de negocio.</p>
    </main>
  );
}

