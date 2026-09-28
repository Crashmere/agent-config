#!/usr/bin/env python3
"""Check any site's real HTML and anonymous HTTPS branding resources (standard library only)."""
import argparse
from html.parser import HTMLParser
import json
import struct
import sys
from urllib.parse import urljoin, urlsplit
from urllib.request import build_opener, HTTPRedirectHandler, Request


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Head(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.base = None
        self.finished = False

    def handle_starttag(self, tag, attributes):
        if self.finished:
            return
        attrs = dict(attributes)
        if tag == 'base' and self.base is None:
            self.base = attrs.get('href')
        if tag == 'link':
            self.links.append(attrs)

    def handle_endtag(self, tag):
        if tag == 'head':
            self.finished = True


def check(page_url, public_url):
    origin = urlsplit(public_url)
    if origin.scheme != 'https' or not origin.netloc or origin.username or origin.password:
        raise ValueError('--public-url must be an HTTPS page URL without credentials')
    # No cookie jar, Authorization header, certificate bypass or redirect following.
    client = build_opener(NoRedirect)

    def fetch(url, method='GET'):
        request = Request(url, method=method, headers={'User-Agent': 'SiteIconCheck/1.0'})
        with client.open(request, timeout=15) as response:
            if response.status != 200:
                raise ValueError(f'{method}: expected 200, got {response.status}')
            body = response.read(2 * 1024 * 1024 + 1)
            if len(body) > 2 * 1024 * 1024:
                raise ValueError('HTML/icon/manifest exceeds 2 MiB check limit')
            return response.headers.get_content_type(), body

    content_type, html = fetch(page_url)
    if content_type != 'text/html':
        raise ValueError('page source must return HTML')
    head = Head()
    head.feed(html.decode('utf-8'))
    base = urljoin(public_url, head.base or '')

    def asset_url(reference, relative_to=base):
        url = urljoin(relative_to, reference)
        parsed = urlsplit(url)
        if (parsed.scheme, parsed.netloc) != (origin.scheme, origin.netloc):
            raise ValueError('branding resource must use the same HTTPS origin')
        if parsed.username or parsed.password:
            raise ValueError('branding resource URL must not contain credentials')
        return url

    checked = {}

    def resource(url):
        if url not in checked:
            mime, body = fetch(url)
            head_mime, _ = fetch(url, 'HEAD')
            if mime != head_mime:
                raise ValueError('GET and HEAD Content-Type disagree')
            checked[url] = (mime, body)
        return checked[url]

    def picture(url, touch=False):
        mime, body = resource(url)
        if not mime.startswith('image/'):
            raise ValueError('icon did not return an image Content-Type')
        if mime == 'image/png' or touch:
            if mime != 'image/png' or body[:8] != b'\x89PNG\r\n\x1a\n' or len(body) < 33:
                raise ValueError('PNG icon has wrong type or signature')
            width, height = struct.unpack('>II', body[16:24])
            if touch and (width, height) != (180, 180):
                raise ValueError('apple-touch-icon must be 180 x 180')
        elif mime == 'image/svg+xml':
            if b'<svg' not in body:
                raise ValueError('SVG icon has no svg element')
        elif mime in ('image/x-icon', 'image/vnd.microsoft.icon'):
            if body[:4] != b'\x00\x00\x01\x00':
                raise ValueError('ICO icon has wrong signature')
        else:
            raise ValueError(f'unsupported branding image type: {mime}')

    touch_count = favicon_count = 0
    for link in head.links:
        rel = (link.get('rel') or '').lower().split()
        if not any(value in rel for value in ('icon', 'apple-touch-icon', 'manifest')):
            continue
        href = link.get('href')
        if not href:
            raise ValueError('icon/manifest link is missing href')
        url = asset_url(href)
        if 'apple-touch-icon' in rel:
            picture(url, touch=True)
            touch_count += 1
        elif 'icon' in rel:
            picture(url)
            favicon_count += 1
        elif 'manifest' in rel:
            mime, body = resource(url)
            if mime not in ('application/manifest+json', 'application/json'):
                raise ValueError('manifest did not return JSON Content-Type')
            manifest = json.loads(body)
            if not manifest.get('icons'):
                raise ValueError('manifest has no icons')
            for icon in manifest['icons']:
                picture(asset_url(icon['src'], url))
    if not touch_count or not favicon_count:
        raise ValueError('page must declare both apple-touch-icon and favicon')
    print(f'PASS {origin.path}: {len(checked)} resources; anonymous GET/HEAD, '
          'MIME/signatures, 180x180 touch icon and manifest references')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--page-url', required=True, help='trusted local upstream HTML page URL')
    parser.add_argument('--public-url', required=True, help='corresponding public HTTPS page URL')
    args = parser.parse_args()
    try:
        check(args.page_url, args.public_url)
    except Exception as error:
        # Avoid printing credentials, HTML, production addresses or business content.
        message = str(error) if isinstance(error, ValueError) else type(error).__name__
        print('FAIL: ' + message, file=sys.stderr)
        sys.exit(1)
