"""The Tuya BLE integration."""
from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Callable

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .devices import TuyaBLEData, TuyaBLEEntity, TuyaBLEProductInfo
from .tuya_ble import TuyaBLEDataPointType, TuyaBLEDevice

_LOGGER = logging.getLogger(__name__)

TuyaBLEButtonIsAvailable = Callable[["TuyaBLEButton", TuyaBLEProductInfo], bool] | None

@dataclass
class TuyaBLEButtonMapping:
    """Model a DP for a button entity."""
    dp_id: int
    description: ButtonEntityDescription
    force_add: bool = True
    dp_type: TuyaBLEDataPointType | None = None
    is_available: TuyaBLEButtonIsAvailable = None

def is_fingerbot_in_push_mode(self: TuyaBLEButton, product: TuyaBLEProductInfo) -> bool:
    """Check if the fingerbot is in push mode."""
    result: bool = True
    if product.fingerbot:
        datapoint = self._device.datapoints.get(product.fingerbot.mode)
        if datapoint:
            result = datapoint.value == 0
    return result

@dataclass
class TuyaBLEFingerbotModeMapping(TuyaBLEButtonMapping):
    """A button mapping for a fingerbot."""
    description: ButtonEntityDescription = field(
        default_factory=lambda: ButtonEntityDescription(
            key="push",
        )
    )
    is_available: TuyaBLEButtonIsAvailable = is_fingerbot_in_push_mode

@dataclass
class TuyaBLECategoryButtonMapping:
    """Models a dict of products and their mappings."""
    products: dict[str, list[TuyaBLEButtonMapping]] | None = None
    mapping: list[TuyaBLEButtonMapping] | None = None

mapping: dict[str, TuyaBLECategoryButtonMapping] = {
    "dcb": TuyaBLECategoryButtonMapping(
        products={
            "ajrhf1aj": [ # PARKSIDE Smart battery 8Ah
                TuyaBLEButtonMapping(
                    dp_id=115,
                    description=ButtonEntityDescription(
                        key="battery_finder",
                        icon="mdi:find-replace",
                        entity_category=EntityCategory.DIAGNOSTIC,
                    ),
                ),
                TuyaBLEButtonMapping(
                    dp_id=162,
                    description=ButtonEntityDescription(
                        key="factory_data_reset",
                        device_class=ButtonDeviceClass.RESTART,
                        icon="mdi:restore",
                        entity_category=EntityCategory.CONFIG,
                    ),
                    dp_type=TuyaBLEDataPointType.DT_RAW,
                ),
            ],
        },
    ),
    "szjqr": TuyaBLECategoryButtonMapping(
        products={
            **dict.fromkeys(
                ["3yqdo5yt", "xhf790if"], # CubeTouch 1s and II
            ): [
                TuyaBLEFingerbotModeMapping(dp_id=1),
            ],
            **dict.fromkeys(
                [
                    "blliqpsj",
                    "ndvkgsrm",
                    "yiihr7zh",
                    "neq16kgd"
                ], # Fingerbot Plus
            ): [
                TuyaBLEFingerbotModeMapping(dp_id=2),
            ],
            **dict.fromkeys(
                [
                    "ltak7e1p",
                    "y6kttvd6",
                    "yrnk7mnn",
                    "nvr2rocq",
                    "bnt7wajf",
                    "rvdceqjh",
                    "5xhbk964",
                ], # Fingerbot
            ): [
                TuyaBLEFingerbotModeMapping(dp_id=2),
            ],
        },
    ),
    "znhsb": TuyaBLECategoryButtonMapping(
        products={
            "cdlandip": [ # Smart water bottle
                TuyaBLEButtonMapping(
                    dp_id=109,
                    description=ButtonEntityDescription(
                        key="bright_lid_screen",
                    ),
                ),
            ],
        },
    ),
}

def get_mapping_by_device(device: TuyaBLEDevice) -> list[TuyaBLEButtonMapping]:
    """Get the button mapping for a device."""
    category = mapping.get(device.category)
    if category:
        if category.products:
            product_mapping = category.products.get(device.product_id)
            if product_mapping:
                return product_mapping
        if category.mapping:
            return category.mapping
    return []

class TuyaBLEButton(TuyaBLEEntity, ButtonEntity):
    """Representation of a Tuya BLE Button."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: DataUpdateCoordinator,
        device: TuyaBLEDevice,
        product: TuyaBLEProductInfo,
        mapping: TuyaBLEButtonMapping,
    ) -> None:
        """Initialize the button."""
        super().__init__(hass, coordinator, device, product, mapping.description)
        self._mapping = mapping

    async def async_press(self) -> None:
        """Handle the button press."""
        value: bool | bytes = True
        dp_type = self._mapping.dp_type
        if dp_type == TuyaBLEDataPointType.DT_RAW:
            value = b'\x01'
        elif dp_type is None: # Assume boolean for older configs
            dp_type = TuyaBLEDataPointType.DT_BOOL

        datapoint = self._device.datapoints.get_or_create(
            self._mapping.dp_id,
            dp_type,
            value,
        )
        if datapoint:
            if dp_type == TuyaBLEDataPointType.DT_BOOL:
                # Toggle for boolean buttons
                await datapoint.set_value(not bool(datapoint.value))
            else:
                await datapoint.set_value(value)

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
    """Set up the Tuya BLE buttons."""
    data: TuyaBLEData = hass.data[DOMAIN][entry.entry_id]
    mappings = get_mapping_by_device(data.device)
    entities: list[TuyaBLEButton] = []
    for entity_mapping in mappings:
        if entity_mapping.force_add or data.device.datapoints.has_id(
            entity_mapping.dp_id, entity_mapping.dp_type
        ):
            entities.append(
                TuyaBLEButton(
                    hass,
                    data.coordinator,
                    data.device,
                    data.product,
                    entity_mapping,
                )
            )
    async_add_entities(entities)
