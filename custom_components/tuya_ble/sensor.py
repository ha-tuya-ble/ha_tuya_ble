"""The Tuya BLE integration."""

from __future__ import annotations
from dataclasses import dataclass, field
import logging
from typing import Callable
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolume,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import (
    BATTERY_STATE_HIGH,
    BATTERY_STATE_LOW,
    BATTERY_STATE_NORMAL,
    BATTERY_CHARGED,
    BATTERY_CHARGING,
    BATTERY_NOT_CHARGING,
    CO2_LEVEL_ALARM,
    CO2_LEVEL_NORMAL,
    DOMAIN,
)
from .devices import TuyaBLEData, TuyaBLEEntity, TuyaBLEProductInfo
from .tuya_ble import TuyaBLEDataPointType, TuyaBLEDevice

_LOGGER = logging.getLogger(__name__)
SIGNAL_STRENGTH_DP_ID = -1
TuyaBLESensorIsAvailable = Callable[["TuyaBLESensor", TuyaBLEProductInfo], bool] | None


@dataclass
class TuyaBLESensorMapping:
    """Model a DP, description and default values"""

    dp_id: int
    description: SensorEntityDescription
    force_add: bool = True
    dp_type: TuyaBLEDataPointType | None = None
    getter: Callable[[TuyaBLESensor], None] | None = None
    coefficient: float = 1.0
    icons: list[str] | None = None
    is_available: TuyaBLESensorIsAvailable = None


@dataclass
class TuyaBLEBatteryMapping(TuyaBLESensorMapping):
    description: SensorEntityDescription = field(
        default_factory=lambda: SensorEntityDescription(
            key="battery",
            device_class=SensorDeviceClass.BATTERY,
            native_unit_of_measurement=PERCENTAGE,
            entity_category=EntityCategory.DIAGNOSTIC,
            state_class=SensorStateClass.MEASUREMENT,
        )
    )


@dataclass
class TuyaBLETemperatureMapping(TuyaBLESensorMapping):
    description: SensorEntityDescription = field(
        default_factory=lambda: SensorEntityDescription(
            key="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            state_class=SensorStateClass.MEASUREMENT,
        )
    )


def is_co2_alarm_enabled(self: TuyaBLESensor, product: TuyaBLEProductInfo) -> bool:
    """For a given sensor, read the datapoints and determine if co2 alarm is enabled"""
    result: bool = True
    datapoint = self._device.datapoints[13]
    if datapoint:
        result = bool(datapoint.value)
    return result


def battery_enum_getter(self: TuyaBLESensor) -> None:
    """For a given sensor, read the datapoints and detemine battery info"""
    datapoint = self._device.datapoints[104]
    if datapoint:
        self._attr_native_value = datapoint.value * 20.0


@dataclass
class TuyaBLECategorySensorMapping:
    """Models a dict of products and their mappings"""

    products: dict[str, list[TuyaBLESensorMapping]] | None = None
    mapping: list[TuyaBLESensorMapping] | None = None


@dataclass
class TuyaBLEWorkStateMapping(TuyaBLESensorMapping):
    description: SensorEntityDescription = field(
        default_factory=lambda: SensorEntityDescription(
            key="work_state",
            device_class=SensorDeviceClass.ENUM,
            options=[
                "auto",
                "manual",
                "idle",
            ],
        )
    )


@dataclass
class TuyaBLEAlarmLockStateMapping(TuyaBLESensorMapping):
    description: SensorEntityDescription = field(
        default_factory=lambda: SensorEntityDescription(
            key="alarm_lock",
            device_class=SensorDeviceClass.ENUM,
            options=[
                "wrong_finger",
                "wrong_password",
                "wrong_card",
                "wrong_face",
                "tongue_bad",
                "too_hot",
                "unclosed_time",
                "tongue_not_out",
                "pry",
                "key_in",
                "low_battery",
                "power_off",
                "shock",
            ],
        )
    )


mapping: dict[str, TuyaBLECategorySensorMapping] = {
    "co2bj": TuyaBLECategorySensorMapping(
        products={
            "59s19z5m": [  # CO2 Detector
                TuyaBLESensorMapping(
                    dp_id=1,
                    description=SensorEntityDescription(
                        key="carbon_dioxide_alarm",
                        icon="mdi:molecule-co2",
                        device_class=SensorDeviceClass.ENUM,
                        options=[
                            CO2_LEVEL_ALARM,
                            CO2_LEVEL_NORMAL,
                        ],
                    ),
                    is_available=is_co2_alarm_enabled,
                ),
                TuyaBLESensorMapping(
                    dp_id=2,
                    description=SensorEntityDescription(
                        key="carbon_dioxide",
                        device_class=SensorDeviceClass.CO2,
                        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                ),
                TuyaBLEBatteryMapping(dp_id=15),
                TuyaBLETemperatureMapping(dp_id=18),
                TuyaBLESensorMapping(
                    dp_id=19,
                    description=SensorEntityDescription(
                        key="humidity",
                        device_class=SensorDeviceClass.HUMIDITY,
                        native_unit_of_measurement=PERCENTAGE,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                ),
            ]
        }
    ),
    "ms": TuyaBLECategorySensorMapping(
        products={
            **dict.fromkeys(
                [
                    "ludzroix",
                    "isk2p555",
                    "gumrixyt",
                    "uamrw6h3",
                    "okkyfgfs",
                    "bvclwu9b",
                    "k53ok3u9",
                ],  # Smart Lock
                [
                    TuyaBLEAlarmLockStateMapping(dp_id=21),
                    TuyaBLEBatteryMapping(dp_id=8),
                    TuyaBLESensorMapping(
                        dp_id=40,
                        description=SensorEntityDescription(
                            key="lock_door_status",
                            entity_category=EntityCategory.DIAGNOSTIC,
                            device_class=SensorDeviceClass.ENUM,
                            options=[
                                "door_status_unknown",
                                "door_status_open",
                                "door_status_closed",
                            ],
                        ),
                    ),
                ],
            ),
        }
    ),
    "jtmspro": TuyaBLECategorySensorMapping(
        products={
            "xicdxood": [  # Raycube K7 Pro+
                TuyaBLEAlarmLockStateMapping(dp_id=21),
                TuyaBLESensorMapping(
                    dp_id=12,  # Retrieve last fingerprint used
                    description=SensorEntityDescription(
                        key="unlock_fingerprint",
                        icon="mdi:fingerprint",
                    ),
                ),
                TuyaBLESensorMapping(
                    dp_id=15,  # Retrieve last card used
                    description=SensorEntityDescription(
                        key="unlock_card",
                        icon="mdi:nfc-variant",
                    ),
                ),
                TuyaBLESensorMapping(
                    dp_id=13,  # Retrieve last code used
                    description=SensorEntityDescription(
                        key="unlock_password",
                        icon="mdi:keyboard-outline",
                    ),
                ),
                TuyaBLEBatteryMapping(dp_id=8),
            ],
            "ajk32biq": [
                TuyaBLESensorMapping(
                    dp_id=21,
                    description=SensorEntityDescription(
                        key="alarm_lock",
                        device_class=SensorDeviceClass.ENUM,
                        options=[
                            "wrong_finger",
                            "wrong_password",
                            "wrong_card",
                            "wrong_face",
                            "tongue_bad",
                            "too_hot",
                            "unclosed_time",
                            "tongue_not_out",
                            "pry",
                            "key_in",
                            "low_battery",
                            "power_off",
                            "shock",
                        ],
                    ),
                ),
                TuyaBLEBatteryMapping(
                    dp_id=8,
                ),
            ],
        }
    ),
    "szjqr": TuyaBLECategorySensorMapping(
        products={
            **dict.fromkeys(
                ["3yqdo5yt", "xhf790if", "okkyfgfs"],  # CubeTouch 1s and II
                [
                    TuyaBLESensorMapping(
                        dp_id=7,
                        description=SensorEntityDescription(
                            key="battery_charging",
                            device_class=SensorDeviceClass.ENUM,
                            entity_category=EntityCategory.DIAGNOSTIC,
                            options=[
                                BATTERY_NOT_CHARGING,
                                BATTERY_CHARGING,
                                BATTERY_CHARGED,
                            ],
                        ),
                        icons=[
                            "mdi:battery",
                            "mdi:power-plug-battery",
                            "mdi:battery-check",
                        ],
                    ),
                    TuyaBLEBatteryMapping(dp_id=8),
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
                    TuyaBLEBatteryMapping(dp_id=12),
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
                    TuyaBLEBatteryMapping(dp_id=12),
                ],
            ),
        },
    ),
    "kg": TuyaBLECategorySensorMapping(
        products={
            **dict.fromkeys(
                ["mknd4lci", "riecov42"],  # Fingerbot Plus
                [
                    TuyaBLEBatteryMapping(dp_id=105),
                ],
            ),
        },
    ),
    "wsdcg": TuyaBLECategorySensorMapping(
        products={
            "ojzlzzsw": [  # Soil moisture sensor
                TuyaBLETemperatureMapping(
                    dp_id=1,
                    coefficient=10.0,
                ),
                TuyaBLESensorMapping(
                    dp_id=2,
                    description=SensorEntityDescription(
                        key="moisture",
                        device_class=SensorDeviceClass.MOISTURE,
                        native_unit_of_measurement=PERCENTAGE,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                ),
                TuyaBLESensorMapping(
                    dp_id=3,
                    description=SensorEntityDescription(
                        key="battery_state",
                        icon="mdi:battery",
                        device_class=SensorDeviceClass.ENUM,
                        entity_category=EntityCategory.DIAGNOSTIC,
                        options=[
                            BATTERY_STATE_LOW,
                            BATTERY_STATE_NORMAL,
                            BATTERY_STATE_HIGH,
                        ],
                    ),
                    icons=[
                        "mdi:battery-alert",
                        "mdi:battery-50",
                        "mdi:battery-check",
                    ],
                ),
                TuyaBLEBatteryMapping(dp_id=4),
            ],
            "iv7hudlj": [  # Bluetooth Temperature Humidity Sensor
                TuyaBLETemperatureMapping(
                    dp_id=1,
                    coefficient=10.0,
                    description=SensorEntityDescription(
                        key="va_temperature",
                        device_class=SensorDeviceClass.TEMPERATURE,
                        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                ),
                TuyaBLESensorMapping(
                    dp_id=2,
                    description=SensorEntityDescription(
                        key="va_moisture",
                        device_class=SensorDeviceClass.MOISTURE,
                        native_unit_of_measurement=PERCENTAGE,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                ),
                TuyaBLEBatteryMapping(
                    dp_id=4,
                    description=SensorEntityDescription(
                        key="battery_percentage",
                        device_class=SensorDeviceClass.BATTERY,
                        native_unit_of_measurement=PERCENTAGE,
                        entity_category=EntityCategory.DIAGNOSTIC,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                ),
            ],
            "jm6iasmb": [  # Bluetooth Temperature Humidity Sensor
                TuyaBLETemperatureMapping(
                    dp_id=1,
                    coefficient=10.0,
                    description=SensorEntityDescription(
                        key="va_temperature",
                        device_class=SensorDeviceClass.TEMPERATURE,
                        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                ),
                TuyaBLESensorMapping(
                    dp_id=2,
                    description=SensorEntityDescription(
                        key="va_moisture",
                        device_class=SensorDeviceClass.MOISTURE,
                        native_unit_of_measurement=PERCENTAGE,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                ),
                TuyaBLEBatteryMapping(
                    dp_id=4,
                    description=SensorEntityDescription(
                        key="battery_percentage",
                        device_class=SensorDeviceClass.BATTERY,
                        native_unit_of_measurement=PERCENTAGE,
                        entity_category=EntityCategory.DIAGNOSTIC,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                ),
            ],
            "tv6peegl": [  # Soil moisture sensor
                TuyaBLETemperatureMapping(
                    dp_id=101,
                ),
                TuyaBLESensorMapping(
                    dp_id=102,
                    description=SensorEntityDescription(
                        key="moisture",
                        device_class=SensorDeviceClass.MOISTURE,
                        native_unit_of_measurement=PERCENTAGE,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                ),
            ],
            "vlzqwckk": [
                TuyaBLETemperatureMapping(
                    dp_id=1,
                    coefficient=10.0,
                    description=SensorEntityDescription(
                        key="va_temperature",
                        device_class=SensorDeviceClass.TEMPERATURE,
                        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                ),
                TuyaBLESensorMapping(
                    dp_id=2,
                    description=SensorEntityDescription(
                        key="va_humidity",
                        device_class=SensorDeviceClass.HUMIDITY,
                        native_unit_of_measurement=PERCENTAGE,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                ),
                TuyaBLEBatteryMapping(
                    dp_id=4,
                    description=SensorEntityDescription(
                        key="battery_percentage",
                        device_class=SensorDeviceClass.BATTERY,
                        native_unit_of_measurement=PERCENTAGE,
                        entity_category=EntityCategory.DIAGNOSTIC,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                ),
            ],
        },
    ),
    "dcb": TuyaBLECategorySensorMapping(
        products={
            **dict.fromkeys(
                [
                    "z5ztlw3k",
                    "ajrhf1aj",
                ],  # PARKSIDE Smart battery
                [
                    TuyaBLEBatteryMapping(dp_id=16),
                    TuyaBLETemperatureMapping(dp_id=11),
                    TuyaBLESensorMapping(
                        dp_id=172,
                        description=SensorEntityDescription(
                            key="battery_temp_current",
                            device_class=SensorDeviceClass.TEMPERATURE,
                            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                            state_class=SensorStateClass.MEASUREMENT,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=102,
                        description=SensorEntityDescription(
                            key="battery_status",
                            device_class=SensorDeviceClass.ENUM,
                            options=[
                                "Ready",
                                "Charging",
                                "Discharging",
                                "Full",
                                "Sleep",
                                "Error",
                            ],
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=2,
                        description=SensorEntityDescription(
                            key="charge_current",
                            device_class=SensorDeviceClass.CURRENT,
                            native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
                            state_class=SensorStateClass.MEASUREMENT,
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=3,
                        description=SensorEntityDescription(
                            key="charge_voltage",
                            device_class=SensorDeviceClass.VOLTAGE,
                            native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
                            state_class=SensorStateClass.MEASUREMENT,
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=101,
                        description=SensorEntityDescription(
                            key="discharging_current",
                            device_class=SensorDeviceClass.CURRENT,
                            native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
                            state_class=SensorStateClass.MEASUREMENT,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=103,
                        description=SensorEntityDescription(
                            key="charge_to_full_time",
                            device_class=SensorDeviceClass.DURATION,
                            native_unit_of_measurement=UnitOfTime.MINUTES,
                            state_class=SensorStateClass.MEASUREMENT,
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=104,
                        description=SensorEntityDescription(
                            key="discharge_to_empty_time",
                            device_class=SensorDeviceClass.DURATION,
                            native_unit_of_measurement=UnitOfTime.SECONDS,
                            state_class=SensorStateClass.MEASUREMENT,
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=8,
                        description=SensorEntityDescription(
                            key="charge_times",
                            icon="mdi:counter",
                            state_class=SensorStateClass.TOTAL_INCREASING,
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=9,
                        description=SensorEntityDescription(
                            key="discharge_times",
                            icon="mdi:counter",
                            state_class=SensorStateClass.TOTAL_INCREASING,
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=14,
                        description=SensorEntityDescription(
                            key="use_time",
                            device_class=SensorDeviceClass.DURATION,
                            native_unit_of_measurement=UnitOfTime.MINUTES,
                            state_class=SensorStateClass.MEASUREMENT,
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=15,
                        description=SensorEntityDescription(
                            key="runtime_total",
                            device_class=SensorDeviceClass.DURATION,
                            native_unit_of_measurement=UnitOfTime.MINUTES,
                            state_class=SensorStateClass.TOTAL_INCREASING,
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=10,
                        description=SensorEntityDescription(
                            key="peak_current_times",
                            icon="mdi:counter",
                            state_class=SensorStateClass.TOTAL_INCREASING,
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=21,
                        description=SensorEntityDescription(
                            key="fault",
                            icon="mdi:alert-circle-outline",
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=107,
                        description=SensorEntityDescription(
                            key="over_voltage_times",
                            icon="mdi:counter",
                            state_class=SensorStateClass.TOTAL_INCREASING,
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=108,
                        description=SensorEntityDescription(
                            key="under_voltage_times",
                            icon="mdi:counter",
                            state_class=SensorStateClass.TOTAL_INCREASING,
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=109,
                        description=SensorEntityDescription(
                            key="overtemp_discharge_times",
                            icon="mdi:counter",
                            state_class=SensorStateClass.TOTAL_INCREASING,
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=110,
                        description=SensorEntityDescription(
                            key="overtemp_charge_times",
                            icon="mdi:counter",
                            state_class=SensorStateClass.TOTAL_INCREASING,
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=111,
                        description=SensorEntityDescription(
                            key="undertemp_discharge_times",
                            icon="mdi:counter",
                            state_class=SensorStateClass.TOTAL_INCREASING,
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=112,
                        description=SensorEntityDescription(
                            key="undertemp_charge_times",
                            icon="mdi:counter",
                            state_class=SensorStateClass.TOTAL_INCREASING,
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=113,
                        description=SensorEntityDescription(
                            key="short_circuit_times",
                            icon="mdi:counter",
                            state_class=SensorStateClass.TOTAL_INCREASING,
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=114,
                        description=SensorEntityDescription(
                            key="over_current_times",
                            icon="mdi:counter",
                            state_class=SensorStateClass.TOTAL_INCREASING,
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=19,
                        description=SensorEntityDescription(
                            key="product_type",
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=150,
                        description=SensorEntityDescription(
                            key="tool_product_type",
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=152,
                        description=SensorEntityDescription(
                            key="tool_rotation_speed",
                            icon="mdi:rotate-3d-variant",
                            state_class=SensorStateClass.MEASUREMENT,
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=153,
                        description=SensorEntityDescription(
                            key="tool_torque",
                            icon="mdi:screw-lag",
                            state_class=SensorStateClass.MEASUREMENT,
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=154,
                        description=SensorEntityDescription(
                            key="tool_runtime_total",
                            device_class=SensorDeviceClass.DURATION,
                            native_unit_of_measurement=UnitOfTime.MINUTES,
                            state_class=SensorStateClass.TOTAL_INCREASING,
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=156,
                        description=SensorEntityDescription(
                            key="tool_fault",
                            icon="mdi:alert-circle-outline",
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=157,
                        description=SensorEntityDescription(
                            key="tools_current",
                            device_class=SensorDeviceClass.CURRENT,
                            state_class=SensorStateClass.MEASUREMENT,
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=158,
                        description=SensorEntityDescription(
                            key="tool_ot_times",
                            state_class=SensorStateClass.TOTAL_INCREASING,
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=159,
                        description=SensorEntityDescription(
                            key="tool_locked_times",
                            state_class=SensorStateClass.TOTAL_INCREASING,
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=160,
                        description=SensorEntityDescription(
                            key="tool_oc_times",
                            state_class=SensorStateClass.TOTAL_INCREASING,
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    ),
                ],
            ),
        },
    ),
    "zwjcy": TuyaBLECategorySensorMapping(
        products={
            "gvygg3m8": [  # Smartlife Plant Sensor SGS01
                TuyaBLETemperatureMapping(
                    dp_id=5,
                    coefficient=10.0,
                    description=SensorEntityDescription(
                        key="temp_current",
                        device_class=SensorDeviceClass.TEMPERATURE,
                        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                ),
                TuyaBLESensorMapping(
                    dp_id=3,
                    description=SensorEntityDescription(
                        key="humidity",
                        device_class=SensorDeviceClass.HUMIDITY,
                        native_unit_of_measurement=PERCENTAGE,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                ),
                TuyaBLESensorMapping(
                    dp_id=14,
                    description=SensorEntityDescription(
                        key="battery_state",
                        icon="mdi:battery",
                        device_class=SensorDeviceClass.ENUM,
                        entity_category=EntityCategory.DIAGNOSTIC,
                        options=[
                            BATTERY_STATE_LOW,
                            BATTERY_STATE_NORMAL,
                            BATTERY_STATE_HIGH,
                        ],
                    ),
                    icons=[
                        "mdi:battery-alert",
                        "mdi:battery-50",
                        "mdi:battery-check",
                    ],
                ),
                TuyaBLEBatteryMapping(
                    dp_id=15,
                    description=SensorEntityDescription(
                        key="battery_percentage",
                        device_class=SensorDeviceClass.BATTERY,
                        native_unit_of_measurement=PERCENTAGE,
                        entity_category=EntityCategory.DIAGNOSTIC,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                ),
            ],
        },
    ),
    "znhsb": TuyaBLECategorySensorMapping(
        products={
            "cdlandip": [  # Smart water bottle
                TuyaBLETemperatureMapping(
                    dp_id=101,
                ),
                TuyaBLESensorMapping(
                    dp_id=102,
                    description=SensorEntityDescription(
                        key="water_intake",
                        device_class=SensorDeviceClass.WATER,
                        native_unit_of_measurement=UnitOfVolume.MILLILITERS,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                ),
                TuyaBLESensorMapping(
                    dp_id=104,
                    description=SensorEntityDescription(
                        key="battery",
                        device_class=SensorDeviceClass.BATTERY,
                        native_unit_of_measurement=PERCENTAGE,
                        entity_category=EntityCategory.DIAGNOSTIC,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                    getter=battery_enum_getter,
                ),
            ],
        },
    ),
    "ggq": TuyaBLECategorySensorMapping(
        products={
            "6pahkcau": [  # Irrigation computer PARKSIDE PPB A1
                TuyaBLEBatteryMapping(dp_id=11),
                TuyaBLESensorMapping(
                    dp_id=6,
                    description=SensorEntityDescription(
                        key="time_left",
                        device_class=SensorDeviceClass.DURATION,
                        native_unit_of_measurement=UnitOfTime.MINUTES,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                ),
            ],
            **dict.fromkeys(
                [
                    "hfgdqhho",
                    "qycalacn",
                    "fnlw6npo",
                    "jjqi2syk",
                ],  # Irrigation computer - dual outlet
                [
                    TuyaBLEBatteryMapping(dp_id=11),
                    TuyaBLESensorMapping(
                        dp_id=111,
                        description=SensorEntityDescription(
                            key="use_time_z1",
                            device_class=SensorDeviceClass.DURATION,
                            native_unit_of_measurement=UnitOfTime.SECONDS,
                            state_class=SensorStateClass.MEASUREMENT,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=110,
                        description=SensorEntityDescription(
                            key="use_time_z2",
                            device_class=SensorDeviceClass.DURATION,
                            native_unit_of_measurement=UnitOfTime.SECONDS,
                            state_class=SensorStateClass.MEASUREMENT,
                        ),
                    ),
                ],
            ),
        },
    ),
    "sfkzq": TuyaBLECategorySensorMapping(
        products={
            "0axr5s0b": [  # Valve Controller
                TuyaBLEBatteryMapping(dp_id=7),
                TuyaBLESensorMapping(
                    # dp_id=15,
                    dp_id=11,
                    description=SensorEntityDescription(
                        key="time_left",
                        device_class=SensorDeviceClass.DURATION,
                        native_unit_of_measurement=UnitOfTime.SECONDS,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                ),
            ],
            "hfgdqhho": [  # Irrigation computer - SGW02/SGW08
                TuyaBLEBatteryMapping(dp_id=11),
                TuyaBLESensorMapping(
                    # dp_id=15,
                    dp_id=11,
                    description=SensorEntityDescription(
                        key="time_left",
                        device_class=SensorDeviceClass.DURATION,
                        native_unit_of_measurement=UnitOfTime.SECONDS,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                ),
            ],
            **dict.fromkeys(
                ["46zia2nz", "1fcnd8xk", "nxquc5lb", "svhikeyq"],
                [
                    TuyaBLEBatteryMapping(dp_id=7),
                    TuyaBLEWorkStateMapping(dp_id=12),
                    TuyaBLESensorMapping(
                        dp_id=15,
                        description=SensorEntityDescription(
                            key="use_time_one",
                            device_class=SensorDeviceClass.DURATION,
                            native_unit_of_measurement=UnitOfTime.SECONDS,
                            state_class=SensorStateClass.MEASUREMENT,
                        ),
                    ),
                    TuyaBLESensorMapping(
                        dp_id=9,
                        description=SensorEntityDescription(
                            key="time_use",
                            device_class=SensorDeviceClass.DURATION,
                            native_unit_of_measurement=UnitOfTime.SECONDS,
                            state_class=SensorStateClass.MEASUREMENT,
                        ),
                    ),
                ],
            ),
        },
    ),
    "cl": TuyaBLECategorySensorMapping(
        products={
            **dict.fromkeys(
                ["4pbr8eig", "qqdxfdht", "kcy0x4pi", "vlwf3ud6"],  # Blind Controller
                [
                    TuyaBLEBatteryMapping(dp_id=13),
                    TuyaBLESensorMapping(
                        dp_id=7,
                        description=SensorEntityDescription(
                            key="cover_work_state",
                            entity_category=EntityCategory.DIAGNOSTIC,
                            device_class=SensorDeviceClass.ENUM,
                            options=["STANDBY", "SUCCESS", "LEARNING"],
                        ),
                    ),
                ],
            ),
        }
    ),
}


def rssi_getter(sensor: TuyaBLESensor) -> None:
    sensor._attr_native_value = sensor._device.rssi


rssi_mapping = TuyaBLESensorMapping(
    dp_id=SIGNAL_STRENGTH_DP_ID,
    description=SensorEntityDescription(
        key="signal_strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    getter=rssi_getter,
)


def get_mapping_by_device(device: TuyaBLEDevice) -> list[TuyaBLESensorMapping]:
    category = mapping.get(device.category)
    if category is not None and category.products is not None:
        product_mapping = category.products.get(device.product_id)
        if product_mapping is not None:
            return product_mapping
        if category.mapping is not None:
            return category.mapping

    return []


class TuyaBLESensor(TuyaBLEEntity, SensorEntity):
    """Representation of a Tuya BLE sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: DataUpdateCoordinator,
        device: TuyaBLEDevice,
        product: TuyaBLEProductInfo,
        mapping: TuyaBLESensorMapping,
    ) -> None:
        super().__init__(hass, coordinator, device, product, mapping.description)
        self._mapping = mapping

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self._mapping.getter is not None:
            self._mapping.getter(self)
        else:
            datapoint = self._device.datapoints[self._mapping.dp_id]
            if datapoint:
                if datapoint.type == TuyaBLEDataPointType.DT_ENUM:
                    if self.entity_description.options is not None:
                        if datapoint.value >= 0 and datapoint.value < len(
                            self.entity_description.options
                        ):
                            self._attr_native_value = self.entity_description.options[
                                datapoint.value
                            ]
                        else:
                            self._attr_native_value = datapoint.value
                    if self._mapping.icons is not None:
                        if datapoint.value >= 0 and datapoint.value < len(
                            self._mapping.icons
                        ):
                            self._attr_icon = self._mapping.icons[datapoint.value]
                elif datapoint.type == TuyaBLEDataPointType.DT_VALUE:
                    self._attr_native_value = (
                        datapoint.value / self._mapping.coefficient
                    )
                else:
                    self._attr_native_value = datapoint.value
        self.async_write_ha_state()

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
    entities: list[TuyaBLESensor] = [
        TuyaBLESensor(
            hass,
            data.coordinator,
            data.device,
            data.product,
            rssi_mapping,
        )
    ]
    for mapping in mappings:
        if mapping.force_add or data.device.datapoints.has_id(
            mapping.dp_id, mapping.dp_type
        ):
            entities.append(
                TuyaBLESensor(
                    hass,
                    data.coordinator,
                    data.device,
                    data.product,
                    mapping,
                )
            )
    async_add_entities(entities)
