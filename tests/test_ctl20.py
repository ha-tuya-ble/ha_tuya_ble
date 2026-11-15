"""Tests for the jtmspro/tkbdvrzr CTL20 SmartLock."""

import base64
from unittest.mock import AsyncMock, Mock, patch

from bleak.backends.device import BLEDevice
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import pytest

from custom_components.tuya_ble.button import (
    TuyaBLEButton,
    get_mapping_by_device,
)
from custom_components.tuya_ble.cloud import BLE_UNLOCK_CHECK_STATUS_PRODUCT_IDS
from custom_components.tuya_ble.devices import TuyaBLECoordinator, TuyaBLEProductInfo
from custom_components.tuya_ble.lock import build_timestamped_unlock_command
from custom_components.tuya_ble.tuya_ble import (
    TuyaBLEDevice,
    TuyaBLEDeviceCredentials,
)
from custom_components.tuya_ble.tuya_ble.security import (
    decode_timestamped_ble_unlock_check,
)

# member id 3 (not the first app user), check code "87654321"
MEMBER3_PAYLOAD = b"\x00\x03\xff\xff87654321\x01\x01\x02\x03\x04\x00\x00"
MEMBER3_VALUE = base64.b64encode(MEMBER3_PAYLOAD).decode()


def _device(product_id: str = "tkbdvrzr") -> TuyaBLEDevice:
    device = TuyaBLEDevice(
        Mock(), BLEDevice(name="CTL20", address="02:00:00:00:00:02", details="")
    )
    device._device_info = TuyaBLEDeviceCredentials(
        uuid="testuuid00000002",
        local_key="0123456789abcdef",
        device_id="testlock000000002",
        category="jtmspro",
        product_id=product_id,
        device_name="CTL20",
        product_model="",
        product_name="CTL20 SmartLock",
        functions=[],
        status_range=[],
    )
    device._send_datapoints = AsyncMock()
    return device


def test_unlock_check_keeps_the_member_id() -> None:
    """The check issued for another app member is accepted and used as is."""
    assert decode_timestamped_ble_unlock_check(MEMBER3_VALUE) == MEMBER3_PAYLOAD
    assert build_timestamped_unlock_command(MEMBER3_VALUE, 0x6AD8EB64) == (
        bytes.fromhex("ffff0003") + b"87654321" + bytes.fromhex("016ad8eb640001")
    )


@pytest.mark.parametrize("member", [b"\x00\x00", b"\xff\xff"])
def test_unlock_check_rejects_invalid_member_id(member: bytes) -> None:
    value = base64.b64encode(member + MEMBER3_PAYLOAD[2:]).decode()
    with pytest.raises(ValueError, match="invalid timestamped lock format"):
        decode_timestamped_ble_unlock_check(value)


def test_ctl20_handshake_and_cloud_lookup() -> None:
    """FD50 framing + v1 keys, like qcrilcpr; check read from cloud status."""
    device = _device()
    device._characteristic_notify = "00000002-0000-1001-8001-00805f9b07d0"
    assert device._requires_fd50_device_info_handshake()
    assert device._device_info_payload() == b"\x00\xf3"
    assert "tkbdvrzr" in BLE_UNLOCK_CHECK_STATUS_PRODUCT_IDS


async def test_ctl20_unlock_button(hass: HomeAssistant) -> None:
    """The unlock button writes the timestamped DP71 command."""
    device = _device()
    product = TuyaBLEProductInfo("Drawer Lock CTL20")
    mappings = [
        m
        for m in get_mapping_by_device(device)
        if m.description.key == "bluetooth_unlock"
    ]
    assert len(mappings) == 1
    button = TuyaBLEButton(
        hass, TuyaBLECoordinator(hass, device), device, product, mappings[0]
    )

    with pytest.raises(HomeAssistantError, match="BLE unlock check is missing"):
        button.press()
    device._device_info.ble_unlock_check = "invalid"
    with pytest.raises(HomeAssistantError, match="BLE unlock check is invalid"):
        button.press()
    assert device.datapoints[71] is None

    device._device_info.ble_unlock_check = MEMBER3_VALUE
    with patch("time.time", return_value=0x6AD8EB64):
        button.press()
    await hass.async_block_till_done()
    assert device.datapoints[71].value == (
        bytes.fromhex("ffff0003") + b"87654321" + bytes.fromhex("016ad8eb640001")
    )
    device._send_datapoints.assert_awaited_once()
