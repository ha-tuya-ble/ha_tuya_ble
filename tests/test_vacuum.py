"""Test for tuya_ble vacuum."""

from unittest.mock import Mock, AsyncMock
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.components.vacuum import (
    StateVacuumEntityDescription,
    VacuumActivity,
    VacuumEntityFeature,
)
from custom_components.tuya_ble.vacuum import TuyaBLEVacuumEntity, TuyaBLEVacuumMapping
from custom_components.tuya_ble.tuya_ble import TuyaBLEDataPointType

from . import *

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "entity_category": "None",
                "friendly_name": "Vacuum 1",
                "icon": "",
                "id": "vacuum",
                "platform": "vacuum",
                "restore_on_reconnect": False,
                "address": "12:23:44",
            }
        ],
    }
}


async def test_vacuum_bool_control(hass: HomeAssistant) -> None:
    """Test vacuum entity with basic boolean start/stop control and status mapping."""
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
    product_info = TuyaBLEProductInfo("Fake Vacuum Product")

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

    # Map our vacuum entity with boolean start/stop control and separate mode select
    mapping = TuyaBLEVacuumMapping(
        dp_start_bool=1,
        dp_mode=2,
        dp_status=4,
        dp_pause=5,
        dp_return_home=6,
        fan_speed_list=["smart", "z_mode", "n_mode"],
    )

    entity = TuyaBLEVacuumEntity(hass, coordinator, device, product_info, mapping)
    entity.async_write_ha_state = Mock()

    # Initial state and features check
    assert entity.available is False
    coordinator._async_handle_connect()
    assert entity.available is True

    # Check dynamically assigned features
    expected_features = (
        VacuumEntityFeature.STATE
        | VacuumEntityFeature.START
        | VacuumEntityFeature.STOP
        | VacuumEntityFeature.PAUSE
        | VacuumEntityFeature.RETURN_HOME
        | VacuumEntityFeature.FAN_SPEED
    )
    assert entity.supported_features == expected_features
    assert entity.fan_speed_list == ["smart", "z_mode", "n_mode"]

    # Test Activity when status DP is None (falls back to start bool DP)
    assert entity.activity == VacuumActivity.IDLE
    device.datapoints._update_from_device(1, 0, 0, TuyaBLEDataPointType.DT_BOOL, True)
    assert entity.activity == VacuumActivity.CLEANING
    device.datapoints._update_from_device(1, 0, 0, TuyaBLEDataPointType.DT_BOOL, False)
    assert entity.activity == VacuumActivity.IDLE

    # Test Activity from status DP (string / enum)
    device.datapoints._update_from_device(
        4, 0, 0, TuyaBLEDataPointType.DT_ENUM, 0
    )  # 0 maps to "standby"
    assert entity.activity == VacuumActivity.IDLE

    device.datapoints._update_from_device(
        4, 0, 0, TuyaBLEDataPointType.DT_ENUM, 1
    )  # 1 maps to "cleaning"
    assert entity.activity == VacuumActivity.CLEANING

    # Test unknown status value defaults to VacuumActivity.IDLE
    device.datapoints._update_from_device(4, 0, 0, TuyaBLEDataPointType.DT_ENUM, 99)
    assert entity.activity == VacuumActivity.IDLE

    # Test raw string status value mapping
    device.datapoints._update_from_device(
        4, 0, 0, TuyaBLEDataPointType.DT_STRING, "pause"
    )
    assert entity.activity == VacuumActivity.PAUSED

    # Test fan speed tracking
    assert entity.fan_speed is None
    device.datapoints._update_from_device(
        2, 0, 0, TuyaBLEDataPointType.DT_ENUM, 1
    )  # 1 maps to "z_mode"
    assert entity.fan_speed == "z_mode"

    device.datapoints._update_from_device(
        2, 0, 0, TuyaBLEDataPointType.DT_ENUM, 9
    )  # out of range defaults to string
    assert entity.fan_speed == "9"

    # Test start action (should send True to DP 1)
    await entity.async_start()
    await hass.async_block_till_done()
    device._send_datapoints.assert_any_call([1])
    assert device.datapoints[1].value is True

    # Test stop action (should send False to DP 1)
    await entity.async_stop()
    await hass.async_block_till_done()
    device._send_datapoints.assert_any_call([1])
    assert device.datapoints[1].value is False

    # Test pause action (should send True to DP 5)
    await entity.async_pause()
    await hass.async_block_till_done()
    device._send_datapoints.assert_any_call([5])
    assert device.datapoints[5].value is True

    # Test return to base action (should send True to DP 6)
    await entity.async_return_to_base()
    await hass.async_block_till_done()
    device._send_datapoints.assert_any_call([6])
    assert device.datapoints[6].value is True

    # Test set fan speed (mode) action (should set DP 2 to index and start)
    await entity.async_set_fan_speed("n_mode")
    await hass.async_block_till_done()
    device._send_datapoints.assert_any_call([2])
    device._send_datapoints.assert_any_call([1])
    assert device.datapoints[2].value == 2
    assert device.datapoints[1].value is True


async def test_vacuum_enum_control(hass: HomeAssistant) -> None:
    """Test vacuum entity with enum-based start/stop/pause control and custom return home value."""
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
    product_info = TuyaBLEProductInfo("Fake Vacuum Product")

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

    # Map vacuum with enum start control and custom return home value (int enum)
    mapping = TuyaBLEVacuumMapping(
        dp_start_enum=3,
        start_enum_value=1,
        stop_enum_value=2,
        pause_enum_value=3,
        dp_return_home=6,
        return_home_value=5,
    )

    entity = TuyaBLEVacuumEntity(hass, coordinator, device, product_info, mapping)

    # Check dynamically assigned features
    expected_features = (
        VacuumEntityFeature.STATE
        | VacuumEntityFeature.START
        | VacuumEntityFeature.STOP
        | VacuumEntityFeature.PAUSE
        | VacuumEntityFeature.RETURN_HOME
    )
    assert entity.supported_features == expected_features

    # Test start action (sends start_enum_value 1 on DP 3)
    await entity.async_start()
    await hass.async_block_till_done()
    device._send_datapoints.assert_any_call([3])
    assert device.datapoints[3].value == 1

    # Test stop action (sends stop_enum_value 2 on DP 3)
    await entity.async_stop()
    await hass.async_block_till_done()
    device._send_datapoints.assert_any_call([3])
    assert device.datapoints[3].value == 2

    # Test pause action (sends pause_enum_value 3 on DP 3)
    await entity.async_pause()
    await hass.async_block_till_done()
    device._send_datapoints.assert_any_call([3])
    assert device.datapoints[3].value == 3

    # Test return to base action (sends return_home_value 5 on DP 6)
    await entity.async_return_to_base()
    await hass.async_block_till_done()
    device._send_datapoints.assert_any_call([6])
    assert device.datapoints[6].value == 5


async def test_vacuum_fallback_control(hass: HomeAssistant) -> None:
    """Test vacuum entity fallback behavior for pause/return to base when DPs are missing."""
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
    product_info = TuyaBLEProductInfo("Fake Vacuum Product")

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

    # Map vacuum with ONLY boolean start
    mapping = TuyaBLEVacuumMapping(
        dp_start_bool=1,
    )

    entity = TuyaBLEVacuumEntity(hass, coordinator, device, product_info, mapping)

    # Check dynamically assigned features (should NOT support pause, return home, fan speed)
    expected_features = (
        VacuumEntityFeature.STATE | VacuumEntityFeature.START | VacuumEntityFeature.STOP
    )
    assert entity.supported_features == expected_features

    # Test fallback pause action (should fall back to stop, sending False to DP 1)
    await entity.async_pause()
    await hass.async_block_till_done()
    device._send_datapoints.assert_any_call([1])
    assert device.datapoints[1].value is False

    # Test fallback return to base action (should fall back to stop, sending False to DP 1)
    await entity.async_return_to_base()
    await hass.async_block_till_done()
    device._send_datapoints.assert_any_call([1])
    assert device.datapoints[1].value is False


async def test_vacuum_setup_entry_via_platform(hass: HomeAssistant) -> None:
    """Test setup entry for the vacuum platform."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.tuya_ble.const import DOMAIN
    from custom_components.tuya_ble.cloud import HASSTuyaBLEDeviceManager
    from custom_components.tuya_ble.devices import (
        TuyaBLEDevice,
        TuyaBLEProductInfo,
        TuyaBLECoordinator,
        TuyaBLEData,
    )
    from custom_components.tuya_ble.vacuum import async_setup_entry
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
    product_info = TuyaBLEProductInfo("Fake Vacuum Product")

    # Let's set device category to "cxjmb" and product_id to "pnxl0r3l"
    device._device_info = Mock()
    device._device_info.category = "cxjmb"
    device._device_info.product_id = "pnxl0r3l"

    coordinator = TuyaBLECoordinator(hass, device)

    tuya_ble_hass_data = TuyaBLEData(
        title="Hello",
        device=device,
        manager=manager,
        product=product_info,
        coordinator=coordinator,
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = tuya_ble_hass_data

    # Setup the platform
    async_add_entities = Mock()
    await async_setup_entry(hass, entry, async_add_entities)

    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 1
    assert isinstance(entities[0], TuyaBLEVacuumEntity)
