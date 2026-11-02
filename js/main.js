/**
 * main.js — Punto de entrada de JavaScript.
 * Importa e inicia los módulos de la página.
 */

import { initNavigation } from './modules/navigation.js?v=8.1';
import { initReveal } from './modules/reveal.js?v=8.1';
import { initServiceBooking, initBookingForm } from './modules/booking.js?v=8.1';
import { initLightbox } from './modules/lightbox.js?v=8.1';

initNavigation();
initReveal();
initServiceBooking();
initLightbox();
initBookingForm();
