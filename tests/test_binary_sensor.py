"""Test for tuya_ble."""
import time
from unittest.mock import Mock

from custom_components.tuya_ble.tuya_ble import TuyaBLEDataPointType
from . import *
from custom_components.tuya_ble.binary_sensor import (
    TuyaBLEBinarySensor,
    DOMAIN as PLATFORM_DOMAIN,
)

STATE_ON = True
CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "entity_category": "None",
                "friendly_name": f"{PLATFORM_DOMAIN} 1",
                "icon": "",
                "id": "24",
                "state_on": STATE_ON,
                "platform": PLATFORM_DOMAIN,
                "restore_on_reconnect": False,
                "address": "12:23:44"
            }
        ],
    }
}

DPS_STATUS = {"24": True, "2": False}


@pytest.mark.asyncio
async def test_binary_sensor():
    coordinator, entities = await init(CONFIG, PLATFORM_DOMAIN, TuyaBLEBinarySensor)
    tuya_device = coordinator._device

    assert len(entities) > 0
    entity_1, *_ = entities
    assert type(entity_1) is TuyaBLEBinarySensor
    entity_1.async_write_ha_state = Mock()

    assert entity_1.is_on is False

    # Manually update the datapoint and call the handler
    tuya_device.datapoints._update_from_device(24, time.time(), 0, TuyaBLEDataPointType.DT_BOOL, True)
    entity_1._handle_coordinator_update()

    assert entity_1.is_on is True
