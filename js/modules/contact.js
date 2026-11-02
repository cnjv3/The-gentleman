/**
 * contact.js — Sección Ubicación y contacto.
 *
 * Dibuja la información desde config.js (fuente única) y muestra cada
 * botón solo si su dato existe. Así nunca hay botones que no hagan nada
 * ni datos inventados presentados como reales.
 */

import { BUSINESS, BOOKING_HOURS, CONTACT } from '../config.js?v=9.0';
import { buildWhatsAppUrl } from './booking.js?v=9.0';

const PENDING = 'Por confirmar';

/** "56900000000" → "+56 9 0000 0000" (formato chileno de celular; otros, agrupado simple). */
export function formatPhone(digits) {
  const d = String(digits).replace(/\D/g, '');
  if (/^569\d{8}$/.test(d)) return `+56 9 ${d.slice(3, 7)} ${d.slice(7)}`;
  if (/^56\d{9}$/.test(d)) return `+56 ${d.slice(2, 3)} ${d.slice(3, 7)} ${d.slice(7)}`;
  return d ? `+${d}` : '';
}

/** Dirección completa a partir de los campos que existan. */
export function fullAddress(c = CONTACT) {
  return [c.address, c.city, c.country].map((s) => s.trim()).filter(Boolean).join(', ');
}

/** Enlace a Google Maps: el configurado o, si hay dirección, uno de búsqueda. */
export function mapsLink(c = CONTACT) {
  if (c.mapsUrl.trim()) return c.mapsUrl.trim();
  if (!c.address.trim()) return '';
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(fullAddress(c))}`;
}

/** Solo acepta enlaces https (evita javascript: u otros esquemas en la configuración). */
const safeUrl = (url) => (/^https:\/\//i.test(url.trim()) ? url.trim() : '');

/** Datos listos para mostrar: texto, si es real y su acción (si existe). */
export function getContactView(c = CONTACT, hours = BOOKING_HOURS, business = BUSINESS) {
  const address = fullAddress(c);
  const map = safeUrl(mapsLink(c)); // '' si no hay dirección ni enlace configurado
  const instagram = safeUrl(c.instagram);
  const handle = instagram ? `@${instagram.replace(/\/+$/, '').split('/').pop()}` : '';
  return {
    address: { text: address || 'Dirección por confirmar', real: Boolean(c.address.trim()) },
    hours: {
      days: hours.days.trim() || 'Días por confirmar',
      time: `${hours.open} – ${hours.close}`,
    },
    phone: c.phone.trim() ? { text: formatPhone(c.phone), href: `tel:+${c.phone.replace(/\D/g, '')}` } : null,
    whatsapp: {
      text: formatPhone(business.whatsappNumber),
      href: buildWhatsAppUrl(`Hola, ${business.name}. Quisiera hacer una consulta.`),
    },
    email: c.email.trim() ? { text: c.email.trim(), href: `mailto:${c.email.trim()}` } : null,
    instagram: instagram ? { text: handle, href: instagram } : null,
    map: map ? { href: map } : null,
    embed: c.showMapEmbed && c.address.trim()
      ? `https://www.google.com/maps?q=${encodeURIComponent(address)}&output=embed`
      : '',
    isDemo: Boolean(c.isDemo),
  };
}

/* ---------- Dibujo ---------- */

const $ = (root, sel) => root.querySelector(sel);

function setText(root, key, text, pending = false) {
  const el = $(root, `[data-contact="${key}"]`);
  if (!el) return;
  el.textContent = text;
  el.classList.toggle('is-pending', pending);
}

/** Muestra u oculta los enlaces de una acción según exista su dato. */
function setAction(root, key, action) {
  root.querySelectorAll(`[data-contact-action="${key}"]`).forEach((el) => {
    el.hidden = !action;
    if (action) el.href = action.href;
  });
}

export function initContact() {
  const section = document.querySelector('[data-contact-section]');
  if (!section) return;
  const v = getContactView();

  setText(section, 'address', v.address.text, !v.address.real);
  setText(section, 'days', v.hours.days, !BOOKING_HOURS.days.trim());
  setText(section, 'time', v.hours.time);
  setText(section, 'whatsapp', v.whatsapp.text);
  setText(section, 'phone', v.phone ? v.phone.text : PENDING, !v.phone);
  setText(section, 'email', v.email ? v.email.text : PENDING, !v.email);
  setText(section, 'instagram', v.instagram ? v.instagram.text : PENDING, !v.instagram);

  setAction(section, 'whatsapp', v.whatsapp);
  setAction(section, 'phone', v.phone);
  setAction(section, 'email', v.email);
  setAction(section, 'instagram', v.instagram);
  setAction(section, 'map', v.map);

  // Avisos de datos ilustrativos
  section.querySelectorAll('[data-contact-demo]').forEach((el) => { el.hidden = !v.isDemo; });

  // Mapa: real (iframe) solo con dirección confirmada; si no, estado de demostración
  const frame = $(section, '[data-contact-map]');
  const placeholder = $(section, '[data-contact-placeholder]');
  if (v.embed && frame) {
    const iframe = document.createElement('iframe');
    iframe.className = 'location-map__frame';
    iframe.src = v.embed;
    iframe.title = `Mapa de ubicación de ${BUSINESS.name}`;
    iframe.loading = 'lazy';
    iframe.referrerPolicy = 'no-referrer-when-downgrade';
    iframe.allowFullscreen = true;
    frame.append(iframe);
    if (placeholder) placeholder.hidden = true;
  }
}
