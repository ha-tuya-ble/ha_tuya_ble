"""Test for tuya_ble switch."""

from unittest.mock import Mock, AsyncMock
from homeassistant.core import HomeAssistant
from homeassistant.components.switch import SwitchEntityDescription
from custom_components.tuya_ble.switch import TuyaBLESwitch, TuyaBLESwitchMapping
from custom_components.tuya_ble.tuya_ble import TuyaBLEDataPointType

from . import *

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "entity_category": "None",
                "friendly_name": "Switch 1",
                "icon": "",
                "id": "1",
                "platform": "switch",
                "restore_on_reconnect": False,
                "address": "12:23:44"
            }
        ],
    }
}


async def test_switch(hass: HomeAssistant) -> None:
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
    product_info = TuyaBLEProductInfo("Fake Switch Product")

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

    # Map our switch entity
    mapping = TuyaBLESwitchMapping(
        dp_id=1,
        description=SwitchEntityDescription(
            key="water_valve",
        ),
        force_add=True,
    )

    entity = TuyaBLESwitch(
        hass, coordinator, device, product_info, mapping
    )
    entity.async_write_ha_state = Mock()

    # Initial state
    assert entity.available is False
    coordinator._async_handle_connect()
    assert entity.available is True
    assert entity.is_on is False

    # Update coordinator state
    device.datapoints._update_from_device(1, 0, 0, TuyaBLEDataPointType.DT_BOOL, True)
    entity._handle_coordinator_update()
    assert entity.is_on is True

    # Call turn_off
    entity.turn_off()
    await hass.async_block_till_done()
    device._send_datapoints.assert_any_call([1])
    assert entity.is_on is False

    # Call turn_on
    entity.turn_on()
    await hass.async_block_till_done()
    device._send_datapoints.assert_any_call([1])
    assert entity.is_on is True


async def test_switch_bitmap(hass: HomeAssistant) -> None:
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
        title="Mock TuyaBLE 2",
    )
    entry.add_to_hass(hass)

    ble_device = BLEDevice(name="bob", address="11:22:33", details="", rssi=-50)
    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())
    device = TuyaBLEDevice(manager, ble_device)
    await device.initialize()
    product_info = TuyaBLEProductInfo("Fake Switch Product")

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

    # Map a switch with bitmap mask (e.g. low battery alarm mapping, mask b"\x02")
    mapping = TuyaBLESwitchMapping(
        dp_id=11,
        description=SwitchEntityDescription(
            key="low_battery_alarm",
        ),
        bitmap_mask=b"\x02",
        force_add=True,
    )

    entity = TuyaBLESwitch(
        hass, coordinator, device, product_info, mapping
    )
    entity.async_write_ha_state = Mock()

    # Initial state
    coordinator._async_handle_connect()
    assert entity.is_on is False

    # Update coordinator state with bitmap b"\x02" -> should be on
    device.datapoints._update_from_device(11, 0, 0, TuyaBLEDataPointType.DT_BITMAP, b"\x02")
    entity._handle_coordinator_update()
    assert entity.is_on is True

    # Update coordinator state with bitmap b"\x01" -> should be off (doesn't match b"\x02")
    device.datapoints._update_from_device(11, 0, 0, TuyaBLEDataPointType.DT_BITMAP, b"\x01")
    entity._handle_coordinator_update()
    assert entity.is_on is False

    # Call turn_on (should bitwise OR with mask b"\x02")
    entity.turn_on()
    await hass.async_block_till_done()
    device._send_datapoints.assert_any_call([11])
    assert device.datapoints[11].value == b"\x03"  # b"\x01" | b"\x02" = b"\x03"

    # Call turn_off (should bitwise AND with ~mask b"\x02")
    entity.turn_off()
    await hass.async_block_till_done()
    assert device.datapoints[11].value == b"\x01"  # b"\x03" & ~b"\x02" = b"\x01"
