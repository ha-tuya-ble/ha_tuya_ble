"""Tuya BLE vacuum platform.

Supports robotic window cleaners, floor robot vacuums and similar devices.

To add a new device, add an entry to the `mapping` dict below following this pattern:

    "your_category": TuyaBLECategoryVacuumMapping(
        products={
            "your_product_id": TuyaBLEVacuumMapping(
                # -- Required: at least one of dp_start_bool or dp_start_enum --
                dp_start_bool=1,     # bool DP that starts (True) / stops (False)
                # -- or --
                dp_start_enum=...,   # enum DP: set start_enum_value to start
                start_enum_value=.., # value to send for "start"
                stop_enum_value=..., # value to send for "stop"

                # -- Optional DPs --
                dp_status=4,         # enum/str (RO) – current running state
                dp_mode=2,           # enum – cleaning mode selector
                dp_pause=...,        # separate pause DP (int index or bool)
                dp_return_home=...,  # separate return-to-base DP

                # -- Status value → HA VacuumActivity mapping --
                status_map={
                    "standby": VacuumActivity.IDLE,
                    "cleaning": VacuumActivity.CLEANING,
                    "charge":   VacuumActivity.DOCKED,
                    ...
                },

                # -- Cleaning modes shown in HA (fan_speed_list) --
                fan_speed_list=["auto", "max", "quiet"],
            ),
        },
    ),

All fields except the start DP are optional; features are enabled automatically
based on which DPs are configured.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    StateVacuumEntityDescription,
    VacuumEntityFeature,
    VacuumActivity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import Platform

from .const import DOMAIN
from .devices import TuyaBLEData, TuyaBLEEntity, TuyaBLEProductInfo
from .tuya_ble import TuyaBLEDataPointType, TuyaBLEDevice

_LOGGER = logging.getLogger(__name__)

# Window cleaner robot status values
STATUS_MAP_WINDOW_CLEANER: dict[str, VacuumActivity] = {
    "standby": VacuumActivity.IDLE,
    "cleaning": VacuumActivity.CLEANING,
    "smart_clean": VacuumActivity.CLEANING,
    "z_clean": VacuumActivity.CLEANING,
    "n_clean": VacuumActivity.CLEANING,
    "edge_clean": VacuumActivity.CLEANING,
    "spot_clean": VacuumActivity.CLEANING,
    "pause": VacuumActivity.PAUSED,
    "stop": VacuumActivity.IDLE,
    "charge": VacuumActivity.DOCKED,
}

# Generic floor robot vacuum status values (common Tuya convention)
STATUS_MAP_ROBOT_VACUUM: dict[str, VacuumActivity] = {
    "standby": VacuumActivity.IDLE,
    "random": VacuumActivity.CLEANING,
    "smart": VacuumActivity.CLEANING,
    "wall_follow": VacuumActivity.CLEANING,
    "mop": VacuumActivity.CLEANING,
    "spiral": VacuumActivity.CLEANING,
    "left_spiral": VacuumActivity.CLEANING,
    "right_spiral": VacuumActivity.CLEANING,
    "partial_bow": VacuumActivity.CLEANING,
    "cleaning": VacuumActivity.CLEANING,
    "paused": VacuumActivity.PAUSED,
    "pause": VacuumActivity.PAUSED,
    "docking": VacuumActivity.RETURNING,
    "returning": VacuumActivity.RETURNING,
    "charging": VacuumActivity.DOCKED,
    "charged": VacuumActivity.DOCKED,
    "charge": VacuumActivity.DOCKED,
    "sleep": VacuumActivity.IDLE,
    "fault": VacuumActivity.ERROR,
}


@dataclass
class TuyaBLEVacuumMapping:
    """Defines how a Tuya BLE vacuum device maps to HA vacuum entity.

    At minimum, one of dp_start_bool or dp_start_enum must be provided.
    All other fields are optional; features are enabled automatically.
    """

    # -- Start/Stop control (choose one) --
    dp_start_bool: int | None = None
    """DP id of a bool datapoint: True = start, False = stop."""

    dp_start_enum: int | None = None
    """DP id of an enum datapoint used for start/stop/pause."""
    start_enum_value: int = 0
    """Enum index to send for 'start'."""
    stop_enum_value: int | None = None
    """Enum index to send for 'stop' (None = same as start off)."""
    pause_enum_value: int | None = None
    """Enum index to send for 'pause' via dp_start_enum."""

    # -- Optional control DPs --
    dp_status: int | None = None
    """Read-only DP reporting current device status (enum or string)."""
    dp_mode: int | None = None
    """Enum DP for cleaning mode (shown as fan_speed in HA)."""
    dp_pause: int | None = None
    """Separate bool DP for pause (if device has one)."""
    dp_return_home: int | None = None
    """Separate DP to command return-to-base."""
    return_home_value: Any = True
    """Value to send on dp_return_home DP."""

    # -- Status mapping --
    status_map: dict[str, VacuumActivity] = field(
        default_factory=lambda: dict(STATUS_MAP_WINDOW_CLEANER)
    )
    """Maps device status string values to HA VacuumActivity states."""

    # -- Cleaning modes --
    fan_speed_list: list[str] = field(
        default_factory=lambda: ["smart", "z_mode", "n_mode", "edge", "spot"]
    )
    """List of cleaning mode strings shown as fan speeds in HA."""

    # -- Entity description --
    description: StateVacuumEntityDescription = field(
        default_factory=lambda: StateVacuumEntityDescription(key="vacuum")
    )


@dataclass
class TuyaBLECategoryVacuumMapping:
    """Per-category vacuum mapping container."""

    products: dict[str, TuyaBLEVacuumMapping] | None = None
    mapping: TuyaBLEVacuumMapping | None = None


# ---------------------------------------------------------------------------
# Device mapping database
# ---------------------------------------------------------------------------

mapping: dict[str, TuyaBLECategoryVacuumMapping] = {
    "cxjmb": TuyaBLECategoryVacuumMapping(
        products={
            "pnxl0r3l": TuyaBLEVacuumMapping(  # CHYW200.ABIR
                dp_start_bool=1,  # switch_go (bool)
                dp_mode=2,  # mode (enum): smart/z_mode/n_mode/edge/spot
                dp_status=4,  # status (enum, RO)
                # dp_direction handled separately via select entity (select.py)
                status_map=STATUS_MAP_WINDOW_CLEANER,
                fan_speed_list=["smart", "z_mode", "n_mode", "edge", "spot"],
            ),
        },
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tuya BLE vacuum entities."""
    data: TuyaBLEData = hass.data[DOMAIN][entry.entry_id]
    vac_mapping = _get_mapping(data.device)
    if vac_mapping is None:
        return

    async_add_entities(
        [
            TuyaBLEVacuumEntity(
                hass, data.coordinator, data.device, data.product, vac_mapping
            )
        ]
    )


def _get_mapping(device: TuyaBLEDevice) -> TuyaBLEVacuumMapping | None:
    """Resolve mapping by category+product_id, with product_id-only fallback."""
    cat = mapping.get(device.category)
    if cat is not None:
        if cat.products:
            result = cat.products.get(device.product_id)
            if result is not None:
                return result
        if cat.mapping is not None:
            return cat.mapping

    # Fallback: scan all categories by product_id (handles unknown BLE category)
    for cat_info in mapping.values():
        if cat_info.products:
            result = cat_info.products.get(device.product_id)
            if result is not None:
                return result

    return None


class TuyaBLEVacuumEntity(TuyaBLEEntity, StateVacuumEntity):
    """Tuya BLE vacuum / window cleaner robot entity."""

    platform = Platform.VACUUM

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: Any,
        device: TuyaBLEDevice,
        product: TuyaBLEProductInfo,
        vac_mapping: TuyaBLEVacuumMapping,
    ) -> None:
        super().__init__(hass, coordinator, device, product, vac_mapping.description)
        self._vac = vac_mapping

        # Build supported features dynamically from configured DPs
        features = VacuumEntityFeature.STATE
        if (
            vac_mapping.dp_start_bool is not None
            or vac_mapping.dp_start_enum is not None
        ):
            features |= VacuumEntityFeature.START | VacuumEntityFeature.STOP
        if vac_mapping.dp_pause is not None or vac_mapping.pause_enum_value is not None:
            features |= VacuumEntityFeature.PAUSE
        if vac_mapping.dp_return_home is not None:
            features |= VacuumEntityFeature.RETURN_HOME
        if vac_mapping.dp_mode is not None:
            features |= VacuumEntityFeature.FAN_SPEED

        self._attr_supported_features = features
        self._attr_fan_speed_list = list(vac_mapping.fan_speed_list)

    # ------------------------------------------------------------------ helpers

    def _dp_value(self, dp_id: int | None) -> Any:
        if dp_id is None:
            return None
        dp = self._device.datapoints[dp_id]
        return dp.value if dp else None

    def _send_bool(self, dp_id: int, value: bool) -> None:
        dp = self._device.datapoints.get_or_create(
            dp_id, TuyaBLEDataPointType.DT_BOOL, value
        )
        self._hass.create_task(dp.set_value(value))

    def _send_enum(self, dp_id: int, value: int) -> None:
        dp = self._device.datapoints.get_or_create(
            dp_id, TuyaBLEDataPointType.DT_ENUM, value
        )
        self._hass.create_task(dp.set_value(value))

    def _send_start(self) -> None:
        if self._vac.dp_start_bool is not None:
            self._send_bool(self._vac.dp_start_bool, True)
        elif self._vac.dp_start_enum is not None:
            self._send_enum(self._vac.dp_start_enum, self._vac.start_enum_value)

    def _send_stop(self) -> None:
        if self._vac.dp_start_bool is not None:
            self._send_bool(self._vac.dp_start_bool, False)
        elif (
            self._vac.dp_start_enum is not None
            and self._vac.stop_enum_value is not None
        ):
            self._send_enum(self._vac.dp_start_enum, self._vac.stop_enum_value)

    # --------------------------------------------------------------- HA state

    @property
    def activity(self) -> VacuumActivity | None:
        """Derive activity from status DP, falling back to start DP."""
        raw = self._dp_value(self._vac.dp_status)

        if raw is None:
            # No status DP — infer from start bool
            on = self._dp_value(self._vac.dp_start_bool)
            return VacuumActivity.CLEANING if on else VacuumActivity.IDLE

        # BLE enums arrive as int index — convert via status_map key order
        if isinstance(raw, int):
            keys = list(self._vac.status_map.keys())
            if 0 <= raw < len(keys):
                raw = keys[raw]

        return self._vac.status_map.get(str(raw), VacuumActivity.IDLE)

    @property
    def fan_speed(self) -> str | None:
        """Return current cleaning mode."""
        raw = self._dp_value(self._vac.dp_mode)
        if raw is None:
            return None
        if isinstance(raw, int):
            lst = self._vac.fan_speed_list
            if 0 <= raw < len(lst):
                return lst[raw]
        return str(raw)

    # -------------------------------------------------------------- HA actions

    async def async_start(self) -> None:
        self._send_start()

    async def async_stop(self, **kwargs: Any) -> None:
        self._send_stop()

    async def async_pause(self) -> None:
        if self._vac.dp_pause is not None:
            self._send_bool(self._vac.dp_pause, True)
        elif (
            self._vac.pause_enum_value is not None
            and self._vac.dp_start_enum is not None
        ):
            self._send_enum(self._vac.dp_start_enum, self._vac.pause_enum_value)
        else:
            self._send_stop()

    async def async_return_to_base(self, **kwargs: Any) -> None:
        if self._vac.dp_return_home is not None:
            val = self._vac.return_home_value
            if isinstance(val, bool):
                self._send_bool(self._vac.dp_return_home, val)
            else:
                self._send_enum(self._vac.dp_return_home, int(val))
        else:
            self._send_stop()

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        if self._vac.dp_mode is None:
            return
        lst = self._vac.fan_speed_list
        idx = lst.index(fan_speed) if fan_speed in lst else 0
        self._send_enum(self._vac.dp_mode, idx)
        # Start cleaning when mode selected
        self._send_start()
