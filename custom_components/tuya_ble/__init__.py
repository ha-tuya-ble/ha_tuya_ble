"""The Tuya BLE integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

from .const import DOMAIN
from .cloud import HASSTuyaBLEDeviceManager
from .devices import TuyaBLEData

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.TEXT,
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tuya BLE from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Initialize the manager
    manager = HASSTuyaBLEDeviceManager(hass, entry.options)
    
    # Store the entry data with manager for proper handling
    hass.data[DOMAIN][entry.entry_id] = TuyaBLEData(
        title=entry.title,
        device=None,  # Will be initialized later
        product=None,  # Will be initialized later
        manager=manager,
        coordinator=None,  # Will be initialized later
    )
    
    # Forward the setup to the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Forward the unloading to the sensor platform
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Remove the config entry from the domain data
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
