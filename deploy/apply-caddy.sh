#!/bin/sh
set -eu

candidate="/home/goodpapa/wordstat-gpt-proxy/deploy/Caddyfile.goodpapa12"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup="/etc/caddy/Caddyfile.backup.wordstat.${timestamp}"

caddy validate --config "${candidate}"
cp -a /etc/caddy/Caddyfile "${backup}"
install -o root -g root -m 644 "${candidate}" /etc/caddy/Caddyfile
systemctl reload caddy
systemctl is-active --quiet caddy

printf 'Caddy reloaded. Backup: %s\n' "${backup}"
