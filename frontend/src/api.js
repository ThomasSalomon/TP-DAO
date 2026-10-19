export const HEALTH_PATH = '/api/health';

export async function consultarSalud(signal) {
  const response = await fetch(HEALTH_PATH, {
    signal,
    headers: { Accept: 'application/json' },
    cache: 'no-store',
  });

  if (!response.ok) {
    throw new Error(`La API respondió con HTTP ${response.status}.`);
  }

  const data = await response.json();
  if (data?.status !== 'ok') {
    throw new Error('La API devolvió una respuesta de salud inesperada.');
  }

  return data;
}

