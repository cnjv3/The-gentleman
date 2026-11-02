/**
 * reveal.js — Animaciones de aparición.
 * Muestra suavemente los elementos con [data-reveal] al entrar en pantalla.
 * El retraso opcional se define en el HTML con style="--reveal-delay: 150ms".
 */

export function initReveal() {
  const items = document.querySelectorAll('[data-reveal]');
  if (!items.length) return;

  const showAll = () => items.forEach((el) => el.classList.add('is-visible'));

  // Movimiento reducido o navegador sin soporte: mostrar todo de inmediato
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduceMotion || !('IntersectionObserver' in window)) {
    showAll();
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target); // Se anima una sola vez
      });
    },
    // Se activa cuando el elemento asoma un poco sobre el borde inferior
    { rootMargin: '0px 0px -10% 0px', threshold: 0.15 }
  );

  items.forEach((el) => observer.observe(el));
}
