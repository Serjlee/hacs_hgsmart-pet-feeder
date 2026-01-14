"""Helper functions for the HGSmart Pet Feeder integration."""
from typing import Any

from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


def get_device_info(device_id: str, device_info: dict[str, Any]) -> DeviceInfo:
    """Build device info dictionary for entities."""
    return DeviceInfo(
        identifiers={(DOMAIN, device_id)},
        name=device_info["name"],
        manufacturer="HGSmart",
        model=device_info["type"],
        sw_version=device_info.get("fwVersion"),
    )
