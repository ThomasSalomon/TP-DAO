import { useEffect, useRef, useState } from 'react';

function valoresIniciales(registro) {
  return {
    codigo: registro?.codigo || '', nombre: registro?.nombre || '',
    categoria_id: registro?.categoria ? String(registro.categoria.id) : '',
    precio: registro?.precio || '',
    tipo: registro?.tipo || '',
  };
}

export default function FormularioCatalogo({
  tipo, registro, categorias, bloqueado, soloLectura = false, onGuardar, onCancelar, onActividad,
}) {
  const esProducto = tipo === 'productos';
  const esCategoria = tipo === 'categorias';
  const esUbicacion = tipo === 'ubicaciones';
  const singular = {
    categorias: 'categoría', productos: 'producto', proveedores: 'proveedor', ubicaciones: 'ubicación',
  }[tipo];
  const titulo = {
    categorias: 'Categoría', productos: 'Producto', proveedores: 'Proveedor', ubicaciones: 'Ubicación',
  }[tipo];
  const prefijo = esCategoria ? 'categoria' : esUbicacion ? 'ubicacion' : singular;
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
    if (pendiente.current || soloLectura || bloqueado) return;
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
    if (esUbicacion && !registro) entrada.tipo = datos.tipo;
    try {
      const resultado = await onGuardar(registro?.id, entrada);
      setDatos(valoresIniciales(registro ? resultado : null));
      const accion = esCategoria || esUbicacion
        ? (registro ? 'actualizada' : 'registrada') : (registro ? 'actualizado' : 'registrado');
      setExito(`${titulo} ${accion}.`);
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
        campo === 'codigo' ? `${prefijo}-codigo-ayuda` : '',
        esUbicacion && campo === 'tipo' ? 'ubicacion-tipo-ayuda' : '',
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
        {registro ? `${soloLectura ? 'Consultar' : 'Editar'} ${singular} · ID ${registro.id}` : `Registrar ${singular}`}
      </h3>
      {soloLectura && <p className="notice">Registro inactivo. Los campos se conservan y no pueden guardarse. Usá Consultar para recuperar los datos registrados.</p>}
      {error && <p className="notice error" role="alert" id={`${prefijo}-error`}>{error.message}</p>}
      {exito && <p className="notice success" role="status">{exito}</p>}
      {enviando && <p role="status">Guardando {singular}…</p>}
      <fieldset disabled={bloqueado || enviando || soloLectura}>
        <legend className="sr-only">Datos de {singular}</legend>
        <div className="form-fields">
          <div>
            <label htmlFor={`${prefijo}-codigo`}>Código de {singular}</label>
            <input {...atributos('codigo')} type="text" autoComplete="off" />
            <p id={`${prefijo}-codigo-ayuda`} className="detail">
              Si cambiás el código, el anterior queda reservado y no puede volver a usarse.
            </p>
            {errorCampo('codigo')}
          </div>
          <div>
            <label htmlFor={`${prefijo}-nombre`}>Nombre de {singular}</label>
            <input {...atributos('nombre')} type="text" autoComplete="off" />
            {errorCampo('nombre')}
          </div>
          {esUbicacion && (
            <div>
              {registro ? (
                <>
                  <p>Tipo de ubicación: <strong>
                    {registro.tipo === 'CD' ? 'Centro de Distribución (CD)' : 'Local o sucursal'}
                  </strong></p>
                  <p className="detail">El tipo no puede modificarse.</p>
                </>
              ) : (
                <>
                  <label htmlFor="ubicacion-tipo">Tipo de ubicación</label>
                  <select {...atributos('tipo')}>
                    <option value="">Elegí un tipo</option>
                    <option value="LOCAL">Local o sucursal</option>
                    <option value="CD">Centro de Distribución (CD)</option>
                  </select>
                  <p id="ubicacion-tipo-ayuda" className="detail">Sólo se permite un Centro de Distribución.</p>
                  {errorCampo('tipo')}
                </>
              )}
            </div>
          )}
          {esProducto && (
            <>
              <div>
                <label htmlFor="producto-categoria_id">Categoría del producto</label>
                <select {...atributos('categoria_id')}>
                  <option value="">Elegí una categoría</option>
                  {soloLectura && registro?.categoria && !categorias.some((item) => item.id === registro.categoria.id) && (
                    <option value={registro.categoria.id} disabled>{registro.categoria.codigo} · {registro.categoria.nombre} (inactiva)</option>
                  )}
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
      </fieldset>
      <div className="actions">
        {!soloLectura && <button type="submit" disabled={bloqueado || enviando || (esProducto && !categorias.length)}>
          {enviando ? 'Guardando…' : registro ? `Guardar ${singular}` : `Registrar ${singular}`}
        </button>}
        {registro && <button type="button" className="secondary" disabled={bloqueado || enviando} onClick={onCancelar}>{soloLectura ? 'Cerrar consulta' : 'Cancelar edición'}</button>}
      </div>
    </form>
  );
}
