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
from custom_components.tuya_ble.tuya_ble import TuyaBLEDeviceCredentials, TuyaBLEDataPointType
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

mock_ble_device = BLEDevice(
    name="MockTuyaDevice", address=DEVICE_ADDRESS, rssi=-70, details=""
)

CentralBluetoothManager.manager = Mock()  # HomeAssistantBlueToothManager
CentralBluetoothManager.manager.async_ble_device_from_address.side_effect = lambda address, connectable: (
        mock_ble_device if address == DEVICE_ADDRESS else None
    )
    

class MockHASSTuyaBLEDeviceManager(HASSTuyaBLEDeviceManager):
    def __init__(self, hass: HomeAssistant, data: dict[str, Any]) -> None:
        super().__init__(hass, data)

    async def get_device_credentials(
        self,
        address: str,
        force_update: bool = False,
        save_data: bool = False,
    ) -> TuyaBLEDeviceCredentials | None:
        return TuyaBLEDeviceCredentials(
            category="jtmspro",
            product_id="ajk32biq",
            device_id="some_id",
            local_key="some_key",
            uuid="some_uuid",
            device_name="some_name",
            product_model="some_model",
            product_name="some_product_name",
            functions=[],
            status_range=[]
        )


async def init(config: dict[str, dict[str, Any]], entity_domain, entity_class):
    add_entities = AsyncMock()

    asyncio.create_task = lambda _: None
    asyncio.get_running_loop = lambda: type(
        "", (), {"_thread_id": threading.get_ident()}
    )
    hass = HomeAssistant("")
    hass.loop = asyncio.new_event_loop()
    hass.config_entries = Mock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(
        return_value=True
    )

    entry = ConfigEntry(**create_entry(config))

    ble_device = BLEDevice(name="bob", address="11:22:33", details="", rssi=-50)
    manager = MockHASSTuyaBLEDeviceManager(hass, entry.options.copy())

    device = TuyaBLEDevice(manager, ble_device)
    await device.initialize()
    product_info = TuyaBLEProductInfo("Fake Product")

    hass.data.setdefault("tuya_ble", {entry.entry_id: {}})
    dump_device = TuyaBLECoordinator(hass, device)

    def status_updated(statuses: dict):
        for dpid, value in statuses.items():
            dpid = int(dpid)
            dp_type = TuyaBLEDataPointType.DT_BOOL if type(value) is bool else TuyaBLEDataPointType.DT_VALUE
            device.datapoints._update_from_device(dpid, time.time(), 0, dp_type, value)
        dump_device._async_handle_update(list(device.datapoints._datapoints.values()))
    dump_device.status_updated = status_updated


    tuya_ble_hass_data = TuyaBLEData(
        title="Hello",
        device=device,
        manager=manager,
        product=product_info,
        coordinator=dump_device,
    )

    hass.data[DOMAIN][entry.entry_id] = tuya_ble_hass_data

    import importlib
    platform = entity_class.__module__.split('.')[-1]
    platform_module = importlib.import_module(f"custom_components.tuya_ble.{platform}")
    await platform_module.async_setup_entry(hass, entry, add_entities)

    add_entities.assert_called_once()
    return dump_device, add_entities.call_args.args[0]


def create_entry(config: dict[str, dict[str, Any]]):
    return {
        "data": {
            "devices": config,
            "address": DEVICE_ADDRESS,
        },
        "disabled_by": None,
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
