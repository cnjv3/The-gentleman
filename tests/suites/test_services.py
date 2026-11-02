from playwright.sync_api import sync_playwright
from urllib.parse import urlparse, parse_qs
import sys

URL = 'http://localhost:8771/'
OUT = sys.argv[1]
results = []
def check(name, cond, detail=''):
    results.append((bool(cond), name, detail))

EXPECTED = [
    ('Corte Clásico', 'Corte tradicional con técnica de precisión y acabado profesional.', '$12.000', '12000', '30 min', 'PT30M'),
    ('Arreglo de Barba', 'Perfilado, definición y cuidado de tu barba.', '$8.000', '8000', '20 min', 'PT20M'),
    ('Tratamiento Capilar', 'Limpieza profunda, hidratación y fortalecimiento del cabello.', '$15.000', '15000', '40 min', 'PT40M'),
    ('Cuidado Facial', 'Limpieza, exfoliación e hidratación para una piel más sana y fresca.', '$18.000', '18000', '40 min', 'PT40M'),
    ('Diseño Premium', 'Cortes con diseño personalizado, líneas, figuras o degradados especiales.', '$14.000', '14000', '40 min', 'PT40M'),
    ('Peinado y Styling', 'Asesoría y peinado con productos de alta calidad.', '$6.000', '6000', '15 min', 'PT15M'),
    ('Coloración', 'Cambio de tono, cobertura de canas y color personalizado.', '$22.000', '22000', '60 min', 'PT60M'),
    ('Ritual The Gentleman', 'Experiencia completa: corte, barba y cuidado facial.', '$28.000', '28000', '70 min', 'PT70M'),
]

CONTRAST_JS = r'''(sel) => {
 const p=c=>{const v=c.match(/[\d.]+/g).slice(0,3).map(Number);return c.startsWith('color(')?v.map(x=>x*255):v};
 const lum=a=>{const m=a.map(v=>{v/=255;return v<=0.04045?v/12.92:((v+0.055)/1.055)**2.4});return .2126*m[0]+.7152*m[1]+.0722*m[2]};
 const el=document.querySelector(sel), cs=getComputedStyle(el);
 let n=el, bg; while(n){const b=getComputedStyle(n).backgroundColor; if(!/rgba\(0, 0, 0, 0\)|transparent/.test(b)){bg=b;break} n=n.parentElement}
 const a=lum(p(cs.color)), b=lum(p(bg)); return +((Math.max(a,b)+.05)/(Math.min(a,b)+.05)).toFixed(2);
}'''

CARDS_JS = '''() => [...document.querySelectorAll('.service-card')].map(c => {
  const a=c.querySelector('.service-card__cta'), r=c.getBoundingClientRect(), ar=a.getBoundingClientRect();
  return {name:c.querySelector('h3').textContent.trim(), text:c.querySelector('.service-card__text').textContent.trim(),
          price:c.querySelector('data').textContent.trim(), value:c.querySelector('data').value,
          time:c.querySelector('time').textContent.trim(), dt:c.querySelector('time').getAttribute('datetime'),
          href:a.href, target:a.target, rel:a.rel, label:a.textContent.trim().replace(/\\s+/g,' '),
          x:Math.round(r.x), top:Math.round(r.top), h:Math.round(r.height), ctaTop:Math.round(ar.top), ctaH:Math.round(ar.height),
          ctaOverflow:a.scrollWidth>a.clientWidth+1,
          minFont:Math.min(...[...c.querySelectorAll('h3,p,a,time,data')].map(e=>parseFloat(getComputedStyle(e).fontSize)))};
})'''

def scroll_all(pg):
    pg.evaluate("document.querySelector('#servicios').scrollIntoView()"); pg.wait_for_timeout(400)
    for _ in range(12):
        pg.mouse.wheel(0, 500); pg.wait_for_timeout(120)
    pg.wait_for_timeout(1200)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome')
    errors = []
    def page(**kw):
        ctx = b.new_context(**kw); pg = ctx.new_page()
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.on('response', lambda r: r.status >= 400 and not r.url.endswith('/favicon.ico') and errors.append(f'{r.status} {r.url}'))
        pg.goto(URL, wait_until='load'); pg.wait_for_timeout(300)
        return pg

    # ---------- Contenido y WhatsApp (Android simulado) ----------
    pg = page(**p.devices['Pixel 7'])
    order = pg.evaluate("[...document.querySelectorAll('main > section')].map(s=>s.id)")
    check('Orden de secciones: inicio → nosotros → servicios', order[:3] == ['inicio', 'nosotros', 'servicios'], str(order))
    head = pg.evaluate("(()=>{const s=document.querySelector('#servicios');return [s.querySelector('.section-heading__eyebrow').textContent.trim(), s.querySelector('h2').textContent.trim(), s.querySelector('.section-heading__text').textContent.trim()]})()")
    check('Encabezado con etiqueta, título y descripción exactos',
          head == ['Nuestros servicios', 'Cortes y cuidado masculino', 'Servicios diseñados para realzar tu estilo, con la precisión, el cuidado y la experiencia que caracterizan a THE GENTLEMAN.'], str(head))
    st = pg.evaluate("[...document.querySelectorAll('#servicios [data-reveal]')].filter(e=>e.classList.contains('is-visible')).length")
    check('Antes de desplazarse: tarjetas aún no animadas', st == 0, f'{st} visibles')
    scroll_all(pg)
    cards = pg.evaluate(CARDS_JS)
    check('Exactamente 8 tarjetas', len(cards) == 8, str(len(cards)))
    for c, (n, t, pr, v, tm, dt) in zip(cards, EXPECTED):
        ok = (c['name'], c['text'], c['price'], c['value'], c['time'], c['dt']) == (n, t, pr, v, tm, dt)
        check(f'Tarjeta "{n}": nombre, descripción, precio y duración', ok, f"{c['price']} · {c['time']}")
        q = urlparse(c['href'])
        msg = parse_qs(q.query).get('text', [''])[0]
        good = (q.netloc == 'wa.me' and q.path == '/56900000000'
                and msg == f'Hola, me gustaría reservar el servicio de {n} en THE GENTLEMAN.'
                and c['target'] == '_blank' and 'noopener' in c['rel'])
        check(f'WhatsApp "{n}": número de demostración y mensaje correcto', good, msg)
        check(f'Nombre accesible del botón "{n}"', c['label'] == f'Reservar ahora: {n} (abre WhatsApp)', c['label'])
    vis = pg.evaluate("[...document.querySelectorAll('#servicios [data-reveal]')].every(e=>e.classList.contains('is-visible') && getComputedStyle(e).opacity==='1')")
    check('Al desplazarse: encabezado y 8 tarjetas aparecen', vis)
    imgs = pg.evaluate("[...document.querySelectorAll('.service-card img')].map(i=>({src:i.currentSrc.split('/').pop(), ok:i.complete&&i.naturalWidth>0}))")
    check('Las 8 imágenes cargan (AVIF)', all(i['ok'] and i['src'].endswith('.avif') for i in imgs), ', '.join(i['src'] for i in imgs))
    check('Las 8 imágenes son distintas', len({i['src'] for i in imgs}) == 8)
    for sel, need in (('#servicios .section-heading__eyebrow', 4.5), ('#services-title', 3), ('#servicios .section-heading__text', 4.5),
                      ('.service-card__title', 3), ('.service-card__text', 4.5), ('.service-card__price', 4.5),
                      ('.service-card__time', 4.5), ('.service-card__cta', 4.5), ('.services__note', 4.5)):
        r = pg.evaluate(CONTRAST_JS, sel); check(f'Contraste {sel}', r >= need, f'{r}:1')
    pg.screenshot(path=f'{OUT}/servicios-pixel7-412.png', full_page=False)
    pg.evaluate("document.querySelector('#servicios').scrollIntoView()"); pg.wait_for_timeout(300)
    sec = pg.evaluate("(()=>{const r=document.querySelector('#servicios').getBoundingClientRect();return [r.top+scrollY, r.height]})()")
    pg.screenshot(path=f'{OUT}/servicios-pixel7-412-completa.png', full_page=True, clip={'x': 0, 'y': sec[0], 'width': 412, 'height': sec[1]})
    pg.context.close()

    # ---------- Composición por tamaño ----------
    for w, h, cols in ((320, 640, 1), (360, 740, 1), (412, 915, 2), (768, 1024, 2), (1024, 768, 4), (1280, 800, 4), (1920, 1080, 4)):
        pg = page(viewport={'width': w, 'height': h}, device_scale_factor=2 if w < 1000 else 1, has_touch=w < 1000)
        scroll_all(pg)
        cards = pg.evaluate(CARDS_JS)
        ncols = len({c['x'] for c in cards})
        check(f'{w}px: {cols} columna(s)', ncols == cols, f'{ncols} columnas')
        rows = {}
        for c in cards: rows.setdefault(c['top'], []).append(c)
        same_h = all(len({c['h'] for c in r}) == 1 for r in rows.values())
        same_cta = all(len({c['ctaTop'] for c in r}) == 1 for r in rows.values())
        check(f'{w}px: misma altura y botones alineados en cada fila', same_h and same_cta)
        check(f'{w}px: botones ≥ 44px y texto sin desbordar', all(c['ctaH'] >= 44 and not c['ctaOverflow'] for c in cards),
              f"alto {min(c['ctaH'] for c in cards)}px")
        check(f'{w}px: letra mínima ≥ 12px', min(c['minFont'] for c in cards) >= 12, f"{min(c['minFont'] for c in cards)}px")
        check(f'{w}px: sin scroll horizontal', not pg.evaluate('document.documentElement.scrollWidth > innerWidth'))
        if w in (360, 768, 1280, 1920):
            pg.evaluate("document.querySelector('#servicios').scrollIntoView()"); pg.wait_for_timeout(300)
            sec = pg.evaluate("(()=>{const r=document.querySelector('#servicios').getBoundingClientRect();return [r.top+scrollY, r.height]})()")
            pg.screenshot(path=f'{OUT}/servicios-{w}.png', full_page=True, clip={'x': 0, 'y': sec[0], 'width': w, 'height': sec[1]})
        if w == 1280:
            pg.evaluate("document.querySelector('.service-card').scrollIntoView({block:'center'})"); pg.wait_for_timeout(200)
            pg.hover('.service-card'); pg.wait_for_timeout(600)
            tf = pg.evaluate("getComputedStyle(document.querySelector('.service-card')).transform")
            check('Escritorio: hover sutil en la tarjeta (se eleva)', tf != 'none', tf)
            pg.screenshot(path=f'{OUT}/servicios-hover.png', clip={'x': 0, 'y': 0, 'width': 1280, 'height': 800})
            # Teclado: foco visible en un botón de servicio
            pg.focus('.service-card__cta'); oc = pg.evaluate("getComputedStyle(document.activeElement).outlineStyle")
            check('Teclado: foco visible en "Reservar ahora"', oc == 'solid', oc)
        pg.context.close()

    # ---------- Movimiento reducido y sin JavaScript ----------
    pg = page(viewport={'width': 412, 'height': 839}, reduced_motion='reduce')
    op = pg.evaluate("[...document.querySelectorAll('#servicios [data-reveal]')].every(e=>getComputedStyle(e).opacity==='1')")
    check('Movimiento reducido: tarjetas visibles sin esperar', op)
    pg.context.close()
    pg = page(viewport={'width': 412, 'height': 839}, java_script_enabled=False)
    r = pg.evaluate("(()=>({vis:[...document.querySelectorAll('#servicios [data-reveal]')].every(e=>getComputedStyle(e).opacity==='1'), hrefs:[...new Set([...document.querySelectorAll('.service-card__cta')].map(a=>a.getAttribute('href')))]}))()")
    check('Sin JavaScript: tarjetas visibles y botones llevan a #reservas', r['vis'] and r['hrefs'] == ['#reservas'], str(r))
    pg.context.close()

    check('Sin errores de JavaScript ni recursos rotos', not errors, '; '.join(errors))
    b.close()

ok = sum(r[0] for r in results)
for r in results:
    print(('OK   ' if r[0] else 'FALLA'), r[1], ('· ' + r[2]) if r[2] else '')
print(f'\n{ok}/{len(results)} pruebas superadas')
