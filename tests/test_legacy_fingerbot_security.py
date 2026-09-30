"""Regression coverage for devices given a SecKey despite legacy encryption."""

import hashlib
from unittest.mock import AsyncMock, Mock

from bleak.backends.device import BLEDevice
import pytest

from custom_components.tuya_ble.tuya_ble import (
    TuyaBLEDevice,
    TuyaBLEDeviceCredentials,
)
from custom_components.tuya_ble.tuya_ble.const import TuyaBLECode


@pytest.mark.parametrize(
    ("product_id", "sec_key", "expected_login_flag"),
    [
        ("mknd4lci", "fedcba9876543210", 4),
        ("mknd4lci", None, 4),
        ("qcrilcpr", "fedcba9876543210", 4),
        ("jntxv3q4", "fedcba9876543210", 14),
    ],
)
async def test_device_selects_matching_login_and_session_security(
    product_id: str, sec_key: str | None, expected_login_flag: int
) -> None:
    """A cloud SecKey must not break classic Fingerbots or existing exceptions."""

    local_key = "0123456789abcdef"
    creds = TuyaBLEDeviceCredentials(
        uuid="1234567890abcdef",
        local_key=local_key,
        device_id="test-device",
        category="kg",
        product_id=product_id,
        device_name="Test",
        product_model="Test",
        product_name="Test",
        functions=[],
        status_range=[],
        sec_key=sec_key,
    )
    manager = Mock()
    manager.get_device_credentials = AsyncMock(return_value=creds)
    device = TuyaBLEDevice(manager, BLEDevice("11:22:33:44:55:66", "Test", {}))
    assert await device._update_device_info()

    material = (
        local_key[:6] if expected_login_flag == 4 else local_key + sec_key
    ).encode("ascii")
    assert device._login_key == hashlib.md5(material).digest()
    packets = device._build_packets(1, TuyaBLECode.FUN_SENDER_DEVICE_INFO, b"")
    assert packets[0][3] == expected_login_flag

    response = bytearray(46)
    response[2:4] = bytes([3, 3])
    response[6:12] = b"random"
    device._handle_command_or_response(
        1, 0, TuyaBLECode.FUN_SENDER_DEVICE_INFO, response
    )
    assert device._session_key == hashlib.md5(material + b"random").digest()
    packets = device._build_packets(2, TuyaBLECode.FUN_SENDER_DEVICE_STATUS, b"")
    assert packets[0][3] == expected_login_flag + 1
    # Do not remove or overwrite the saved key as part of protocol selection.
    assert creds.sec_key == sec_key
