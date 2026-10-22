// Importes ARS en centavos con BigInt: sólo para mostrar estimaciones del borrador.
// El total, los precios y la validación de los cobros los confirma Python.

const IMPORTE = /^[0-9]+(\.[0-9]{1,2})?$/;

// "1500", "1500.5" o "1500.50" → centavos; null si el texto no es un importe.
export function aCentavos(texto) {
  const limpio = texto.trim();
  if (!IMPORTE.test(limpio)) return null;
  const [enteros, decimales = ''] = limpio.split('.');
  return BigInt(enteros) * 100n + BigInt(decimales.padEnd(2, '0'));
}

export function aTexto(centavos) {
  const signo = centavos < 0n ? '-' : '';
  const absoluto = centavos < 0n ? -centavos : centavos;
  return `${signo}${absoluto / 100n}.${String(absoluto % 100n).padStart(2, '0')}`;
}
