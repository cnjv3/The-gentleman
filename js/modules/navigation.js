/**
 * navigation.js — Menú de navegación.
 * Abre y cierra el menú hamburguesa en dispositivos móviles
 * siguiendo el patrón "disclosure" (botón que muestra/oculta un panel).
 */

// Mismo punto de quiebre que el CSS (64em = 1024px)
const DESKTOP_QUERY = window.matchMedia('(min-width: 64em)');

export function initNavigation() {
  const header = document.querySelector('[data-header]');
  if (!header) return;

  const toggle = header.querySelector('[data-nav-toggle]');
  const panel = header.querySelector('[data-nav-panel]');
  const label = header.querySelector('[data-nav-label]');
  const nav = toggle?.closest('nav');
  if (!toggle || !panel || !nav) return;

  const isOpen = () => toggle.getAttribute('aria-expanded') === 'true';

  function setOpen(open, { returnFocus = false } = {}) {
    toggle.setAttribute('aria-expanded', String(open));
    header.classList.toggle('is-open', open);
    if (label) label.textContent = open ? 'Cerrar menú' : 'Abrir menú';
    if (!open && returnFocus) toggle.focus();
  }

  // Abrir / cerrar con el botón
  toggle.addEventListener('click', () => setOpen(!isOpen()));

  // Cerrar al elegir un enlace del menú
  panel.addEventListener('click', (event) => {
    if (event.target.closest('a') && isOpen()) setOpen(false);
  });

  // Cerrar con Escape y devolver el foco al botón
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && isOpen()) {
      setOpen(false, { returnFocus: true });
    }
  });

  // Cerrar al tocar fuera del menú
  document.addEventListener('click', (event) => {
    if (isOpen() && !nav.contains(event.target)) setOpen(false);
  });

  // Cerrar cuando el foco del teclado sale del menú
  nav.addEventListener('focusout', (event) => {
    const next = event.relatedTarget;
    if (isOpen() && next && !nav.contains(next)) setOpen(false);
  });

  // Restablecer al pasar a tamaño escritorio
  DESKTOP_QUERY.addEventListener('change', (event) => {
    if (event.matches && isOpen()) setOpen(false);
  });
}
