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

class DummyBLEDevice:
    """A simple class to emulate BLEDevice for dummy devices."""
    
    def __init__(self, address="unknown"):
        self.address = address
        self.name = "Initializing..."

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tuya BLE from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Initialize the manager
    manager = HASSTuyaBLEDeviceManager(hass, entry.options)
    
    # Create a dummy BLE device with the address from the entry data
    dummy_ble_device = DummyBLEDevice(entry.data.get(CONF_ADDRESS, "unknown"))
    
    # Create a dummy device to avoid None errors during setup
    # This will be replaced with the real device later if/when it connects
    dummy_device = TuyaBLEDevice(None, dummy_ble_device)
    
    # Now initialize other properties
    dummy_device.category = ""
    dummy_device.product_id = ""
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
