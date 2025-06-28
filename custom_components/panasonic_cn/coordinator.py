"""The Panasonic CN coordinator."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, List

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api.client import PanasonicCNClient
from .api.devices.base import PanasonicDevice
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
        self._devices_dict: Dict[str, PanasonicDevice] = {}
        self._client = client

    async def _async_update_data(self) -> Dict[str, PanasonicDevice]:
        """Fetch data from API endpoint."""
        try:
            self._devices_dict = await self._client.get_devices()
            # Get status for all devices
            for device in self._devices_dict.values():
                try:
                    await self._client.fetch_device_status(device.id)
                except Exception as err:
                    _LOGGER.error("Error fetching status for device %s: %s", device.id, err)
                    continue
            return self._devices_dict
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    async def async_select_option(self, device_id: str, select_key: str, option_key: str) -> None:
        """Select device item."""
        device = self._devices_dict[device_id]
        options_dict = device.get_select_options(select_key)
        for option in options_dict.values():
            option["status"] = 0
        options_dict[option_key]["status"] = 1
        success = await self._client.set_device_status(device_id, **options_dict)
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
