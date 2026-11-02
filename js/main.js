/**
 * main.js — Punto de entrada de JavaScript.
 * Importa e inicia los módulos de la página.
 */

import { initNavigation } from './modules/navigation.js';
import { initReveal } from './modules/reveal.js';
import { initServiceBooking, initBookingForm } from './modules/booking.js';
import { initLightbox } from './modules/lightbox.js';

initNavigation();
initReveal();
initServiceBooking();
initLightbox();
initBookingForm();
