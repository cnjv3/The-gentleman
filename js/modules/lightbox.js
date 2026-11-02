/**
 * lightbox.js — Visor ampliado de la galería.
 * Usa <dialog> nativo: atrapa el foco, inertiza el fondo y se cierra
 * con Escape. Agrega navegación (botones, flechas del teclado y
 * deslizamiento táctil) y bloqueo del desplazamiento del fondo.
 * Sin JavaScript, cada foto es un enlace normal a la imagen grande.
 */

const SWIPE_MIN = 50; // px mínimos para considerar un deslizamiento

export function initLightbox() {
  const dialog = document.querySelector('[data-lightbox-dialog]');
  const links = [...document.querySelectorAll('a[data-lightbox]')];
  if (!dialog || !links.length || typeof dialog.showModal !== 'function') return;

  const image = dialog.querySelector('[data-lightbox-image]');
  const source = dialog.querySelector('[data-lightbox-source]');
  const caption = dialog.querySelector('[data-lightbox-caption]');
  const counter = dialog.querySelector('[data-lightbox-counter]');
  const root = document.documentElement;
  let index = 0;

  function show(i) {
    index = (i + links.length) % links.length; // Circular
    const link = links[index];
    const thumb = link.querySelector('img');
    if (source) source.srcset = link.dataset.avif || '';
    image.src = link.href;
    image.alt = thumb ? thumb.alt : '';
    caption.textContent = link.dataset.caption || '';
    counter.textContent = `${index + 1} / ${links.length}`;
  }

  function open(i) {
    show(i);
    root.classList.add('is-scroll-locked');
    dialog.showModal();
  }

  const close = () => dialog.close();
  const prev = () => show(index - 1);
  const next = () => show(index + 1);

  links.forEach((link, i) => {
    link.addEventListener('click', (event) => {
      event.preventDefault();
      open(i);
    });
  });

  dialog.querySelector('[data-lightbox-close]').addEventListener('click', close);
  dialog.querySelector('[data-lightbox-prev]').addEventListener('click', prev);
  dialog.querySelector('[data-lightbox-next]').addEventListener('click', next);

  // Al cerrar (botón, Escape o fondo): liberar el desplazamiento
  // y devolver el foco a la foto que se estaba viendo.
  dialog.addEventListener('close', () => {
    root.classList.remove('is-scroll-locked');
    links[index].focus();
  });

  // Tocar el fondo oscuro (fuera de la foto y los botones) cierra
  dialog.addEventListener('click', (event) => {
    if (event.target === dialog) close();
  });

  // Teclado: flechas para navegar y Tab en ciclo dentro del visor
  // (el <dialog> nativo deja salir el foco hacia el navegador).
  const controls = [...dialog.querySelectorAll('button')];
  dialog.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowLeft') prev();
    if (event.key === 'ArrowRight') next();
    if (event.key !== 'Tab') return;
    const first = controls[0];
    const last = controls[controls.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });

  // Deslizamiento táctil
  let startX = null;
  dialog.addEventListener('pointerdown', (event) => {
    if (event.pointerType === 'touch') startX = event.clientX;
  });
  dialog.addEventListener('pointerup', (event) => {
    if (startX === null) return;
    const dx = event.clientX - startX;
    startX = null;
    if (Math.abs(dx) >= SWIPE_MIN) (dx < 0 ? next : prev)();
  });
}
