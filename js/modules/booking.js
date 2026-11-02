/**
 * booking.js — Reservas por WhatsApp.
 * Arma los enlaces de WhatsApp con un mensaje preparado.
 * (El formulario de reservas se agregará en su propia etapa.)
 */

import { BUSINESS } from '../config.js';

/** Crea un enlace de WhatsApp con el mensaje codificado para URL. */
export function buildWhatsAppUrl(message) {
  return `https://wa.me/${BUSINESS.whatsappNumber}?text=${encodeURIComponent(message)}`;
}

/**
 * Botones "Reservar ahora" de los servicios.
 * Cada enlace indica su servicio con data-service="Nombre".
 * Sin JavaScript, el enlace mantiene su destino original (#reservas).
 */
export function initServiceBooking() {
  document.querySelectorAll('a[data-service]').forEach((link) => {
    const service = link.dataset.service;
    const message = `Hola, me gustaría reservar el servicio de ${service} en ${BUSINESS.name}.`;
    link.href = buildWhatsAppUrl(message);
    link.target = '_blank';
    link.rel = 'noopener';
  });
}
