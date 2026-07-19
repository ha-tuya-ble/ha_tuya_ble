"""Test for YZD05 (d4vpmigg) water valve."""

from custom_components.tuya_ble.devices import get_product_info_by_ids
from custom_components.tuya_ble.number import get_mapping_by_device
from custom_components.tuya_ble.select import (
    get_mapping_by_device as get_select_mapping_by_device,
)
from custom_components.tuya_ble.sensor import (
    get_mapping_by_device as get_sensor_mapping_by_device,
)
from custom_components.tuya_ble.switch import (
    get_mapping_by_device as get_switch_mapping_by_device,
)


class FakeDevice:
    """Fake device to test mapping functions."""

    def __init__(self, category: str, product_id: str):
        self.category = category
        self.product_id = product_id


def test_d4vpmigg_mappings() -> None:
    """Verify that d4vpmigg device mappings are loaded and correct."""
    device = FakeDevice("sfkzq", "d4vpmigg")

    # 1. Product info in devices database
    product_info = get_product_info_by_ids(device.category, device.product_id)
    assert product_info is not None
    assert product_info.name == "Valve controller"
    assert product_info.watervalve is not None
    assert product_info.watervalve.switch == 1
    assert product_info.watervalve.countdown == 11
    assert product_info.watervalve.weather_delay == 10
    assert product_info.watervalve.smart_weather == 13
    assert product_info.watervalve.use_time == 15

    # 2. Number mapping
    number_mappings = get_mapping_by_device(device)
    assert len(number_mappings) > 0
    # countdown_duration should be mapped on DP 11
    assert any(
        m.dp_id == 11 and m.description.key == "countdown_duration"
        for m in number_mappings
    )

    # 3. Select mapping
    select_mappings = get_select_mapping_by_device(device)
    assert len(select_mappings) == 3
    keys = {m.description.key for m in select_mappings}
    assert "weather_delay" in keys
    assert "work_state" in keys
    assert "smart_weather" in keys

    # 4. Sensor mapping
    sensor_mappings = get_sensor_mapping_by_device(device)
    assert len(sensor_mappings) > 0
    dp_ids = {m.dp_id for m in sensor_mappings}
    assert 7 in dp_ids  # battery
    assert 12 in dp_ids  # work_state
    assert 15 in dp_ids  # use_time_one
    assert 9 in dp_ids  # time_use

    # 5. Switch mapping
    switch_mappings = get_switch_mapping_by_device(device)
    assert len(switch_mappings) > 0
    assert any(
        m.dp_id == 1 and m.description.key == "water_valve" for m in switch_mappings
    )
