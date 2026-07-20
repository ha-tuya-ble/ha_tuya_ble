"""Test for XCase NX-4964 Lock Box (qicggi0m)."""

from unittest.mock import Mock, AsyncMock
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorEntityDescription
from custom_components.tuya_ble.sensor import TuyaBLESensor, get_mapping_by_device
from custom_components.tuya_ble.lock import TuyaBLELock
from custom_components.tuya_ble.tuya_ble import (
    TuyaBLEDataPointType,
    TuyaBLEDeviceCredentials,
)
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


async def test_xcase_lockbox(hass: HomeAssistant) -> None:
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.tuya_ble.const import DOMAIN
    from custom_components.tuya_ble.cloud import HASSTuyaBLEDeviceManager
    from custom_components.tuya_ble.devices import (
        TuyaBLEDevice,
        TuyaBLEProductInfo,
        TuyaBLECoordinator,
        TuyaBLEData,
        get_device_product_info,
    )
    from bleak.backends.device import BLEDevice

    # Setup mock entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "devices": CONFIG,
            "address": DEVICE_ADDRESS,
        },
        title="Mock TuyaBLE XCase",
    )
    entry.add_to_hass(hass)

    ble_device = BLEDevice(
        name="XCase Lock Box", address="11:22:33", details="", rssi=-50
    )
    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())
    device = TuyaBLEDevice(manager, ble_device)
    await device.initialize()

    # Configure device with category 'jtmspro' and product_id 'qicggi0m'
    device._device_info = TuyaBLEDeviceCredentials(
        uuid="test-uuid",
        local_key="test-key",
        device_id="test-device-id",
        category="jtmspro",
        product_id="qicggi0m",
        device_name="XCase NX-4964 Lock Box",
        product_model="NX-4964 BLE",
        product_name="Lockbox",
        functions=[],
        status_range=[],
    )

    # Prevent real BLE transmission attempts
    device._send_datapoints = AsyncMock()

    # Create coordinator
    coordinator = TuyaBLECoordinator(hass, device)
    product_info = get_device_product_info(device)
    assert product_info is not None
    assert product_info.name == "XCase NX-4964 Lock Box"
    assert product_info.lock == 1

    # Verify lock entity setup
    lock_entity = TuyaBLELock(hass, coordinator, device, product_info)
    lock_entity.async_write_ha_state = Mock()

    # Initial lock state (defaults to locked because get_or_create defaults to False)
    coordinator._async_handle_connect()
    assert lock_entity.is_locked is True

    # Simulation: Motor state changes to unlocked
    device.datapoints._update_from_device(
        DPCode.LOCK_MOTOR_STATE, 0, 0, TuyaBLEDataPointType.DT_BOOL, True
    )
    lock_entity._handle_coordinator_update()
    assert lock_entity.is_locked is False

    # Call async_lock
    await lock_entity.async_lock()
    await hass.async_block_till_done()
    device._send_datapoints.assert_called_with([DPCode.MANUAL_LOCK])
    assert device.datapoints[DPCode.MANUAL_LOCK].value is True

    # Call async_unlock
    await lock_entity.async_unlock()
    await hass.async_block_till_done()
    device._send_datapoints.assert_called_with([DPCode.MANUAL_LOCK])
    assert device.datapoints[DPCode.MANUAL_LOCK].value is False

    # Verify mapped sensors
    sensor_mappings = get_mapping_by_device(device)
    assert len(sensor_mappings) > 0

    # Ensure mapped sensors contain the ones we added
    mapped_keys = [mapping.description.key for mapping in sensor_mappings]
    assert "alarm_lock" in mapped_keys
    assert "unlock_password" in mapped_keys
    assert "unlock_dynamic" in mapped_keys
    assert "unlock_ble" in mapped_keys
    assert "unlock_temp_pwd" in mapped_keys
    assert "unlock_app" in mapped_keys
    assert "unlock_voice" in mapped_keys
    assert "battery" in mapped_keys

    # Instantiate sensors and verify they process updates correctly
    for mapping in sensor_mappings:
        sensor_entity = TuyaBLESensor(hass, coordinator, device, product_info, mapping)
        sensor_entity.async_write_ha_state = Mock()

        # Test simulated updates on DP ids
        if mapping.description.key == "battery":
            device.datapoints._update_from_device(
                mapping.dp_id, 0, 0, TuyaBLEDataPointType.DT_VALUE, 85
            )
            sensor_entity._handle_coordinator_update()
            assert sensor_entity.native_value == 85
        elif mapping.description.key == "unlock_temp_pwd":
            device.datapoints._update_from_device(
                mapping.dp_id, 0, 0, TuyaBLEDataPointType.DT_VALUE, 12345
            )
            sensor_entity._handle_coordinator_update()
            assert sensor_entity.native_value == 12345
        elif mapping.description.key == "alarm_lock":
            # For alarm lock, update to wrong_finger enum (index 0)
            device.datapoints._update_from_device(
                mapping.dp_id, 0, 0, TuyaBLEDataPointType.DT_ENUM, 0
            )
            sensor_entity._handle_coordinator_update()
            assert sensor_entity.native_value == "wrong_finger"
