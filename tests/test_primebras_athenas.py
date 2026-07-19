"""Test for Primebras Athenas and Foxgard lock products."""

from unittest.mock import AsyncMock
from homeassistant.core import HomeAssistant
from custom_components.tuya_ble.devices import devices_database
from custom_components.tuya_ble.sensor import (
    get_mapping_by_device as get_sensor_mapping,
)
from custom_components.tuya_ble.binary_sensor import (
    get_mapping_by_device as get_binary_sensor_mapping,
)
from custom_components.tuya_ble.select import (
    get_mapping_by_device as get_select_mapping,
)
from custom_components.tuya_ble.switch import (
    get_mapping_by_device as get_switch_mapping,
)
from custom_components.tuya_ble.number import (
    get_mapping_by_device as get_number_mapping,
)
from custom_components.tuya_ble.tuya_ble import TuyaBLEDevice, TuyaBLEDeviceCredentials
from bleak.backends.device import BLEDevice


async def test_primebras_athenas_lock_database_registration() -> None:
    """Test both lock products are registered under the ms category with lock=1."""
    category_info = devices_database.get("ms")
    assert category_info is not None

    athenas = category_info.products.get("6fibxtph")
    assert athenas is not None
    assert athenas.name == "Primebras Athenas Lock"
    assert athenas.manufacturer == "Primebras"
    assert athenas.lock == 1

    foxgard = category_info.products.get("99gv5nmz")
    assert foxgard is not None
    assert foxgard.name == "Foxgard Smart Fingerprint Door Lock"
    assert foxgard.manufacturer == "Foxgard"
    assert foxgard.lock == 1


async def test_primebras_athenas_mappings() -> None:
    """Test that correct entities are mapped for both locks."""
    ble_device = BLEDevice(
        name="bob", address="11:22:33:44:55:66", details="", rssi=-50
    )

    for product_id in ["6fibxtph", "99gv5nmz"]:
        credentials = TuyaBLEDeviceCredentials(
            uuid="mock_uuid",
            local_key="mock_key",
            device_id="mock_id",
            category="ms",
            product_id=product_id,
            device_name="mock_name",
            product_model="mock_model",
            product_name="mock_name",
            functions=[],
            status_range=[],
        )
        device = TuyaBLEDevice(None, ble_device)
        device._device_info = credentials
        device._send_datapoints = AsyncMock()

        # Check sensor mappings
        sensor_mappings = get_sensor_mapping(device)
        # Should contain Alarm Lock (DP 21) and Battery (DP 8)
        sensor_keys = {mapping.description.key for mapping in sensor_mappings}
        assert "alarm_lock" in sensor_keys
        assert "battery" in sensor_keys

        # Check binary sensor mappings
        binary_mappings = get_binary_sensor_mapping(device)
        binary_keys = {mapping.description.key for mapping in binary_mappings}
        assert "lock_motor_state" in binary_keys

        # Check select mappings
        select_mappings = get_select_mapping(device)
        select_keys = {mapping.description.key for mapping in select_mappings}
        assert "beep_volume" in select_keys
        assert "language" in select_keys

        # Check switch mappings
        switch_mappings = get_switch_mapping(device)
        switch_keys = {mapping.description.key for mapping in switch_mappings}
        assert "lock_motor_state" in switch_keys
        assert "manual_lock" in switch_keys
        assert "automatic_lock" in switch_keys

        # Check number mappings
        number_mappings = get_number_mapping(device)
        number_keys = {mapping.description.key for mapping in number_mappings}
        assert "auto_lock_time" in number_keys
