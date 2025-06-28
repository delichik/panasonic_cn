"""Panasonic CN API client."""
from __future__ import annotations

import traceback
import logging
import json
from typing import Any, Dict, List, Optional
import httpx
import hashlib

from .mapping import DEVICE_TYPES
from .devices.base import PanasonicDevice

_LOGGER = logging.getLogger(__name__)

class PanasonicCNClient:
    """Panasonic CN API client.
    
    This class handles all communication with the Panasonic CN cloud API.
    It manages authentication, device discovery, and device control.
    
    Attributes:
        DOMAIN: The API domain for Panasonic CN cloud service
        BASE_URL: The base URL for API requests
        APP_URL: The URL for app-specific API endpoints
    """

    DOMAIN = "app.psmartcloud.com"
    BASE_URL = "https://" + DOMAIN
    APP_URL = BASE_URL + "/App"
    
    def __init__(self) -> None:
        """Initialize the client.
        
        Sets up the HTTP client and initializes internal state variables.
        """
        self._session = httpx.AsyncClient(verify=False)
        self._ssid = ""
        self._cookie = ""
        self._user_id = ""
        self._family_id = ""
        self._real_family_id = ""
        self._devices: Dict[str, PanasonicDevice] = {}
        self._message_id = 0

    def _generate_message_id(self) -> int:
        """Generate a sequential message ID for API requests.
        
        Returns:
            int: A unique message ID for the request
        """
        self._message_id += 1
        return self._message_id

    def _hex_upper_md5(self, text: str) -> str:
        """Calculate MD5 hash and convert to uppercase hex string.
        
        Args:
            text: The text to hash
            
        Returns:
            str: The MD5 hash in uppercase hexadecimal format
        """
        md = hashlib.md5()
        md.update(text.encode('utf-8'))
        return md.hexdigest().upper()

    def _encode_password(self, username: str, password: str, token: str) -> str:
        """Encode password for authentication.
        
        This method implements the password encoding algorithm used by the Panasonic CN API.
        The password is already in MD5 format when passed to this method.
        
        Args:
            username: Username for authentication
            password: Password already in MD5 format
            token: Authentication token received from the server
            
        Returns:
            str: The encoded password for authentication
        """
        mid = password + username  # Password is already in MD5 format, no need to encrypt again
        if token:
            mid = self._hex_upper_md5(mid) + token
        return self._hex_upper_md5(mid)

    def get_user_id(self) -> str:
        """Get the current user ID.
        
        Returns:
            str: The user ID from the last successful authentication
        """
        return self._user_id
    
    def get_ssid(self) -> str:
        """Get the current session ID.
        
        Returns:
            str: The session ID from the last successful authentication
        """
        return self._ssid
        
    async def authenticate(self, mac: str, username: str, password: str) -> bool:
        """Authenticate with the Panasonic CN API.
        
        This method performs a two-step authentication process:
        1. Get an authentication token
        2. Use the token to perform the actual login
        
        Args:
            mac: MAC address of the client device
            username: Username for authentication
            password: Password in MD5 format
            
        Returns:
            bool: True if authentication was successful, False otherwise
        """
        try:
            # Step 1: Get authentication token
            token_request = {
                "id": self._generate_message_id(),
                "uiVersion": 4.0,
                "params": {
                    "usrId": username
                }
            }
            token_headers = {
                "Host": self.DOMAIN,
                "Content-Type": "application/json",
                "User-Agent": "SmartApp",
                "Prefer": self.BASE_URL
            }
            
            _LOGGER.debug("Getting token - Request: %s", json.dumps(token_request, ensure_ascii=False))
            _LOGGER.debug("Getting token - Headers: %s", json.dumps(token_headers, ensure_ascii=False))
            
            token_response = await self._session.post(
                f"{self.APP_URL}/UsrGetToken",
                json=token_request,
                headers=token_headers
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            
            _LOGGER.debug("Getting token - Response: %s", json.dumps(token_data, ensure_ascii=False))
            
            if "error" in token_data:
                _LOGGER.error("Failed to get token: %s", token_data["error"])
                return False
            login_cookie = token_response.headers.get("set-cookie").split(";")[0]
            token = token_data["results"]["token"]

            # Step 2: Login
            encoded_password = self._encode_password(username, password, token)
            _LOGGER.debug("Encoded password: %s", encoded_password)
            
            login_request = {
                "id": self._generate_message_id(),
                "uiVersion": 4.0,
                "params": {
                    "teleId": mac,
                    "usrId": username,
                    "pwd": encoded_password
                }
            }
            login_headers = {
                "Host": self.DOMAIN,
                "Content-Type": "application/json",
                "User-Agent": "SmartApp",
                "Prefer": self.BASE_URL,
                "xtoken": "",
                "Cookie": login_cookie
            }
            
            _LOGGER.debug("Login - Request: %s", json.dumps(login_request, ensure_ascii=False))
            _LOGGER.debug("Login - Headers: %s", json.dumps(login_headers, ensure_ascii=False))
            
            login_response = await self._session.post(
                f"{self.APP_URL}/UsrLogin",
                json=login_request,
                headers=login_headers
            )
            login_response.raise_for_status()
            login_data = login_response.json()
            
            _LOGGER.debug("Login - Response: %s", json.dumps(login_data, ensure_ascii=False))
            
            if "error" in login_data:
                _LOGGER.error("Failed to login: %s", login_data["error"])
                return False

            # Save user information
            new_cookie = login_response.headers.get("set-cookie").split(";")[0]
            if new_cookie != "":
                self._cookie = new_cookie
            results = login_data["results"]
            self._user_id = results["usrId"]
            self._real_family_id = results["realFamilyId"]
            self._family_id = results["familyId"]
            self._ssid = results["ssId"]
            
            _LOGGER.debug("Login successful - User ID: %s, Family ID: %s, Real Family ID: %s",
                         self._user_id, self._family_id, self._real_family_id)
            
            return True

        except Exception as err:
            _LOGGER.error("Authentication error: %s", err)
            return False

    async def get_devices(self) -> Dict[str, PanasonicDevice]:
        """Get list of bound devices.
        
        This method retrieves all devices bound to the current user account.
        It creates appropriate device instances based on the device type.
        
        Returns:
            List[Dict[str, Any]]: List of device information dictionaries
        """
        try:
            request = {
                "id": self._generate_message_id(),
                "uiVersion": 4.0,
                "params": {
                    "usrId": self._user_id,
                    "realFamilyId": self._real_family_id,
                    "familyId": self._family_id
                }
            }
            headers = {
                "Host": self.DOMAIN,
                "Content-Type": "application/json",
                "User-Agent": "SmartApp",
                "Prefer": self.BASE_URL,
                "xtoken": self._cookie,
                "Cookie": self._cookie
            }
            
            _LOGGER.debug("Getting devices - Request: %s", json.dumps(request, ensure_ascii=False))
            _LOGGER.debug("Getting devices - Headers: %s", json.dumps(headers, ensure_ascii=False))
            
            response = await self._session.post(
                f"{self.APP_URL}/UsrGetBindDevInfo",
                json=request,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            
            _LOGGER.debug("Getting devices - Response: %s", json.dumps(data, ensure_ascii=False))
            
            if "error" in data:
                _LOGGER.error("Failed to get devices: %s", data["error"])
                return {}

            # Create device instances
            self._devices.clear()
            for device_info in data["results"]["devList"]:
                device_id = device_info["deviceId"]
                device_type = device_id.split("_")[1]
                
                _LOGGER.debug("Found device - ID: %s, Type: %s", device_id, device_type)
                
                if device_type in DEVICE_TYPES:
                    self._devices[device_id] = DEVICE_TYPES[device_type](device_info, self)
                    _LOGGER.debug("Created device instance for %s", device_id)

            return self._devices

        except Exception as err:
            _LOGGER.error("Failed to get devices: %s", err)
            return {}

    async def fetch_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Fetch device status."""
        device = self._devices.get(device_id)
        if not device:
            _LOGGER.error("Device not found: %s", device_id)
            return None

        try:
            device_cookie = await device.get_device_cookie()
            if not device_cookie:
                _LOGGER.error("Failed to get device token for %s", device_id)
                return None

            request = {
                "id": self._generate_message_id(),
                "usrId": self._user_id,
                "deviceId": device_id,
                "token": device.token
            }
            headers = {
                "Host": self.DOMAIN,
                "Content-Type": "application/json",
                "User-Agent": "SmartApp",
                "Prefer": self.BASE_URL,
                "xtoken": self._cookie,
                "Cookie": device_cookie
            }
            
            _LOGGER.debug("Getting device status - Device: %s, Request: %s", 
                         device_id, json.dumps(request, ensure_ascii=False))
            _LOGGER.debug("Getting device status - Device: %s, Headers: %s", 
                         device_id, json.dumps(headers, ensure_ascii=False))
            
            response = await self._session.post(
                f"{self.APP_URL}/FDevGetStatusInfo",
                json=request,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            
            _LOGGER.debug("Getting device status - Device: %s, Response: %s", 
                         device_id, json.dumps(data, ensure_ascii=False))
            
            if "error" in data:
                _LOGGER.error("Failed to get device status: %s", data["error"])
                return None

            # Use the device's parse_status method to handle the status
            device.status = data["results"]
            return device.status

        except Exception as err:
            _LOGGER.error("Failed to get device status: %s", err)
            return None

    async def set_device_status(self, device_id: str, **kwargs: Any) -> bool:
        """Set device status."""
        device = self._devices.get(device_id)
        if not device:
            _LOGGER.error("Device not found: %s", device_id)
            return False

        try:
            device_cookie = await device.get_device_cookie()
            if not device_cookie:
                _LOGGER.error("Failed to get device cookie for %s", device_id)
                return False
            
            # Get current status
            new_status = await self.fetch_device_status(device_id)
            # Update parameters to be modified
            for key, value in kwargs.items():
                if key in new_status:
                    new_status[key] = value
                    device.status[key] = value

            request = {
                "id": self._generate_message_id(),
                "usrId": self._user_id,
                "deviceId": device_id,
                "token": device.token,
                "params": new_status
            }
            headers = {
                "Host": self.DOMAIN,
                "Content-Type": "application/json",
                "User-Agent": "SmartApp",
                "Prefer": self.BASE_URL,
                "xtoken": self._cookie,
                "Cookie": device_cookie
            }
            
            _LOGGER.debug("Setting device status - Device: %s, Request: %s", 
                         device_id, json.dumps(request, ensure_ascii=False))
            _LOGGER.debug("Setting device status - Device: %s, Headers: %s", 
                         device_id, json.dumps(headers, ensure_ascii=False))
            
            response = await self._session.post(
                f"{self.APP_URL}/FDevSetStatusInfo",
                json=request,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            
            _LOGGER.debug("Setting device status - Device: %s, Response: %s", 
                         device_id, json.dumps(data, ensure_ascii=False))
            
            if "error" in data:
                _LOGGER.error("Failed to set device status: %s", data["error"])
                return False
            return True

        except Exception as err:
            _LOGGER.error("Failed to set device status: %s\n%s", err, traceback.format_exc())
            return False

    async def close(self) -> None:
        """Close the client session."""
        await self._session.aclose()
