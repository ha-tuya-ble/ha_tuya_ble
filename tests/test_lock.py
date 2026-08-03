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
                "address": "12:23:44",
            }
        ],
    }
}


async def test_lock(hass: HomeAssistant) -> None:
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.tuya_ble.const import DOMAIN
    from custom_components.tuya_ble.cloud import HASSTuyaBLEDeviceManager
    from custom_components.tuya_ble.devices import (
        TuyaBLEDevice,
        TuyaBLEProductInfo,
        TuyaBLECoordinator,
        TuyaBLEData,
    )
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

    entity = TuyaBLELock(hass, coordinator, device, product_info)
    entity.async_write_ha_state = Mock()

    # Initial state
    assert entity.available is False
    coordinator._async_handle_connect()
    assert entity.available is True
    # Initial: not motor_state.value -> True (locked) because get_or_create defaults to False
    assert entity.is_locked is True

    # Update coordinator state to unlocked: "lock_motor_state" = True
    device.datapoints._update_from_device(
        DPCode.LOCK_MOTOR_STATE, 0, 0, TuyaBLEDataPointType.DT_BOOL, True
    )
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


async def test_guard_dog_lock(hass: HomeAssistant) -> None:
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.tuya_ble.const import DOMAIN
    from custom_components.tuya_ble.cloud import HASSTuyaBLEDeviceManager
    from custom_components.tuya_ble.devices import (
        TuyaBLEDevice,
        TuyaBLECoordinator,
        TuyaBLEData,
        get_device_product_info,
    )
    from custom_components.tuya_ble.tuya_ble.manager import TuyaBLEDeviceCredentials
    from bleak.backends.device import BLEDevice

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "devices": CONFIG,
            "address": DEVICE_ADDRESS,
        },
        title="Mock TuyaBLE Guard Dog",
    )
    entry.add_to_hass(hass)

    ble_device = BLEDevice(name="bob", address="11:22:33", details="", rssi=-50)
    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())
    device = TuyaBLEDevice(manager, ble_device)
    await device.initialize()

    # Set credentials with wgv4haro
    device._device_info = TuyaBLEDeviceCredentials(
        uuid="uuid123",
        local_key="wV[NcWGUSFF`dSgO",
        device_id="767823809c9c1f458745",
        category="ms",
        product_id="wgv4haro",
        device_name="Guard Dog Lock",
        product_model="BS_PLD01",
        product_name="Guard Dog Security Smart Lock",
        functions=[],
        status_range=[],
    )

    # Mock _send_datapoints to prevent actual BLE calls and exceptions
    device._send_datapoints = AsyncMock()

    product_info = get_device_product_info(device)
    assert product_info is not None
    assert product_info.name == "Guard Dog Security Smart Lock"
    assert product_info.manufacturer == "Guard Dog Security"
    assert product_info.lock == 1

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

    entity = TuyaBLELock(hass, coordinator, device, product_info)
    entity.async_write_ha_state = Mock()

    # Initial state
    assert entity.available is False
    coordinator._async_handle_connect()
    assert entity.available is True
    # Initial: not motor_state.value -> True (locked) because get_or_create defaults to False
    assert entity.is_locked is True

    # Update coordinator state to unlocked: "lock_motor_state" = True
    device.datapoints._update_from_device(
        DPCode.LOCK_MOTOR_STATE, 0, 0, TuyaBLEDataPointType.DT_BOOL, True
    )
    entity._handle_coordinator_update()
    assert entity.is_locked is False

    # Call async_lock (should be no-op for wgv4haro)
    device._send_datapoints.reset_mock()
    await entity.async_lock()
    await hass.async_block_till_done()
    device._send_datapoints.assert_not_called()

    # Call async_unlock (should trigger DP 6 for wgv4haro)
    device._send_datapoints.reset_mock()
    await entity.async_unlock()
    await hass.async_block_till_done()
    device._send_datapoints.assert_called_with([6])
    assert device.datapoints[6].value is True

    # Verify refined sensor mappings for wgv4haro
    from custom_components.tuya_ble.sensor import (
        get_mapping_by_device as get_sensor_mapping,
    )

    sensor_mappings = get_sensor_mapping(device)
    assert any(
        m.description.key == "unlock_fingerprint" and m.dp_id == 12
        for m in sensor_mappings
    )
    assert any(
        m.description.key == "unlock_password" and m.dp_id == 13
        for m in sensor_mappings
    )
    assert any(
        m.description.key == "unlock_dynamic" and m.dp_id == 14 for m in sensor_mappings
    )
    assert any(
        m.description.key == "unlock_ble" and m.dp_id == 19 for m in sensor_mappings
    )
    assert any(
        m.description.key == "unlock_temp_pwd" and m.dp_id == 55
        for m in sensor_mappings
    )
    assert any(
        m.description.key == "unlock_app" and m.dp_id == 62 for m in sensor_mappings
    )

    # Verify button mappings for wgv4haro
    from custom_components.tuya_ble.button import (
        get_mapping_by_device as get_button_mapping,
    )

    button_mappings = get_button_mapping(device)
    assert any(
        m.description.key == "bluetooth_unlock" and m.dp_id == 6
        for m in button_mappings
    )

    # Verify select mappings for wgv4haro
    from custom_components.tuya_ble.select import (
        get_mapping_by_device as get_select_mapping,
    )

    select_mappings = get_select_mapping(device)
    assert any(
        m.description.key == "beep_volume" and m.dp_id == 31 for m in select_mappings
    )
