import { useEffect, useRef, useState } from 'react';
import { logisticaAPI } from './api';
import PanelBultos from './PanelBultos';
import PanelReposicion from './PanelReposicion';

const VACIO = { necesidades: [], ordenes: [], bultos: [], remitos: [] };

export default function SeccionLogistica({ productos, ubicaciones, bloqueado, estadoCatalogo, onActividad, onCambio }) {
  const [datos, setDatos] = useState(VACIO);
  const [consulta, setConsulta] = useState({ estado: 'cargando' });
  const [revision, setRevision] = useState(0);
  const [ocupado, setOcupado] = useState(false);
  const pendiente = useRef(false);
  const centro = ubicaciones.find((item) => item.tipo === 'CD');

  useEffect(() => {
    const controller = new AbortController();
    setConsulta({ estado: 'cargando' });
    logisticaAPI.listar(controller.signal)
      .then((resultado) => {
        if (!controller.signal.aborted) {
          setDatos(resultado);
          setConsulta({ estado: 'lista' });
        }
      })
      .catch((fallo) => {
        if (!controller.signal.aborted) setConsulta({ estado: 'error', mensaje: fallo.message });
      });
    return () => controller.abort();
  }, [revision, productos, ubicaciones]);

  // Una operación a la vez: Python confirma y después se vuelven a consultar los documentos y el stock.
  async function ejecutar(operacion) {
    if (pendiente.current) return { ok: false };
    pendiente.current = true;
    setOcupado(true);
    onActividad(true);
    try {
      const resultado = await operacion();
      setRevision((valor) => valor + 1);
      onCambio();
      return { ok: true, resultado };
    } catch (error) {
      return { ok: false, error };
    } finally {
      pendiente.current = false;
      setOcupado(false);
      onActividad(false);
    }
  }

  const comun = { datos, productos, ubicaciones, bloqueado: bloqueado || ocupado, ejecutar };

  return (
    <section className="catalog-section logistica" aria-labelledby="logistica-title">
      <div className="section-heading">
        <h2 id="logistica-title">Reposición y logística CD → locales</h2>
        <button className="secondary" type="button" disabled={bloqueado || ocupado || consulta.estado === 'cargando'}
          onClick={() => setRevision((valor) => valor + 1)}>
          Actualizar logística
        </button>
      </div>
      <p className="detail">El stock llega como disponible al local sólo cuando el bulto y su remito están verificados. Un precinto roto o distinto rechaza el bulto en la recepción.</p>
      {estadoCatalogo === 'lista' && !centro && <p className="empty">Registrá el Centro de Distribución para operar la reposición.</p>}
      {consulta.estado === 'cargando' && <p role="status">Cargando reposición y bultos…</p>}
      {consulta.estado === 'error' && <p className="notice error" role="alert">{consulta.mensaje} Los borradores se conservan.</p>}
      {ocupado && <p role="status">Guardando operación…</p>}
      <PanelReposicion {...comun} />
      <PanelBultos {...comun} />
    </section>
  );
}
