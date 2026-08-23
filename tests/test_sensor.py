"""Test for tuya_ble sensor."""

from unittest.mock import Mock, AsyncMock
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorEntityDescription
from custom_components.tuya_ble.sensor import TuyaBLESensor, TuyaBLESensorMapping, rssi_mapping
from custom_components.tuya_ble.tuya_ble import TuyaBLEDataPointType

from . import *

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "entity_category": "None",
                "friendly_name": "Sensor 1",
                "icon": "",
                "id": "2",
                "platform": "sensor",
                "restore_on_reconnect": False,
                "address": "12:23:44"
            }
        ],
    }
}


async def test_sensor(hass: HomeAssistant) -> None:
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
    product_info = TuyaBLEProductInfo("Fake Sensor Product")

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

    # Map our sensor entity
    mapping = TuyaBLESensorMapping(
        dp_id=2,
        description=SensorEntityDescription(
            key="carbon_dioxide",
        ),
        force_add=True,
    )

    entity = TuyaBLESensor(
        hass, coordinator, device, product_info, mapping
    )
    entity.async_write_ha_state = Mock()

    # Initial state
    assert entity.available is False
    coordinator._async_handle_connect()
    assert entity.available is True
    assert entity.native_value is None

    # Update coordinator state: 600 -> 600
    device.datapoints._update_from_device(2, 0, 0, TuyaBLEDataPointType.DT_VALUE, 600)
    entity._handle_coordinator_update()
    assert entity.native_value == 600


async def test_sensor_rssi(hass: HomeAssistant) -> None:
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
        title="Mock TuyaBLE RSSI",
    )
    entry.add_to_hass(hass)

    ble_device = BLEDevice(name="bob", address="11:22:33", details="", rssi=-50)
    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())
    device = TuyaBLEDevice(manager, ble_device)
    await device.initialize()
    product_info = TuyaBLEProductInfo("Fake Sensor Product")

    # Mock rssi via advertisement data
    device._advertisement_data = Mock()
    device._advertisement_data.rssi = -65

    hass.data.setdefault(DOMAIN, {})
    coordinator = TuyaBLECoordinator(hass, device)

    # Map rssi sensor entity
    entity = TuyaBLESensor(
        hass, coordinator, device, product_info, rssi_mapping
    )
    entity.async_write_ha_state = Mock()

    # Verify rssi value gets pulled
    coordinator._async_handle_connect()
    entity._handle_coordinator_update()
    assert entity.native_value == -65
