import { useState } from 'react';
import { ErrorAPI, formatearInstante, logisticaAPI } from './api';
import { ESTADOS_BULTO, ESTADOS_REMITO, nombreUbicacion } from './etiquetas';

function borradorVacio(bulto) {
  return { precinto: '', leido: '', intacto: '', localId: String(bulto.destino.id), anulando: false };
}

const RECORRIDO = ['PREPARADO', 'PRECINTADO', 'EN_TRANSITO', 'RECIBIDO', 'VERIFICADO'];

// Recorrido del bulto según su historial; uno rechazado o anulado termina en ese estado.
function RecorridoBulto({ bulto }) {
  const alcanzados = bulto.eventos.map((evento) => evento.estado_nuevo);
  const cerrado = bulto.estado === 'RECHAZADO' || bulto.estado === 'ANULADO';
  const pasos = cerrado ? alcanzados : RECORRIDO;
  return (
    <ol className={`parcel-track${cerrado ? ' cerrado' : ''}`} aria-label={`Recorrido de ${bulto.codigo}`}>
      {pasos.map((estado) => (
        <li key={estado} aria-current={estado === bulto.estado ? 'step' : undefined}
          className={estado === bulto.estado ? 'actual' : alcanzados.includes(estado) ? 'hecho' : ''}>
          {ESTADOS_BULTO[estado]}
        </li>
      ))}
    </ol>
  );
}

export default function PanelBultos({ datos, ubicaciones, bloqueado, ejecutar }) {
  const abiertas = datos.ordenes.filter((orden) => orden.estado === 'ABIERTA');
  const locales = ubicaciones.filter((item) => item.tipo === 'LOCAL');
  const [ordenId, setOrdenId] = useState('');
  const [cantidades, setCantidades] = useState({});
  const [preparacion, setPreparacion] = useState({ error: null, exito: '' });
  const [borradores, setBorradores] = useState({});
  const [avisos, setAvisos] = useState({});
  const orden = abiertas.find((item) => String(item.id) === ordenId);

  async function preparar(evento) {
    evento.preventDefault();
    const lineas = [];
    for (const linea of orden.lineas) {
      const texto = (cantidades[linea.producto.id] ?? '').trim();
      if (!texto) continue;
      if (!/^[0-9]+$/.test(texto) || !Number.isSafeInteger(Number(texto))) {
        setPreparacion({ error: new ErrorAPI(`Revisá la cantidad de ${linea.producto.codigo}: debe ser un entero.`), exito: '' });
        return;
      }
      if (Number(texto) > 0) lineas.push({ producto_id: linea.producto.id, cantidad: Number(texto) });
    }
    if (!lineas.length) {
      setPreparacion({ error: new ErrorAPI('Indicá al menos una cantidad mayor que cero.'), exito: '' });
      return;
    }
    const resultado = await ejecutar(() => logisticaAPI.prepararBulto(orden.id, lineas));
    if (resultado.ok) {
      setCantidades({});
      setPreparacion({ error: null, exito: `Bulto ${resultado.resultado.codigo} preparado; su contenido quedó reservado en el CD.` });
    } else {
      setPreparacion({ error: resultado.error, exito: '' });
    }
  }

  function borrador(bulto) {
    return borradores[bulto.id] ?? borradorVacio(bulto);
  }

  function editar(bulto, campos) {
    setBorradores((actual) => ({ ...actual, [bulto.id]: { ...borrador(bulto), ...campos } }));
    setAvisos((actual) => ({ ...actual, [bulto.id]: null }));
  }

  // exito puede depender de la respuesta de Python, por ejemplo una recepción rechazada.
  async function operar(bulto, operacion, exito) {
    const resultado = await ejecutar(operacion);
    const texto = resultado.ok && (typeof exito === 'function' ? exito(resultado.resultado) : exito);
    setAvisos((actual) => ({
      ...actual, [bulto.id]: resultado.ok ? { exito: texto } : resultado.error && { error: resultado.error },
    }));
    if (resultado.ok) setBorradores((actual) => ({ ...actual, [bulto.id]: undefined }));
  }

  function acciones(bulto) {
    const datosBorrador = borrador(bulto);
    const prefijo = `bulto-${bulto.id}`;
    if (bulto.estado === 'PREPARADO') {
      return (
        <>
          <form className="inline-form" onSubmit={(evento) => {
            evento.preventDefault();
            operar(bulto, () => logisticaAPI.operarBulto(bulto.id, 'precintar', { precinto: datosBorrador.precinto }),
              'Precintado; se emitió el remito.');
          }}>
            <label htmlFor={`${prefijo}-precinto`}>Número de precinto<span className="sr-only"> de {bulto.codigo}</span></label>
            <input id={`${prefijo}-precinto`} type="text" required value={datosBorrador.precinto}
              onChange={(evento) => editar(bulto, { precinto: evento.target.value })} />
            <button type="submit">Precintar</button>
          </form>
          {!datosBorrador.anulando ? (
            <button className="secondary compact" type="button" onClick={() => editar(bulto, { anulando: true })}>
              Anular preparación
            </button>
          ) : (
            <div className="confirm" role="group" aria-label={`Confirmar anulación de ${bulto.codigo}`}>
              <p>Se libera la reserva en el CD y el bulto queda anulado. No se puede deshacer.</p>
              <button className="secondary compact" type="button" onClick={() => editar(bulto, { anulando: false })}>Cancelar</button>
              <button className="compact" type="button"
                onClick={() => operar(bulto, () => logisticaAPI.operarBulto(bulto.id, 'anular'), 'Preparación anulada; reserva liberada.')}>
                Confirmar anulación
              </button>
            </div>
          )}
        </>
      );
    }
    if (bulto.estado === 'PRECINTADO') {
      return (
        <button type="button" onClick={() => operar(bulto, () => logisticaAPI.operarBulto(bulto.id, 'despachar'),
          `Despachado hacia ${bulto.destino.codigo}.`)}>
          Despachar desde el CD
        </button>
      );
    }
    if (bulto.estado === 'EN_TRANSITO') {
      return (
        <form className="reception-form" onSubmit={(evento) => {
          evento.preventDefault();
          operar(bulto, () => logisticaAPI.operarBulto(bulto.id, 'recibir', {
            local_id: Number(datosBorrador.localId), precinto_leido: datosBorrador.leido,
            precinto_intacto: datosBorrador.intacto === 'si',
          }), (respuesta) => respuesta.estado === 'RECHAZADO'
            ? 'Recepción registrada: el bulto quedó rechazado y su remito también.'
            : 'Recepción registrada con precinto conforme. Falta verificar el contenedor.');
        }}>
          <div>
            <label htmlFor={`${prefijo}-local`}>Local que recibe</label>
            <select id={`${prefijo}-local`} value={datosBorrador.localId}
              onChange={(evento) => editar(bulto, { localId: evento.target.value })}>
              {locales.map((item) => <option key={item.id} value={item.id}>{nombreUbicacion(item)}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor={`${prefijo}-leido`}>Precinto leído</label>
            <input id={`${prefijo}-leido`} type="text" required value={datosBorrador.leido}
              onChange={(evento) => editar(bulto, { leido: evento.target.value })} />
          </div>
          <fieldset className="radio-group">
            <legend>Estado del precinto</legend>
            {[['si', 'Intacto'], ['no', 'Roto']].map(([valor, texto]) => (
              <label key={valor} className="check-option">
                <input type="radio" name={`${prefijo}-intacto`} value={valor} checked={datosBorrador.intacto === valor}
                  onChange={() => editar(bulto, { intacto: valor })} />
                {texto}
              </label>
            ))}
          </fieldset>
          <button type="submit" disabled={!datosBorrador.intacto}>Registrar recepción</button>
        </form>
      );
    }
    if (bulto.estado === 'RECIBIDO') {
      return (
        <button type="button" onClick={() => operar(bulto, () => logisticaAPI.operarBulto(bulto.id, 'verificar'),
          'Contenedor verificado. Falta verificar el remito para habilitar el stock.')}>
          Verificar contenedor
        </button>
      );
    }
    if (bulto.estado === 'VERIFICADO' && bulto.remito.estado === 'EMITIDO') {
      return (
        <button type="button" onClick={() => operar(bulto, () => logisticaAPI.verificarRemito(bulto.remito.id),
          `Remito verificado: el contenido está disponible en ${bulto.destino.codigo}.`)}>
          Verificar remito {bulto.remito.numero}
        </button>
      );
    }
    if (bulto.estado === 'VERIFICADO') return <p className="detail">Bulto y remito verificados: stock disponible en {bulto.destino.codigo}.</p>;
    if (bulto.estado === 'RECHAZADO') {
      return <p className="detail">{bulto.eventos.at(-1).motivo} El contenido queda en custodia del local, sin habilitar venta.</p>;
    }
    return <p className="detail">Preparación anulada; la reserva volvió a estar disponible en el CD.</p>;
  }

  return (
    <div className="subsection">
      <h3>Bultos y remitos</h3>
      <form onSubmit={preparar} aria-labelledby="bulto-form-title">
        <h4 id="bulto-form-title">Preparar bulto de una orden</h4>
        {preparacion.error && <p className="notice error" role="alert">{preparacion.error.message}</p>}
        {preparacion.exito && <p className="notice success" role="status">{preparacion.exito}</p>}
        <fieldset disabled={bloqueado}>
          <legend className="sr-only">Orden y cantidades del bulto</legend>
          <label htmlFor="bulto-orden">Orden abierta</label>
          <select id="bulto-orden" required value={ordenId}
            onChange={(evento) => { setOrdenId(evento.target.value); setCantidades({}); setPreparacion({ error: null, exito: '' }); }}>
            <option value="">Elegí una orden</option>
            {abiertas.map((item) => <option key={item.id} value={item.id}>Orden {item.id} → {nombreUbicacion(item.destino)}</option>)}
          </select>
          {!abiertas.length && <p className="empty">No hay órdenes con cantidades pendientes.</p>}
          {orden && (
            <div className="line-fields compact-lines">
              {orden.lineas.filter((linea) => linea.pendiente > 0).map((linea) => (
                <div key={linea.producto.id}>
                  <label htmlFor={`bulto-cantidad-${linea.producto.id}`}>
                    {linea.producto.codigo} · {linea.producto.nombre} (pendiente {linea.pendiente})
                  </label>
                  <input id={`bulto-cantidad-${linea.producto.id}`} type="text" inputMode="numeric"
                    value={cantidades[linea.producto.id] ?? ''} placeholder="0"
                    onChange={(evento) => { setCantidades({ ...cantidades, [linea.producto.id]: evento.target.value }); setPreparacion({ error: null, exito: '' }); }} />
                </div>
              ))}
            </div>
          )}
          <p className="detail">Se reserva en el CD lo que se prepara; no puede superar lo pendiente ni lo disponible.</p>
          <div className="actions"><button type="submit" disabled={!orden}>Preparar bulto</button></div>
        </fieldset>
      </form>
      <h4>Bultos</h4>
      {!datos.bultos.length ? <p className="empty">Todavía no hay bultos.</p> : (
        <ul className="parcel-list">
          {[...datos.bultos].reverse().map((bulto) => (
            <li key={bulto.id} className={`parcel estado-${bulto.estado.toLowerCase()}`} aria-labelledby={`bulto-${bulto.id}-titulo`}>
              <div className="parcel-heading">
                <h5 id={`bulto-${bulto.id}-titulo`}>{bulto.codigo}</h5>
                <span className="badge">{ESTADOS_BULTO[bulto.estado]}</span>
              </div>
              <RecorridoBulto bulto={bulto} />
              <p className="detail">
                Orden {bulto.orden_id} · {bulto.origen.codigo} → {nombreUbicacion(bulto.destino)}
                {bulto.precinto && ` · Precinto ${bulto.precinto}`}
                {bulto.remito && ` · Remito ${bulto.remito.numero} (${ESTADOS_REMITO[bulto.remito.estado].toLowerCase()})`}
              </p>
              <ul className="plain-list">{bulto.lineas.map((linea) => (
                <li key={linea.producto.id}>{linea.producto.codigo} · {linea.producto.nombre}: {linea.cantidad} u.{linea.costo_referencia ? ` (costo ref. $ ${linea.costo_referencia})` : ' (sin costo registrado)'}</li>
              ))}</ul>
              {avisos[bulto.id]?.error && <p className="notice error" role="alert">{avisos[bulto.id].error.message}</p>}
              {avisos[bulto.id]?.exito && <p className="notice success" role="status">{avisos[bulto.id].exito}</p>}
              <fieldset className="parcel-actions" disabled={bloqueado}>
                <legend className="sr-only">Acciones de {bulto.codigo}</legend>
                {acciones(bulto)}
              </fieldset>
              <details>
                <summary>Historial de estados ({bulto.eventos.length})</summary>
                <ol className="history">{bulto.eventos.map((evento) => (
                  <li key={evento.secuencia}>
                    <strong>{ESTADOS_BULTO[evento.estado_nuevo]}</strong> · {formatearInstante(evento.instante)} · {evento.motivo}
                  </li>
                ))}</ol>
              </details>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
