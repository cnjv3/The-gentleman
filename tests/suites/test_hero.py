from playwright.sync_api import sync_playwright
from PIL import Image
import io, sys

URL = 'http://localhost:8771/'
OUT = sys.argv[1]
results = []
def check(name, cond, detail=''):
    results.append((bool(cond), name, detail))

def lum(rgb):
    c = [v / 255 for v in rgb[:3]]
    c = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
def ratio(a, b):
    x, y = sorted([lum(a), lum(b)], reverse=True)
    return (x + 0.05) / (y + 0.05)

IVORY = (242, 239, 231); GOLD = (166, 138, 96)
# texto → (selector, color del texto, mínimo exigido)
TEXTS = [('.hero__eyebrow span', (215, 200, 175), 4.5), ('.hero__title', IVORY, 3.0),
         ('.hero__text', IVORY, 4.5), ('.hero__credit', (225, 222, 214), 4.5)]

def worst_contrast(pg):
    """Oculta los textos, captura el fondo real (foto + degradado) y busca
    el píxel más claro detrás de cada texto."""
    pg.add_style_tag(content='.hero__content *, .hero__credit {color: transparent !important}')
    pg.wait_for_timeout(100)
    shot = Image.open(io.BytesIO(pg.screenshot())).convert('RGB')
    dpr = pg.evaluate('devicePixelRatio')
    out = {}
    for sel, col, need in TEXTS:
        r = pg.evaluate(f"(() => {{const b=document.querySelector('{sel}').getBoundingClientRect();return [b.x,b.y,b.width,b.height]}})()")
        box = [int(v * dpr) for v in (r[0], r[1], r[0] + r[2], r[1] + r[3])]
        crop = shot.crop(box)
        # Percentil 98 del brillo para ignorar píxeles aislados
        px = sorted(crop.getdata(), key=lum)
        bright = px[int(len(px) * 0.98) - 1] if px else (0, 0, 0)
        out[sel] = (round(ratio(col, bright), 2), need)
    pg.reload(); pg.wait_for_timeout(2200)
    return out

SIZES = [
    ('360x740', dict(viewport={'width': 360, 'height': 740}, device_scale_factor=3, is_mobile=True, has_touch=True)),
    ('pixel7-412', None),
    ('motorola-horizontal', dict(viewport={'width': 915, 'height': 360}, device_scale_factor=2.6, is_mobile=True, has_touch=True)),
    ('768x1024', dict(viewport={'width': 768, 'height': 1024}, device_scale_factor=2)),
    ('1024x768', dict(viewport={'width': 1024, 'height': 768})),
    ('1280x800', dict(viewport={'width': 1280, 'height': 800})),
    ('1920x1080', dict(viewport={'width': 1920, 'height': 1080})),
]

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome')
    errors = []
    for name, opts in SIZES:
        opts = opts or p.devices['Pixel 7']
        ctx = b.new_context(**opts)
        pg = ctx.new_page()
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.on('response', lambda r: r.status >= 400 and not r.url.endswith('/favicon.ico') and errors.append(f'{r.status} {r.url}'))
        pg.add_init_script('''
          window.__cls = 0; window.__lcp = null;
          new PerformanceObserver(l => l.getEntries().forEach(e => { if (!e.hadRecentInput) window.__cls += e.value })).observe({type:'layout-shift', buffered:true});
          new PerformanceObserver(l => { const e=l.getEntries().at(-1); window.__lcp = {t:e.startTime, el:e.element && (e.element.className||e.element.tagName)} }).observe({type:'largest-contentful-paint', buffered:true});
        ''')
        pg.goto(URL, wait_until='load'); pg.wait_for_timeout(2200)
        m = pg.evaluate('''() => {
          const h=document.querySelector('.hero'), hd=document.querySelector('[data-header]'), img=document.querySelector('.hero__image');
          const c=document.querySelector('.hero__content').getBoundingClientRect(), hr=h.getBoundingClientRect();
          const btns=[...document.querySelectorAll('.hero__actions .btn')].map(x=>{const r=x.getBoundingClientRect();return {h:Math.round(r.height), href:x.getAttribute('href'), txt:x.textContent}});
          const credit=document.querySelector('.hero__credit').getBoundingClientRect(), act=document.querySelector('.hero__actions').getBoundingClientRect();
          return {vh:innerHeight, total:Math.round(hd.offsetHeight+h.offsetHeight), src:img.currentSrc.split('/').pop(),
                  contentInside: c.top>=hr.top && c.bottom<=hr.bottom, btns, overflow:document.documentElement.scrollWidth>innerWidth,
                  creditClear: credit.top >= act.bottom || credit.left >= act.right,
                  h1s: document.querySelectorAll('h1').length, cls: window.__cls, lcp: window.__lcp};
        }''')
        portrait = pg.viewport_size['height'] > pg.viewport_size['width']
        check(f'{name}: imagen correcta ({m["src"]})', ('mobile' in m['src']) == portrait)
        if name != 'motorola-horizontal':
            check(f'{name}: header + hero = una pantalla', abs(m['total'] - m['vh']) <= 1, f"{m['total']} / {m['vh']}px")
        else:
            check(f'{name}: el hero crece y nada queda cortado', m['contentInside'], f"alto total {m['total']}px")
        check(f'{name}: contenido dentro del hero', m['contentInside'])
        check(f'{name}: sin scroll horizontal', not m['overflow'])
        check(f'{name}: leyenda sin chocar con los botones', m['creditClear'])
        check(f'{name}: botones ≥ 48px y destinos correctos', all(x['h'] >= 48 for x in m['btns']) and [x['href'] for x in m['btns']] == ['#reservas', '#servicios'], str(m['btns']))
        check(f'{name}: sin saltos de diseño (CLS)', m['cls'] < 0.01, f"CLS {m['cls']:.3f}")
        pg.screenshot(path=f'{OUT}/hero-{name}.png')
        cs = worst_contrast(pg)
        for sel, (r, need) in cs.items():
            check(f'{name}: contraste {sel}', r >= need, f'{r}:1 (mínimo {need})')
        if name == 'pixel7-412':
            check('Un solo h1 en la página', m['h1s'] == 1)
            check('LCP medido', m['lcp'] is not None, f"{m['lcp']['t']:.0f} ms · {m['lcp']['el']}" if m['lcp'] else '')
            sizes = pg.evaluate("performance.getEntriesByType('resource').filter(r=>r.name.includes('/hero/')).map(r=>r.name.split('/').pop()+' '+Math.round(r.encodedBodySize/1024)+'KB')")
            check('Android descarga solo 1 imagen del hero', len(sizes) == 1, ', '.join(sizes))
            pg.focus('.btn--outline')
            pg.screenshot(path=f'{OUT}/hero-foco.png', clip={'x': 0, 'y': 500, 'width': 412, 'height': 339})
            # Letra grande de Android (130%)
            pg.add_style_tag(content='html{font-size:130%}'); pg.wait_for_timeout(200)
            big = pg.evaluate("(()=>{const c=document.querySelector('.hero__content').getBoundingClientRect(),h=document.querySelector('.hero').getBoundingClientRect();return {inside:c.top>=h.top&&c.bottom<=h.bottom, ov:document.documentElement.scrollWidth>innerWidth}})()")
            check('Letra al 130%: nada cortado ni scroll horizontal', big['inside'] and not big['ov'])
            pg.screenshot(path=f'{OUT}/hero-letra-130.png', full_page=True)
        if name == '1280x800':
            sizes = pg.evaluate("performance.getEntriesByType('resource').filter(r=>r.name.includes('/hero/')).map(r=>r.name.split('/').pop()+' '+Math.round(r.encodedBodySize/1024)+'KB')")
            check('Escritorio descarga solo 1 imagen del hero', len(sizes) == 1, ', '.join(sizes))
            order = []
            for _ in range(12):
                pg.keyboard.press('Tab'); order.append(pg.evaluate("document.activeElement.textContent.trim()"))
            check('Teclado: tras el menú siguen Reservar ahora → Explorar servicios', order[9:11] == ['Reservar ahora', 'Explorar servicios'], ' → '.join(order[8:11]))
        ctx.close()

    # Movimiento reducido: todo visible de inmediato
    ctx = b.new_context(viewport={'width': 412, 'height': 839}, reduced_motion='reduce')
    pg = ctx.new_page(); pg.goto(URL, wait_until='load'); pg.wait_for_timeout(50)
    op = pg.evaluate("[...document.querySelectorAll('.hero__eyebrow,.hero__title,.hero__text,.hero__actions')].map(e=>+getComputedStyle(e).opacity)")
    check('Movimiento reducido: textos visibles al instante', all(o == 1 for o in op), str(op))
    ctx.close()
    check('Sin errores de JavaScript ni recursos rotos', not errors, '; '.join(errors))
    b.close()

ok = sum(r[0] for r in results)
for r in results:
    print(('OK   ' if r[0] else 'FALLA'), r[1], ('· ' + r[2]) if r[2] else '')
print(f'\n{ok}/{len(results)} pruebas superadas')
