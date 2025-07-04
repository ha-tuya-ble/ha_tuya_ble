"""The Tuya BLE integration."""
from __future__ import annotations

from dataclasses import dataclass, field
import logging

from homeassistant.components.select import (
    SelectEntityDescription,
    SelectEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    FINGERBOT_MODE_PROGRAM,
    FINGERBOT_MODE_PUSH,
    FINGERBOT_MODE_SWITCH,
)
from .devices import TuyaBLEData, TuyaBLEEntity, TuyaBLEProductInfo
from .tuya_ble import TuyaBLEDataPointType, TuyaBLEDevice

_LOGGER = logging.getLogger(__name__)

@dataclass
class TuyaBLESelectMapping:
    """Model a DP for a select entity."""
    dp_id: int
    description: SelectEntityDescription
    force_add: bool = True
    dp_type: TuyaBLEDataPointType | None = None

@dataclass
class TemperatureUnitDescription(SelectEntityDescription):
    """A SelectEntityDescription for temperature units."""
    key: str = "temperature_unit"
    icon: str = "mdi:thermometer"
    entity_category: EntityCategory = EntityCategory.CONFIG

@dataclass
class TuyaBLEFingerbotModeMapping(TuyaBLESelectMapping):
    """A select mapping for a fingerbot's mode."""
    description: SelectEntityDescription = field(
        default_factory=lambda: SelectEntityDescription(
            key="fingerbot_mode",
            entity_category=EntityCategory.CONFIG,
            options=[
                FINGERBOT_MODE_PUSH,
                FINGERBOT_MODE_SWITCH,
                FINGERBOT_MODE_PROGRAM,
            ],
        )
    )

@dataclass
class TuyaBLECategorySelectMapping:
    """Models a dict of products and their mappings"""
    products: dict[str, list[TuyaBLESelectMapping]] | None = None
    mapping: list[TuyaBLESelectMapping] | None = None

mapping: dict[str, TuyaBLECategorySelectMapping] = {
    "co2bj": TuyaBLECategorySelectMapping(
        products={
            "59s19z5m": [  # CO2 Detector
                TuyaBLESelectMapping(
                    dp_id=101,
                    description=TemperatureUnitDescription(
                        options=[
                            UnitOfTemperature.CELSIUS,
                            UnitOfTemperature.FAHRENHEIT,
                        ],
                    ),
                ),
            ],
        },
    ),
    "dcb": TuyaBLECategorySelectMapping(
        products={
            "ajrhf1aj": [  # PARKSIDE Smart battery 8Ah
                TuyaBLESelectMapping(
                    dp_id=105,
                    description=SelectEntityDescription(
                        key="battery_work_mode",
                        icon="mdi:leaf-circle-outline",
                        options=["Performance", "Balanced", "Eco", "Expert"],
                        entity_category=EntityCategory.CONFIG,
                    ),
                ),
                TuyaBLESelectMapping(
                    dp_id=174,
                    description=SelectEntityDescription(
                        key="pack_work_mode",
                        icon="mdi:leaf-circle-outline",
                        options=["Performance", "Balanced", "Eco", "Expert"],
                        entity_category=EntityCategory.CONFIG,
                    ),
                ),
            ],
        },
    ),
    "ms": TuyaBLECategorySelectMapping(
        products={
            **dict.fromkeys(
                ["ludzroix", "isk2p555"],  # Smart Lock
            ): [
                TuyaBLESelectMapping(
                    dp_id=31,
                    description=SelectEntityDescription(
                        key="beep_volume",
                        options=[
                            "mute",
                            "low",
                            "normal",
                            "high",
                        ],
                        entity_category=EntityCategory.CONFIG,
                    ),
                ),
            ],
        },
    ),
    "szjqr": TuyaBLECategorySelectMapping(
        products={
            **dict.fromkeys(
                ["3yqdo5yt", "xhf790if"],  # CubeTouch 1s and II
            ): [
                TuyaBLEFingerbotModeMapping(dp_id=2),
            ],
            **dict.fromkeys(
                [
                    "blliqpsj",
                    "ndvkgsrm",
                    "yiihr7zh",
                    "neq16kgd"
                ],  # Fingerbot Plus
            ): [
                TuyaBLEFingerbotModeMapping(dp_id=8),
            ],
            **dict.fromkeys(
                ["ltak7e1p", "y6kttvd6", "yrnk7mnn",
                 "nvr2rocq", "bnt7wajf", "rvdceqjh",
                 "5xhbk964"],  # Fingerbot
            ): [
                TuyaBLEFingerbotModeMapping(dp_id=8),
            ],
        },
    ),
    "wsdcg": TuyaBLECategorySelectMapping(
        products={
            "ojzlzzsw": [  # Soil moisture sensor
                TuyaBLESelectMapping(
                    dp_id=9,
                    description=TemperatureUnitDescription(
                        options=[
                            UnitOfTemperature.CELSIUS,
                            UnitOfTemperature.FAHRENHEIT,
                        ],
                        entity_registry_enabled_default=False,
                    ),
                ),
            ],
        },
    ),
    "znhsb": TuyaBLECategorySelectMapping(
        products={
            "cdlandip": [  # Smart water bottle
                TuyaBLESelectMapping(
                    dp_id=106,
                    description=TemperatureUnitDescription(
                        options=[
                            UnitOfTemperature.CELSIUS,
                            UnitOfTemperature.FAHRENHEIT,
                        ],
                    ),
                ),
                TuyaBLESelectMapping(
                    dp_id=107,
                    description=SelectEntityDescription(
                        key="reminder_mode",
                        options=[
                            "interval_reminder",
                            "schedule_reminder",
                        ],
                        entity_category=EntityCategory.CONFIG,
                    ),
                ),
            ],
        },
    ),
}

def get_mapping_by_device(device: TuyaBLEDevice) -> list[TuyaBLESelectMapping]:
    """Get the select mapping for a device."""
    category = mapping.get(device.category)
    if category:
        if category.products:
            product_mapping = category.products.get(device.product_id)
            if product_mapping:
                return product_mapping
        if category.mapping:
            return category.mapping
    return []

class TuyaBLESelect(TuyaBLEEntity, SelectEntity):
    """Representation of a Tuya BLE select."""

    def __init__(
        self,
        hass: HomeAssistant,
