/**
 * store.js — Estado reactivo mínimo (sin librerías).
 *
 * Un "store" guarda un objeto de estado. Cuando algo cambia con
 * setState(), avisa a todas las funciones suscritas, que vuelven a
 * dibujar su parte de la interfaz a partir del estado. Así, la
 * pantalla siempre refleja el estado y nunca al revés.
 */

export function createStore(initialState) {
  let state = { ...initialState };
  const listeners = new Set();

  return {
    getState: () => state,

    /** Mezcla los cambios y notifica solo si algo cambió de verdad. */
    setState(patch) {
      const changed = Object.keys(patch).some((key) => !Object.is(state[key], patch[key]));
      if (!changed) return;
      const previous = state;
      state = { ...state, ...patch };
      listeners.forEach((listener) => listener(state, previous));
    },

    /** Ejecuta la función ahora y en cada cambio. Devuelve cómo desuscribirse. */
    subscribe(listener) {
      listeners.add(listener);
      listener(state, state);
      return () => listeners.delete(listener);
    },
  };
}
