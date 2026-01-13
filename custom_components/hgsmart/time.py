"""Time platform for HGSmart Pet Feeder."""
import logging
from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import HGSmartApiClient
from .const import DOMAIN, SCHEDULE_SLOTS
from .coordinator import HGSmartDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HGSmart time entities."""
    coordinator: HGSmartDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api: HGSmartApiClient = hass.data[DOMAIN][entry.entry_id]["api"]

    entities = []
    for device_id, device_data in coordinator.data.items():
        device_info = device_data["device_info"]
        
        # Add time entity for each schedule slot
        for slot in range(SCHEDULE_SLOTS):
            entities.append(
                HGSmartScheduleTime(coordinator, api, device_id, device_info, slot)
            )

    async_add_entities(entities)


class HGSmartScheduleTime(CoordinatorEntity, TimeEntity):
    """Time entity for feeding schedule."""

    def __init__(
        self,
        coordinator: HGSmartDataUpdateCoordinator,
        api: HGSmartApiClient,
        device_id: str,
        device_info: dict,
        slot: int,
    ) -> None:
        """Initialize the time entity."""
        super().__init__(coordinator)
        self.api = api
        self.device_id = device_id
        self.slot = slot
        self._attr_unique_id = f"{device_id}_schedule_{slot}_time"
        self._attr_name = f"{device_info['name']} Schedule {slot + 1} Time"
        self._attr_icon = "mdi:clock-time-four-outline"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_id)},
            "name": device_info["name"],
            "manufacturer": "HGSmart",
            "model": device_info["type"],
            "sw_version": device_info.get("fwVersion"),
        }

    @property
    def native_value(self) -> time | None:
        """Return the time value."""
        device_data = self.coordinator.data.get(self.device_id)
        if not device_data:
            return None
            
        schedule = device_data.get("schedules", {}).get(self.slot)
        if schedule:
            return time(hour=schedule["hour"], minute=schedule["minute"])
        return None

    async def async_set_value(self, value: time) -> None:
        """Set the time value."""
        device_data = self.coordinator.data.get(self.device_id)
        if not device_data:
            return
            
        # Get current portions from schedule, default to 1
        schedule = device_data.get("schedules", {}).get(self.slot)
        portions = schedule["portions"] if schedule else 1
        
        # Set the schedule with new time
        await self.api.set_feeding_schedule(
            self.device_id,
            self.slot,
            value.hour,
            value.minute,
            portions,
            enabled=True,
        )
        
        # Refresh data
        await self.coordinator.async_request_refresh()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.device_id in self.coordinator.data
        )
