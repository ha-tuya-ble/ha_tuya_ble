"""The Tuya BLE integration."""

from __future__ import annotations

from dataclasses import dataclass, field

from homeassistant.components.lawn_mower import (
    LawnMowerActivity,
    LawnMowerEntity,
    LawnMowerEntityEntityDescription,
    LawnMowerEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, PARKSIDE_MOWER_COMMANDS, PARKSIDE_MOWER_STATUSES
from .devices import TuyaBLEData, TuyaBLEEntity, TuyaBLEProductInfo
from .tuya_ble import TuyaBLEDataPointType, TuyaBLEDevice

# Home Assistant has no idle activity, so every status in which the mower is
# neither cutting, returning nor faulted is reported as docked.
PARKSIDE_ACTIVITIES: dict[str, LawnMowerActivity] = {
    "STANDBY": LawnMowerActivity.DOCKED,
    "CHARGING": LawnMowerActivity.DOCKED,
    "MOWING": LawnMowerActivity.MOWING,
    "PAUSED": LawnMowerActivity.PAUSED,
    "PARK": LawnMowerActivity.RETURNING,
    "UPDATA": LawnMowerActivity.DOCKED,
    "FIXED_MOWING": LawnMowerActivity.MOWING,
    "ERROR": LawnMowerActivity.ERROR,
    "SELF_TEST": LawnMowerActivity.DOCKED,
    "CHARGING_WITH_TASK_SUSPEND": LawnMowerActivity.DOCKED,
    "EMERGENCY": LawnMowerActivity.ERROR,
    "LOCKED": LawnMowerActivity.DOCKED,
    "EDGE": LawnMowerActivity.MOWING,
}


@dataclass
class TuyaBLELawnMowerMapping:
    """Model the DPs and command values of a lawn mower"""

    dp_status: int
    """Read-only DP reporting the machine status."""
    dp_command: int
    """Write-only DP accepting the control commands."""
    status_values: list[str]
    """Status values, in the order declared by the device model."""
    command_values: list[str]
    """Command values, in the order declared by the device model."""
    activities: dict[str, LawnMowerActivity]
    """Maps a status value to the activity reported to Home Assistant."""
    start_command: str
    """Command that starts a mowing job."""
    resume_command: str
    """Command that resumes a paused mowing job."""
    pause_command: str
    """Command that pauses a running mowing job."""
    dock_command: str
    """Command that sends the mower back to its charging station."""
    command_dp_type: TuyaBLEDataPointType = TuyaBLEDataPointType.DT_ENUM
    """Type used to write the command DP. An enum carries the index of the
    value, DT_STRING writes the value itself for devices that expect that."""
    description: LawnMowerEntityEntityDescription = field(
        default_factory=lambda: LawnMowerEntityEntityDescription(key="lawn_mower")
    )


@dataclass
class TuyaBLECategoryLawnMowerMapping:
    products: dict[str, TuyaBLELawnMowerMapping] | None = None
    mapping: TuyaBLELawnMowerMapping | None = None


mapping: dict[str, TuyaBLECategoryLawnMowerMapping] = {
    "gcj": TuyaBLECategoryLawnMowerMapping(
        products={
            "9hdajpiw": TuyaBLELawnMowerMapping(
                dp_status=101,  # MachineStatus
                dp_command=115,  # MachineControlCmd
                status_values=PARKSIDE_MOWER_STATUSES,
                command_values=PARKSIDE_MOWER_COMMANDS,
                activities=PARKSIDE_ACTIVITIES,
                start_command="StartMowing",
                resume_command="ContinueWork",
                pause_command="PauseWork",
                dock_command="StartReturnStation",
            ),
        },
    ),
}


def get_mapping_by_device(device: TuyaBLEDevice) -> TuyaBLELawnMowerMapping | None:
    category = mapping.get(device.category)
    if category is None:
        return None
    if category.products is not None:
        product_mapping = category.products.get(device.product_id)
        if product_mapping is not None:
            return product_mapping

    return category.mapping


class TuyaBLELawnMower(TuyaBLEEntity, LawnMowerEntity):
    """Representation of a Tuya BLE lawn mower."""

    platform = Platform.LAWN_MOWER

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: DataUpdateCoordinator,
        device: TuyaBLEDevice,
        product: TuyaBLEProductInfo,
        mapping: TuyaBLELawnMowerMapping,
    ) -> None:
        super().__init__(hass, coordinator, device, product, mapping.description)
        self._mapping = mapping
        self._attr_supported_features = (
            LawnMowerEntityFeature.START_MOWING
            | LawnMowerEntityFeature.PAUSE
            | LawnMowerEntityFeature.DOCK
        )

    @property
    def _machine_status(self) -> str | None:
        """Return the reported status as a value of the device model."""
        datapoint = self._device.datapoints[self._mapping.dp_status]
        if datapoint is None:
            return None

        value = datapoint.value
        if isinstance(value, int) and 0 <= value < len(self._mapping.status_values):
            return self._mapping.status_values[value]

        return str(value) if value is not None else None

    @property
    def activity(self) -> LawnMowerActivity | None:
        """Return the activity the reported status maps to."""
        status = self._machine_status
        if status is None:
            return None

        return self._mapping.activities.get(status)

    def _send_control_command(self, command: str) -> None:
        """Write a control command to the command DP."""
        if self._mapping.command_dp_type == TuyaBLEDataPointType.DT_STRING:
            value: int | str = command
        else:
            value = self._mapping.command_values.index(command)

        datapoint = self._device.datapoints.get_or_create(
            self._mapping.dp_command,
            self._mapping.command_dp_type,
            value,
        )
        self._hass.create_task(datapoint.set_value(value))

    async def async_start_mowing(self) -> None:
        """Start mowing, or resume when paused."""
        # The mower rejects the start command while paused, it only accepts the
        # resume command in that state.
        if self.activity == LawnMowerActivity.PAUSED:
            self._send_control_command(self._mapping.resume_command)
        else:
            self._send_control_command(self._mapping.start_command)

    async def async_pause(self) -> None:
        """Pause mowing."""
        self._send_control_command(self._mapping.pause_command)

    async def async_dock(self) -> None:
        """Send the mower back to its charging station."""
        self._send_control_command(self._mapping.dock_command)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Tuya BLE lawn mowers."""
    data: TuyaBLEData = hass.data[DOMAIN][entry.entry_id]
    mower_mapping = get_mapping_by_device(data.device)
    if mower_mapping is None:
        return

    async_add_entities(
        [
            TuyaBLELawnMower(
                hass,
                data.coordinator,
                data.device,
                data.product,
                mower_mapping,
            )
        ]
    )
