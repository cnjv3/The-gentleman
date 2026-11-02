/**
 * config.js — Datos editables del negocio.
 * Para adaptar la web a un cliente real, se edita solo este archivo.
 */

export const BUSINESS = {
  name: 'THE GENTLEMAN',

  // ⚠ DEMOSTRACIÓN: número ficticio, no pertenece a ningún negocio.
  // Reemplazar por el número oficial: código de país + número,
  // solo dígitos (ej. Chile: 569XXXXXXXX).
  whatsappNumber: '56900000000',
};

// ⚠ DEMOSTRACIÓN: horario de atención ficticio. Solo define qué horas
// aparecen en el formulario; no indica disponibilidad real.
export const BOOKING_HOURS = {
  open: '10:00',     // Primera hora que se puede solicitar
  close: '20:00',    // Cierre (la última opción es close - slotMinutes)
  slotMinutes: 30,   // Intervalo entre horarios
};
