# WireGuard Relay API

A Python FastAPI project to manage **edge devices** and dynamically add/remove them as **WireGuard peers**.

This repo provides:

- A REST API to register, remove, and list devices.
- A `device_store` using `JSON` to store device info and assigned IPs.
- Concurrency-safe operations using file locks.
- Automatic WireGuard configuration updates (`wg0.conf`).
- Logging for all device operations.
- A shell script (`wireguard-setup.sh`) to setup the WireGuard relay server.

---

## Table of Contents

1.  [Requirements](#requirements)
2.  [Setup](#setup)
3.  [WireGuard Setup](#wireguard-setup)
4.  [Running the API](#running-the-api)
5.  [API Endpoints](#api-endpoints)
6.  [Logging](#logging)
7.  [Project Structure](#project-structure)
8.  [Notes](#notes)

---

## Requirements

All Python dependencies are listed in `requirements.txt`:

```text
fastapi
uvicorn
python-dotenv
pydantic
```

Install them via pip:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## WireGuard Setup

Run the `wireguard-setup.sh` script to configure the relay server:

```bash
sudo ./wireguard-setup.sh
```

This script will:

- Install WireGuard if not present.
- Generate a private/public key pair for the relay.
- Create `/etc/wireguard/wg0.conf`.
- Enable IP forwarding.
- Enable the interface to start on boot.
- Output the relay public key (needed by clients).

---

## Running the API
**Note:** This API must be run as a superuser (`root`) because it manages WireGuard interfaces.
Activate your virtual environment and start the FastAPI server:

```bash
sudo -i   # or use sudo before commands if not already root
source venv/bin/activate
python3 -m src.main
```

By default, the API listens on `http://0.0.0.0:8000`. You can configure the port in `.env`:

```text
APP_PORT=8000
RELAY_PUBLIC_KEY=<relay_public_key_from_setup>
```

---

## Running as a Service

To run the API as a persistent `systemd` service, use the `service-setup.sh` script. This will ensure the API starts on boot and restarts automatically if it fails.

Run the script with `sudo`:

```bash
sudo ./service-setup.sh
```

This will:
- Create a systemd service file at `/etc/systemd/system/wg-relay.service`.
- Reload the systemd daemon.
- Enable and start the `wg-relay` service.

You can check the status of the service at any time:

```bash
systemctl status wg-relay.service
```

---

## API Endpoints

All endpoints are prefixed with `/devices`.

| Endpoint    | Method | Request Body                            | Description                                           |
| :---------- | :----- | :-------------------------------------- | :---------------------------------------------------- |
| `/register` | `POST` | `{ "serial": "...", "public_key": "..." }` | Register a new device, assign IP, and add it to WireGuard. |
| `/remove`   | `POST` | `{ "serial": "..." }`                     | Remove a device from WireGuard and JSON store.        |
| `/list`     | `GET`  | N/A                                     | List all registered devices and assigned IPs.         |

### Example: Register device

```bash
curl -X POST http://127.0.0.1:8000/devices/register \
  -H "Content-Type: application/json" \
  -d '{
    "serial": "EDGE1234",
    "public_key": "your_device_public_key_here"
  }'
```

**Response:**

```json
{
  "ip": "10.10.0.2",
  "relay_public_key": "relay_public_key_here"
}
```

---

## Logging

All device operations are logged to `relay_api.log` in the project root.

**Example log entries:**

```log
[2026-01-05 09:44:40] INFO: Attempting to register device: test2
[2026-01-05 09:44:40] INFO: Device test2 registered in JSON with IP 10.10.0.4
[2026-01-05 09:44:40] INFO: Device test2 added to WireGuard successfully
```

---

## Project Structure

```
wireguard-relay-api/
│
├── src/
│   ├── main.py               # FastAPI app entrypoint
│   ├── config.py             # Settings loader from .env
│   ├── logger.py             # Logger configuration
│   ├── device_store.py       # DeviceStore class (JSON + concurrency)
│   ├── wireguard_manager.py  # WireGuardManager class
│   ├── device_routes.py      # API router for /devices endpoints
│   └── __init__.py
│
├── devices.json              # JSON file storing device info (created at runtime)
├── wireguard-setup.sh        # Shell script to setup WireGuard relay
├── service-setup.sh          # Shell script to setup the app as a systemd service
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

---

## Notes

- Ensure `devices.json` is writable by the user running the API.
- The API safely handles concurrent access to the JSON file using file locks.
- The WireGuard interface (`wg0`) must be running for peers to be added.
- The relay public key from `wireguard-setup.sh` is required by clients to connect.
