"""The Panasonic CN sensor integration."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from homeassistant import config_entries
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PanasonicCNDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Panasonic CN sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities = []
    
    # Iterate through all devices
    for device in coordinator.devices.values():
        # Get list of supported entities for the device
        device_entities = device.get_entities()
        
        # Add sensor entities
        for entity_info in device_entities:
            if entity_info["type"] == "sensor":
                entities.append(
                    PanasonicCNSensor(
                        coordinator,
                        device.id,
                        entity_info
                    )
                )
    
    async_add_entities(entities)

class PanasonicCNSensor(SensorEntity, CoordinatorEntity):
    """Representation of a Panasonic CN sensor."""

    def __init__(
        self,
        coordinator: PanasonicCNDataUpdateCoordinator,
        device_id: str,
        entity_info: Dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device = coordinator.data[device_id]
        self._entity_info = entity_info
        self.coordinator = coordinator
        self._attr_unique_id = f"{DOMAIN}_{entity_info['unique_id']}"
        self._attr_name = entity_info["name"]
        self._attr_native_unit_of_measurement = entity_info.get("unit")
        
        # Set icon based on entity type
        if "temp" in entity_info["unique_id"]:
            self._attr_icon = "mdi:thermometer"
        else:
            self._attr_icon = "mdi:information"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        return self._device.get_value(self._entity_info["key"])

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