from playwright.sync_api import sync_playwright
import sys

URL = 'http://localhost:8771/'
OUT = sys.argv[1]
results = []

def check(name, cond, detail=''):
    results.append((bool(cond), name, detail))

CONTRAST_JS = r'''(sel) => {
 const lum=c=>{const m=c.match(/[\d.]+/g).slice(0,3).map(v=>{v/=255;return v<=0.04045?v/12.92:((v+0.055)/1.055)**2.4});return .2126*m[0]+.7152*m[1]+.0722*m[2]};
 const bgOf=el=>{while(el){const b=getComputedStyle(el).backgroundColor;if(!/rgba\(0, 0, 0, 0\)|transparent/.test(b))return b;el=el.parentElement}return 'rgb(255,255,255)'};
 const el=document.querySelector(sel);const a=lum(getComputedStyle(el).color),b=lum(bgOf(el));
 return +((Math.max(a,b)+.05)/(Math.min(a,b)+.05)).toFixed(2);
}'''

def state(pg):
    return pg.evaluate('''() => {
      const t=document.querySelector('[data-nav-toggle]'), p=document.querySelector('[data-nav-panel]');
      return {expanded:t.getAttribute('aria-expanded'), label:document.querySelector('[data-nav-label]').textContent,
              visibility:getComputedStyle(p).visibility, open:document.querySelector('[data-header]').classList.contains('is-open')};
    }''')

def active(pg):
    return pg.evaluate("() => { const a=document.activeElement; return a===document.body?'BODY':(a.textContent.trim().replace(/\\s+/g,' ')||a.tagName) }")

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome')
    errors = []

    def page(**kw):
        ctx = b.new_context(**kw)
        pg = ctx.new_page()
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.on('response', lambda r: r.status >= 400 and not r.url.endswith('/favicon.ico') and errors.append(f'{r.status} {r.url}'))
        pg.goto(URL, wait_until='load')
        pg.wait_for_timeout(300)
        return pg

    # ---------- 1. Android simulado (Pixel 7: táctil) ----------
    pg = page(**p.devices['Pixel 7'])
    s = state(pg)
    check('Android: menú cerrado al cargar', s['expanded'] == 'false' and s['visibility'] == 'hidden', str(s))
    h = pg.evaluate("document.querySelector('[data-header]').getBoundingClientRect().height")
    check('Android: altura del header ~76px', 75 <= h <= 80, f'{h:.0f}px')
    pg.screenshot(path=f'{OUT}/h-412-cerrado.png')
    pg.tap('[data-nav-toggle]'); pg.wait_for_timeout(500)
    s = state(pg)
    check('Android: tocar hamburguesa abre', s['expanded'] == 'true' and s['visibility'] == 'visible' and s['label'] == 'Cerrar menú', str(s))
    pg.screenshot(path=f'{OUT}/h-412-abierto.png')
    sizes = pg.evaluate("[...document.querySelectorAll('.site-nav__link, .site-nav__cta, [data-nav-toggle]')].map(e=>Math.round(e.getBoundingClientRect().height))")
    check('Android: objetivos táctiles ≥ 44px', min(sizes) >= 44, f'alturas {sizes}')
    check('Contraste enlace en panel', pg.evaluate(CONTRAST_JS, '.site-nav__link') >= 4.5, str(pg.evaluate(CONTRAST_JS, '.site-nav__link')))
    check('Contraste botón Reservar en panel', pg.evaluate(CONTRAST_JS, '.site-nav__cta') >= 4.5, str(pg.evaluate(CONTRAST_JS, '.site-nav__cta')))
    pg.tap('a.site-nav__link[href="#servicios"]'); pg.wait_for_timeout(500)
    s = state(pg)
    check('Android: tocar un enlace cierra el menú', s['expanded'] == 'false' and s['visibility'] == 'hidden', str(s))
    check('Android: el enlace navega', pg.evaluate('location.hash') == '#servicios')
    pg.tap('[data-nav-toggle]'); pg.wait_for_timeout(500)
    pg.touchscreen.tap(200, 780); pg.wait_for_timeout(500)
    check('Android: tocar fuera cierra el menú', state(pg)['expanded'] == 'false')
    check('Sin scroll horizontal (412)', not pg.evaluate('document.documentElement.scrollWidth > innerWidth'))
    pg.context.close()

    # ---------- 2. Teclado en móvil ----------
    pg = page(viewport={'width': 412, 'height': 915})
    order = []
    for _ in range(4):
        pg.keyboard.press('Tab'); order.append(active(pg))
    check('Teclado móvil (cerrado): enlaces ocultos no reciben foco', order == ['Saltar al contenido', 'THE GENTLEMAN Barber Studio', 'Abrir menú', 'Reservar ahora'], ' → '.join(order))
    pg.focus('[data-nav-toggle]'); pg.keyboard.press('Enter'); pg.wait_for_timeout(450)
    check('Teclado: Enter abre', state(pg)['expanded'] == 'true')
    pg.keyboard.press('Tab')
    check('Teclado: Tab entra al menú', active(pg) == 'Inicio', active(pg))
    pg.screenshot(path=f'{OUT}/h-412-foco-panel.png', clip={'x': 0, 'y': 0, 'width': 412, 'height': 220})
    pg.keyboard.press('Escape'); pg.wait_for_timeout(450)
    check('Teclado: Esc cierra y devuelve el foco al botón', state(pg)['expanded'] == 'false' and active(pg) == 'Abrir menú', active(pg))
    # Simula contenido enfocable después del header (las secciones aún no existen)
    pg.evaluate("document.querySelector('main').insertAdjacentHTML('beforeend','<a href=\\'#x\\' id=\\'tmp\\'>contenido</a>')")
    pg.keyboard.press('Enter'); pg.wait_for_timeout(450)
    for _ in range(8): pg.keyboard.press('Tab')
    check('Teclado: salir del menú con Tab lo cierra', state(pg)['expanded'] == 'false', active(pg))
    # Cambio a escritorio con el menú abierto
    pg.focus('[data-nav-toggle]'); pg.keyboard.press('Enter'); pg.wait_for_timeout(300)
    pg.set_viewport_size({'width': 1280, 'height': 900}); pg.wait_for_timeout(400)
    check('Pasar a escritorio con menú abierto lo restablece', state(pg)['expanded'] == 'false' and not state(pg)['open'])
    pg.context.close()

    # ---------- 3. Capturas y medidas por tamaño ----------
    for w in (360, 768, 1024, 1280):
        pg = page(viewport={'width': w, 'height': 800}, device_scale_factor=2 if w < 1000 else 1)
        m = pg.evaluate('''() => {
          const r=s=>document.querySelector(s).getBoundingClientRect();
          const links=[...document.querySelectorAll('.site-nav__link')].map(l=>l.getBoundingClientRect());
          return {h:r('[data-header]').height, logo:r('.logo'), list:r('.site-nav__list'), cta:r('.site-nav__cta'),
                  toggle:getComputedStyle(document.querySelector('[data-nav-toggle]')).display,
                  oneLine:links.every(l=>l.height<50 && Math.abs(l.top-links[0].top)<2), overflow:document.documentElement.scrollWidth>innerWidth};
        }''')
        check(f'{w}px: sin scroll horizontal', not m['overflow'])
        if w < 1024:
            check(f'{w}px: hamburguesa visible', m['toggle'] != 'none')
            if w == 360:
                pg.screenshot(path=f'{OUT}/h-360-cerrado.png')
                pg.click('[data-nav-toggle]'); pg.wait_for_timeout(500)
                pg.screenshot(path=f'{OUT}/h-360-abierto.png')
            else:
                pg.screenshot(path=f'{OUT}/h-{w}.png', clip={'x': 0, 'y': 0, 'width': w, 'height': 200})
        else:
            gap_logo = m['list']['x'] - (m['logo']['x'] + m['logo']['width'])
            gap_cta = m['cta']['x'] - (m['list']['x'] + m['list']['width'])
            check(f'{w}px: altura del header ~88px', 87 <= m['h'] <= 92, f"{m['h']:.0f}px")
            check(f'{w}px: hamburguesa oculta', m['toggle'] == 'none')
            check(f'{w}px: todo cabe en una línea sin choques', m['oneLine'] and gap_logo >= 24 and gap_cta >= 24, f'espacio logo→menú {gap_logo:.0f}px, menú→botón {gap_cta:.0f}px')
            pg.screenshot(path=f'{OUT}/h-{w}.png', clip={'x': 0, 'y': 0, 'width': w, 'height': 200})
            if w == 1280:
                for sel in ('.logo__name', '.logo__tagline span', '.site-nav__link', '.site-nav__cta'):
                    c = pg.evaluate(CONTRAST_JS, sel)
                    check(f'Contraste escritorio {sel}', c >= 4.5, str(c))
                order = []
                for _ in range(10):
                    pg.keyboard.press('Tab'); order.append(active(pg))
                exp = ['Saltar al contenido', 'THE GENTLEMAN Barber Studio', 'Inicio', 'Nosotros', 'Servicios', 'Galería', 'Ubicación', 'Contacto', 'Reservar', 'Reservar ahora']
                check('Escritorio: orden de Tab correcto', order == exp, ' → '.join(order))
                pg.focus('a.site-nav__link[href="#galeria"]'); pg.wait_for_timeout(450)
                pg.screenshot(path=f'{OUT}/h-1280-foco.png', clip={'x': 0, 'y': 0, 'width': 1280, 'height': 120})
        pg.context.close()

    # ---------- 4. Movimiento reducido ----------
    pg = page(viewport={'width': 412, 'height': 915}, reduced_motion='reduce')
    d = pg.evaluate("getComputedStyle(document.querySelector('[data-nav-panel]')).transitionDuration")
    check('Movimiento reducido: transiciones anuladas', all(float(x.strip()[:-1]) < 0.001 for x in d.split(',')), d)
    pg.context.close()

    # ---------- 5. Sin JavaScript ----------
    pg = page(viewport={'width': 412, 'height': 915}, java_script_enabled=False)
    vis = pg.evaluate("getComputedStyle(document.querySelector('[data-nav-panel]')).visibility")
    check('Sin JavaScript: el menú queda visible y usable', vis == 'visible')
    pg.screenshot(path=f'{OUT}/h-412-sin-js.png')
    pg.context.close()

    check('Sin errores de JavaScript ni consola', not errors, '; '.join(errors))
    b.close()

ok = sum(r[0] for r in results)
for r in results:
    print(('OK   ' if r[0] else 'FALLA'), r[1], ('· ' + r[2]) if r[2] else '')
print(f'\n{ok}/{len(results)} pruebas superadas')
