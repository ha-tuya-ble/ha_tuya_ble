"""Regression tests for awaiting button commands."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError

from custom_components.tuya_ble.button import TuyaBLEButton
from custom_components.tuya_ble.tuya_ble.const import TuyaBLEDataPointType
from custom_components.tuya_ble.tuya_ble.tuya_ble import TuyaBLEDevice


@pytest.fixture
def button() -> TuyaBLEButton:
    """Create a button using real datapoints and a mocked BLE sender."""
    device = TuyaBLEDevice(
        Mock(), BLEDevice("11:22:33:44:55:66", "Test device", {}, rssi=-50)
    )
    device._send_datapoints = AsyncMock()
    button = TuyaBLEButton.__new__(TuyaBLEButton)
    button._device = device
    button._product = SimpleNamespace(lock=None)
    button._mapping = SimpleNamespace(
        dp_id=1,
        dp_type=None,
        value=None,
        description=SimpleNamespace(key="push"),
    )
    return button


async def test_press_waits_for_command(button):
    """Press must remain pending until the BLE command finishes."""
    started = asyncio.Event()
    finished = asyncio.Event()

    async def send(datapoint_ids):
        started.set()
        await finished.wait()

    button._device._send_datapoints.side_effect = send
    press = asyncio.create_task(button.async_press())
    await started.wait()
    assert not press.done()
    finished.set()
    await press


@pytest.mark.parametrize("kind", ["toggle", "trigger", "enum", "raw_unlock"])
async def test_press_propagates_command_failure(button, kind):
    """Each command branch must propagate failure to the caller."""
    if kind == "trigger":
        button._mapping.value = True
    elif kind == "enum":
        button._mapping.dp_type = TuyaBLEDataPointType.DT_ENUM
        button._mapping.value = 2
    elif kind == "raw_unlock":
        button._device._device_info = SimpleNamespace(product_id="oyqux5vv")
        button._mapping.description.key = "bluetooth_unlock"
    button._device._send_datapoints.side_effect = BleakError("Write failed")
    with pytest.raises(BleakError, match="Write failed"):
        await button.async_press()


async def test_concurrent_presses_toggle_separately(button):
    """Rapid presses must calculate their toggles when each command starts."""
    first_started = asyncio.Event()
    finish_first = asyncio.Event()
    values = []

    async def send(datapoint_ids):
        values.append(button._device.datapoints[1].value)
        if len(values) == 1:
            first_started.set()
            await finish_first.wait()

    button._device._send_datapoints.side_effect = send
    first_press = asyncio.create_task(button.async_press())
    await first_started.wait()
    await button.async_press()
    finish_first.set()
    await first_press
    assert values == [True, False]
