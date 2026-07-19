"""Init tuya_ble tests"""

from typing import Any
from unittest.mock import Mock

from bleak.backends.device import BLEDevice
from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.core import HomeAssistant

from habluetooth.central_manager import CentralBluetoothManager

from custom_components.tuya_ble.const import DOMAIN
from custom_components.tuya_ble.devices import (
    TuyaBLECoordinator,
    TuyaBLEData,
    TuyaBLEDevice,
    TuyaBLEProductInfo,
)
from custom_components.tuya_ble.cloud import HASSTuyaBLEDeviceManager
from custom_components.tuya_ble.binary_sensor import TuyaBLEBinarySensorMapping
from custom_components.tuya_ble.tuya_ble import TuyaBLEDataPointType

DEVICE_NAME = "1234"
DEVICE_ADDRESS = "00:11:22:33:44:55"
DEVICE_CONFIG = {
    "address": DEVICE_ADDRESS,
    "device_id": "767823809c9c1f458745",
    "protocol_version": "3.3",
    "local_key": "wV[NcWGUSFF`dSgO",
    "friendly_name": "Local 3G",
}

mock_ble_device = BLEDevice(
    name="MockTuyaDevice", address=DEVICE_ADDRESS, rssi=-70, details=""
)

CentralBluetoothManager.manager = Mock()
CentralBluetoothManager.manager.async_ble_device_from_address.side_effect = (
    lambda address, connectable: (
        mock_ble_device if address == DEVICE_ADDRESS else None
    )
)


def _dp_type_for_value(value: Any) -> TuyaBLEDataPointType:
    if isinstance(value, bool):
        return TuyaBLEDataPointType.DT_BOOL
    if isinstance(value, int):
        return TuyaBLEDataPointType.DT_VALUE
    if isinstance(value, bytes):
        return TuyaBLEDataPointType.DT_STRING
    return TuyaBLEDataPointType.DT_STRING


async def init(
    hass: HomeAssistant,
    config: dict[str, dict[str, Any]],
    entity_domain: str,
    entity_class,
):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "devices": config,
            "address": DEVICE_ADDRESS,
        },
        title="Mock TuyaBLE",
    )
    entry.add_to_hass(hass)

    ble_device = BLEDevice(name="bob", address="11:22:33", details="", rssi=-50)
    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())
    device = TuyaBLEDevice(manager, ble_device)
    await device.initialize()
    product_info = TuyaBLEProductInfo("Fake Product")

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

    entities = []
    entity_dp_ids = []
    for device_name, device_config in config.items():
        for entity_config in device_config.get("entities", []):
            if entity_config.get("platform") == entity_domain:
                dp_id = int(entity_config["id"])
                entity_dp_ids.append(dp_id)
                mapping = TuyaBLEBinarySensorMapping(
                    dp_id=dp_id,
                    description=BinarySensorEntityDescription(
                        key=entity_config["id"],
                        name=entity_config.get("friendly_name", ""),
                    ),
                    force_add=True,
                )
                entity = entity_class(
                    hass, coordinator, device, product_info, mapping
                )
                entity.async_write_ha_state = Mock()
                entities.append(entity)

    coordinator._entities = entities

    for dp_id in entity_dp_ids:
        device.datapoints._update_from_device(
            dp_id, 0, 0, TuyaBLEDataPointType.DT_STRING, ""
        )

    for entity in entities:
        entity._handle_coordinator_update()

    def status_updates(status: dict[str, Any]):
        for dp_id_str, value in status.items():
            dp_id = int(dp_id_str)
            device.datapoints._update_from_device(
                dp_id, 0, 0, _dp_type_for_value(value), value
            )
        for entity in entities:
            entity._handle_coordinator_update()

    coordinator.status_updated = status_updates

    return coordinator


def create_entry(config: dict[str, dict[str, Any]]):
    return {
        "data": {
            "devices": config,
            "address": DEVICE_ADDRESS,
        },
        "domain": DOMAIN,
        "title": "Mock TuyaBLE",
        "unique_id": None,
        "version": 1,
    }


def get_entites(device: TuyaBLECoordinator):
    return getattr(device, "_entities", [])
