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


async def test_button():
    device = await init(CONFIG, PLATFORM_DOMAIN, TuyaBLEBinarySensor)
    entities: list[TuyaBLEBinarySensor] = get_entites(device)

    assert len(entities) > 0
    entity_1, *_ = entities
    assert type(entity_1) is TuyaBLEBinarySensor

    assert entity_1.state == "off"

    device.status_updated(DPS_STATUS)

    assert entity_1.state == "on"
    assert entity_1.dp_value("1") == STATE_ON