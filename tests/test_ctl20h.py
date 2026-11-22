"""Tests for the jtmspro/y2yaegze Drawer Lock CTL20H."""

import base64
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.tuya_ble.lock import build_stored_check_unlock_command

CHECK_PAYLOAD = b"\x00\x01\xff\xff12345678\x01\x01\x02\x03\x04\x00\x00"
CHECK_VALUE = base64.b64encode(CHECK_PAYLOAD).decode()
UNLOCK_COMMAND = bytes.fromhex("ffff0001313233343536373801010203040001")


def test_ctl20h_stored_check_unlock_command() -> None:
    """The DP71 command replays the check code and key from the cloud value."""
    assert build_stored_check_unlock_command(CHECK_VALUE) == UNLOCK_COMMAND
    assert len(UNLOCK_COMMAND) == 19

    with pytest.raises(ValueError, match="invalid timestamped lock format"):
        build_stored_check_unlock_command(base64.b64encode(b"invalid").decode())


def test_ctl20h_uses_fd50_handshake_with_legacy_key() -> None:
    """y2yaegze needs FD50 framing and ignores a cloud-provided sec_key."""
    from bleak.backends.device import BLEDevice

    from custom_components.tuya_ble.tuya_ble import TuyaBLEDevice
    from custom_components.tuya_ble.tuya_ble.tuya_ble import (
        LEGACY_KEY_DERIVATION_PRODUCT_IDS,
    )

    device = TuyaBLEDevice(
        Mock(),
        BLEDevice(name="lock", address="11:22:33:44:55:66", details="", rssi=-50),
    )
    device._device_info = Mock(product_id="y2yaegze")
    device._characteristic_notify = "00000002-0000-1001-8001-00805f9b07d0"

    assert device._requires_fd50_device_info_handshake()
    assert device._device_info_payload() == b"\x00\xf3"
    assert "y2yaegze" in LEGACY_KEY_DERIVATION_PRODUCT_IDS


async def test_ctl20h_lock_state_and_commands(hass: HomeAssistant) -> None:
    """DP47 is the state, DP46 locks and DP71 unlocks with the stored check."""
    from bleak.backends.device import BLEDevice

    from custom_components.tuya_ble.devices import (
        TuyaBLECoordinator,
        TuyaBLEProductInfo,
    )
    from custom_components.tuya_ble.lock import TuyaBLELock
    from custom_components.tuya_ble.tuya_ble import (
        TuyaBLEDataPointType,
        TuyaBLEDevice,
        TuyaBLEDeviceCredentials,
    )

    device = TuyaBLEDevice(
        Mock(), BLEDevice(name="Test lock", address="02:00:00:00:00:02", details="")
    )
    device._device_info = TuyaBLEDeviceCredentials(
        uuid="testuuid00000002",
        local_key="0123456789abcdef",
        device_id="testlock000000002",
        category="jtmspro",
        product_id="y2yaegze",
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
        TuyaBLEProductInfo("Drawer Lock CTL20H", lock=1),
    )

    # No DP47 report yet: the state is unknown instead of defaulting to locked.
    assert lock.is_locked is None

    device.datapoints._update_from_device(47, 0, 0, TuyaBLEDataPointType.DT_BOOL, False)
    assert lock.is_locked is True
    device.datapoints._update_from_device(47, 0, 0, TuyaBLEDataPointType.DT_BOOL, True)
    assert lock.is_locked is False

    await lock.async_lock()
    assert device.datapoints[46].value is True
    device._send_datapoints.assert_awaited_once_with([46])

    with pytest.raises(HomeAssistantError, match="BLE unlock check is missing"):
        await lock.async_unlock()
    device._device_info.ble_unlock_check = "invalid"
    with pytest.raises(HomeAssistantError, match="BLE unlock check is invalid"):
        await lock.async_open()
    assert device._send_datapoints.await_count == 1

    device._device_info.ble_unlock_check = CHECK_VALUE
    await lock.async_unlock()
    assert device.datapoints[71].value == UNLOCK_COMMAND
    assert device._send_datapoints.await_args.args == ([71],)

    # The command does not change between calls and must still be sent again.
    await lock.async_open()
    assert device._send_datapoints.await_count == 3
