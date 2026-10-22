// Textos de presentación para los valores estables que devuelve Python.

export const CONDICIONES = {
  DISPONIBLE: 'Disponible', RESERVADO: 'Reservado', EN_TRANSITO: 'En tránsito',
  PENDIENTE: 'Pendiente de verificación', RECHAZADO: 'Rechazado', BLOQUEADO: 'Bloqueado',
};

export const ESTADOS_BULTO = {
  PREPARADO: 'Preparado', PRECINTADO: 'Precintado', EN_TRANSITO: 'En tránsito', RECIBIDO: 'Recibido',
  VERIFICADO: 'Verificado', RECHAZADO: 'Rechazado', ANULADO: 'Anulado',
};

export const ESTADOS_REMITO = { EMITIDO: 'Emitido', VERIFICADO: 'Verificado', RECHAZADO: 'Rechazado' };

export const TIPOS_CAJA = { INGRESO: 'Ingreso', EGRESO: 'Egreso' };

export function nombreCondicion(condicion) {
  return condicion === null ? 'Fuera de la ubicación' : CONDICIONES[condicion] ?? condicion;
}

export function nombreUbicacion(ubicacion) {
  return `${ubicacion.codigo} · ${ubicacion.nombre}`;
}
