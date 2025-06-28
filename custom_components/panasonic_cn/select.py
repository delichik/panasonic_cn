"""The Panasonic CN select platform."""
from __future__ import annotations

import logging
from typing import Any, Dict

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api.devices.base import PanasonicDevice
from .const import DOMAIN
from .coordinator import PanasonicCNDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Panasonic CN select platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities = []
    
    # Iterate through all devices
    for device in coordinator.data.values():
        # Get list of supported entities for the device
        device_entities = device.get_entities()
        
        # Add select entities
        for entity_info in device_entities:
            if entity_info["type"] == "select":
                entities.append(
                    PanasonicCNSelect(
                        coordinator,
                        device,
                        entity_info
                    )
                )
    
    async_add_entities(entities)

class PanasonicCNSelect(SelectEntity, CoordinatorEntity):
    """Representation of a Panasonic CN select entity."""

    def __init__(
            self,
            coordinator: PanasonicCNDataUpdateCoordinator,
            device: PanasonicDevice,
            entity_info: Dict[str, Any],
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._device = device
        self._entity_info = entity_info
        self._attr_unique_id = f"{DOMAIN}_{entity_info['unique_id']}"
        self._attr_name = entity_info["name"]
        self.entity_id = f"select.{DOMAIN}_{entity_info['unique_id']}"
        self._options = entity_info.get("options", [])
        self._name_to_key = {option["name"]: option["key"] for option in self._options}
        self._attr_options = list(self._name_to_key.keys())
        self._data = None

        # Set icon based on entity function
        if "mode" in entity_info["unique_id"]:
            self._attr_icon = "mdi:tune"
        else:
            self._attr_icon = "mdi:power"

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        if self._data is None:
            items = self._device.get_select_options(self._entity_info["key"])
            for item in items.values():
                if item["status"]:
                    # Return the name that corresponds to the active key
                    for name, key in self._name_to_key.items():
                        if key == item["key"]:
                            self._data = name
                            break
        return self._data

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        items = self._device.get_select_options(self._entity_info["key"])
        for item in items.values():
            if item["status"]:
                # Return the name that corresponds to the active key
                for name, key in self._name_to_key.items():
                    if key == item["key"]:
                        self._data = name
                        self.async_write_ha_state()
                        return

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Get the key for the selected name
        selected_key = self._name_to_key.get(option)
        if selected_key is None:
            return

        await self.coordinator.async_select_option(
            self._device.id,
            self._entity_info["key"],
            selected_key
        )

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
