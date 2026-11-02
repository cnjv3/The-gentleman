"""Etapa 11: SEO, íconos, carga de módulos, imágenes, enlaces, teclado y seguridad."""
from playwright.sync_api import sync_playwright
from PIL import Image
from urllib.parse import urlparse
import sys, re, os, glob, html as H

URL = 'http://localhost:8771/'
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # raíz del repositorio (calculada desde este archivo)
OUT = sys.argv[1]
LIVE = 'https://cnjv3.github.io/The-gentleman/'
results = []
def check(name, cond, detail=''):
    results.append((bool(cond), name, detail))

src = open(f'{REPO}/index.html', encoding='utf-8').read()
head = src[:src.index('</head>')]
meta = lambda attr, key: (re.search(rf'<meta {attr}="{re.escape(key)}" content="([^"]*)"', head) or [None, None])[1]

# ---------- 1. SEO y vista previa ----------
desc = meta('name', 'description')
check('Meta description presente, 50–160 caracteres', desc and 50 <= len(desc) <= 160, f'{len(desc or "")} caracteres')
check('La descripción declara que es un sitio de demostración', desc and 'demostración' in desc)
canon = (re.search(r'<link rel="canonical" href="([^"]+)"', head) or [None, None])[1]
check('Canonical absoluta a la dirección publicada', canon == LIVE, str(canon))
og = {k: meta('property', k) for k in ('og:type', 'og:locale', 'og:site_name', 'og:title', 'og:description', 'og:url', 'og:image', 'og:image:width', 'og:image:height', 'og:image:alt')}
check('Open Graph completo (10 propiedades)', all(og.values()), str([k for k, v in og.items() if not v]))
check('og:url coincide con la canonical', og['og:url'] == canon)
img_rel = (og['og:image'] or '').replace(LIVE, '')
img_path = f'{REPO}/{img_rel}'
check('og:image apunta a un archivo del repositorio', og['og:image'].startswith(LIVE) and os.path.isfile(img_path), img_rel)
if os.path.isfile(img_path):
    im = Image.open(img_path)
    check('og:image en JPEG 1200×630 y < 300 KB (compatible con WhatsApp)', im.format == 'JPEG' and im.size == (1200, 630) and os.path.getsize(img_path) < 300 * 1024 and og['og:image:width'] == '1200' and og['og:image:height'] == '630', f'{im.format} {im.size} {os.path.getsize(img_path)//1024} KB')
check('Tarjeta para redes: summary_large_image', meta('name', 'twitter:card') == 'summary_large_image')
check('theme-color marfil de la paleta', meta('name', 'theme-color') == '#F2EFE7')
check('Título conciso (≤ 60 caracteres)', 0 < len(re.search(r'<title>([^<]+)</title>', head).group(1)) <= 60)
check('Sin robots.txt ni sitemap.xml en la carpeta del proyecto (no funcionarían fuera de la raíz del dominio)', not os.path.exists(f'{REPO}/robots.txt') and not os.path.exists(f'{REPO}/sitemap.xml'))

# ---------- 2. Rutas: toda referencia local existe ----------
refs = set()
for m in re.finditer(r'(?:src|href)="([^"#][^"]*)"', src):
    refs.add(m.group(1))
for m in re.finditer(r'srcset="([^"]+)"', src):
    refs.update(x.strip().split(' ')[0] for x in m.group(1).split(','))
for m in re.finditer(r'data-avif="([^"]+)"', src):
    refs.add(m.group(1))
local = sorted(r for r in refs if not re.match(r'^(https?:|mailto:|tel:)', r))
missing = [r for r in local if not os.path.isfile(f'{REPO}/{r.split("?")[0]}')]
check(f'Todas las referencias locales existen ({len(local)})', not missing, str(missing))
check('Rutas relativas (ninguna empieza con "/")', not any(r.startswith('/') for r in local))
case_bad = [r for r in local if r.split('?')[0] not in [os.path.relpath(f, REPO) for f in glob.glob(f'{REPO}/**/*', recursive=True)]]
check('Mayúsculas/minúsculas exactas (GitHub Pages las distingue)', not case_bad, str(case_bad))

# ---------- 3. Seguridad básica (código fuente) ----------
js_src = {f: open(f, encoding='utf-8').read() for f in glob.glob(f'{REPO}/js/**/*.js', recursive=True)}
risky = [os.path.basename(f) for f, t in js_src.items() if re.search(r'innerHTML|outerHTML|insertAdjacentHTML|document\.write|\beval\(|new Function', t)]
check('JS sin inserción de HTML ni eval', not risky, str(risky))
blank = re.findall(r'<a [^>]*target="_blank"[^>]*>', src)
check(f'Enlaces target="_blank" del HTML con rel="noopener" ({len(blank)})', all('noopener' in a for a in blank))
check('Sin credenciales ni claves en el código', not re.search(r'(api[_-]?key|secret|password|token)\s*[:=]', src + ''.join(js_src.values()) + open(f'{REPO}/css/styles.css').read(), re.I))
check('Validación de URLs https en contacto (safeUrl) y de URLs de inserción de mapas', 'const safeUrl' in js_src[f'{REPO}/js/modules/contact.js'] and 'EMBED_URL' in js_src[f'{REPO}/js/modules/contact.js'])

# ---------- 4. Configuración intacta ----------
cfg = js_src[f'{REPO}/js/config.js']
block = cfg[cfg.index('export const CONTACT'):]; block = block[:block.index('\n};')]
fields = dict(re.findall(r"\n  (\w+): ([^,\n]+),", block))
check('CONTACT sin datos inventados e isDemo: true', all(v == "''" for k, v in fields.items() if v.startswith("'")) and fields.get('isDemo') == 'true')
check("BUSINESS y BOOKING_HOURS intactos (56900000000 · 10:00–20:00 · 30 min)", "whatsappNumber: '56900000000'" in cfg and "open: '10:00'" in cfg and "close: '20:00'" in cfg and 'slotMinutes: 30' in cfg)

# ---------- 5. Navegador ----------
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome')
    errors = []
    def page(**kw):
        ctx = b.new_context(**kw); pg = ctx.new_page()
        pg.route('**://fonts.g*/**', lambda r: r.abort()); pg.route('**://www.google.com/**', lambda r: r.abort())
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.on('console', lambda m: m.type == 'error' and 'Failed to load resource' not in m.text and errors.append(m.text))
        reqs = []
        pg.on('request', lambda r: reqs.append(r.url))
        pg.on('response', lambda r: r.status >= 400 and 'fonts.g' not in r.url and errors.append(f'{r.status} {r.url}'))
        pg.goto(URL, wait_until='load'); pg.wait_for_timeout(600)
        return pg, reqs

    pg, reqs = page(viewport={'width': 412, 'height': 915}, device_scale_factor=2.625, is_mobile=True, has_touch=True)
    icons = pg.evaluate("[...document.querySelectorAll('link[rel~=icon],link[rel=apple-touch-icon]')].map(l=>l.href)")
    check('Íconos declarados y servidos (favicon 32 px y apple-touch-icon 180 px)', len(icons) == 2 and all(Image.open(f"{REPO}/{urlparse(u).path.lstrip('/')}").size in ((32, 32), (180, 180)) for u in icons))
    check('Sin petición a /favicon.ico en la raíz (evita el 404 de GitHub Pages)', not any(urlparse(u).path == '/favicon.ico' for u in reqs))
    js = [u for u in reqs if '.js' in u]
    names = sorted(urlparse(u).path.split('/')[-1] for u in js)
    check('Cada módulo JS se descarga una sola vez (preload = import)', len(names) == len(set(names)) == 10, str(names))
    graph = set()
    for f, t in js_src.items():
        for m in re.findall(r"from '(\.{1,2}/[^']+)'", t):
            graph.add(os.path.normpath(os.path.join(os.path.dirname(os.path.relpath(f, REPO)), m.split('?')[0])))
    pre = set(re.findall(r'<link rel="modulepreload" href="([^"?]+)', head))
    check(f'Todo módulo importado tiene modulepreload ({len(graph)})', graph == pre, f'faltan {graph - pre} · sobran {pre - graph}')
    starts = pg.evaluate("performance.getEntriesByType('resource').filter(r=>r.name.includes('.js')).map(r=>r.startTime)")
    check('Módulos descargados en paralelo (sin cascada: todos inician en < 50 ms entre sí)', max(starts) - min(starts) < 50, f'{max(starts)-min(starts):.0f} ms')
    pg.evaluate("document.documentElement.style.scrollBehavior='auto'")
    for y in range(0, pg.evaluate('document.body.scrollHeight'), 500):
        pg.evaluate(f'scrollTo(0,{y})'); pg.wait_for_timeout(100)
    pg.wait_for_timeout(1200)
    gal = pg.evaluate("""(()=>{const out=[]; for(const i of document.querySelectorAll('.gallery__link img')){const r=i.getBoundingClientRect(); const mm=i.currentSrc.match(/-(v?)(\\d+)\\.avif/), ratio=mm[1]?0.8:1.5; const need=Math.max(r.width, r.height*ratio)*devicePixelRatio; const w=+mm[2]; out.push({f:i.currentSrc.split('/').pop(), need:Math.round(need), w, ok: w>=need*0.9 || w===1536 || (mm[1]&&w===820)})} return out})()""")
    check('Galería móvil: cada foto con resolución suficiente para su celda recortada (≥ 90 %)', all(g['ok'] for g in gal), str([(g['f'], g['need']) for g in gal if not g['ok']]))
    check('Galería móvil: ninguna foto descarga 1536 px si basta con menos', not [g for g in gal if g['w'] == 1536 and g['need'] <= 1080], str([g['f'] for g in gal if g['w'] == 1536]))
    kb = pg.evaluate("Math.round(performance.getEntriesByType('resource').filter(r=>r.name.includes('/gallery/')).reduce((a,r)=>a+r.encodedBodySize,0)/1024)")
    check('Galería móvil: peso no mayor que en main (488 KB, mismo método), ahora sin fotos borrosas', kb <= 488, f'{kb} KB')
    pg.click('.gallery__item--1 .gallery__link'); pg.wait_for_timeout(600)
    check('El visor sigue mostrando la versión de 1536 px', pg.evaluate("document.querySelector('[data-lightbox-image]').currentSrc.endsWith('01-corte-clasico-1536.avif')"))
    pg.keyboard.press('Escape'); pg.context.close()

    # Escritorio 1440: la galería usa versiones adecuadas
    pg, reqs = page(viewport={'width': 1440, 'height': 900})
    pg.evaluate("document.documentElement.style.scrollBehavior='auto'")
    for y in range(0, pg.evaluate('document.body.scrollHeight'), 600):
        pg.evaluate(f'scrollTo(0,{y})'); pg.wait_for_timeout(80)
    pg.wait_for_timeout(1200)
    sm = pg.evaluate("""(()=>{const out=[]; for(const i of document.querySelectorAll('.gallery__link img')){const r=i.getBoundingClientRect(); const mm=i.currentSrc.match(/-(v?)(\\d+)\\.avif/), ratio=mm[1]?0.8:1.5; const need=Math.max(r.width, r.height*ratio)*devicePixelRatio; const w=+mm[2]; out.push({f:i.currentSrc.split('/').pop(), need:Math.round(need), w, ok: w>=need*0.9 || w===1536 || (mm[1]&&w===820)})} return out})()""")
    check('Escritorio 1440: cada foto con resolución suficiente para su celda recortada (≥ 90 %)', all(g['ok'] for g in sm), str([(g['f'], g['need'], g['w']) for g in sm if not g['ok']]))

    pg.context.close()
    pg, reqs = page(viewport={'width': 768, 'height': 1024}, device_scale_factor=2, has_touch=True)
    pg.evaluate("document.documentElement.style.scrollBehavior='auto'")
    for y in range(0, pg.evaluate('document.body.scrollHeight'), 600):
        pg.evaluate(f'scrollTo(0,{y})'); pg.wait_for_timeout(80)
    pg.wait_for_timeout(1200)
    tb = pg.evaluate("""(()=>{const out=[]; for(const i of document.querySelectorAll('.gallery__link img')){const r=i.getBoundingClientRect(); const mm=i.currentSrc.match(/-(v?)(\\d+)\\.avif/), ratio=mm[1]?0.8:1.5; const need=Math.max(r.width, r.height*ratio)*devicePixelRatio; const w=+mm[2]; out.push({f:i.currentSrc.split('/').pop(), need:Math.round(need), w, ok: w>=need*0.9 || w===1536 || (mm[1]&&w===820)})} return out})()""")
    check('Tablet 768: cada foto con resolución suficiente (incluida la 4, a todo el ancho)', all(g['ok'] for g in tb), str([(g['f'], g['need'], g['w']) for g in tb if not g['ok']]))
    pg.context.close()
    # Variantes, versiones verticales y peso por ancho
    LIM = {360: 400, 412: 400, 768: 640, 1440: 400}
    for w, h, d in ((360, 740, 3), (412, 915, 2.625), (768, 1024, 2), (1440, 900, 1)):
        ctx2 = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=d, has_touch=w < 1000); pq = ctx2.new_page()
        pq.route('**://fonts.g*/**', lambda r: r.abort())
        got = []
        pq.on('requestfinished', lambda r: '/gallery/' in r.url and got.append((r.url.split('/')[-1], r.sizes()['responseBodySize'])))
        pq.goto(URL); pq.wait_for_timeout(300); pq.evaluate("document.documentElement.style.scrollBehavior='auto'")
        for y in range(0, pq.evaluate('document.body.scrollHeight'), 500):
            pq.evaluate(f'scrollTo(0,{y})'); pq.wait_for_timeout(90)
        pq.wait_for_timeout(1300)
        gal_files = pq.evaluate("[...document.querySelectorAll('.gallery__link img')].map(i=>i.currentSrc.split('/').pop())")
        decor = pq.evaluate("(i=>i&&i.currentSrc?i.currentSrc.split('/').pop():null)(document.querySelector('.booking__decor img'))")
        others = [f for f, _ in got if f not in gal_files and f != decor]
        check(f'{w}px: una sola variante por foto (sin descargas extra)', not others and len(set(gal_files)) == 8, str(others))
        pairs = [gal_files[i] for i in (1, 2, 4, 5)]
        if w < 1024:
            check(f'{w}px: fotos en pareja con versión vertical recortada (sin descargar lo que no se ve)', all(re.search(r'-v\d+\.avif$', f) for f in pairs), str(pairs))
        else:
            check(f'{w}px: escritorio sin versiones verticales', not any('-v' in f.rsplit('-', 1)[1] for f in gal_files), str(gal_files))
        kb = round(sum(sz for f, sz in got if f in gal_files) / 1024)
        check(f'{w}px: peso de la galería ≤ {LIM[w]} KB', kb <= LIM[w], f'{kb} KB')
        ctx2.close()

    pg, reqs = page(viewport={'width': 1440, 'height': 900})

    # Teclado: recorrido completo de la página con foco visible
    pg.evaluate("scrollTo(0,0); document.activeElement.blur()")
    stops, bad = [], []
    for _ in range(120):
        pg.keyboard.press('Tab')
        info = pg.evaluate('''() => {const e=document.activeElement; if(!e||e===document.body) return null; const s=getComputedStyle(e);
          return {k:(e.id||e.getAttribute('class')||e.tagName)+'|'+(e.getAttribute('href')||e.name||''), ring:s.outlineStyle!=='none'&&parseFloat(s.outlineWidth)>0}}''')
        if info is None or (stops and info['k'] == stops[0]): break
        if not stops or info['k'] != stops[-1]:
            stops.append(info['k'])
            if not info['ring']: bad.append(info['k'])
    check(f'Teclado: recorrido completo de la página ({len(stops)} elementos) con foco visible en todos', len(stops) >= 40 and not bad, str(bad[:5]))
    check('Teclado: el recorrido llega hasta el footer', any('site-footer__top' in s for s in stops))
    pg.context.close()

    # Sin JavaScript: el contenido principal sigue disponible
    ctx = b.new_context(viewport={'width': 412, 'height': 915}, java_script_enabled=False); pgn = ctx.new_page(); pgn.goto(URL); pgn.wait_for_timeout(1500)  # animación de entrada del hero (CSS)
    check('Sin JavaScript: h1, servicios, galería y footer visibles', pgn.evaluate("['h1','#servicios .service-card','.gallery__item','.site-footer'].every(s=>{const e=document.querySelector(s);return e&&e.getBoundingClientRect().height>0&&getComputedStyle(e).opacity!=='0'})"))
    ctx.close()

    check('Sin errores de consola ni recursos rotos', not errors, '; '.join(errors[:3]))
    b.close()

ok = sum(r[0] for r in results)
for r in results:
    print(('OK   ' if r[0] else 'FALLA'), r[1], ('· ' + r[2]) if r[2] else '')
print(f'\n{ok}/{len(results)} pruebas superadas')
