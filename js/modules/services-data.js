/**
 * services-data.js — Fuente única de los servicios.
 *
 * Los servicios, precios y duraciones se escriben UNA sola vez: en las
 * tarjetas de la sección #servicios del HTML. Este módulo los lee desde
 * ahí, así que el formulario de reservas nunca duplica precios.
 */

/** "Diseño Premium" → "diseno-premium" */
function slugify(text) {
  return text
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '');
}

export function getServices(root = document) {
  return [...root.querySelectorAll('#servicios .service-card')].map((card) => {
    const name = card.querySelector('.service-card__title').textContent.trim();
    const price = card.querySelector('.service-card__price data');
    const time = card.querySelector('.service-card__time time');
    return {
      id: slugify(name),
      name,
      price: Number(price.value),
      priceLabel: price.textContent.trim(), // Texto visible, ej.: "$X.XXX"
      duration: time ? time.textContent.trim() : '',
    };
  });
}
