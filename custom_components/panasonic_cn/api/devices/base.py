"""Panasonic CN device base class."""
from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

_LOGGER = logging.getLogger(__name__)

COOKIE_EXPIRE = 3600  # Cookie expiration time in seconds


def _sha512(text):
    """Calculate SHA-512 hash of the input text.
    
    Args:
        text: The text to hash
        
    Returns:
        str: The SHA-512 hash in hexadecimal format
    """
    return hashlib.sha512(text.encode("utf-8")).hexdigest()

class PanasonicClienIface(ABC):
    """Interface for Panasonic CN client.
    
    This abstract class defines the interface that must be implemented
    by any client class that wants to interact with Panasonic devices.
    """
    @abstractmethod
    def get_user_id(self) -> str:
        """Get the current user ID.
        
        Returns:
            str: The user ID from the last successful authentication
        """
        pass
        
    @abstractmethod
    def get_ssid(self) -> str:
        """Get the current session ID.
        
        Returns:
            str: The session ID from the last successful authentication
        """
        pass

class PanasonicDevice(ABC):
    """Base class for Panasonic devices.
    
    This abstract class provides the base functionality for all Panasonic devices.
    It handles device identification, status management, and entity creation.
    
    Attributes:
        _id: The unique device ID
        _type: The device type code
        _sub_type: The device sub-type code
        _mno: The device model number
        _name: The device name
        _raw_status: The raw device status data
        _client: The API client instance
        _cookie: The device-specific authentication cookie
        _cookie_create_time: The timestamp when the cookie was created
        _token: The device-specific authentication token
    """

    def __init__(self, device_info: Dict[str, Any], client: PanasonicClienIface) -> None:
        """Initialize device.
        
        Args:
            device_info: Dictionary containing device information
            client: The API client instance
        """
        self._id = device_info["deviceId"]
        self._type = self._id.split("_")[1]
        self._sub_type = device_info["params"]["devSubTypeId"]
        self._mno = device_info["params"]["deviceMNO"]
        self._name = device_info["params"]["deviceName"]
        self._raw_status: Dict[str, Any] = {}
        self._client = client
        self._cookie = ""
        self._cookie_create_time = 0
        split_id = self._id.split("_")
        equip_type = self._id.split("_" + self._type + "_")[1]
        self._token = _sha512(
            _sha512(split_id[0][6:] + "_" + self._type + "_" + split_id[0][:6]) + "_" + equip_type)

    @property
    def id(self) -> str:
        """Return device ID.
        
        Returns:
            str: The unique device identifier
        """
        return self._id

    @property
    def raw_status(self) -> Optional[Dict[str, Any]]:
        """Return device status.
        
        Returns:
            Optional[Dict[str, Any]]: The raw device status data
        """
        return self._raw_status
    
    @property
    def parsed_status(self) -> Dict[str, Any]:
        """Parse device status.
        
        Returns:
            Dict[str, Any]: The parsed device status data
        """
        return self._parsed_status

    @raw_status.setter
    def raw_status(self, value: Dict[str, Any]) -> None:
        """Set device status.
        
        When setting the raw status, it also triggers parsing of the status data.
        
        Args:
            value: The new raw status data
        """
        self._parsed_status = self.parse_status(value)
        self._raw_status = value

    @property
    def type(self) -> str:
        """Return the device type.
        
        Returns:
            str: The device type code
        """
        return self._type

    @property
    def sub_type(self) -> str:
        """Return the device sub type.
        
        Returns:
            str: The device sub-type code
        """
        return self._sub_type

    @property
    def name(self) -> str:
        """Return the device name.
        
        Returns:
            str: The device name
        """
        return self._name

    @property
    def token(self) -> str:
        """Return the device token.
        
        Returns:
            str: The device-specific authentication token
        """
        return self._token

    @abstractmethod
    async def get_device_cookie(self) -> str:
        """Get device specific token.
        
        This method should be implemented by each device type to handle its specific
        token retrieval logic. The implementation should:
        1. Check if the current token is still valid
        2. If not valid, get a new token using device-specific method
        3. Cache the new token and its creation time
        4. Return the token
        
        Returns:
            str: The device token
        """
        pass

    @abstractmethod
    def parse_status(self, status: Dict[str, Any]) -> Dict[str, Any]:
        """Parse device status.
        
        This method should be implemented by each device type to parse its specific
        status data into a standardized format.
        
        Args:
            status: The raw status data from the device
            
        Returns:
            Dict[str, Any]: The parsed status data
        """
        pass

    @abstractmethod
    def get_entities(self) -> List[Dict[str, Any]]:
        """Get list of entities supported by this device.
        
        This method should be implemented by each device type to define its supported
        entities (switches, sensors, numbers, etc.).
        
        Returns:
            List of entity configurations, each containing:
            - type: Entity type (switch, number, etc.)
            - unique_id: Unique identifier for the entity
            - name: Display name for the entity
            - state_key: Key in raw_status for the entity's state
            - control_key: Key in params for controlling the entity
            - min_value: Minimum value (for number entities)
            - max_value: Maximum value (for number entities)
            - step: Step value (for number entities)
            - unit: Unit of measurement (for number entities)
        """
        pass

    @abstractmethod
    def get_preference(self) -> Dict[str, Any]:
        pass

    def get_value(self, key: str) -> Any:
        """Get value from raw status.
        
        Args:
            key: The key to look up in the parsed status
            
        Returns:
            Any: The value associated with the key, or None if not found
        """
        return self._parsed_status.get(key)
    
    def get_select_items(self, key: str) -> Dict[str, Dict[str, Any]]:
        """Get select items from raw status.
        
        Args:
            key: The key of the select group
            
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of items with their status
        """
        items = {}
        for select_group in self.get_preference()["select"]:
            if select_group["key"] == key:
                for item in select_group["items"]:
                    items[item["key"]] = {
                        "key": item["key"],
                        "name": item["name"],
                        "status": self._parsed_status.get(item["key"], 0) == 1
                    }
                break
        return items

    def get_switch_state(self, key: str) -> bool:
        """Get switch state from raw status.
        
        Args:
            key: The key to look up in the parsed status
            
        Returns:
            bool: True if the switch is on (value is 1), False otherwise
        """
        return self._parsed_status.get(key, 0) == 1

    def get_number_value(self, key: str) -> Optional[float]:
        """Get number value from raw status.
        
        Args:
            key: The key to look up in the parsed status
            
        Returns:
            Optional[float]: The numeric value, or None if not found or invalid
        """
        value = self._parsed_status.get(key)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
        return None