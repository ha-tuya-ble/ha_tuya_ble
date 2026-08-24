"""Tests for unloading an entry while a connection attempt is in progress."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from bleak.backends.device import BLEDevice
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tuya_ble import async_unload_entry
from custom_components.tuya_ble.cloud import HASSTuyaBLEDeviceManager
from custom_components.tuya_ble.const import DOMAIN
from custom_components.tuya_ble.tuya_ble import TuyaBLEDevice

ADDRESS = "11:22:33:44:55:66"

CONFIG = {
    "1234": {
        "address": ADDRESS,
        "device_id": "767823809c9c1f458745",
        "protocol_version": "3.3",
        "local_key": "wV[NcWGUSFF`dSgO",
        "friendly_name": "Local 3G",
    }
}


def _entry_with_device(hass: HomeAssistant, device) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"devices": CONFIG, "address": ADDRESS},
        title="Mock TuyaBLE",
    )
    entry.add_to_hass(hass)
    data = Mock()
    data.device = device
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = data
    return entry


async def _make_device(hass: HomeAssistant) -> TuyaBLEDevice:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"devices": CONFIG, "address": ADDRESS},
        title="Mock TuyaBLE",
    )
    entry.add_to_hass(hass)
    ble_device = BLEDevice(name="bob", address=ADDRESS, details="", rssi=-50)
    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())
    device = TuyaBLEDevice(manager, ble_device)
    await device.initialize()
    return device


async def test_disconnect_waits_for_the_connection_lock(hass: HomeAssistant) -> None:
    """This is what makes unloading hang.

    _execute_disconnect() takes self._connect_lock, and _ensure_connected() holds
    that lock for its whole retry loop, so a disconnect requested during a
    connection attempt does not complete until that loop is done.
    """
    device = await _make_device(hass)

    async with device._connect_lock:
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(device.stop(), 0.05)


async def test_unload_gives_up_on_a_stuck_disconnect(hass: HomeAssistant) -> None:
    """A disconnect that never returns must not keep the entry loaded forever."""
    device = Mock()
    never_returns = asyncio.Event()
    device.stop = AsyncMock(side_effect=never_returns.wait)
    entry = _entry_with_device(hass, device)

    with (
        patch.object(
            hass.config_entries, "async_unload_platforms", AsyncMock(return_value=True)
        ),
        patch("custom_components.tuya_ble.DISCONNECT_TIMEOUT", 0.05),
    ):
        assert await async_unload_entry(hass, entry) is True

    device.stop.assert_awaited_once()
    assert entry.entry_id not in hass.data[DOMAIN]
    never_returns.set()


async def test_unload_awaits_a_clean_disconnect(hass: HomeAssistant) -> None:
    """The normal path is unchanged: the disconnect is awaited, then we unload."""
    device = Mock()
    device.stop = AsyncMock()
    entry = _entry_with_device(hass, device)

    with patch.object(
        hass.config_entries, "async_unload_platforms", AsyncMock(return_value=True)
    ):
        assert await async_unload_entry(hass, entry) is True

    device.stop.assert_awaited_once()
    assert entry.entry_id not in hass.data[DOMAIN]


async def test_failed_platform_unload_leaves_the_device_alone(
    hass: HomeAssistant,
) -> None:
    """If the platforms refuse to unload, nothing is torn down."""
    device = Mock()
    device.stop = AsyncMock()
    entry = _entry_with_device(hass, device)

    with patch.object(
        hass.config_entries, "async_unload_platforms", AsyncMock(return_value=False)
    ):
        assert await async_unload_entry(hass, entry) is False

    device.stop.assert_not_awaited()
    assert entry.entry_id in hass.data[DOMAIN]
