"""Diagnostics support for Tuya BLE."""

from __future__ import annotations

import time
from typing import Any

from homeassistant.components import bluetooth
from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_LOCAL_KEY,
    CONF_SEC_KEY,
    CONF_UUID,
    DOMAIN,
)
from .devices import TuyaBLEData

TO_REDACT = {
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_LOCAL_KEY,
    CONF_SEC_KEY,
    CONF_UUID,
    "api_key",
    "token",
    "mac",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    address: str = entry.data.get(CONF_ADDRESS, "")
    result: dict[str, Any] = {
        "entry": {
            "title": entry.title,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        },
    }

    # Bluetooth visibility, independent of whether the entry is loaded
    service_info = (
        bluetooth.async_last_service_info(hass, address, connectable=True)
        if address
        else None
    )
    result["bluetooth"] = {
        "seen": service_info is not None,
        "rssi": service_info.rssi if service_info else None,
        "source": service_info.source if service_info else None,
        "name": service_info.name if service_info else None,
        "connectable": service_info.connectable if service_info else None,
        "connectable_scanner_count": bluetooth.async_scanner_count(
            hass, connectable=True
        ),
    }

    data: TuyaBLEData | None = getattr(entry, "runtime_data", None)
    if data is None and DOMAIN in hass.data:
        data = hass.data[DOMAIN].get(entry.entry_id)

    if data is None:
        result["device"] = {"loaded": False}
        return result

    device = data.device
    is_connected = getattr(
        device,
        "is_connected",
        bool(
            getattr(device, "_client", None)
            and getattr(device._client, "is_connected", False)
            and getattr(device, "_is_paired", False)
        ),
    )
    seconds_since_last_connect = None
    last_connected_at = getattr(device, "last_connected_at", None)
    if last_connected_at is not None:
        seconds_since_last_connect = round(time.monotonic() - last_connected_at, 1)

    result["device"] = {
        "loaded": True,
        "address": device.address,
        "name": device.name,
        "product_id": device.product_id,
        "category": device.category,
        "product_name": device.product_name,
        "product_model": device.product_model,
        "device_version": device.device_version,
        "hardware_version": device.hardware_version,
        "protocol_version": device.protocol_version,
        "keep_connection": getattr(device, "keep_connection", True),
        "connected": is_connected,
        "coordinator_connected": (
            data.coordinator.connected if data.coordinator else False
        ),
        "seconds_since_last_connect": seconds_since_last_connect,
        "last_connect_error": getattr(device, "last_connect_error", None),
        "rssi": device.rssi,
    }
    result["product_info"] = (
        {"manufacturer": data.product.manufacturer, "name": data.product.name}
        if data.product
        else None
    )
    result["datapoints"] = [
        {
            "id": dp.id,
            "type": dp.type.name if dp.type else None,
            "value": (
                dp.value
                if not isinstance(dp.value, (bytes, bytearray))
                else dp.value.hex()
            ),
        }
        for dp in _iter_datapoints(device)
    ]
    return result


def _iter_datapoints(device) -> list:
    dps = device.datapoints
    inner = getattr(dps, "_datapoints", {})
    return [inner[k] for k in sorted(inner)]
