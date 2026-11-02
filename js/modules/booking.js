/**
 * booking.js — Reservas por WhatsApp.
 * - Enlaces "Reservar ahora" de cada servicio.
 * - Formulario de reservas con resumen sincronizado en tiempo real.
 *
 * Flujo del formulario (una sola dirección):
 *   el usuario escribe → setState() → el store avisa → render()
 * El resumen nunca se escribe "a mano": siempre se dibuja desde el estado.
 */

import { BUSINESS, BOOKING_HOURS } from '../config.js?v=10.0';
import { createStore } from './store.js?v=10.0';
import { getServices } from './services-data.js?v=10.0';

const EMPTY = '—';

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

/* ---------- Utilidades de fecha y hora ---------- */

const pad = (n) => String(n).padStart(2, '0');
const toMinutes = (hhmm) => {
  const [h, m] = hhmm.split(':').map(Number);
  return h * 60 + m;
};
const toHHMM = (minutes) => `${pad(Math.floor(minutes / 60))}:${pad(minutes % 60)}`;

/** Fecha local de hoy en formato del input date: "2026-11-02". */
export function todayISO(now = new Date()) {
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/** "2026-11-09" → "Lunes, 9 de noviembre de 2026" (fecha local, sin desfase UTC). */
export function formatDate(iso) {
  if (!iso) return '';
  const [y, m, d] = iso.split('-').map(Number);
  const text = new Intl.DateTimeFormat('es-CL', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  }).format(new Date(y, m - 1, d));
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/**
 * Horarios cada BOOKING_HOURS.slotMinutes dentro del horario configurado.
 * Si la fecha es hoy, solo se ofrecen horas posteriores a la actual.
 */
export function getTimeSlots(dateISO, now = new Date()) {
  const { open, close, slotMinutes } = BOOKING_HOURS;
  const slots = [];
  for (let t = toMinutes(open); t + slotMinutes <= toMinutes(close); t += slotMinutes) {
    slots.push(toHHMM(t));
  }
  if (dateISO !== todayISO(now)) return slots;
  const current = now.getHours() * 60 + now.getMinutes();
  return slots.filter((slot) => toMinutes(slot) > current);
}

/* ---------- Validación ---------- */

const PHONE_ALLOWED = /^[0-9+()\s-]+$/;

/** Devuelve { campo: 'mensaje' } solo para los campos con error. */
export function validate(state, services, now = new Date()) {
  const errors = {};
  if (state.name.trim().length < 2) errors.name = 'Ingresa tu nombre completo.';
  if (!services.some((s) => s.id === state.serviceId)) errors.serviceId = 'Selecciona un servicio.';
  if (!state.date) errors.date = 'Selecciona una fecha.';
  else if (state.date < todayISO(now)) errors.date = 'La fecha no puede ser anterior a hoy.';
  if (!state.time) errors.time = 'Selecciona una hora.';
  else if (state.date && !getTimeSlots(state.date, now).includes(state.time)) {
    errors.time = 'Selecciona una hora válida dentro del horario de atención.';
  }
  const phone = state.phone.trim();
  const digits = phone.replace(/\D/g, '').length;
  if (phone && (!PHONE_ALLOWED.test(phone) || digits < 8 || digits > 15)) {
    errors.phone = 'Ingresa un teléfono válido (solo números, espacios y +).';
  }
  return errors;
}

/* ---------- Mensaje de WhatsApp ---------- */

export function buildBookingMessage(state, service) {
  const lines = [
    `Hola, ${BUSINESS.name}. Quisiera solicitar una reserva.`,
    '',
    `Nombre: ${state.name.trim()}`,
    `Servicio: ${service.name}`,
    `Precio referencial: ${service.priceLabel}`,
    `Fecha deseada: ${formatDate(state.date)}`,
    `Hora deseada: ${state.time}`,
  ];
  if (state.phone.trim()) lines.push(`Teléfono: ${state.phone.trim()}`);
  lines.push(`Observaciones: ${state.notes.trim() || EMPTY}`);
  lines.push('', 'Entiendo que esta solicitud debe ser confirmada por el establecimiento.');
  return lines.join('\n');
}

/* ---------- Formulario ---------- */

const FIELD_LABELS = {
  name: 'Nombre completo',
  serviceId: 'Servicio',
  date: 'Fecha deseada',
  time: 'Hora deseada',
  phone: 'Teléfono',
};

export function initBookingForm() {
  const form = document.querySelector('[data-booking-form]');
  if (!form) return;

  const services = getServices();
  const fields = {
    name: form.elements.name,
    serviceId: form.elements.serviceId,
    date: form.elements.date,
    time: form.elements.time,
    phone: form.elements.phone,
    notes: form.elements.notes,
  };
  const summary = Object.fromEntries(
    [...document.querySelectorAll('[data-summary]')].map((el) => [el.dataset.summary, el])
  );
  const status = document.querySelector('[data-booking-status]');

  // Servicios del selector desde la fuente única (tarjetas)
  services.forEach((s) => fields.serviceId.add(new Option(`${s.name} · ${s.priceLabel}`, s.id)));

  // Bloquear fechas pasadas
  fields.date.min = todayISO();

  const store = createStore({
    name: '', serviceId: '', date: '', time: '', phone: '', notes: '',
    attempted: false, // ¿Ya intentó enviar? (para mostrar errores en vivo)
  });

  // 1) Formulario → estado (todos los campos, en cada tecla o selección)
  const onInput = (event) => {
    const { name, value } = event.target;
    if (name in fields) store.setState({ [name]: value });
  };
  form.addEventListener('input', onInput);
  form.addEventListener('change', onInput);

  // 2) Estado → resumen (se redibuja completo desde el estado)
  store.subscribe((state) => {
    const service = services.find((s) => s.id === state.serviceId);
    const view = {
      name: state.name.trim(),
      service: service ? service.name : '',
      price: service ? service.priceLabel : '',
      date: formatDate(state.date),
      time: state.time,
      phone: state.phone.trim(),
      notes: state.notes.trim(),
    };
    Object.entries(view).forEach(([key, value]) => {
      const el = summary[key];
      if (!el) return;
      const text = value || EMPTY;
      if (el.textContent !== text) el.textContent = text;
      el.classList.toggle('is-empty', !value);
    });
  });

  // 3) Estado → horas disponibles para la fecha elegida
  store.subscribe((state, previous) => {
    const firstRun = state === previous;
    if (!firstRun && state.date === previous.date) return; // Solo al cambiar la fecha
    const slots = getTimeSlots(state.date);
    const select = fields.time;
    select.length = 1; // Conserva solo "Selecciona una hora"
    slots.forEach((slot) => select.add(new Option(slot, slot)));
    select.disabled = Boolean(state.date) && slots.length === 0;
    select.options[0].textContent = select.disabled ? 'Sin horarios para hoy' : 'Elige una hora';
    if (slots.includes(state.time)) select.value = state.time;
    else if (state.time) store.setState({ time: '' }); // La hora elegida ya no aplica
  });

  // 4) Estado → mensajes de error (solo después del primer intento)
  store.subscribe((state) => {
    const errors = state.attempted ? validate(state, services) : {};
    Object.keys(FIELD_LABELS).forEach((key) => {
      const input = fields[key];
      const message = form.querySelector(`[data-error-for="${key}"]`);
      const text = errors[key] || '';
      if (text) input.setAttribute('aria-invalid', 'true');
      else input.removeAttribute('aria-invalid');
      if (message) {
        message.textContent = text;
        message.hidden = !text;
      }
    });
    // Si ya corrigió todo, se retira el aviso de error del resumen
    if (state.attempted && !Object.keys(errors).length && status.dataset.state === 'error') {
      status.textContent = '';
      delete status.dataset.state;
    }
  });

  // 5) Enviar → validar → abrir WhatsApp
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    store.setState({ attempted: true });
    const state = store.getState();
    const errors = validate(state, services);
    const keys = Object.keys(errors);

    if (keys.length) {
      const list = keys.map((key) => FIELD_LABELS[key]).join(', ');
      status.textContent = `Revisa ${keys.length === 1 ? 'el campo' : 'los campos'}: ${list}.`;
      status.dataset.state = 'error';
      fields[keys[0]].focus();
      return;
    }

    const service = services.find((s) => s.id === state.serviceId);
    window.open(buildWhatsAppUrl(buildBookingMessage(state, service)), '_blank', 'noopener');
    status.textContent = 'Abrimos WhatsApp con tu solicitud. Envía el mensaje para que podamos confirmarla.';
    status.dataset.state = 'success';
  });
}
