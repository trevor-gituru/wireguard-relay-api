import subprocess
from pathlib import Path
import fcntl
from typing import List

class WireGuardManager:
    def __init__(self, interface: str = "wg0", conf_file: str = "/etc/wireguard/wg0.conf"):
        self.interface = interface
        self.conf_file = Path(conf_file)

    def _run(self, cmd: List[str]) -> str:
        """Run a shell command and return stdout."""
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()

    def show(self) -> str:
        """Return WireGuard interface status."""
        try:
            return self._run(["wg", "show", self.interface])
        except subprocess.CalledProcessError:
            return f"[!] Interface {self.interface} not running"

    def add_peer(self, device: dict) -> None:
        """
        Add a peer to WireGuard using a device dict:
        {
            "serial": "...",
            "public_key": "...",
            "ip_last_octet": ...,
            "network": "10.10.0"
        }
        """
        public_key = device["public_key"]
        network = device.get("network", "10.10.0")
        ip_address = f"{network}.{device['ip_last_octet']}"

        # 1️⃣ Update running interface
        try:
            self._run([
                "wg", "set", self.interface,
                "peer", public_key,
                "allowed-ips", f"{ip_address}/32"
            ])
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to add peer: {e.stderr}")

        # 2️⃣ Update wg0.conf safely with file lock
        self._modify_conf(lambda lines: lines + [
            "",
            "[Peer]",
            f"PublicKey = {public_key}",
            f"AllowedIPs = {ip_address}/32"
        ])



    def remove_peer(self, public_key: str) -> None:
        """Remove a peer from WireGuard and wg0.conf safely."""
        # 1️⃣ Remove from running interface
        try:
            self._run([
                "wg", "set", self.interface,
                "peer", public_key,
                "remove"
            ])
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to remove peer: {e.stderr}")

        # 2️⃣ Remove from wg0.conf safely
        def remove_block(lines: list[str]) -> list[str]:
            new_lines = []
            skip = 0
            for i, line in enumerate(lines):
                if f"PublicKey = {public_key}" in line:
                    # Skip this line and previous line if it’s [Peer]
                    if i > 0 and lines[i-1].strip() == "[Peer]":
                        new_lines.pop()  # remove [Peer] line
                    skip = 1  # skip this line
                    continue
                elif skip > 0:
                    skip -= 1
                    continue
                new_lines.append(line)
            return new_lines

        self._modify_conf(remove_block)

    def restart_interface(self) -> None:
        """Restart the WireGuard interface using wg-quick."""
        try:
            self._run(["wg-quick", "down", self.interface])
        except subprocess.CalledProcessError:
            pass  # it's fine if interface was not up
        self._run(["wg-quick", "up", self.interface])

    def _modify_conf(self, modify_func):
        """
        Safely read/write wg0.conf with file locking.
        `modify_func` is a function that takes a list of lines and returns the modified list.
        """
        with self.conf_file.open("r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            lines = f.read().splitlines()
            new_lines = modify_func(lines)
            f.seek(0)
            f.truncate()
            f.write("\n".join(new_lines) + "\n")
            fcntl.flock(f, fcntl.LOCK_UN)

wg_manager = WireGuardManager(interface="wg0", conf_file="/etc/wireguard/wg0.conf")
