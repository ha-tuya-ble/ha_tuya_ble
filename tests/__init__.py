"""Init tuya_ble tests"""

import asyncio
import homeassistant.util.ulid as ulid_util
import os, sys
import pytest
import threading
import time

from bleak.backends.device import BLEDevice
from typing import Any
from unittest.mock import AsyncMock, Mock
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription


from habluetooth.central_manager import CentralBluetoothManager

from custom_components.tuya_ble import async_setup_entry
from custom_components.tuya_ble.const import DOMAIN
from custom_components.tuya_ble.devices import (
    TuyaBLECoordinator,
    TuyaBLEData,
    TuyaBLEDevice,
    TuyaBLEProductInfo,
    TuyaBLEEntity,
)
from custom_components.tuya_ble.cloud import HASSTuyaBLEDeviceManager


DEVICE_NAME = "1234"
DEVICE_ADDRESS = "00:11:22:33:44:55"
DEVICE_CONFIG = {
    "address": DEVICE_ADDRESS,
    "device_id": "767823809c9c1f458745",
    "protocol_version": "3.3",
    "local_key": "wV[NcWGUSFF`dSgO",
    "friendly_name": "Local 3G",
}


from unittest.mock import AsyncMock, patch

CentralBluetoothManager.manager = AsyncMock()  # HomeAssistantBlueToothManager

# Mock data for the BLE device
mock_ble_device = BLEDevice(
    name="MockTuyaDevice", address=DEVICE_ADDRESS, rssi=-70, details=""
)
with patch(
    "homeassistant.components.bluetooth.api.async_ble_device_from_address", new=Mock()
) as mock_async_ble_device_from_address:
    mock_async_ble_device_from_address.side_effect = None

with patch("bleak_retry_connector.get_device", new=AsyncMock()) as mock_get_device:
    # Define the behavior of the mock
    mock_get_device.side_effect = Exception('Boom!')
    

async def init(config: dict[str, dict[str, Any]], entity_domain, entity_class):
    add_entities = AsyncMock()

    asyncio.create_task = lambda _: None
    asyncio.get_running_loop = lambda: type(
        "", (), {"_thread_id": threading.get_ident()}
    )
    hass = HomeAssistant("")
    entry = ConfigEntry(**create_entry(config))

    ble_device = BLEDevice(name="bob", address="11:22:33", details="", rssi=-50)
    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())
    device = TuyaBLEDevice(manager, ble_device)
    # await device.initialize()
    product_info = TuyaBLEProductInfo("Fake Product")

    hass.data.setdefault("tuya_ble", {entry.entry_id: {}})
    dump_device = TuyaBLECoordinator(hass, device)
    dump_device.status_updated = lambda x: [
        [e._status.update(x), e.connection_made(), e.status_updated()]
        for e in get_entites(dump_device)
    ]
    # entity = TuyaBLEEntity(hass, dump_device, device, product_info, EntityDescription("Hello"))

    tuya_ble_hass_data = TuyaBLEData(
        title="Hello",
        device=device,
        manager=manager,
        product=product_info,
        coordinator=dump_device,
    )

    hass.data[DOMAIN][entry.entry_id] = tuya_ble_hass_data

    await async_setup_entry(hass, entry)  # async_add_entities=add_entities,

    add_entities.assert_called_once()
    return dump_device


def create_entry(config: dict[str, dict[str, Any]]):
    return {
        "data": {
            "devices": config,
            "address": DEVICE_ADDRESS,
        },
        "disabled_by": None,
        "discovery_keys": None,
        "domain": "test",
        "entry_id": ulid_util.ulid_now(),
        "minor_version": 1,
        "options": {},
        "pref_disable_new_entities": None,
        "pref_disable_polling": None,
        "title": "Mock TuyaBLE",
        "unique_id": None,
        "version": 1,
        "source": "user",
    }


def get_entites(device: TuyaBLECoordinator):
    return getattr(device, "_entities")
