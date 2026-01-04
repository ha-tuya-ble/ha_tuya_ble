from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.lock import LockEntity, LockEntityFeature, LockEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, DPCode
from .devices import (
    TuyaBLEData,
    TuyaBLEEntity,
    TuyaBLECoordinator,
    get_device_product_info,
)
from .tuya_ble.productinfo import TuyaBLEProductInfo
from .models.geeksmartk11 import TuyaBLEGeeksmartLockInfo

from .tuya_ble import TuyaBLEDataPointType, TuyaBLEDevice

TuyaBLELockIsAvailable = Callable[["TuyaBLELock", TuyaBLEProductInfo], bool] | None

@dataclass
class TuyaBLELockMapping:
    """Models a BLE Lock"""

    dp_id: int
    description: LockEntityDescription
    force_add: bool = True
    dp_type: TuyaBLEDataPointType | None = None
    getter: Callable[[TuyaBLELock], None] | None = None
    is_available: TuyaBLELockIsAvailable = None

@dataclass
class TuyaBLECategoryLockMapping:
    """Maps between a dict of products and the sensors"""

    products: dict[str, list[TuyaBLELockMapping]] | None = None
    mapping: list[TuyaBLELockMapping] | None = None


mapping: dict[str, TuyaBLECategoryLockMapping] = {
    "jtmspro": TuyaBLECategoryLockMapping(
        products={
            **dict.fromkeys(
                ["czybdhba"],  # Geeksmart K11 Smart Lock
                [
                    TuyaBLELockMapping(
                        dp_id=47,
                        description=LockEntityDescription(
                            key="lock_motor_state",
                        ),
                    ),
                ],
            ),
        }
    ),
}

def get_mapping_by_device(device: TuyaBLEDevice) -> list[TuyaBLELockMapping]:
    category = mapping.get(device.category)
    if category is not None and category.products is not None:
        product_mapping = category.products.get(device.product_id)
        if product_mapping is not None:
            return product_mapping
        if category.mapping is not None:
            return category.mapping

    return []

class TuyaBLELock(TuyaBLEEntity, LockEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: TuyaBLECoordinator,
        device: TuyaBLEDevice,
        product: TuyaBLEProductInfo,
        mapping: TuyaBLELockMapping,
    ) -> None:
        super().__init__(hass, coordinator, device, product, mapping.description)
        self._attr_supported_features = LockEntityFeature.OPEN
        self._mapping = mapping
        if isinstance(self._product, TuyaBLEGeeksmartLockInfo):
            self._attr_supported_features = None
            # The Geeksmart K11 requires a 'Random Number' to be set before it can be used
            # Get the random number by unlocking the lock with the mobile app. Then get it from the Tuya IoT Cloud logs.
            # TODO: Update the readme with these instructions
            options = device.get_options_data()
            if "secret_code" in options:
                self._product.random_number = options["secret_code"].encode("ascii").hex()
            self._product.load_store(hass)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        result = super().available
        if result and self._mapping.is_available:
            result = self._mapping.is_available(self, self._product)
        return result

    @property
    def is_locked(self) -> bool:
        """Return true if lock is locked."""
        state = None
        
        if isinstance(self._product, TuyaBLEGeeksmartLockInfo):
            state = self._product.locked
            if state is None:
                # If the device is offline, show previous state or None
                return getattr(self, "_attr_is_locked", None)
        else:
            if motor_state := self._device.datapoints.get_or_create(
                DPCode.LOCK_MOTOR_STATE, TuyaBLEDataPointType.DT_BOOL, False
            ):
                state = not motor_state.value
        
        return bool(state)

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the lock."""
        if isinstance(self._product, TuyaBLEGeeksmartLockInfo):
            return self._product.extra_state_attributes()

        return super().extra_state_attributes
    
    async def async_handle_lock_sequence(self, value: bool) -> None:
        if isinstance(self._product, TuyaBLEGeeksmartLockInfo):
            if value:
                await self._product.async_lock(self._device)
            else:
                await self._product.async_unlock(self._device)
        else:
            if manual_lock := self._device.datapoints.get_or_create(
                DPCode.MANUAL_LOCK, TuyaBLEDataPointType.DT_BOOL, value
            ):
                await manual_lock.set_value(value)

    async def async_lock(self, **kwargs) -> None:
        """Lock all or specified locks. A code to lock the lock with may optionally be specified."""
        await self.async_handle_lock_sequence(True)

    async def async_unlock(self, **kwargs) -> None:
        """Unlock all or specified locks. A code to unlock the lock with may optionally be specified."""
        await self.async_handle_lock_sequence(False)

    async def async_open(self, **kwargs: Any) -> None:
        """Open the covering."""
        await self.async_handle_lock_sequence(False)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Tuya BLE sensors."""
    data: TuyaBLEData = hass.data[DOMAIN][entry.entry_id]
    mappings = get_mapping_by_device(data.device)
    entities: list[TuyaBLELock] = []
    for mapping in mappings:
        if mapping.force_add or data.device.datapoints.has_id(
            mapping.dp_id, mapping.dp_type
        ):
            entities.append(
                TuyaBLELock(
                    hass,
                    data.coordinator,
                    data.device,
                    data.product,
                    mapping,
                )
            )
    async_add_entities(entities)

