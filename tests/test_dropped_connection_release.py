"""Tests for releasing a connection that dropped unexpectedly."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tuya_ble.cloud import HASSTuyaBLEDeviceManager
from custom_components.tuya_ble.const import DOMAIN
from custom_components.tuya_ble.tuya_ble import TuyaBLEDevice

CONFIG = {
    "1234": {
        "address": "11:22:33:44:55:66",
        "device_id": "767823809c9c1f458745",
        "protocol_version": "3.3",
        "local_key": "wV[NcWGUSFF`dSgO",
        "friendly_name": "Local 3G",
    }
}


async def _make_device(hass: HomeAssistant) -> TuyaBLEDevice:
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
    return device


async def test_unexpected_disconnect_releases_the_dropped_client(
    hass: HomeAssistant,
) -> None:
    """A connection that drops on us has to be released, not just forgotten.

    bleak removes its per-device notification watcher when the client is
    disconnected. Forgetting the client leaves the watcher registered, the next
    connection adds another, and every notification is then delivered once per
    watcher.
    """
    device = await _make_device(hass)
    dropped = Mock()
    dropped.disconnect = AsyncMock()
    device._client = dropped
    device._is_paired = True
    device._expected_disconnect = False

    with patch.object(device, "_reconnect", AsyncMock()):
        device._disconnected(dropped)
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    dropped.disconnect.assert_awaited_once()


async def test_dropped_client_is_released_before_reconnecting(
    hass: HomeAssistant,
) -> None:
    """Order matters: the old watcher must go before a new one is registered."""
    device = await _make_device(hass)
    dropped = Mock()
    calls: list[str] = []

    async def _disconnect() -> None:
        calls.append("release")

    async def _reconnect() -> None:
        calls.append("reconnect")

    dropped.disconnect = _disconnect

    with patch.object(device, "_reconnect", _reconnect):
        await device._release_and_reconnect(dropped)

    assert calls == ["release", "reconnect"]


async def test_release_survives_a_failing_disconnect(hass: HomeAssistant) -> None:
    """The link is already gone, so a failing disconnect must not stop us."""
    device = await _make_device(hass)
    dropped = Mock()
    dropped.disconnect = AsyncMock(side_effect=BleakError("not connected"))

    await device._release_client(dropped)

    dropped.disconnect.assert_awaited_once()


async def test_planned_disconnect_does_not_release_again(
    hass: HomeAssistant,
) -> None:
    """_execute_disconnect() already cleans up; do not double up on its path."""
    device = await _make_device(hass)
    client = Mock()
    client.disconnect = AsyncMock()
    device._client = client
    device._expected_disconnect = True

    device._disconnected(client)
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    client.disconnect.assert_not_awaited()
