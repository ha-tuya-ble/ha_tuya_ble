from __future__ import annotations

from typing import Any

from homeassistant.components.lock import (
    LockEntity,
    LockEntityFeature,
    LockEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
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
    """Set up the Tuya BLE sensors."""
    data: TuyaBLEData = hass.data[DOMAIN][entry.entry_id]
    product = get_device_product_info(data.device)
    if product and product.lock:
        async_add_entities([TuyaBLELock(hass, data.coordinator, data.device, product)])


class TuyaBLELock(TuyaBLEEntity, LockEntity):
    platform = Platform.LOCK

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: TuyaBLECoordinator,
        device: TuyaBLEDevice,
        product: TuyaBLEProductInfo,
    ) -> None:
        super().__init__(
            hass,
            coordinator,
            device,
            product,
            LockEntityDescription(key="lock", name=product.name),
        )
        self._attr_supported_features = LockEntityFeature.OPEN

    @property
    def is_locked(self) -> bool | None:
        """Return true if lock is locked."""
        dpid = self.find_dpid(DPCode.LOCK_MOTOR_STATE)
        if dpid is None:
            dpid = DPCode.LOCK_MOTOR_STATE
        if motor_state := self._device.datapoints.get_or_create(
            dpid, TuyaBLEDataPointType.DT_BOOL, False
        ):
            return not motor_state.value
        return None

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the lock."""
        manual_lock_id = self.find_dpid(DPCode.MANUAL_LOCK)
        if manual_lock_id is not None:
            if manual_lock := self._device.datapoints.get_or_create(
                manual_lock_id, TuyaBLEDataPointType.DT_BOOL, True
            ):
                await manual_lock.set_value(True)
        elif self.find_dpid(DPCode.LOCK_MOTOR_STATE) is not None:
            if motor_state := self._device.datapoints.get_or_create(
                self.find_dpid(DPCode.LOCK_MOTOR_STATE),
                TuyaBLEDataPointType.DT_BOOL,
                False,
            ):
                await motor_state.set_value(False)
        elif self._device.product_id == "wgv4haro":
            # Guard Dog Security Smart Lock locks automatically, locking command is no-op
            # NOTE: Other momentary locks in category ms/jtmspro (like okkyfgfs, k53ok3u9,
            # sidhzylo, a6nttc41, stugc8dl, xicdxood, rlyxv7pe, oyqux5vv, hs21i377, kholoaew)
            # may also need updating in the future.
            return
        else:
            if manual_lock := self._device.datapoints.get_or_create(
                DPCode.MANUAL_LOCK, TuyaBLEDataPointType.DT_BOOL, True
            ):
                await manual_lock.set_value(True)

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the lock."""
        manual_lock_id = self.find_dpid(DPCode.MANUAL_LOCK)
        if manual_lock_id is not None:
            if manual_lock := self._device.datapoints.get_or_create(
                manual_lock_id, TuyaBLEDataPointType.DT_BOOL, False
            ):
                await manual_lock.set_value(False)
        elif self.find_dpid(DPCode.LOCK_MOTOR_STATE) is not None:
            if motor_state := self._device.datapoints.get_or_create(
                self.find_dpid(DPCode.LOCK_MOTOR_STATE),
                TuyaBLEDataPointType.DT_BOOL,
                True,
            ):
                await motor_state.set_value(True)
        elif self._device.product_id == "wgv4haro":
            # Guard Dog Security Smart Lock uses DP 6 for bluetooth unlock
            # NOTE: Other momentary locks (e.g. okkyfgfs, k53ok3u9, sidhzylo, a6nttc41 on DP 6;
            # or stugc8dl, xicdxood, rlyxv7pe, oyqux5vv, hs21i377, kholoaew on DP 71)
            # may also need updating in the future.
            if bluetooth_unlock := self._device.datapoints.get_or_create(
                6, TuyaBLEDataPointType.DT_BOOL, False
            ):
                await bluetooth_unlock.set_value(True)
        else:
            if manual_lock := self._device.datapoints.get_or_create(
                DPCode.MANUAL_LOCK, TuyaBLEDataPointType.DT_BOOL, False
            ):
                await manual_lock.set_value(False)

    async def async_open(self, **kwargs: Any) -> None:
        """Open the covering."""
        await self.async_unlock(**kwargs)
