"""The Tuya BLE integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .devices import TuyaBLEData, TuyaBLEEntity, TuyaBLEProductInfo
from .tuya_ble import TuyaBLEDataPointType, TuyaBLEDevice

_LOGGER = logging.getLogger(__name__)

TuyaBLEBinarySensorIsAvailable = (
    Callable[["TuyaBLEBinarySensor", TuyaBLEProductInfo], bool] | None
)

@dataclass
class TuyaBLEBinarySensorMapping:
    """Model a DP for a binary sensor entity."""
    dp_id: int
    description: BinarySensorEntityDescription
    force_add: bool = True
    dp_type: TuyaBLEDataPointType | None = None
    getter: Callable[[TuyaBLEBinarySensor], None] | None = None
    is_available: TuyaBLEBinarySensorIsAvailable = None

@dataclass
class TuyaBLECategoryBinarySensorMapping:
    """Models a dict of products and their mappings."""
    products: dict[str, list[TuyaBLEBinarySensorMapping]] | None = None
    mapping: list[TuyaBLEBinarySensorMapping] | None = None

mapping: dict[str, TuyaBLECategoryBinarySensorMapping] = {
    "dcb": TuyaBLECategoryBinarySensorMapping(
        products={
            "ajrhf1aj": [ # PARKSIDE Smart battery 8Ah
                TuyaBLEBinarySensorMapping(
                    dp_id=171,
                    description=BinarySensorEntityDescription(
                        key="cw_or_ccw_display",
                        icon="mdi:rotate-3d-variant",
                    ),
                ),
            ],
        },
    ),
    "wk": TuyaBLECategoryBinarySensorMapping(
        products={
            "drlajpqc": [ # Thermostatic Radiator Valve
                TuyaBLEBinarySensorMapping(
                    dp_id=105,
                    description=BinarySensorEntityDescription(
                        key="battery",
                        device_class=BinarySensorDeviceClass.BATTERY,
                        entity_category=EntityCategory.DIAGNOSTIC,
                    ),
                ),
            ],
        },
    ),
}

def get_mapping_by_device(device: TuyaBLEDevice) -> list[TuyaBLEBinarySensorMapping]:
    """Get the binary sensor mapping for a device."""
    category = mapping.get(device.category)
    if category:
        if category.products:
            product_mapping = category.products.get(device.product_id)
            if product_mapping:
                return product_mapping
        if category.mapping:
            return category.mapping
    return []

class TuyaBLEBinarySensor(TuyaBLEEntity, BinarySensorEntity):
    """Representation of a Tuya BLE binary sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: DataUpdateCoordinator,
        device: TuyaBLEDevice,
        product: TuyaBLEProductInfo,
        mapping: TuyaBLEBinarySensorMapping,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(hass, coordinator, device, product, mapping.description)
        self._mapping = mapping

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self._mapping.getter is not None:
            self._mapping.getter(self)
        else:
            datapoint = self._device.datapoints.get(self._mapping.dp_id)
            if datapoint:
                self._attr_is_on = bool(datapoint.value)
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        is_available = super().available
        if is_available and self._mapping.is_available:
            is_available = self._mapping.is_available(self, self._product)
        return is_available

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Tuya BLE binary sensors."""
    data: TuyaBLEData = hass.data[DOMAIN][entry.entry_id]
    mappings = get_mapping_by_device(data.device)
    entities: list[TuyaBLEBinarySensor] = []
    for entity_mapping in mappings:
        if entity_mapping.force_add or data.device.datapoints.has_id(
            entity_mapping.dp_id, entity_mapping.dp_type
        ):
            entities.append(
                TuyaBLEBinarySensor(
                    hass,
                    data.coordinator,
                    data.device,
                    data.product,
                    entity_mapping,
                )
            )
    async_add_entities(entities)
