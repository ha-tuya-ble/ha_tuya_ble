"""Test for tuya_ble select."""

from unittest.mock import Mock, AsyncMock
from homeassistant.core import HomeAssistant
from homeassistant.components.select import SelectEntityDescription
from custom_components.tuya_ble.select import TuyaBLESelect, TuyaBLESelectMapping
from custom_components.tuya_ble.tuya_ble import TuyaBLEDataPointType

from . import *

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "entity_category": "None",
                "friendly_name": "Select 1",
                "icon": "",
                "id": "31",
                "platform": "select",
                "restore_on_reconnect": False,
                "address": "12:23:44"
            }
        ],
    }
}


async def test_select(hass: HomeAssistant) -> None:
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
    product_info = TuyaBLEProductInfo("Fake Select Product")

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

    # Map our select entity
    mapping = TuyaBLESelectMapping(
        dp_id=31,
        description=SelectEntityDescription(
            key="beep_volume",
            options=[
                "mute",
                "low",
                "normal",
                "high",
            ],
        ),
        force_add=True,
    )

    entity = TuyaBLESelect(
        hass, coordinator, device, product_info, mapping
    )
    entity.async_write_ha_state = Mock()

    # Initial state
    assert entity.available is False
    coordinator._async_handle_connect()
    assert entity.available is True
    assert entity.current_option is None

    # Update coordinator state: 1 -> "low"
    device.datapoints._update_from_device(31, 0, 0, TuyaBLEDataPointType.DT_ENUM, 1)
    entity._handle_coordinator_update()
    assert entity.current_option == "low"

    # Call select_option
    entity.select_option("high")
    await hass.async_block_till_done()
    device._send_datapoints.assert_called_once_with([31])
    assert device.datapoints[31].value == 3
    assert entity.current_option == "high"


async def test_select_zwjcy_gpkyrocn(hass: HomeAssistant) -> None:
    from custom_components.tuya_ble.select import get_mapping_by_device, TuyaBLESelect
    from custom_components.tuya_ble.devices import TuyaBLEDevice, TuyaBLECoordinator, TuyaBLEProductInfo, TuyaBLEDeviceCredentials
    from bleak.backends.device import BLEDevice

    ble_device = BLEDevice(name="SGS01B-JR", address="11:22:33", details="", rssi=-50)
    device = TuyaBLEDevice(Mock(), ble_device)
    device._device_info = TuyaBLEDeviceCredentials(
        uuid="uuid123",
        local_key="0000000000000000",
        device_id="bf2c23dntrqxugvw",
        category="zwjcy",
        product_id="gpkyrocn",
        device_name="SGS01B-JR",
        product_model="SGS01B-JR",
        product_name="SGS01B-JR",
        functions=[],
        status_range=[],
    )
    await device.initialize()

    mappings = get_mapping_by_device(device)
    assert len(mappings) == 1
    assert mappings[0].dp_id == 9

    coordinator = TuyaBLECoordinator(hass, device)
    product_info = TuyaBLEProductInfo("Soil moisture sensor")

    entity = TuyaBLESelect(hass, coordinator, device, product_info, mappings[0])
    entity.async_write_ha_state = Mock()

    # Update state: DP 9 = 0 -> UnitOfTemperature.CELSIUS
    from homeassistant.const import UnitOfTemperature
    device.datapoints._update_from_device(9, 0, 0, TuyaBLEDataPointType.DT_ENUM, 0)
    entity._handle_coordinator_update()
    assert entity.current_option == UnitOfTemperature.CELSIUS
