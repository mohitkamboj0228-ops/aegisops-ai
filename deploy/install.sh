#!/usr/bin/env bash
# Run as root on the dedicated Amazon Linux 2023 host, from an uploaded release.
set -euo pipefail
release_root="$(cd "$(dirname "$0")/.." && pwd)"
release_hash="$(cat "$release_root/RELEASE_ID")"
[[ "$release_hash" =~ ^[a-f0-9]{64}$ ]] || { echo 'Invalid release identifier'; exit 1; }
id aegis >/dev/null 2>&1 || useradd --system --home-dir /var/lib/aegis --shell /sbin/nologin aegis
mkdir -p /var/lib/aegis/backups /opt/aegis/releases
chown -R aegis:aegis /var/lib/aegis
chmod 700 /var/lib/aegis /var/lib/aegis/backups
if [[ -f /var/lib/aegis/aegis.db ]]; then
  python3 - <<'PY'
import sqlite3, time
with sqlite3.connect('/var/lib/aegis/aegis.db') as src, sqlite3.connect('/var/lib/aegis/backups/predeploy-'+str(time.time_ns())+'.db') as dst:
    src.backup(dst)
PY
fi
release_dir="/opt/aegis/releases/$release_hash"
if [[ ! -d "$release_dir" ]]; then
  mkdir -p "$release_dir"
  cp -a "$release_root/." "$release_dir/"
fi
[[ -x "$release_dir/.venv/bin/python" ]] || python3 -m venv "$release_dir/.venv"
"$release_dir/.venv/bin/python" -m pip install --disable-pip-version-check -r "$release_dir/backend/requirements-ai.txt"
# Atomic release switch; previous releases are preserved for operator rollback.
previous_release="$(readlink -f /opt/aegis/current || true)"
ln -sfn "$release_dir" /opt/aegis/next
mv -Tf /opt/aegis/next /opt/aegis/current
cat > /etc/systemd/system/aegisops.service <<'UNIT'
[Unit]
Description=AegisOps policy workspace
After=network-online.target
Wants=network-online.target
[Service]
User=aegis
Group=aegis
WorkingDirectory=/opt/aegis/current
EnvironmentFile=/etc/aegisops.env
ExecStart=/opt/aegis/current/.venv/bin/python backend/server.py
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/var/lib/aegis
UMask=0077
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable aegisops
systemctl restart aegisops
for attempt in $(seq 1 30); do
  if curl --fail --silent http://127.0.0.1:8080/api/health >/dev/null; then
    echo "AegisOps healthy; release $release_hash"
    exit 0
  fi
  sleep 2
done
if [[ -n "$previous_release" && "$previous_release" != "$release_dir" ]]; then
  ln -sfn "$previous_release" /opt/aegis/next
  mv -Tf /opt/aegis/next /opt/aegis/current
  systemctl restart aegisops
  echo "Restored previous application release: $previous_release" >&2
fi
echo 'Health check failed. Inspect journalctl -u aegisops and restore /opt/aegis/current to a previous release.' >&2
exit 1
