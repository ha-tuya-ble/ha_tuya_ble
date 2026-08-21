"""Test for tuya_ble lawn mower."""

from unittest.mock import AsyncMock, Mock

from homeassistant.components.lawn_mower import (
    LawnMowerActivity,
    LawnMowerEntityFeature,
)
from homeassistant.core import HomeAssistant

from custom_components.tuya_ble.lawn_mower import (
    TuyaBLELawnMower,
    get_mapping_by_device,
)
from custom_components.tuya_ble.tuya_ble import (
    TuyaBLEDataPointType,
    TuyaBLEDeviceCredentials,
)

from . import *

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "entity_category": "None",
                "friendly_name": "Mower 1",
                "icon": "",
                "id": "lawn_mower",
                "platform": "lawn_mower",
                "restore_on_reconnect": False,
                "address": "12:23:44",
            }
        ],
    }
}

# Indices into the DP 101 and DP 115 enum values of the Parkside mapping.
STATUS_MOWING = 2
STATUS_PAUSED = 3
STATUS_PARK = 4
COMMAND_PAUSE_WORK = 0
COMMAND_CONTINUE_WORK = 2
COMMAND_START_MOWING = 3
COMMAND_START_RETURN_STATION = 5


async def _init_mower(hass: HomeAssistant):
    """Set up a lawn mower entity using the Parkside mapping."""
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
    product_info = TuyaBLEProductInfo("Fake Mower Product")

    # Mock _send_datapoints to prevent actual BLE calls and exceptions
    device._send_datapoints = AsyncMock()

    hass.data.setdefault(DOMAIN, {})
    coordinator = TuyaBLECoordinator(hass, device)

    hass.data[DOMAIN][entry.entry_id] = TuyaBLEData(
        title="Hello",
        device=device,
        manager=manager,
        product=product_info,
        coordinator=coordinator,
    )

    # category and product_id are read from the cloud credentials
    device._device_info = TuyaBLEDeviceCredentials(
        uuid="",
        local_key="",
        device_id="",
        category="gcj",
        product_id="9hdajpiw",
        device_name=None,
        product_model=None,
        product_name=None,
        functions=None,
        status_range=None,
    )
    mapping = get_mapping_by_device(device)
    assert mapping is not None

    entity = TuyaBLELawnMower(hass, coordinator, device, product_info, mapping)
    entity.async_write_ha_state = Mock()

    return device, coordinator, entity


async def test_lawn_mower_activity(hass: HomeAssistant) -> None:
    """Test that the machine status DP maps to the reported activity."""
    device, coordinator, entity = await _init_mower(hass)

    assert entity.available is False
    coordinator._async_handle_connect()
    assert entity.available is True

    assert entity.supported_features == (
        LawnMowerEntityFeature.START_MOWING
        | LawnMowerEntityFeature.PAUSE
        | LawnMowerEntityFeature.DOCK
    )

    # No status reported yet
    assert entity.activity is None

    # STANDBY and CHARGING both report as docked
    device.datapoints._update_from_device(101, 0, 0, TuyaBLEDataPointType.DT_ENUM, 0)
    assert entity.activity == LawnMowerActivity.DOCKED
    device.datapoints._update_from_device(101, 0, 0, TuyaBLEDataPointType.DT_ENUM, 1)
    assert entity.activity == LawnMowerActivity.DOCKED

    device.datapoints._update_from_device(
        101, 0, 0, TuyaBLEDataPointType.DT_ENUM, STATUS_MOWING
    )
    assert entity.activity == LawnMowerActivity.MOWING

    device.datapoints._update_from_device(
        101, 0, 0, TuyaBLEDataPointType.DT_ENUM, STATUS_PAUSED
    )
    assert entity.activity == LawnMowerActivity.PAUSED

    device.datapoints._update_from_device(
        101, 0, 0, TuyaBLEDataPointType.DT_ENUM, STATUS_PARK
    )
    assert entity.activity == LawnMowerActivity.RETURNING

    # EDGE is the last declared value and also counts as mowing
    device.datapoints._update_from_device(101, 0, 0, TuyaBLEDataPointType.DT_ENUM, 12)
    assert entity.activity == LawnMowerActivity.MOWING

    # EMERGENCY is reported as an error
    device.datapoints._update_from_device(101, 0, 0, TuyaBLEDataPointType.DT_ENUM, 10)
    assert entity.activity == LawnMowerActivity.ERROR

    # An index outside the declared values has no activity
    device.datapoints._update_from_device(101, 0, 0, TuyaBLEDataPointType.DT_ENUM, 99)
    assert entity.activity is None

    # A status sent as a string is mapped by value
    device.datapoints._update_from_device(
        101, 0, 0, TuyaBLEDataPointType.DT_STRING, "MOWING"
    )
    assert entity.activity == LawnMowerActivity.MOWING


async def test_lawn_mower_commands(hass: HomeAssistant) -> None:
    """Test that the actions write the expected command to the command DP."""
    device, coordinator, entity = await _init_mower(hass)

    await entity.async_start_mowing()
    await hass.async_block_till_done()
    device._send_datapoints.assert_any_call([115])
    assert device.datapoints[115].value == COMMAND_START_MOWING

    await entity.async_pause()
    await hass.async_block_till_done()
    assert device.datapoints[115].value == COMMAND_PAUSE_WORK

    await entity.async_dock()
    await hass.async_block_till_done()
    assert device.datapoints[115].value == COMMAND_START_RETURN_STATION


async def test_lawn_mower_start_resumes_when_paused(hass: HomeAssistant) -> None:
    """Test that starting while paused resumes instead of starting a new job."""
    device, coordinator, entity = await _init_mower(hass)

    device.datapoints._update_from_device(
        101, 0, 0, TuyaBLEDataPointType.DT_ENUM, STATUS_PAUSED
    )
    assert entity.activity == LawnMowerActivity.PAUSED

    await entity.async_start_mowing()
    await hass.async_block_till_done()
    assert device.datapoints[115].value == COMMAND_CONTINUE_WORK
