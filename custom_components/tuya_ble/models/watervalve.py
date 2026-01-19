from dataclasses import dataclass
from ..tuya_ble.productinfo import TuyaBLEProductInfo

@dataclass
class TuyaBLEWaterValveInfo(TuyaBLEProductInfo):
    """Model a water valve"""

    switch: bool = None
    countdown: int = None
    weather_delay: str = None
    smart_weather: str = None
    use_time: int = None