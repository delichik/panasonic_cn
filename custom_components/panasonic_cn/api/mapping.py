from typing import Dict, Type

from .devices.base import PanasonicDevice
from .devices.fridge import PanasonicFridge

# Device type mapping
DEVICE_TYPES: Dict[str, Type[PanasonicDevice]] = {
    "0100": PanasonicFridge,
}
