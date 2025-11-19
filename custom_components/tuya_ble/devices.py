"""The Tuya BLE integration."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any

import logging
from homeassistant.const import CONF_ADDRESS, CONF_DEVICE_ID

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import (
    DeviceInfo,
    EntityDescription,
    generate_entity_id,
)
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from homeassistant.components.tuya.const import (
    DPCode,
    DPType,
)

from home_assistant_bluetooth import BluetoothServiceInfoBleak
from .tuya_ble import (
    AbstaractTuyaBLEDeviceManager,
    TuyaBLEDataPoint,
    TuyaBLEDataPointType,
    TuyaBLEDevice,
    TuyaBLEDeviceCredentials,
)

from .cloud import HASSTuyaBLEDeviceManager
from .const import (
    DEVICE_DEF_MANUFACTURER,
    DOMAIN,
    FINGERBOT_BUTTON_EVENT,
    SET_DISCONNECTED_DELAY,
    DPCode,
    DPType,
)

from .base import IntegerTypeData, EnumTypeData

_LOGGER = logging.getLogger(__name__)


@dataclass
class TuyaBLEFingerbotInfo:
    """Model a fingerbot"""

    switch: int
    mode: int
    up_position: int
    down_position: int
    hold_time: int
    reverse_positions: int
    manual_control: int = 0
    program: int = 0


@dataclass
class TuyaBLEWaterValveInfo:
    """Model a water valve"""

    switch: bool
    countdown: int
    weather_delay: str
    smart_weather: str
    use_time: int


@dataclass
class TuyaBLEProductInfo:
    """Model product info"""

    name: str
    manufacturer: str = DEVICE_DEF_MANUFACTURER
    fingerbot: TuyaBLEFingerbotInfo | None = None
    watervalve: TuyaBLEWaterValveInfo | None = None
    lock: int | None = None


class TuyaBLEEntity(CoordinatorEntity):
    """Tuya BLE base entity."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: TuyaBLECoordinator,
        device: TuyaBLEDevice,
        product: TuyaBLEProductInfo,
        description: EntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self._hass = hass
        self._coordinator = coordinator
        self._device = device
        self._product = product
        if description.translation_key is None:
            self._attr_translation_key = description.key
        self.entity_description = description
        self._attr_has_entity_name = True
        self._attr_device_info = get_device_info(self._device)
        self._attr_unique_id = f"{self._device.device_id}-{description.key}"
        self.entity_id = generate_entity_id(
            "sensor.{}", self._attr_unique_id, hass=hass
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._coordinator.connected

    @property
    def device(self) -> TuyaBLEDevice:
        """Return the associated BLE Device."""
        return self._device

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    def send_dp_value(
        self,
        key: DPCode | None,
        dp_type: TuyaBLEDataPointType,
        value: bytes | bool | int | str | None = None,
    ) -> None:
        dpid = self.find_dpid(key)
        if dpid is not None:
            datapoint = self._device.datapoints.get_or_create(
                dpid,
                dp_type,
                value,
            )
            self._hass.create_task(datapoint.set_value(value))

    def _send_command(self, commands: list[dict[str, Any]]) -> None:
        """Send the commands to the device"""
        for command in commands:
            code = command.get("code")
            value = command.get("value")

            if code and value is not None:
                dttype = self.get_dptype(code)
                if isinstance(value, str):
                    # We suppose here that cloud JSON type are sent as string
                    if dttype in (DPType.STRING, DPType.JSON):
                        self.send_dp_value(code, TuyaBLEDataPointType.DT_STRING, value)
                    elif dttype == DPType.ENUM:
                        int_value = 0
                        values = self.device.function[code].values
                        if isinstance(values, dict):
                            range = values.get("range")
                            if isinstance(range, list):
                                int_value = (
                                    range.index(value) if value in range else None
                                )
                        self.send_dp_value(
                            code, TuyaBLEDataPointType.DT_ENUM, int_value
                        )

                elif isinstance(value, bool):
                    self.send_dp_value(code, TuyaBLEDataPointType.DT_BOOL, value)
                else:
                    self.send_dp_value(code, TuyaBLEDataPointType.DT_VALUE, value)

    def find_dpid(
        self, dpcode: DPCode | None, prefer_function: bool = False
    ) -> int | None:
        """Returns the dp id for the given code"""
        if dpcode is None:
            return None

        order = ["status_range", "function"]
        if prefer_function:
            order = ["function", "status_range"]
        for key in order:
            if dpcode in getattr(self.device, key):
                return getattr(self.device, key)[dpcode].dp_id

        return None

    def find_dpcode(
        self,
        dpcodes: str | DPCode | tuple[DPCode, ...] | None,
        *,
        prefer_function: bool = False,
        dptype: DPType | None = None,
    ) -> DPCode | EnumTypeData | IntegerTypeData | None:
        """Find a matching DP code available on for this device."""
        if dpcodes is None:
            return None

        if isinstance(dpcodes, str):
            dpcodes = (DPCode(dpcodes),)
        elif not isinstance(dpcodes, tuple):
            dpcodes = (dpcodes,)

        order = ["status_range", "function"]
        if prefer_function:
            order = ["function", "status_range"]

        # When we are not looking for a specific datatype, we can append status for
        # searching
        if not dptype:
            order.append("status")

        for dpcode in dpcodes:
            for key in order:
                if dpcode not in getattr(self.device, key):
                    continue
                if (
                    dptype == DPType.ENUM
                    and getattr(self.device, key)[dpcode].type == DPType.ENUM
                ):
                    if not (
                        enum_type := EnumTypeData.from_json(
                            dpcode, getattr(self.device, key)[dpcode].values
                        )
                    ):
                        continue
                    return enum_type

                if (
                    dptype == DPType.INTEGER
                    and getattr(self.device, key)[dpcode].type == DPType.INTEGER
                ):
                    if not (
                        integer_type := IntegerTypeData.from_json(
                            dpcode, getattr(self.device, key)[dpcode].values
                        )
                    ):
                        continue
                    return integer_type

                if dptype not in (DPType.ENUM, DPType.INTEGER):
                    return dpcode

        return None

    def get_dptype(
        self, dpcode: DPCode | None, prefer_function: bool = False
    ) -> DPType | None:
        """Find a matching DPCode data type available on for this device."""
        if dpcode is None:
            return None

        order = ["status_range", "function"]
        if prefer_function:
            order = ["function", "status_range"]
        for key in order:
            if dpcode in getattr(self.device, key):
                return DPType(getattr(self.device, key)[dpcode].type)

        return None


class TuyaBLECoordinator(DataUpdateCoordinator[None]):
    """Data coordinator for receiving Tuya BLE updates."""

    def __init__(self, hass: HomeAssistant, device: TuyaBLEDevice) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
        )
        self._device = device
        self._disconnected: bool = True
        self._unsub_disconnect: CALLBACK_TYPE | None = None
        device.register_connected_callback(self._async_handle_connect)
        device.register_callback(self._async_handle_update)
        device.register_disconnected_callback(self._async_handle_disconnect)

    @property
    def connected(self) -> bool:
        return not self._disconnected

    @callback
    def _async_handle_connect(self) -> None:
        if self._unsub_disconnect is not None:
            self._unsub_disconnect()
        if self._disconnected:
            self._disconnected = False
            self.async_update_listeners()

    @callback
    def _async_handle_update(self, updates: list[TuyaBLEDataPoint]) -> None:
        """Just trigger the callbacks."""
        self._async_handle_connect()
        self.async_set_updated_data(None)
        info = get_device_product_info(self._device)
        if info and info.fingerbot and info.fingerbot.manual_control != 0:
            for update in updates:
                if update.id == info.fingerbot.switch and update.changed_by_device:
                    self.hass.bus.fire(
                        FINGERBOT_BUTTON_EVENT,
                        {
                            CONF_ADDRESS: self._device.address,
                            CONF_DEVICE_ID: self._device.device_id,
                        },
                    )

    @callback
    def _set_disconnected(self, _: None) -> None:
        """Invoke the idle timeout callback, called when the alarm fires."""
        self._disconnected = True
        self._unsub_disconnect = None
        self.async_update_listeners()

    @callback
    def _async_handle_disconnect(self) -> None:
        """Trigger the callbacks for disconnected."""
        if self._unsub_disconnect is None:
            delay: float = SET_DISCONNECTED_DELAY
            self._unsub_disconnect = async_call_later(
                self.hass, delay, self._set_disconnected
            )


@dataclass
class TuyaBLEData:
    """Data for the Tuya BLE integration."""

    title: str
    device: TuyaBLEDevice
    product: TuyaBLEProductInfo
    manager: HASSTuyaBLEDeviceManager
    coordinator: TuyaBLECoordinator


@dataclass
class TuyaBLECategoryInfo:
    """Defines category info"""

    products: dict[str, TuyaBLEProductInfo]
    info: TuyaBLEProductInfo | None = None


devices_database: dict[str, TuyaBLECategoryInfo] = {
    "co2bj": TuyaBLECategoryInfo(
        products={
            "59s19z5m": TuyaBLEProductInfo(  # device product_id
                name="CO2 Detector",
            ),
        },
    ),
    "ms": TuyaBLECategoryInfo(
        products={
            **dict.fromkeys(
                ["ludzroix", "isk2p555", "gumrixyt", "uamrw6h3"],
                TuyaBLEProductInfo(  # device product_id
                    name="Smart Lock",
                ),
            ),
            "okkyfgfs": TuyaBLEProductInfo(
                name="TEKXDD Fingerprint Smart Lock",
                lock=1,
            ),
            "k53ok3u9": TuyaBLEProductInfo(
                name="Fingerprint Smart Lock",
                lock=1,
            ),
        },
    ),
    "dcb": TuyaBLECategoryInfo(
        products={
            **dict.fromkeys(
                ["z5ztlw3k"],
                TuyaBLEProductInfo(  # device product_id
                    name="PARKSIDE Smart battery 4Ah",
                ),
            ),
            **dict.fromkeys(
                ["ajrhf1aj"],
                TuyaBLEProductInfo(  # device product_id
                    name="PARKSIDE Smart battery 8Ah",
                ),
            ),
        },
    ),
    "jtmspro": TuyaBLECategoryInfo(
        products={
            "xicdxood": TuyaBLEProductInfo(  # device product_id
                name="Raycube K7 Pro+",
            ),
            "rlyxv7pe": TuyaBLEProductInfo(  # device product_id
                name="A1 PRO MAX",
            ),
            "ebd5e0uauqx0vfsp": TuyaBLEProductInfo(  # device product_id
                name="CentralAcesso",
            ),
        },
    ),
    "szjqr": TuyaBLECategoryInfo(
        products={
            "3yqdo5yt": TuyaBLEProductInfo(  # device product_id
                name="CUBETOUCH 1s",
                fingerbot=TuyaBLEFingerbotInfo(
                    switch=1,
                    mode=2,
                    up_position=5,
                    down_position=6,
                    hold_time=3,
                    reverse_positions=4,
                ),
            ),
            "xhf790if": TuyaBLEProductInfo(  # device product_id
                name="CubeTouch II",
                fingerbot=TuyaBLEFingerbotInfo(
                    switch=1,
                    mode=2,
                    up_position=5,
                    down_position=6,
                    hold_time=3,
                    reverse_positions=4,
                ),
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
                ],  # device product_ids
                TuyaBLEProductInfo(
                    name="Fingerbot Plus",
                    fingerbot=TuyaBLEFingerbotInfo(
                        switch=2,
                        mode=8,
                        up_position=15,
                        down_position=9,
                        hold_time=10,
                        reverse_positions=11,
                        manual_control=17,
                        program=121,
                    ),
                ),
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
                ],  # device product_ids
                TuyaBLEProductInfo(
                    name="Fingerbot",
                    fingerbot=TuyaBLEFingerbotInfo(
                        switch=2,
                        mode=8,
                        up_position=15,
                        down_position=9,
                        hold_time=10,
                        reverse_positions=11,
                        program=121,
                    ),
                ),
            ),
            "yn4x5fa7": TuyaBLEProductInfo(
                name="Nedis SmartLife Finger Robot",
                fingerbot=TuyaBLEFingerbotInfo(
                    switch=1,
                    mode=2,
                    up_position=4,
                    down_position=5,
                    hold_time=3,
                    reverse_positions=6,
                ),
            ),
        },
    ),
    "kg": TuyaBLECategoryInfo(
        products={
            **dict.fromkeys(
                ["mknd4lci", "riecov42", "bs3ubslo"],  # device product_ids
                TuyaBLEProductInfo(
                    name="Fingerbot Plus",
                    fingerbot=TuyaBLEFingerbotInfo(
                        switch=1,
                        mode=101,
                        up_position=106,
                        down_position=102,
                        hold_time=103,
                        reverse_positions=104,
                        manual_control=107,
                        program=109,
                    ),
                ),
            ),
        },
    ),
    "wk": TuyaBLECategoryInfo(
        products={
            **dict.fromkeys(
                [
                    "drlajpqc",
                    "nhj2j7su",
                    "zmachryv",
                ],  # device product_id
                TuyaBLEProductInfo(
                    name="Thermostatic Radiator Valve",
                ),
            ),
        },
    ),
    "wsdcg": TuyaBLECategoryInfo(
        products={
            "ojzlzzsw": TuyaBLEProductInfo(  # device product_id
                name="Soil moisture sensor",
            ),
            "iv7hudlj": TuyaBLEProductInfo(
                name="Bluetooth Temperature Humidity Sensor",
            ),
            "jm6iasmb": TuyaBLEProductInfo(
                name="Bluetooth Temperature Humidity Sensor",
            ),
            "tv6peegl": TuyaBLEProductInfo(  # new device product_id
                name="Soil Thermo-Hygrometer",
            ),
            "vlzqwckk": TuyaBLEProductInfo(
                name="Temperature Humidity Sensor",
            ),
        },
    ),
    "znhsb": TuyaBLECategoryInfo(
        products={
            "cdlandip": TuyaBLEProductInfo(  # device product_id
                name="Smart water bottle",
            ),
        },
    ),
    "sfkzq": TuyaBLECategoryInfo(
        products={
            **dict.fromkeys(
                [
                    "6pahkcau",
                    "hfgdqhho",
                    "qycalacn",
                    "fnlw6npo",
                    "jjqi2syk",
                ],  # device product_ids
                TuyaBLEProductInfo(
                    name="Irrigation computer",
                ),
            ),
            **dict.fromkeys(
                [
                    "svhikeyq",
                    "0axr5s0b",
                ],  # device product_id
                TuyaBLEProductInfo(
                    name="Valve controller",
                    watervalve=TuyaBLEWaterValveInfo(
                        switch=1,
                        countdown=11,
                        weather_delay=10,
                        smart_weather=13,
                        use_time=15,
                    ),
                ),
            ),
            **dict.fromkeys(
                [
                    "nxquc5lb",
                    "46zia2nz",
                    "1fcnd8xk",
                ],
                TuyaBLEProductInfo(
                    name="Water valve controller",
                    watervalve=TuyaBLEWaterValveInfo(
                        switch=1,
                        countdown=8,
                        weather_delay=10,
                        smart_weather=13,
                        use_time=9,
                    ),
                ),
            ),
        },
    ),
    "ggq": TuyaBLECategoryInfo(
        products={
            **dict.fromkeys(
                ["6pahkcau", "hfgdqhho"],  # PPB A1  # SGW08  # device product_id
                TuyaBLEProductInfo(
                    name="Irrigation computer",
                ),
            )
        },
    ),
    "dd": TuyaBLECategoryInfo(
        products={
            **dict.fromkeys(
                [
                    "nvfrtxlq",
                ],  # device product_id
                TuyaBLEProductInfo(
                    name="LGB102 Magic Strip Lights",
                    manufacturer="Magiacous",
                ),
            ),
            "umzu0c2y": TuyaBLEProductInfo(  # device product_id
                name="Floor Lamp",
                manufacturer="Magiacous",
            ),
            "6jxcdae1": TuyaBLEProductInfo(  # device product_id
                name="Sunset Lamp",
                manufacturer="Comfamoli",
            ),
        },
        info=TuyaBLEProductInfo(
            name="Lights",
        ),
    ),
    "cl": TuyaBLECategoryInfo(
        products={
            **dict.fromkeys(
                ["4pbr8eig", "vlwf3ud6"], TuyaBLEProductInfo(name="Blind Controller")
            ),
            "kcy0x4pi": TuyaBLEProductInfo(name="Curtain Controller"),
        }
    ),
}


def get_product_info_by_ids(
    category: str, product_id: str
) -> TuyaBLEProductInfo | None:
    category_info = devices_database.get(category)
    if category_info is not None:
        product_info = category_info.products.get(product_id)
        if product_info is not None:
            return product_info
        return category_info.info

    return None


def get_device_product_info(device: TuyaBLEDevice) -> TuyaBLEProductInfo | None:
    return get_product_info_by_ids(device.category, device.product_id)


def get_short_address(address: str) -> str:
    """Short address"""
    results = address.replace("-", ":").upper().split(":")
    return f"{results[-3]}{results[-2]}{results[-1]}"[-6:]


async def get_device_readable_name(
    discovery_info: BluetoothServiceInfoBleak,
    manager: AbstaractTuyaBLEDeviceManager | None,
) -> str:
    """Readable name"""
    credentials: TuyaBLEDeviceCredentials | None = None
    product_info: TuyaBLEProductInfo | None = None
    if manager:
        credentials = await manager.get_device_credentials(discovery_info.address)
        if credentials:
            product_info = get_product_info_by_ids(
                credentials.category,
                credentials.product_id,
            )
    short_address = get_short_address(discovery_info.address)
    if product_info:
        return "%s %s" % (product_info.name, short_address)
    if credentials:
        return "%s %s" % (credentials.device_name, short_address)
    return "%s %s" % (discovery_info.device.name, short_address)


def get_device_info(device: TuyaBLEDevice) -> DeviceInfo | None:
    product_info = None
    if device.category and device.product_id:
        product_info = get_product_info_by_ids(device.category, device.product_id)
    product_name: str
    if product_info:
        product_name = product_info.name
    else:
        product_name = device.name
    result = DeviceInfo(
        connections={(dr.CONNECTION_BLUETOOTH, device.address)},
        hw_version=device.hardware_version,
        identifiers={(DOMAIN, device.address)},
        manufacturer=(
            product_info.manufacturer if product_info else DEVICE_DEF_MANUFACTURER
        ),
        model=("%s (%s)")
        % (
            device.product_model or product_name,
            device.product_id,
        ),
        name=("%s %s")
        % (
            product_name,
            get_short_address(device.address),
        ),
        sw_version=("%s (protocol %s)")
        % (
            device.device_version,
            device.protocol_version,
        ),
    )
    return result
