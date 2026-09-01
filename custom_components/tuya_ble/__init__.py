"""The Tuya BLE integration."""

from __future__ import annotations

import asyncio
import logging

from bleak_retry_connector import BLEAK_RETRY_EXCEPTIONS as BLEAK_EXCEPTIONS, get_device

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth.match import ADDRESS, BluetoothCallbackMatcher
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady

from .tuya_ble import TuyaBLEDevice

from .cloud import HASSTuyaBLEDeviceManager
from .const import (
    CONF_IDLE_DISCONNECT_DELAY,
    CONF_KEEP_CONNECTION,
    DEFAULT_IDLE_DISCONNECT_DELAY,
    DEFAULT_KEEP_CONNECTION,
    DOMAIN,
)
from .devices import TuyaBLECoordinator, TuyaBLEData, get_device_product_info

PLATFORMS: list[Platform] = [
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.LAWN_MOWER,
    Platform.LOCK,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.LIGHT,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.TEXT,
    Platform.COVER,
    Platform.EVENT,
    Platform.VACUUM,
]

_LOGGER = logging.getLogger(__name__)

# How long unloading waits for a disconnect before giving up on it.
DISCONNECT_TIMEOUT = 15


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tuya BLE from a config entry."""

    address: str = entry.data[CONF_ADDRESS]
    ble_device = bluetooth.async_ble_device_from_address(
        hass, address.upper(), True
    ) or await get_device(address)
    if not ble_device:
        raise ConfigEntryNotReady(
            f"Could not find Tuya BLE device with address {address}"
        )

    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())
    device = TuyaBLEDevice(
        manager,
        ble_device,
        keep_connection=entry.options.get(
            CONF_KEEP_CONNECTION, DEFAULT_KEEP_CONNECTION
        ),
        idle_disconnect_delay=entry.options.get(
            CONF_IDLE_DISCONNECT_DELAY, DEFAULT_IDLE_DISCONNECT_DELAY
        ),
    )
    await device.initialize()
    product_info = get_device_product_info(device)

    coordinator = TuyaBLECoordinator(hass, device)

    async def _initial_update() -> None:
        """Perform the first update, retrying until the device answers.

        The first update used to be fired with `hass.add_job()` and never awaited.
        When the device is out of range while the entry is being set up,
        `_ensure_connected()` exhausts its attempts and raises `BleakNotFoundError`
        out of a task nobody watches ("Task exception was never retrieved"), so the
        device is never polled again and stays unavailable until Home Assistant is
        restarted. Retrying in an entry-scoped background task keeps the device
        recoverable without a restart; the task is cancelled when the entry unloads.
        """
        delay = 60
        while True:
            try:
                # Cap a single attempt: `_ensure_connected()` retries internally and
                # can occupy the task for a long time, which would delay the next
                # real attempt long after the device became reachable again.
                await asyncio.wait_for(device.update(), 240)
                return
            except BLEAK_EXCEPTIONS + (TimeoutError,) as ex:
                _LOGGER.debug(
                    "%s: Initial update failed (%s); retrying in %s s",
                    address,
                    type(ex).__name__,
                    delay,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, 300)

    entry.async_create_background_task(
        hass, _initial_update(), f"tuya_ble initial update {address}"
    )

    @callback
    def _async_update_ble(
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        """Update from a ble callback."""
        device.set_ble_device_and_advertisement_data(
            service_info.device, service_info.advertisement
        )

    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            _async_update_ble,
            BluetoothCallbackMatcher({ADDRESS: address}),
            bluetooth.BluetoothScanningMode.ACTIVE,
        )
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = TuyaBLEData(
        entry.title,
        device,
        product_info,
        manager,
        coordinator,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    async def _async_stop(event: Event) -> None:
        """Close the connection."""
        await device.stop()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_stop)
    )
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    data: TuyaBLEData = hass.data[DOMAIN][entry.entry_id]
    if (
        entry.options.get(CONF_KEEP_CONNECTION, DEFAULT_KEEP_CONNECTION)
        != data.device.keep_connection
    ):
        await hass.config_entries.async_reload(entry.entry_id)
        return
    if entry.title != data.title:
        await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        data: TuyaBLEData = hass.data[DOMAIN].pop(entry.entry_id)
        # stop() -> _execute_disconnect() waits for self._connect_lock, which
        # _ensure_connected() holds for the whole duration of its retry loop.
        # While that loop runs, unloading blocks and the entry is stuck in
        # ConfigEntryState.UNLOAD_IN_PROGRESS, so reloading the entry (and every
        # operation that reloads it, e.g. renaming it or changing its options)
        # never completes and only a Home Assistant restart clears it.
        # Give the disconnect a bounded amount of time; the abandoned connection
        # is dropped by the adapter/proxy anyway once the client is discarded.
        try:
            await asyncio.wait_for(data.device.stop(), DISCONNECT_TIMEOUT)
        except TimeoutError:
            _LOGGER.warning(
                "%s: Timed out waiting for the device to disconnect, unloading anyway",
                entry.data[CONF_ADDRESS],
            )

    return unload_ok
