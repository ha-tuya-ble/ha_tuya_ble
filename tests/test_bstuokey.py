"""Test for BSTUOKEY Invisible Lock (kpn4zaf7)."""

from unittest.mock import Mock, AsyncMock
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.components.lock import LockEntityDescription
from custom_components.tuya_ble.lock import TuyaBLELock
from custom_components.tuya_ble.sensor import TuyaBLESensor, get_mapping_by_device
from custom_components.tuya_ble.select import (
    TuyaBLESelect,
    get_mapping_by_device as get_select_mapping,
)
from custom_components.tuya_ble.button import (
    TuyaBLEButton,
    get_mapping_by_device as get_button_mapping,
)
from custom_components.tuya_ble.tuya_ble import (
    TuyaBLEDataPointType,
    TuyaBLEDeviceCredentials,
)
from custom_components.tuya_ble.const import DPCode

from . import *


async def test_bstuokey_invisible_lock(hass: HomeAssistant) -> None:
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.tuya_ble.const import DOMAIN
    from custom_components.tuya_ble.cloud import HASSTuyaBLEDeviceManager
    from custom_components.tuya_ble.devices import (
        TuyaBLEDevice,
        get_device_product_info,
        TuyaBLECoordinator,
        TuyaBLEData,
    )
    from bleak.backends.device import BLEDevice

    config = {
        DEVICE_NAME: {
            **DEVICE_CONFIG,
            "entities": [],
        }
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "devices": config,
            "address": DEVICE_ADDRESS,
        },
        title="Mock TuyaBLE BSTUOKEY",
    )
    entry.add_to_hass(hass)

    ble_device = BLEDevice(name="bob", address="11:22:33", details="", rssi=-50)
    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())
    device = TuyaBLEDevice(manager, ble_device)
    await device.initialize()

    # Populate device credentials so category and product_id match kpn4zaf7
    device._device_info = TuyaBLEDeviceCredentials(
        uuid="mock-uuid",
        local_key="wV[NcWGUSFF`dSgO",
        device_id="767823809c9c1f458745",
        category="ms",
        product_id="kpn4zaf7",
        device_name="BSTUOKEY RX2052",
        product_model="RX2052",
        product_name="Invisible induction lock",
        functions=[
            {
                "code": "lock_motor_state",
                "dp_id": 47,
                "type": "Boolean",
                "values": None,
            },
            {
                "code": "beep_volume",
                "dp_id": 31,
                "type": "Enum",
                "values": '{"range": ["mute", "low", "normal", "high"]}',
            },
            {
                "code": "language",
                "dp_id": 28,
                "type": "Enum",
                "values": '{"range": ["chinese_simplified", "english"]}',
            },
            {"code": "ble_unlock_check", "dp_id": 71, "type": "String", "values": None},
        ],
        status_range=[
            {
                "code": "alarm_lock",
                "dp_id": 21,
                "type": "Enum",
                "values": '{"range": ["wrong_finger", "wrong_password", "wrong_card"]}',
            },
            {"code": "battery", "dp_id": 9, "type": "String", "values": None},
            {"code": "unlock_card", "dp_id": 15, "type": "Integer", "values": None},
            {"code": "unlock_ble", "dp_id": 19, "type": "Integer", "values": None},
        ],
    )
    device.append_functions(
        device._device_info.functions, device._device_info.status_range
    )

    product_info = get_device_product_info(device)
    assert product_info is not None
    assert product_info.lock == 1

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

    # --- Test 1: Lock platform with fallback logic ---
    lock_entity = TuyaBLELock(hass, coordinator, device, product_info)
    lock_entity.async_write_ha_state = Mock()

    # Verify fallback detection
    assert lock_entity.find_dpid(DPCode.MANUAL_LOCK) is None
    assert lock_entity.find_dpid(DPCode.LOCK_MOTOR_STATE) == 47

    # Initial lock state (defaults to False on get_or_create -> is_locked is True)
    assert lock_entity.is_locked is True

    # Set LOCK_MOTOR_STATE = True (means unlocked in properties)
    device.datapoints._update_from_device(47, 0, 0, TuyaBLEDataPointType.DT_BOOL, True)
    lock_entity._handle_coordinator_update()
    assert lock_entity.is_locked is False

    # Calling async_lock should set LOCK_MOTOR_STATE (DP 47) to False
    await lock_entity.async_lock()
    await hass.async_block_till_done()
    device._send_datapoints.assert_called_with([47])
    assert device.datapoints[47].value is False

    # Calling async_unlock should set LOCK_MOTOR_STATE (DP 47) to True
    await lock_entity.async_unlock()
    await hass.async_block_till_done()
    device._send_datapoints.assert_called_with([47])
    assert device.datapoints[47].value is True

    # --- Test 2: Sensors platform ---
    sensor_mappings = get_mapping_by_device(device)
    # Filter mapping lists
    battery_mapping = next(m for m in sensor_mappings if m.description.key == "battery")
    alarm_mapping = next(
        m for m in sensor_mappings if m.description.key == "alarm_lock"
    )
    card_mapping = next(
        m for m in sensor_mappings if m.description.key == "unlock_card"
    )
    ble_mapping = next(m for m in sensor_mappings if m.description.key == "unlock_ble")

    # Instantiate sensor entities
    battery_sensor = TuyaBLESensor(
        hass, coordinator, device, product_info, battery_mapping
    )
    battery_sensor.async_write_ha_state = Mock()

    # Update battery string value from device
    device.datapoints._update_from_device(
        9, 0, 0, TuyaBLEDataPointType.DT_STRING, "medium"
    )
    battery_sensor._handle_coordinator_update()
    assert battery_sensor.native_value == 60

    device.datapoints._update_from_device(
        9, 0, 0, TuyaBLEDataPointType.DT_STRING, "high"
    )
    battery_sensor._handle_coordinator_update()
    assert battery_sensor.native_value == 90

    # --- Test 3: Select platform ---
    select_mappings = get_select_mapping(device)
    beep_select_mapping = next(
        m for m in select_mappings if m.description.key == "beep_volume"
    )
    lang_select_mapping = next(
        m for m in select_mappings if m.description.key == "language"
    )

    beep_select = TuyaBLESelect(
        hass, coordinator, device, product_info, beep_select_mapping
    )
    beep_select.async_write_ha_state = Mock()

    # Default option
    assert beep_select.current_option is None

    # Update state from device
    device.datapoints._update_from_device(
        31, 0, 0, TuyaBLEDataPointType.DT_ENUM, 2
    )  # normal
    beep_select._handle_coordinator_update()
    assert beep_select.current_option == "normal"

    # Select option
    await hass.async_add_executor_job(beep_select.select_option, "high")
    await hass.async_block_till_done()
    device._send_datapoints.assert_called_with([31])
    assert device.datapoints[31].value == 3

    # --- Test 4: Button platform ---
    button_mappings = get_button_mapping(device)
    unlock_check_mapping = next(
        m for m in button_mappings if m.description.key == "ble_unlock_check"
    )

    unlock_button = TuyaBLEButton(
        hass, coordinator, device, product_info, unlock_check_mapping
    )
    unlock_button.async_write_ha_state = Mock()

    # Press button
    await hass.async_add_executor_job(unlock_button.press)
    await hass.async_block_till_done()
    device._send_datapoints.assert_called_with([71])
    assert device.datapoints[71].value is True
