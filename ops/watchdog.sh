#!/usr/bin/env bash
set -euo pipefail
cd /home/ubuntu/leo-project/multica
systemctl is-active --quiet multica.service || exit 0
for attempt in 1 2 3; do
    if curl --fail --silent --max-time 10 http://127.0.0.1:8080/readyz >/dev/null && curl --fail --silent --max-time 10 http://127.0.0.1:3000/login >/dev/null; then
        systemctl is-active --quiet multica-proxy.service || systemctl start multica-proxy.service
        exit 0
    fi
    sleep 5
done
echo 'Multica readiness failed three times; recovering containers.' >&2
compose=(docker compose -f docker-compose.selfhost.yml -f ops/compose.production.yml)
"${compose[@]}" up -d
"${compose[@]}" restart backend frontend
