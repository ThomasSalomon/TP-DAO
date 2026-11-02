import { useEffect, useRef, useState } from 'react';
import { formatearInstante, reportesAPI } from './api';
import { CONDICIONES, nombreUbicacion } from './etiquetas';

const REPORTES = [
  { id: 'ventas', titulo: 'R-01 · Ventas, cobros e ingresos netos', periodo: true,
    ayuda: 'Ventas, devoluciones y venta neta del período, y la caja agrupada por día, local o medio de pago.' },
  { id: 'productos', titulo: 'R-02 · Productos más vendidos y margen estimado', periodo: true,
    ayuda: 'Ranking por unidades netas (vendidas menos devueltas) con importe, costo y margen a valores históricos.' },
  { id: 'existencias', titulo: 'R-03 · Existencias, mínimos y faltantes', periodo: false,
    ayuda: 'Stock actual por condición frente al mínimo de cada producto. Es una foto del momento: no tiene período.' },
  { id: 'rechazos', titulo: 'R-04 · Rechazos logísticos', periodo: true,
    ayuda: 'Bultos rechazados por precinto en la fecha del rechazo, y bultos recibidos y rechazados por local.' },
];
const AGRUPACIONES = { dia: 'Día', local: 'Local', medio: 'Medio de pago' };

function fechaISO(fecha) {
  return `${fecha.getFullYear()}-${String(fecha.getMonth() + 1).padStart(2, '0')}-${String(fecha.getDate()).padStart(2, '0')}`;
}

// Suma días a una fecha AAAA-MM-DD sin depender de la zona del navegador.
function correrDias(texto, dias) {
  const [anio, mes, dia] = texto.split('-').map(Number);
  return new Date(Date.UTC(anio, mes - 1, dia + dias)).toISOString().slice(0, 10);
}

function fechaCorta(texto) {
  const [anio, mes, dia] = texto.split('-');
  return `${dia}/${mes}/${anio}`;
}

function filtrosIniciales() {
  const hoy = fechaISO(new Date());
  return {
    desde: `${hoy.slice(0, 8)}01`, hasta: hoy, localId: '', agrupacion: 'dia',
    ubicacionId: '', categoriaId: '', soloEnMinimo: false, productoId: '',
  };
}

// La pantalla pide el último día incluido; la API excluye el fin, así que se envía el día siguiente.
function parametros(tipo, filtros, ubicacionId) {
  const periodo = { desde: filtros.desde, hasta: filtros.hasta && correrDias(filtros.hasta, 1) };
  if (tipo === 'ventas') return { ...periodo, local_id: filtros.localId, agrupacion: filtros.agrupacion };
  if (tipo === 'productos') return { ...periodo, local_id: filtros.localId };
  if (tipo === 'existencias') {
    return { ubicacion_id: ubicacionId, categoria_id: filtros.categoriaId, solo_en_minimo: filtros.soloEnMinimo ? 'true' : '' };
  }
  return { ...periodo, local_id: filtros.localId, producto_id: filtros.productoId };
}

// Python informa los importes con signo; aquí sólo se agrega el símbolo y se marcan los negativos.
function Importe({ valor, faltante = 'Sin costo' }) {
  if (valor === null) return <span className="detail">{faltante}</span>;
  const negativo = valor.startsWith('-');
  return <span className={negativo ? 'negativo' : undefined}>{negativo ? `−$ ${valor.slice(1)}` : `$ ${valor}`}</span>;
}

function Campo({ id, etiqueta, error, children }) {
  return (
    <div>
      <label htmlFor={id}>{etiqueta}</label>
      {children}
      {error && <p className="field-error" id={`${id}-error`}>{error}</p>}
    </div>
  );
}

function descripcionPeriodo(periodo) {
  return `Del ${fechaCorta(periodo.desde)} al ${fechaCorta(correrDias(periodo.hasta, -1))}`;
}

function Tabla({ etiqueta, children }) {
  return (
    <div className="table-scroll" role="region" aria-label={etiqueta} tabIndex="0">
      <table>
        <caption className="sr-only">{etiqueta}</caption>
        {children}
      </table>
    </div>
  );
}

function ResultadoVentas({ datos }) {
  return (
    <>
      <dl className="report-summary">
        <div><dt>Ventas ({datos.ventas.cantidad})</dt><dd><Importe valor={datos.ventas.importe} /></dd></div>
        <div><dt>Devoluciones ({datos.devoluciones.cantidad})</dt><dd><Importe valor={datos.devoluciones.importe} /></dd></div>
        <div><dt>Venta neta</dt><dd><Importe valor={datos.venta_neta} /></dd></div>
      </dl>
      <h4>Caja por {AGRUPACIONES[datos.agrupacion].toLowerCase()}</h4>
      {!datos.grupos.length ? <p className="empty">Sin cobros ni reintegros en el período.</p> : (
        <Tabla etiqueta={`Cobros, reintegros e ingreso neto por ${AGRUPACIONES[datos.agrupacion].toLowerCase()}`}>
          <thead><tr>
            <th scope="col">{AGRUPACIONES[datos.agrupacion]}</th><th scope="col" className="num">Cobros</th>
            <th scope="col" className="num">Reintegros</th><th scope="col" className="num">Ingreso neto</th>
          </tr></thead>
          <tbody>{datos.grupos.map((grupo) => (
            <tr key={grupo.etiqueta}>
              <td>{grupo.etiqueta}</td>
              <td className="price"><Importe valor={grupo.cobros} /></td>
              <td className="price"><Importe valor={grupo.reintegros} /></td>
              <td className="price"><Importe valor={grupo.ingreso_neto} /></td>
            </tr>
          ))}</tbody>
          <tfoot><tr>
            <th scope="row">Total</th>
            <td className="price"><Importe valor={datos.cobros} /></td>
            <td className="price"><Importe valor={datos.reintegros} /></td>
            <td className="price"><Importe valor={datos.ingreso_neto} /></td>
          </tr></tfoot>
        </Tabla>
      )}
      <p className="detail">Cada venta se cobra completa y cada reintegro cubre su devolución, así que el ingreso neto total coincide con la venta neta. Las ventas no se reparten entre medios de pago: sólo se agrupan los cobros y los reintegros.</p>
    </>
  );
}

function ResultadoProductos({ datos }) {
  if (!datos.productos.length) return <p className="empty">No hubo ventas ni devoluciones en el período.</p>;
  return (
    <>
      {datos.productos_sin_costo.length > 0 && (
        <div className="notice" role="note">
          <p>Sin costo de referencia: {datos.productos_sin_costo.map((producto) => `${producto.codigo} · ${producto.nombre}`).join(', ')}. Su margen y el margen total no se informan; el costo faltante no se toma como cero.</p>
        </div>
      )}
      <Tabla etiqueta="Productos ordenados por unidades netas vendidas">
        <thead><tr>
          <th scope="col">Puesto</th><th scope="col">Producto</th>
          <th scope="col" className="num">Vendidas</th><th scope="col" className="num">Devueltas</th>
          <th scope="col" className="num">Netas</th><th scope="col" className="num">Importe neto</th>
          <th scope="col" className="num">Costo neto</th><th scope="col" className="num">Margen estimado</th>
        </tr></thead>
        <tbody>{datos.productos.map((fila) => (
          <tr key={fila.producto.id}>
            <td>{fila.posicion}</td>
            <td>{fila.producto.codigo} · {fila.producto.nombre}{!fila.producto.activo ? ' (inactivo)' : ''}</td>
            <td className="price">{fila.unidades_vendidas} u.</td>
            <td className="price">{fila.unidades_devueltas} u.</td>
            <td className="price">{fila.unidades_netas} u.</td>
            <td className="price"><Importe valor={fila.importe_neto} /></td>
            <td className="price"><Importe valor={fila.costo_neto} /></td>
            <td className="price"><Importe valor={fila.margen} /></td>
          </tr>
        ))}</tbody>
        <tfoot><tr>
          <th scope="row" colSpan="4">Total</th>
          <td className="price">{datos.unidades_netas} u.</td>
          <td className="price"><Importe valor={datos.importe_neto} /></td>
          <td />
          <td className="price"><Importe valor={datos.margen} faltante="No se informa" /></td>
        </tr></tfoot>
      </Tabla>
      <p className="detail">Margen estimado = importe neto − costo neto. El costo es el de referencia (última compra) guardado en cada venta; una devolución revierte el de su venta original. No es un costo por lote ni un resultado contable completo. Ante igual cantidad de unidades, el orden es el de alta de los productos.</p>
    </>
  );
}

function ResultadoExistencias({ datos }) {
  if (!datos.productos.length) {
    return <p className="empty">{datos.solo_en_minimo ? 'Ningún producto está en su mínimo.' : 'La ubicación no tiene stock ni mínimos configurados para estos filtros.'}</p>;
  }
  const columnas = Object.keys(CONDICIONES).filter((condicion) => condicion === 'DISPONIBLE' || datos.totales[condicion]);
  // Sin ningún mínimo configurado (por ejemplo, en el CD) el déficit no aplica, igual que en cada fila.
  const deficitTotal = datos.productos.every((fila) => fila.minimo === null) ? '—' : `${datos.deficit_total} u.`;
  return (
    <>
      <dl className="report-summary">
        <div><dt>Productos en mínimo</dt><dd>{datos.productos_en_minimo}</dd></div>
        <div><dt>Déficit total</dt><dd>{deficitTotal}</dd></div>
      </dl>
      <Tabla etiqueta={`Existencias y mínimos de ${datos.ubicacion.codigo}`}>
        <thead><tr>
          <th scope="col">Producto</th><th scope="col">Categoría</th>
          {columnas.map((condicion) => <th key={condicion} scope="col" className="num">{CONDICIONES[condicion]}</th>)}
          <th scope="col" className="num">Mínimo</th><th scope="col" className="num">Déficit</th><th scope="col">Alerta</th>
        </tr></thead>
        <tbody>{datos.productos.map((fila) => (
          <tr key={fila.producto.id}>
            <td>{fila.producto.codigo} · {fila.producto.nombre}{!fila.producto.activo ? ' (inactivo)' : ''}</td>
            <td>{fila.categoria.nombre}</td>
            {columnas.map((condicion) => <td key={condicion} className="price">{fila.saldos[condicion]} u.</td>)}
            <td className="price">{fila.minimo === null ? '—' : `${fila.minimo} u.`}</td>
            <td className="price">{fila.deficit === null ? '—' : `${fila.deficit} u.`}</td>
            <td>{fila.en_minimo && <span className="badge badge-alerta">En mínimo</span>}</td>
          </tr>
        ))}</tbody>
        <tfoot><tr>
          <th scope="row" colSpan="2">Total</th>
          {columnas.map((condicion) => <td key={condicion} className="price">{datos.totales[condicion]} u.</td>)}
          <td />
          <td className="price">{deficitTotal}</td>
          <td />
        </tr></tfoot>
      </Tabla>
      <p className="detail">Déficit = mínimo − disponible, nunca menos de cero. La alerta aparece cuando el disponible es menor o igual que el mínimo. Sólo el disponible se puede vender; sin mínimo configurado no hay déficit ni alerta, y el CD no tiene mínimos.</p>
    </>
  );
}

function ResultadoRechazos({ datos }) {
  return (
    <>
      <dl className="report-summary">
        <div><dt>Bultos recibidos</dt><dd>{datos.bultos_recibidos}</dd></div>
        <div><dt>Bultos rechazados</dt><dd>{datos.bultos_rechazados}</dd></div>
        <div><dt>Unidades afectadas</dt><dd>{datos.unidades} u.</dd></div>
        <div><dt>Valor bloqueado</dt><dd><Importe valor={datos.valor_bloqueado} faltante="Incompleto" /></dd></div>
      </dl>
      <h4>Por local destino</h4>
      {!datos.locales.length ? <p className="empty">Ningún local recibió bultos en el período.</p> : (
        <Tabla etiqueta="Bultos recibidos y rechazados por local">
          <thead><tr>
            <th scope="col">Local</th><th scope="col" className="num">Recibidos</th><th scope="col" className="num">Rechazados</th>
            <th scope="col" className="num">Unidades</th><th scope="col" className="num">Valor bloqueado</th>
          </tr></thead>
          <tbody>{datos.locales.map((item) => (
            <tr key={item.destino.id}>
              <td>{nombreUbicacion(item.destino)}</td>
              <td className="price">{item.bultos_recibidos}</td>
              <td className="price">{item.bultos_rechazados}</td>
              <td className="price">{item.unidades} u.</td>
              <td className="price"><Importe valor={item.valor_bloqueado} faltante="Incompleto" /></td>
            </tr>
          ))}</tbody>
        </Tabla>
      )}
      <h4>Bultos rechazados</h4>
      {!datos.rechazos.length ? <p className="empty">Sin rechazos en el período.</p> : (
        <Tabla etiqueta="Bultos rechazados, del más antiguo al más reciente">
          <thead><tr>
            <th scope="col">Bulto</th><th scope="col">Remito</th><th scope="col">Destino</th><th scope="col">Fecha y hora</th>
            <th scope="col">Motivo</th><th scope="col">Contenido</th><th scope="col" className="num">Valor bloqueado</th>
          </tr></thead>
          <tbody>{datos.rechazos.map((rechazo) => (
            <tr key={rechazo.bulto_id}>
              <td>{rechazo.bulto_codigo}</td>
              <td>{rechazo.remito}</td>
              <td>{rechazo.destino.codigo}</td>
              <td>{formatearInstante(rechazo.instante)}</td>
              <td>{rechazo.motivo}</td>
              <td>
                <ul className="plain-list">{rechazo.lineas.map((linea) => (
                  <li key={linea.producto.id}>{linea.cantidad} u. de {linea.producto.codigo} · {linea.producto.nombre}</li>
                ))}</ul>
              </td>
              <td className="price"><Importe valor={rechazo.valor_bloqueado} faltante="Incompleto" /></td>
            </tr>
          ))}</tbody>
        </Tabla>
      )}
      <p className="detail">El valor bloqueado usa el costo de referencia guardado al preparar cada bulto; una compra posterior no lo cambia. Es mercadería en custodia del local, no una merma ni una pérdida definitiva. «Incompleto» indica que a alguna línea le falta el costo.</p>
    </>
  );
}

const RESULTADOS = {
  ventas: ResultadoVentas, productos: ResultadoProductos, existencias: ResultadoExistencias, rechazos: ResultadoRechazos,
};

function alcance(tipo, datos) {
  if (tipo === 'existencias') {
    return [nombreUbicacion(datos.ubicacion), datos.categoria ? `categoría ${datos.categoria.nombre}` : 'todas las categorías',
      ...(datos.solo_en_minimo ? ['sólo productos en mínimo'] : [])].join(' · ');
  }
  const partes = [descripcionPeriodo(datos.periodo), datos.local ? nombreUbicacion(datos.local) : 'todos los locales'];
  if (tipo === 'ventas') partes.push(`por ${AGRUPACIONES[datos.agrupacion].toLowerCase()}`);
  if (tipo === 'rechazos' && datos.producto) partes.push(`${datos.producto.codigo} · ${datos.producto.nombre}`);
  return partes.join(' · ');
}

export default function SeccionReportes({ ubicaciones, productos, categorias, estadoCatalogo }) {
  const [tipo, setTipo] = useState('ventas');
  const [filtros, setFiltros] = useState(filtrosIniciales);
  // El último resultado de cada reporte se conserva al cambiar de reporte.
  const [resultados, setResultados] = useState({});
  const controladores = useRef({});
  const locales = ubicaciones.filter((item) => item.tipo === 'LOCAL');
  const centro = ubicaciones.find((item) => item.tipo === 'CD');
  const ubicacionId = filtros.ubicacionId || (centro ? String(centro.id) : '');
  const reporte = REPORTES.find((item) => item.id === tipo);
  const resultado = resultados[tipo] ?? { estado: 'inicial' };
  const errores = resultado.estado === 'error' ? resultado.campos : {};
  const Resultado = RESULTADOS[tipo];

  useEffect(() => () => Object.values(controladores.current).forEach((controller) => controller.abort()), []);

  function cambiar(campo, valor) {
    setFiltros((actual) => ({ ...actual, [campo]: valor }));
  }

  function actualizar(consultado, valor) {
    setResultados((actual) => ({ ...actual, [consultado]: valor }));
  }

  async function generar(evento) {
    evento.preventDefault();
    const consultado = tipo;
    controladores.current[consultado]?.abort();
    const controller = new AbortController();
    controladores.current[consultado] = controller;
    actualizar(consultado, { estado: 'cargando' });
    try {
      const datos = await reportesAPI.generar(consultado, parametros(consultado, filtros, ubicacionId), controller.signal);
      if (!controller.signal.aborted) actualizar(consultado, { estado: 'lista', datos });
    } catch (fallo) {
      if (!controller.signal.aborted) actualizar(consultado, { estado: 'error', mensaje: fallo.message, campos: fallo.campos ?? {} });
    }
  }

  function atributosError(id, campo) {
    return { 'aria-invalid': Boolean(errores[campo]), 'aria-describedby': errores[campo] ? `${id}-error` : undefined };
  }

  return (
    <section className="catalog-section report" aria-labelledby="reportes-title">
      <div className="section-heading">
        <h2 id="reportes-title">Reportes</h2>
      </div>
      <p className="detail">Calculados en Python con las operaciones confirmadas; consultarlos no modifica stock, caja ni documentos. Generá el reporte otra vez para ver operaciones nuevas.</p>
      <form onSubmit={generar}>
        <div className="form-fields">
          <Campo id="reporte-tipo" etiqueta="Reporte">
            <select id="reporte-tipo" value={tipo} onChange={(evento) => setTipo(evento.target.value)}>
              {REPORTES.map((item) => <option key={item.id} value={item.id}>{item.titulo}</option>)}
            </select>
          </Campo>
          {tipo === 'ventas' && (
            <Campo id="reporte-agrupacion" etiqueta="Agrupar la caja por" error={errores.agrupacion}>
              <select id="reporte-agrupacion" value={filtros.agrupacion} {...atributosError('reporte-agrupacion', 'agrupacion')}
                onChange={(evento) => cambiar('agrupacion', evento.target.value)}>
                {Object.entries(AGRUPACIONES).map(([id, titulo]) => <option key={id} value={id}>{titulo}</option>)}
              </select>
            </Campo>
          )}
          {reporte.periodo && (
            <>
              <Campo id="reporte-desde" etiqueta="Desde" error={errores.desde}>
                <input id="reporte-desde" type="date" required value={filtros.desde} {...atributosError('reporte-desde', 'desde')}
                  onChange={(evento) => cambiar('desde', evento.target.value)} />
              </Campo>
              <Campo id="reporte-hasta" etiqueta="Hasta (inclusive)" error={errores.hasta}>
                <input id="reporte-hasta" type="date" required value={filtros.hasta} {...atributosError('reporte-hasta', 'hasta')}
                  onChange={(evento) => cambiar('hasta', evento.target.value)} />
              </Campo>
              <Campo id="reporte-local" etiqueta="Local" error={errores.local_id}>
                <select id="reporte-local" value={filtros.localId} {...atributosError('reporte-local', 'local_id')}
                  onChange={(evento) => cambiar('localId', evento.target.value)}>
                  <option value="">Todos los locales</option>
                  {locales.map((item) => (
                    <option key={item.id} value={item.id}>{nombreUbicacion(item)}{!item.activo ? ' (inactivo)' : ''}</option>
                  ))}
                </select>
              </Campo>
            </>
          )}
          {tipo === 'rechazos' && (
            <Campo id="reporte-producto" etiqueta="Producto" error={errores.producto_id}>
              <select id="reporte-producto" value={filtros.productoId} {...atributosError('reporte-producto', 'producto_id')}
                onChange={(evento) => cambiar('productoId', evento.target.value)}>
                <option value="">Todos los productos</option>
                {productos.map((item) => (
                  <option key={item.id} value={item.id}>{item.codigo} · {item.nombre}{!item.activo ? ' (inactivo)' : ''}</option>
                ))}
              </select>
            </Campo>
          )}
          {tipo === 'existencias' && (
            <>
              <Campo id="reporte-ubicacion" etiqueta="Ubicación" error={errores.ubicacion_id}>
                <select id="reporte-ubicacion" value={ubicacionId} disabled={!ubicaciones.length}
                  {...atributosError('reporte-ubicacion', 'ubicacion_id')} onChange={(evento) => cambiar('ubicacionId', evento.target.value)}>
                  {ubicaciones.map((item) => (
                    <option key={item.id} value={item.id}>{nombreUbicacion(item)}{item.tipo === 'CD' ? ' (CD)' : ''}{!item.activo ? ' (inactivo)' : ''}</option>
                  ))}
                </select>
              </Campo>
              <Campo id="reporte-categoria" etiqueta="Categoría" error={errores.categoria_id}>
                <select id="reporte-categoria" value={filtros.categoriaId} {...atributosError('reporte-categoria', 'categoria_id')}
                  onChange={(evento) => cambiar('categoriaId', evento.target.value)}>
                  <option value="">Todas las categorías</option>
                  {categorias.map((item) => (
                    <option key={item.id} value={item.id}>{item.nombre}{!item.activo ? ' (inactiva)' : ''}</option>
                  ))}
                </select>
              </Campo>
              <div className="report-check">
                <label className="check-option" htmlFor="reporte-minimo">
                  <input id="reporte-minimo" type="checkbox" checked={filtros.soloEnMinimo}
                    onChange={(evento) => cambiar('soloEnMinimo', evento.target.checked)} />
                  Sólo productos en su mínimo
                </label>
              </div>
            </>
          )}
        </div>
        <p className="detail report-help">{reporte.ayuda}</p>
        {estadoCatalogo === 'lista' && tipo === 'existencias' && !ubicaciones.length && (
          <p className="empty">Registrá una ubicación para consultar sus existencias.</p>
        )}
        <div className="actions">
          <button type="submit" disabled={resultado.estado === 'cargando' || (tipo === 'existencias' && !ubicacionId)}>
            Generar reporte
          </button>
        </div>
      </form>
      <div aria-live="polite">
        {resultado.estado === 'inicial' && <p className="empty">Elegí los filtros y generá el reporte.</p>}
        {resultado.estado === 'cargando' && <p role="status">Generando reporte…</p>}
        {resultado.estado === 'error' && <div className="notice error" role="alert"><p>{resultado.mensaje}</p></div>}
        {resultado.estado === 'lista' && (
          <>
            <h3>{reporte.titulo}</h3>
            <p className="detail">{alcance(tipo, resultado.datos)}</p>
            <Resultado datos={resultado.datos} />
          </>
        )}
      </div>
    </section>
  );
}
