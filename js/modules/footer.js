/**
 * footer.js — Pie de página.
 *
 * Reutiliza getContactView() de contact.js: los mismos datos y las mismas
 * reglas que la sección de contacto (fuente única en config.js).
 * Cada dato se muestra solo si existe; el aviso de demostración depende
 * de CONTACT.isDemo; el año del copyright es dinámico.
 */

import { getContactView } from './contact.js?v=11.0';

export function initFooter(now = new Date()) {
  const footer = document.querySelector('[data-footer]');
  if (!footer) return;
  const v = getContactView();

  const show = (key, visible) => {
    const item = footer.querySelector(`[data-footer-item="${key}"]`);
    if (item) item.hidden = !visible;
  };
  const text = (key, value) => {
    const el = footer.querySelector(`[data-footer="${key}"]`);
    if (el) el.textContent = value;
  };
  const link = (key, action) => {
    const el = footer.querySelector(`[data-footer-link="${key}"]`);
    if (el && action) el.href = action.href;
  };

  // Dirección: solo si es real
  show('address', v.address.real);
  if (v.address.real) text('address', v.address.text);

  // Horario (mismo origen que reservas y contacto)
  text('days', v.hours.days);
  text('time', v.hours.time);
  show('hours', true);

  // WhatsApp: canal principal ya usado en todo el sitio
  text('whatsapp', v.whatsapp.text);
  link('whatsapp', v.whatsapp);
  show('whatsapp', true);

  // Teléfono, correo e Instagram: solo con datos reales
  for (const key of ['phone', 'email', 'instagram']) {
    const action = v[key];
    show(key, Boolean(action));
    if (action) {
      text(key, action.text);
      link(key, action);
    }
  }

  // Aviso de sitio demostrativo
  const demo = footer.querySelector('[data-footer-demo]');
  if (demo) demo.hidden = !v.isDemo;

  // Año dinámico
  const year = footer.querySelector('[data-footer-year]');
  if (year) year.textContent = String(now.getFullYear());
}
