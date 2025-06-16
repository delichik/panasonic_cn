"""The Panasonic CN coordinator."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api.client import PanasonicCNClient
from .const import DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

class PanasonicCNDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Panasonic CN data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: PanasonicCNClient,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Panasonic CN",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.devices = []
        self._device_dict = {}
        self._client = client

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from API endpoint."""
        try:
            self.devices = await self._client.get_devices()
            self._device_dict = {}
            # Get status for all devices
            for device in self.devices.values():
                try:
                    await self._client.get_device_status(device.id)
                except Exception as err:
                    _LOGGER.error("Error fetching status for device %s: %s", device.id, err)
                    continue
                self._device_dict[device.id] = device
            return self.devices
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    async def async_select_item(self, device_id: str, select_key: str, item_key: str) -> None:
        """Select device item."""
        device = self._devices_dict[device_id]
        item_dict = device.get_select_items(select_key)
        for item in item_dict.values():
            item["status"] = 0
        item_dict[item_key]["status"] = 1
        success = await self._client.set_device_status(device_id, **item_dict)
        if not success:
            raise Exception("Failed to set device switch state")

    async def async_set_switch_state(self, device_id: str, state: bool, key: str) -> None:
        """Set device switch state."""
        success = await self._client.set_device_status(device_id, **{key: 1 if state else 0})
        if not success:
            raise Exception("Failed to set device switch state")

    async def async_set_number_value(self, device_id: str, value: float, control_key: str) -> None:
        """Set device number value."""
        success = await self._client.set_device_status(
            device_id,
            **{control_key: int(value)}
        )
        if not success:
            raise Exception("Failed to set device number value") 