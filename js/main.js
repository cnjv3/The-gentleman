/**
 * main.js — Punto de entrada de JavaScript.
 * Importa e inicia los módulos de la página.
 */

import { initNavigation } from './modules/navigation.js';
import { initReveal } from './modules/reveal.js';
import { initServiceBooking } from './modules/booking.js';

initNavigation();
initReveal();
initServiceBooking();
