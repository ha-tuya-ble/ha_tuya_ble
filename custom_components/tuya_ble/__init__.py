"""The Tuya BLE integration."""

from __future__ import annotations

import asyncio
import logging

from bleak_retry_connector import BLEAK_RETRY_EXCEPTIONS as BLEAK_EXCEPTIONS, get_device

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth.match import ADDRESS, BluetoothCallbackMatcher
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_ADDRESS,
    CONF_DEVICE_ID,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady

from .tuya_ble import TuyaBLEDevice

from .cloud import HASSTuyaBLEDeviceManager
from .const import (
    CONF_CATEGORY,
    CONF_BLE_UNLOCK_CHECK,
    CONF_LOCAL_KEY,
    CONF_PRODUCT_ID,
    CONF_SEC_KEY,
    CONF_UUID,
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

CREDENTIAL_OPTION_KEYS = (
    CONF_UUID,
    CONF_LOCAL_KEY,
    CONF_SEC_KEY,
    CONF_BLE_UNLOCK_CHECK,
    CONF_DEVICE_ID,
    CONF_PRODUCT_ID,
    CONF_CATEGORY,
)

# How long unloading waits for a disconnect before giving up on it.
DISCONNECT_TIMEOUT = 15

# Watchers registered while a device could not be found, by entry id. These
# cannot be tracked with `entry.async_on_unload()`: setting up an entry that
# raises ConfigEntryNotReady is not a successful setup, so Home Assistant runs
# its on-unload callbacks straight away and the watcher would be cancelled
# before it ever saw an advertisement.
_missing_device_watchers: dict[str, CALLBACK_TYPE] = {}


@callback
def _async_stop_watching(entry: ConfigEntry) -> None:
    """Cancel the watcher for an entry, if one is registered."""
    if unregister := _missing_device_watchers.pop(entry.entry_id, None):
        unregister()


@callback
def _async_watch_for_device(
    hass: HomeAssistant, entry: ConfigEntry, address: str
) -> None:
    """Reload the entry once a device we could not find advertises again.

    A device that advertises rarely can stay unavailable indefinitely after it
    briefly goes out of range, because nothing reliably retries once it is back:

    - The setup retry backs off to one attempt every 10 minutes, while a remote
      scanner only keeps an advertisement for a few minutes, so a retry usually
      lands in a gap and finds nothing even for a device that is advertising.
    - Home Assistant reloads an entry in the retry state when a bluetooth
      discovery flow fires for its address, but the integration matcher
      remembers an address once it has matched, so that rescue only happens on
      the first matching advertisement after a restart.

    Watching the address directly closes the gap: the entry is reloaded as soon
    as the device is heard from. Registering in a non-passive mode also asks
    scanners that support it to actively scan for this address while the device
    is missing, which is otherwise only requested once the entry is set up.
    """
    if entry.entry_id in _missing_device_watchers:
        return

    @callback
    def _async_device_found(
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        """Handle an advertisement from a device that was missing."""
        _LOGGER.debug(
            "%s: Device found again (RSSI %s), reloading entry",
            address,
            service_info.rssi,
        )
        _async_stop_watching(entry)
        hass.config_entries.async_schedule_reload(entry.entry_id)

    _missing_device_watchers[entry.entry_id] = bluetooth.async_register_callback(
        hass,
        _async_device_found,
        BluetoothCallbackMatcher({ADDRESS: address}),
        bluetooth.BluetoothScanningMode.ACTIVE,
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tuya BLE from a config entry."""

    address: str = entry.data[CONF_ADDRESS]
    ble_device = bluetooth.async_ble_device_from_address(
        hass, address.upper(), True
    ) or await get_device(address)
    if not ble_device:
        _async_watch_for_device(hass, entry, address.upper())
        raise ConfigEntryNotReady(
            f"Could not find Tuya BLE device with address {address}"
        )

    _async_stop_watching(entry)
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
        or entry.options.get(CONF_IDLE_DISCONNECT_DELAY, DEFAULT_IDLE_DISCONNECT_DELAY)
        != data.device.idle_disconnect_delay
        or any(
            entry.options.get(key) != data.manager.data.get(key)
            for key in CREDENTIAL_OPTION_KEYS
        )
    ):
        await hass.config_entries.async_reload(entry.entry_id)
        return
    if entry.title != data.title:
        await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _async_stop_watching(entry)
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
