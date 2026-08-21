"""Test for the raw Parkside mower datapoints."""

from struct import pack
from unittest.mock import AsyncMock, Mock

from homeassistant.core import HomeAssistant

from custom_components.tuya_ble.const import PARKSIDE_MOWER_ERRORS
from custom_components.tuya_ble.sensor import (
    TuyaBLESensor,
    mapping as sensor_mapping,
)
from custom_components.tuya_ble.number import (
    TuyaBLENumber,
    mapping as number_mapping,
)
from custom_components.tuya_ble.tuya_ble import TuyaBLEDataPointType

from . import *

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "entity_category": "None",
                "friendly_name": "Mower 1",
                "icon": "",
                "id": "sensor",
                "platform": "sensor",
                "restore_on_reconnect": False,
                "address": "12:23:44",
            }
        ],
    }
}


async def _init(hass: HomeAssistant):
    """Set up a coordinator and device for the Parkside mower."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.tuya_ble.const import DOMAIN
    from custom_components.tuya_ble.cloud import HASSTuyaBLEDeviceManager
    from custom_components.tuya_ble.devices import (
        TuyaBLECoordinator,
        TuyaBLEData,
        TuyaBLEDevice,
        TuyaBLEProductInfo,
    )
    from bleak.backends.device import BLEDevice

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"devices": CONFIG, "address": DEVICE_ADDRESS},
        title="Mock TuyaBLE",
    )
    entry.add_to_hass(hass)

    ble_device = BLEDevice(name="bob", address="11:22:33", details="", rssi=-50)
    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())
    device = TuyaBLEDevice(manager, ble_device)
    await device.initialize()
    device._send_datapoints = AsyncMock()
    product_info = TuyaBLEProductInfo("Robot Mower")

    hass.data.setdefault(DOMAIN, {})
    coordinator = TuyaBLECoordinator(hass, device)
    hass.data[DOMAIN][entry.entry_id] = TuyaBLEData(
        title="Hello",
        device=device,
        manager=manager,
        product=product_info,
        coordinator=coordinator,
    )
    return device, coordinator, product_info


def _sensor(hass, coordinator, device, product, key):
    """Build the mower sensor with the given key from the real mapping."""
    mapping = {
        m.description.key: m for m in sensor_mapping["gcj"].products["9hdajpiw"]
    }[key]
    entity = TuyaBLESensor(hass, coordinator, device, product, mapping)
    entity.async_write_ha_state = Mock()
    return entity


def _raw(device, dp_id, payload):
    device.datapoints._update_from_device(
        dp_id, 0, 0, TuyaBLEDataPointType.DT_RAW, payload
    )


async def test_error_log(hass: HomeAssistant) -> None:
    """Test DP 111, a uint32 epoch plus an index into the error bitmap."""
    device, coordinator, product = await _init(hass)
    entity = _sensor(hass, coordinator, device, product, "error_log")

    # One populated entry followed by an empty one, which is skipped
    payload = pack(">IB", 1700000000, 2) + pack(">IB", 0, 0)
    _raw(device, 111, payload)
    entity._handle_coordinator_update()

    assert entity.native_value == 1
    errors = entity.extra_state_attributes["errors"]
    assert errors[0]["error"] == PARKSIDE_MOWER_ERRORS[2] == "NO_SIGNAL"
    assert errors[0]["time"].startswith("2023-11-14T")


async def test_work_log(hass: HomeAssistant) -> None:
    """Test DP 112, a uint32 start plus a uint32 duration plus a mode."""
    device, coordinator, product = await _init(hass)
    entity = _sensor(hass, coordinator, device, product, "work_log")

    _raw(device, 112, pack(">IIB", 1700000000, 3600, 2))
    entity._handle_coordinator_update()

    assert entity.native_value == 1
    session = entity.extra_state_attributes["sessions"][0]
    assert session["duration_seconds"] == 3600
    assert session["mode"] == "spot_mowing"


async def test_error_log_2(hass: HomeAssistant) -> None:
    """Test DP 150, a packed date and time plus two error indexes."""
    device, coordinator, product = await _init(hass)
    entity = _sensor(hass, coordinator, device, product, "error_log_2")

    # 2024-03-09 14:31:07, errors 0 and 3, then an entry with an invalid month
    _raw(device, 150, bytes([24, 3, 9, 14, 31, 7, 0, 3]) + bytes(8))
    entity._handle_coordinator_update()

    assert entity.native_value == 1
    entry = entity.extra_state_attributes["errors"][0]
    assert entry["time"].startswith("2024-03-09T14:31:07")
    assert entry["errors"] == ["FAULT_LEAN", "L_MOTOR_ERROR"]


async def test_schedule(hass: HomeAssistant) -> None:
    """Test DP 110, where 0x88 marks an unused slot."""
    device, coordinator, product = await _init(hass)
    entity = _sensor(hass, coordinator, device, product, "schedule")

    used = bytes([2, 9, 30, 11, 45])
    unused = bytes([3, 0x88, 0x88, 0x88, 0x88])
    _raw(device, 110, used + unused)
    entity._handle_coordinator_update()

    assert entity.native_value == 1
    slot = entity.extra_state_attributes["slots"][0]
    assert (slot["weekday"], slot["start"], slot["end"]) == (2, "09:30", "11:45")


async def test_work_schedule(hass: HomeAssistant) -> None:
    """Test DP 140, using the bit packing example from the device model."""
    device, coordinator, product = await _init(hass)
    entity = _sensor(hass, coordinator, device, product, "work_schedule")

    # Model example: set and potential energy, 01:15 to 10:45
    task = bytes([0b11000000, 0b00001010, 0b01010110])
    _raw(device, 140, task + bytes([0, 0, 0]))
    entity._handle_coordinator_update()

    assert entity.native_value == 1
    entry = entity.extra_state_attributes["tasks"][0]
    assert entry["start"] == "01:15"
    assert entry["end"] == "10:45"
    assert entry["potential_energy"] is True


async def test_zones(hass: HomeAssistant) -> None:
    """Test DP 113, a uint32 passage length plus an area share."""
    device, coordinator, product = await _init(hass)
    entity = _sensor(hass, coordinator, device, product, "zones")

    _raw(device, 113, pack(">IB", 25, 60) + pack(">IB", 0, 0))
    entity._handle_coordinator_update()

    assert entity.native_value == 1
    zone = entity.extra_state_attributes["zones"][0]
    assert zone["passage_length_m"] == 25
    assert zone["area_share_percent"] == 60


async def test_rain_delay(hass: HomeAssistant) -> None:
    """Test DP 139, where the first byte follows the rain mode switch."""
    device, coordinator, product = await _init(hass)
    mapping = {
        m.description.key: m for m in number_mapping["gcj"].products["9hdajpiw"]
    }["rain_delay"]
    entity = TuyaBLENumber(hass, coordinator, device, product, mapping)
    entity.async_write_ha_state = Mock()

    # Nothing reported yet
    assert entity.native_value is None

    _raw(device, 139, bytes([1, 45]))
    assert entity.native_value == 45

    # Rain mode on, so the first byte is written as enabled
    device.datapoints._update_from_device(
        104, 0, 0, TuyaBLEDataPointType.DT_BOOL, True
    )
    entity.set_native_value(60)
    await hass.async_block_till_done()
    assert device.datapoints[139].value == bytes([1, 60])

    # Rain mode off, so the first byte follows it down
    device.datapoints._update_from_device(
        104, 0, 0, TuyaBLEDataPointType.DT_BOOL, False
    )
    entity.set_native_value(30)
    await hass.async_block_till_done()
    assert device.datapoints[139].value == bytes([0, 30])
