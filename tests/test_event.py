"""Test for tuya_ble event."""

from unittest.mock import Mock, AsyncMock
from homeassistant.core import HomeAssistant
from homeassistant.components.event import EventEntityDescription, EventDeviceClass
from custom_components.tuya_ble.event import TuyaBLEEvent, TuyaBLEEventMapping
from custom_components.tuya_ble.tuya_ble import TuyaBLEDataPointType

from . import *

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "entity_category": "None",
                "friendly_name": "Button Event",
                "icon": "",
                "id": "1",
                "platform": "event",
                "restore_on_reconnect": False,
                "address": "12:23:44",
            }
        ],
    }
}


async def test_event(hass: HomeAssistant) -> None:
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
        title="Mock TuyaBLE Event",
    )
    entry.add_to_hass(hass)

    ble_device = BLEDevice(name="bob", address="11:22:33", details="", rssi=-50)
    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())
    device = TuyaBLEDevice(manager, ble_device)
    await device.initialize()
    product_info = TuyaBLEProductInfo("Fake Event Product")

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

    # Map our event entity
    mapping = TuyaBLEEventMapping(
        dp_id=1,
        description=EventEntityDescription(
            key="event",
            device_class=EventDeviceClass.BUTTON,
        ),
        event_types=["single_click", "double_click", "long_press"],
        force_add=True,
    )

    entity = TuyaBLEEvent(hass, coordinator, device, product_info, mapping)
    entity.async_write_ha_state = Mock()
    entity._trigger_event = Mock()
    coordinator.async_add_listener(entity._handle_coordinator_update)

    # Initial state
    assert entity.available is False
    coordinator._async_handle_connect()
    assert entity.available is True

    # 1. Update unrelated DP (DP 10) to coordinator
    device.datapoints._update_from_device(10, 0, 0, TuyaBLEDataPointType.DT_VALUE, 80)
    dp10 = device.datapoints[10]

    # Send update packet containing only DP 10
    coordinator._async_handle_update([dp10])

    # Verify that event trigger was NOT called
    entity._trigger_event.assert_not_called()

    # 2. Update DP 1 (value "single_click" as string) to coordinator
    device.datapoints._update_from_device(
        1, 0, 0, TuyaBLEDataPointType.DT_STRING, "single_click"
    )
    dp1 = device.datapoints[1]

    # Send update packet containing DP 1
    coordinator._async_handle_update([dp1])

    # Verify event trigger was called with "single_click"
    entity._trigger_event.assert_called_once_with("single_click")
    entity._trigger_event.reset_mock()

    # 3. Verify clearing of last_updates: If another DP (10) updates, DP 1 is not in updates, event should NOT re-trigger
    coordinator._async_handle_update([dp10])
    entity._trigger_event.assert_not_called()

    # 4. Update DP 1 (value 2 as integer/enum index -> "long_press") to coordinator
    device.datapoints._update_from_device(1, 0, 0, TuyaBLEDataPointType.DT_ENUM, 2)
    dp1_enum = device.datapoints[1]

    coordinator._async_handle_update([dp1_enum])
    entity._trigger_event.assert_called_once_with("long_press")
    entity._trigger_event.reset_mock()

    # 5. Connect/Disconnect should clear last_updates and should NOT trigger stale events
    coordinator.last_updates = [dp1_enum]  # Inject stale update manually
    coordinator._async_handle_connect()
    assert coordinator.last_updates is None
    entity._trigger_event.assert_not_called()

    coordinator.last_updates = [dp1_enum]  # Inject stale update manually
    coordinator._set_disconnected(None)
    assert coordinator.last_updates is None
    entity._trigger_event.assert_not_called()
