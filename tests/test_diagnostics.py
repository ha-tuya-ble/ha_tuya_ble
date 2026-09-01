"""Test Tuya BLE diagnostics."""

from unittest.mock import AsyncMock, Mock, patch

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tuya_ble.const import (
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_LOCAL_KEY,
    CONF_SEC_KEY,
    CONF_UUID,
    DOMAIN,
)
from custom_components.tuya_ble.devices import (
    TuyaBLECoordinator,
    TuyaBLEData,
    TuyaBLEDevice,
    TuyaBLEProductInfo,
)
from custom_components.tuya_ble.diagnostics import async_get_config_entry_diagnostics
from custom_components.tuya_ble.tuya_ble import TuyaBLEDataPointType

from . import DEVICE_ADDRESS


async def test_diagnostics_unloaded_entry(hass: HomeAssistant) -> None:
    """Test diagnostics output when the config entry is not loaded."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "address": DEVICE_ADDRESS,
            CONF_ACCESS_ID: "secret_access_id",
            CONF_LOCAL_KEY: "secret_local_key",
        },
        title="Unloaded Entry",
    )
    entry.add_to_hass(hass)

    with patch("homeassistant.components.bluetooth.async_last_service_info", return_value=None), patch(
        "homeassistant.components.bluetooth.async_scanner_count", return_value=2
    ):
        diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["entry"]["title"] == "Unloaded Entry"
    assert diagnostics["entry"]["data"][CONF_ACCESS_ID] == "**REDACTED**"
    assert diagnostics["entry"]["data"][CONF_LOCAL_KEY] == "**REDACTED**"
    assert diagnostics["bluetooth"] == {
        "seen": False,
        "rssi": None,
        "source": None,
        "name": None,
        "connectable": None,
        "connectable_scanner_count": 2,
    }
    assert diagnostics["device"] == {"loaded": False}


async def test_diagnostics_loaded_entry(hass: HomeAssistant) -> None:
    """Test diagnostics output when the config entry is loaded with device data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "address": DEVICE_ADDRESS,
            CONF_ACCESS_ID: "secret_access_id",
            CONF_ACCESS_SECRET: "secret_access_secret",
            CONF_LOCAL_KEY: "secret_local_key",
            CONF_SEC_KEY: "secret_sec_key",
            CONF_UUID: "secret_uuid",
        },
        options={},
        title="Loaded Entry",
    )
    entry.add_to_hass(hass)

    ble_device = Mock(name="mock_ble_device", address=DEVICE_ADDRESS, rssi=-65)
    manager = Mock()
    manager.get_device_credentials = AsyncMock(return_value=None)

    device = TuyaBLEDevice(manager, ble_device)
    await device.initialize()

    # Add datapoints to test formatting
    device.datapoints._update_from_device(1, 0, 0, TuyaBLEDataPointType.DT_BOOL, True)
    device.datapoints._update_from_device(2, 0, 0, TuyaBLEDataPointType.DT_VALUE, 42)
    device.datapoints._update_from_device(
        3, 0, 0, TuyaBLEDataPointType.DT_RAW, bytes.fromhex("01020304")
    )

    product_info = TuyaBLEProductInfo(name="Test Product", manufacturer="Test Maker")
    coordinator = TuyaBLECoordinator(hass, device)

    data = TuyaBLEData(
        title="Loaded Entry",
        device=device,
        product=product_info,
        manager=manager,
        coordinator=coordinator,
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = data

    service_info = Mock(
        spec=BluetoothServiceInfoBleak,
        rssi=-65,
        source="local_adapter",
        connectable=True,
    )
    service_info.name = "TuyaBLEDevice"

    with patch(
        "homeassistant.components.bluetooth.async_last_service_info", return_value=service_info
    ), patch("homeassistant.components.bluetooth.async_scanner_count", return_value=3):
        diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    # Verify entry redaction
    assert diagnostics["entry"]["data"][CONF_ACCESS_ID] == "**REDACTED**"
    assert diagnostics["entry"]["data"][CONF_ACCESS_SECRET] == "**REDACTED**"
    assert diagnostics["entry"]["data"][CONF_LOCAL_KEY] == "**REDACTED**"
    assert diagnostics["entry"]["data"][CONF_SEC_KEY] == "**REDACTED**"
    assert diagnostics["entry"]["data"][CONF_UUID] == "**REDACTED**"

    # Verify bluetooth details
    assert diagnostics["bluetooth"] == {
        "seen": True,
        "rssi": -65,
        "source": "local_adapter",
        "name": "TuyaBLEDevice",
        "connectable": True,
        "connectable_scanner_count": 3,
    }

    # Verify device state details
    assert diagnostics["device"]["loaded"] is True
    assert diagnostics["device"]["address"] == DEVICE_ADDRESS
    assert diagnostics["device"]["keep_connection"] is True
    assert diagnostics["device"]["coordinator_connected"] is False

    # Verify product info
    assert diagnostics["product_info"] == {
        "manufacturer": "Test Maker",
        "name": "Test Product",
    }

    # Verify formatted datapoints
    assert diagnostics["datapoints"] == [
        {"id": 1, "type": "DT_BOOL", "value": True},
        {"id": 2, "type": "DT_VALUE", "value": 42},
        {"id": 3, "type": "DT_RAW", "value": "01020304"},
    ]
