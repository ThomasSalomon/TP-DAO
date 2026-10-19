export const HEALTH_PATH = '/api/health';

export class ErrorAPI extends Error {
  constructor(message, estado = null, campos = {}) {
    super(message);
    this.estado = estado;
    this.campos = campos;
  }
}

async function solicitar(ruta, { signal, ...opciones } = {}) {
  const controller = new AbortController();
  const cancelar = () => controller.abort();
  let agotado = false;
  if (signal?.aborted) controller.abort();
  else signal?.addEventListener('abort', cancelar, { once: true });
  const timeout = setTimeout(() => {
    agotado = true;
    controller.abort();
  }, 10000);

  try {
    const respuesta = await fetch(ruta, {
      ...opciones, signal: controller.signal, cache: 'no-store',
      headers: {
        Accept: 'application/json',
        ...(opciones.body ? { 'Content-Type': 'application/json' } : {}),
      },
    });
    const datos = await respuesta.json().catch(() => null);
    if (!respuesta.ok) {
      const mensaje = respuesta.status >= 500
        ? `La API no está disponible o no pudo completar la solicitud (HTTP ${respuesta.status}).`
        : datos?.error?.message || `La solicitud falló (HTTP ${respuesta.status}).`;
      throw new ErrorAPI(mensaje, respuesta.status, datos?.error?.fields || {});
    }
    if (datos === null) throw new ErrorAPI('La API devolvió una respuesta JSON inesperada.');
    return datos;
  } catch (error) {
    if (signal?.aborted || error instanceof ErrorAPI) throw error;
    const mensaje = agotado
      ? 'La consulta superó los 10 segundos.'
      : 'No se pudo conectar con la API. Comprobá que Flask esté ejecutándose.';
    const aviso = opciones.method
      ? ' No se pudo confirmar el guardado; actualizá el listado antes de reenviar.' : '';
    throw new ErrorAPI(mensaje + aviso);
  } finally {
    clearTimeout(timeout);
    signal?.removeEventListener('abort', cancelar);
  }
}

function recurso(nombre) {
  const ruta = `/api/${nombre}`;
  return {
    listar: async (signal) => (await solicitar(ruta, { signal }))[nombre],
    obtener: (id, signal) => solicitar(`${ruta}/${id}`, { signal }),
    crear: (datos) => solicitar(ruta, { method: 'POST', body: JSON.stringify(datos) }),
    modificar: (id, datos) => solicitar(`${ruta}/${id}`, {
      method: 'PUT', body: JSON.stringify(datos),
    }),
  };
}

export const categoriasAPI = recurso('categorias');
export const productosAPI = recurso('productos');
export const proveedoresAPI = recurso('proveedores');
export const ubicacionesAPI = recurso('ubicaciones');
export const catalogoAPI = {
  categorias: categoriasAPI, productos: productosAPI,
  proveedores: proveedoresAPI, ubicaciones: ubicacionesAPI,
};

export const minimosAPI = {
  listar: (localId, signal) => solicitar(`/api/ubicaciones/${localId}/minimos`, { signal }),
  establecer: (localId, productoId, minimo) => solicitar(
    `/api/ubicaciones/${localId}/minimos/${productoId}`,
    { method: 'PUT', body: JSON.stringify({ minimo }) },
  ),
};

export async function consultarSalud(signal) {
  const datos = await solicitar(HEALTH_PATH, { signal });
  if (datos.status !== 'ok') throw new ErrorAPI('La respuesta de salud no es la esperada.');
  return datos;
}

