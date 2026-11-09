"""Tests for the jtmspro/dappsdq4 smart lock."""

import base64
import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.tuya_ble.cloud import extract_ble_unlock_check
from custom_components.tuya_ble.lock import build_timestamped_unlock_command
from custom_components.tuya_ble.tuya_ble.security import (
    decode_timestamped_ble_unlock_check,
)


async def test_lock_dp33_polarity_and_timestamped_open(hass: HomeAssistant) -> None:
    """DP33 polarity and DP71 Open are independent of other locks' commands."""
    from bleak.backends.device import BLEDevice

    from custom_components.tuya_ble.devices import (
        TuyaBLECoordinator,
        TuyaBLEProductInfo,
    )
    from custom_components.tuya_ble.lock import TuyaBLELock
    from custom_components.tuya_ble.tuya_ble import (
        TuyaBLEDevice,
        TuyaBLEDeviceCredentials,
    )

    device = TuyaBLEDevice(
        Mock(), BLEDevice(name="Test lock", address="02:00:00:00:00:01", details="")
    )
    device._device_info = TuyaBLEDeviceCredentials(
        uuid="testuuid00000001",
        local_key="0123456789abcdef",
        device_id="testlock000000001",
        category="jtmspro",
        product_id="dappsdq4",
        device_name="Test lock",
        product_model="",
        product_name="Test lock",
        functions=[],
        status_range=[],
    )
    device._send_datapoints = AsyncMock()
    lock = TuyaBLELock(
        hass,
        TuyaBLECoordinator(hass, device),
        device,
        TuyaBLEProductInfo("Test lock", lock=1),
    )
    assert lock.is_locked is None
    await lock.async_unlock()
    assert lock.is_locked is False
    assert device.datapoints[33].value is False
    await lock.async_lock()
    assert lock.is_locked is True
    assert device.datapoints[33].value is True
    with pytest.raises(HomeAssistantError, match="BLE unlock check is missing"):
        await lock.async_open()
    assert device._send_datapoints.await_count == 2
    device._device_info.ble_unlock_check = "invalid"
    with pytest.raises(HomeAssistantError, match="BLE unlock check is invalid"):
        await lock.async_open()
    assert device._send_datapoints.await_count == 2
    device._device_info.ble_unlock_check = CHECK_VALUE
    with patch("time.time", return_value=0x6AD8EB64):
        await lock.async_open()
    assert device.datapoints[71].value == bytes.fromhex(
        "ffff00013132333435363738016ad8eb640001"
    )


CHECK_PAYLOAD = b"\x00\x01\xff\xff12345678\x01\x01\x02\x03\x04\x00\x00"
CHECK_VALUE = base64.b64encode(CHECK_PAYLOAD).decode()


def test_lock_activity_unlock_check_validation_and_command() -> None:
    """The cloud secret is validated and produces the documented DP71 payload."""
    assert decode_timestamped_ble_unlock_check(CHECK_VALUE) == CHECK_PAYLOAD
    assert build_timestamped_unlock_command(CHECK_VALUE, 0x6AD8EB64) == bytes.fromhex(
        "ffff00013132333435363738016ad8eb640001"
    )

    with pytest.raises(ValueError, match="invalid timestamped lock format"):
        decode_timestamped_ble_unlock_check(base64.b64encode(b"invalid").decode())


def test_lock_activity_unlock_check_is_extracted_from_status() -> None:
    """Only the validated BLE unlock check is selected from cloud status."""
    status = [
        {"code": "residual_electricity", "value": 28},
        {"code": "ble_unlock_check", "value": CHECK_VALUE},
    ]
    assert extract_ble_unlock_check(status) == CHECK_VALUE
    assert (
        extract_ble_unlock_check([{"code": "residual_electricity", "value": 28}])
        is None
    )


def test_lock_activity_device_info_payload_keeps_protocol_v4() -> None:
    """dappsdq4 sends its FD50 MTU payload without the legacy v2 framing."""
    from bleak.backends.device import BLEDevice

    from custom_components.tuya_ble.tuya_ble import TuyaBLEDevice

    device = TuyaBLEDevice(
        Mock(),
        BLEDevice(name="lock", address="11:22:33:44:55:66", details="", rssi=-50),
    )
    device._device_info = Mock(product_id="dappsdq4")
    device._characteristic_notify = "00000002-0000-1001-8001-00805f9b07d0"
    device._protocol_version = 4

    assert device._device_info_payload() == b"\x00\xf4"
    assert not device._requires_fd50_device_info_handshake()


async def test_lock_activity_protocol_v4_examples() -> None:
    """Decode the documented 0x8006/0x8007 reports and encode DP33 writes."""
    from bleak.backends.device import BLEDevice

    from custom_components.tuya_ble.tuya_ble import (
        TuyaBLEDataPointType,
        TuyaBLEDevice,
    )
    from custom_components.tuya_ble.tuya_ble.const import TuyaBLECode

    device = TuyaBLEDevice(
        Mock(),
        BLEDevice(name="lock", address="11:22:33:44:55:66", details="", rssi=-50),
    )
    device._protocol_version = 4
    device._send_response = AsyncMock()
    device._handle_command_or_response(
        1,
        0,
        TuyaBLECode.FUN_RECEIVE_DP_V4,
        bytes.fromhex("000000000e8000080200040000001c"),
    )
    device._handle_command_or_response(
        2,
        0,
        TuyaBLECode.FUN_RECEIVE_TIME_DP_V4,
        bytes.fromhex("000000000e0000016ad8e2c40c02000400000001"),
    )
    await asyncio.sleep(0)
    assert device.datapoints[8].value == 28
    assert device.datapoints[12].value == 1
    assert device.datapoints[12].timestamp == 0x6AD8E2C4

    device.datapoints.get_or_create(33, TuyaBLEDataPointType.DT_BOOL, False)
    device._get_seq_num = AsyncMock(return_value=0x0F)
    device._send_packet = AsyncMock()
    await device.set_multiple_values({33: True})
    device._send_packet.assert_awaited_once_with(
        TuyaBLECode.FUN_SENDER_DPS_V4,
        bytes.fromhex("000000000f2101000101"),
    )
