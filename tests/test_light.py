"""Test for tuya_ble light."""

from unittest.mock import Mock, AsyncMock
from homeassistant.core import HomeAssistant
from custom_components.tuya_ble.light import TuyaBLELight, TuyaLightEntityDescription
from custom_components.tuya_ble.tuya_ble.tuya_ble import TuyaBLEDataPointType, TuyaBLEDeviceFunction
from custom_components.tuya_ble.const import DPCode, DPType
from custom_components.tuya_ble.tuya_ble.manager import TuyaBLEDeviceCredentials

from . import *

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "entity_category": "None",
                "friendly_name": "Light 1",
                "icon": "",
                "id": "switch_led",
                "platform": "light",
                "restore_on_reconnect": False,
                "address": "12:23:44"
            }
        ],
    }
}


async def test_light(hass: HomeAssistant) -> None:
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
    product_info = TuyaBLEProductInfo("Fake Light Product")

    # Set up TuyaBLEDeviceCredentials directly
    device._device_info = TuyaBLEDeviceCredentials(
        uuid="uuid123",
        local_key="wV[NcWGUSFF`dSgO",
        device_id="767823809c9c1f458745",
        category="dd",
        product_id="nvfrtxlq",
        device_name="Light",
        product_model="Strip Light",
        product_name="Strip Light",
        functions=[],
        status_range=[],
    )

    # Mock _send_datapoints to prevent actual BLE calls and exceptions
    device._send_datapoints = AsyncMock()

    # Populate device.function with DPCode.SWITCH_LED
    device.function[DPCode.SWITCH_LED] = TuyaBLEDeviceFunction(
        code=DPCode.SWITCH_LED,
        dp_id=1,
        type=DPType.BOOLEAN,
        values=None,
    )

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

    description = TuyaLightEntityDescription(
        key=DPCode.SWITCH_LED,
        name="Led",
    )

    entity = TuyaBLELight(
        hass, coordinator, device, product_info, description
    )
    entity.async_write_ha_state = Mock()

    # Initial state
    assert entity.available is False
    coordinator._async_handle_connect()
    assert entity.available is True
    assert entity.is_on is False

    # Update coordinator state via updating DP 1
    device.datapoints._update_from_device(1, 0, 0, TuyaBLEDataPointType.DT_BOOL, True)
    entity._handle_coordinator_update()
    assert entity.is_on is True

    # Call turn_off
    entity.turn_off()
    await hass.async_block_till_done()
    device._send_datapoints.assert_any_call([1])
    assert device.datapoints[1].value is False

    # Call turn_on
    entity.turn_on()
    await hass.async_block_till_done()
    device._send_datapoints.assert_any_call([1])
    assert device.datapoints[1].value is True


async def test_light_color_temp_kelvin(hass: HomeAssistant) -> None:
    """Colour temperature maps linearly between the kelvin bounds and the DP."""
    from homeassistant.components.light import ATTR_COLOR_TEMP_KELVIN, ColorMode
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.tuya_ble.const import DOMAIN
    from custom_components.tuya_ble.cloud import HASSTuyaBLEDeviceManager
    from custom_components.tuya_ble.devices import TuyaBLEDevice, TuyaBLEProductInfo, TuyaBLECoordinator
    from bleak.backends.device import BLEDevice

    entry = MockConfigEntry(domain=DOMAIN, data={"address": DEVICE_ADDRESS})
    entry.add_to_hass(hass)

    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())
    device = TuyaBLEDevice(manager, BLEDevice("11:22:33", "bob", {}))
    device._send_datapoints = AsyncMock()
    product_info = TuyaBLEProductInfo("Fake Light Product")
    coordinator = TuyaBLECoordinator(hass, device)

    description = TuyaLightEntityDescription(
        key=DPCode.SWITCH_LED,
        name=None,
        brightness=DPCode.BRIGHT_VALUE,
        color_temp=DPCode.TEMP_VALUE,
        function=[
            {"code": "switch_led", "dp_id": 1, "type": "Boolean", "values": {}},
            {
                "code": "bright_value",
                "dp_id": 3,
                "type": "Integer",
                "values": {"min": 10, "max": 1000, "scale": 0, "step": 1},
            },
            {
                "code": "temp_value",
                "dp_id": 4,
                "type": "Integer",
                "values": {"min": 0, "max": 1000, "scale": 0, "step": 1},
            },
        ],
        status_range=[],
    )
    entity = TuyaBLELight(hass, coordinator, device, product_info, description)
    entity.async_write_ha_state = Mock()
    coordinator._async_handle_connect()

    # BRIGHTNESS is only valid on its own; COLOR_TEMP already includes it
    assert entity.supported_color_modes == {ColorMode.COLOR_TEMP}

    warm, cool = entity.min_color_temp_kelvin, entity.max_color_temp_kelvin
    for kelvin, expected in ((warm, 0), (cool, 1000), ((warm + cool) / 2, 500)):
        entity.turn_on(**{ATTR_COLOR_TEMP_KELVIN: kelvin})
        await hass.async_block_till_done()
        device._send_datapoints.assert_any_call([4])
        assert device.datapoints[4].value == expected

    device.datapoints._update_from_device(4, 0, 0, TuyaBLEDataPointType.DT_VALUE, 1000)
    assert entity.color_temp_kelvin == cool
    device.datapoints._update_from_device(4, 0, 0, TuyaBLEDataPointType.DT_VALUE, 0)
    assert entity.color_temp_kelvin == warm
