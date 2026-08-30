"""Tests for recovering an entry whose device was not found during setup."""

from unittest.mock import AsyncMock, Mock, patch

from homeassistant.components.bluetooth import BluetoothChange
from homeassistant.components.bluetooth.match import ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from pytest_homeassistant_custom_component.common import MockConfigEntry
import pytest

from custom_components.tuya_ble import (
    _missing_device_watchers,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.tuya_ble.const import DOMAIN

ADDR = "11:22:33:44:55:66"


@pytest.fixture(autouse=True)
def _no_leaked_watchers():
    """Each test starts and ends with no watchers registered."""
    _missing_device_watchers.clear()
    yield
    _missing_device_watchers.clear()


def _entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data={"address": ADDR}, title="Mock TuyaBLE")
    entry.add_to_hass(hass)
    return entry


async def _setup_with_no_device(hass: HomeAssistant, entry: MockConfigEntry) -> Mock:
    """Run setup for a device that cannot be found, returning the register mock."""
    register = Mock(return_value=Mock())
    with (
        patch(
            "custom_components.tuya_ble.bluetooth.async_ble_device_from_address",
            return_value=None,
        ),
        patch("custom_components.tuya_ble.get_device", AsyncMock(return_value=None)),
        patch("custom_components.tuya_ble.bluetooth.async_register_callback", register),
        pytest.raises(ConfigEntryNotReady),
    ):
        await async_setup_entry(hass, entry)
    return register


async def test_a_missing_device_is_watched_for(hass: HomeAssistant) -> None:
    """Setup that cannot find the device must leave a watcher behind.

    Without it nothing reliably notices the device coming back: the setup retry
    backs off past the lifetime of an advertisement, and the discovery-flow
    rescue only fires on the first match after a restart.
    """
    entry = _entry(hass)

    register = await _setup_with_no_device(hass, entry)

    assert entry.entry_id in _missing_device_watchers
    matcher = register.call_args.args[2]
    assert matcher[ADDRESS] == ADDR


async def test_the_watcher_reloads_the_entry(hass: HomeAssistant) -> None:
    """An advertisement from the missing device reloads the entry."""
    entry = _entry(hass)
    register = await _setup_with_no_device(hass, entry)
    on_advertisement = register.call_args.args[1]

    with patch.object(hass.config_entries, "async_schedule_reload") as reload:
        on_advertisement(Mock(rssi=-60), BluetoothChange.ADVERTISEMENT)

    reload.assert_called_once_with(entry.entry_id)
    assert entry.entry_id not in _missing_device_watchers


async def test_retries_do_not_stack_watchers(hass: HomeAssistant) -> None:
    """Setup runs again on every retry; each run must not add a watcher."""
    entry = _entry(hass)

    first = await _setup_with_no_device(hass, entry)
    second = await _setup_with_no_device(hass, entry)

    assert first.call_count == 1
    assert second.call_count == 0
    assert len(_missing_device_watchers) == 1


async def test_unloading_cancels_the_watcher(hass: HomeAssistant) -> None:
    """An entry being removed must not leave a registration behind."""
    entry = _entry(hass)
    register = await _setup_with_no_device(hass, entry)
    unregister = register.return_value

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = Mock(
        device=Mock(stop=AsyncMock())
    )
    with patch.object(
        hass.config_entries, "async_unload_platforms", AsyncMock(return_value=True)
    ):
        assert await async_unload_entry(hass, entry) is True

    unregister.assert_called_once()
    assert entry.entry_id not in _missing_device_watchers
