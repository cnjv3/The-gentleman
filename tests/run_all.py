"""Ejecuta las suites de pruebas de THE GENTLEMAN y muestra el recuento total.

Uso (desde la raíz del repositorio):
    python3 tests/run_all.py                  # las 10 suites
    python3 tests/run_all.py header booking   # solo algunas (nombre sin "test_")

Qué hace:
  1. Comprueba los requisitos (Playwright, Pillow, Chrome, historial de Git, puerto libre).
  2. Sirve la carpeta del repositorio en http://localhost:8771/ (las suites usan esa dirección).
  3. Ejecuta cada suite en orden y guarda su salida completa y sus capturas en tests/output/.
  4. Apaga el servidor y muestra el total. Termina con código 1 si alguna prueba falla.
"""
import os, re, socket, subprocess, sys, time, urllib.request, shutil, importlib.util

TESTS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TESTS)
SUITES_DIR = os.path.join(TESTS, 'suites')
OUTPUT = os.path.join(TESTS, 'output')
PORT = 8771                      # fijo en cada suite: URL = 'http://localhost:8771/'
CHROME = '/usr/bin/google-chrome'  # fijo en cada suite: executable_path='/usr/bin/google-chrome'
OLD_CSS_COMMIT = 'd4daf3e'       # test_fix_mobile.py lee el CSS de este commit con git show

# Orden en que se crearon (etapas 3 a 11). La cifra es la que dio la ejecución sobre 0839655.
SUITES = [
    ('header', 36), ('hero', 85), ('about', 25), ('services', 80), ('gallery', 78),
    ('booking', 127), ('fix_mobile', 49), ('contact', 113), ('footer', 94), ('optim', 47),
]


def fail(msg):
    print(f'\nNo se pueden ejecutar las pruebas: {msg}')
    sys.exit(2)


def preflight():
    for mod, pkg in (('playwright', 'playwright'), ('PIL', 'Pillow')):
        if importlib.util.find_spec(mod) is None:
            fail(f'falta el paquete de Python "{pkg}". Instálalo con: pip install -r tests/requirements.txt')
    if not os.path.isfile(CHROME):
        fail(f'no se encontró Google Chrome en {CHROME} (las suites lo usan con esa ruta exacta).')
    ok = subprocess.run(['git', '-C', REPO, 'cat-file', '-e', f'{OLD_CSS_COMMIT}^{{commit}}'], capture_output=True).returncode == 0
    if not ok:
        fail(f'el repositorio no tiene el commit {OLD_CSS_COMMIT} (¿clon parcial con --depth?). '
             'test_fix_mobile.py lo necesita. Solución: git fetch --unshallow')
    with socket.socket() as s:
        if s.connect_ex(('127.0.0.1', PORT)) == 0:
            fail(f'el puerto {PORT} ya está en uso. Detén el otro servidor y vuelve a intentarlo.')


def start_server():
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1', '-d', REPO],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            urllib.request.urlopen(f'http://localhost:{PORT}/', timeout=1).read()
            return srv
        except OSError:
            time.sleep(0.1)
    srv.terminate()
    fail(f'el servidor local no respondió en el puerto {PORT}.')


def main():
    wanted = [a.removeprefix('test_').removesuffix('.py') for a in sys.argv[1:]]
    unknown = [w for w in wanted if w not in dict(SUITES)]
    if unknown:
        fail(f'suite desconocida: {", ".join(unknown)}. Disponibles: {", ".join(n for n, _ in SUITES)}')
    selected = [(n, e) for n, e in SUITES if not wanted or n in wanted]

    preflight()
    commit = subprocess.run(['git', '-C', REPO, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
    shutil.rmtree(OUTPUT, ignore_errors=True)
    os.makedirs(OUTPUT)
    print(f'THE GENTLEMAN · pruebas sobre el commit {commit or "?"} · servidor http://localhost:{PORT}/\n')

    srv = start_server()
    total_ok = total = 0
    problems = []
    try:
        for name, expected in selected:
            out_dir = os.path.join(OUTPUT, name)
            os.makedirs(out_dir)
            t0 = time.time()
            r = subprocess.run([sys.executable, os.path.join(SUITES_DIR, f'test_{name}.py'), out_dir],
                               cwd=REPO, capture_output=True, text=True)
            secs = time.time() - t0
            log = r.stdout + (('\n--- errores ---\n' + r.stderr) if r.stderr.strip() else '')
            with open(os.path.join(OUTPUT, f'{name}.log'), 'w', encoding='utf-8') as fh:
                fh.write(log)
            m = re.search(r'^(\d+)/(\d+) pruebas superadas$', r.stdout, re.M)
            if not m:
                problems.append(f'{name}: la suite se interrumpió (ver tests/output/{name}.log)')
                print(f'  ERROR  test_{name}.py · se interrumpió antes de terminar ({secs:.0f} s)')
                continue
            ok, n = int(m.group(1)), int(m.group(2))
            total_ok += ok; total += n
            note = '' if n == expected else f' · ojo: se esperaban {expected} pruebas'
            print(f'  {"OK   " if ok == n else "FALLA"}  test_{name}.py  {ok}/{n}  ({secs:.0f} s){note}')
            for line in r.stdout.splitlines():
                if line.startswith('FALLA'):
                    print(f'           {line}')
            if ok != n:
                problems.append(f'{name}: {n - ok} prueba(s) fallaron')
            if n != expected:
                problems.append(f'{name}: {n} pruebas en lugar de {expected}')
    finally:
        srv.terminate()
        srv.wait()

    print(f'\nTotal: {total_ok}/{total} pruebas superadas · {total - total_ok} fallas')
    print(f'Salida completa y capturas: tests/output/')
    if problems:
        print('Revisar:\n  - ' + '\n  - '.join(problems))
    sys.exit(0 if not problems else 1)


if __name__ == '__main__':
    main()
