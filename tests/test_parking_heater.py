"""Tests for the MaXpeedingRods parking diesel heater (qn / vmdizama)."""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.components.climate import HVACAction, HVACMode, ClimateEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from custom_components.tuya_ble import climate as climate_mod
from custom_components.tuya_ble import select as select_mod
from custom_components.tuya_ble import sensor as sensor_mod
from custom_components.tuya_ble.devices import get_product_info_by_ids
from custom_components.tuya_ble.tuya_ble import TuyaBLEDataPointType

from . import *

HEATER = SimpleNamespace(category="qn", product_id="vmdizama")
BOOL = TuyaBLEDataPointType.DT_BOOL
VALUE = TuyaBLEDataPointType.DT_VALUE
ENUM = TuyaBLEDataPointType.DT_ENUM


async def _setup(hass: HomeAssistant):
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from bleak.backends.device import BLEDevice
    from custom_components.tuya_ble.const import DOMAIN
    from custom_components.tuya_ble.cloud import HASSTuyaBLEDeviceManager
    from custom_components.tuya_ble.devices import (
        TuyaBLECoordinator,
        TuyaBLEData,
        TuyaBLEDevice,
    )

    entry = MockConfigEntry(
        domain=DOMAIN, data={"address": DEVICE_ADDRESS}, title="Heater"
    )
    entry.add_to_hass(hass)
    ble_device = BLEDevice(
        name="heater", address="DC:23:4F:7C:11:BC", details="", rssi=-50
    )
    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())
    device = TuyaBLEDevice(manager, ble_device)
    await device.initialize()
    device._send_datapoints = AsyncMock()
    product = get_product_info_by_ids("qn", "vmdizama")
    coordinator = TuyaBLECoordinator(hass, device)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = TuyaBLEData(
        title="Heater",
        device=device,
        manager=manager,
        product=product,
        coordinator=coordinator,
    )
    coordinator._async_handle_connect()
    return device, coordinator, product


def _dp(device, dp_id, dp_type, value):
    device.datapoints._update_from_device(dp_id, 0, 0, dp_type, value)


# --------------------------------------------------------------------------- mappings


def test_trv_mappings_unchanged():
    """The heater-only options must not leak into other climate devices."""
    for category in ("wk", "wkf"):
        for products in climate_mod.mapping[category].products.values():
            for m in products:
                assert m.target_temperature_scale is None
                assert m.hvac_action_from_switch is False
                assert (m.target_temperature_min, m.target_temperature_max) == (
                    5.0,
                    30.0,
                )
    assert "zmachryv" in climate_mod.mapping["wk"].products


# --------------------------------------------------------------------------- climate


async def test_climate(hass: HomeAssistant) -> None:
    device, coordinator, product = await _setup(hass)
    mapping = climate_mod.get_mapping_by_device(HEATER)[0]
    entity = climate_mod.TuyaBLEClimate(hass, coordinator, device, product, mapping)
    entity.async_write_ha_state = Mock()

    assert entity.unique_id.endswith("-parking_heater")
    assert not entity.supported_features & ClimateEntityFeature.PRESET_MODE
    assert entity.supported_features & ClimateEntityFeature.TARGET_TEMPERATURE
    assert (entity.min_temp, entity.max_temp, entity.target_temperature_step) == (
        0.0,
        40.0,
        1.0,
    )

    # Running, exchanger at 162 C, set point 22 C
    _dp(device, 1, BOOL, True)
    _dp(device, 2, VALUE, 22)
    _dp(device, 3, VALUE, 162)
    entity._handle_coordinator_update()
    assert entity.hvac_mode == HVACMode.HEAT
    assert entity.hvac_action == HVACAction.HEATING
    assert entity.target_temperature == 22.0
    assert entity.current_temperature is None  # exchanger temp is NOT room temp

    # Switched off
    _dp(device, 1, BOOL, False)
    entity._handle_coordinator_update()
    assert entity.hvac_mode == HVACMode.OFF
    assert entity.hvac_action == HVACAction.OFF

    # Set point is written 1:1 as a value DP (not doubled like the TRVs)
    await entity.async_set_temperature(temperature=25)
    await hass.async_block_till_done()
    assert device.datapoints[2].value == 25
    assert device.datapoints[2].type == VALUE
    device._send_datapoints.assert_any_call([2])

    # On / off goes to DP 1 as a bool
    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await hass.async_block_till_done()
    assert device.datapoints[1].value is True
    assert device.datapoints[1].type == BOOL
    device._send_datapoints.assert_any_call([1])
    await entity.async_set_hvac_mode(HVACMode.OFF)
    await hass.async_block_till_done()
    assert device.datapoints[1].value is False


async def test_climate_before_any_report(hass: HomeAssistant) -> None:
    """No data yet must not raise."""
    device, coordinator, product = await _setup(hass)
    mapping = climate_mod.get_mapping_by_device(HEATER)[0]
    entity = climate_mod.TuyaBLEClimate(hass, coordinator, device, product, mapping)
    entity.async_write_ha_state = Mock()
    entity._handle_coordinator_update()
    assert entity.target_temperature is None
    assert entity.current_temperature is None


# --------------------------------------------------------------------------- selects


async def test_mode_select(hass: HomeAssistant) -> None:
    device, coordinator, product = await _setup(hass)
    m = select_mod.get_mapping_by_device(HEATER)[0]
    entity = select_mod.TuyaBLESelect(hass, coordinator, device, product, m)
    assert entity.current_option is None
    _dp(device, 4, ENUM, 1)
    assert entity.current_option == "auto"
    entity.select_option("smart")
    await hass.async_block_till_done()
    assert device.datapoints[4].value == 0
    assert device.datapoints[4].type == ENUM
    device._send_datapoints.assert_any_call([4])


async def test_level_select(hass: HomeAssistant) -> None:
    device, coordinator, product = await _setup(hass)
    m = select_mod.get_mapping_by_device(HEATER)[1]
    entity = select_mod.TuyaBLESelect(hass, coordinator, device, product, m)
    _dp(device, 5, ENUM, 4)
    assert entity.current_option == "5"  # levels 4-5 can still be displayed
    entity.select_option("2")
    await hass.async_block_till_done()
    assert device.datapoints[5].value == 1
    assert device.datapoints[5].type == ENUM
    device._send_datapoints.assert_any_call([5])

    device._send_datapoints.reset_mock()
    with pytest.raises(HomeAssistantError):
        entity.select_option("4")
    await hass.async_block_till_done()
    device._send_datapoints.assert_not_called()
    assert device.datapoints[5].value == 1


# --------------------------------------------------------------------------- sensors


async def test_work_state(hass: HomeAssistant) -> None:
    device, coordinator, product = await _setup(hass)
    m = sensor_mod.get_mapping_by_device(HEATER)[1]
    entity = sensor_mod.TuyaBLESensor(hass, coordinator, device, product, m)
    entity.async_write_ha_state = Mock()
    entity._handle_coordinator_update()
    assert entity.native_value is None
    _dp(device, 11, ENUM, 0)
    entity._handle_coordinator_update()
    assert entity.native_value == "heating"
    _dp(device, 11, ENUM, 3)
    entity._handle_coordinator_update()
    assert entity.native_value == "state_3"


async def test_exchanger_temperature(hass: HomeAssistant) -> None:
    device, coordinator, product = await _setup(hass)
    m = sensor_mod.get_mapping_by_device(HEATER)[0]
    entity = sensor_mod.TuyaBLESensor(hass, coordinator, device, product, m)
    entity.async_write_ha_state = Mock()
    t0 = dt_util.utcnow()

    def at(seconds, dp3, switch=True):
        _dp(device, 1, BOOL, switch)
        if dp3 is not None:
            _dp(device, 3, VALUE, dp3)
        with patch.object(
            sensor_mod.dt_util, "utcnow", return_value=t0 + timedelta(seconds=seconds)
        ):
            entity._handle_coordinator_update()
        return entity.native_value

    assert at(0, 10) == 10.0  # first reading shown immediately
    assert at(1, 14) == 10.0  # +4 C within 30 s: held
    assert at(2, 15) == 15.0  # +5 C: updated
    assert at(10, 17) == 15.0  # held
    assert at(32, 17) == 17.0  # 30 s since last update: refreshed
    assert at(33, 12) == 12.0  # falling by 5: updated
    assert at(34, 162, switch=False) is None  # off: blank, not stuck
    assert at(35, None, switch=False) is None
    assert at(40, 9) == 9.0  # back on: fresh value immediately


async def test_exchanger_temperature_real_run(hass: HomeAssistant) -> None:
    """Replay a run like 9 Nov (1 report/s, 9 C -> 224 C -> 162 C, then off)."""
    device, coordinator, product = await _setup(hass)
    m = sensor_mod.get_mapping_by_device(HEATER)[0]
    entity = sensor_mod.TuyaBLESensor(hass, coordinator, device, product, m)
    entity.async_write_ha_state = Mock()
    t0 = dt_util.utcnow()
    readings = list(range(9, 225)) + [224] * 3000 + list(range(224, 161, -1))
    shown = []
    _dp(device, 1, BOOL, True)
    for second, temp in enumerate(readings):
        _dp(device, 3, VALUE, temp)
        with patch.object(
            sensor_mod.dt_util, "utcnow", return_value=t0 + timedelta(seconds=second)
        ):
            entity._handle_coordinator_update()
        if not shown or shown[-1] != entity.native_value:
            shown.append(entity.native_value)
        assert abs(entity.native_value - temp) < 5  # never more than ~5 C behind
    # ~3,300 device reports collapse to a few hundred distinct states at most
    assert len(shown) < 150, len(shown)
    _dp(device, 1, BOOL, False)
    entity._handle_coordinator_update()
    assert entity.native_value is None
