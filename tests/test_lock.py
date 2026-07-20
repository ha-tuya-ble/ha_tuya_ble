"""Test for tuya_ble lock."""

from unittest.mock import Mock, AsyncMock
from homeassistant.core import HomeAssistant
from custom_components.tuya_ble.lock import TuyaBLELock
from custom_components.tuya_ble.tuya_ble import TuyaBLEDataPointType
from custom_components.tuya_ble.const import DPCode

from . import *

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "entity_category": "None",
                "friendly_name": "Lock 1",
                "icon": "",
                "id": "lock",
                "platform": "lock",
                "restore_on_reconnect": False,
                "address": "12:23:44"
            }
        ],
    }
}


async def test_lock(hass: HomeAssistant) -> None:
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.tuya_ble.const import DOMAIN
    from custom_components.tuya_ble.cloud import HASSTuyaBLEDeviceManager
    from custom_components.tuya_ble.devices import TuyaBLEDevice, TuyaBLEProductInfo, TuyaBLECoordinator, TuyaBLEData
    from bleak.backends.device import BLEDevice

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "devices": CONFIG,
            "address": DEVICE_ADDRESS,
        },
        title="Mock TuyaBLE",
    )
    entry.add_to_hass(hass)

    ble_device = BLEDevice(name="bob", address="11:22:33", details="", rssi=-50)
    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())
    device = TuyaBLEDevice(manager, ble_device)
    await device.initialize()
    product_info = TuyaBLEProductInfo("Fake Lock Product", lock=1)

    # Mock _send_datapoints to prevent actual BLE calls and exceptions
    device._send_datapoints = AsyncMock()

    hass.data.setdefault(DOMAIN, {})
    coordinator = TuyaBLECoordinator(hass, device)

    tuya_ble_hass_data = TuyaBLEData(
        title="Hello",
        device=device,
        manager=manager,
        product=product_info,
        coordinator=coordinator,
    )
    hass.data[DOMAIN][entry.entry_id] = tuya_ble_hass_data

    entity = TuyaBLELock(
        hass, coordinator, device, product_info
    )
    entity.async_write_ha_state = Mock()

    # Initial state
    assert entity.available is False
    coordinator._async_handle_connect()
    assert entity.available is True
    # Initial: not motor_state.value -> True (locked) because get_or_create defaults to False
    assert entity.is_locked is True

    # Update coordinator state to unlocked: "lock_motor_state" = True
    device.datapoints._update_from_device(DPCode.LOCK_MOTOR_STATE, 0, 0, TuyaBLEDataPointType.DT_BOOL, True)
    entity._handle_coordinator_update()
    assert entity.is_locked is False

    # Call async_lock
    await entity.async_lock()
    await hass.async_block_till_done()
    device._send_datapoints.assert_called_with([DPCode.MANUAL_LOCK])
    assert device.datapoints[DPCode.MANUAL_LOCK].value is True

    # Call async_unlock
    await entity.async_unlock()
    await hass.async_block_till_done()
    device._send_datapoints.assert_called_with([DPCode.MANUAL_LOCK])
    assert device.datapoints[DPCode.MANUAL_LOCK].value is False
