"""Tests for Tuya BLE protocol-v4 datapoint transport."""

import asyncio
from unittest.mock import AsyncMock, Mock

from bleak.backends.device import BLEDevice
import pytest

from custom_components.tuya_ble.tuya_ble import (
    TuyaBLEDataPointType,
    TuyaBLEDevice,
)
from custom_components.tuya_ble.tuya_ble.const import TuyaBLECode
from custom_components.tuya_ble.tuya_ble.exceptions import TuyaBLEDeviceError


def _make_device() -> TuyaBLEDevice:
    ble_device = BLEDevice(
        name="protocol-v4-test",
        address="11:22:33:44:55:66",
        details="",
        rssi=-50,
    )
    return TuyaBLEDevice(Mock(), ble_device)


async def test_protocol_v4_write_uses_two_byte_datapoint_length() -> None:
    """Protocol v4 writes use command 0x0027 and a four-byte DP sequence."""
    device = _make_device()
    device._protocol_version = 4
    datapoint = device.datapoints.get_or_create(
        105, TuyaBLEDataPointType.DT_BOOL, False
    )
    datapoint._value = True
    device._get_seq_num = AsyncMock(return_value=0x01020304)
    device._send_packet = AsyncMock()

    await device._send_datapoints([105])

    device._send_packet.assert_awaited_once_with(
        TuyaBLECode.FUN_SENDER_DPS_V4,
        bytes.fromhex("00 01020304 69 01 0001 01"),
    )


async def test_protocol_v3_write_keeps_one_byte_datapoint_length() -> None:
    """The shared encoder preserves the existing protocol-v3 wire format."""
    device = _make_device()
    device._protocol_version = 3
    datapoint = device.datapoints.get_or_create(
        105, TuyaBLEDataPointType.DT_BOOL, False
    )
    datapoint._value = True
    device._send_packet = AsyncMock()

    await device._send_datapoints([105])

    device._send_packet.assert_awaited_once_with(
        TuyaBLECode.FUN_SENDER_DPS,
        bytes.fromhex("69 01 01 01"),
    )


async def test_protocol_v4_atomic_write_uses_v4_encoder() -> None:
    """Atomic writes dispatch through the protocol-specific encoder."""
    device = _make_device()
    device._protocol_version = 4
    device.datapoints.get_or_create(105, TuyaBLEDataPointType.DT_BOOL, False)
    device.datapoints.get_or_create(106, TuyaBLEDataPointType.DT_VALUE, 0)
    device._get_seq_num = AsyncMock(return_value=0x01020304)
    device._send_packet = AsyncMock()

    await device.set_multiple_values({105: True, 106: 60})

    device._send_packet.assert_awaited_once_with(
        TuyaBLECode.FUN_SENDER_DPS_V4,
        bytes.fromhex("00 01020304 69 01 0001 01 6a 02 0004 0000003c"),
    )


async def test_protocol_v4_report_updates_datapoint_and_is_acknowledged() -> None:
    """Command 0x8006 reports a v4 datapoint and receives a metadata echo."""
    device = _make_device()
    device._send_response = AsyncMock()
    report = bytes.fromhex("00 01020304 00 00 0b 02 0004 00000057")

    device._handle_command_or_response(23, 0, TuyaBLECode.FUN_RECEIVE_DP_V4, report)
    await asyncio.sleep(0)

    datapoint = device.datapoints[11]
    assert datapoint is not None
    assert datapoint.type == TuyaBLEDataPointType.DT_VALUE
    assert datapoint.value == 87
    assert datapoint.flags == 0
    device._send_response.assert_awaited_once_with(
        TuyaBLECode.FUN_RECEIVE_DP_V4,
        bytes.fromhex("00 01020304 00 00 00"),
        23,
    )


async def test_protocol_v4_report_honors_no_ack_flag() -> None:
    """Bit 7 in the v4 send flags suppresses the acknowledgement."""
    device = _make_device()
    device._send_response = AsyncMock()
    report = bytes.fromhex("00 01020304 80 00 0b 02 0004 00000057")

    device._handle_command_or_response(23, 0, TuyaBLECode.FUN_RECEIVE_DP_V4, report)
    await asyncio.sleep(0)

    assert device.datapoints[11].value == 87
    device._send_response.assert_not_awaited()


async def test_protocol_v4_timestamped_report() -> None:
    """Command 0x8007 carries a timestamp before its v4 datapoints."""
    device = _make_device()
    device._send_response = AsyncMock()
    report = bytes.fromhex("00 01020304 00 04 01 66aabbcc 0b 02 0004 00000062")

    device._handle_command_or_response(
        24, 0, TuyaBLECode.FUN_RECEIVE_TIME_DP_V4, report
    )
    await asyncio.sleep(0)

    datapoint = device.datapoints[11]
    assert datapoint is not None
    assert datapoint.value == 98
    assert datapoint.flags == 4
    assert datapoint.timestamp == 0x66AABBCC
    device._send_response.assert_awaited_once_with(
        TuyaBLECode.FUN_RECEIVE_TIME_DP_V4,
        bytes.fromhex("00 01020304 00 04 00"),
        24,
    )


async def test_protocol_v4_write_response_propagates_device_error() -> None:
    """The final byte of a 0x0027 response is its result code."""
    device = _make_device()
    response = asyncio.get_running_loop().create_future()
    device._input_expected_responses[9] = response

    device._handle_command_or_response(
        25,
        9,
        TuyaBLECode.FUN_SENDER_DPS_V4,
        bytes.fromhex("00 01020304 02"),
    )

    with pytest.raises(TuyaBLEDeviceError):
        await response
