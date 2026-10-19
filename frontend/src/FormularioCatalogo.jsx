import { useEffect, useRef, useState } from 'react';

function valoresIniciales(registro) {
  return {
    codigo: registro?.codigo || '', nombre: registro?.nombre || '',
    categoria_id: registro?.categoria ? String(registro.categoria.id) : '',
    precio: registro?.precio || '',
  };
}

export default function FormularioCatalogo({
  tipo, registro, categorias, bloqueado, onGuardar, onCancelar, onActividad,
}) {
  const esProducto = tipo === 'productos';
  const singular = esProducto ? 'producto' : 'categoría';
  const prefijo = esProducto ? 'producto' : 'categoria';
  const [datos, setDatos] = useState(() => valoresIniciales(registro));
  const [error, setError] = useState(null);
  const [exito, setExito] = useState('');
  const [enviando, setEnviando] = useState(false);
  const pendiente = useRef(false);

  useEffect(() => {
    setDatos(valoresIniciales(registro));
    setError(null);
    setExito('');
  }, [registro]);

  function cambiar(evento) {
    setDatos((actual) => ({ ...actual, [evento.target.name]: evento.target.value }));
    setError(null);
    setExito('');
  }

  async function guardar(evento) {
    evento.preventDefault();
    if (pendiente.current) return;
    pendiente.current = true;
    setEnviando(true);
    onActividad(true);
    setError(null);
    setExito('');
    const entrada = { codigo: datos.codigo, nombre: datos.nombre };
    if (esProducto) {
      entrada.categoria_id = Number(datos.categoria_id);
      entrada.precio = datos.precio;
    }
    try {
      const resultado = await onGuardar(registro?.id, entrada);
      setDatos(valoresIniciales(registro ? resultado : null));
      const accion = esProducto
        ? (registro ? 'actualizado' : 'registrado') : (registro ? 'actualizada' : 'registrada');
      setExito(`${esProducto ? 'Producto' : 'Categoría'} ${accion}.`);
    } catch (fallo) {
      setError(fallo);
    } finally {
      pendiente.current = false;
      setEnviando(false);
      onActividad(false);
    }
  }

  function atributos(campo) {
    const tieneError = Boolean(error?.campos?.[campo]);
    return {
      id: `${prefijo}-${campo}`, name: campo, value: datos[campo], onChange: cambiar,
      required: true, 'aria-invalid': tieneError || undefined,
      'aria-describedby': [
        campo === 'precio' ? 'producto-precio-ayuda' : '',
        tieneError ? `${prefijo}-${campo}-error` : '',
        error && !tieneError ? `${prefijo}-error` : '',
      ].filter(Boolean).join(' ') || undefined,
    };
  }

  function errorCampo(campo) {
    return error?.campos?.[campo] && (
      <p className="field-error" id={`${prefijo}-${campo}-error`}>{error.campos[campo]}</p>
    );
  }

  return (
    <form onSubmit={guardar} aria-labelledby={`${prefijo}-form-title`}>
      <h3 id={`${prefijo}-form-title`}>
        {registro ? `Editar ${singular} · ID ${registro.id}` : `Registrar ${singular}`}
      </h3>
      {error && <p className="notice error" role="alert" id={`${prefijo}-error`}>{error.message}</p>}
      {exito && <p className="notice success" role="status">{exito}</p>}
      {enviando && <p role="status">Guardando {singular}…</p>}
      <fieldset disabled={bloqueado || enviando}>
        <legend className="sr-only">Datos de {singular}</legend>
        <div className="form-fields">
          <div>
            <label htmlFor={`${prefijo}-codigo`}>Código de {singular}</label>
            <input {...atributos('codigo')} type="text" autoComplete="off" />
            {errorCampo('codigo')}
          </div>
          <div>
            <label htmlFor={`${prefijo}-nombre`}>Nombre de {singular}</label>
            <input {...atributos('nombre')} type="text" autoComplete="off" />
            {errorCampo('nombre')}
          </div>
          {esProducto && (
            <>
              <div>
                <label htmlFor="producto-categoria_id">Categoría del producto</label>
                <select {...atributos('categoria_id')}>
                  <option value="">Elegí una categoría</option>
                  {categorias.map((item) => (
                    <option key={item.id} value={item.id}>{item.codigo} · {item.nombre}</option>
                  ))}
                </select>
                {errorCampo('categoria_id')}
                {!categorias.length && <p className="detail">Registrá una categoría para crear productos.</p>}
              </div>
              <div>
                <label htmlFor="producto-precio">Precio ARS</label>
                <input {...atributos('precio')} type="text" inputMode="decimal" />
                <p id="producto-precio-ayuda" className="detail">Usá punto decimal, por ejemplo 125.50.</p>
                {errorCampo('precio')}
              </div>
            </>
          )}
        </div>
        <div className="actions">
          <button type="submit" disabled={esProducto && !categorias.length}>
            {enviando ? 'Guardando…' : registro ? `Guardar ${singular}` : `Registrar ${singular}`}
          </button>
          {registro && <button type="button" className="secondary" onClick={onCancelar}>Cancelar edición</button>}
        </div>
      </fieldset>
    </form>
  );
}
