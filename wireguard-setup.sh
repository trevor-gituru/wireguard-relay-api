#!/usr/bin/env bash

# Exit immediately if a command fails (-e), 
# treat unset variables as errors (-u), 
# and ensure that any failure in a pipeline is caught (-o pipefail).
# This makes the script safer and prevents it from continuing in an unexpected state.
set -euo pipefail

WG_DIR="/etc/wireguard"
WG_INTERFACE="wg0"
WG_CONF="${WG_DIR}/${WG_INTERFACE}.conf"
PRIVATE_KEY_FILE="${WG_DIR}/relay_private.key"
PUBLIC_KEY_FILE="${WG_DIR}/relay_public.key"
# SCRIPT_DIR: directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"


echo "[+] Starting WireGuard relay setup..."

# Ensure script is run as root
if [[ "$EUID" -ne 0 ]]; then
  echo "[-] Please run as root"
  exit 1
fi

echo "[+] Installing WireGuard..."
apt update -y
apt install -y wireguard

echo "[+] Creating WireGuard directory..."
mkdir -p "${WG_DIR}"
chmod 700 "${WG_DIR}"

# Generate keys only if they don't already exist
if [[ ! -f "${PRIVATE_KEY_FILE}" ]]; then
  echo "[+] Generating WireGuard keys..."
  wg genkey | tee "${PRIVATE_KEY_FILE}" | wg pubkey > "${PUBLIC_KEY_FILE}"
  chmod 600 "${PRIVATE_KEY_FILE}"
else
  echo "[+] WireGuard keys already exist, skipping generation"
fi

PRIVATE_KEY=$(cat "${PRIVATE_KEY_FILE}")
PUBLIC_KEY=$(cat "${PUBLIC_KEY_FILE}")

# Create wg0.conf if it doesn't exist
if [[ ! -f "${WG_CONF}" ]]; then
  echo "[+] Creating WireGuard interface config..."
  cat <<EOF > "${WG_CONF}"
[Interface]
Address = 10.10.0.1/24
ListenPort = 51820
PrivateKey = ${PRIVATE_KEY}
SaveConfig = false
EOF
  chmod 600 "${WG_CONF}"
else
  echo "[+] ${WG_CONF} already exists, skipping"
fi

# Enable IPv4 forwarding & Make the change permanent across reboots
echo "[+] Enabling IP forwarding..."
sysctl -w net.ipv4.ip_forward=1
grep -q "net.ipv4.ip_forward=1" /etc/sysctl.conf || \
  echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf

# Bring up WireGuard interface if not already up
if ! wg show "${WG_INTERFACE}" &>/dev/null; then
  echo "[+] Starting WireGuard interface..."
  wg-quick up "${WG_INTERFACE}"
else
  echo "[+] WireGuard interface already running"
fi

echo "[+] Enabling WireGuard on boot..."
systemctl enable "wg-quick@${WG_INTERFACE}"

echo "[+] Ensuring RELAY_PUBLIC_KEY is set in ${ENV_FILE}..."

# Create .env file if it does not exist
if [[ ! -f "${ENV_FILE}" ]]; then
  touch "${ENV_FILE}"
  chmod 600 "${ENV_FILE}"
fi

# Check if RELAY_PUBLIC_KEY already exists
if grep -q "^RELAY_PUBLIC_KEY=" "${ENV_FILE}"; then
  CURRENT_KEY=$(grep "^RELAY_PUBLIC_KEY=" "${ENV_FILE}" | cut -d= -f2-)

  if [[ "${CURRENT_KEY}" == "${PUBLIC_KEY}" ]]; then
    echo "[+] RELAY_PUBLIC_KEY already up to date"
  else
    echo "[+] Updating RELAY_PUBLIC_KEY in ${ENV_FILE}"
    sed -i "s|^RELAY_PUBLIC_KEY=.*|RELAY_PUBLIC_KEY=${PUBLIC_KEY}|" "${ENV_FILE}"
  fi
else
  echo "[+] Adding RELAY_PUBLIC_KEY to ${ENV_FILE}"
  echo "RELAY_PUBLIC_KEY=${PUBLIC_KEY}" >> "${ENV_FILE}"
fi

echo "[+] WireGuard relay setup complete."
echo "[+] Relay public key:"
echo "${PUBLIC_KEY}"

