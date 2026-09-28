#!/usr/bin/env python3
"""Check shared auth cookie forwarding using isolated Nginx and synthetic credentials."""
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
parser.add_argument('--locations', required=True, type=Path)
parser.add_argument('--auth', required=True, type=Path)
parser.add_argument('--nginx', default='nginx')
args = parser.parse_args()
cookie = '__Host-portal_device=synthetic; Path=/; Max-Age=34560000; HttpOnly; Secure; SameSite=Strict'


class Upstream(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/auth/check':
            authorized = self.headers.get('Cookie') == '__Host-portal_device=synthetic'
            self.send_response(204 if authorized else 401)
            if authorized:
                self.send_header('Set-Cookie', cookie)
        else:
            self.send_response(401 if self.path == '/auth/required' else 200)
        self.end_headers()

    def log_message(self, *unused):
        pass


upstream = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Upstream)
thread = threading.Thread(target=upstream.serve_forever, daemon=True)
thread.start()
process = None
try:
    with tempfile.TemporaryDirectory(prefix='portal-cookie-check-') as directory:
        temporary = Path(directory)
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            port = reservation.getsockname()[1]
        apps = ['ledger', 'feetable', 'fabricworld', 'recipebox', 'yuyan']
        locations = []
        for index, app in enumerate(apps):
            locations.append((args.locations / (app + '.conf')).read_text().replace(
                '127.0.0.1:' + str(18080 + index), '127.0.0.1:' + str(upstream.server_port)))
        auth = args.auth.read_text().replace('127.0.0.1:18085', '127.0.0.1:' + str(upstream.server_port))
        config = temporary / 'nginx.conf'
        config.write_text('daemon off; master_process off;\n'
                          f'pid {temporary}/pid; error_log {temporary}/error.log;\n'
                          'events {}\nhttp { access_log off; server {\n'
                          f'listen 127.0.0.1:{port};\n' + auth + '\n' + '\n'.join(locations) + '\n}}')
        command = [args.nginx, '-p', str(temporary) + '/', '-c', str(config)]
        subprocess.run(command + ['-t'], check=True, capture_output=True)
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=.2):
                    break
            except OSError:
                time.sleep(.05)
        checks = 0
        for app in apps:
            for credential in ['synthetic', '', 'invalid']:
                headers = {'Cookie': '__Host-portal_device=' + credential} if credential else {}
                request = urllib.request.Request(f'http://127.0.0.1:{port}/{app}/healthz', headers=headers)
                try:
                    response = urllib.request.urlopen(request, timeout=3)
                except urllib.error.HTTPError as error:
                    response = error
                with response:
                    assert response.status == (200 if credential == 'synthetic' else 401), app
                    assert response.headers.get_all('Set-Cookie', []) == ([cookie] if credential == 'synthetic' else []), app
                checks += 1
        print(f'PASS {checks} checks: all five apps renew only valid credentials, once, preserving cookie attributes.')
finally:
    if process is not None and process.poll() is None:
        process.terminate()
        process.wait(timeout=5)
    upstream.shutdown()
    thread.join(timeout=5)
    upstream.server_close()
