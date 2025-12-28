from __future__ import annotations

from typing import Any

from homeassistant.components.lock import LockEntity, LockEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DPCode
from .devices import (
    TuyaBLEData,
    TuyaBLEEntity,
    TuyaBLEProductInfo,
    TuyaBLECoordinator,
    get_device_product_info,
)
from .tuya_ble import TuyaBLEDataPointType, TuyaBLEDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Tuya BLE Locks."""
    data: TuyaBLEData = hass.data[DOMAIN][entry.entry_id]
    entities: list[TuyaBLELock] = []

    product = get_device_product_info(data.device)
    if product and product.lock == 1:
        entities.append([TuyaBLELock(hass, data.coordinator, data.device, product)])

    async_add_entities(entities)


class TuyaBLELock(TuyaBLEEntity, LockEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: TuyaBLECoordinator,
        device: TuyaBLEDevice,
        product: TuyaBLEProductInfo,
    ) -> None:
        super().__init__(hass, coordinator, device, product, None)
        self._attr_supported_features = LockEntityFeature.OPEN

    @property
    def is_locked(self) -> bool | None:
        """Return true if lock is locked."""
        if motor_state := self._device.datapoints.get_or_create(
            DPCode.LOCK_MOTOR_STATE, TuyaBLEDataPointType.DT_BOOL, False
        ):
            return not motor_state.value
        return None

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the lock."""
        if manual_lock := self._device.datapoints.get_or_create(
            DPCode.MANUAL_LOCK, TuyaBLEDataPointType.DT_BOOL, True
        ):
            await manual_lock.set_value(True)

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the lock."""
        if manual_lock := self._device.datapoints.get_or_create(
            DPCode.MANUAL_LOCK, TuyaBLEDataPointType.DT_BOOL, False
        ):
            await manual_lock.set_value(False)

    async def async_open(self, **kwargs: Any) -> None:
        """Open the covering."""
        if manual_lock := self._device.datapoints.get_or_create(
            DPCode.MANUAL_LOCK, TuyaBLEDataPointType.DT_BOOL, False
        ):
            await manual_lock.set_value(False)
