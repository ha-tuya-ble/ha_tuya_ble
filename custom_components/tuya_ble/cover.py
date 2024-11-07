"""The Tuya BLE integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from homeassistant.components.cover import (
    CoverEntity,
    CoverEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
)
from .devices import TuyaBLEData, TuyaBLEEntity, TuyaBLEProductInfo
from .tuya_ble import TuyaBLEDataPointType, TuyaBLEDevice

_LOGGER = logging.getLogger(__name__)

SIGNAL_STRENGTH_DP_ID = -1

TuyaBLECoverGetter = Callable[["TuyaBLECover", TuyaBLEProductInfo], str | None] | None


TuyaBLECoverIsAvailable = Callable[["TuyaBLECover", TuyaBLEProductInfo], bool] | None


TuyaBLECoverSetter = Callable[["TuyaBLECover", TuyaBLEProductInfo, str], None] | None


@dataclass
class TuyaBLECoverMapping:
    dp_id: int
    description: CoverEntityDescription
    force_add: bool = True
    dp_type: TuyaBLEDataPointType | None = None
    default_value: str | None = None
    is_available: TuyaBLECoverIsAvailable = None
    getter: Callable[[TuyaBLECover], None] | None = None
    setter: Callable[[TuyaBLECover], None] | None = None


@dataclass
class TuyaBLECategoryCoverMapping:
    products: dict[str, list[TuyaBLECoverMapping]] | None = None
    mapping: list[TuyaBLECoverMapping] | None = None


mapping: dict[str, TuyaBLECategoryCoverMapping] = {}


def get_mapping_by_device(device: TuyaBLEDevice) -> list[TuyaBLECoverMapping]:
    category = mapping.get(device.category)
    if category is not None and category.products is not None:
        product_mapping = category.products.get(device.product_id)
        if product_mapping is not None:
            return product_mapping
        if category.mapping is not None:
            return category.mapping
        else:
            return []
    else:
        return []


class TuyaBLECover(TuyaBLEEntity, CoverEntity):
    """Representation of a Tuya BLE text entity."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: DataUpdateCoordinator,
        device: TuyaBLEDevice,
        product: TuyaBLEProductInfo,
        mapping: TuyaBLECoverMapping,
    ) -> None:
        super().__init__(hass, coordinator, device, product, mapping.description)
        self._mapping = mapping

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        result = super().available
        if result and self._mapping.is_available:
            result = self._mapping.is_available(self, self._product)
        return result

    @property
    def native_value(self) -> str | None:
        """Return the value reported by the text."""
        if self._mapping.getter:
            return self._mapping.getter(self, self._product)

        datapoint = self._device.datapoints[self._mapping.dp_id]
        if datapoint:
            return str(datapoint.value)

        return self._mapping.description.default_value

    def set_value(self, value: str) -> None:
        """Change the value."""
        if self._mapping.setter:
            self._mapping.setter(self, self._product, value)
            return
        datapoint = self._device.datapoints.get_or_create(
            self._mapping.dp_id,
            TuyaBLEDataPointType.DT_STRING,
            value,
        )
        if datapoint:
            self._hass.create_task(datapoint.set_value(value))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Tuya BLE sensors."""
    data: TuyaBLEData = hass.data[DOMAIN][entry.entry_id]
    mappings = get_mapping_by_device(data.device)
    entities: list[TuyaBLECover] = []
    for mapping in mappings:
        if mapping.force_add or data.device.datapoints.has_id(
            mapping.dp_id, mapping.dp_type
        ):
            entities.append(
                TuyaBLECover(
                    hass,
                    data.coordinator,
                    data.device,
                    data.product,
                    mapping,
                )
            )
    async_add_entities(entities)
