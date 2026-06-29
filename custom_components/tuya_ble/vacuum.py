"""Tuya BLE vacuum (window cleaner robot) platform."""

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

from .const import DOMAIN, DPCode
from .devices import TuyaBLEData, TuyaBLEEntity, TuyaBLEProductInfo
from .tuya_ble import TuyaBLEDataPointType, TuyaBLEDevice

_LOGGER = logging.getLogger(__name__)

# Mapping from Tuya status DP values to HA VacuumActivity states
TUYA_STATUS_TO_HA: dict[str, VacuumActivity] = {
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

# Cleaning modes available
WINDOW_CLEANER_MODES = ["smart", "z_mode", "n_mode", "edge", "spot"]

# Friendly names for modes (displayed in HA)
MODE_LABELS: dict[str, str] = {
    "smart": "Smart",
    "z_mode": "Z-Mode",
    "n_mode": "N-Mode",
    "edge": "Edge",
    "spot": "Spot",
}


@dataclass
class TuyaBLEVacuumMapping:
    """Mapping of Tuya BLE DPs for a vacuum device."""

    dp_switch_go: int  # bool – start/stop cleaning
    dp_mode: int       # enum – cleaning mode
    dp_status: int     # enum (RO) – current status
    dp_direction: int  # enum – direction control
    description: StateVacuumEntityDescription = field(
        default_factory=lambda: StateVacuumEntityDescription(key="vacuum")
    )


@dataclass
class TuyaBLECategoryVacuumMapping:
    """Per-category vacuum mappings."""

    products: dict[str, TuyaBLEVacuumMapping] | None = None
    mapping: TuyaBLEVacuumMapping | None = None


# Category → product → mapping
mapping: dict[str, TuyaBLECategoryVacuumMapping] = {
    "cxjmb": TuyaBLECategoryVacuumMapping(
        products={
            "pnxl0r3l": TuyaBLEVacuumMapping(
                dp_switch_go=1,   # switch_go  (bool)
                dp_mode=2,        # mode       (enum)
                dp_status=4,      # status     (enum, RO)
                dp_direction=3,   # direction_control (enum)
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
    category = data.device.category
    cat_mapping = mapping.get(category)
    vac_mapping: TuyaBLEVacuumMapping | None = None

    if cat_mapping is not None:
        if cat_mapping.products:
            vac_mapping = cat_mapping.products.get(data.device.product_id)
        if vac_mapping is None and cat_mapping.mapping is not None:
            vac_mapping = cat_mapping.mapping

    # Fallback: scan all categories by product_id (handles unknown category)
    if vac_mapping is None:
        for cat_info in mapping.values():
            if cat_info.products:
                vac_mapping = cat_info.products.get(data.device.product_id)
                if vac_mapping is not None:
                    break

    if vac_mapping is None:
        return

    async_add_entities(
        [
            TuyaBLEVacuumEntity(
                hass,
                data.coordinator,
                data.device,
                data.product,
                vac_mapping,
            )
        ]
    )


class TuyaBLEVacuumEntity(TuyaBLEEntity, StateVacuumEntity):
    """Tuya BLE window cleaner robot as a vacuum entity."""

    _attr_supported_features = (
        VacuumEntityFeature.START
        | VacuumEntityFeature.STOP
        | VacuumEntityFeature.PAUSE
        | VacuumEntityFeature.RETURN_HOME
        | VacuumEntityFeature.FAN_SPEED
        | VacuumEntityFeature.STATE
    )
    _attr_fan_speed_list = WINDOW_CLEANER_MODES

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

    # ------------------------------------------------------------------ helpers

    def _get_dp_value(self, dp_id: int) -> Any:
        dp = self._device.datapoints[dp_id]
        return dp.value if dp else None

    def _send_bool(self, dp_id: int, value: bool) -> None:
        dp = self._device.datapoints.get_or_create(dp_id, TuyaBLEDataPointType.DT_BOOL, value)
        self._hass.create_task(dp.set_value(value))

    def _send_enum(self, dp_id: int, options: list[str], value: str) -> None:
        int_value = options.index(value) if value in options else 0
        dp = self._device.datapoints.get_or_create(dp_id, TuyaBLEDataPointType.DT_ENUM, int_value)
        self._hass.create_task(dp.set_value(int_value))

    # --------------------------------------------------------------- HA states

    @property
    def activity(self) -> VacuumActivity | None:
        """Return current activity based on status DP."""
        status = self._get_dp_value(self._vac.dp_status)
        if status is None:
            # Fall back to switch_go
            is_on = self._get_dp_value(self._vac.dp_switch_go)
            if is_on:
                return VacuumActivity.CLEANING
            return VacuumActivity.IDLE
        if isinstance(status, int):
            # BLE enum arrives as int index
            status_list = list(TUYA_STATUS_TO_HA.keys())
            if 0 <= status < len(status_list):
                status = status_list[status]
        return TUYA_STATUS_TO_HA.get(str(status), VacuumActivity.IDLE)

    @property
    def fan_speed(self) -> str | None:
        """Return current cleaning mode (shown as fan speed)."""
        mode = self._get_dp_value(self._vac.dp_mode)
        if mode is None:
            return None
        if isinstance(mode, int) and 0 <= mode < len(WINDOW_CLEANER_MODES):
            return WINDOW_CLEANER_MODES[mode]
        return str(mode)

    # -------------------------------------------------------------- HA actions

    async def async_start(self) -> None:
        """Start cleaning."""
        self._send_bool(self._vac.dp_switch_go, True)

    async def async_stop(self, **kwargs: Any) -> None:
        """Stop cleaning."""
        self._send_bool(self._vac.dp_switch_go, False)

    async def async_pause(self) -> None:
        """Pause cleaning by stopping (no separate pause DP)."""
        self._send_bool(self._vac.dp_switch_go, False)

    async def async_return_to_base(self, **kwargs: Any) -> None:
        """Return to charging dock – stop the device."""
        self._send_bool(self._vac.dp_switch_go, False)

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        """Set cleaning mode via the mode DP."""
        self._send_enum(self._vac.dp_mode, WINDOW_CLEANER_MODES, fan_speed)
        # Also start cleaning when a mode is selected
        self._send_bool(self._vac.dp_switch_go, True)
