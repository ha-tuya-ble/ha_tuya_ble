"""Test the CBF02V2 actuator's inverted read/write behavior."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.tuya_ble.switch import get_inverted_switch, set_inverted_switch
from custom_components.tuya_ble.tuya_ble import TuyaBLEDataPointType


@pytest.mark.parametrize(("raw_value", "expected"), [(False, True), (True, False)])
def test_inverted_switch_report(raw_value: bool, expected: bool) -> None:
    """The reported false position is shown as on, and true as off."""
    entity = SimpleNamespace(
        _mapping=SimpleNamespace(dp_id=1),
        _device=SimpleNamespace(datapoints={1: SimpleNamespace(value=raw_value)}),
    )

    assert get_inverted_switch(entity, None) is expected


def test_inverted_switch_without_report() -> None:
    """Do not turn a missing initial report into an on state."""
    entity = SimpleNamespace(
        _mapping=SimpleNamespace(dp_id=1),
        _device=SimpleNamespace(datapoints={1: None}),
    )

    assert get_inverted_switch(entity, None) is False


@pytest.mark.parametrize(("requested", "raw_value"), [(True, False), (False, True)])
async def test_inverted_switch_command(requested: bool, raw_value: bool) -> None:
    """Both on and off create and send an inverted boolean DP1 command."""
    datapoint = SimpleNamespace(set_value=AsyncMock())
    datapoints = SimpleNamespace(get_or_create=Mock(return_value=datapoint))
    tasks = []

    def create_task(coro):
        task = asyncio.create_task(coro)
        tasks.append(task)
        return task

    entity = SimpleNamespace(
        _mapping=SimpleNamespace(dp_id=1),
        _device=SimpleNamespace(datapoints=datapoints),
        _hass=SimpleNamespace(create_task=create_task),
    )

    set_inverted_switch(entity, None, requested)
    await asyncio.gather(*tasks)

    datapoints.get_or_create.assert_called_once_with(
        1, TuyaBLEDataPointType.DT_BOOL, raw_value
    )
    datapoint.set_value.assert_awaited_once_with(raw_value)
