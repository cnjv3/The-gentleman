"""Pruebas del arreglo: versionado de archivos, íconos con tamaño propio
y maquetación móvil de Reservas en anchos de Motorola Edge 50 Fusion."""
from playwright.sync_api import sync_playwright
import sys, re, glob, subprocess, os

URL = 'http://localhost:8771/'
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # raíz del repositorio (calculada desde este archivo)
OUT = sys.argv[1]
results = []
def check(name, cond, detail=''):
    results.append((bool(cond), name, detail))

# ---------- 1. Versionado: todas las URLs locales de CSS/JS con la misma versión ----------
html = open(f'{REPO}/index.html', encoding='utf-8').read()
refs = re.findall(r'(?:href|src)="((?!https?:)[^"]+\.(?:css|js)(?:\?[^"]*)?)"', html)
for f in glob.glob(f'{REPO}/js/**/*.js', recursive=True):
    refs += re.findall(r"from '(\.{1,2}/[^']+)'", open(f, encoding='utf-8').read())
versions = {re.search(r'\?v=([\w.-]+)$', r).group(1) if re.search(r'\?v=([\w.-]+)$', r) else None for r in refs}
check('Versionado: todas las referencias a CSS/JS llevan ?v=', None not in versions, ', '.join(r for r in refs if '?v=' not in r))
check('Versionado: una sola versión en todo el proyecto', len(versions) == 1, str(versions))
check(f'Versionado: se revisaron {len(refs)} referencias (CSS, JS de entrada e imports)', len(refs) >= 9, str(len(refs)))

ICONS_JS = "[...document.querySelectorAll('#reservas svg, #servicios svg, .lightbox svg')].map(s=>{const r=s.getBoundingClientRect();return Math.max(r.width,r.height)})"
MOTO = dict(device_scale_factor=2.625, is_mobile=True, has_touch=True)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome')
    errors = []
    def page(route=None, **kw):
        ctx = b.new_context(**kw); pg = ctx.new_page()
        if route: pg.route(*route)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(URL, wait_until='load'); pg.wait_for_timeout(400)
        return pg

    # ---------- 2. Resistencia: si el CSS no carga o es una copia antigua ----------
    pg = page(route=('**/css/styles.css*', lambda r: r.abort()), viewport={'width': 412, 'height': 915}, **MOTO)
    sizes = pg.evaluate("[...document.querySelectorAll('svg')].map(s=>{const r=s.getBoundingClientRect();return Math.max(r.width,r.height)})")
    check('Sin CSS: ningún ícono SVG crece (todos ≤ 24 px)', max(sizes) <= 24, f'máximo {max(sizes):.0f}px de {len(sizes)} íconos')
    pg.context.close()
    old_css = subprocess.run(['git', '-C', REPO, 'show', 'd4daf3e:css/styles.css'], capture_output=True, text=True).stdout
    pg = page(route=('**/css/styles.css*', lambda r: r.fulfill(body=old_css, content_type='text/css')), viewport={'width': 412, 'height': 915}, **MOTO)
    sizes = pg.evaluate("[...document.querySelectorAll('#reservas svg')].map(s=>s.getBoundingClientRect().width)")
    check('Con el CSS anterior (caso de la captura): íconos de reservas ≤ 24 px', max(sizes) <= 24, f'antes del arreglo: 375px · ahora máx. {max(sizes):.0f}px')
    pg.context.close()

    # ---------- 3. Maquetación móvil de Reservas (anchos del Motorola) ----------
    for w in (360, 384, 390, 412, 430):
        pg = page(viewport={'width': w, 'height': 915}, **MOTO)
        loaded = pg.evaluate("[...document.styleSheets].some(s=>s.href&&s.href.includes('styles.css?v='))")
        pg.evaluate("document.documentElement.style.scrollBehavior='auto'; document.querySelector('#reservas').scrollIntoView()"); pg.wait_for_timeout(1300)
        m = pg.evaluate('''() => {
          const R=e=>e.getBoundingClientRect(), form=R(document.querySelector('#booking-form'));
          const fields=[...document.querySelectorAll('#booking-form .field')];
          const rows=fields.map(f=>{const l=R(f.querySelector('.field__label')), c=R(f.querySelector('.field__control')), i=R(f.querySelector('.field__input')), ic=R(f.querySelector('.field__icon'));
             return {labelAbove:l.bottom<=c.top+0.5, alignLeft:Math.abs(l.left-c.left)<1, h:i.height, iconW:ic.width, iconH:ic.height,
                     iconInside:ic.left>=i.left&&ic.right<=i.right&&ic.top>=i.top&&ic.bottom<=i.bottom, top:R(f).top, bottom:R(f).bottom, w:i.width}});
          const full=rows.filter((_,k)=>!fields[k].closest('.booking-form__row')).every(r=>Math.abs(r.w-form.width)<1);
          const gaps=[]; for(let k=1;k<rows.length;k++){const g=rows[k].top-rows[k-1].bottom; if(g>0) gaps.push(Math.round(g));}
          const sumIcons=[...document.querySelectorAll('.booking-summary__icon')].map(s=>Math.round(R(s).width));
          return {rows, full, gaps, sumIcons, title:Math.round(R(document.querySelector('.booking-summary__title-icon')).width),
                  chevron:Math.round(R(document.querySelector('.field__chevron')).width),
                  summaryBelow:R(document.querySelector('.booking-summary')).top>=form.bottom, ov:document.documentElement.scrollWidth>innerWidth};
        }''')
        r = m['rows']
        check(f'{w}px: CSS versionado cargado', loaded)
        check(f'{w}px: íconos de campos de 20×20 px y dentro del campo', all(x['iconW'] == 20 and x['iconH'] == 20 and x['iconInside'] for x in r), str({(x['iconW'], x['iconH']) for x in r}))
        check(f'{w}px: íconos del resumen 20 px, título 28 px, flecha 18 px', set(m['sumIcons']) == {20} and m['title'] == 28 and m['chevron'] == 18)
        check(f'{w}px: etiquetas encima de su campo y alineadas', all(x['labelAbove'] and x['alignLeft'] for x in r))
        check(f'{w}px: campos a todo el ancho del formulario', m['full'])
        check(f'{w}px: campos de 52 px de alto', all(abs(x['h'] - 52) < 1 for x in r if x['h'] < 100), str(sorted({round(x['h']) for x in r})))
        check(f'{w}px: espacios verticales proporcionados (16–40 px)', m['gaps'] and all(16 <= g <= 40 for g in m['gaps']), str(m['gaps']))
        check(f'{w}px: resumen debajo del formulario y sin scroll horizontal', m['summaryBelow'] and not m['ov'])
        if w in (360, 412):
            y = pg.evaluate("document.querySelector('#booking-title').getBoundingClientRect().top+scrollY")
            pg.evaluate(f"window.scrollTo(0,{y}-30)"); pg.wait_for_timeout(300)
            pg.screenshot(path=f'{OUT}/fix-formulario-{w}.png')
        pg.context.close()

    # ---------- 4. La sincronización y WhatsApp siguen funcionando ----------
    pg = page(viewport={'width': 412, 'height': 915}, **MOTO)
    pg.evaluate("window.__o=[]; window.open=(u)=>{window.__o.push(u); return null}; true")
    pg.fill('#booking-name', 'Ana'); pg.select_option('#booking-serviceId', index=1)
    d = pg.evaluate("(()=>{const t=new Date(Date.now()+7*864e5);return t.getFullYear()+'-'+String(t.getMonth()+1).padStart(2,'0')+'-'+String(t.getDate()).padStart(2,'0')})()")
    pg.fill('#booking-date', d); pg.select_option('#booking-time', '10:00')
    s = pg.evaluate("Object.fromEntries([...document.querySelectorAll('[data-summary]')].map(e=>[e.dataset.summary,e.textContent]))")
    check('Sincronización intacta tras el arreglo', s['name'] == 'Ana' and s['service'] == 'Corte Clásico' and s['price'] == '$12.000' and s['time'] == '10:00', str(s))
    pg.click('.booking-summary__submit'); pg.wait_for_timeout(200)
    check('WhatsApp intacto tras el arreglo', pg.evaluate("window.__o.length===1 && window.__o[0].startsWith('https://wa.me/56900000000?text=')"))
    pg.context.close()

    # ---------- 5. Escritorio sin cambios visuales en los íconos ----------
    pg = page(viewport={'width': 1280, 'height': 900})
    pg.evaluate("document.documentElement.style.scrollBehavior='auto'; document.querySelector('#reservas').scrollIntoView()"); pg.wait_for_timeout(1300)
    sz = pg.evaluate("[...document.querySelectorAll('.field__icon')].map(s=>Math.round(s.getBoundingClientRect().width))")
    check('Escritorio: íconos de campos siguen en 20 px', set(sz) == {20}, str(sz))
    pg.screenshot(path=f'{OUT}/fix-reservas-1280.png')
    pg.context.close()

    check('Sin errores de JavaScript', not errors, '; '.join(errors[:3]))
    b.close()

ok = sum(r[0] for r in results)
for r in results:
    print(('OK   ' if r[0] else 'FALLA'), r[1], ('· ' + r[2]) if r[2] else '')
print(f'\n{ok}/{len(results)} pruebas superadas')
