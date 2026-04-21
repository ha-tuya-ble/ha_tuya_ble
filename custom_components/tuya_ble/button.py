"""The Tuya BLE integration."""

from __future__ import annotations

from dataclasses import dataclass, field

import logging
from typing import Callable

from homeassistant.components.button import (
    ButtonEntityDescription,
    ButtonEntity,
    ButtonDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .devices import TuyaBLEData, TuyaBLEEntity, TuyaBLEProductInfo
from .tuya_ble import TuyaBLEDataPointType, TuyaBLEDevice

_LOGGER = logging.getLogger(__name__)


TuyaBLEButtonIsAvailable = Callable[["TuyaBLEButton", TuyaBLEProductInfo], bool] | None


@dataclass
class TuyaBLEButtonMapping:
    """Model a DP, description and default values"""

    dp_id: int
    description: ButtonEntityDescription
    force_add: bool = True
    dp_type: TuyaBLEDataPointType | None = None
    is_available: TuyaBLEButtonIsAvailable = None


def is_fingerbot_in_push_mode(self: TuyaBLEButton, product: TuyaBLEProductInfo) -> bool:
    result: bool = True
    if product.fingerbot:
        datapoint = self._device.datapoints[product.fingerbot.mode]
        if datapoint:
            result = datapoint.value == 0
    return result


@dataclass
class TuyaBLEFingerbotModeMapping(TuyaBLEButtonMapping):
    """Describes availability of a given button"""

    description: ButtonEntityDescription = field(
        default_factory=lambda: ButtonEntityDescription(
            key="push",
        )
    )
    is_available: TuyaBLEButtonIsAvailable = is_fingerbot_in_push_mode


@dataclass
class TuyaBLELockMapping(TuyaBLEButtonMapping):
    """Describes availability of a given button"""

    description: ButtonEntityDescription = field(
        default_factory=lambda: ButtonEntityDescription(
            key="push",
        )
    )
    is_available: TuyaBLEButtonIsAvailable = 0


@dataclass
class TuyaBLECategoryButtonMapping:
    """Describes a dict of products and their mappings"""

    products: dict[str, list[TuyaBLEButtonMapping]] | None = None
    mapping: list[TuyaBLEButtonMapping] | None = None


mapping: dict[str, TuyaBLECategoryButtonMapping] = {
    "dcb": TuyaBLECategoryButtonMapping(
        products={
            **dict.fromkeys(
                ["ajrhf1aj", "z5ztlw3k"],  # PARKSIDE Smart battery
                [
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
            ),
        },
    ),
    "szjqr": TuyaBLECategoryButtonMapping(
        products={
            **dict.fromkeys(
                ["3yqdo5yt", "xhf790if"],  # CubeTouch 1s and II
                [
                    TuyaBLEFingerbotModeMapping(dp_id=1),
                ],
            ),
            **dict.fromkeys(
                [
                    "blliqpsj",
                    "ndvkgsrm",
                    "riecov42",
                    "yiihr7zh",
                    "neq16kgd",
                    "6jcvqwh0",
                    "h8kdwywx",
                ],  # Fingerbot Plus
                [
                    TuyaBLEFingerbotModeMapping(dp_id=2),
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
                    TuyaBLEFingerbotModeMapping(dp_id=2),
                ],
            ),
        },
    ),
    "kg": TuyaBLECategoryButtonMapping(
        products={
            **dict.fromkeys(
                ["mknd4lci", "riecov42", "bs3ubslo"],  # Fingerbot Plus
                [
                    TuyaBLEFingerbotModeMapping(dp_id=108),
                ],
            ),
        },
    ),
    "znhsb": TuyaBLECategoryButtonMapping(
        products={
            "cdlandip": [  # Smart water bottle
                TuyaBLEButtonMapping(
                    dp_id=109,
                    description=ButtonEntityDescription(
                        key="bright_lid_screen",
                    ),
                ),
            ],
        },
    ),
    "jtmspro": TuyaBLECategoryButtonMapping(
        products={
            **dict.fromkeys(
                [
                    "xicdxood",  # Raycube K7 Pro+
                    "rlyxv7pe",  # A1 PRO MAX
                    "oyqux5vv",  # LA-01
                ],
                [
                    # Raycube K7 Pro+, unclear if applicable to A1 PRO MAX
                    TuyaBLEButtonMapping(
                        dp_id=71,  # On click it opens the lock, just like connecting via Smart Life App
                        # and holding the center button
                        description=ButtonEntityDescription(
                            key="bluetooth_unlock",
                            icon="mdi:lock-open-variant-outline",
                        ),
                    ),
                ],
            ),
            "hs21i377": [
                TuyaBLEButtonMapping(
                    dp_id=71,
                    description=ButtonEntityDescription(
                        key="bluetooth_unlock",
                        icon="mdi:lock-open-check-outline",
                    ),
                    dp_type=TuyaBLEDataPointType.DT_RAW,
                ),
            ],
        },
    ),
    "ms": TuyaBLECategoryButtonMapping(
        products={
            **dict.fromkeys(
                ["okkyfgfs", "k53ok3u9", "sidhzylo", "a6nttc41"],  # Smart Lock
                [
                    TuyaBLEButtonMapping(
                        dp_id=6,
                        description=ButtonEntityDescription(
                            key="bluetooth_unlock",
                        ),
                    ),
                    # TuyaBLEButtonMapping(
                    #    dp_id=12,
                    #    description=ButtonEntityDescription(
                    #        key="unlock_fingerprint",
                    #    ),
                    # ),
                ],
            ),
        }
    ),
}


def get_mapping_by_device(device: TuyaBLEDevice) -> list[TuyaBLECategoryButtonMapping]:
    category = mapping.get(device.category)
    if category is not None and category.products is not None:
        product_mapping = category.products.get(device.product_id)
        if product_mapping is not None:
            return product_mapping
        if category.mapping is not None:
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
        super().__init__(hass, coordinator, device, product, mapping.description)
        self._mapping = mapping

    async def _run_hs21i377_unlock(self) -> None:
        """Run the validated dp71 unlock flow for hs21i377."""
        # hs21i377 uses a device-specific dp71 unlock payload.
        # Practical testing confirmed multiple payload variants can unlock,
        # so this is not treated as a fixed "known lock code". We keep an
        # empirically validated value here until the payload semantics are
        # understood better.
        dp71_value = bytes.fromhex("0001ffff36383538313536320169ab34cd0000")

        dp71 = self._device.datapoints.get_or_create(
            71,
            TuyaBLEDataPointType.DT_RAW,
            b"",
        )
        if dp71:
            await dp71.set_value(dp71_value)

    def press(self) -> None:
        """Press the button."""
        if self._device.product_id == "hs21i377":
            if self._mapping.description.key == "bluetooth_unlock":
                self._hass.create_task(self._run_hs21i377_unlock())
                return

        datapoint = self._device.datapoints.get_or_create(
            self._mapping.dp_id,
            TuyaBLEDataPointType.DT_BOOL,
            False,
        )
        if datapoint:
            if self._product.lock:
                # Lock needs true to activate lock/unlock commands
                self._hass.create_task(datapoint.set_value(True))
            else:
                self._hass.create_task(datapoint.set_value(not bool(datapoint.value)))

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        result = super().available
        if result and self._mapping.is_available:
            result = self._mapping.is_available(self, self._product)
        return result


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Tuya BLE sensors."""
    data: TuyaBLEData = hass.data[DOMAIN][entry.entry_id]
    mappings = get_mapping_by_device(data.device)
    entities: list[TuyaBLEButton] = []
    for mapping in mappings:
        if mapping.force_add or data.device.datapoints.has_id(
            mapping.dp_id, mapping.dp_type
        ):
            entities.append(
                TuyaBLEButton(
                    hass,
                    data.coordinator,
                    data.device,
                    data.product,
                    mapping,
                )
            )
    async_add_entities(entities)
