"""Support for Tuya BLE devices."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Optional

SERVICE_UUID = "1910"  # Tuya BLE service UUID

_LOGGER = logging.getLogger(__name__)


@dataclass
class TuyaBLEDataPoint:
    """Tuya BLE data point."""

    id: int
    value: Any
    changed_by_device: bool = False


class TuyaBLEDevice:
    """Representation of a Tuya BLE device."""

    def __init__(self, address: str, device_id: str) -> None:
        """Initialize the device."""
        self.address = address
        self.device_id = device_id
        self.category = ""
        self.product_id = ""
        self.name = ""
        self.hardware_version = ""
        self.device_version = ""
        self.protocol_version = ""
        self.product_model = ""

    def register_callback(self, callback: Callable[[list[TuyaBLEDataPoint]], None]) -> None:
        """Register callback for device updates."""
        pass

    def register_connected_callback(self, callback: Callable[[], None]) -> None:
        """Register callback for device connection."""
        pass

    def register_disconnected_callback(self, callback: Callable[[], None]) -> None:
        """Register callback for device disconnection."""
        pass


class AbstaractTuyaBLEDeviceManager(ABC):
    """Abstract class for Tuya BLE device managers."""

    @abstractmethod
    async def get_device_credentials(
        self,
        address: str,
        force_update: bool = False,
        save_data: bool = False,
    ) -> Optional[TuyaBLEDeviceCredentials]:
        """Get device credentials."""
        pass

    @abstractmethod
    def get_login_from_cache(self) -> None:
        """Get login data from cache."""
        pass


@dataclass
class TuyaBLEDeviceCredentials:
    """Credentials for Tuya BLE device."""

    uuid: str
    local_key: str
    device_id: str = ""
    category: str = ""
    product_id: str = ""
    device_name: str = ""
    product_name: str = ""
    product_model: str = ""
