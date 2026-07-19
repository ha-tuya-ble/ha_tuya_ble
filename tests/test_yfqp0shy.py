"""Tests for Gainsborough Liberty Lock (yfqp0shy) integration."""

from unittest.mock import Mock, AsyncMock
from homeassistant.core import HomeAssistant
from homeassistant.components.lock import LockEntityDescription
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.event import EventDeviceClass
from homeassistant.helpers.entity import EntityCategory
from homeassistant.const import Platform

from custom_components.tuya_ble.lock import TuyaBLELock
from custom_components.tuya_ble.binary_sensor import TuyaBLEBinarySensor, get_mapping_by_device as get_binary_sensor_mapping
from custom_components.tuya_ble.sensor import TuyaBLESensor, get_mapping_by_device as get_sensor_mapping
from custom_components.tuya_ble.switch import TuyaBLESwitch, get_mapping_by_device as get_switch_mapping
from custom_components.tuya_ble.select import TuyaBLESelect, get_mapping_by_device as get_select_mapping
from custom_components.tuya_ble.number import TuyaBLENumber, get_mapping_by_device as get_number_mapping
from custom_components.tuya_ble.event import TuyaBLEEvent, get_mapping_by_device as get_event_mapping

from custom_components.tuya_ble.tuya_ble import TuyaBLEDataPointType
from custom_components.tuya_ble.const import DOMAIN, DPCode

from . import *

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [],
    }
}


async def test_yfqp0shy_lock_integration(hass: HomeAssistant) -> None:
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.tuya_ble.cloud import HASSTuyaBLEDeviceManager
    from custom_components.tuya_ble.devices import TuyaBLEDevice, TuyaBLEProductInfo, TuyaBLECoordinator, TuyaBLEData
    from bleak.backends.device import BLEDevice

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "devices": CONFIG,
            "address": DEVICE_ADDRESS,
        },
        title="Mock Gainsborough Lock",
    )
    entry.add_to_hass(hass)

    ble_device = BLEDevice(name="Gainsborough Lock", address=DEVICE_ADDRESS, details="", rssi=-60)
    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())

    # Configure device characteristics using credentials cache or direct assignment
    device = TuyaBLEDevice(manager, ble_device)
    device._device_info = Mock()
    device._device_info.category = "jtmspro"
    device._device_info.product_id = "yfqp0shy"
    device._device_info.device_name = "Gainsborough Liberty BLE Lock (GGC01HA)"

    await device.initialize()
    product_info = TuyaBLEProductInfo("Gainsborough Liberty BLE Lock (GGC01HA)", lock=1)

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

    # Connect coordinator
    coordinator._async_handle_connect()

    # 1. Test lock entity
    lock_entity = TuyaBLELock(hass, coordinator, device, product_info)
    assert lock_entity.is_locked is True

    # 2. Test binary sensor mappings (DP 47, 22)
    binary_sensor_mappings = get_binary_sensor_mapping(device)
    assert len(binary_sensor_mappings) == 2

    lock_motor_mapping = next(m for m in binary_sensor_mappings if m.dp_id == 47)
    assert lock_motor_mapping.description.key == "lock_motor_state"
    assert lock_motor_mapping.description.device_class == BinarySensorDeviceClass.LOCK

    hijack_mapping = next(m for m in binary_sensor_mappings if m.dp_id == 22)
    assert hijack_mapping.description.key == "hijack"
    assert hijack_mapping.description.device_class == BinarySensorDeviceClass.TAMPER

    # 3. Test event mappings (DP 24)
    event_mappings = get_event_mapping(device)
    assert len(event_mappings) == 1
    doorbell_event_mapping = next(m for m in event_mappings if m.dp_id == 24)
    assert doorbell_event_mapping.description.key == "doorbell"
    assert doorbell_event_mapping.description.device_class == EventDeviceClass.DOORBELL
    assert doorbell_event_mapping.event_types == ["ring"]

    # 4. Test sensor mappings (DP 21, 12, 15, 13, 19, 14, 16, 8)
    sensor_mappings = get_sensor_mapping(device)
    assert any(m.dp_id == 21 for m in sensor_mappings)
    assert any(m.dp_id == 12 for m in sensor_mappings)
    assert any(m.dp_id == 15 for m in sensor_mappings)
    assert any(m.dp_id == 13 for m in sensor_mappings)
    assert any(m.dp_id == 19 for m in sensor_mappings)
    assert any(m.dp_id == 14 for m in sensor_mappings)
    assert any(m.dp_id == 16 for m in sensor_mappings)
    assert any(m.dp_id == 8 for m in sensor_mappings)

    # 5. Test switch mappings (DP 47, 46, 33)
    switch_mappings = get_switch_mapping(device)
    assert any(m.dp_id == 47 for m in switch_mappings)
    assert any(m.dp_id == 46 for m in switch_mappings)
    assert any(m.dp_id == 33 for m in switch_mappings)

    # 6. Test select mappings (DP 34)
    select_mappings = get_select_mapping(device)
    assert any(m.dp_id == 34 for m in select_mappings)

    # 7. Test number mappings (DP 36)
    number_mappings = get_number_mapping(device)
    assert any(m.dp_id == 36 for m in number_mappings)
