"""Test for tuya_ble cover."""

from unittest.mock import Mock, AsyncMock
from homeassistant.core import HomeAssistant
from homeassistant.components.cover import CoverEntityDescription
from custom_components.tuya_ble.cover import TuyaBLECover, TuyaBLECoverMapping
from custom_components.tuya_ble.tuya_ble import TuyaBLEDataPointType

from . import *

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "entity_category": "None",
                "friendly_name": "Cover 1",
                "icon": "",
                "id": "cover",
                "platform": "cover",
                "restore_on_reconnect": False,
                "address": "12:23:44"
            }
        ],
    }
}


async def test_cover(hass: HomeAssistant) -> None:
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
    product_info = TuyaBLEProductInfo("Fake Cover Product")

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

    # Map our cover entity
    mapping = TuyaBLECoverMapping(
        description=CoverEntityDescription(
            key="ble_blind_controller",
        ),
        cover_state_dp_id=1,
        cover_position_set_dp=2,
        cover_position_dp_id=3,
    )

    entity = TuyaBLECover(
        hass, coordinator, device, product_info, mapping
    )
    entity.async_write_ha_state = Mock()

    # Initial state
    assert entity.available is False
    coordinator._async_handle_connect()
    assert entity.available is True
    assert entity.current_cover_position == 0

    # Update coordinator state: position DP 3 to 20 -> current_cover_position = 80
    device.datapoints._update_from_device(3, 0, 0, TuyaBLEDataPointType.DT_VALUE, 20)
    entity._handle_coordinator_update()
    assert entity.current_cover_position == 80

    # Call async_open_cover (sets state DP 1 to 0)
    await entity.async_open_cover()
    await hass.async_block_till_done()
    device._send_datapoints.assert_any_call([1])
    assert device.datapoints[1].value == 0

    # Call async_close_cover (sets state DP 1 to 2)
    await entity.async_close_cover()
    await hass.async_block_till_done()
    device._send_datapoints.assert_any_call([1])
    assert device.datapoints[1].value == 2

    # Call async_stop_cover (sets state DP 1 to 1)
    await entity.async_stop_cover()
    await hass.async_block_till_done()
    device._send_datapoints.assert_any_call([1])
    assert device.datapoints[1].value == 1

    # Call async_set_cover_position (sets position DP 2 to 100 - 70 = 30)
    await entity.async_set_cover_position(position=70)
    await hass.async_block_till_done()
    device._send_datapoints.assert_any_call([2])
    assert device.datapoints[2].value == 30
