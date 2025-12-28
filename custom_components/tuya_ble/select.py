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
    """Model a DP, description and default values"""

    dp_id: int
    description: SelectEntityDescription
    force_add: bool = True
    dp_type: TuyaBLEDataPointType | None = None


@dataclass
class TemperatureUnitDescription(SelectEntityDescription):
    """Description of temperature unit"""

    key: str = "temperature_unit"
    icon: str = "mdi:thermometer"
    entity_category: EntityCategory = EntityCategory.CONFIG


@dataclass
class TuyaBLEFingerbotModeMapping(TuyaBLESelectMapping):
    """Fingerbot mode mapping"""

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
class TuyaBLEWeatherDelayMapping(TuyaBLESelectMapping):
    description: SelectEntityDescription = field(
        default_factory=lambda: SelectEntityDescription(
            key="weather_delay",
            entity_category=EntityCategory.CONFIG,
            options=[
                "cancel",
                "24h",
                "48h",
                "72h",
                "96h",
                "120h",
                "144h",
                "168h",
            ],
        )
    )


@dataclass
class TuyaBLESmartWeatherMapping(TuyaBLESelectMapping):
    description: SelectEntityDescription = field(
        default_factory=lambda: SelectEntityDescription(
            key="smart_weather",
            entity_category=EntityCategory.CONFIG,
            options=[
                "sunny",
                "cloudy",
                "rainy",
            ],
        )
    )


@dataclass
class TuyaBLECategorySelectMapping:
    products: dict[str, list[TuyaBLESelectMapping]] | None = None
    mapping: list[TuyaBLESelectMapping] | None = None


@dataclass
class TuyaBLETemperatureUnitMapping(TuyaBLESelectMapping):
    description: TemperatureUnitDescription = field(
        default_factory=lambda: TemperatureUnitDescription(
            options=[
                UnitOfTemperature.CELSIUS,
                UnitOfTemperature.FAHRENHEIT,
            ],
            entity_registry_enabled_default=False,
        )
    )


mapping: dict[str, TuyaBLECategorySelectMapping] = {
    "sfkzq": TuyaBLECategorySelectMapping(
        products={
            **dict.fromkeys(
                ["46zia2nz", "1fcnd8xk", "0axr5s0b"],
                [
                    TuyaBLESelectMapping(
                        dp_id=10,
                        description=SelectEntityDescription(
                            key="weather_delay",
                            options=[
                                "cancel",
                                "24h",
                                "48h",
                                "72h",
                            ],
                            entity_category=EntityCategory.CONFIG,
                        ),
                    ),
                    TuyaBLESelectMapping(
                        dp_id=12,
                        description=SelectEntityDescription(
                            key="work_state",
                            options=["auto", "manual", "idle"],
                            entity_category=EntityCategory.CONFIG,
                        ),
                    ),
                ],
            ),
            "nxquc5lb": [  # Smart water timer - SOP10
                TuyaBLEWeatherDelayMapping(dp_id=10),
                TuyaBLESmartWeatherMapping(dp_id=13),
            ],
            "svhikeyq": [  # Smart water timer
                TuyaBLESelectMapping(
                    dp_id=10,
                    description=SelectEntityDescription(
                        key="weather_delay",
                        options=[
                            "cancel",
                            "24h",
                            "48h",
                            "72h",
                        ],
                        entity_category=EntityCategory.CONFIG,
                    ),
                ),
                TuyaBLESmartWeatherMapping(dp_id=13),
            ],
        },
    ),
    "co2bj": TuyaBLECategorySelectMapping(
        products={
            "59s19z5m": [TuyaBLETemperatureUnitMapping(dp_id=101)],  # CO2 Detector
        },
    ),
    "dcb": TuyaBLECategorySelectMapping(
        products={
            **dict.fromkeys(
                ["ajrhf1aj", "z5ztlw3k"],  # PARKSIDE Smart battery
                [
                    TuyaBLESelectMapping(
                        dp_id=105,
                        description=SelectEntityDescription(
                            key="battery_work_mode",
                            icon="mdi:leaf-circle-outline",
                            options=[
                                "Performance",
                                "Balanced",
                                "Eco",
                                "Expert",
                            ],
                            entity_category=EntityCategory.CONFIG,
                        ),
                    ),
                    TuyaBLESelectMapping(
                        dp_id=174,
                        description=SelectEntityDescription(
                            key="pack_work_mode",
                            icon="mdi:leaf-circle-outline",
                            options=[
                                "Performance",
                                "Balanced",
                                "Eco",
                                "Expert",
                            ],
                            entity_category=EntityCategory.CONFIG,
                        ),
                    ),
                ],
            ),
        },
    ),
    "ms": TuyaBLECategorySelectMapping(
        products={
            **dict.fromkeys(
                [
                    "ludzroix",
                    "isk2p555",
                    "gumrixyt",
                    "uamrw6h3",
                    "okkyfgfs",
                ],  # Smart Lock
                [
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
            ),
        }
    ),
    "jtmspro": TuyaBLECategorySelectMapping(
        products={
            **dict.fromkeys(
                [
                    "xicdxood",  # Raycube K7 Pro+
                    "rlyxv7pe",  # A1 PRO MAX - Experimental
                    "oyqux5vv",  # LA-01 - Experimental
                    "ajk32biq",  # B16
                    "z7lj676i",  # Smart Cylinder Lock - Experimental
                ],
                [  # Raycube K7 Pro+
                    TuyaBLESelectMapping(
                        dp_id=31,
                        description=SelectEntityDescription(
                            key="beep_volume",
                            options=[
                                "Mute",
                                "Low",
                                "Normal",
                                "High",
                            ],
                            entity_category=EntityCategory.CONFIG,
                        ),
                    ),
                    TuyaBLESelectMapping(
                        dp_id=28,
                        description=SelectEntityDescription(
                            key="language",
                            options=[
                                "Chinese Simplified",
                                "English",
                                "Arabic",
                                "Indonesian",
                                "Portuguese",
                            ],
                            entity_category=EntityCategory.CONFIG,
                        ),
                    ),
                ],
            )
        }
    ),
    "szjqr": TuyaBLECategorySelectMapping(
        products={
            **dict.fromkeys(
                ["3yqdo5yt", "xhf790if", "yn4x5fa7"],  # CubeTouch 1s and II
                [
                    TuyaBLEFingerbotModeMapping(dp_id=2),
                ],
            ),
            **dict.fromkeys(
                [
                    "blliqpsj",
                    "ndvkgsrm",
                    "yiihr7zh",
                    "neq16kgd",
                    "6jcvqwh0",
                    "riecov42",
                    "h8kdwywx",
                ],  # Fingerbot Plus
                [
                    TuyaBLEFingerbotModeMapping(dp_id=8),
                ],
            ),
            **dict.fromkeys(
                [
                    "ltak7e1p",
                    "y6kttvd6",
                    "yrnk7mnn",
                    "nvr2rocq",
                    "bnt7wajf",
                    "rvdceqjh",
                    "5xhbk964",
                ],  # Fingerbot
                [
                    TuyaBLEFingerbotModeMapping(dp_id=8),
                ],
            ),
        },
    ),
    "kg": TuyaBLECategorySelectMapping(
        products={
            **dict.fromkeys(
                ["mknd4lci", "riecov42", "bs3ubslo"],  # Fingerbot Plus
                [
                    TuyaBLEFingerbotModeMapping(dp_id=101),
                ],
            ),
        },
    ),
    "wsdcg": TuyaBLECategorySelectMapping(
        products={
            "ojzlzzsw": [  # Soil moisture sensor
                TuyaBLETemperatureUnitMapping(dp_id=9)
            ],
            "iv7hudlj": [  # Bluetooth Temperature Humidity Sensor
                TuyaBLETemperatureUnitMapping(dp_id=9)
            ],
            "jm6iasmb": [  # Bluetooth Temperature Humidity Sensor
                TuyaBLETemperatureUnitMapping(dp_id=9)
            ],
            "vlzqwckk": [TuyaBLETemperatureUnitMapping(dp_id=9)],
        },
    ),
    "znhsb": TuyaBLECategorySelectMapping(
        products={
            "cdlandip": [  # Smart water bottle
                TuyaBLETemperatureUnitMapping(dp_id=106),
                TuyaBLESelectMapping(
                    dp_id=107,
                    description=SelectEntityDescription(
                        key="reminder_mode",
                        options=[
                            "interval_reminder",
                            "alarm_reminder",  # TODO: schedule_reminder?
                        ],
                        entity_category=EntityCategory.CONFIG,
                    ),
                ),
            ],
        },
    ),
    # "swtz": TuyaBLECategorySelectMapping(
    #     products={
    #         "bf092bejeznilat9": [  # LSC BBQ Thermometer
    #             TuyaBLESelectMapping(
    #                 dp_id=106,
    #                 description=TemperatureUnitDescription(
    #                     options=[
    #                         "c",
    #                         "f",
    #                     ],
    #                 ),
    #             ),
    #         ]
    #     },
    # ),
}


def get_mapping_by_device(device: TuyaBLEDevice) -> list[TuyaBLECategorySelectMapping]:
    category = mapping.get(device.category)
    if category is not None and category.products is not None:
        product_mapping = category.products.get(device.product_id)
        if product_mapping is not None:
            return product_mapping
        if category.mapping is not None:
            return category.mapping

    return []


class TuyaBLESelect(TuyaBLEEntity, SelectEntity):
    """Representation of a Tuya BLE select."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: DataUpdateCoordinator,
        device: TuyaBLEDevice,
        product: TuyaBLEProductInfo,
        mapping: TuyaBLESelectMapping,
    ) -> None:
        super().__init__(hass, coordinator, device, product, mapping.description)
        self._mapping = mapping
        self._attr_options = mapping.description.options

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""
        # Raw value
        value: str | None = None
        datapoint = self._device.datapoints[self._mapping.dp_id]
        if datapoint:
            value = datapoint.value
            if 0 <= value < len(self._attr_options):
                return self._attr_options[value]

            return value
        return None

    def select_option(self, value: str) -> None:
        """Change the selected option."""
        if value in self._attr_options:
            int_value = self._attr_options.index(value)
            datapoint = self._device.datapoints.get_or_create(
                self._mapping.dp_id,
                TuyaBLEDataPointType.DT_ENUM,
                int_value,
            )
            if datapoint:
                self._hass.create_task(datapoint.set_value(int_value))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Tuya BLE sensors."""
    data: TuyaBLEData = hass.data[DOMAIN][entry.entry_id]
    mappings = get_mapping_by_device(data.device)
    entities: list[TuyaBLESelect] = []
    for mapping in mappings:
        if mapping.force_add or data.device.datapoints.has_id(
            mapping.dp_id, mapping.dp_type
        ):
            entities.append(
                TuyaBLESelect(
                    hass,
                    data.coordinator,
                    data.device,
                    data.product,
                    mapping,
                )
            )
    async_add_entities(entities)
