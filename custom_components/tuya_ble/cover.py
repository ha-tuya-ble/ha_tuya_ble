"""The Tuya BLE integration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from datetime import datetime, timezone
from enum import IntEnum
import logging

from homeassistant.components.cover import (
    CoverEntityDescription,
    CoverEntityFeature,
    CoverEntity,
    STATE_CLOSED,
    STATE_OPEN,
    ATTR_POSITION,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .devices import TuyaBLEData, TuyaBLEEntity, TuyaBLEProductInfo
from .tuya_ble import TuyaBLEDataPointType, TuyaBLEDevice

_LOGGER = logging.getLogger(__name__)

TUYA_COVER_STATE_MAP = {0: STATE_OPEN, 2: STATE_CLOSED}


class TuyaCoverState(IntEnum):
    """State of cover"""

    OPEN = 0
    STOP = 1
    CLOSE = 2


@dataclass
class TuyaBLECoverMapping:
    """Model a DP, description and default values"""

    description: CoverEntityDescription

    cover_state_dp_id: int = 0
    cover_position_dp_id: int = 0
    cover_opening_mode_dp_id: int = 0
    cover_work_state_dp_id: int = 0
    cover_battery_dp_id: int = 0
    cover_motor_direction_dp_id: int = 0
    cover_set_upper_limit_dp_id: int = 0
    cover_factory_reset_dp_id: int = 0
    cover_position_set_dp: int = 0


@dataclass
class TuyaBLECategoryCoverMapping:
    """Models a dict of products and their mappings"""

    products: dict[str, list[TuyaBLECoverMapping]] | None = None
    mapping: list[TuyaBLECoverMapping] | None = None


# Blind Controller
# - [X] 1   - State (0=open, 1=stop, 2=close)
# - [X] 2   - Position (SET)
# - [X] 3   - Position (RAW)
# - [ ] 4   - Opening Mode
# - [ ] 5   - UNKNOWN?
# - [X] 7   - Work State (0=stdby, 1=success, 2=learning)
# - [X] 13  - Battery
# - [ ] 101 - Direction
# - [ ] 102 - Upper Limit
# - [ ] 103 - UNKNOWN? DT_BOOL
# - [ ] 104 - UNKNOWN? DT_BOOL
# - [X] 105 - Speed
# - [ ] 107 - Reset

# Curtain Controller
# - [X] 1   - State (0=open, 1=stop, 2=close)
# - [X] 2   - Position Set
# - [X] 3   - Position (RAW)
# - [X] 13  - Battery (RAW)


mapping: dict[str, TuyaBLECategoryCoverMapping] = {
    "cl": TuyaBLECategoryCoverMapping(
        products={
            **dict.fromkeys(
                ["4pbr8eig", "qqdxfdht", "ulughw4g"],
                [
                    TuyaBLECoverMapping(  # BLE Blind Controller
                        description=CoverEntityDescription(
                            key="ble_blind_controller",
                        ),
                        cover_state_dp_id=1,
                        cover_position_set_dp=2,
                        cover_position_dp_id=3,
                        cover_opening_mode_dp_id=4,
                        cover_work_state_dp_id=7,
                        cover_battery_dp_id=13,
                        cover_motor_direction_dp_id=101,
                        cover_set_upper_limit_dp_id=102,
                        cover_factory_reset_dp_id=107,
                    )
                ],
            ),
            "kcy0x4pi": [
                TuyaBLECoverMapping(
                    description=CoverEntityDescription(key="ble_curtain_controller"),
                    cover_state_dp_id=1,
                    cover_position_set_dp=2,
                    cover_position_dp_id=3,
                    cover_battery_dp_id=13,
                )
            ],
        },
    ),
}


def get_mapping_by_device(device: TuyaBLEDevice) -> list[TuyaBLECategoryCoverMapping]:
    """For a given device, work out the category cover mapping"""
    category = mapping.get(device.category)
    if category is not None and category.products is not None:
        product_mapping = category.products.get(device.product_id)
        if product_mapping is not None:
            return product_mapping
        if category.mapping is not None:
            return category.mapping

    return []


class TuyaBLECover(TuyaBLEEntity, CoverEntity):
    """Representation of a Tuya BLE Cover."""

    _attr_is_closed = False
    _attr_current_cover_position = 0

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
    def supported_features(self) -> CoverEntityFeature:
        """Return the supported features of the device."""
        return (
            CoverEntityFeature.CLOSE
            | CoverEntityFeature.OPEN
            | CoverEntityFeature.SET_POSITION
            | CoverEntityFeature.STOP
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug(
            "Updated data for %s: %s",
            self._device.name,
            self._device.datapoints.__dict__(),
        )
        if self._mapping.cover_state_dp_id != 0:
            datapoint = self._device.datapoints[self._mapping.cover_state_dp_id]
            if datapoint:
                self._attr_is_opening = False
                self._attr_is_closing = False
                match datapoint.value:
                    case 0:
                        self._attr_is_opening = True
                    case 1:
                        # Do nothing as it stopped
                        pass
                    case 2:
                        self._attr_is_closing = True

        if self._mapping.cover_position_dp_id != 0:
            datapoint = self._device.datapoints[self._mapping.cover_position_dp_id]
            if datapoint:
                self._attr_current_cover_position = 100 - int(
                    datapoint.value
                )  # reverse position
                if self._attr_current_cover_position == 0:
                    self._attr_is_closed = True
                    self._attr_is_closing = False
                else:
                    self._attr_is_closed = False

                if self._attr_current_cover_position == 100:
                    self._attr_is_opening = False

        self.async_write_ha_state()

    async def async_open_cover(self, **kwargs) -> None:
        """Open a cover."""
        await self._update_cover_state(TuyaCoverState.OPEN)

    async def async_stop_cover(self, **kwargs: logging.Any) -> None:
        """Stop a cover."""
        await self._update_cover_state(TuyaCoverState.STOP)

    async def async_close_cover(self, **kwargs) -> None:
        """Set new target temperature."""
        await self._update_cover_state(TuyaCoverState.CLOSE)

    async def _update_cover_state(self, state: TuyaCoverState) -> None:
        if self._mapping.cover_state_dp_id != 0:
            # In some circumstances (presumably due to a communication error in between where packets were lost)
            # It can be the case that the device does not update the state of the cover and does not accept new commands.
            # This is why a timer is here to verify that the state is updated and to manually request the status update
            # if no new data has come in within 1 second as it points to a communication error (as happened in tests with
            # the kcy0x4pi product).
            self._hass.add_job(
                self._validate_data_update_from_device_and_reconnect_if_needed(
                    time_now=datetime.now(timezone.utc)
                )
            )
            self._update_cover_state_without_validation(state)
            self._update_ha_state_for_cover_state(state)

    def _update_cover_state_without_validation(self, state: TuyaCoverState) -> None:
        if self._mapping.cover_state_dp_id != 0:
            datapoint = self._device.datapoints.get_or_create(
                self._mapping.cover_state_dp_id,
                TuyaBLEDataPointType.DT_VALUE,
                state.value,
            )
            if datapoint:
                self._hass.create_task(datapoint.set_value(state.value))

    async def _validate_data_update_from_device_and_reconnect_if_needed(
        self,
        sleep_ms: int = 1000,
        time_now: datetime | None = None,
    ) -> None:
        time_now = time_now or datetime.now(timezone.utc)
        await asyncio.sleep(sleep_ms / 1000.0)
        if self._device._is_paired and (
            not self._device.last_data_received
            or self._device.last_data_received < time_now
        ):
            _LOGGER.warning(
                "No data received from device (cover) %s within %dms, manually requesting status update",
                self._device.name,
                sleep_ms,
            )
            await self._device.update()

    def _update_ha_state_for_cover_state(self, state: TuyaCoverState) -> None:
        # sometimes the device does not update DP 1 so force the current state
        self._attr_is_closed = False
        self._attr_is_closing = False
        self._attr_is_opening = False

        if self._attr_current_cover_position == 0:
            self._attr_is_closed = True

        if state == TuyaCoverState.OPEN and self._attr_current_cover_position != 100:
            self._attr_is_opening = True
        elif state == TuyaCoverState.CLOSE and self._attr_current_cover_position != 0:
            self._attr_is_closing = True
        self.async_write_ha_state()

    async def async_set_cover_position(self, **kwargs: logging.Any) -> None:
        """Set cover position"""
        position = 100 - kwargs[ATTR_POSITION]
        if self._mapping.cover_position_set_dp != 0:
            datapoint = self._device.datapoints.get_or_create(
                self._mapping.cover_position_set_dp,
                TuyaBLEDataPointType.DT_VALUE,
                position,
            )
            if datapoint:
                self._hass.create_task(datapoint.set_value(position))


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
