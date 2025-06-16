"""The Panasonic CN integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api.client import PanasonicCNClient
from .coordinator import PanasonicCNDataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SELECT, Platform.NUMBER, Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Panasonic CN from a config entry."""
    client = PanasonicCNClient()
    
    try:
        success = await client.authenticate(
            entry.data["mac"],
            entry.data["username"],
            entry.data["password"]
        )
        
        if not success:
            _LOGGER.error("Failed to authenticate with Panasonic CN")
            return False
        
        coordinator = PanasonicCNDataUpdateCoordinator(hass, client)
        await coordinator.async_config_entry_first_refresh()
        
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = {
            "coordinator": coordinator,
            "client": client
        }
        
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        return True
        
    except Exception as err:
        _LOGGER.error("Failed to setup Panasonic CN: %s", err)
        await client.close()
        return False

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["client"].close()
        
    return unload_ok 