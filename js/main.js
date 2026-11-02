/**
 * main.js — Punto de entrada de JavaScript.
 * Importa e inicia los módulos de la página.
 */

import { initNavigation } from './modules/navigation.js?v=10.0';
import { initReveal } from './modules/reveal.js?v=10.0';
import { initServiceBooking, initBookingForm } from './modules/booking.js?v=10.0';
import { initLightbox } from './modules/lightbox.js?v=10.0';
import { initContact } from './modules/contact.js?v=10.0';
import { initFooter } from './modules/footer.js?v=10.0';

initNavigation();
initReveal();
initServiceBooking();
initLightbox();
initBookingForm();
initContact();
initFooter();
