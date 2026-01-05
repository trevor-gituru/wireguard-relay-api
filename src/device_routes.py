# src/device_routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator
from src.device_store import device_store
from src.wireguard_manager import wg_manager
from src.config import settings
from src.logger import logger

router = APIRouter()

# ------------------------------
# Request models
# ------------------------------
class RegisterDeviceRequest(BaseModel):
    serial: str = Field(..., min_length=1, description="Device serial must not be empty")
    public_key: str = Field(..., min_length=44, max_length=44, description="WireGuard public key must be 44 characters Base64")

    @validator("public_key")
    def valid_base64_key(cls, v):
        import base64
        try:
            # decode to check valid Base64
            decoded = base64.b64decode(v, validate=True)
            if len(decoded) != 32:
                raise ValueError("Public key must decode to 32 bytes")
        except Exception:
            raise ValueError("Invalid Base64 public key")
        return v


class RemoveDeviceRequest(BaseModel):
    serial: str = Field(..., min_length=1, description="Device serial must not be empty")


# ------------------------------
# Endpoints
# ------------------------------
@router.post("/register")
def register_device(req: RegisterDeviceRequest):
    """
    Register a new device:
    1. Store it in devices.json
    2. Add it as a WireGuard peer
    3. Return assigned IP and relay public key
    If adding to WireGuard fails, remove the device from JSON.
    """
    try:
        logger.info("Attempting to register device: %s", req.serial)

        # 1️⃣ Register in devices.json
        device = device_store.register_device(req.serial, req.public_key)
        logger.info("Device %s registered in JSON with IP %s.%s",
                    req.serial, device['network'], device['ip_last_octet'])
        try:
            # 2️⃣ Add to WireGuard
            wg_manager.add_peer(device)
            logger.info("Device %s added to WireGuard successfully", req.serial)
        except Exception as wg_error:
            # Rollback JSON registration if WireGuard fails
            device_store.remove_device(req.serial)
            logger.error("Failed to add device %s to WireGuard: %s. Rolled back JSON entry.", req.serial, str(wg_error))
            raise RuntimeError(f"Failed to add to WireGuard: {wg_error}")

        # 3️⃣ Return IP and relay public key
        return {
            "assigned_ip": f"{device['network']}.{device['ip_last_octet']}",
            "relay_public_key": settings.RELAY_PUBLIC_KEY
        }

    except ValueError as e:
        logger.warning("Registration failed for device %s: %s", req.serial, str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.error("Runtime error during registration for device %s: %s", req.serial, str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error during registration for device %s", req.serial)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.post("/remove")
def remove_device(req: RemoveDeviceRequest):
    """
    Remove a device:
    1. Remove from WireGuard
    2. Remove from devices.json
    """
    try:
        logger.info("Attempting to remove device: %s", req.serial)
        device = device_store.get_device(req.serial)

        wg_manager.remove_peer(device["public_key"])
        device_store.remove_device(req.serial)
        logger.info("Device %s removed successfully", req.serial)

        return {"detail": f"Device {req.serial} removed successfully"}

    except ValueError as e:
        logger.warning("Remove failed for device %s: %s", req.serial, str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        logger.error("Runtime error during removal for device %s: %s", req.serial, str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error during removal for device %s", req.serial)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/list")
def list_devices():
    """
    List all registered devices.
    """
    try:
        devices = device_store.list_devices()
        # Include full IP for convenience
        result = {
            serial: {
                **device,
                "full_ip": f"{device.get('network', '10.10.0')}.{device['ip_last_octet']}"
            }
            for serial, device in devices.items()
        }
        logger.info("Listed %d devices", len(result))
        return result

    except Exception as e:
        logger.exception("Unexpected error while listing devices")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

