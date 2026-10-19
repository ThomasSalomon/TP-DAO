import { useEffect, useState } from 'react';
import { consultarSalud, HEALTH_PATH } from './api';

export default function EstadoConexion() {
  const [intento, setIntento] = useState(0);
  const [conexion, setConexion] = useState({ estado: 'cargando' });

  useEffect(() => {
    const controller = new AbortController();
    setConexion({ estado: 'cargando' });
    consultarSalud(controller.signal)
      .then((respuesta) => {
        if (!controller.signal.aborted) setConexion({ estado: 'conectada', respuesta });
      })
      .catch((error) => {
        if (!controller.signal.aborted) setConexion({ estado: 'error', detalle: error.message });
      });
    return () => controller.abort();
  }, [intento]);

  return (
    <details className="technical panel">
      <summary>Estado técnico de conexión</summary>
      <div role="status" aria-live="polite">
        {conexion.estado === 'cargando' && <p>Consultando la API…</p>}
        {conexion.estado === 'conectada' && <p className="success">Conectada · La API está disponible.</p>}
        {conexion.estado === 'error' && <p className="error">{conexion.detalle}</p>}
      </div>
      {conexion.respuesta && <><p>GET {HEALTH_PATH}</p><pre>{JSON.stringify(conexion.respuesta, null, 2)}</pre></>}
      <button
        type="button" className="secondary" disabled={conexion.estado === 'cargando'}
        onClick={() => setIntento((valor) => valor + 1)}
      >Volver a comprobar conexión</button>
    </details>
  );
}
