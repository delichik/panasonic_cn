"""The Panasonic CN switch platform."""
from __future__ import annotations

import logging
from typing import Any, Dict

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import PanasonicCNDataUpdateCoordinator
from .api.devices.base import PanasonicDevice
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Panasonic CN switch platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities = []
    # Iterate through all devices
    for device in coordinator.data.values():
        # Get list of supported entities for the device
        device_entities = device.get_entities()
        
        # Add switch entities
        for entity_info in device_entities:
            if entity_info["type"] == "switch":
                entities.append(
                    PanasonicCNSwitch(
                        coordinator,
                        device,
                        entity_info
                    )
                )
    
    async_add_entities(entities)

class PanasonicCNSwitch(SwitchEntity, CoordinatorEntity):
    """Representation of a Panasonic CN switch."""

    def __init__(
        self,
        coordinator: PanasonicCNDataUpdateCoordinator,
        device: PanasonicDevice,
        entity_info: Dict[str, Any],
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._device = device
        self._entity_info = entity_info
        self._attr_unique_id = f"{DOMAIN}_{entity_info['unique_id']}"
        self._attr_name = entity_info["name"]
        self.entity_id = f"switch.{DOMAIN}_{entity_info['unique_id']}"
        self._data = None

        # Set icon based on entity function
        if "quick_freeze" in entity_info["unique_id"]:
            self._attr_icon = "mdi:snowflake"
        elif "vacation" in entity_info["unique_id"]:
            self._attr_icon = "mdi:beach"
        elif "icing" in entity_info["unique_id"]:
            self._attr_icon = "mdi:ice-cream"
        else:
            self._attr_icon = "mdi:power"

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        if self._data is None:
            self._data = self._device.get_switch_state(self._entity_info["key"])
        return self._data

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._data = self._device.get_switch_state(self._entity_info["key"])

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.async_set_switch_state(self._device.id, True, self._entity_info["key"])

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.async_set_switch_state(self._device.id, False, self._entity_info["key"])

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._device.id)},
            "name": self._device.name,
            "manufacturer": "Panasonic",
            "model": self._device.sub_type,
            "sw_version": "0.0.1",
        }
