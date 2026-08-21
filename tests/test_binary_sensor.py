"""Test for tuya_ble."""

from . import *
from custom_components.tuya_ble.binary_sensor import (
    TuyaBLEBinarySensor,
    DOMAIN as PLATFORM_DOMAIN,
)

STATE_ON = "activated"
CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "entity_category": "None",
                "friendly_name": f"{PLATFORM_DOMAIN} 1",
                "icon": "",
                "id": "1",
                "state_on": STATE_ON,
                "platform": PLATFORM_DOMAIN,
                "restore_on_reconnect": False,
                "address": "12:23:44"
            }
        ],
    }
}

DPS_STATUS = {"1": "activated", "2": False}


async def test_binary_sensor(hass: HomeAssistant) -> None:
    coordinator = await init(hass, CONFIG, PLATFORM_DOMAIN, TuyaBLEBinarySensor)
    entities: list[TuyaBLEBinarySensor] = get_entites(coordinator)

    assert len(entities) > 0
    entity_1, *_ = entities
    assert type(entity_1) is TuyaBLEBinarySensor

    assert entity_1.state == "off"

    coordinator.status_updated(DPS_STATUS)

    assert entity_1.state == "on"
    assert coordinator._device.datapoints[1].value == STATE_ON


async def test_machine_error_bitmap(hass: HomeAssistant) -> None:
    """Test that the machine error bitmap only reports a problem when a bit is set."""
    from unittest.mock import Mock
    from homeassistant.components.binary_sensor import BinarySensorEntityDescription
    from custom_components.tuya_ble.binary_sensor import (
        TuyaBLEBinarySensorMapping,
        machine_error_getter,
    )
    from custom_components.tuya_ble.tuya_ble import TuyaBLEDataPointType

    coordinator = await init(hass, CONFIG, PLATFORM_DOMAIN, TuyaBLEBinarySensor)
    device = coordinator._device

    mapping = TuyaBLEBinarySensorMapping(
        dp_id=102,
        description=BinarySensorEntityDescription(key="machine_problem"),
        getter=machine_error_getter,
    )
    entity = TuyaBLEBinarySensor(
        hass, coordinator, device, TuyaBLEProductInfo("Robot Mower"), mapping
    )
    entity.async_write_ha_state = Mock()

    # An all zero bitmap is truthy as raw bytes, but reports no problem
    device.datapoints._update_from_device(
        102, 0, 0, TuyaBLEDataPointType.DT_BITMAP, b"\x00\x00\x00\x00"
    )
    entity._handle_coordinator_update()
    assert entity.is_on is False

    # Any set bit reports a problem
    device.datapoints._update_from_device(
        102, 0, 0, TuyaBLEDataPointType.DT_BITMAP, b"\x00\x00\x00\x08"
    )
    entity._handle_coordinator_update()
    assert entity.is_on is True
