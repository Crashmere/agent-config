#!/usr/bin/env python3
"""Test candidate app Nginx locations with a private mock upstream, never production data."""
import argparse
import http.server
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--locations', required=True, type=Path, help='directory containing <app>.conf')
parser.add_argument('--nginx', default='nginx')
args = parser.parse_args()
cases = {
    'ledger': (18080, ['favicon.svg', 'favicon-32.png', 'apple-touch-icon.png', 'icon-192.png',
                      'icon-512.png', 'icon-maskable-512.png', 'manifest.webmanifest']),
    'feetable': (18081, ['assets/icon-32-Abc12345.png', 'assets/icon-Abc12345.svg',
                        'assets/apple-touch-icon-Abc12345.png']),
    'fabricworld': (18082, ['favicon.ico', 'fabricworld.svg', 'apple-touch-icon.png']),
    'recipebox': (18083, ['favicon.ico', 'recipebox.svg', 'apple-touch-icon.png']),
    'yuyan': (18084, ['static/favicon.svg', 'static/apple-touch-icon.png']),
}

class Upstream(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(self.path.encode())

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    do_POST = do_GET  # A 403 must come from Nginx, not the mock application.

    def log_message(self, *unused):
        pass

upstream = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Upstream)
thread = threading.Thread(target=upstream.serve_forever, daemon=True)
thread.start()
process = None
try:
    with tempfile.TemporaryDirectory(prefix='portal-icon-access-') as directory:
        temporary = Path(directory)
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            port = reservation.getsockname()[1]
        includes = []
        for app, (app_port, _) in cases.items():
            source = (args.locations / (app + '.conf')).read_text()
            target = temporary / (app + '.conf')
            target.write_text(source.replace('127.0.0.1:' + str(app_port),
                                             '127.0.0.1:' + str(upstream.server_port)))
            includes.append('include ' + str(target) + ';')
        config = temporary / 'nginx.conf'
        config.write_text('daemon off; master_process off;\n'
                          f'pid {temporary}/nginx.pid; error_log {temporary}/error.log;\n'
                          'events {}\nhttp { access_log off; server {\n'
                          f'listen 127.0.0.1:{port};\n'
                          'auth_request /_test_auth;\n'
                          'location = /_test_auth { internal; auth_request off; return 401; }\n'
                          + '\n'.join(includes) + '\nlocation / { return 404; }\n}}\n')
        command = [args.nginx, '-p', str(temporary) + '/', '-c', str(config)]
        check = subprocess.run(command + ['-t'], capture_output=True, text=True)
        if check.returncode:
            raise RuntimeError(check.stderr)
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=.2):
                    break
            except OSError:
                if process.poll() is not None:
                    raise RuntimeError((temporary / 'error.log').read_text())
                time.sleep(.05)
        else:
            raise RuntimeError('Temporary Nginx did not start')

        def fetch(path, method='GET'):
            request = urllib.request.Request(f'http://127.0.0.1:{port}' + path, method=method)
            try:
                response = urllib.request.urlopen(request, timeout=3)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                return response.status, response.read().decode()

        checks = 0
        for app, (_, assets) in cases.items():
            for asset in assets:
                path = '/' + app + '/' + asset
                assert fetch(path + '?v=test') == (200, '/' + asset + '?v=test'), path
                assert fetch(path, 'HEAD')[0] == 200, path
                assert fetch(path, 'POST')[0] == 403, path
                assert fetch(path + '/private')[0] == 401, path
                checks += 4
            for relative in ['', 'search', 'api/private', 'healthz', 'media/private.png',
                             'static/app.js', 'assets/private.png', 'assets/apple-touch-icon-private.js',
                             'data/apple-touch-icon.png', 'apple-touch-icon.png.bak',
                             'manifest.webmanifest/private', 'a/favicon.svg/../../api/private']:
                path = '/' + app + '/' + relative
                assert fetch(path)[0] == 401, path
                checks += 1
        print(f'Passed {checks} checks: only named GET/HEAD branding assets bypass authentication; '
              'pages, APIs, media, unrelated assets and non-read methods stay protected.')
finally:
    if process is not None and process.poll() is None:
        process.terminate()
        process.wait(timeout=5)
    upstream.shutdown()
    thread.join(timeout=5)
    upstream.server_close()
