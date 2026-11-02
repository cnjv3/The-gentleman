from playwright.sync_api import sync_playwright
from urllib.parse import urlparse, parse_qs
import sys, re, os

URL = 'http://localhost:8771/'
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # raíz del repositorio (calculada desde este archivo)
OUT = sys.argv[1]
results = []
def check(name, cond, detail=''):
    results.append((bool(cond), name, detail))

CONTRAST_JS = r'''([sel, bgSel]) => {
 const p=c=>{const v=c.match(/[\d.]+/g).slice(0,3).map(Number);return c.startsWith('color(')?v.map(x=>x*255):v};
 const lum=a=>{const m=a.map(v=>{v/=255;return v<=0.04045?v/12.92:((v+0.055)/1.055)**2.4});return .2126*m[0]+.7152*m[1]+.0722*m[2]};
 const el=document.querySelector(sel);
 let n=bgSel?document.querySelector(bgSel):el, bg; while(n){const b=getComputedStyle(n).backgroundColor; if(!/rgba\(0, 0, 0, 0\)|transparent/.test(b)&&!/, 0\.\d+\)$/.test(b)||/0\.9\d?\)$/.test(b)){bg=b;break} n=n.parentElement}
 const a=lum(p(getComputedStyle(el).color)), b=lum(p(bg)); return +((Math.max(a,b)+.05)/(Math.min(a,b)+.05)).toFixed(2);
}'''
VIEW = '''() => {
  const sec=document.querySelector('#ubicacion'), T=k=>{const e=sec.querySelector(`[data-contact="${k}"]`);return e?[e.textContent, e.classList.contains('is-pending')]:null};
  const A=k=>[...sec.querySelectorAll(`[data-contact-action="${k}"]`)].map(a=>({vis:!a.hidden&&a.offsetParent!==null, href:a.getAttribute('href'), target:a.target, rel:a.rel, name:a.textContent.trim().replace(/\\s+/g,' ')}));
  return {address:T('address'), days:T('days'), time:T('time'), whatsapp:T('whatsapp'), phone:T('phone'), email:T('email'), instagram:T('instagram'),
          a:{whatsapp:A('whatsapp'), phone:A('phone'), email:A('email'), instagram:A('instagram'), map:A('map')},
          iframe:(f=>f?f.src:null)(sec.querySelector('iframe')), placeholder:(e=>!e.hidden&&e.offsetParent!==null)(sec.querySelector('[data-contact-placeholder]')),
          demo:(e=>!e.hidden&&e.offsetParent!==null)(sec.querySelector('[data-contact-demo]')),
          fallback:(e=>({vis:!e.hidden&&e.offsetParent!==null, address:(a=>a.hidden?null:a.textContent)(e.querySelector('[data-contact=map-address]')), hint:e.querySelector('[data-contact=map-hint]').textContent}))(sec.querySelector('[data-contact-map-fallback]')),
          mapEyebrow:sec.querySelector('[data-contact=map-eyebrow]').textContent,
          visibleLinks:[...sec.querySelectorAll('a')].filter(a=>!a.hidden&&a.offsetParent!==null).map(a=>a.getAttribute('href')),
          text:sec.textContent.replace(/\\s+/g,' ')};
}'''

def patched_config(extra_contact, hours=None):
    def handler(route):
        r = route.fetch(); body = r.text()
        for k, v in extra_contact.items():
            body = re.sub(rf"(\n  {k}: )[^,\n]+,", rf"\g<1>{v},", body, count=1)
        if hours:
            for k, v in hours.items():
                body = re.sub(rf"(\n  {k}: )[^,\n]+,", rf"\g<1>{v},", body, count=1)
        route.fulfill(response=r, body=body)
    return handler

CFG = open(f'{REPO}/js/config.js', encoding='utf-8').read()
block = CFG[CFG.index('export const CONTACT'):]; block = block[:block.index('\n};')]
fields = dict(re.findall(r"\n  (\w+): ([^,\n]+),", block))
strings = {k: v for k, v in fields.items() if v.startswith("'")}
check('Config: CONTACT predeterminado con todos los datos vacíos', set(strings) == {'address', 'city', 'country', 'phone', 'email', 'instagram', 'mapsUrl', 'mapsEmbedUrl'} and all(v == "''" for v in strings.values()), str(strings))
check('Config: isDemo activado (true) y showMapEmbed true', fields.get('isDemo') == 'true' and fields.get('showMapEmbed') == 'true', f"isDemo={fields.get('isDemo')}")
check('Config: número de WhatsApp de demostración intacto', "whatsappNumber: '56900000000'" in CFG)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome')
    errors = []
    def page(route=None, **kw):
        ctx = b.new_context(**kw); pg = ctx.new_page()
        pg.route('**://www.google.com/**', lambda r: r.abort())  # El entorno no tiene red externa
        if route: pg.route(*route)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.on('console', lambda m: m.type == 'error' and 'Failed to load resource' not in m.text and errors.append(m.text))
        pg.on('response', lambda r: r.status >= 400 and not r.url.endswith('/favicon.ico') and errors.append(f'{r.status} {r.url}'))
        pg.goto(URL, wait_until='load'); pg.wait_for_timeout(300)
        pg.evaluate("document.documentElement.style.scrollBehavior='auto'; document.querySelector('#ubicacion').scrollIntoView()"); pg.wait_for_timeout(1300)
        return pg

    # ---------- 1. Estructura ----------
    pg = page(viewport={'width': 1280, 'height': 900})
    order = pg.evaluate("[...document.querySelectorAll('main > section')].map(s=>s.id)")
    check('Orden: … reservas → ubicación', order == ['inicio', 'nosotros', 'servicios', 'galeria', 'reservas', 'ubicacion'], str(order))
    head = pg.evaluate("(()=>{const s=document.querySelector('#ubicacion');return [s.querySelector('.section-heading__eyebrow').textContent.trim(), s.querySelector('h2').textContent.trim(), s.querySelector('.section-heading__text').textContent.trim()]})()")
    check('Encabezado exacto', head == ['Visítanos', 'Un espacio creado para ti.', 'Descubre THE GENTLEMAN y vive una experiencia donde la tradición y el estilo contemporáneo se encuentran.'], str(head))
    titles = pg.evaluate("[...document.querySelectorAll('.contact-card__title')].map(e=>e.textContent)")
    check('5 bloques: dirección, horario, teléfono/WhatsApp, correo y redes', titles == ['Dirección', 'Horario de atención', 'Teléfono y WhatsApp', 'Correo electrónico', 'Redes sociales'], str(titles))
    check('Cada bloque con ícono y título (h3)', pg.evaluate("[...document.querySelectorAll('.contact-card')].every(c=>c.querySelector('svg.contact-card__icon')&&c.querySelector('h3'))"))
    check('Anclas del menú: #ubicacion y #contacto existen', pg.evaluate("!!document.querySelector('section#ubicacion') && !!document.querySelector('#ubicacion #contacto')"))
    ver = pg.evaluate("(document.querySelector('link[href*=\"styles.css?v=\"]').getAttribute('href').split('?v=')[1])")
    check(f'CSS y contact.js cargados con la versión vigente ({ver})', pg.evaluate(f"[...document.styleSheets].some(s=>s.href&&s.href.endsWith('styles.css?v={ver}')) && performance.getEntriesByType('resource').some(r=>r.name.endsWith('contact.js?v={ver}'))"))

    # ---------- 2. Datos de demostración (configuración actual) ----------
    v = pg.evaluate(VIEW)
    check('Dirección: "Dirección por confirmar" (no inventada)', v['address'] == ['Dirección por confirmar', True], str(v['address']))
    check('Horario tomado de BOOKING_HOURS: 10:00 – 20:00, días por confirmar', v['time'][0] == '10:00 – 20:00' and v['days'] == ['Días por confirmar', True], f"{v['days']} {v['time']}")
    check('WhatsApp: número de demostración formateado', v['whatsapp'][0] == '+56 9 0000 0000', v['whatsapp'][0])
    wa = v['a']['whatsapp'][0]; q = urlparse(wa['href'])
    check('Botón WhatsApp: visible, número centralizado y mensaje correcto',
          wa['vis'] and q.netloc == 'wa.me' and q.path == '/56900000000' and parse_qs(q.query)['text'][0] == 'Hola, THE GENTLEMAN. Quisiera hacer una consulta.' and wa['target'] == '_blank' and 'noopener' in wa['rel'], wa['href'][:60])
    check('Teléfono, correo e Instagram: "por confirmar"', v['phone'][1] and v['email'] == ['Por confirmar', True] and v['instagram'] == ['Por confirmar', True], f"{v['phone']} {v['email']} {v['instagram']}")
    hidden = {k: [a['vis'] for a in v['a'][k]] for k in ('phone', 'email', 'instagram', 'map')}
    check('Sin datos: botones de llamar, correo, Instagram y mapa ocultos', all(not any(x) for x in hidden.values()), str(hidden))
    check('Ningún enlace visible sin acción (href="#")', '#' not in v['visibleLinks'] and v['visibleLinks'] == [wa['href']], str(v['visibleLinks']))
    check('Sin datos ficticios presentados como reales (sin @correo, tel:, instagram.com ni maps)',
          not re.search(r'@\w|tel:|instagram\.com|google\.com/maps', v['text'] + ' '.join(v['visibleLinks'])))
    check('Mapa: estado de demostración visible, sin iframe', v['placeholder'] and v['iframe'] is None and 'Ubicación de demostración' in v['text'])
    check('Aviso "Datos ilustrativos" visible', v['demo'] and 'Datos ilustrativos' in v['text'])
    check('El horario de contacto y el de reservas coinciden', pg.evaluate("document.querySelector('#booking-time') !== null"))
    pg.context.close()

    # ---------- 3. Fuente única: cambiar config.js cambia la sección y reservas ----------
    real = {'isDemo': 'false', 'address': "'Calle Prueba 123'", 'city': "'Santiago'", 'country': "'Chile'", 'phone': "'56222222222'",
            'email': "'contacto@example.com'", 'instagram': "'https://www.instagram.com/prueba_tg/'"}
    pg = page(route=('**/js/config.js*', patched_config(real, {'days': "'Lunes a sábado'", 'open': "'09:00'"})), viewport={'width': 412, 'height': 915}, is_mobile=True, has_touch=True, device_scale_factor=2.625)
    v = pg.evaluate(VIEW)
    check('Con datos reales: dirección completa', v['address'] == ['Calle Prueba 123, Santiago, Chile', False], str(v['address']))
    check('Con datos reales: horario y días desde la configuración', v['days'] == ['Lunes a sábado', False] and v['time'][0] == '09:00 – 20:00')
    pg.evaluate("document.querySelector('#booking-date').value='2030-01-07'; document.querySelector('#booking-date').dispatchEvent(new Event('input',{bubbles:true}))")
    first = pg.evaluate("document.querySelector('#booking-time option:nth-child(2)').value")
    check('El mismo horario alimenta el formulario de reservas (primera hora 09:00)', first == '09:00', first)
    a = v['a']
    check('Botón Llamar visible con tel:+56222222222', a['phone'][0]['vis'] and a['phone'][0]['href'] == 'tel:+56222222222' and v['phone'][0] == '+56 2 2222 2222', str(a['phone']) + str(v['phone']))
    check('Enlace de correo visible con mailto:', a['email'][0]['vis'] and a['email'][0]['href'] == 'mailto:contacto@example.com')
    check('Instagram visible, pestaña nueva y @usuario', a['instagram'][0]['vis'] and a['instagram'][0]['href'] == 'https://www.instagram.com/prueba_tg/' and a['instagram'][0]['target'] == '_blank' and v['instagram'][0] == '@prueba_tg', str(v['instagram']))
    mq = parse_qs(urlparse(a['map'][0]['href']).query).get('query', [''])[0]
    check('Botones de mapa (2) visibles con la dirección codificada', len(a['map']) == 2 and all(x['vis'] for x in a['map']) and mq == 'Calle Prueba 123, Santiago, Chile', mq)
    check('Mapa real (iframe) con título y carga diferida; placeholder oculto',
          v['iframe'] and 'output=embed' in v['iframe'] and 'Calle%20Prueba%20123' in v['iframe'] and not v['placeholder']
          and pg.evaluate("(f=>f.title.includes('THE GENTLEMAN')&&f.loading==='lazy')(document.querySelector('#ubicacion iframe'))"))
    check('Con isDemo=false: el aviso de datos ilustrativos desaparece', not v['demo'])
    check('Mapa insertado: franja con la dirección y la alternativa siempre visible', v['fallback']['vis'] and v['fallback']['address'] == 'Calle Prueba 123, Santiago, Chile' and 'Abrir en Google Maps' in v['fallback']['hint'], str(v['fallback']))
    pg.screenshot(path=f'{OUT}/contacto-datos-reales-412.png', full_page=False)
    pg.context.close()

    # mapsUrl explícito y URL insegura
    pg = page(route=('**/js/config.js*', patched_config({'isDemo': 'false', 'mapsUrl': "'https://maps.app.goo.gl/ejemplo'", 'instagram': "'javascript:alert(1)'"})), viewport={'width': 1280, 'height': 900})
    v = pg.evaluate(VIEW)
    check('Enlace para compartir sin dirección: botón sí, iframe no (Google no permite insertarlo)', all(x['vis'] and x['href'] == 'https://maps.app.goo.gl/ejemplo' for x in v['a']['map']) and v['iframe'] is None and v['mapEyebrow'] == 'Ubicación en Google Maps', v['mapEyebrow'])
    check('URL insegura en Instagram (javascript:) se ignora', not v['a']['instagram'][0]['vis'] and v['instagram'][1])
    pg.context.close()

    # ---------- 3b. Estados del mapa ----------
    # Modo demostración con una dirección escrita: no debe ubicarse en un mapa real
    pg = page(route=('**/js/config.js*', patched_config({'address': "'Calle Prueba 123'", 'city': "'Santiago'"})), viewport={'width': 412, 'height': 915})
    v = pg.evaluate(VIEW)
    check('isDemo=true con dirección: sin iframe ni botones de mapa (no se ubica un dato ilustrativo)',
          v['iframe'] is None and not any(x['vis'] for x in v['a']['map']) and v['placeholder'] and v['mapEyebrow'] == 'Ubicación de demostración' and v['demo'], str(v['a']['map']))
    pg.context.close()
    # URL de inserción válida, sin dirección
    EMB = 'https://www.google.com/maps/embed?pb=!1m18!1m12!TEST'
    pg = page(route=('**/js/config.js*', patched_config({'isDemo': 'false', 'mapsEmbedUrl': f"'{EMB}'"})), viewport={'width': 412, 'height': 915})
    v = pg.evaluate(VIEW)
    check('mapsEmbedUrl válida: el iframe usa esa URL', v['iframe'] == EMB, str(v['iframe']))
    check('…sin dirección: la franja no muestra "Dirección por confirmar" ni menciona un botón inexistente', v['fallback']['vis'] and v['fallback']['address'] is None and v['fallback']['hint'] == 'Mapa proporcionado por Google Maps.' and not any(x['vis'] for x in v['a']['map']), str(v['fallback']))
    pg.context.close()
    # URL inválida como mapsEmbedUrl
    pg = page(route=('**/js/config.js*', patched_config({'isDemo': 'false', 'mapsEmbedUrl': "'https://maps.app.goo.gl/ejemplo'"})), viewport={'width': 412, 'height': 915})
    v = pg.evaluate(VIEW)
    check('mapsEmbedUrl que no es de inserción: se ignora (sin iframe, ilustración visible)', v['iframe'] is None and v['placeholder'])
    pg.context.close()
    # El iframe falla (petición abortada): la alternativa sigue visible y usable
    pg = page(route=('**/js/config.js*', patched_config(real)), viewport={'width': 412, 'height': 915}, is_mobile=True, has_touch=True, device_scale_factor=2.625)
    pg.evaluate("document.querySelector('.location__map').scrollIntoView({block:'center'})"); pg.wait_for_timeout(2500)
    m = pg.evaluate('''() => {const R=s=>document.querySelector(s).getBoundingClientRect(), f=R('.location-map__frame'), fb=R('.location-map__fallback'), map=R('.location-map'), b=R('.location-map__cta');
      return {frameH:Math.round(f.height), fbBelow:fb.top>=f.bottom-1, fbInside:fb.bottom<=map.bottom+1, btnBelow:b.top>=map.bottom, btnVis:!document.querySelector('.location-map__cta').hidden}}''')
    check('Mapa que falla: franja con dirección bajo el mapa y botón «Abrir en Google Maps» visible', m['fbBelow'] and m['fbInside'] and m['btnBelow'] and m['btnVis'] and m['frameH'] > 200, str(m))
    sec = pg.evaluate("(()=>{const r=document.querySelector('.location__map').getBoundingClientRect();return [r.top+scrollY-20, r.height+40]})()")
    pg.screenshot(path=f'{OUT}/mapa-falla-412.png', full_page=True, clip={'x': 0, 'y': sec[0], 'width': 412, 'height': sec[1]})
    pg.context.close()
    # El iframe carga (respuesta simulada de Google): el contenido se muestra en el panel
    pg = page(route=('**/js/config.js*', patched_config(real)), viewport={'width': 412, 'height': 915}, is_mobile=True, has_touch=True, device_scale_factor=2.625)
    pg.route('**://www.google.com/maps**', lambda r: r.fulfill(status=200, content_type='text/html', body='<body style="margin:0;background:#cfe3c8;font:20px sans-serif;display:grid;place-items:center;height:100vh">MAPA SIMULADO OK</body>'))
    pg.evaluate("document.querySelector('.location-map__frame').src = document.querySelector('.location-map__frame').src")
    pg.evaluate("document.querySelector('.location__map').scrollIntoView({block:'center'})"); pg.wait_for_timeout(2500)
    fr = [f for f in pg.frames if 'google.com/maps' in f.url]
    txt = fr[0].evaluate('document.body.innerText') if fr else ''
    check('Mapa que carga: el contenido del iframe se muestra (respuesta simulada)', txt == 'MAPA SIMULADO OK', txt)
    sec = pg.evaluate("(()=>{const r=document.querySelector('.location__map').getBoundingClientRect();return [r.top+scrollY-20, r.height+40]})()")
    pg.screenshot(path=f'{OUT}/mapa-carga-simulada-412.png', full_page=True, clip={'x': 0, 'y': sec[0], 'width': 412, 'height': sec[1]})
    pg.context.close()

    # ---------- 4. Responsive ----------
    for w, h in ((360, 740), (384, 854), (390, 844), (412, 915), (430, 932), (768, 1024), (1024, 768), (1280, 900), (1920, 1080)):
        mob = w < 1000
        pg = page(viewport={'width': w, 'height': h}, device_scale_factor=2.625 if w < 600 else (2 if mob else 1), is_mobile=w < 600, has_touch=mob)
        m = pg.evaluate('''() => {
          const R=s=>document.querySelector(s).getBoundingClientRect();
          const info=R('.location__info'), map=R('.location__map'), cont=document.querySelector('#ubicacion .container');
          const cw=cont.clientWidth-2*parseFloat(getComputedStyle(cont).paddingLeft);
          const cards=[...document.querySelectorAll('.contact-card')].map(c=>c.getBoundingClientRect().width);
          const icons=[...document.querySelectorAll('#ubicacion svg:not(.location-map__art)')].filter(s=>s.getBoundingClientRect().width>0).map(s=>{const r=s.getBoundingClientRect();return Math.round(Math.max(r.width,r.height))});
          const ci=[...document.querySelectorAll('.contact-card__icon')].map(s=>Math.round(s.getBoundingClientRect().width));
          const fonts=[...document.querySelectorAll('#ubicacion p, #ubicacion h3, #ubicacion span, #ubicacion a')].filter(e=>e.offsetParent).map(e=>parseFloat(getComputedStyle(e).fontSize));
          const btn=[...document.querySelectorAll('#ubicacion a.btn')].filter(a=>a.offsetParent).map(a=>a.getBoundingClientRect().height);
          const cut=[...document.querySelectorAll('.contact-card__title, .contact-card__text, #ubicacion .btn')].some(e=>e.offsetParent&&e.scrollWidth>e.clientWidth+1);
          const lines=e=>{const t=[...e.childNodes].find(n=>n.nodeType===3&&n.textContent.trim()); if(!t) return 1; const r=document.createRange(); r.selectNodeContents(t); return new Set([...r.getClientRects()].filter(x=>x.width>0).map(x=>Math.round(x.top))).size};
          const btnLines=[...document.querySelectorAll('#ubicacion a.btn')].filter(a=>a.offsetParent).map(lines);
          const capLines=lines(document.querySelector('.location-map__eyebrow'));
          return {btnLines, capLines, ov:document.documentElement.scrollWidth>innerWidth, below:map.top>=info.bottom-1, side:map.left>=info.right, cw, cards, maxIcon:Math.max(...icons), ci, minFont:Math.min(...fonts), btn, cut,
                  mapH:map.height};
        }''')
        check(f'{w}px: sin scroll horizontal ni textos cortados', not m['ov'] and not m['cut'])
        if w < 1024:
            check(f'{w}px: información primero, ubicación debajo', m['below'])
        else:
            check(f'{w}px: información a la izquierda, mapa a la derecha', m['side'])
        if w < 768:
            check(f'{w}px: tarjetas a todo el ancho', all(abs(c - m['cw']) < 1 for c in m['cards']), f"{set(round(c) for c in m['cards'])} / {m['cw']:.0f}")
        check(f'{w}px: íconos controlados (tarjetas 44 px con aro, resto ≤ 24 px)', set(m['ci']) == {44} and m['maxIcon'] <= 44, f"aros {set(m['ci'])}, máx {m['maxIcon']}px")
        check(f'{w}px: botón de WhatsApp cómodo al tacto (≥ 48 px)', m['btn'] and min(m['btn']) >= 48, str(m['btn']))
        check(f'{w}px: letra mínima ≥ 12px', m['minFont'] >= 12, f"{m['minFont']}px")
        check(f'{w}px: botones y etiqueta del mapa en una sola línea', all(x == 1 for x in m['btnLines']) and m['capLines'] == 1, f"botones {m['btnLines']} · etiqueta {m['capLines']}")
        if w in (360, 412, 768, 1280, 1920):
            sec = pg.evaluate("(()=>{const r=document.querySelector('#ubicacion').getBoundingClientRect();return [r.top+scrollY, r.height]})()")
            pg.screenshot(path=f'{OUT}/contacto-{w}.png', full_page=True, clip={'x': 0, 'y': sec[0], 'width': w, 'height': sec[1]})
        if w == 1280:
            for sel, bg, need in (('.contact-card__title', None, 3), ('.contact-card__text', None, 4.5), ('.location__demo', '#ubicacion', 4.5),
                                  ('.location__demo-tag', None, 4.5), ('.location-map__eyebrow', '.location-map__caption', 4.5),
                                  ('.location-map__text', '.location-map__caption', 4.5), ('a[data-contact-action=whatsapp]', None, 4.5)):
                r = pg.evaluate(CONTRAST_JS, [sel, bg]); check(f'Contraste {sel}', r >= need, f'{r}:1')
            pg.focus('a[data-contact-action=whatsapp]')
            check('Foco visible en el botón de WhatsApp', pg.evaluate("getComputedStyle(document.activeElement).outlineStyle") == 'solid')
            hs = pg.evaluate("[document.querySelector('.location__info').getBoundingClientRect(), document.querySelector('.location__map').getBoundingClientRect()].map(r=>[Math.round(r.top),Math.round(r.height)])")
            check('Escritorio: columnas equilibradas (mismo inicio y misma altura)', abs(hs[0][0]-hs[1][0]) <= 1 and abs(hs[0][1]-hs[1][1]) <= 1, str(hs))
        pg.context.close()

    # Botón "ghost" (con datos) en escritorio: contraste y tamaño
    pg = page(route=('**/js/config.js*', patched_config({'phone': "'56222222222'"})), viewport={'width': 1280, 'height': 900})
    r = pg.evaluate(CONTRAST_JS, ['a[data-contact-action=phone]', '.contact-card'])
    check('Contraste botón "Llamar" (borde y texto)', r >= 4.5, f'{r}:1')
    pg.context.close()

    # ---------- 5. Animación, movimiento reducido y menú ----------
    ctx = b.new_context(viewport={'width': 412, 'height': 915}); pg = ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(300)
    check('Antes de desplazarse: tarjetas sin animar', pg.evaluate("[...document.querySelectorAll('#ubicacion [data-reveal]')].every(e=>!e.classList.contains('is-visible'))"))
    pg.evaluate("document.documentElement.style.scrollBehavior='auto'"); pg.click('[data-nav-toggle]'); pg.wait_for_timeout(400)
    pg.click('a.site-nav__link[href="#contacto"]'); pg.wait_for_timeout(1500)
    top = pg.evaluate("document.querySelector('#contacto').getBoundingClientRect().top")
    check('Menú → Contacto: lleva a la información con margen superior', 20 <= top <= 40, f'top {top:.0f}px')
    check('Al llegar, las tarjetas aparecen (reveal.js)', pg.evaluate("document.querySelector('.contact-card').classList.contains('is-visible')"))
    ctx.close()
    pg = page(viewport={'width': 412, 'height': 839}, reduced_motion='reduce')
    check('Movimiento reducido: todo visible sin esperar', pg.evaluate("[...document.querySelectorAll('#ubicacion [data-reveal]')].every(e=>getComputedStyle(e).opacity==='1')"))
    pg.context.close()
    ctx = b.new_context(viewport={'width': 412, 'height': 839}, java_script_enabled=False); pg = ctx.new_page(); pg.goto(URL)
    check('Sin JavaScript: aviso visible y ningún botón sin acción', pg.is_visible('.location__noscript') and pg.evaluate("[...document.querySelectorAll('#ubicacion a')].every(a=>a.hidden)"))
    ctx.close()

    check('Sin errores de consola ni recursos rotos', not errors, '; '.join(errors[:3]))
    b.close()

ok = sum(r[0] for r in results)
for r in results:
    print(('OK   ' if r[0] else 'FALLA'), r[1], ('· ' + r[2]) if r[2] else '')
print(f'\n{ok}/{len(results)} pruebas superadas')
