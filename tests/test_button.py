"""Test for tuya_ble button."""

from unittest.mock import Mock, AsyncMock
from homeassistant.core import HomeAssistant
from homeassistant.components.button import ButtonEntityDescription
from custom_components.tuya_ble.button import TuyaBLEButton, TuyaBLEButtonMapping
from custom_components.tuya_ble.tuya_ble import TuyaBLEDataPointType

from . import *

STATE_ON = "activated"
CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "entity_category": "None",
                "friendly_name": "button 1",
                "icon": "",
                "id": "71",
                "platform": "button",
                "restore_on_reconnect": False,
                "address": "12:23:44",
            }
        ],
    }
}


async def test_button(hass: HomeAssistant) -> None:
    # Set up our own custom init for button to avoid mapping issues in __init__.py's init
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
    product_info = TuyaBLEProductInfo("Fake Product", lock=1)

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

    mapping = TuyaBLEButtonMapping(
        dp_id=71,
        description=ButtonEntityDescription(
            key="bluetooth_unlock",
            name="Unlock",
        ),
        force_add=True,
    )
    entity = TuyaBLEButton(hass, coordinator, device, product_info, mapping)
    entity.async_write_ha_state = Mock()

    assert entity.available is False

    coordinator._async_handle_connect()
    assert entity.available is True

    # Call press
    entity.press()
    await hass.async_block_till_done()

    # Verify _send_datapoints was called
    device._send_datapoints.assert_called_once_with([71])

    # DP 71 was created as DT_BOOL and set to True because product_info has lock=1
    dp = device.datapoints[71]
    assert dp is not None
    assert dp.value is True


async def test_oyqux5vv_raw_unlock(hass: HomeAssistant) -> None:
    """Test raw bluetooth unlock button for LA-01 (oyqux5vv)."""
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
    # Explicitly set product_id to oyqux5vv in device_info so button platform uses it
    from custom_components.tuya_ble.tuya_ble.manager import TuyaBLEDeviceCredentials

    device._device_info = TuyaBLEDeviceCredentials(
        uuid="uuid123",
        local_key="wV[NcWGUSFF`dSgO",
        device_id="767823809c9c1f458745",
        category="jtmspro",
        product_id="oyqux5vv",
        device_name="LA-01",
        product_model="LA-01",
        product_name="LA-01",
        functions=[],
        status_range=[],
    )
    product_info = TuyaBLEProductInfo("LA-01 Smart lock", lock=1)

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

    # Map the button mapping for oyqux5vv
    mapping = TuyaBLEButtonMapping(
        dp_id=71,
        description=ButtonEntityDescription(
            key="bluetooth_unlock",
            name="Unlock",
        ),
        dp_type=TuyaBLEDataPointType.DT_RAW,
        force_add=True,
    )
    entity = TuyaBLEButton(hass, coordinator, device, product_info, mapping)
    entity.async_write_ha_state = Mock()

    coordinator._async_handle_connect()
    assert entity.available is True

    # Press the button
    entity.press()
    await hass.async_block_till_done()

    # Verify _send_datapoints was called with DP 71
    device._send_datapoints.assert_called_once_with([71])

    # DP 71 was created as DT_RAW and should contain the validated bytes payload
    dp = device.datapoints[71]
    assert dp is not None
    assert dp.type == TuyaBLEDataPointType.DT_RAW
    assert dp.value == bytes.fromhex("0001ffff36383538313536320169ab34cd0000")
