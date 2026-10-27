"""Warm immutable Next assets into Caddy's local cache; never cache page/API data."""
import concurrent.futures
import gzip
import http.cookiejar
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request


def save_asset(reference, target, compress):
    path=urllib.parse.unquote(urllib.parse.urlsplit(reference).path)
    if not path.startswith('/_next/static/') or '..' in Path(path).parts:
        raise ValueError('Only immutable Next static assets may be cached')
    url='http://127.0.0.1:3000'+urllib.parse.quote(path,safe='/@()-._~')
    with urllib.request.urlopen(url,timeout=30) as response:
        body=response.read(20*1024*1024)
        if response.status!=200:raise ValueError('Asset unavailable')
    destination=target/path.lstrip('/')
    destination.parent.mkdir(parents=True,exist_ok=True)
    for filename,data in [(destination,body),(Path(str(destination)+'.gz'),gzip.compress(body,compresslevel=9,mtime=0)),(Path(str(destination)+'.br'),compress(body))]:
        temporary=filename.with_name(filename.name+'.next')
        temporary.write_bytes(data);temporary.chmod(0o644);os.replace(temporary,filename)
    return len(body),Path(str(destination)+'.gz').stat().st_size,Path(str(destination)+'.br').stat().st_size


def warm(target):
    try:
        import brotli
        compress=lambda data:brotli.compress(data,quality=9)
    except ImportError:
        import subprocess
        program="const z=require('node:zlib'),s=[];process.stdin.on('data',d=>s.push(d)).on('end',()=>process.stdout.write(z.brotliCompressSync(Buffer.concat(s),{params:{[z.constants.BROTLI_PARAM_QUALITY]:9}})));"
        compress=lambda data:subprocess.run(['node','-e',program],input=data,stdout=subprocess.PIPE,check=True).stdout
    # The existing shared-login endpoint supplies cookies in memory. Never log
    # headers, cookies, page contents or personal task data.
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    with opener.open('https://d.58nft.net:9447/login',timeout=30) as response:html=response.read().decode()
    references=sorted(set(re.findall(r'(?:src|href)="(/_next/static/[^"?]+\.(?:js|css))',html)))
    if not references:raise ValueError('No Next assets found')
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        sizes=list(pool.map(lambda reference:save_asset(reference,target,compress),references))
    return {'assets':len(sizes),'raw_bytes':sum(s[0] for s in sizes),'gzip_bytes':sum(s[1] for s in sizes),'brotli_bytes':sum(s[2] for s in sizes)}

if __name__=='__main__':
    print(json.dumps(warm(Path(sys.argv[1] if len(sys.argv)>1 else '/srv/multica-assets'))))
