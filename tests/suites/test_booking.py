from playwright.sync_api import sync_playwright
from urllib.parse import urlparse, parse_qs
import sys, re, glob, datetime, os

URL = 'http://localhost:8771/'
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # raíz del repositorio (calculada desde este archivo)
OUT = sys.argv[1]
results = []
def check(name, cond, detail=''):
    results.append((bool(cond), name, detail))

# Reloj fijo: lunes 2 de noviembre de 2026, 15:10 en Santiago (UTC-3)
NOW = datetime.datetime(2026, 11, 2, 18, 10, tzinfo=datetime.timezone.utc)
TODAY = '2026-11-02'
FUTURE = '2026-11-09'
SERVICES = [('Corte Clásico', '$12.000'), ('Arreglo de Barba', '$8.000'), ('Tratamiento Capilar', '$15.000'), ('Cuidado Facial', '$18.000'),
            ('Diseño Premium', '$14.000'), ('Peinado y Styling', '$6.000'), ('Coloración', '$22.000'), ('Ritual The Gentleman', '$28.000')]

SUMMARY = "Object.fromEntries([...document.querySelectorAll('[data-summary]')].map(e=>[e.dataset.summary,e.textContent]))"
CAPTURE_OPEN = "window.__opened=[]; window.open=(u,t,f)=>{window.__opened.push([u,t,f]); return null;}; true"
CONTRAST_JS = r'''([sel, prop, bgSel]) => {
 const p=c=>{const v=c.match(/[\d.]+/g).slice(0,3).map(Number);return c.startsWith('color(')?v.map(x=>x*255):v};
 const lum=a=>{const m=a.map(v=>{v/=255;return v<=0.04045?v/12.92:((v+0.055)/1.055)**2.4});return .2126*m[0]+.7152*m[1]+.0722*m[2]};
 const el=document.querySelector(sel); const fg=getComputedStyle(el, prop==='placeholder'?'::placeholder':null)[prop==='border'?'borderTopColor':'color'];
 let n=bgSel?document.querySelector(bgSel):(prop==='border'?el.parentElement:el), bg; while(n){const b=getComputedStyle(n).backgroundColor; if(!/rgba\(0, 0, 0, 0\)|transparent/.test(b)){bg=b;break} n=n.parentElement}
 const a=lum(p(fg)), b=lum(p(bg)); return +((Math.max(a,b)+.05)/(Math.min(a,b)+.05)).toFixed(2);
}'''

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome')
    errors = []
    def page(route=None, **kw):
        kw.setdefault('timezone_id', 'America/Santiago'); kw.setdefault('locale', 'es-CL')
        ctx = b.new_context(**kw); pg = ctx.new_page()
        pg.clock.install(time=NOW)
        if route: pg.route(route[0], route[1])
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.on('console', lambda m: m.type == 'error' and 'favicon' not in m.text and 'Failed to load resource' not in m.text and errors.append(m.text))
        pg.on('response', lambda r: r.status >= 400 and not r.url.endswith('/favicon.ico') and errors.append(f'{r.status} {r.url}'))
        pg.goto(URL, wait_until='load'); pg.wait_for_timeout(300)
        pg.evaluate(CAPTURE_OPEN)
        pg.evaluate("document.querySelector('#reservas').scrollIntoView()"); pg.wait_for_timeout(900)
        return pg
    S = lambda pg: pg.evaluate(SUMMARY)

    # ---------- Estructura y fuente única de datos ----------
    pg = page(viewport={'width': 1280, 'height': 900})
    order = pg.evaluate("[...document.querySelectorAll('main > section')].map(s=>s.id)")
    check('Orden: … galería → reservas', order[:5] == ['inicio', 'nosotros', 'servicios', 'galeria', 'reservas'], str(order))
    head = pg.evaluate("(()=>{const s=document.querySelector('#reservas');return [s.querySelector('.section-heading__eyebrow').textContent.trim(), s.querySelector('h2').textContent.trim(), s.querySelector('.section-heading__text').textContent.trim()]})()")
    check('Encabezado exacto', head == ['Reserva tu experiencia', 'Tu próximo estilo comienza aquí.', 'Elige tu servicio y solicita tu próxima visita a THE GENTLEMAN.'], str(head))
    labels = pg.evaluate("[...document.querySelectorAll('#booking-form input, #booking-form select, #booking-form textarea')].map(f=>[f.name, f.labels.length===1, f.required])")
    check('Cada campo tiene su etiqueta asociada', all(l for _, l, _ in labels), str(labels))
    check('Obligatorios: nombre, servicio, fecha y hora; opcionales: teléfono y observaciones',
          {n: r for n, _, r in labels} == {'name': True, 'serviceId': True, 'date': True, 'time': True, 'phone': False, 'notes': False})
    check('Placeholder del nombre: "Ingresa tu nombre"', pg.get_attribute('#booking-name', 'placeholder') == 'Ingresa tu nombre')
    opts = pg.evaluate("[...document.querySelectorAll('#booking-serviceId option')].slice(1).map(o=>o.textContent)")
    check('Selector con los 8 servicios y precios de las tarjetas', opts == [f'{n} · {pr}' for n, pr in SERVICES], ' | '.join(opts))
    dup = [f for f in glob.glob(f'{REPO}/js/**/*.js', recursive=True) + [f'{REPO}/css/styles.css'] if re.search(r'12\.000|28\.000|\b12000\b', open(f).read())]
    check('Precios no duplicados en JS ni CSS (solo en las tarjetas)', not dup, str(dup))
    check('Resumen inicial: todo con guion (—)', set(S(pg).values()) == {'—'} and len(S(pg)) == 7, str(S(pg)))
    check('Fechas anteriores bloqueadas (min = hoy)', pg.get_attribute('#booking-date', 'min') == TODAY)

    # ---------- Sincronización en tiempo real ----------
    typed_ok = True
    pg.click('#booking-name')
    for i, ch in enumerate('Juan Pérez'):
        pg.keyboard.type(ch)
        if S(pg)['name'] != 'Juan Pérez'[:i + 1].strip(): typed_ok = False
    check('Nombre: aparece letra por letra mientras se escribe', typed_ok and S(pg)['name'] == 'Juan Pérez', S(pg)['name'])
    pg.select_option('#booking-serviceId', label='Diseño Premium · $14.000')
    check('Servicio: actualiza nombre y precio', (S(pg)['service'], S(pg)['price']) == ('Diseño Premium', '$14.000'))
    pg.select_option('#booking-serviceId', label='Ritual The Gentleman · $28.000')
    check('Cambiar de servicio actualiza el precio', (S(pg)['service'], S(pg)['price']) == ('Ritual The Gentleman', '$28.000'))
    pg.fill('#booking-date', FUTURE)
    check('Fecha: aparece con formato legible', S(pg)['date'] == 'Lunes, 9 de noviembre de 2026', S(pg)['date'])
    slots = pg.evaluate("[...document.querySelectorAll('#booking-time option')].slice(1).map(o=>o.value)")
    exp = [f'{h:02d}:{m:02d}' for h in range(10, 20) for m in (0, 30)]
    check('Horarios cada 30 min dentro del horario configurado (10:00–19:30)', slots == exp, f'{len(slots)}: {slots[0]}…{slots[-1]}')
    pg.select_option('#booking-time', '11:30')
    check('Hora: aparece en el resumen', S(pg)['time'] == '11:30')
    pg.fill('#booking-phone', '+56 9 1111 2222')
    check('Teléfono: aparece en el resumen', S(pg)['phone'] == '+56 9 1111 2222')
    pg.fill('#booking-notes', 'Degradado bajo.\nTraeré una referencia.')
    check('Observaciones: aparecen respetando saltos de línea', S(pg)['notes'] == 'Degradado bajo.\nTraeré una referencia.')
    pg.fill('#booking-name', 'Juan Pérez Soto')
    check('Modificar un campo actualiza el resumen al instante', S(pg)['name'] == 'Juan Pérez Soto')
    pg.fill('#booking-notes', '')
    pg.fill('#booking-phone', '')
    check('Vaciar un campo vuelve a mostrar el guion', S(pg)['notes'] == '—' and S(pg)['phone'] == '—')
    pg.fill('#booking-date', TODAY)
    s_today = pg.evaluate("[...document.querySelectorAll('#booking-time option')].slice(1).map(o=>o.value)")
    check('Hoy (15:10): solo se ofrecen horas posteriores', s_today == ['15:30', '16:00', '16:30', '17:00', '17:30', '18:00', '18:30', '19:00', '19:30'], str(s_today))
    check('La hora elegida (11:30) se descarta si ya no aplica', S(pg)['time'] == '—' and pg.input_value('#booking-time') == '')
    pg.screenshot(path=f'{OUT}/reservas-sincronizado-1280.png')
    pg.context.close()

    # ---------- Validación y WhatsApp ----------
    pg = page(viewport={'width': 412, 'height': 915}, is_mobile=True, has_touch=True, device_scale_factor=2.6)
    pg.click('.booking-summary__submit'); pg.wait_for_timeout(200)
    errs = pg.evaluate("Object.fromEntries([...document.querySelectorAll('[data-error-for]')].map(e=>[e.dataset.errorFor, e.hidden?'':e.textContent]))")
    check('Enviar vacío: errores claros en los 4 obligatorios', errs == {'name': 'Ingresa tu nombre completo.', 'serviceId': 'Selecciona un servicio.', 'date': 'Selecciona una fecha.', 'time': 'Selecciona una hora.', 'phone': ''}, str(errs))
    inv = pg.evaluate("[...document.querySelectorAll('[aria-invalid=\"true\"]')].map(e=>e.name)")
    check('Campos con error marcados con aria-invalid', inv == ['name', 'serviceId', 'date', 'time'], str(inv))
    check('Mensaje accesible en el resumen (role=status)', pg.text_content('[data-booking-status]') == 'Revisa los campos: Nombre completo, Servicio, Fecha deseada, Hora deseada.')
    check('El foco va al primer campo con error', pg.evaluate("document.activeElement.id") == 'booking-name')
    check('No se abre WhatsApp si faltan datos', pg.evaluate('window.__opened.length') == 0)
    pg.screenshot(path=f'{OUT}/reservas-errores-412.png', full_page=False)
    pg.fill('#booking-name', 'Ana')
    check('Corregir un campo retira su error en vivo', pg.evaluate("document.querySelector('[data-error-for=name]').hidden") and pg.get_attribute('#booking-name', 'aria-invalid') is None)
    pg.fill('#booking-date', '2026-10-30')
    check('Fecha pasada rechazada', pg.text_content('[data-error-for=date]') == 'La fecha no puede ser anterior a hoy.')
    pg.fill('#booking-phone', 'abc')
    check('Teléfono inválido rechazado', 'teléfono válido' in pg.text_content('[data-error-for=phone]'))
    pg.fill('#booking-phone', '+56 9 8765 4321')
    pg.select_option('#booking-serviceId', label='Corte Clásico · $12.000')
    pg.fill('#booking-date', FUTURE); pg.select_option('#booking-time', '10:00')
    pg.fill('#booking-notes', 'Primera visita.')
    check('Todo corregido: el aviso de error desaparece', pg.text_content('[data-booking-status]') == '')
    pg.screenshot(path=f'{OUT}/reservas-completo-412.png', full_page=False)
    pg.tap('.booking-summary__submit'); pg.wait_for_timeout(200)
    opened = pg.evaluate('window.__opened')
    check('Datos válidos: abre WhatsApp en una pestaña nueva', len(opened) == 1 and opened[0][1] == '_blank' and 'noopener' in opened[0][2])
    u = urlparse(opened[0][0]); msg = parse_qs(u.query)['text'][0]
    expected = ('Hola, THE GENTLEMAN. Quisiera solicitar una reserva.\n\nNombre: Ana\nServicio: Corte Clásico\nPrecio referencial: $12.000\n'
                'Fecha deseada: Lunes, 9 de noviembre de 2026\nHora deseada: 10:00\nTeléfono: +56 9 8765 4321\nObservaciones: Primera visita.\n\n'
                'Entiendo que esta solicitud debe ser confirmada por el establecimiento.')
    check('Número de demostración 56900000000', u.netloc == 'wa.me' and u.path == '/56900000000', opened[0][0][:40])
    check('Mensaje completo y codificado correctamente', msg == expected and '%0A' in opened[0][0] and ' ' not in opened[0][0], msg.replace('\n', ' ⏎ '))
    pg.evaluate("document.querySelector('.booking-summary').scrollIntoView({block:'center'})"); pg.wait_for_timeout(1300)
    check('Móvil: el resumen aparece al desplazarse hasta él', pg.evaluate("(e=>e.classList.contains('is-visible')&&getComputedStyle(e).opacity==='1')(document.querySelector('.booking-summary'))"))
    check('Confirmación accesible tras abrir WhatsApp', 'Abrimos WhatsApp' in pg.text_content('[data-booking-status]'))
    pg.context.close()

    # ---------- Fuente única: cambiar la tarjeta y el config cambia todo ----------
    def patch_html(route):
        r = route.fetch(); body = r.text().replace('<data value="12000">$12.000</data>', '<data value="99999">$99.999</data>')
        route.fulfill(response=r, body=body)
    pg = page(route=('**/index.html', patch_html), viewport={'width': 412, 'height': 915})
    pg.goto(URL + 'index.html'); pg.wait_for_timeout(300); pg.evaluate(CAPTURE_OPEN)
    pg.select_option('#booking-serviceId', index=1)
    check('Si cambia el precio en la tarjeta, cambian selector y resumen', S(pg)['price'] == '$99.999' and '$99.999' in pg.evaluate("document.querySelector('#booking-serviceId option:nth-child(2)').textContent"))
    pg.context.close()
    def patch_cfg(route):
        r = route.fetch(); route.fulfill(response=r, body=r.text().replace("'56900000000'", "'56911112222'"))
    pg = page(route=('**/js/config.js*', patch_cfg), viewport={'width': 412, 'height': 915})
    pg.fill('#booking-name', 'Ana'); pg.select_option('#booking-serviceId', index=1); pg.fill('#booking-date', FUTURE); pg.select_option('#booking-time', '10:00')
    pg.click('.booking-summary__submit'); pg.wait_for_timeout(200)
    check('El número sale de config.js (cambiarlo allí cambia el enlace)', pg.evaluate('window.__opened[0][0]').startswith('https://wa.me/56911112222?'))
    pg.context.close()

    # ---------- Responsive ----------
    for w, h in ((360, 740), (390, 844), (412, 915), (430, 932), (768, 1024), (1024, 768), (1280, 900), (1920, 1080)):
        pg = page(viewport={'width': w, 'height': h}, device_scale_factor=2 if w < 1000 else 1, has_touch=w < 1000, is_mobile=w < 600)
        pg.fill('#booking-date', '2026-11-11'); pg.wait_for_timeout(1200)
        m = pg.evaluate('''() => {
          const r=s=>document.querySelector(s).getBoundingClientRect();
          const f=r('#booking-form'), s=r('.booking-summary'), b=r('.booking-summary__submit'), d=document.querySelector('.booking__decor');
          const ctrls=[...document.querySelectorAll('.field__input, .booking-summary__submit')].map(e=>e.getBoundingClientRect().height);
          const fonts=[...document.querySelectorAll('#reservas label, #reservas p, #reservas dt, #reservas dd, #reservas input, #reservas select, #reservas button')].map(e=>parseFloat(getComputedStyle(e).fontSize));
          const cut=[...document.querySelectorAll('#reservas dt, #reservas dd, #reservas .field__label, .booking-summary__submit')].some(e=>e.scrollWidth>e.clientWidth+1);
          const btnEl=document.querySelector('.booking-summary__submit');
          const textNode=[...btnEl.childNodes].find(n=>n.nodeType===3&&n.textContent.trim());
          const rg=document.createRange(); rg.selectNodeContents(textNode);
          const tops=new Set([...rg.getClientRects()].filter(r=>r.width>0).map(r=>Math.round(r.top)));
          const sel=document.querySelector('#booking-time'), selCut=sel.scrollWidth>sel.clientWidth+1;
          const dateDD=document.querySelector('[data-summary=date]'); const ddLH=parseFloat(getComputedStyle(dateDD).lineHeight); const dateLines=Math.round(dateDD.getBoundingClientRect().height/ddLH);
          return {btn1:tops.size===1, btnLines:tops.size, selCut, dateLines, ov:document.documentElement.scrollWidth>innerWidth, stacked:s.top>=f.bottom, side:s.left>=f.right, fullBtn:Math.abs(b.width-(document.querySelector('.booking-summary').clientWidth-2*parseFloat(getComputedStyle(document.querySelector('.booking-summary')).paddingLeft)))<1,
                  minCtrl:Math.min(...ctrls), minFont:Math.min(...fonts), decor:getComputedStyle(d).display!=='none', decorLeft:d.getBoundingClientRect().left, cut};
        }''')
        check(f'{w}px: sin scroll horizontal ni textos cortados', not m['ov'] and not m['cut'])
        if w < 1024:
            check(f'{w}px: formulario primero y resumen debajo', m['stacked'])
        else:
            check(f'{w}px: formulario a la izquierda y resumen a la derecha', m['side'])
        check(f'{w}px: botón de WhatsApp a todo el ancho del resumen', m['fullBtn'])
        check(f'{w}px: botón de WhatsApp en una sola línea', m['btn1'], f"{m['btnLines']} línea(s)")
        check(f'{w}px: "Elige una hora" no se corta', not m['selCut'])
        check(f'{w}px: fecha del resumen en ≤ 2 líneas', m['dateLines'] <= 2, f"{m['dateLines']} líneas")
        check(f'{w}px: campos y botón cómodos al tacto (≥ 48px)', m['minCtrl'] >= 48, f"{m['minCtrl']:.0f}px")
        check(f'{w}px: letra mínima ≥ 12px', m['minFont'] >= 12, f"{m['minFont']}px")
        check(f'{w}px: imagen decorativa solo en escritorio amplio', m['decor'] == (w >= 1200) and (not m['decor'] or m['decorLeft'] <= 1))
        if w in (360, 412, 768, 1280, 1920):
            sec = pg.evaluate("(()=>{const r=document.querySelector('#reservas').getBoundingClientRect();return [r.top+scrollY, r.height]})()")
            pg.screenshot(path=f'{OUT}/reservas-{w}.png', full_page=True, clip={'x': 0, 'y': sec[0], 'width': w, 'height': sec[1]})
        if w == 1280:
            pg.evaluate("document.querySelector('.field--placeholder')");
            # Dentro del rango real del sticky: 120 px después del inicio de la composición
            pg.evaluate("document.documentElement.style.scrollBehavior='auto'; window.scrollTo(0, document.querySelector('.booking__layout').getBoundingClientRect().top + scrollY + 120)"); pg.wait_for_timeout(200)
            t = pg.evaluate("document.querySelector('.booking-summary').getBoundingClientRect().top")
            check('Escritorio: el resumen acompaña al formulario al desplazarse (sticky)', 20 <= t <= 40, f'top {t:.0f}px')
            # Teclado
            pg.focus('#booking-name'); order = ['booking-name']
            for _ in range(12):
                pg.keyboard.press('Tab'); cur = pg.evaluate("document.activeElement.id || document.activeElement.className")
                if cur != order[-1]: order.append(cur)  # La fecha tiene paradas internas (día/mes/año)
                if 'submit' in cur: break
            check('Teclado: orden lógico hasta el botón de WhatsApp', order == ['booking-name', 'booking-serviceId', 'booking-date', 'booking-time', 'booking-phone', 'booking-notes', 'btn btn--gold booking-summary__submit'], ' → '.join(order))
            pg.focus('#booking-phone'); pg.keyboard.press('Shift+Tab'); pg.keyboard.press('Tab')
            check('Foco visible en los campos', pg.evaluate("getComputedStyle(document.activeElement).outlineStyle") == 'solid')
            for sel, prop, need, bg in (('.field__label', 'color', 4.5, None), ('#booking-name', 'color', 4.5, None), ('#booking-name', 'placeholder', 4.5, '#booking-name'),
                                        ('#booking-name', 'border', 3, '#reservas'), ('.field__req', 'color', 3, None), ('.booking-summary__row dt', 'color', 4.5, None),
                                        ('.booking-summary__row dd', 'color', 4.5, None), ('.booking-summary__notice p', 'color', 4.5, '.booking-summary'),
                                        ('.booking-summary__submit', 'color', 4.5, None), ('.booking-summary__demo', 'color', 4.5, None), ('.field__hint', 'color', 4.5, None)):
                r = pg.evaluate(CONTRAST_JS, [sel, prop, bg]); check(f'Contraste {sel} ({prop})', r >= need, f'{r}:1')
            pg.click('.booking-summary__submit'); pg.wait_for_timeout(150)
            r = pg.evaluate(CONTRAST_JS, ['[data-error-for=name]', 'color', None]); check('Contraste del mensaje de error', r >= 4.5, f'{r}:1')
        pg.context.close()

    # ---------- Movimiento reducido y sin JavaScript ----------
    pg = page(viewport={'width': 412, 'height': 839}, reduced_motion='reduce')
    check('Movimiento reducido: sección visible sin esperar', pg.evaluate("[...document.querySelectorAll('#reservas [data-reveal]')].every(e=>getComputedStyle(e).opacity==='1')"))
    pg.context.close()
    ctx = b.new_context(viewport={'width': 412, 'height': 839}, java_script_enabled=False); pg = ctx.new_page(); pg.goto(URL)
    check('Sin JavaScript: aviso visible para enviar la solicitud', pg.is_visible('.booking-form__noscript'))
    ctx.close()

    check('Sin errores de consola ni recursos rotos', not errors, '; '.join(errors[:3]))
    b.close()

ok = sum(r[0] for r in results)
for r in results:
    print(('OK   ' if r[0] else 'FALLA'), r[1], ('· ' + r[2]) if r[2] else '')
print(f'\n{ok}/{len(results)} pruebas superadas')
