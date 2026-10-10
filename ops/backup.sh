#!/usr/bin/env bash
set -euo pipefail
umask 077
cd /home/ubuntu/leo-project/multica
backup_root=/var/backups/multica
install -d -m 700 "$backup_root"
backup_temp=$(mktemp -d "$backup_root/.pending-XXXXXXXX")
trap 'rm -rf "$backup_temp"' EXIT
compose=(docker compose -f docker-compose.selfhost.yml -f ops/compose.production.yml)
"${compose[@]}" exec -T postgres pg_dump -U multica -d multica -Fc > "$backup_temp/database.dump"
"${compose[@]}" exec -T backend tar -C /app/data/uploads -czf - . > "$backup_temp/uploads.tar.gz"
cp .env "$backup_temp/deployment.env"
cp ops/compose.production.yml "$backup_temp/compose.production.yml"
backup_destination="$backup_root/$(date -u +%Y%m%dT%H%M%SZ)"
mv "$backup_temp" "$backup_destination"
find "$backup_root" -mindepth 1 -maxdepth 1 -type d -name '20*' -mtime +14 -exec rm -rf -- {} +
echo "Backup complete: $backup_destination"
