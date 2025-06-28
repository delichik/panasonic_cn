"""Panasonic CN fridge device."""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List
import httpx

from .base import PanasonicDevice, COOKIE_EXPIRE

_LOGGER = logging.getLogger(__name__)

# Entity definitions for different fridge models
FRIDGE_ENTITIES = {
    "Fridge-11": {
        "select": [
            {
                "unique_id": "mode",
                "key": "mode",
                "name": "模式",
                "options": [
                    {
                        "name": "速冻",
                        "key": "quickFreeze"
                    },
                    {
                        "name": "假期模式",
                        "key": "vacation"
                    },
                    {
                        "name": "快速制冰",
                        "key": "quickicing"
                    },
                    {
                        "name": "制冰停止",
                        "key": "icingStop"
                    },
                    {
                        "name": "制冰清洁",
                        "key": "icingDeice"
                    }
                ],
            }
        ],
        "sensor": [
            {
                "unique_id": "pc_temp_current",
                "name": "冷藏室当前温度",
                "key": "PCTempCur",
                "unit": "°C"
            },
            {
                "unique_id": "fc_temp_current",
                "name": "冷冻室当前温度",
                "key": "FCTempCur",
                "unit": "°C"
            },
            {
                "unique_id": "scb1_temp_current",
                "name": "软冻室当前温度",
                "key": "SCB1TempCur",
                "unit": "°C"
            }
        ],
        "number": [
            {
                "unique_id": "pc_temp_set",
                "name": "冰箱设定温度",
                "key": "PCTempSet",
                "unit": "°C",
                "min_value": 0,
                "max_value": 10,
                "step": 1
            },
            {
                "unique_id": "fc_temp_set",
                "name": "冷冻室设定温度",
                "key": "FCTempSet",
                "unit": "°C",
                "min_value": -20,
                "max_value": 0,
                "step": 1
            },
            {
                "unique_id": "scb1_temp_set",
                "name": "软冻室设定温度",
                "key": "SCB1TempSet",
                "unit": "°C",
                "min_value": -20,
                "max_value": 10,
                "step": 1
            }
        ],
        "default_params": {
            "PCTempSet": 4,
            "FCTempSet": -20,
            "SCS1TempSet": 0,
            "SCS2TempSet": 0,
            "SCB1TempSet": -5,
            "SCB2TempSet": 0,
            "quickFreeze": 0,
            "vacation": 0,
            "quickicing": 0,
            "icingStop": 0,
            "icingDeice": 0,
            "ecoNaviSet": 0,
            "freshFrozen": 0,
            "nanoe": 0,
            "zhencaiSet": 0,
            "silver": 0,
            "preservation": 0,
            "RAModeCur": 0,
            "SAModeCur": 0,
            "isTodoLimit": 0
        }
    }
}

class PanasonicFridge(PanasonicDevice):
    """Panasonic fridge device.
    
    This class implements the specific functionality for Panasonic fridge devices.
    It handles device-specific authentication, status parsing, and entity management.
    """

    async def get_device_cookie(self) -> str:
        """Get device specific token.
        
        This method implements the device-specific token retrieval logic for fridge devices.
        It first checks if the current token is still valid, and if not, requests a new one
        from the device's web interface.
        
        Returns:
            str: The device token, or an empty string if token retrieval failed
        """
        if self._cookie and self._cookie_create_time + COOKIE_EXPIRE >= time.time():
            return self._cookie
        
        url = f"{self._client.BASE_URL}/ca/cn/{self._type}/{self._sub_type}/index.html?deviceId={self._id}&usrId={self._client.get_user_id()}&SSID={self._client.get_ssid()}&devType={self._type}&deviceName={self._name}"

        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(url)
                response.raise_for_status()
                cookie = response.headers.get("set-cookie", "").split(";")[0]
                if cookie:
                    self._cookie = cookie
                    self._cookie_create_time = time.time()
                    return cookie
        except Exception as err:
            _LOGGER.error("Failed to get device token: %s", err)

        return ""

    def parse_form(self, status: Dict[str, Any]) -> Dict[str, Any]:
        """Parse device status.
        
        This method parses the raw status data from the fridge device into a standardized format.
        It uses the default parameters for the specific model as a base and updates them with
        the actual status values. Only predefined parameters in default_params will be kept.
        
        Args:
            status: The raw status data from the device
            
        Returns:
            Dict[str, Any]: The parsed status data containing only predefined parameters
        """
        # Get default parameters for this model
        default_params = FRIDGE_ENTITIES[self._sub_type]["default_params"]
        
        # Create a new dictionary with default values
        parsed_status = default_params.copy()
        
        # Only update values for keys that exist in default_params
        for key, value in status.items():
            if key in default_params:
                parsed_status[key] = value
        
        return parsed_status

    def get_preference(self) -> Dict[str, Any]:
        return FRIDGE_ENTITIES[self._sub_type]

    def get_entities(self) -> List[Dict[str, Any]]:
        """Get list of entities supported by this device.
        
        This method returns the list of entities (switches, sensors, numbers) that are
        supported by this specific fridge model. The entities are defined in the
        FRIDGE_ENTITIES dictionary.
        
        Returns:
            List[Dict[str, Any]]: List of entity configurations
        """
        entities = []
        
        # Get entity definitions for this model
        entity_defs = FRIDGE_ENTITIES[self._sub_type]

        # Add switch entities
        for switch in entity_defs.get("select", []):
            entity = {
                "type": "select",
                "unique_id": f"{self._id}_{switch['unique_id']}",
                "name": f"{self._name} {switch['name']}",
                "key": switch["key"],
                "options": switch["options"],
            }
            entities.append(entity)
        
        # Add sensor entities
        for sensor in entity_defs.get("sensor", []):
            if sensor["key"] in self._status:
                entities.append({
                    "type": "sensor",
                    "unique_id": f"{self._id}_{sensor['unique_id']}",
                    "name": f"{self._name} {sensor['name']}",
                    "key": sensor["key"],
                    "unit": sensor["unit"]
                })
        
        # Add number entities
        for number in entity_defs.get("number", []):
            if number["key"] in self._status:
                entities.append({
                    "type": "number",
                    "unique_id": f"{self._id}_{number['unique_id']}",
                    "name": f"{self._name} {number['name']}",
                    "key": number["key"],
                    "unit": number["unit"],
                    "min_value": number["min_value"],
                    "max_value": number["max_value"],
                    "step": number["step"]
                })
        
        return entities
