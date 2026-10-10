#!/usr/bin/env python3
"""Issue a session for the explicitly configured shared Multica account."""
import base64
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import secrets
import time
import urllib.request
from urllib.parse import urlsplit
import uuid

SECRET = os.environ['JWT_SECRET'].encode()
USER_ID = os.environ['MULTICA_DEFAULT_USER_ID']
EMAIL = os.environ['MULTICA_DEFAULT_EMAIL']
NAME = os.environ['MULTICA_DEFAULT_NAME']
DESTINATION = '/leo/issues'
TTL = 30 * 24 * 3600


def destination(path):
    parsed = urlsplit(path)
    if parsed.scheme or parsed.netloc or '\\' in path or any(ord(c) < 32 for c in path):
        return DESTINATION
    if parsed.path.startswith('/leo/'):
        return path
    return DESTINATION


def authenticated(cookie):
    if not cookie:
        return False
    request = urllib.request.Request('http://127.0.0.1:8080/api/me', headers={'Cookie': cookie})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return bool(json.load(response).get('id'))
    except Exception:
        return False


def b64(value):
    return base64.urlsafe_b64encode(value).rstrip(b'=')


def session():
    now = int(time.time())
    sid = str(uuid.uuid4())
    claims = {'sub': USER_ID, 'email': EMAIL, 'name': NAME, 'sid': sid,
              'iat': now, 'exp': now + TTL}
    payload = b'.'.join(b64(json.dumps(part, separators=(',', ':')).encode())
                        for part in ({'alg': 'HS256', 'typ': 'JWT'}, claims))
    token = (payload + b'.' + b64(hmac.digest(SECRET, payload, 'sha256'))).decode()
    def csrf(key, prefix=b''):
        nonce = secrets.token_bytes(16)
        return nonce.hex() + '.' + hmac.digest(key, prefix + nonce, 'sha256').hex()
    return token, csrf(token.encode()), csrf(SECRET, sid.encode() + b'\0')


class Login(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/session-check' and authenticated(self.headers.get('Cookie', '')):
            self.send_response(200)
            self.send_header('Content-Length', '0')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            return
        if path not in ('/', '/login', '/signup', '/register', '/leo', '/session-check') and not path.startswith('/leo/'):
            self.send_error(404)
            return
        token, csrf_token, csrf_session = session()
        # Fail closed if the shared account is unavailable or backend auth changes.
        request = urllib.request.Request('http://127.0.0.1:8080/api/me',
                                         headers={'Authorization': 'Bearer ' + token})
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                user = json.load(response)
            if user.get('id') != USER_ID:
                raise ValueError('Unexpected default user')
        except Exception:
            self.send_error(503, 'Default account unavailable')
            return
        self.send_response(302)
        requested_path = self.headers.get('X-Forwarded-Uri', '') if path == '/session-check' else self.path
        self.send_header('Location', destination(requested_path))
        self.send_header('Cache-Control', 'no-store')
        for name, value, http_only in (
            ('multica_auth', token, True), ('multica_csrf', csrf_token, False),
            ('multica_csrf_session', csrf_session, False),
        ):
            cookie = f'{name}={value}; Path=/; Max-Age={TTL}; Secure; SameSite=Strict'
            if http_only:
                cookie += '; HttpOnly'
            self.send_header('Set-Cookie', cookie)
        self.send_header('Content-Length', '0')
        self.end_headers()

    def log_message(self, format, *args):
        # Do not log URLs, cookies, or session material.
        pass


if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', 8091), Login).serve_forever()
