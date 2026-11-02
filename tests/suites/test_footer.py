from playwright.sync_api import sync_playwright
from urllib.parse import urlparse
import sys, re, datetime

URL = 'http://localhost:8771/'
OUT = sys.argv[1]
results = []
def check(name, cond, detail=''):
    results.append((bool(cond), name, detail))

CONTRAST_JS = r'''(sel) => {
 const p=c=>{const v=c.match(/[\d.]+/g).slice(0,3).map(Number);return c.startsWith('color(')?v.map(x=>x*255):v};
 const lum=a=>{const m=a.map(v=>{v/=255;return v<=0.04045?v/12.92:((v+0.055)/1.055)**2.4});return .2126*m[0]+.7152*m[1]+.0722*m[2]};
 const el=document.querySelector(sel); let n=el, bg; while(n){const b=getComputedStyle(n).backgroundColor; if(!/rgba\(0, 0, 0, 0\)|transparent/.test(b)){bg=b;break} n=n.parentElement}
 const a=lum(p(getComputedStyle(el).color)), b=lum(p(bg)); return +((Math.max(a,b)+.05)/(Math.min(a,b)+.05)).toFixed(2);
}'''
VIEW = '''() => {
  const f=document.querySelector('footer.site-footer'), vis=e=>!!e&&!e.closest('[hidden]')&&e.offsetParent!==null;
  const item=k=>{const li=f.querySelector(`[data-footer-item="${k}"]`); const a=li.querySelector('a'); return {vis:vis(li), text:li.innerText.replace(/\\s+/g,' ').trim(), href:a?a.getAttribute('href'):null, target:a?a.target:null, rel:a?a.rel:null}};
  return {address:item('address'), hours:item('hours'), whatsapp:item('whatsapp'), phone:item('phone'), email:item('email'), instagram:item('instagram'),
          demo:vis(f.querySelector('[data-footer-demo]')), year:f.querySelector('[data-footer-year]').textContent,
          visibleHrefs:[...f.querySelectorAll('a')].filter(vis).map(a=>a.getAttribute('href')), text:f.textContent.replace(/\\s+/g,' ')};
}'''

def patched_config(values):
    def handler(route):
        r = route.fetch(); body = r.text()
        for k, v in values.items():
            body, n = re.subn(rf"(\n  {k}: )[^,\n]+,", rf"\g<1>{v},", body, count=1)
            assert n == 1, k
        route.fulfill(response=r, body=body)
    return handler
REAL = {'isDemo': 'false', 'address': "'Calle Prueba 123'", 'city': "'Santiago'", 'country': "'Chile'", 'phone': "'56222222222'",
        'email': "'contacto@example.com'", 'instagram': "'https://www.instagram.com/prueba_tg/'", 'days': "'Lunes a sábado'"}

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome')
    errors = []
    def page(route=None, clock=None, **kw):
        ctx = b.new_context(**kw); pg = ctx.new_page()
        pg.route('**://www.google.com/**', lambda r: r.abort())
        if clock: pg.clock.install(time=clock)
        if route: pg.route('**/js/config.js*', route)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.on('console', lambda m: m.type == 'error' and 'Failed to load resource' not in m.text and errors.append(m.text))
        pg.on('response', lambda r: r.status >= 400 and not r.url.endswith('/favicon.ico') and errors.append(f'{r.status} {r.url}'))
        pg.goto(URL, wait_until='load'); pg.wait_for_timeout(400)
        return pg

    # ---------- 1. Estructura y semántica ----------
    pg = page(viewport={'width': 1280, 'height': 900})
    s = pg.evaluate('''() => {const f=document.querySelector('footer.site-footer');
      return {last:document.body.lastElementChild===f || [...document.body.children].filter(e=>e.tagName!=='SCRIPT').pop()===f,
              outsideMain:!f.closest('main'), footers:document.querySelectorAll('body > footer').length,
              navLabel:(n=>n&&document.getElementById(n.getAttribute('aria-labelledby')).textContent)(f.querySelector('nav[aria-labelledby]')),
              h2:[...f.querySelectorAll('h2')].map(h=>h.textContent), address:!!f.querySelector('address'),
              logo:f.querySelector('.site-footer__logo').getAttribute('href'), motto:f.querySelector('.site-footer__motto').textContent}}''')
    check('Footer al final del documento, fuera de <main> (región "contentinfo")', s['last'] and s['outsideMain'] and s['footers'] == 1)
    check('Navegación etiquetada y títulos h2', s['navLabel'] == 'Navegación' and s['h2'] == ['Navegación', 'Contacto'], str(s['h2']))
    check('Contacto dentro de <address>', s['address'])
    check('Logotipo enlaza al inicio y frase de identidad presente', s['logo'] == '#inicio' and s['motto'] == 'Tradición, estilo y cuidado personal en un solo lugar.')
    ver = pg.evaluate("document.querySelector('link[href*=\"styles.css?v=\"]').getAttribute('href').split('?v=')[1]")
    check(f'CSS y footer.js cargados con la versión vigente ({ver})', pg.evaluate(f"[...document.styleSheets].some(s=>s.href&&s.href.endsWith('styles.css?v={ver}')) && performance.getEntriesByType('resource').some(r=>r.name.endsWith('footer.js?v={ver}'))"))

    # ---------- 2. Enlaces internos ----------
    links = pg.evaluate("[...document.querySelectorAll('.site-footer nav a')].map(a=>[a.textContent.trim(), a.getAttribute('href')])")
    check('6 enlaces: Inicio, Nosotros, Servicios, Galería, Reservas, Contacto',
          links == [['Inicio', '#inicio'], ['Nosotros', '#nosotros'], ['Servicios', '#servicios'], ['Galería', '#galeria'], ['Reservas', '#reservas'], ['Contacto', '#contacto']], str(links))
    internal = pg.evaluate("[...document.querySelectorAll('.site-footer a[href^=\"#\"]')].filter(a=>!a.closest('[hidden]')).map(a=>a.getAttribute('href'))")
    # '#top' es un fragmento definido por el estándar HTML: lleva al inicio del documento
    missing = [h for h in internal if h != '#top' and not pg.evaluate(f"!!document.getElementById('{h[1:]}')")]
    check(f'Todos los enlaces internos visibles ({len(internal)}) apuntan a un destino existente', not missing and '#' not in internal, str(missing))
    pg.evaluate("document.documentElement.style.scrollBehavior='auto'")
    nav_ok = []
    for text, href in links:
        pg.evaluate("window.scrollTo(0, document.body.scrollHeight)"); pg.wait_for_timeout(150)
        pg.click(f'.site-footer nav a[href="{href}"]'); pg.wait_for_timeout(350)
        top = pg.evaluate(f"document.getElementById('{href[1:]}').getBoundingClientRect().top")
        nav_ok.append(pg.evaluate('location.hash') == href and -2 <= top <= 60)
    check('Cada enlace de navegación lleva a su sección', all(nav_ok), str(nav_ok))
    pg.evaluate("window.scrollTo(0, document.body.scrollHeight)"); pg.click('.site-footer__top'); pg.wait_for_timeout(350)
    check('"Volver arriba" vuelve al inicio', pg.evaluate('scrollY') < 5)
    pg.evaluate("window.scrollTo(0, document.body.scrollHeight)"); pg.click('.site-footer__cta'); pg.wait_for_timeout(350)
    check('"Reservar ahora" lleva al formulario de reservas', pg.evaluate("location.hash==='#reservas' && Math.abs(document.getElementById('reservas').getBoundingClientRect().top)<60"))

    # ---------- 3. Datos vacíos (configuración actual) ----------
    v = pg.evaluate(VIEW)
    check('Datos vacíos: dirección, teléfono, correo e Instagram ocultos', not any(v[k]['vis'] for k in ('address', 'phone', 'email', 'instagram')))
    check('Horario desde la configuración compartida', v['hours']['vis'] and v['hours']['text'] == 'Días por confirmar · 10:00 – 20:00', v['hours']['text'])
    wa = v['whatsapp']; q = urlparse(wa['href'] or '')
    check('WhatsApp: número de demostración, pestaña nueva y noopener', wa['vis'] and q.netloc == 'wa.me' and q.path == '/56900000000' and wa['target'] == '_blank' and 'noopener' in wa['rel'] and '+56 9 0000 0000' in wa['text'])
    same = pg.evaluate("document.querySelector('[data-footer-link=whatsapp]').href === document.querySelector('#ubicacion [data-contact-action=whatsapp]').href")
    check('Mismo enlace de WhatsApp que la sección de contacto (sin duplicar lógica)', same)
    check('Ningún enlace visible sin acción (href="#")', '#' not in v['visibleHrefs'], str(v['visibleHrefs']))
    check('Sin datos inventados (correo, tel:, Instagram, dirección, TikTok, páginas legales)',
          not re.search(r'@\w|tel:|instagram\.com|Prueba|TikTok|Privacidad|Términos', v['text'] + ' '.join(v['visibleHrefs'])))
    check('isDemo true: aviso de sitio demostrativo visible', v['demo'] and 'Sitio de demostración' in v['text'])
    check('Año del copyright = año actual', v['year'] == str(datetime.date.today().year), v['year'])
    pg.context.close()

    # Año dinámico con reloj simulado
    pg = page(clock=datetime.datetime(2031, 3, 15, 12, 0, tzinfo=datetime.timezone.utc), viewport={'width': 412, 'height': 915})
    check('Año dinámico: con el reloj en 2031 muestra 2031', pg.evaluate(VIEW)['year'] == '2031')
    pg.context.close()

    # ---------- 4. Datos configurados ----------
    pg = page(route=patched_config(REAL), viewport={'width': 1280, 'height': 900})
    v = pg.evaluate(VIEW)
    check('Configurado: dirección visible', v['address']['vis'] and v['address']['text'] == 'Calle Prueba 123, Santiago, Chile', v['address']['text'])
    check('Configurado: teléfono con tel:', v['phone']['vis'] and v['phone']['href'] == 'tel:+56222222222' and '+56 2 2222 2222' in v['phone']['text'])
    check('Configurado: correo con mailto:', v['email']['vis'] and v['email']['href'] == 'mailto:contacto@example.com')
    check('Configurado: Instagram https, @usuario y pestaña nueva', v['instagram']['vis'] and v['instagram']['href'] == 'https://www.instagram.com/prueba_tg/' and '@prueba_tg' in v['instagram']['text'] and v['instagram']['target'] == '_blank')
    check('Configurado: días del horario desde la configuración', v['hours']['text'] == 'Lunes a sábado · 10:00 – 20:00', v['hours']['text'])
    check('isDemo false: aviso demostrativo oculto', not v['demo'])
    al = pg.evaluate("(()=>{const t=document.querySelector('.site-footer__top').getBoundingClientRect(), c=document.querySelector('.site-footer .container'), cr=c.getBoundingClientRect(), pr=parseFloat(getComputedStyle(c).paddingRight); return Math.round(cr.right-pr-t.right)})()")
    check('isDemo false (escritorio): "Volver arriba" sigue alineado a la derecha', abs(al) <= 1, f'{al}px del borde')
    names = pg.evaluate("[...document.querySelectorAll('.site-footer__contact a')].filter(a=>!a.closest('[hidden]')).map(a=>a.textContent.replace(/\\s+/g,' ').trim())")
    check('Enlaces de contacto descriptivos para lectores de pantalla', names == ['WhatsApp: +56 9 0000 0000 (abre WhatsApp)', 'Teléfono: +56 2 2222 2222', 'Correo: contacto@example.com', 'Instagram: @prueba_tg (abre en una pestaña nueva)'], str(names))
    fh = pg.evaluate("(()=>{const r=document.querySelector('.site-footer').getBoundingClientRect();return [r.top+scrollY, r.height]})()")
    pg.screenshot(path=f'{OUT}/footer-configurado-1280.png', full_page=True, clip={'x': 0, 'y': fh[0], 'width': 1280, 'height': fh[1]})
    pg.context.close()
    pg = page(route=patched_config({**REAL, 'isDemo': 'true'}), viewport={'width': 412, 'height': 915})
    v = pg.evaluate(VIEW)
    check('isDemo true con datos: los datos se ven y el aviso sigue visible', v['demo'] and v['phone']['vis'] and v['address']['vis'])
    pg.context.close()
    pg = page(route=patched_config({'isDemo': 'false', 'instagram': "'javascript:alert(1)'"}), viewport={'width': 412, 'height': 915})
    check('URL insegura en Instagram se ignora en el footer', not pg.evaluate(VIEW)['instagram']['vis'])
    pg.context.close()

    # ---------- 5. Responsive ----------
    for w, h in ((360, 740), (390, 844), (412, 915), (430, 932), (768, 1024), (1024, 768), (1280, 900), (1920, 1080)):
        mob = w < 1000
        pg = page(viewport={'width': w, 'height': h}, device_scale_factor=2.625 if w < 600 else (2 if mob else 1), is_mobile=w < 600, has_touch=mob)
        m = pg.evaluate('''() => {
          const f=document.querySelector('.site-footer'), R=s=>f.querySelector(s).getBoundingClientRect();
          const brand=R('.site-footer__brand'), nav=R('nav.site-footer__col'), con=R('.site-footer__col:not(nav)');
          const vis=e=>!e.closest('[hidden]')&&e.offsetParent!==null;
          const targets=[...f.querySelectorAll('a')].filter(vis).map(a=>Math.round(a.getBoundingClientRect().height));
          const icons=[...f.querySelectorAll('svg')].filter(vis).map(s=>Math.round(s.getBoundingClientRect().width));
          const fonts=[...f.querySelectorAll('p, a, span, h2, li')].filter(vis).map(e=>parseFloat(getComputedStyle(e).fontSize));
          const cut=[...f.querySelectorAll('a, p, h2, .site-footer__contact-item')].filter(vis).some(e=>e.scrollWidth>e.clientWidth+1);
          const lines=e=>{const t=[...e.childNodes].find(n=>n.nodeType===3&&n.textContent.trim()); if(!t) return 1; const r=document.createRange(); r.selectNodeContents(t); return new Set([...r.getClientRects()].filter(x=>x.width>0).map(x=>Math.round(x.top))).size};
          return {ov:document.documentElement.scrollWidth>innerWidth, cut, stacked:brand.bottom<=nav.top&&nav.bottom<=con.top,
                  tablet:brand.bottom<=nav.top&&Math.abs(nav.top-con.top)<2&&nav.right<=con.left,
                  three:Math.abs(brand.top-nav.top)<2&&Math.abs(nav.top-con.top)<2&&brand.right<=nav.left&&nav.right<=con.left,
                  minTarget:Math.min(...targets), icons:[...new Set(icons)].sort(), minFont:Math.min(...fonts),
                  ctaLines:lines(f.querySelector('.site-footer__cta')), logoLines:lines(f.querySelector('.site-footer__logo-name'))};
        }''')
        check(f'{w}px: sin scroll horizontal ni textos cortados', not m['ov'] and not m['cut'])
        if w < 768: check(f'{w}px: marca, navegación y contacto apilados', m['stacked'])
        elif w < 1024: check(f'{w}px: marca arriba; navegación y contacto en dos columnas', m['tablet'])
        else: check(f'{w}px: tres columnas alineadas', m['three'])
        check(f'{w}px: enlaces cómodos al tacto (≥ 44 px)', m['minTarget'] >= 44, f"{m['minTarget']}px")
        check(f'{w}px: íconos controlados (16–20 px)', set(m['icons']) <= {16, 18, 20}, str(m['icons']))
        check(f'{w}px: letra mínima ≥ 12px', m['minFont'] >= 12, f"{m['minFont']}px")
        check(f'{w}px: logotipo y botón en una sola línea', m['logoLines'] == 1 and m['ctaLines'] == 1, f"logo {m['logoLines']} · botón {m['ctaLines']}")
        fh = pg.evaluate("(()=>{const r=document.querySelector('.site-footer').getBoundingClientRect();return [r.top+scrollY, r.height]})()")
        pg.screenshot(path=f'{OUT}/footer-{w}.png', full_page=True, clip={'x': 0, 'y': fh[0], 'width': w, 'height': fh[1]})
        if w == 1280:
            for sel, need in (('.site-footer__logo-name', 3), ('.site-footer__logo-tagline', 4.5), ('.site-footer__motto', 4.5), ('.site-footer__title', 4.5),
                              ('.site-footer nav a', 4.5), ('.site-footer__contact-item', 4.5), ('[data-footer-link=whatsapp]', 4.5),
                              ('.site-footer__cta', 4.5), ('.site-footer__copy', 4.5), ('.site-footer__demo', 4.5), ('.site-footer__top', 4.5)):
                r = pg.evaluate(CONTRAST_JS, sel); check(f'Contraste {sel}', r >= need, f'{r}:1')
            dh = pg.evaluate("[...document.querySelectorAll('.site-footer__col')].map(c=>Math.round(c.getBoundingClientRect().height))")
            check('Escritorio: divisores dorados de igual altura', len(set(dh)) == 1, str(dh))
            ml = pg.evaluate("(e=>{const r=document.createRange(); r.selectNodeContents(e.firstChild); const rs=[...r.getClientRects()]; const tops=[...new Set(rs.map(x=>Math.round(x.top)))]; const last=rs.filter(x=>Math.round(x.top)===tops.at(-1)).reduce((a,x)=>a+x.width,0); const first=rs.filter(x=>Math.round(x.top)===tops[0]).reduce((a,x)=>a+x.width,0); return [tops.length, Math.round(last/first*100)]})(document.querySelector('.site-footer__motto'))")
            check('Escritorio: frase de identidad equilibrada (última línea ≥ 50 %)', ml[0] == 1 or ml[1] >= 50, f'{ml[0]} líneas, última al {ml[1]} %')
            pg.focus('.site-footer__logo'); order = ['logo']
            for _ in range(10):
                pg.keyboard.press('Tab'); order.append(pg.evaluate("document.activeElement.textContent.replace(/\\s+/g,' ').trim()"))
            exp = ['logo', 'Inicio', 'Nosotros', 'Servicios', 'Galería', 'Reservas', 'Contacto', 'WhatsApp: +56 9 0000 0000 (abre WhatsApp)', 'Reservar ahora', 'Volver arriba']
            check('Teclado: orden lógico, sin pasar por elementos ocultos', order[:10] == exp, ' → '.join(order[:10]))
            pg.focus('.site-footer nav a')
            st = pg.evaluate("(s=>[s.outlineStyle, s.outlineColor])(getComputedStyle(document.activeElement))")
            check('Foco visible en dorado (≥ 3:1 sobre carbón)', st[0] == 'solid' and st[1] == 'rgb(166, 138, 96)', str(st))
        pg.context.close()

    # ---------- 6. Sin JavaScript ----------
    ctx = b.new_context(viewport={'width': 412, 'height': 915}, java_script_enabled=False); pg = ctx.new_page(); pg.goto(URL)
    r = pg.evaluate('''() => {const f=document.querySelector('.site-footer'), vis=e=>!e.closest('[hidden]')&&e.offsetParent!==null;
      return {nav:[...f.querySelectorAll('nav a')].every(vis), hrefs:[...f.querySelectorAll('a')].filter(vis).map(a=>a.getAttribute('href')), demo:vis(f.querySelector('[data-footer-demo]')), year:f.querySelector('[data-footer-year]').textContent}}''')
    check('Sin JavaScript: navegación visible, aviso visible y ningún enlace vacío', r['nav'] and r['demo'] and '#' not in r['hrefs'] and r['year'] == '2026', str(r))
    ctx.close()

    check('Sin errores de consola ni recursos rotos', not errors, '; '.join(errors[:3]))
    b.close()

ok = sum(r[0] for r in results)
for r in results:
    print(('OK   ' if r[0] else 'FALLA'), r[1], ('· ' + r[2]) if r[2] else '')
print(f'\n{ok}/{len(results)} pruebas superadas')
