import logging


from functools import wraps
from homeassistant.core import HomeAssistant, ServiceCall
from .const import DOMAIN
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er



_LOGGER = logging.getLogger(__name__)

class TuyaBLEServiceRegistry:
    def __init__(self):
        # Format: { "service_name": { "product_id": method_handle } }
        self._services = {}

    def get_data_from_call(self, call: ServiceCall, hass: HomeAssistant):
        """Helper to extract the device manager from a service call."""

        # 1. Get the Entity ID from the 'target' or 'data'
        # This works if you pass 'entity_id: select.your_lock_user'
        target_entities = call.data.get("entity_id")
        
        if not target_entities:
            # Fallback to check the 'target' key (modern HA style)
            target_entities = call.context.to_dict().get("entity_id") 

        if isinstance(target_entities, list):
            target_entity = target_entities[0]
        else:
            target_entity = target_entities

        # 2. Resolve Entity ID -> Device ID
        ent_reg = er.async_get(hass)
        dev_reg = dr.async_get(hass)
        
        entity_entry = ent_reg.async_get(target_entity)
        if not entity_entry or not entity_entry.device_id:
            raise ValueError(f"Could not find device for entity: {target_entity}")

        device_id = entity_entry.device_id
        
        # 3. Get the Device Object (to access your device_manager)
        device_entry = dev_reg.async_get(device_id)
        # Now you can use device_id to find your coordinator/manager in hass.data
        
        if not device_entry:
            return None

        for entry_id in device_entry.config_entries:
            if entry_id in hass.data[DOMAIN]:
                # Assuming your manager is stored here
                return hass.data[DOMAIN][entry_id]
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
        data = self.get_data_from_call(call, hass)
        if not data:
            _LOGGER.error("Device not found for service call: %s", call)
            return

        target_method_name = self._services[service_name].get(data.device.product_id)
        if target_method_name:
            method = getattr(data.coordinator.device_manager, target_method_name)
            await method(call, data.device)

# Global instance
SERVICE_REGISTRY = TuyaBLEServiceRegistry()
