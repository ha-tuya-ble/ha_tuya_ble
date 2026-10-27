"""Tests for the MiBoxer BS64 stair controller light (c2twgywo)."""

from unittest.mock import AsyncMock, Mock

from bleak.backends.device import BLEDevice
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ColorMode,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tuya_ble.cloud import HASSTuyaBLEDeviceManager
from custom_components.tuya_ble.const import DOMAIN
from custom_components.tuya_ble.devices import (
    TuyaBLECoordinator,
    TuyaBLEData,
    TuyaBLEDevice,
    TuyaBLEProductInfo,
)
from custom_components.tuya_ble.light import TuyaBLEStairLight, async_setup_entry
from custom_components.tuya_ble.tuya_ble.manager import TuyaBLEDeviceCredentials
from custom_components.tuya_ble.tuya_ble.tuya_ble import TuyaBLEDataPointType

MODE_DP = 114
BRIGHTNESS_DP = 3
COLOR_TEMP_DP = 4
WORK_MODE_DP = 2


async def _setup_stair_light(
    hass: HomeAssistant,
) -> tuple[TuyaBLEDevice, TuyaBLEStairLight]:
    entry = MockConfigEntry(domain=DOMAIN, data={"address": "11:22:33:44:55:66"})
    entry.add_to_hass(hass)

    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())
    device = TuyaBLEDevice(manager, BLEDevice("11:22:33:44:55:66", "BS64", {}))
    device._device_info = TuyaBLEDeviceCredentials(
        uuid="uuid123",
        local_key="0123456789abcdef",
        device_id="eb49abgupvuqmz7p",
        category="dj",
        product_id="c2twgywo",
        device_name="Stair Light",
        product_model="BS64",
        product_name="BS64",
        functions=[],
        status_range=[],
    )
    device._send_datapoints = AsyncMock()

    coordinator = TuyaBLECoordinator(hass, device)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = TuyaBLEData(
        title="Stair Light",
        device=device,
        manager=manager,
        product=TuyaBLEProductInfo("BS64 Stair Light Controller", "MiBoxer"),
        coordinator=coordinator,
    )

    add_entities = Mock()
    await async_setup_entry(hass, entry, add_entities)
    entities = add_entities.call_args.args[0]
    assert len(entities) == 1
    entity = entities[0]
    entity.async_write_ha_state = Mock()
    coordinator._async_handle_connect()
    return device, entity


def _report_mode(device: TuyaBLEDevice, mode: int) -> None:
    device.datapoints._update_from_device(
        MODE_DP, 0, 0, TuyaBLEDataPointType.DT_ENUM, mode
    )


async def test_stair_light_uses_mode_for_state(hass: HomeAssistant) -> None:
    """Auto and Off read as off, On reads as on."""
    device, entity = await _setup_stair_light(hass)

    assert isinstance(entity, TuyaBLEStairLight)
    # COLOR_TEMP includes brightness; BRIGHTNESS is only valid on its own.
    assert entity.supported_color_modes == {ColorMode.COLOR_TEMP}

    for mode, expected in ((0, False), (1, True), (2, False)):
        _report_mode(device, mode)
        assert entity.is_on is expected


async def test_stair_light_turn_on_and_off_set_mode(hass: HomeAssistant) -> None:
    """Turning on from Auto selects On mode; turning off selects Off mode."""
    device, entity = await _setup_stair_light(hass)
    _report_mode(device, 0)

    entity.turn_on()
    await hass.async_block_till_done()
    device._send_datapoints.assert_called_once_with([MODE_DP])
    assert device.datapoints[MODE_DP].value == 1
    # The device forces DP1 back on, so it is never sent.
    assert device.datapoints[1] is None

    device._send_datapoints.reset_mock()
    entity.turn_off()
    await hass.async_block_till_done()
    device._send_datapoints.assert_called_once_with([MODE_DP])
    assert device.datapoints[MODE_DP].value == 2


async def test_stair_light_brightness(hass: HomeAssistant) -> None:
    """Brightness maps onto DP3 (10-1000), sent with white work mode.

    The device ignores DP3 unless work_mode (DP2) is in the same packet, and
    the mode is not re-sent when already on.
    """
    device, entity = await _setup_stair_light(hass)
    _report_mode(device, 1)

    entity.turn_on(**{ATTR_BRIGHTNESS: 255})
    await hass.async_block_till_done()
    device._send_datapoints.assert_called_once_with([WORK_MODE_DP, BRIGHTNESS_DP])
    assert device.datapoints[WORK_MODE_DP].value == 0
    assert device.datapoints[BRIGHTNESS_DP].value == 1000


async def test_stair_light_turn_on_from_auto_with_brightness(
    hass: HomeAssistant,
) -> None:
    """Turning on from Auto with a brightness sends everything in one packet."""
    device, entity = await _setup_stair_light(hass)
    _report_mode(device, 0)

    entity.turn_on(**{ATTR_BRIGHTNESS: 255})
    await hass.async_block_till_done()
    device._send_datapoints.assert_called_once_with(
        [MODE_DP, WORK_MODE_DP, BRIGHTNESS_DP]
    )
    assert device.datapoints[MODE_DP].value == 1
    assert device.datapoints[WORK_MODE_DP].value == 0
    assert device.datapoints[BRIGHTNESS_DP].value == 1000


async def test_stair_light_color_temp(hass: HomeAssistant) -> None:
    """Colour temperature maps kelvin linearly onto DP4 (0 warm, 1000 cool)."""
    device, entity = await _setup_stair_light(hass)
    _report_mode(device, 1)
    warm, cool = entity.min_color_temp_kelvin, entity.max_color_temp_kelvin

    for kelvin, expected in ((warm, 0), (cool, 1000), ((warm + cool) / 2, 500)):
        device._send_datapoints.reset_mock()
        entity.turn_on(**{ATTR_COLOR_TEMP_KELVIN: kelvin})
        await hass.async_block_till_done()
        device._send_datapoints.assert_called_once_with([WORK_MODE_DP, COLOR_TEMP_DP])
        assert device.datapoints[COLOR_TEMP_DP].value == expected

    device.datapoints._update_from_device(
        COLOR_TEMP_DP, 0, 0, TuyaBLEDataPointType.DT_VALUE, 0
    )
    assert entity.color_temp_kelvin == warm
    assert entity.color_mode == ColorMode.COLOR_TEMP
