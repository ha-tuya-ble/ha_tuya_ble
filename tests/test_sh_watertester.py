"""Test for Tuya BLE Water Quality Tester (BLE-YL01)."""

from unittest.mock import Mock, AsyncMock
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.button import ButtonEntityDescription
from homeassistant.components.number import NumberEntityDescription

from custom_components.tuya_ble.sensor import TuyaBLESensor, get_mapping_by_device
from custom_components.tuya_ble.select import TuyaBLESelect, get_mapping_by_device as get_select_mapping
from custom_components.tuya_ble.button import TuyaBLEButton, get_mapping_by_device as get_button_mapping
from custom_components.tuya_ble.number import TuyaBLENumber, get_mapping_by_device as get_number_mapping
from custom_components.tuya_ble.light import TuyaBLELight, get_mapping_by_device as get_light_mapping, TuyaLightEntityDescription
from custom_components.tuya_ble.tuya_ble import TuyaBLEDataPointType, TuyaBLEDeviceCredentials

from . import *

async def test_sh_watertester_sensor(hass: HomeAssistant) -> None:
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.tuya_ble.const import DOMAIN
    from custom_components.tuya_ble.cloud import HASSTuyaBLEDeviceManager
    from custom_components.tuya_ble.devices import TuyaBLEDevice, TuyaBLEProductInfo, TuyaBLECoordinator, TuyaBLEData
    from bleak.backends.device import BLEDevice

    config = {
        DEVICE_NAME: {
            **DEVICE_CONFIG,
            "entities": [],
        }
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "devices": config,
            "address": DEVICE_ADDRESS,
        },
        title="Mock TuyaBLE SH",
    )
    entry.add_to_hass(hass)

    ble_device = BLEDevice(name="yieryi_yl01", address="11:22:33", details="", rssi=-50)
    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())
    device = TuyaBLEDevice(manager, ble_device)
    await device.initialize()

    # Assign sh category and v1jqz5cy product ID to credentials
    device._device_info = TuyaBLEDeviceCredentials(
        uuid="",
        local_key="wV[NcWGUSFF`dSgO",
        device_id="767823809c9c1f458745",
        category="sh",
        product_id="v1jqz5cy",
        device_name="Water Quality Tester",
        product_model="BLE-YL01",
        product_name="Water Quality Monitor",
        functions=[],
        status_range=[],
    )

    product_info = TuyaBLEProductInfo("Yieryi Water Quality Monitor")
    device._send_datapoints = AsyncMock()

    hass.data.setdefault(DOMAIN, {})
    coordinator = TuyaBLECoordinator(hass, device)

    # Verify sensor mappings are retrieved successfully
    sensor_mappings = get_mapping_by_device(device)
    assert len(sensor_mappings) > 0

    # Let's map TDS, pH, Temp, EC, ORP, CL, Salinity, and Battery
    tds_mapping = next(m for m in sensor_mappings if m.description.key == "tds")
    temp_mapping = next(m for m in sensor_mappings if m.description.key == "temperature")
    ph_mapping = next(m for m in sensor_mappings if m.description.key == "ph")
    ec_mapping = next(m for m in sensor_mappings if m.description.key == "ec")
    orp_mapping = next(m for m in sensor_mappings if m.description.key == "orp")
    cl_mapping = next(m for m in sensor_mappings if m.description.key == "cl")
    sal_mapping = next(m for m in sensor_mappings if m.description.key == "salinity")
    bat_mapping = next(m for m in sensor_mappings if m.description.key == "battery")

    # Instantiate sensor entities
    tds_sensor = TuyaBLESensor(hass, coordinator, device, product_info, tds_mapping)
    temp_sensor = TuyaBLESensor(hass, coordinator, device, product_info, temp_mapping)
    ph_sensor = TuyaBLESensor(hass, coordinator, device, product_info, ph_mapping)
    ec_sensor = TuyaBLESensor(hass, coordinator, device, product_info, ec_mapping)
    orp_sensor = TuyaBLESensor(hass, coordinator, device, product_info, orp_mapping)
    cl_sensor = TuyaBLESensor(hass, coordinator, device, product_info, cl_mapping)
    sal_sensor = TuyaBLESensor(hass, coordinator, device, product_info, sal_mapping)
    bat_sensor = TuyaBLESensor(hass, coordinator, device, product_info, bat_mapping)

    # Mock async_write_ha_state on all sensors
    for sensor in [tds_sensor, temp_sensor, ph_sensor, ec_sensor, orp_sensor, cl_sensor, sal_sensor, bat_sensor]:
        sensor.async_write_ha_state = Mock()

    coordinator._async_handle_connect()

    # Update states and assert values are scaled correctly
    device.datapoints._update_from_device(1, 0, 0, TuyaBLEDataPointType.DT_VALUE, 300) # TDS = 300 ppm
    tds_sensor._handle_coordinator_update()
    assert tds_sensor.native_value == 300

    device.datapoints._update_from_device(2, 0, 0, TuyaBLEDataPointType.DT_VALUE, 255) # Temp = 25.5 C
    temp_sensor._handle_coordinator_update()
    assert temp_sensor.native_value == 25.5

    device.datapoints._update_from_device(10, 0, 0, TuyaBLEDataPointType.DT_VALUE, 72) # pH = 7.2
    ph_sensor._handle_coordinator_update()
    assert ph_sensor.native_value == 7.2

    device.datapoints._update_from_device(11, 0, 0, TuyaBLEDataPointType.DT_VALUE, 1200) # EC = 1200
    ec_sensor._handle_coordinator_update()
    assert ec_sensor.native_value == 1200

    device.datapoints._update_from_device(101, 0, 0, TuyaBLEDataPointType.DT_VALUE, 250) # ORP = 250 mV
    orp_sensor._handle_coordinator_update()
    assert orp_sensor.native_value == 250

    device.datapoints._update_from_device(102, 0, 0, TuyaBLEDataPointType.DT_VALUE, 15) # CL = 1.5 mg/L
    cl_sensor._handle_coordinator_update()
    assert cl_sensor.native_value == 1.5

    device.datapoints._update_from_device(117, 0, 0, TuyaBLEDataPointType.DT_VALUE, 500) # Salinity = 500 ppm
    sal_sensor._handle_coordinator_update()
    assert sal_sensor.native_value == 500

    device.datapoints._update_from_device(7, 0, 0, TuyaBLEDataPointType.DT_VALUE, 95) # Battery = 95%
    bat_sensor._handle_coordinator_update()
    assert bat_sensor.native_value == 95


async def test_sh_watertester_select(hass: HomeAssistant) -> None:
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.tuya_ble.const import DOMAIN
    from custom_components.tuya_ble.cloud import HASSTuyaBLEDeviceManager
    from custom_components.tuya_ble.devices import TuyaBLEDevice, TuyaBLEProductInfo, TuyaBLECoordinator, TuyaBLEData
    from bleak.backends.device import BLEDevice

    config = {DEVICE_NAME: {**DEVICE_CONFIG, "entities": []}}
    entry = MockConfigEntry(domain=DOMAIN, data={"devices": config, "address": DEVICE_ADDRESS}, title="Mock Select")
    entry.add_to_hass(hass)

    ble_device = BLEDevice(name="yieryi_yl01", address="11:22:33", details="", rssi=-50)
    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())
    device = TuyaBLEDevice(manager, ble_device)
    await device.initialize()

    device._device_info = TuyaBLEDeviceCredentials(
        uuid="",
        local_key="wV[NcWGUSFF`dSgO",
        device_id="767823809c9c1f458745",
        category="sh",
        product_id="v1jqz5cy",
        device_name="Water Quality Tester",
        product_model="BLE-YL01",
        product_name="Water Quality Monitor",
        functions=[],
        status_range=[],
    )

    product_info = TuyaBLEProductInfo("Yieryi Water Quality Monitor")
    device._send_datapoints = AsyncMock()
    coordinator = TuyaBLECoordinator(hass, device)

    select_mappings = get_select_mapping(device)
    assert len(select_mappings) == 1
    buf_mapping = select_mappings[0]

    select_entity = TuyaBLESelect(hass, coordinator, device, product_info, buf_mapping)
    select_entity.async_write_ha_state = Mock()
    coordinator._async_handle_connect()

    # Initial state or default value
    assert select_entity.current_option is None

    # Update state to EUStandard
    device.datapoints._update_from_device(103, 0, 0, TuyaBLEDataPointType.DT_STRING, "EUStandard")
    select_entity._handle_coordinator_update()
    assert select_entity.current_option == "eu_standard"

    # Select another option
    select_entity.select_option("asia_standard")
    await hass.async_block_till_done()
    device._send_datapoints.assert_called_once_with([103])
    assert device.datapoints[103].value == "AsiaStandard"


async def test_sh_watertester_light(hass: HomeAssistant) -> None:
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.tuya_ble.const import DOMAIN
    from custom_components.tuya_ble.cloud import HASSTuyaBLEDeviceManager
    from custom_components.tuya_ble.devices import TuyaBLEDevice, TuyaBLEProductInfo, TuyaBLECoordinator, TuyaBLEData
    from bleak.backends.device import BLEDevice

    config = {DEVICE_NAME: {**DEVICE_CONFIG, "entities": []}}
    entry = MockConfigEntry(domain=DOMAIN, data={"devices": config, "address": DEVICE_ADDRESS}, title="Mock Light")
    entry.add_to_hass(hass)

    ble_device = BLEDevice(name="yieryi_yl01", address="11:22:33", details="", rssi=-50)
    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())
    device = TuyaBLEDevice(manager, ble_device)
    await device.initialize()

    device._device_info = TuyaBLEDeviceCredentials(
        uuid="",
        local_key="wV[NcWGUSFF`dSgO",
        device_id="767823809c9c1f458745",
        category="sh",
        product_id="v1jqz5cy",
        device_name="Water Quality Tester",
        product_model="BLE-YL01",
        product_name="Water Quality Monitor",
        functions=[],
        status_range=[],
    )

    product_info = TuyaBLEProductInfo("Yieryi Water Quality Monitor")
    device._send_datapoints = AsyncMock()
    coordinator = TuyaBLECoordinator(hass, device)

    light_mappings = get_light_mapping(device)
    assert len(light_mappings) == 1
    backlight_mapping = light_mappings[0]

    # Populate device status with key so find_dpid works
    device.status["switch_led"] = False
    device.function["switch_led"] = Mock(dp_id=104, type="Boolean")

    light_entity = TuyaBLELight(hass, coordinator, device, product_info, backlight_mapping)
    light_entity.async_write_ha_state = Mock()
    coordinator._async_handle_connect()

    assert light_entity.is_on is False

    # Turn on backlight
    light_entity.turn_on()
    await hass.async_block_till_done()
    device._send_datapoints.assert_called_with([104])
    assert device.datapoints[104].value is True


async def test_sh_watertester_button(hass: HomeAssistant) -> None:
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.tuya_ble.const import DOMAIN
    from custom_components.tuya_ble.cloud import HASSTuyaBLEDeviceManager
    from custom_components.tuya_ble.devices import TuyaBLEDevice, TuyaBLEProductInfo, TuyaBLECoordinator, TuyaBLEData
    from bleak.backends.device import BLEDevice

    config = {DEVICE_NAME: {**DEVICE_CONFIG, "entities": []}}
    entry = MockConfigEntry(domain=DOMAIN, data={"devices": config, "address": DEVICE_ADDRESS}, title="Mock Button")
    entry.add_to_hass(hass)

    ble_device = BLEDevice(name="yieryi_yl01", address="11:22:33", details="", rssi=-50)
    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())
    device = TuyaBLEDevice(manager, ble_device)
    await device.initialize()

    device._device_info = TuyaBLEDeviceCredentials(
        uuid="",
        local_key="wV[NcWGUSFF`dSgO",
        device_id="767823809c9c1f458745",
        category="sh",
        product_id="v1jqz5cy",
        device_name="Water Quality Tester",
        product_model="BLE-YL01",
        product_name="Water Quality Monitor",
        functions=[],
        status_range=[],
    )

    product_info = TuyaBLEProductInfo("Yieryi Water Quality Monitor")
    device._send_datapoints = AsyncMock()
    coordinator = TuyaBLECoordinator(hass, device)

    button_mappings = get_button_mapping(device)
    assert len(button_mappings) == 2

    update_mapping = next(m for m in button_mappings if m.description.key == "update")
    reset_mapping = next(m for m in button_mappings if m.description.key == "ph_reset")

    update_btn = TuyaBLEButton(hass, coordinator, device, product_info, update_mapping)
    update_btn.async_write_ha_state = Mock()
    reset_btn = TuyaBLEButton(hass, coordinator, device, product_info, reset_mapping)
    reset_btn.async_write_ha_state = Mock()
    coordinator._async_handle_connect()

    # Press update (DT_VALUE)
    update_btn.press()
    await hass.async_block_till_done()
    device._send_datapoints.assert_any_call([105])
    assert device.datapoints[105].value == 1

    # Press pH reset (DT_BOOL)
    reset_btn.press()
    await hass.async_block_till_done()
    device._send_datapoints.assert_any_call([118])
    assert device.datapoints[118].value is True


async def test_sh_watertester_number(hass: HomeAssistant) -> None:
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.tuya_ble.const import DOMAIN
    from custom_components.tuya_ble.cloud import HASSTuyaBLEDeviceManager
    from custom_components.tuya_ble.devices import TuyaBLEDevice, TuyaBLEProductInfo, TuyaBLECoordinator, TuyaBLEData
    from bleak.backends.device import BLEDevice

    config = {DEVICE_NAME: {**DEVICE_CONFIG, "entities": []}}
    entry = MockConfigEntry(domain=DOMAIN, data={"devices": config, "address": DEVICE_ADDRESS}, title="Mock Number")
    entry.add_to_hass(hass)

    ble_device = BLEDevice(name="yieryi_yl01", address="11:22:33", details="", rssi=-50)
    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())
    device = TuyaBLEDevice(manager, ble_device)
    await device.initialize()

    device._device_info = TuyaBLEDeviceCredentials(
        uuid="",
        local_key="wV[NcWGUSFF`dSgO",
        device_id="767823809c9c1f458745",
        category="sh",
        product_id="v1jqz5cy",
        device_name="Water Quality Tester",
        product_model="BLE-YL01",
        product_name="Water Quality Monitor",
        functions=[],
        status_range=[],
    )

    product_info = TuyaBLEProductInfo("Yieryi Water Quality Monitor")
    device._send_datapoints = AsyncMock()
    coordinator = TuyaBLECoordinator(hass, device)

    number_mappings = get_number_mapping(device)
    assert len(number_mappings) > 0

    max_ph_mapping = next(m for m in number_mappings if m.description.key == "max_ph")
    ph_cal_mapping = next(m for m in number_mappings if m.description.key == "ph_calibration")
    max_ec_mapping = next(m for m in number_mappings if m.description.key == "max_ec")

    max_ph_num = TuyaBLENumber(hass, coordinator, device, product_info, max_ph_mapping)
    max_ph_num.async_write_ha_state = Mock()
    ph_cal_num = TuyaBLENumber(hass, coordinator, device, product_info, ph_cal_mapping)
    ph_cal_num.async_write_ha_state = Mock()
    max_ec_num = TuyaBLENumber(hass, coordinator, device, product_info, max_ec_mapping)
    max_ec_num.async_write_ha_state = Mock()
    coordinator._async_handle_connect()

    # Initial or default value
    assert max_ph_num.native_value == 0.0

    # Max pH value parsing and setting (coefficient 10.0)
    device.datapoints._update_from_device(106, 0, 0, TuyaBLEDataPointType.DT_VALUE, 115) # pH 11.5
    max_ph_num._handle_coordinator_update()
    assert max_ph_num.native_value == 11.5

    max_ph_num.set_native_value(12.4)
    await hass.async_block_till_done()
    device._send_datapoints.assert_called_with([106])
    assert device.datapoints[106].value == 124

    # pH Calibration parsing and setting (coefficient 100.0)
    device.datapoints._update_from_device(114, 0, 0, TuyaBLEDataPointType.DT_VALUE, 705) # pH 7.05
    ph_cal_num._handle_coordinator_update()
    assert ph_cal_num.native_value == 7.05

    ph_cal_num.set_native_value(6.84)
    await hass.async_block_till_done()
    device._send_datapoints.assert_called_with([114])
    assert device.datapoints[114].value == 684

    # Max EC parsing and setting (coefficient 1.0)
    device.datapoints._update_from_device(108, 0, 0, TuyaBLEDataPointType.DT_VALUE, 5000)
    max_ec_num._handle_coordinator_update()
    assert max_ec_num.native_value == 5000

    max_ec_num.set_native_value(4500)
    await hass.async_block_till_done()
    device._send_datapoints.assert_called_with([108])
    assert device.datapoints[108].value == 4500
