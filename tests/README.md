# Pruebas automáticas de THE GENTLEMAN

Esta carpeta guarda las **10 suites de pruebas** que se usaron durante el desarrollo (etapas 3 a 11).
Juntas suman **734 comprobaciones**. Cada suite abre la página en un navegador real (Google Chrome,
controlado con Playwright), simula teléfonos, tablets y escritorio, y revisa contenido, enlaces,
accesibilidad, diseño responsive y funcionamiento de los módulos de JavaScript.

Las pruebas **no modifican el sitio**: solo lo leen y lo abren en el navegador.

## Estructura

```
tests/
├── README.md          ← este documento
├── run_all.py         ← ejecuta todas las suites (o algunas) y suma el resultado
├── requirements.txt   ← paquetes de Python necesarios (versiones exactas usadas)
├── .gitignore         ← evita subir a GitHub las capturas y registros generados
├── suites/            ← las 10 suites originales
│   ├── test_header.py
│   ├── test_hero.py
│   ├── test_about.py
│   ├── test_services.py
│   ├── test_gallery.py
│   ├── test_booking.py
│   ├── test_fix_mobile.py
│   ├── test_contact.py
│   ├── test_footer.py
│   └── test_optim.py
└── output/            ← se crea al ejecutar (capturas .png y un .log por suite); no se sube
```

## Requisitos

| Requisito | Versión usada | Por qué |
|---|---|---|
| Python | 3.13.18 (Playwright exige 3.10 o más) | Lenguaje de las pruebas y del ejecutor |
| Playwright para Python | 1.63.0 (driver 1.63.0) | Controla el navegador |
| pyee · greenlet · typing_extensions | 13.0.1 · 3.5.6 · 4.16.0 | Dependencias de Playwright |
| Pillow | 12.3.0 | Analiza capturas (contraste sobre fotos) e imágenes del sitio |
| Google Chrome | 153.0.8010.12 (Chrome for Testing) | Navegador de las pruebas; **debe estar en `/usr/bin/google-chrome`** |
| Git con el historial completo | 2.43.0 | `test_fix_mobile.py` lee una versión antigua del CSS (commit `d4daf3e`) |
| Puerto 8771 libre | — | El ejecutor sirve el sitio en `http://localhost:8771/` |

No se necesita internet: las peticiones externas (Google Fonts, Google Maps) se bloquean o se
toleran si fallan. En la sesión de Claude Code en la nube donde se desarrolló el proyecto, Python,
Chrome y Git ya venían instalados; en otro entorno hay que instalarlos antes.

## Cómo ejecutarlas paso a paso

1. **Clona el repositorio completo** (sin `--depth`, porque se necesita el historial):
   ```bash
   git clone https://github.com/cnjv3/The-gentleman.git
   cd The-gentleman
   ```
   Para probar una rama concreta: `git checkout etapa-11-optimizacion`.

2. **Crea un entorno de Python** (recomendado, para no mezclar paquetes) **e instala los requisitos**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r tests/requirements.txt
   ```
   No hace falta ejecutar `playwright install`: las suites usan el Chrome del sistema.
   **Advertencia:** este paso todavía no se ha verificado (ver «Verificación de reproducibilidad»).

3. **Ejecuta todas las suites** desde la raíz del repositorio:
   ```bash
   python3 tests/run_all.py
   ```

4. **Lee el resultado.** Cada suite muestra una línea y, al final, el total:
   ```
     OK     test_header.py  36/36  (16 s)
     ...
   Total: 734/734 pruebas superadas · 0 fallas
   ```
   Si algo falla, aparece `FALLA` con el nombre de la comprobación y el detalle. La salida completa
   de cada suite queda en `tests/output/<suite>.log` y las capturas en `tests/output/<suite>/`.
   El comando termina con código 0 si todo pasa, 1 si alguna prueba falla y 2 si falta un requisito.

### Ejecutar solo algunas suites

```bash
python3 tests/run_all.py booking contact
```

Una suite también puede ejecutarse sola, sin el ejecutor, si antes sirves el sitio en el puerto 8771:

```bash
python3 -m http.server 8771 -d . &        # en la raíz del repositorio
python3 tests/suites/test_header.py /tmp/capturas
```

## Qué revisa cada suite

| Suite | Pruebas | Etapa | Qué revisa |
|---|---:|---|---|
| `test_header.py` | 36 | 3 | Menú móvil (abrir, cerrar, tocar fuera), etiquetas ARIA, teclado (orden del foco, Esc devuelve el foco al botón), contraste, tamaños de 360 a 1280 px, movimiento reducido y funcionamiento sin JavaScript |
| `test_hero.py` | 85 | 4 | Hero a pantalla completa en 7 tamaños (de 360×740 a 1920×1080, incluido el Motorola en horizontal): imagen correcta para cada pantalla, nada cortado, sin scroll horizontal, botones de 48 px o más, saltos de diseño (CLS), contraste del texto **medido sobre la foto real**, un solo `h1`, letra al 130 % |
| `test_about.py` | 25 | 5 | Sección Nosotros: contenido, enlace del menú, contraste sobre la imagen, tamaños, movimiento reducido y versión sin JavaScript |
| `test_services.py` | 80 | 6 | Las 8 tarjetas de servicios (nombre, descripción, precio, duración y sus datos legibles por máquina), enlaces hacia Reservas, composición por tamaño y efecto al pasar el cursor |
| `test_gallery.py` | 78 | 7 | 8 fotos en orden, AVIF, carga diferida, composición asimétrica sin huecos ni superposiciones, visor (lightbox) con botones, flechas, teclado, foco atrapado y bloqueo del fondo, versión móvil y tablet |
| `test_booking.py` | 127 | 8 | Formulario de reservas: datos tomados de las tarjetas (fuente única), resumen que se actualiza en tiempo real, validaciones, horarios disponibles, mensaje de WhatsApp exacto y número tomado de `config.js` |
| `test_fix_mobile.py` | 49 | arreglo PR #9 | Versión `?v=` igual en todas las referencias CSS/JS, íconos que no crecen si el CSS falla o es una copia antigua, formulario en los anchos del Motorola (360–430 px) |
| `test_contact.py` | 113 | 9 | Ubicación y contacto: datos de demostración, estados del mapa (sin datos, enlace, mapa insertado, mapa que no carga), validación de URLs, cambios desde `config.js` y responsive |
| `test_footer.py` | 94 | 10 | Footer: estructura, enlaces internos, «Volver arriba», datos vacíos y configurados, año del copyright dinámico, responsive y versión sin JavaScript |
| `test_optim.py` | 47 | 11 | SEO (description, canonical, Open Graph, imagen de vista previa 1200×630), íconos, rutas relativas y mayúsculas exactas, seguridad básica del código, configuración intacta, carga de módulos e imágenes |
| **Total** | **734** | | |

## Dependencias de herramientas y del entorno

Estas suites nacieron en un espacio de trabajo temporal y conservan algunas suposiciones de ese
entorno. Están documentadas aquí para que nadie se lleve una sorpresa:

- **Dirección fija `http://localhost:8771/`.** Todas las suites abren esa dirección. `run_all.py`
  levanta el servidor ahí y se detiene con un aviso si el puerto está ocupado.
- **Ruta fija de Chrome `/usr/bin/google-chrome`.** Si Chrome está en otro lugar, hay que cambiar
  `executable_path` en cada suite. El ejecutor avisa si no lo encuentra.
- **Historial de Git.** `test_fix_mobile.py` ejecuta `git show d4daf3e:css/styles.css` para simular
  un teléfono con el CSS antiguo en caché. En un clon parcial (`--depth 1`) ese comando devolvería
  vacío y la prueba perdería sentido, por eso `run_all.py` comprueba antes que el commit exista.
- **Reloj fijo en Reservas.** `test_booking.py` fija la fecha en el lunes 2 de noviembre de 2026,
  15:10 (Santiago). Así los resultados no dependen del día en que se ejecuten.
- **Año real en el footer.** `test_footer.py` compara el año con el del sistema y además fija el
  reloj en 2031 para comprobar que cambia solo.
- **Configuración simulada.** Contacto y footer prueban «datos reales» reemplazando `config.js`
  **solo dentro del navegador** con datos de ejemplo (`contacto@example.com`, `Calle Prueba 123`,
  etc.). El archivo del repositorio no se toca.
- **Salida.** Cada suite recibe una carpeta donde guardar sus capturas (`tests/output/<suite>/`).

### Cambios respecto de los archivos originales

Los archivos se recuperaron completos del espacio de trabajo donde se ejecutaron. Seis suites son
idénticas byte a byte. En cuatro se cambió **solo la ruta del repositorio**, que estaba fija
(`/home/claude/the-gentleman`) y ahora se calcula desde la ubicación del archivo, para que funcionen
en cualquier carpeta:

| Suite | Líneas cambiadas |
|---|---|
| `test_booking.py` | `import os` y la línea `REPO = …` |
| `test_fix_mobile.py` | `import os` y la línea `REPO = …` |
| `test_optim.py` | la línea `REPO = …` |
| `test_contact.py` | `import os`, una línea `REPO = …` nueva y la lectura de `config.js` usando `REPO` |

Ninguna comprobación se agregó, quitó ni modificó.

## Verificación de reproducibilidad (2 de noviembre de 2026)

**Resultado real:** 734/734 pruebas superadas, 0 fallas y 0 errores de Python, en **una sola
ejecución** de `python3 tests/run_all.py` sobre el commit `947b5a9`. El sitio de ese commit es
idéntico al de `0839655`: solo se agregó `tests/`. El recuento se comprobó además contando las
líneas `OK` y `FALLA` de los 10 registros.

| Suite | Superadas | Fallas | Tiempo |
|---|---:|---:|---:|
| header | 36/36 | 0 | 15 s |
| hero | 85/85 | 0 | 44 s |
| about | 25/25 | 0 | 21 s |
| services | 80/80 | 0 | 41 s |
| gallery | 78/78 | 0 | 52 s |
| booking | 127/127 | 0 | 43 s |
| fix_mobile | 49/49 | 0 | 21 s |
| contact | 113/113 | 0 | 51 s |
| footer | 94/94 | 0 | 19 s |
| optim | 47/47 | 0 | 34 s |
| **Total** | **734/734** | **0** | ~6 min |

**Qué sí se verificó:**
- Clon nuevo desde GitHub, en una carpeta distinta de la de trabajo (así se comprueba que no
  quedan rutas fijas).
- Ejecución con el entorno vaciado (`env -i`, sin variables heredadas y con un `HOME` nuevo) y
  sin acceso a los archivos temporales donde nacieron las suites.
- El aviso de clon parcial: con `git clone --depth 1`, `run_all.py` se detiene con código 2 y
  explica cómo corregirlo.

**Qué NO se verificó: no es una ejecución limpia completa.** Los paquetes de Python no se
instalaron desde `requirements.txt`. Se usaron los que la sesión de Claude Code ya traía
instalados, con las mismas versiones que lista ese archivo. Motivos:
- En esa sesión no había acceso a PyPI. El entorno no resolvía nombres de internet por su cuenta,
  y a través del proxy de la sesión `pypi.org` respondía 403. Es un problema de conectividad: la
  versión 1.63.0 de Playwright existe en PyPI (publicada el 15 de septiembre de 2026).
- La caché local de paquetes (`uv`) no contenía `playwright`, `Pillow`, `greenlet` ni `pyee`, así
  que tampoco se pudo instalar sin conexión.

Para completar la verificación, en un entorno con acceso a PyPI: crear un entorno virtual nuevo
(sin `--system-site-packages`), ejecutar `pip install -r tests/requirements.txt` y luego
`python3 tests/run_all.py`.

## Limitaciones

- **Instalación de dependencias sin verificar.** Ver la sección anterior: el resultado se obtuvo
  con paquetes ya instalados, no instalados desde `requirements.txt`.
- **Un solo navegador.** Todo se prueba en Google Chrome. Firefox, Safari (iPhone) y Samsung
  Internet no se prueban.
- **Teléfonos simulados, no reales.** El Motorola Edge 50 Fusion y otros equipos se simulan con
  tamaño de pantalla, densidad de píxeles y toque. Una revisión en un teléfono real sigue siendo
  necesaria.
- **Sin Google Fonts.** El entorno donde se validaron no tenía acceso a Google Fonts, así que las
  734 pruebas pasaron con las fuentes de respaldo, no con Playfair Display y Montserrat. Con las
  fuentes reales, algunas medidas (alturas, cortes de línea) pueden variar ligeramente.
- **Las capturas no se comparan solas.** Las suites guardan capturas para revisarlas a ojo; no hay
  comparación automática de imágenes contra una referencia.
- **Rendimiento no incluido.** Las mediciones de la etapa 11 (TBT, LCP con 4G simulado, peso por
  dispositivo) se hicieron con scripts de medición aparte, que no forman parte de estas suites.
  `test_hero.py` y `test_gallery.py` solo verifican límites básicos (qué imágenes se descargan,
  CLS, que el LCP se pueda medir).
- **Sin servicios externos.** Google Maps no se carga de verdad (se bloquea o se simula) y WhatsApp
  no se abre: se intercepta `window.open` para leer el enlace y el mensaje generados.
- **Atadas al contenido actual.** Las pruebas esperan textos, precios de ejemplo, número de
  servicios y fotos exactos. Si el contenido cambia a propósito, hay que actualizar la suite
  correspondiente.
- **Recuento fijo por suite.** `run_all.py` avisa si una suite ejecuta un número de pruebas
  distinto del esperado (por ejemplo, 36 en `test_header.py`), para detectar suites que se cortan
  antes de terminar.
- **Duración.** La ejecución completa tarda varios minutos, porque cada suite abre muchas páginas
  en tamaños distintos.
- **Ejecución manual.** No hay integración continua (por ejemplo, GitHub Actions): las pruebas se
  ejecutan a mano con el comando de arriba.
