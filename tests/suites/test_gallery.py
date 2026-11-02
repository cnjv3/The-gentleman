from playwright.sync_api import sync_playwright
import sys, urllib.request

URL = 'http://localhost:8771/'
OUT = sys.argv[1]
results = []
def check(name, cond, detail=''):
    results.append((bool(cond), name, detail))

CAPTIONS = ['Corte clásico', 'Arreglo de barba', 'Tratamiento capilar', 'Peinado y styling',
            'Afeitado clásico', 'Ritual de toalla caliente', 'Degradado y perfilado', 'Experiencia THE GENTLEMAN']

CONTRAST_JS = r'''(sel) => {
 const p=c=>{const v=c.match(/[\d.]+/g).slice(0,3).map(Number);return c.startsWith('color(')?v.map(x=>x*255):v};
 const lum=a=>{const m=a.map(v=>{v/=255;return v<=0.04045?v/12.92:((v+0.055)/1.055)**2.4});return .2126*m[0]+.7152*m[1]+.0722*m[2]};
 const el=document.querySelector(sel), cs=getComputedStyle(el);
 let n=el, bg; while(n){const b=getComputedStyle(n).backgroundColor; if(!/rgba\(0, 0, 0, 0\)|transparent/.test(b)){bg=b;break} n=n.parentElement}
 const a=lum(p(cs.color)), b=lum(p(bg)); return +((Math.max(a,b)+.05)/(Math.min(a,b)+.05)).toFixed(2);
}'''
RECTS_JS = "[...document.querySelectorAll('.gallery__item')].map(e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y+scrollY,w:r.width,h:r.height}})"
LB = '''() => {const d=document.querySelector('[data-lightbox-dialog]'), i=d.querySelector('[data-lightbox-image]');
  return {open:d.open, counter:d.querySelector('[data-lightbox-counter]').textContent, caption:d.querySelector('[data-lightbox-caption]').textContent,
          src:i.currentSrc.split('/').pop(), loaded:i.complete&&i.naturalWidth>0, alt:i.alt, locked:document.documentElement.classList.contains('is-scroll-locked'),
          focusInside:d.contains(document.activeElement)}}'''

def scroll_gallery(pg):
    pg.evaluate("document.querySelector('#galeria').scrollIntoView()"); pg.wait_for_timeout(300)
    for _ in range(14):
        pg.mouse.wheel(0, 450); pg.wait_for_timeout(120)
    pg.wait_for_timeout(1500)

def section_shot(pg, path, w):
    pg.evaluate("document.querySelector('#galeria').scrollIntoView()"); pg.wait_for_timeout(300)
    s = pg.evaluate("(()=>{const r=document.querySelector('#galeria').getBoundingClientRect();return [r.top+scrollY, r.height]})()")
    pg.screenshot(path=path, full_page=True, clip={'x': 0, 'y': s[0], 'width': w, 'height': s[1]})

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome')
    errors = []
    def page(**kw):
        ctx = b.new_context(**kw); pg = ctx.new_page()
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.on('response', lambda r: r.status >= 400 and not r.url.endswith('/favicon.ico') and errors.append(f'{r.status} {r.url}'))
        pg.add_init_script("window.__cls=0;new PerformanceObserver(l=>l.getEntries().forEach(e=>{if(!e.hadRecentInput)window.__cls+=e.value})).observe({type:'layout-shift',buffered:true});")
        pg.goto(URL, wait_until='load'); pg.wait_for_timeout(300)
        return pg
    gal = lambda pg: pg.evaluate("performance.getEntriesByType('resource').filter(r=>r.name.includes('/gallery/')).map(r=>[r.name.split('/').pop(), r.encodedBodySize])")

    # ---------- 1-2. Contenido, imágenes y rutas (escritorio) ----------
    pg = page(viewport={'width': 1280, 'height': 800})
    order = pg.evaluate("[...document.querySelectorAll('main > section')].map(s=>s.id)")
    check('Orden: … servicios → galería', order[:4] == ['inicio', 'nosotros', 'servicios', 'galeria'], str(order))
    head = pg.evaluate("(()=>{const s=document.querySelector('#galeria');return [s.querySelector('.section-heading__eyebrow').textContent.trim(), s.querySelector('h2').textContent.trim(), s.querySelector('.section-heading__text').textContent.trim()]})()")
    check('Encabezado exacto', head == ['Nuestro trabajo', 'El estilo está en los detalles.', 'Cada corte, cada acabado y cada detalle reflejan nuestra pasión por el arte de la barbería.'], str(head))
    sig = pg.evaluate("[...document.querySelectorAll('.gallery__signature p')].map(e=>e.textContent.trim()+'|'+(e.getAttribute('lang')||''))")
    check('Cierre editorial (con lang="en" en el lema)', sig == ['THE GENTLEMAN|', 'Barber Studio|', 'Tradition meets modern style.|en'], str(sig))
    meta = pg.evaluate("[...document.querySelectorAll('.gallery__link')].map(a=>{const i=a.querySelector('img');return {cap:a.dataset.caption, href:a.getAttribute('href'), avif:a.dataset.avif, w:i.getAttribute('width'), h:i.getAttribute('height'), lazy:i.loading, alt:i.alt, srcs:[i.getAttribute('src'), ...i.srcset.split(',').map(s=>s.trim().split(' ')[0]), ...a.querySelector('source').srcset.split(',').map(s=>s.trim().split(' ')[0])]}})")
    check('Exactamente 8 fotografías, en el orden asignado', [m['cap'] for m in meta] == CAPTIONS, ', '.join(m['cap'] for m in meta))
    check('width/height definidos, loading="lazy" y alt descriptivo', all(m['w'] == '1536' and m['h'] == '1024' and m['lazy'] == 'lazy' and m['alt'].startswith('Imagen ilustrativa:') and len(m['alt']) > 40 for m in meta))
    urls = sorted({u for m in meta for u in m['srcs'] + [m['href'], m['avif']]})
    bad = []
    for u in urls:
        try: urllib.request.urlopen(URL + u).read()
        except Exception as e: bad.append(u)
    check(f'Rutas relativas: los {len(urls)} archivos existen', not bad and all(not u.startswith('/') for u in urls), ', '.join(bad))
    check('Ninguna foto reutiliza imágenes de Hero, Nosotros o Servicios', all('/gallery/' in u for u in urls))
    check('Rendimiento: ninguna foto de la galería se descarga al cargar la página', len(gal(pg)) == 0, str(gal(pg)))
    hidden = pg.evaluate("[...document.querySelectorAll('#galeria [data-reveal]')].filter(e=>e.classList.contains('is-visible')).length")
    check('Antes de desplazarse: galería aún sin animar', hidden == 0)
    scroll_gallery(pg)
    imgs = pg.evaluate("[...document.querySelectorAll('.gallery__link img')].map(i=>({src:i.currentSrc.split('/').pop(), ok:i.complete&&i.naturalWidth>0}))")
    check('Las 8 fotos cargan en AVIF', all(i['ok'] and i['src'].endswith('.avif') for i in imgs), ', '.join(i['src'] for i in imgs))
    check('Las 8 fotos son archivos distintos', len({i['src'].split('-')[0] for i in imgs}) == 8)
    check('Aparición con reveal.js al desplazarse', pg.evaluate("[...document.querySelectorAll('#galeria [data-reveal]')].every(e=>e.classList.contains('is-visible')&&getComputedStyle(e).opacity==='1')"))
    kb = sum(s for _, s in gal(pg)) / 1024
    check('Rendimiento: peso de la galería en escritorio', kb < 900, f'{kb:.0f} KB · {len(gal(pg))} archivos')
    check('Sin saltos de diseño (CLS) al desplazarse', pg.evaluate('window.__cls') < 0.02, f"CLS {pg.evaluate('window.__cls'):.3f}")
    for sel, need in (('#galeria .section-heading__eyebrow', 4.5), ('#gallery-title', 3), ('#galeria .section-heading__text', 4.5),
                      ('.gallery__note', 4.5), ('.gallery__brand', 3), ('.gallery__tagline', 4.5), ('.gallery__motto', 4.5)):
        r = pg.evaluate(CONTRAST_JS, sel); check(f'Contraste {sel}', r >= need, f'{r}:1')

    # ---------- Composición editorial (escritorio) ----------
    filled = pg.evaluate("[...document.querySelectorAll('.gallery__link')].map(a=>{const i=a.querySelector('img').getBoundingClientRect(),r=a.getBoundingClientRect();return Math.abs(i.height-r.height)<1.5&&Math.abs(i.width-r.width)<1.5})")
    check('1280px: cada foto llena su celda (sin huecos)', all(filled), str(filled))
    R = pg.evaluate(RECTS_JS)
    sizes = {(round(r['w']), round(r['h'])) for r in R}
    check('Escritorio: composición asimétrica (≥5 tamaños distintos)', len(sizes) >= 5, f'{len(sizes)} tamaños')
    over = any(not (a['x'] + a['w'] <= c['x'] + 1 or c['x'] + c['w'] <= a['x'] + 1 or a['y'] + a['h'] <= c['y'] + 1 or c['y'] + c['h'] <= a['y'] + 1)
               for i, a in enumerate(R) for c in R[i + 1:])
    check('Escritorio: sin superposiciones', not over)
    cw = pg.evaluate("document.querySelector('#galeria .container').getBoundingClientRect().width - 2*parseFloat(getComputedStyle(document.querySelector('#galeria .container')).paddingLeft)")
    last = R[7]
    check('Foto 8: cierre panorámico a todo el ancho, al final', abs(last['w'] - cw) < 2 and last['y'] >= max(r['y'] for r in R[:7]) and last['w'] / last['h'] > 2, f"{last['w']:.0f}×{last['h']:.0f}")
    pg.hover('.gallery__item--2 .gallery__link'); pg.wait_for_timeout(900)
    tf = pg.evaluate("getComputedStyle(document.querySelector('.gallery__item--2 img')).transform")
    check('Hover: zoom fotográfico sutil', tf != 'none' and 1.0 < float(tf.split('(')[1].split(',')[0]) <= 1.05, tf)
    check('Cursor de ampliación', pg.evaluate("getComputedStyle(document.querySelector('.gallery__link')).cursor") == 'zoom-in')
    section_shot(pg, f'{OUT}/galeria-1280.png', 1280)

    # ---------- 3-6. Lightbox con ratón y teclado ----------
    pg.evaluate("document.querySelector('.gallery__item--3').scrollIntoView({block:'center'})"); pg.wait_for_timeout(300)
    y0 = pg.evaluate('scrollY')
    pg.click('.gallery__item--3 .gallery__link'); pg.wait_for_timeout(700)
    s = pg.evaluate(LB)
    check('Abre el visor en la foto seleccionada', s['open'] and s['counter'] == '3 / 8' and s['caption'] == 'Tratamiento capilar', f"{s['counter']} · {s['caption']}")
    check('Foto ampliada en 1536 px (AVIF) y con alt', s['loaded'] and s['src'] == '03-tratamiento-capilar-1536.avif' and s['alt'].startswith('Imagen ilustrativa'), s['src'])
    check('Fondo bloqueado y foco dentro del visor', s['locked'] and s['focusInside'])
    pg.mouse.wheel(0, 800); pg.wait_for_timeout(300)
    check('El fondo no se desplaza con el visor abierto', pg.evaluate('scrollY') == y0)
    pg.screenshot(path=f'{OUT}/lightbox-1280.png')
    pg.click('[data-lightbox-next]'); pg.wait_for_timeout(300)
    check('Botón siguiente → 4 / 8', pg.evaluate(LB)['counter'] == '4 / 8')
    pg.keyboard.press('ArrowRight'); pg.wait_for_timeout(200)
    check('Flecha derecha → 5 / 8', pg.evaluate(LB)['counter'] == '5 / 8')
    pg.keyboard.press('ArrowLeft'); pg.keyboard.press('ArrowLeft'); pg.wait_for_timeout(200)
    check('Flecha izquierda ×2 → 3 / 8', pg.evaluate(LB)['counter'] == '3 / 8')
    for _ in range(3): pg.click('[data-lightbox-prev]')
    pg.wait_for_timeout(300)
    check('Anterior desde la 1 vuelve a la 8 (circular)', pg.evaluate(LB)['counter'] == '8 / 8', pg.evaluate(LB)['counter'])
    inside = []
    for _ in range(8):
        pg.keyboard.press('Shift+Tab' if _ % 4 == 3 else 'Tab'); inside.append(pg.evaluate("document.querySelector('[data-lightbox-dialog]').contains(document.activeElement)"))
    check('Teclado: Tab se mantiene dentro del visor', all(inside))
    pg.keyboard.press('Escape'); pg.wait_for_timeout(400)
    s = pg.evaluate(LB)
    foc = pg.evaluate("document.activeElement.dataset.caption")
    check('Escape cierra, libera el fondo y devuelve el foco a la foto vista', not s['open'] and not s['locked'] and foc == 'Experiencia THE GENTLEMAN', foc)
    # Teclado puro: Enter sobre una foto
    pg.focus('.gallery__item--1 .gallery__link'); pg.keyboard.press('Enter'); pg.wait_for_timeout(500)
    check('Teclado: Enter sobre una foto abre el visor', pg.evaluate(LB)['open'] and pg.evaluate(LB)['counter'] == '1 / 8')
    pg.mouse.click(640, 25); pg.wait_for_timeout(400)
    check('Tocar el fondo oscuro cierra el visor', not pg.evaluate(LB)['open'])
    pg.focus('.gallery__item--1 .gallery__link'); pg.keyboard.press('Shift+Tab'); pg.keyboard.press('Tab')
    check('Foco visible en las fotos', pg.evaluate("getComputedStyle(document.activeElement).outlineStyle") == 'solid')
    pg.context.close()

    # ---------- 7. Responsive móvil y tablet ----------
    for w, h in ((360, 740), (390, 844), (412, 915), (430, 932), (768, 1024), (1920, 1080)):
        pg = page(viewport={'width': w, 'height': h}, device_scale_factor=2 if w < 1000 else 1, has_touch=w < 1000, is_mobile=w < 600)
        scroll_gallery(pg)
        R = pg.evaluate(RECTS_JS)
        check(f'{w}px: sin scroll horizontal', not pg.evaluate('document.documentElement.scrollWidth > innerWidth'))
        filled = pg.evaluate("[...document.querySelectorAll('.gallery__link')].map(a=>{const i=a.querySelector('img').getBoundingClientRect(),r=a.getBoundingClientRect();return Math.abs(i.height-r.height)<1.5&&Math.abs(i.width-r.width)<1.5})")
        check(f'{w}px: cada foto llena su celda (sin huecos)', all(filled), str(filled))
        if w < 1000:
            full = [round(R[i]['w']) for i in (0, 3, 6, 7)]
            pairs = [round(R[i]['w']) for i in (1, 2, 4, 5)]
            check(f'{w}px: fotos 1, 4, 7 y 8 a todo el ancho; el resto en parejas', len(set(full)) == 1 and len(set(pairs)) == 1 and full[0] > 2 * pairs[0] - 1,
                  f'completas {full[0]}px · parejas {pairs[0]}px')
            check(f'{w}px: fotos grandes y reconocibles (parejas ≥ 150 px)', min(pairs) >= 150)
        fonts = pg.evaluate("Math.min(...[...document.querySelectorAll('#galeria p, #galeria h2')].map(e=>parseFloat(getComputedStyle(e).fontSize)))")
        check(f'{w}px: letra mínima ≥ 12px', fonts >= 12, f'{fonts}px')
        if w in (360, 412, 768, 1920):
            section_shot(pg, f'{OUT}/galeria-{w}.png', w)
        pg.context.close()

    # ---------- Lightbox en Android simulado (táctil) ----------
    pg = page(**p.devices['Pixel 7'])
    scroll_gallery(pg)
    pg.evaluate("document.querySelector('.gallery__item--2').scrollIntoView({block:'center'})"); pg.wait_for_timeout(300)
    pg.tap('.gallery__item--2 .gallery__link'); pg.wait_for_timeout(700)
    check('Android: tocar una foto abre el visor', pg.evaluate(LB)['open'] and pg.evaluate(LB)['counter'] == '2 / 8')
    btn = pg.evaluate("[...document.querySelectorAll('.lightbox__btn')].map(b=>{const r=b.getBoundingClientRect();return [Math.round(r.width),Math.round(r.height),r.bottom<=innerHeight&&r.right<=innerWidth&&r.top>=0&&r.left>=0]})")
    check('Android: controles ≥ 48px y dentro de la pantalla', all(w_ >= 48 and h_ >= 48 and inside for w_, h_, inside in btn), str(btn))
    img_box = pg.evaluate("(()=>{const r=document.querySelector('.lightbox__image').getBoundingClientRect(),b=[...document.querySelectorAll('.lightbox__btn')].map(x=>x.getBoundingClientRect());return b.every(x=>x.top>=r.bottom||x.bottom<=r.top||x.left>=r.right||x.right<=r.left)})()")
    check('Android: los botones no tapan la foto', img_box)
    pg.screenshot(path=f'{OUT}/lightbox-pixel7.png')
    pg.evaluate('''(() => {const d=document.querySelector('[data-lightbox-dialog]');
      d.dispatchEvent(new PointerEvent('pointerdown',{pointerType:'touch',clientX:320,clientY:400,bubbles:true}));
      d.dispatchEvent(new PointerEvent('pointerup',{pointerType:'touch',clientX:120,clientY:400,bubbles:true}));})()''')
    pg.wait_for_timeout(300)
    check('Android: deslizar a la izquierda → siguiente (3 / 8)', pg.evaluate(LB)['counter'] == '3 / 8')
    pg.tap('[data-lightbox-next]'); pg.wait_for_timeout(200)
    check('Android: tocar "siguiente" → 4 / 8', pg.evaluate(LB)['counter'] == '4 / 8')
    pg.tap('[data-lightbox-close]'); pg.wait_for_timeout(400)
    check('Android: tocar "cerrar" cierra y libera el fondo', not pg.evaluate(LB)['open'] and not pg.evaluate(LB)['locked'])
    pg.context.close()

    # ---------- Movimiento reducido y sin JavaScript ----------
    pg = page(viewport={'width': 412, 'height': 839}, reduced_motion='reduce')
    check('Movimiento reducido: galería visible sin esperar', pg.evaluate("[...document.querySelectorAll('#galeria [data-reveal]')].every(e=>getComputedStyle(e).opacity==='1')"))
    pg.evaluate("document.querySelector('.gallery__item--1').scrollIntoView()"); pg.click('.gallery__item--1 .gallery__link'); pg.wait_for_timeout(100)
    dur = pg.evaluate("getComputedStyle(document.querySelector('[data-lightbox-dialog]')).animationDuration")
    check('Movimiento reducido: visor sin animación', float(dur[:-1]) < 0.001, dur)
    pg.context.close()
    pg = page(viewport={'width': 412, 'height': 839}, java_script_enabled=False)
    r = pg.evaluate("[...document.querySelectorAll('.gallery__link')].every(a=>a.getAttribute('href').endsWith('-1536.webp'))")
    check('Sin JavaScript: cada foto enlaza a su versión grande', r)
    pg.context.close()

    check('Sin errores de JavaScript ni recursos rotos', not errors, '; '.join(errors[:3]))
    b.close()

ok = sum(r[0] for r in results)
for r in results:
    print(('OK   ' if r[0] else 'FALLA'), r[1], ('· ' + r[2]) if r[2] else '')
print(f'\n{ok}/{len(results)} pruebas superadas')
