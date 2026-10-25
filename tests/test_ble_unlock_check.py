"""Tests for the DP71 (ble_unlock_check) unlock used by the CTL20 SmartLock."""

import base64
from struct import pack
from unittest.mock import AsyncMock, Mock

from homeassistant.components.button import ButtonEntityDescription
from homeassistant.core import HomeAssistant

from custom_components.tuya_ble.button import (
    TuyaBLEButton,
    TuyaBLEButtonMapping,
    build_ble_unlock_check_command,
    parse_ble_unlock_check,
)
from custom_components.tuya_ble.tuya_ble import TuyaBLEDataPointType
from custom_components.tuya_ble.tuya_ble.manager import TuyaBLEDeviceCredentials

from . import *

CHECK_CODE = b"12345678"
TIMESTAMP = 0x6ABBADC8

# Status value reported to the cloud after an app unlock:
# member id | FFFF | code | 01 | time | 0000
CLOUD_VALUE = pack(">HH", 5, 0xFFFF) + CHECK_CODE + b"\x01" + pack(">I", 1) + b"\0\0"
# Value reported by the lock after a rejected command:
# FFFF | member id | code | 01 | time | 0002
DEVICE_VALUE = pack(">HH", 0xFFFF, 5) + CHECK_CODE + b"\x01" + pack(">I", 1) + b"\0\2"
EXPECTED_COMMAND = (
    pack(">HH", 0xFFFF, 5) + CHECK_CODE + b"\x01" + pack(">I", TIMESTAMP) + b"\0\1"
)


def test_parse_ble_unlock_check() -> None:
    """Both field orders yield the member id and the check code."""
    assert parse_ble_unlock_check(CLOUD_VALUE) == (5, CHECK_CODE)
    assert parse_ble_unlock_check(DEVICE_VALUE) == (5, CHECK_CODE)
    assert parse_ble_unlock_check(b"\x00\x05") is None
    assert parse_ble_unlock_check(pack(">HH", 0xFFFF, 0xFFFF) + CHECK_CODE) is None
    assert parse_ble_unlock_check(pack(">HH", 5, 0xFFFF) + b"\x00" * 8) is None


def test_build_ble_unlock_check_command() -> None:
    """The command uses the app layout: FFFF | member | code | 01 | time | 0001."""
    command = build_ble_unlock_check_command(5, CHECK_CODE, now=TIMESTAMP)
    assert command == EXPECTED_COMMAND
    assert len(command) == 19


async def _setup_button(hass: HomeAssistant, ble_unlock_check: str | None):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"address": DEVICE_ADDRESS},
        title="Mock TuyaBLE",
    )
    entry.add_to_hass(hass)

    ble_device = BLEDevice(name="lock", address="11:22:33", details="", rssi=-50)
    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())
    device = TuyaBLEDevice(manager, ble_device)
    await device.initialize()
    device._device_info = TuyaBLEDeviceCredentials(
        uuid="uuid123",
        local_key="wV[NcWGUSFF`dSgO",
        device_id="767823809c9c1f458745",
        category="jtmspro",
        product_id="tkbdvrzr",
        device_name="CTL20",
        product_model="",
        product_name="CTL20 SmartLock",
        functions=[],
        status_range=[],
        ble_unlock_check=ble_unlock_check,
    )
    device._send_datapoints = AsyncMock()

    product_info = TuyaBLEProductInfo("Drawer Lock CTL20")
    coordinator = TuyaBLECoordinator(hass, device)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = TuyaBLEData(
        title="Hello",
        device=device,
        manager=manager,
        product=product_info,
        coordinator=coordinator,
    )
    mapping = TuyaBLEButtonMapping(
        dp_id=71,
        description=ButtonEntityDescription(key="bluetooth_unlock"),
        dp_type=TuyaBLEDataPointType.DT_RAW,
    )
    entity = TuyaBLEButton(hass, coordinator, device, product_info, mapping)
    entity.async_write_ha_state = Mock()
    coordinator._async_handle_connect()
    return device, entity


async def test_unlock_with_cloud_value(hass: HomeAssistant, monkeypatch) -> None:
    """The button sends the DP71 command built from the cloud status value."""
    import custom_components.tuya_ble.button as button_module

    monkeypatch.setattr(button_module.time, "time", lambda: TIMESTAMP)
    device, entity = await _setup_button(hass, base64.b64encode(CLOUD_VALUE).decode())

    entity.press()
    await hass.async_block_till_done()

    device._send_datapoints.assert_called_once_with([71])
    assert device.datapoints[71].value == EXPECTED_COMMAND


async def test_unlock_with_device_value(hass: HomeAssistant, monkeypatch) -> None:
    """Without a cloud value the last DP71 reported by the lock is used."""
    import custom_components.tuya_ble.button as button_module

    monkeypatch.setattr(button_module.time, "time", lambda: TIMESTAMP)
    device, entity = await _setup_button(hass, None)
    device.datapoints._update_from_device(
        71, 0, 0, TuyaBLEDataPointType.DT_RAW, DEVICE_VALUE
    )

    entity.press()
    await hass.async_block_till_done()

    device._send_datapoints.assert_called_once_with([71])
    assert device.datapoints[71].value == EXPECTED_COMMAND


async def test_unlock_without_value(hass: HomeAssistant) -> None:
    """Nothing is sent when no check code is known."""
    device, entity = await _setup_button(hass, None)

    entity.press()
    await hass.async_block_till_done()

    device._send_datapoints.assert_not_called()


async def test_cloud_status_value_is_kept_in_credentials(
    hass: HomeAssistant,
) -> None:
    """ble_unlock_check from the device status list reaches the credentials."""
    from custom_components.tuya_ble.cloud import TuyaCloudCacheItem
    from custom_components.tuya_ble.const import CONF_BLE_UNLOCK_CHECK

    value = base64.b64encode(CLOUD_VALUE).decode()
    responses = {
        "/v1.0/users/uid/devices": {
            "result": [
                {
                    "id": "dev1",
                    "uuid": "uuid1",
                    "local_key": "0123456789abcdef",
                    "category": "jtmspro",
                    "product_id": "tkbdvrzr",
                    "name": "CTL20",
                    "status": [
                        {"code": "residual_electricity", "value": 59},
                        {"code": "ble_unlock_check", "value": value},
                    ],
                }
            ]
        },
        "/v1.0/iot-03/devices/factory-infos?device_ids=dev1": {
            "result": [{"mac": "dc23504f9caf"}]
        },
        "/v1.1/devices/dev1/specifications": {"result": {}},
    }
    api = Mock()
    api.token_info.uid = "uid"
    api.get = Mock(side_effect=lambda url: responses[url])
    item = TuyaCloudCacheItem(api=api, login={}, credentials={})
    manager = HASSTuyaBLEDeviceManager(hass, {})

    await manager._fill_cache_item(item)

    assert item.credentials["DC:23:50:4F:9C:AF"][CONF_BLE_UNLOCK_CHECK] == value
