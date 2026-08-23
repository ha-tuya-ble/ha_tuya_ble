"""Tests for exponential backoff reconnect logic in TuyaBLEDevice."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import BleakNotFoundError

from custom_components.tuya_ble.tuya_ble.const import (
    RECONNECT_BACKOFF_MAX,
    RECONNECT_BACKOFF_MIN,
)
from custom_components.tuya_ble.tuya_ble.tuya_ble import TuyaBLEDevice
from custom_components.tuya_ble.tuya_ble.manager import TuyaBLEDeviceCredentials


def _create_mock_ble_device() -> BLEDevice:
    return BLEDevice(name="MockTuyaDevice", address="00:11:22:33:44:55", details=None)


@pytest.mark.asyncio
async def test_exponential_backoff_doubles_and_caps():
    """Test that connection failure doubles backoff delay up to RECONNECT_BACKOFF_MAX."""
    mock_ble_device = _create_mock_ble_device()
    mock_manager = MagicMock()
    device = TuyaBLEDevice(mock_manager, mock_ble_device)

    assert device._reconnect_backoff == RECONNECT_BACKOFF_MIN

    # Simulate sequential backoff calls
    delay1 = device._next_backoff()
    assert delay1 == RECONNECT_BACKOFF_MIN
    assert device._reconnect_backoff == RECONNECT_BACKOFF_MIN * 2

    delay2 = device._next_backoff()
    assert delay2 == RECONNECT_BACKOFF_MIN * 2
    assert device._reconnect_backoff == RECONNECT_BACKOFF_MIN * 4

    # Force backoff to near cap
    device._reconnect_backoff = RECONNECT_BACKOFF_MAX // 2 + 10
    delay3 = device._next_backoff()
    assert device._reconnect_backoff == RECONNECT_BACKOFF_MAX


@pytest.mark.asyncio
async def test_successful_connection_resets_backoff():
    """Test that successful connection and pairing resets the backoff delay."""
    mock_ble_device = _create_mock_ble_device()
    mock_manager = MagicMock()
    device = TuyaBLEDevice(mock_manager, mock_ble_device)

    device._local_key = b"1234567890123456"
    device._device_info = TuyaBLEDeviceCredentials(
        device_id="dev123",
        product_id="prod123",
        product_name="Mock Product",
        product_model="Mock Model",
        category="ms",
        device_name="Mock Device",
        uuid="uuid123",
        local_key="1234567890123456",
        sec_key="seckey1234567890",
        functions=[],
        status_range=[],
    )

    # Increase backoff state
    device._reconnect_backoff = 80

    mock_client = AsyncMock()
    mock_client.is_connected = True
    mock_client.services.get_characteristic.return_value = MagicMock()

    # _ensure_connected sets _is_paired = True when FUN_SENDER_PAIR response succeeds.
    async def mock_send_packet(code, data, response_to, wait_for_response):
        device._is_paired = True
        return True

    with patch.object(device, "_start_notify_with_retry", return_value=True), \
         patch.object(device, "_send_packet_while_connected", side_effect=mock_send_packet), \
         patch("custom_components.tuya_ble.tuya_ble.tuya_ble.establish_connection", return_value=mock_client):
        await device._ensure_connected()

    assert device._reconnect_backoff == RECONNECT_BACKOFF_MIN
    assert device.is_connected is True
    assert device.last_connect_error is None

    await device.stop()


@pytest.mark.asyncio
async def test_stop_cancels_reconnect_and_prevents_retries():
    """Test that stopping the device cancels any reconnect tasks and prevents future retries."""
    mock_ble_device = _create_mock_ble_device()
    mock_manager = MagicMock()
    device = TuyaBLEDevice(mock_manager, mock_ble_device)

    # Schedule a reconnect task with a long delay
    device._schedule_reconnect(100)
    assert device._reconnect_task is not None
    assert not device._reconnect_task.done()

    await device.stop()
    # Allow event loop to process cancellation
    await asyncio.sleep(0)
    assert device._stopped is True
    assert device._reconnect_task.cancelled() or device._reconnect_task.done()

    # Further attempt to ensure_connected should return early without connecting
    with patch("custom_components.tuya_ble.tuya_ble.tuya_ble.establish_connection") as mock_est:
        await device._ensure_connected()
        mock_est.assert_not_called()
