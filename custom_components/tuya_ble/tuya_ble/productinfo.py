from .const import DEVICE_DEF_MANUFACTURER
from dataclasses import dataclass

@dataclass
class TuyaBLEProductInfo:
    """Model product info"""

    name: str = ""
    manufacturer: str = DEVICE_DEF_MANUFACTURER
    lock: int | None = None
