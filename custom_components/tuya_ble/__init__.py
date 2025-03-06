"""The Tuya BLE integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform, CONF_ADDRESS

from .const import DOMAIN
from .cloud import HASSTuyaBLEDeviceManager
from .devices import TuyaBLEData
from .tuya_ble import TuyaBLEDevice
from .tuya_ble.tuya_ble import DummyDataPoints

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
    
    # Create a dummy device to avoid None errors during setup
    # This will be replaced with the real device later if/when it connects
    dummy_device = TuyaBLEDevice(None, None) 
    dummy_device.address = entry.data.get(CONF_ADDRESS, "unknown")
    dummy_device.category = ""
    dummy_device.product_id = ""
    dummy_device.name = "Initializing..."
    dummy_device.hardware_version = ""
    dummy_device.device_version = ""
    dummy_device.protocol_version = ""
    dummy_device.product_model = "Unknown"
    
    # Create a dummy datapoints property to avoid NoneType errors
    dummy_device._datapoints = DummyDataPoints()
    
    # Store the entry data with manager for proper handling
    hass.data[DOMAIN][entry.entry_id] = TuyaBLEData(
        title=entry.title,
        device=dummy_device,
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
