"""Config flow for Panasonic CN integration."""
from __future__ import annotations

import logging
import hashlib
import netifaces
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_MAC, CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .api.client import PanasonicCNClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

def _hex_upper_md5(text: str) -> str:
    """Calculate MD5 hash and convert to uppercase hex string."""
    md = hashlib.md5()
    md.update(text.encode('utf-8'))
    return md.hexdigest().upper()

def get_mac_address() -> str:
    """Get the MAC address of the first physical network interface."""
    # Get all network interfaces
    interfaces = netifaces.interfaces()
    
    # Exclude virtual interfaces
    virtual_interfaces = {'lo', 'docker', 'veth', 'br-', 'tun', 'tap'}
    
    for interface in interfaces:
        # Skip virtual interfaces
        if any(virtual in interface.lower() for virtual in virtual_interfaces):
            continue
            
        try:
            # Get MAC address of the interface
            mac = netifaces.ifaddresses(interface)[netifaces.AF_LINK][0]['addr']
            if mac and mac != '00:00:00:00:00:00':
                return mac
        except (KeyError, IndexError):
            continue
            
    # Return empty string if no physical interface found
    return ""

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    client = PanasonicCNClient()
    
    # Get MAC address
    mac_address = get_mac_address()
    if not mac_address:
        raise ValueError("No physical network interface found")
    
    # Encrypt plain text password with MD5
    password_md5 = _hex_upper_md5(data[CONF_PASSWORD])
    
    # Authenticate with encrypted password
    if not await client.authenticate(mac_address, data[CONF_USERNAME], password_md5):
        raise ValueError("Invalid authentication")

    # Return encrypted password and MAC address
    return {
        "title": data[CONF_USERNAME],
        "data": {
            CONF_USERNAME: data[CONF_USERNAME],
            CONF_PASSWORD: password_md5,  # Save MD5 encrypted password
            CONF_MAC: mac_address  # Save MAC address
        }
    }

class PanasonicCNConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Panasonic CN."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                return self.async_create_entry(title=info["title"], data=info["data"])
            except ValueError as err:
                if str(err) == "No physical network interface found":
                    errors["base"] = "no_physical_interface"
                else:
                    errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )