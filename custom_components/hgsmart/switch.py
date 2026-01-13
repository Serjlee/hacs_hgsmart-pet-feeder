"""Switch platform for HGSmart Pet Feeder."""
import logging

from homeassistant.components.switch import SwitchEntity
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
    """Set up HGSmart switch entities."""
    coordinator: HGSmartDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api: HGSmartApiClient = hass.data[DOMAIN][entry.entry_id]["api"]

    entities = []
    for device_id, device_data in coordinator.data.items():
        device_info = device_data["device_info"]
        
        # Add switch entity for each schedule slot
        for slot in range(SCHEDULE_SLOTS):
            entities.append(
                HGSmartScheduleSwitch(coordinator, api, device_id, device_info, slot)
            )

    async_add_entities(entities)


class HGSmartScheduleSwitch(CoordinatorEntity, SwitchEntity):
    """Switch entity for enabling/disabling feeding schedule."""

    def __init__(
        self,
        coordinator: HGSmartDataUpdateCoordinator,
        api: HGSmartApiClient,
        device_id: str,
        device_info: dict,
        slot: int,
    ) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator)
        self.api = api
        self.device_id = device_id
        self.slot = slot
        self._attr_unique_id = f"{device_id}_schedule_{slot}_enabled"
        self._attr_name = f"{device_info['name']} Schedule {slot + 1} Enabled"
        self._attr_icon = "mdi:alarm-check"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_id)},
            "name": device_info["name"],
            "manufacturer": "HGSmart",
            "model": device_info["type"],
            "sw_version": device_info.get("fwVersion"),
        }

    @property
    def is_on(self) -> bool:
        """Return true if the schedule is enabled."""
        device_data = self.coordinator.data.get(self.device_id)
        if not device_data:
            return False
            
        schedule = device_data.get("schedules", {}).get(self.slot)
        return schedule is not None and schedule.get("enabled", False)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the schedule."""
        device_data = self.coordinator.data.get(self.device_id)
        if not device_data:
            return
            
        # Get current schedule or use defaults
        schedule = device_data.get("schedules", {}).get(self.slot)
        if schedule:
            hour = schedule["hour"]
            minute = schedule["minute"]
            portions = schedule["portions"]
        else:
            hour = 8
            minute = 0
            portions = 1
        
        # Enable the schedule
        await self.api.set_feeding_schedule(
            self.device_id,
            self.slot,
            hour,
            minute,
            portions,
            enabled=True,
        )
        
        # Refresh data
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the schedule."""
        device_data = self.coordinator.data.get(self.device_id)
        if not device_data:
            return
            
        # Get current schedule
        schedule = device_data.get("schedules", {}).get(self.slot)
        if not schedule:
            return
        
        # Disable the schedule
        await self.api.set_feeding_schedule(
            self.device_id,
            self.slot,
            schedule["hour"],
            schedule["minute"],
            schedule["portions"],
            enabled=False,
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
