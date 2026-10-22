import { createPortal } from 'react-dom';
import { formatearInstante } from './api';
import { nombreUbicacion } from './etiquetas';

function Detalle({ comprobante, nivel, id }) {
  const Titulo = nivel;
  return (
    <>
      <Titulo id={id}>Comprobante interno {comprobante.numero}</Titulo>
      <p className="detail">Documento no fiscal · Local {nombreUbicacion(comprobante.local)} · {formatearInstante(comprobante.instante)}</p>
      <table>
        <caption className="sr-only">Líneas del comprobante {comprobante.numero}</caption>
        <thead><tr><th scope="col">Producto</th><th scope="col">Cantidad</th><th scope="col">Precio unitario</th><th scope="col">Subtotal</th></tr></thead>
        <tbody>{comprobante.lineas.map((linea) => (
          <tr key={linea.linea}>
            <td>{linea.producto.codigo} · {linea.producto.nombre}</td>
            <td className="price">{linea.cantidad} u.</td>
            <td className="price">$ {linea.precio_unitario}</td>
            <td className="price">$ {linea.subtotal}</td>
          </tr>
        ))}</tbody>
        <tfoot><tr><th scope="row" colSpan="3">Total ({comprobante.moneda})</th><td className="price total">$ {comprobante.total}</td></tr></tfoot>
      </table>
      <p className="receipt-payments">Cobros: {comprobante.cobros.map((cobro) => `${cobro.medio.nombre} $ ${cobro.importe}`).join(' · ')}</p>
    </>
  );
}

// Reimprimir sólo consulta el comprobante: no registra otra venta.
export default function ComprobanteVenta({ comprobante, onCerrar }) {
  return (
    <section className="receipt" aria-labelledby="comprobante-title">
      <Detalle comprobante={comprobante} nivel="h4" id="comprobante-title" />
      <div className="actions">
        <button type="button" onClick={() => window.print()}>Imprimir comprobante</button>
        <button className="secondary" type="button" onClick={onCerrar}>Cerrar comprobante</button>
      </div>
      {/* Copia fuera de la aplicación: al imprimir se muestra sólo el comprobante. */}
      {createPortal(
        <div className="receipt-print" aria-hidden="true"><Detalle comprobante={comprobante} nivel="h1" /></div>,
        document.body,
      )}
    </section>
  );
}
