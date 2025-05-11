from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.components.diagnostics import async_redact_data

TO_REDACT = {
    "username",
    "password",
    "local_key",
    "api_key",
    "token",
    "host",
    "mac",
}

async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry):
    data = {
        "entry": entry.as_dict(),
        "data": entry.data,
        "options": entry.options,
    }
    return async_redact_data(data, TO_REDACT)

async def async_get_device_diagnostics(hass: HomeAssistant, entry, device):
    # Optional: if your integration uses devices (via the device registry)
    device_data = {
        "device_name": device.name,
        "identifiers": list(device.identifiers),
        "manufacturer": device.manufacturer,
        "model": device.model,
        # Add any other relevant device details here
    }
    return async_redact_data(device_data, TO_REDACT)