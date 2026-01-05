from pathlib import Path
import json
import fcntl
from datetime import datetime, timezone
from typing import Dict


class DeviceStore:
    def __init__(self, devices_file: Path):
        self.devices_file = devices_file
        self._ensure_file_exists()


    def _ensure_file_exists(self) -> None:
        if not self.devices_file.exists():
            initial_state = {
                "ip_state": {
                    "free_ips": [],
                    "next_ip": 2,
                    "max_ip": 254,
                    "network": "10.10.0",
                },
                "devices": {},
                "metadata": {
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "version": 1
                }
            }
            self.devices_file.write_text(json.dumps(initial_state, indent=2))
            self.devices_file.chmod(0o600)


    def _load(self, file) -> Dict:
        file.seek(0)
        return json.load(file)


    def _save(self, file, data: Dict) -> None:
        file.seek(0)
        json.dump(data, file, indent=2)
        file.truncate()


    def register_device(self, serial: str, public_key: str) -> Dict:
        with open(self.devices_file, "r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)

            data = self._load(f)

            if serial in data["devices"]:
                raise ValueError("Device already registered")

            if any(d["public_key"] == public_key for d in data["devices"].values()):
                raise ValueError("Public key already registered")

            ip_state = data["ip_state"]

            if ip_state["free_ips"]:
                last_octet = ip_state["free_ips"].pop(0)

            elif ip_state["next_ip"] <= ip_state["max_ip"]:
                last_octet = ip_state["next_ip"]
                ip_state["next_ip"] += 1

            else:
                raise RuntimeError("No available IP addresses")

            device = {
                "serial": serial,
                "public_key": public_key,
                "ip_last_octet": last_octet,
                "added_at": datetime.now(timezone.utc).isoformat()
            }

            data["devices"][serial] = device
            self._save(f, data)
            
            network = ip_state.get("network", "10.10.0")
            device["network"] = network
            return device



    def remove_device(self, serial: str) -> None:
        with open(self.devices_file, "r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)

            data = self._load(f)

            if serial not in data["devices"]:
                raise ValueError("Device not found")

            device = data["devices"].pop(serial)

            last_octet = device["ip_last_octet"]
            data["ip_state"]["free_ips"].append(last_octet)
            data["ip_state"]["free_ips"].sort()

            self._save(f, data)


    def get_device(self, serial: str) -> Dict:
        with open(self.devices_file, "r") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            data = json.load(f)

        if serial not in data["devices"]:
            raise ValueError("Device not found")

        return data["devices"][serial]


    def list_devices(self) -> Dict[str, Dict]:
        with open(self.devices_file, "r") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            return json.load(f)["devices"]


DEVICES_FILE = Path(__file__).parent.parent / "devices.json"
device_store = DeviceStore(DEVICES_FILE)

