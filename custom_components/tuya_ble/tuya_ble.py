"""Support for Tuya BLE devices."""

from __future__ import annotations

import logging
from dataclasses import dataclass

SERVICE_UUID = "1910"  # Tuya BLE service UUID

_LOGGER = logging.getLogger(__name__)


@dataclass
class TuyaBLEDeviceCredentials:
    """Credentials for Tuya BLE device."""

    uuid: str
    local_key: str
    category: str = ""
    product_id: str = ""
    device_name: str = ""
    product_name: str = ""
    product_model: str = ""
