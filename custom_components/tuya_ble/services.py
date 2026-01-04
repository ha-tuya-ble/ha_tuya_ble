import logging


from functools import wraps
from homeassistant.core import HomeAssistant, ServiceCall
from .const import DOMAIN
from homeassistant.helpers import device_registry as dr


_LOGGER = logging.getLogger(__name__)

class TuyaBLEServiceRegistry:
    def __init__(self):
        # Format: { "service_name": { "product_id": method_handle } }
        self._services = {}

    def get_device_from_call(self, call: ServiceCall, hass: HomeAssistant):
        """Helper to extract the device manager from a service call."""
        device_id = call.data.get("device_id")
        dev_reg = dr.async_get(hass)
        device_entry = dev_reg.async_get(device_id)
        
        if not device_entry:
            return None

        for entry_id in device_entry.config_entries:
            if entry_id in hass.data[DOMAIN]:
                # Assuming your manager is stored here
                return hass.data[DOMAIN][entry_id].device
        return None

    def register_service(self, service_name, product_ids):
        """Decorator to register a method as a service for specific product IDs."""
        def decorator(func):
            if service_name not in self._services:
                self._services[service_name] = {}
            for pid in product_ids:
                self._services[service_name][pid] = func.__name__
            return func
        return decorator

    async def async_setup(self, hass: HomeAssistant):
        """Register all gathered services with Home Assistant."""
        for service_name in self._services:
            async def handle_service(call: ServiceCall, name=service_name):
                await self._async_dispatch_service(hass, call, name)
            
            hass.services.async_register(DOMAIN, service_name, handle_service)

    async def _async_dispatch_service(self, hass, call, service_name):
        """Find the right device and call its specific method."""
        device = self.get_device_from_call(call, hass)
        if not device:
            _LOGGER.error("Device not found for service call: %s", call)
            return

        target_method_name = self._services[service_name].get(device.product_id)
        if target_method_name:
            method = getattr(device.product_info, target_method_name)
            await method(call, device)

# Global instance
SERVICE_REGISTRY = TuyaBLEServiceRegistry()