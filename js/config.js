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

// ⚠ DEMOSTRACIÓN: horario de atención ficticio. Lo usan el formulario
// de reservas (horas disponibles) y la sección de contacto (horario).
export const BOOKING_HOURS = {
  days: '',          // Ej.: 'Lunes a sábado'. Vacío = "Días por confirmar"
  open: '10:00',     // Apertura / primera hora que se puede solicitar
  close: '20:00',    // Cierre (la última reserva es close - slotMinutes)
  slotMinutes: 30,   // Intervalo entre horarios
};

/**
 * Datos de contacto y ubicación.
 * Regla: un campo vacío ('') significa "sin dato real todavía".
 *   - Se muestra como "por confirmar".
 *   - Su botón (llamar, correo, Instagram, mapa) NO se muestra.
 * El número de WhatsApp y el horario no se repiten aquí: se toman
 * de BUSINESS.whatsappNumber y BOOKING_HOURS.
 */
export const CONTACT = {
  isDemo: true,        // Muestra el aviso "Datos ilustrativos". Poner en false con datos reales.

  address: '',         // Ej.: 'Av. Ejemplo 123, local 4'
  city: '',            // Ej.: 'Santiago'
  country: '',         // Ej.: 'Chile'

  phone: '',           // Para llamadas: código de país + número, solo dígitos (ej. 56222222222)
  email: '',           // Ej.: 'contacto@dominio.cl'
  instagram: '',       // URL completa, ej.: 'https://www.instagram.com/usuario'

  // Mapa: con una dirección real basta. mapsUrl es opcional (enlace exacto
  // de Google Maps al local). showMapEmbed muestra el mapa dentro de la página.
  mapsUrl: '',
  showMapEmbed: true,
};
