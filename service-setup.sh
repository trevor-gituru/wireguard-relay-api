#!/bin/bash
set -e

WORKDIR="$(pwd)"
VENV_PYTHON="$WORKDIR/venv/bin/python3"
SERVICE_NAME="wg-relay"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

echo "[+] Creating systemd service at $SERVICE_PATH"

sudo tee $SERVICE_PATH > /dev/null <<EOF
[Unit]
Description=WireGuard Relay API
After=network-online.target wg-quick@wg0.service
Wants=network-online.target wg-quick@wg0.service

[Service]
Type=simple
User=root
WorkingDirectory=${WORKDIR}
ExecStart=${VENV_PYTHON} -m src.main
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

echo "[+] Reloading systemd and enabling service"

sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}.service
sudo systemctl start ${SERVICE_NAME}.service

echo "[+] WireGuard Relay service setup complete!"
echo "[+] Check status with: systemctl status ${SERVICE_NAME}.service"

