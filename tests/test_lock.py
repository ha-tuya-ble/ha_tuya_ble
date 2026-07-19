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


async def test_foxgard_lock_and_sensors(hass: HomeAssistant) -> None:
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.tuya_ble.const import DOMAIN, DPCode
    from custom_components.tuya_ble.cloud import HASSTuyaBLEDeviceManager
    from custom_components.tuya_ble.devices import (
        TuyaBLEDevice,
        TuyaBLECoordinator,
        TuyaBLEData,
        get_product_info_by_ids,
    )
    from custom_components.tuya_ble.tuya_ble import TuyaBLEDeviceCredentials
    from custom_components.tuya_ble.sensor import get_mapping_by_device, TuyaBLESensor
    from custom_components.tuya_ble.binary_sensor import get_mapping_by_device as get_binary_mapping, TuyaBLEBinarySensor
    from custom_components.tuya_ble.select import get_mapping_by_device as get_select_mapping, TuyaBLESelect
    from custom_components.tuya_ble.switch import get_mapping_by_device as get_switch_mapping, TuyaBLESwitch
    from bleak.backends.device import BLEDevice

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "devices": CONFIG,
            "address": DEVICE_ADDRESS,
        },
        title="Mock TuyaBLE Foxgard",
    )
    entry.add_to_hass(hass)

    ble_device = BLEDevice(name="bob", address="11:22:33", details="", rssi=-50)
    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())
    device = TuyaBLEDevice(manager, ble_device)
    await device.initialize()

    # Assign credentials directly to device to configure characteristics
    credentials = TuyaBLEDeviceCredentials(
        device_id="some_foxgard_id",
        device_name="Foxgard Lock",
        product_id="99gv5nmz",
        product_model="Foxgard Smart Lock",
        product_name="Smart Fingerprint Door Lock",
        uuid="some_foxgard_uuid",
        local_key="some_local_key_16_chars_long",
        category="ms",
        functions=[],
        status_range=[],
    )
    device._device_info = credentials

    product_info = get_product_info_by_ids("ms", "99gv5nmz")
    assert product_info is not None
    assert product_info.lock == 1
    assert product_info.name == "Smart Fingerprint Door Lock"

    device._send_datapoints = AsyncMock()

    hass.data.setdefault(DOMAIN, {})
    coordinator = TuyaBLECoordinator(hass, device)

    tuya_ble_hass_data = TuyaBLEData(
        title="Foxgard",
        device=device,
        manager=manager,
        product=product_info,
        coordinator=coordinator,
    )
    hass.data[DOMAIN][entry.entry_id] = tuya_ble_hass_data

    # 1. Test Lock Entity Setup
    lock_entity = TuyaBLELock(hass, coordinator, device, product_info)
    lock_entity.async_write_ha_state = Mock()
    coordinator._async_handle_connect()

    # Verify is_locked behaves correctly with motor_state
    assert lock_entity.is_locked is True
    device.datapoints._update_from_device(DPCode.LOCK_MOTOR_STATE, 0, 0, TuyaBLEDataPointType.DT_BOOL, True)
    assert lock_entity.is_locked is False

    # 2. Test Sensors Mapped
    sensor_mappings = get_mapping_by_device(device)
    assert len(sensor_mappings) > 0
    # Expected: battery (dp 8), alarm_lock (dp 21), lock_door_status (dp 40)
    dp_ids = [m.dp_id for m in sensor_mappings]
    assert 8 in dp_ids
    assert 21 in dp_ids
    assert 40 in dp_ids

    # Test one sensor entity
    battery_mapping = next(m for m in sensor_mappings if m.dp_id == 8)
    battery_sensor = TuyaBLESensor(hass, coordinator, device, product_info, battery_mapping)
    battery_sensor.async_write_ha_state = Mock()
    device.datapoints._update_from_device(8, 0, 0, TuyaBLEDataPointType.DT_VALUE, 85)
    battery_sensor._handle_coordinator_update()
    assert battery_sensor.native_value == 85

    # 3. Test Binary Sensors Mapped
    binary_mappings = get_binary_mapping(device)
    assert len(binary_mappings) > 0
    # Expected: lock_motor_state (dp 47)
    assert any(m.dp_id == 47 for m in binary_mappings)

    motor_state_mapping = next(m for m in binary_mappings if m.dp_id == 47)
    motor_state_binary = TuyaBLEBinarySensor(hass, coordinator, device, product_info, motor_state_mapping)
    motor_state_binary.async_write_ha_state = Mock()
    device.datapoints._update_from_device(47, 0, 0, TuyaBLEDataPointType.DT_BOOL, True)
    motor_state_binary._handle_coordinator_update()
    assert motor_state_binary.is_on is True

    # 4. Test Select Mappings
    select_mappings = get_select_mapping(device)
    assert len(select_mappings) > 0
    # Expected: beep_volume (dp 31)
    assert any(m.dp_id == 31 for m in select_mappings)

    volume_mapping = next(m for m in select_mappings if m.dp_id == 31)
    volume_select = TuyaBLESelect(hass, coordinator, device, product_info, volume_mapping)
    volume_select.async_write_ha_state = Mock()
    device.datapoints._update_from_device(31, 0, 0, TuyaBLEDataPointType.DT_ENUM, 2)
    volume_select._handle_coordinator_update()
    assert volume_select.current_option == "normal"

    # 5. Test Switch Mappings
    switch_mappings = get_switch_mapping(device)
    assert len(switch_mappings) > 0
    # Expected: lock_motor_state (dp 47), manual_lock (dp 46)
    assert any(m.dp_id == 47 for m in switch_mappings)
    assert any(m.dp_id == 46 for m in switch_mappings)

    manual_lock_mapping = next(m for m in switch_mappings if m.dp_id == 46)
    manual_lock_switch = TuyaBLESwitch(hass, coordinator, device, product_info, manual_lock_mapping)
    manual_lock_switch.async_write_ha_state = Mock()
    device.datapoints._update_from_device(46, 0, 0, TuyaBLEDataPointType.DT_BOOL, True)
    manual_lock_switch._handle_coordinator_update()
    assert manual_lock_switch.is_on is True
