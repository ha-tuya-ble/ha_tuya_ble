"""Test for tuya_ble bluetooth shutdown handling."""

import asyncio
from unittest.mock import Mock, AsyncMock, patch
import pytest
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from custom_components.tuya_ble.tuya_ble import TuyaBLEDevice
from custom_components.tuya_ble.cloud import HASSTuyaBLEDeviceManager
from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.core import HomeAssistant
from custom_components.tuya_ble.const import DOMAIN

CONFIG = {
    "1234": {
        "address": "11:22:33:44:55:66",
        "device_id": "767823809c9c1f458745",
        "protocol_version": "3.3",
        "local_key": "wV[NcWGUSFF`dSgO",
        "friendly_name": "Local 3G",
    }
}

async def test_ensure_connected_bluetooth_shutdown(hass: HomeAssistant) -> None:
    """Test that _ensure_connected terminates immediately on bluetooth shutdown error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "devices": CONFIG,
            "address": "11:22:33:44:55:66",
        },
        title="Mock TuyaBLE",
    )
    entry.add_to_hass(hass)

    ble_device = BLEDevice(name="bob", address="11:22:33:44:55:66", details="", rssi=-50)
    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())
    device = TuyaBLEDevice(manager, ble_device)
    await device.initialize()

    # We patch establish_connection to raise BleakError("Bluetooth is already shutdown")
    with patch(
        "custom_components.tuya_ble.tuya_ble.tuya_ble.establish_connection",
        side_effect=BleakError("Bluetooth is already shutdown"),
    ) as mock_establish:
        with pytest.raises(BleakError, match="Bluetooth is already shutdown"):
            await device._ensure_connected()

        # Assert establish_connection was only called once, not 100 times!
        assert mock_establish.call_count == 1


async def test_reconnect_bluetooth_shutdown(hass: HomeAssistant) -> None:
    """Test that _reconnect does not schedule another task on bluetooth shutdown."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "devices": CONFIG,
            "address": "11:22:33:44:55:66",
        },
        title="Mock TuyaBLE",
    )
    entry.add_to_hass(hass)

    ble_device = BLEDevice(name="bob", address="11:22:33:44:55:66", details="", rssi=-50)
    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())
    device = TuyaBLEDevice(manager, ble_device)
    await device.initialize()

    # Mock _ensure_connected to raise BleakError("Bluetooth is already shutdown")
    with patch.object(
        device, "_ensure_connected", side_effect=BleakError("Bluetooth is already shutdown")
    ):
        with patch("asyncio.create_task") as mock_create_task:
            await device._reconnect()
            # Assert create_task was never called to reschedule _reconnect
            mock_create_task.assert_not_called()


async def test_send_packets_locked_bluetooth_shutdown(hass: HomeAssistant) -> None:
    """Test that _send_packets_locked propagates bluetooth shutdown immediately without retrying/reconnecting."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "devices": CONFIG,
            "address": "11:22:33:44:55:66",
        },
        title="Mock TuyaBLE",
    )
    entry.add_to_hass(hass)

    ble_device = BLEDevice(name="bob", address="11:22:33:44:55:66", details="", rssi=-50)
    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())
    device = TuyaBLEDevice(manager, ble_device)
    await device.initialize()

    # Set some device client mock
    client = Mock()
    client.write_gatt_char = AsyncMock(side_effect=BleakError("Bluetooth is already shutdown"))
    device._client = client

    with patch("asyncio.create_task") as mock_create_task:
        with pytest.raises(BleakError, match="Bluetooth is already shutdown"):
            await device._send_packets_locked([b"\x00"])
        # Verify no create_task calls were made for reconnection or packet resend
        mock_create_task.assert_not_called()
