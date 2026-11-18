"""Regression tests for failed commands and BLE session changes."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError

from custom_components.tuya_ble.tuya_ble.const import TuyaBLECode
from custom_components.tuya_ble.tuya_ble.exceptions import TuyaBLEDeviceError
from custom_components.tuya_ble.tuya_ble.tuya_ble import TuyaBLEDevice


@pytest.fixture
def device() -> TuyaBLEDevice:
    """Create a device with a connected client and mocked packet encoding."""
    device = TuyaBLEDevice(
        Mock(), BLEDevice("11:22:33:44:55:66", "Test device", {}, rssi=-50)
    )
    device._client = Mock(is_connected=True)
    device._client.disconnect = AsyncMock()
    device._is_paired = True
    device._build_packets = Mock(return_value=[b"command"])
    return device


@pytest.mark.parametrize("wait_for_response", [False, True])
async def test_successful_command(device, wait_for_response):
    """A successful write or response completes without leaking a waiter."""

    async def send(packets):
        if wait_for_response:
            next(iter(device._input_expected_responses.values())).set_result(0)

    device._int_send_packet_while_connected = AsyncMock(side_effect=send)
    assert await device._send_packet_while_connected(
        TuyaBLECode.FUN_SENDER_DPS, b"data", 0, wait_for_response
    )
    assert not device._input_expected_responses


@pytest.mark.parametrize("stage", ["encoding", "write", "response"])
async def test_failed_command_cleans_up_waiter(device, stage):
    """Encoding, write and device errors must all remove the response waiter."""
    error = TuyaBLEDeviceError(1) if stage == "response" else BleakError("Failed")
    futures = []

    def encode(*args):
        futures.extend(device._input_expected_responses.values())
        if stage == "encoding":
            raise error
        return [b"command"]

    async def send(packets):
        if stage == "write":
            raise error
        futures[0].set_exception(error)

    device._build_packets = Mock(side_effect=encode)
    device._int_send_packet_while_connected = AsyncMock(side_effect=send)
    with pytest.raises(type(error)):
        await device._send_packet_while_connected(
            TuyaBLECode.FUN_SENDER_DPS, b"data", 0, True
        )
    assert not device._input_expected_responses
    assert futures[0].done()


@pytest.mark.parametrize("during_write", [False, True])
async def test_cancelled_command_cleans_up_waiter(device, during_write):
    """Cancellation while writing or awaiting a response leaves no waiter."""
    started = asyncio.Event()
    futures = []

    async def send(packets):
        futures.extend(device._input_expected_responses.values())
        started.set()
        if during_write:
            await asyncio.Event().wait()

    device._int_send_packet_while_connected = AsyncMock(side_effect=send)
    task = asyncio.create_task(
        device._send_packet_while_connected(
            TuyaBLECode.FUN_SENDER_DPS, b"data", 0, True
        )
    )
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not device._input_expected_responses
    assert futures[0].cancelled()


@pytest.mark.parametrize("keep_connection", [False, True])
async def test_timeout_fails_command_and_resets_session(device, keep_connection):
    """A missing response must be visible and reset the failed session once."""
    device._keep_connection = keep_connection
    client = device._client
    disconnected = Mock()
    device.register_disconnected_callback(disconnected)
    device._int_send_packet_while_connected = AsyncMock()
    with (
        patch(
            "custom_components.tuya_ble.tuya_ble.tuya_ble.RESPONSE_WAIT_TIMEOUT",
            0.001,
        ),
        patch.object(device, "_schedule_reconnect") as reconnect,
        pytest.raises(BleakError, match="No response received"),
    ):
        await device._send_packet(TuyaBLECode.FUN_SENDER_DPS, b"data")

    client.disconnect.assert_awaited_once()
    disconnected.assert_called_once()
    assert not device.is_connected
    assert not device._input_expected_responses
    assert reconnect.call_count == int(keep_connection)


async def test_write_failure_is_not_replayed(device):
    """A failed physical command must not be replayed in another session."""
    client = device._client
    client.write_gatt_char = AsyncMock(side_effect=BleakError("Write failed"))
    with patch.object(device, "_schedule_reconnect") as reconnect:
        with pytest.raises(BleakError):
            await device._send_packet(TuyaBLECode.FUN_SENDER_DPS, b"data")
        await device._release_task
    client.write_gatt_char.assert_awaited_once()
    client.disconnect.assert_awaited_once()
    assert not device._input_expected_responses
    assert not device.is_connected
    # The release task schedules recovery, never another command write.
    assert reconnect.call_count == 1


async def test_shutdown_error_does_not_schedule_recovery(device):
    """An adapter shutdown must not trigger another reconnect attempt."""
    device._int_send_packet_while_connected = AsyncMock(
        side_effect=BleakError("Bluetooth is already shutdown")
    )
    with patch.object(device, "_recover_connection", AsyncMock()) as recover:
        with pytest.raises(BleakError, match="Bluetooth is already shutdown"):
            await device._send_packet(TuyaBLECode.FUN_SENDER_DPS, b"data")
    recover.assert_not_awaited()
    assert not device._input_expected_responses


async def test_unexpected_disconnect_notifies_and_fails_waiters(device):
    """An unexpected disconnect must notify HA and fail old response IDs."""
    client = device._client
    future = asyncio.get_running_loop().create_future()
    device._input_expected_responses[1] = future
    disconnected = Mock()
    device.register_disconnected_callback(disconnected)
    with patch.object(device, "_schedule_reconnect"):
        device._disconnected(client)
        await device._release_task
    disconnected.assert_called_once()
    assert not device._input_expected_responses
    with pytest.raises(BleakError, match="Device disconnected"):
        await future


async def test_stale_disconnect_does_not_drop_current_session(device):
    """A delayed callback from a previous client must leave the new one alone."""
    current = device._client
    future = asyncio.get_running_loop().create_future()
    device._input_expected_responses[1] = future
    disconnected = Mock()
    device.register_disconnected_callback(disconnected)
    device._disconnected(Mock())
    assert device._client is current
    assert device.is_connected
    assert not future.done()
    disconnected.assert_not_called()
    assert device._release_task is None
    future.cancel()


async def test_recovery_does_not_drop_a_new_session(device):
    """A timeout from the old client must not disconnect its replacement."""
    current = device._client
    with patch.object(device, "_schedule_reconnect") as reconnect:
        await device._recover_connection(Mock())
    assert device._client is current
    assert device.is_connected
    current.disconnect.assert_not_awaited()
    reconnect.assert_not_called()


async def test_connect_waits_for_old_client_release(device):
    """Old notification watchers must be released before connecting again."""
    released = asyncio.Event()
    device._release_task = asyncio.create_task(released.wait())
    connect = asyncio.create_task(device._ensure_connected())
    await asyncio.sleep(0)
    assert not connect.done()
    released.set()
    await connect


async def test_queued_packets_do_not_cross_sessions(device):
    """Packets encoded before acquiring the write lock belong to that client."""
    await device._operation_lock.acquire()
    task = asyncio.create_task(device._int_send_packet_while_connected([b"old"]))
    await asyncio.sleep(0)
    replacement = Mock(is_connected=True)
    replacement.write_gatt_char = AsyncMock()
    device._client = replacement
    device._operation_lock.release()
    with pytest.raises(BleakError, match="Connection changed"):
        await task
    replacement.write_gatt_char.assert_not_awaited()


async def test_fragmented_write_does_not_cross_sessions(device):
    """A replacement client must not receive the remaining old fragments."""
    client = device._client
    replacement = Mock(is_connected=True)
    replacement.write_gatt_char = AsyncMock()

    async def write(*args):
        device._client = replacement

    client.write_gatt_char = AsyncMock(side_effect=write)
    with pytest.raises(BleakError):
        await device._int_send_packets_locked([b"first", b"second"])
    client.write_gatt_char.assert_awaited_once()
    replacement.write_gatt_char.assert_not_awaited()


async def test_late_response_to_cancelled_waiter_is_ignored(device):
    """A response arriving just after cancellation must not break the parser."""
    future = asyncio.get_running_loop().create_future()
    future.cancel()
    device._input_expected_responses[1] = future
    device._handle_command_or_response(2, 1, TuyaBLECode.FUN_SENDER_DPS, b"\x00")
    assert not device._input_expected_responses


async def test_old_command_cleanup_preserves_new_waiter(device):
    """Cleanup must not remove a reused response ID belonging to a new session."""
    replacement = asyncio.get_running_loop().create_future()
    old_waiters = []

    async def send(packets):
        old_waiters.extend(device._input_expected_responses.values())
        device._input_expected_responses[1] = replacement
        raise BleakError("Old write failed")

    device._int_send_packet_while_connected = AsyncMock(side_effect=send)
    with pytest.raises(BleakError):
        await device._send_packet_while_connected(
            TuyaBLECode.FUN_SENDER_DPS, b"data", 0, True
        )
    assert old_waiters[0].cancelled()
    assert device._input_expected_responses[1] is replacement
    replacement.cancel()
