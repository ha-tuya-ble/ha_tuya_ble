"""Test for tuya_ble climate."""

from unittest.mock import Mock, AsyncMock
from homeassistant.core import HomeAssistant
from homeassistant.components.climate import ClimateEntityDescription, HVACMode, PRESET_AWAY, PRESET_NONE
from custom_components.tuya_ble.climate import TuyaBLEClimate, TuyaBLEClimateMapping
from custom_components.tuya_ble.tuya_ble import TuyaBLEDataPointType

from . import *

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "entity_category": "None",
                "friendly_name": "Climate 1",
                "icon": "",
                "id": "103",
                "platform": "climate",
                "restore_on_reconnect": False,
                "address": "12:23:44"
            }
        ],
    }
}


async def test_climate(hass: HomeAssistant) -> None:
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
    product_info = TuyaBLEProductInfo("Fake Climate Product")

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

    # Map our climate entity
    mapping = TuyaBLEClimateMapping(
        description=ClimateEntityDescription(
            key="thermostatic_radiator_valve",
        ),
        hvac_switch_dp_id=101,
        hvac_switch_mode=HVACMode.HEAT,
        hvac_modes=[HVACMode.OFF, HVACMode.HEAT],
        preset_mode_dp_ids={PRESET_AWAY: 106, PRESET_NONE: 106},
        current_temperature_dp_id=102,
        current_temperature_coefficient=10.0,
        target_temperature_coefficient=10.0,
        target_temperature_step=0.5,
        target_temperature_dp_id=103,
        target_temperature_min=5.0,
        target_temperature_max=30.0,
    )

    entity = TuyaBLEClimate(
        hass, coordinator, device, product_info, mapping
    )
    entity.async_write_ha_state = Mock()

    # Initial availability and connected check
    assert entity.available is False
    coordinator._async_handle_connect()
    assert entity.available is True

    # Test status updates for temperature
    # Update DP 102 (current_temp) to 220 -> 22.0
    device.datapoints._update_from_device(102, 0, 0, TuyaBLEDataPointType.DT_VALUE, 220)
    # Update DP 103 (target_temp) to 42 -> 42 * 0.5 = 21.0
    device.datapoints._update_from_device(103, 0, 0, TuyaBLEDataPointType.DT_VALUE, 42)
    # Update DP 101 (hvac switch) to True -> HVACMode.HEAT
    device.datapoints._update_from_device(101, 0, 0, TuyaBLEDataPointType.DT_BOOL, True)
    # Update DP 106 (preset) to True -> PRESET_AWAY
    device.datapoints._update_from_device(106, 0, 0, TuyaBLEDataPointType.DT_BOOL, True)

    entity._handle_coordinator_update()

    assert entity.current_temperature == 22.0
    assert entity.target_temperature == 21.0
    assert entity.hvac_mode == HVACMode.HEAT
    assert entity.preset_mode == PRESET_AWAY

    # Test setting target temperature
    await entity.async_set_temperature(temperature=23.5)
    await hass.async_block_till_done()
    device._send_datapoints.assert_any_call([103])
    # 23.5 * 2 = 47
    assert device.datapoints[103].value == 47

    # Test setting HVAC mode
    await entity.async_set_hvac_mode(HVACMode.OFF)
    await hass.async_block_till_done()
    device._send_datapoints.assert_any_call([101])
    assert device.datapoints[101].value is False

    # Test setting preset mode
    await entity.async_set_preset_mode(PRESET_NONE)
    await hass.async_block_till_done()
    device._send_datapoints.assert_any_call([106])
    assert device.datapoints[106].value is False
