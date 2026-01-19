from dataclasses import dataclass
from ..tuya_ble.productinfo import TuyaBLEProductInfo

@dataclass
class TuyaBLEFingerbotInfo(TuyaBLEProductInfo):
    """Model a fingerbot"""

    switch: int = None
    mode: int = None
    up_position: int = None
    down_position: int = None
    hold_time: int = None
    reverse_positions: int = None
    manual_control: int = 0
    program: int = 0
