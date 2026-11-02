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

CONTRAST_JS = r'''(sel) => {
 const p=c=>c.match(/[\d.]+/g).slice(0,3).map(Number);
 const el=document.querySelector(sel), cs=getComputedStyle(el);
 let n=el, bg; while(n){const b=getComputedStyle(n).backgroundColor; if(!/rgba\(0, 0, 0, 0\)|transparent/.test(b)){bg=b;break} n=n.parentElement}
 return [p(cs.color), p(bg)];
}'''

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome')
    errors = []
    def page(**kw):
        ctx = b.new_context(**kw); pg = ctx.new_page()
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.on('response', lambda r: r.status >= 400 and not r.url.endswith('/favicon.ico') and errors.append(f'{r.status} {r.url}'))
        pg.goto(URL, wait_until='load'); pg.wait_for_timeout(300)
        return pg
    imgs = lambda pg: pg.evaluate("performance.getEntriesByType('resource').filter(r=>r.name.includes('/about/')).map(r=>r.name.split('/').pop()+' '+Math.round(r.encodedBodySize/1024)+'KB')")

    # ---------- Android simulado ----------
    pg = page(**p.devices['Pixel 7'])
    order = pg.evaluate("[...document.querySelectorAll('main > section')].map(s=>s.id)")
    check('Nosotros va justo después del hero', order[:2] == ['inicio', 'nosotros'], str(order))
    check('Jerarquía de títulos: h1 en hero, h2 en Nosotros', pg.evaluate("document.querySelector('#nosotros h2').id") == 'about-title' and pg.evaluate("document.querySelectorAll('#nosotros h1').length") == 0)
    st = pg.evaluate("[...document.querySelectorAll('#nosotros [data-reveal]')].map(e=>[e.classList.contains('is-visible'), getComputedStyle(e).opacity])")
    check('Antes de desplazarse: contenido aún oculto (listo para animar)', all(not v and o == '0' for v, o in st), str(st))
    lcp = pg.evaluate("(()=>{const r=performance.getEntriesByType('resource');const h=r.find(x=>x.name.includes('/hero/')),a=r.find(x=>x.name.includes('/about/'));return a?a.startTime>=h.startTime:true})()")
    check('La imagen de Nosotros no se adelanta a la del hero', lcp)
    pg.evaluate("document.querySelector('#nosotros').scrollIntoView()"); pg.wait_for_timeout(1400)
    st = pg.evaluate("[...document.querySelectorAll('#nosotros [data-reveal]')].map(e=>[e.classList.contains('is-visible'), getComputedStyle(e).opacity])")
    check('Al desplazarse: aparece con animación', all(v and o == '1' for v, o in st), str(st))
    check('La imagen se descarga al acercarse (AVIF)', imgs(pg) and 'avif' in imgs(pg)[0], str(imgs(pg)))
    pg.screenshot(path=f'{OUT}/about-pixel7-412.png', full_page=False)
    pg.screenshot(path=f'{OUT}/about-pixel7-412-completa.png', full_page=True)
    # Contraste de textos sobre marfil
    for sel, need in (('#nosotros .eyebrow', 4.5), ('#about-title', 3), ('.about__text', 4.5)):
        fg, bg = pg.evaluate(CONTRAST_JS, sel); r = round(ratio(fg, bg), 2)
        check(f'Contraste {sel}', r >= need, f'{r}:1')
    # Contraste de la leyenda sobre los píxeles reales de la foto
    box = pg.evaluate("(()=>{const r=document.querySelector('.about__caption').getBoundingClientRect();return [r.x,r.y,r.width,r.height]})()")
    pg.add_style_tag(content='.about__caption{color:transparent!important}'); pg.wait_for_timeout(100)
    shot = Image.open(io.BytesIO(pg.screenshot())).convert('RGB'); dpr = pg.evaluate('devicePixelRatio')
    px = sorted(shot.crop([int(v * dpr) for v in (box[0], box[1], box[0] + box[2], box[1] + box[3])]).getdata(), key=lum)
    r = round(ratio((242, 239, 231), px[int(len(px) * .98) - 1]), 2)
    check('Contraste leyenda "Imagen referencial" sobre la foto', r >= 4.5, f'{r}:1')
    check('Sin scroll horizontal (412)', not pg.evaluate('document.documentElement.scrollWidth > innerWidth'))
    pg.context.close()

    # ---------- El enlace del menú lleva a la sección ----------
    pg = page(**p.devices['Pixel 7'])
    pg.tap('[data-nav-toggle]'); pg.wait_for_timeout(450)
    pg.tap('a.site-nav__link[href="#nosotros"]'); pg.wait_for_timeout(1500)
    top = pg.evaluate("document.querySelector('#nosotros').getBoundingClientRect().top")
    vis = pg.evaluate("[...document.querySelectorAll('#nosotros [data-reveal]')].every(e=>e.classList.contains('is-visible'))")
    check('Menú → Nosotros: navega a la sección y la muestra', abs(top) <= 2 and vis, f'top {top:.0f}px')
    pg.context.close()

    # ---------- Tamaños ----------
    for w, h in ((360, 740), (768, 1024), (1024, 768), (1280, 800), (1920, 1080)):
        pg = page(viewport={'width': w, 'height': h}, device_scale_factor=2 if w < 1000 else 1)
        pg.evaluate("document.querySelector('#nosotros').scrollIntoView()"); pg.wait_for_timeout(1400)
        m = pg.evaluate('''() => {
          const r=s=>document.querySelector(s).getBoundingClientRect();
          return {media:r('.about__media'), content:r('.about__content'), sec:r('#nosotros'),
                  ov:document.documentElement.scrollWidth>innerWidth};
        }''')
        check(f'{w}px: sin scroll horizontal (marco dorado incluido)', not m['ov'])
        if w >= 768:
            side = m['media']['right'] < m['content']['left']
            bigger = m['media']['width'] > m['content']['width']
            check(f'{w}px: imagen protagonista a la izquierda, texto a la derecha', side and bigger,
                  f"imagen {m['media']['width']:.0f}px · texto {m['content']['width']:.0f}px")
        else:
            check(f'{w}px: imagen arriba y texto debajo', m['media']['bottom'] <= m['content']['top'])
        pg.screenshot(path=f'{OUT}/about-{w}.png')
        pg.context.close()

    # ---------- Movimiento reducido y sin JavaScript ----------
    pg = page(viewport={'width': 412, 'height': 839}, reduced_motion='reduce')
    op = pg.evaluate("[...document.querySelectorAll('#nosotros [data-reveal]')].map(e=>getComputedStyle(e).opacity)")
    check('Movimiento reducido: visible sin esperar a desplazarse', all(o == '1' for o in op), str(op))
    pg.context.close()
    pg = page(viewport={'width': 412, 'height': 839}, java_script_enabled=False)
    op = pg.evaluate("[...document.querySelectorAll('#nosotros [data-reveal]')].map(e=>getComputedStyle(e).opacity)")
    check('Sin JavaScript: el contenido se ve igual', all(o == '1' for o in op), str(op))
    pg.context.close()

    check('Sin errores de JavaScript ni recursos rotos', not errors, '; '.join(errors))
    b.close()

ok = sum(r[0] for r in results)
for r in results:
    print(('OK   ' if r[0] else 'FALLA'), r[1], ('· ' + r[2]) if r[2] else '')
print(f'\n{ok}/{len(results)} pruebas superadas')
