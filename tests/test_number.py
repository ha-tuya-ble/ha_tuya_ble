"""Test for tuya_ble number."""

from unittest.mock import Mock, AsyncMock
from homeassistant.core import HomeAssistant
from homeassistant.components.number import NumberEntityDescription
from custom_components.tuya_ble.number import TuyaBLENumber, TuyaBLENumberMapping
from custom_components.tuya_ble.tuya_ble import TuyaBLEDataPointType

from . import *

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "entity_category": "None",
                "friendly_name": "Number 1",
                "icon": "",
                "id": "11",
                "platform": "number",
                "restore_on_reconnect": False,
                "address": "12:23:44"
            }
        ],
    }
}


async def test_number(hass: HomeAssistant) -> None:
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
    product_info = TuyaBLEProductInfo("Fake Number Product")

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

    # Map our number entity
    mapping = TuyaBLENumberMapping(
        dp_id=11,
        description=NumberEntityDescription(
            key="countdown_duration",
            native_min_value=1.0,
            native_max_value=100.0,
        ),
        coefficient=10.0,
        force_add=True,
    )

    entity = TuyaBLENumber(
        hass, coordinator, device, product_info, mapping
    )
    entity.async_write_ha_state = Mock()

    # Initial state
    assert entity.available is False
    coordinator._async_handle_connect()
    assert entity.available is True
    assert entity.native_value == 1.0

    # Update coordinator state: 150 -> 15.0 (coefficient=10.0)
    device.datapoints._update_from_device(11, 0, 0, TuyaBLEDataPointType.DT_VALUE, 150)
    entity._handle_coordinator_update()
    assert entity.native_value == 15.0

    # Call set_native_value
    entity.set_native_value(25.0)
    await hass.async_block_till_done()
    device._send_datapoints.assert_called_once_with([11])
    assert device.datapoints[11].value == 250
    assert entity.native_value == 25.0
