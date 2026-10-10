#!/usr/bin/env python3
"""Configure Gmail SMTP without putting its app password in shell history."""
import argparse
import getpass
import json
import os
from pathlib import Path
import smtplib
import ssl
import subprocess
import tempfile
import time
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser(description='Configure Gmail SMTP and request a Multica login email.')
    parser.add_argument('--email', default='fyhvyhj@gmail.com')
    args = parser.parse_args()
    password = ''.join(getpass.getpass('Gmail app password (hidden): ').split())
    if len(password) != 16 or not password.isascii() or not password.isalnum():
        parser.error('Enter the 16-character Google app password, not your account password.')
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15, context=ssl.create_default_context()) as smtp:
        smtp.login(args.email, password)
    print('Gmail SMTP authentication passed.')
    root = Path(__file__).resolve().parents[1]
    env_file = root / '.env'
    settings = {
        'SMTP_HOST': 'smtp.gmail.com', 'SMTP_PORT': '465', 'SMTP_TLS': 'implicit',
        'SMTP_USERNAME': args.email, 'SMTP_PASSWORD': password,
        'SMTP_FROM_EMAIL': args.email, 'SMTP_TLS_INSECURE': 'false',
        'SMTP_EHLO_NAME': 'd.58nft.net',
    }
    original = env_file.read_text()
    lines = [line for line in original.splitlines() if line.split('=', 1)[0] not in settings]
    lines.extend(f'{key}={value}' for key, value in settings.items())
    fd, filename = tempfile.mkstemp(prefix='.smtp-config-', dir=root)
    try:
        with os.fdopen(fd, 'w') as output:
            output.write('\n'.join(lines) + '\n')
        os.replace(filename, env_file)
    finally:
        Path(filename).unlink(missing_ok=True)
    subprocess.run(['sudo', 'docker', 'compose', '-f', 'docker-compose.selfhost.yml', '-f',
                    'ops/compose.production.yml', 'up', '-d', 'backend'], cwd=root, check=True)
    for attempt in range(30):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8080/readyz', timeout=2):
                break
        except (OSError, urllib.error.URLError):
            if attempt == 29:
                raise RuntimeError('Backend readiness failed; inspect its logs.')
            time.sleep(1)
    request = urllib.request.Request('https://d.58nft.net:9447/auth/send-code',
        data=json.dumps({'email': args.email}).encode(), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            print('Multica accepted the login email request. Check your inbox and spam folder.')
    except urllib.error.HTTPError as error:
        if error.code == 429:
            print('SMTP is configured. Wait 60 seconds, then request a code from the login page.')
        else:
            raise RuntimeError(f'Login email request failed: HTTP {error.code}; inspect backend logs.') from None


if __name__ == '__main__':
    main()
