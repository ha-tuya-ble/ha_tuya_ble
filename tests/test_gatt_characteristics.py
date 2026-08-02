"""Test for dynamic GATT characteristic selection."""

from unittest.mock import AsyncMock, Mock, call, patch
import pytest
from bleak.backends.device import BLEDevice
from custom_components.tuya_ble.tuya_ble import TuyaBLEDevice
from custom_components.tuya_ble.tuya_ble.manager import TuyaBLEDeviceCredentials
from custom_components.tuya_ble.tuya_ble.const import TuyaBLECode
from custom_components.tuya_ble.cloud import HASSTuyaBLEDeviceManager
from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.core import HomeAssistant
from custom_components.tuya_ble.const import DOMAIN

CONFIG = {
    "1234": {
        "address": "11:22:33:44:55:66",
        "device_id": "767823809c9c1f458745",
        "protocol_version": "3.3",
        "local_key": "wV[NcWGUSFF`dSgO",
        "friendly_name": "Local 3G",
    }
}


@pytest.mark.asyncio
async def test_gatt_characteristic_selection_classic(hass: HomeAssistant) -> None:
    """Test that classic GATT characteristics are selected when present."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "devices": CONFIG,
            "address": "11:22:33:44:55:66",
        },
        title="Mock TuyaBLE",
    )
    entry.add_to_hass(hass)

    ble_device = BLEDevice(
        name="bob", address="11:22:33:44:55:66", details="", rssi=-50
    )
    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())

    credentials = TuyaBLEDeviceCredentials(
        uuid="12345678901234567890",
        local_key="wV[NcWGUSFF`dSgO",
        device_id="767823809c9c1f458745",
        category="ms",
        product_id="kpn4zaf7",
        device_name="Mock Lock",
        product_model="BSTUOKEY",
        product_name="BSTUOKEY",
        functions=[],
        status_range=[],
    )

    with patch.object(manager, "get_device_credentials", return_value=credentials):
        device = TuyaBLEDevice(manager, ble_device)
        await device.initialize()
        device._is_paired = True

        # Mock Client
        client = Mock()
        client.is_connected = True
        client.start_notify = AsyncMock()

        # Get characteristic mock setup: classic notify exists, fd50 notify does not
        def get_char(uuid):
            if uuid == "00002b10-0000-1000-8000-00805f9b34fb":
                return Mock()
            return None

        client.services.get_characteristic = Mock(side_effect=get_char)

        with patch(
            "custom_components.tuya_ble.tuya_ble.tuya_ble.establish_connection",
            return_value=client,
        ):
            with patch.object(
                device, "_send_packet_while_connected", return_value=True
            ):
                await device._ensure_connected()

                assert (
                    device._characteristic_notify
                    == "00002b10-0000-1000-8000-00805f9b34fb"
                )
                assert (
                    device._characteristic_write
                    == "00002b11-0000-1000-8000-00805f9b34fb"
                )
                client.start_notify.assert_called_with(
                    "00002b10-0000-1000-8000-00805f9b34fb", device._notification_handler
                )


@pytest.mark.asyncio
async def test_gatt_characteristic_selection_fd50(hass: HomeAssistant) -> None:
    """Test that FD50 GATT characteristics are selected when present."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "devices": CONFIG,
            "address": "11:22:33:44:55:66",
        },
        title="Mock TuyaBLE",
    )
    entry.add_to_hass(hass)

    ble_device = BLEDevice(
        name="bob", address="11:22:33:44:55:66", details="", rssi=-50
    )
    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())

    credentials = TuyaBLEDeviceCredentials(
        uuid="12345678901234567890",
        local_key="wV[NcWGUSFF`dSgO",
        device_id="767823809c9c1f458745",
        category="ms",
        product_id="kpn4zaf7",
        device_name="Mock Lock",
        product_model="BSTUOKEY",
        product_name="BSTUOKEY",
        functions=[],
        status_range=[],
    )

    with patch.object(manager, "get_device_credentials", return_value=credentials):
        device = TuyaBLEDevice(manager, ble_device)
        await device.initialize()
        device._is_paired = True
        device._protocol_version = 4

        # Mock Client
        client = Mock()
        client.is_connected = True
        client.start_notify = AsyncMock()

        # Get characteristic mock setup: fd50 notify exists, classic notify does not
        def get_char(uuid):
            if uuid == "00000002-0000-1001-8001-00805f9b07d0":
                return Mock()
            return None

        client.services.get_characteristic = Mock(side_effect=get_char)

        with patch(
            "custom_components.tuya_ble.tuya_ble.tuya_ble.establish_connection",
            return_value=client,
        ):
            with patch.object(
                device, "_send_packet_while_connected", return_value=True
            ):
                await device._ensure_connected()

                assert (
                    device._characteristic_notify
                    == "00000002-0000-1001-8001-00805f9b07d0"
                )
                assert (
                    device._characteristic_write
                    == "00000001-0000-1001-8001-00805f9b07d0"
                )
                client.start_notify.assert_called_with(
                    "00000002-0000-1001-8001-00805f9b07d0", device._notification_handler
                )
                packets = device._build_packets(
                    1,
                    TuyaBLECode.FUN_SENDER_DEVICE_INFO,
                    bytes(),
                )
                assert packets[0][2] == 0x40


@pytest.mark.asyncio
async def test_yzd02b_fd50_device_info_handshake(hass: HomeAssistant) -> None:
    """Test the product-scoped TuyaOS login framing required by YZD02B."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "devices": CONFIG,
            "address": "11:22:33:44:55:66",
        },
        title="Mock TuyaBLE",
    )
    entry.add_to_hass(hass)

    ble_device = BLEDevice(
        name="bob", address="11:22:33:44:55:66", details="", rssi=-50
    )
    manager = HASSTuyaBLEDeviceManager(hass, entry.options.copy())
    credentials = TuyaBLEDeviceCredentials(
        uuid="12345678901234567890",
        local_key="wV[NcWGUSFF`dSgO",
        device_id="767823809c9c1f458745",
        category="ggq",
        product_id="jntxv3q4",
        device_name="Dual smart irrigation timer",
        product_model="YZD02B",
        product_name="Dual smart irrigation timer",
        functions=[],
        status_range=[],
    )

    with patch.object(manager, "get_device_credentials", return_value=credentials):
        device = TuyaBLEDevice(manager, ble_device)
        await device.initialize()
        device._is_paired = True
        device._protocol_version = 4

        client = Mock()
        client.is_connected = True
        client.start_notify = AsyncMock()
        client.services.get_characteristic = Mock(
            side_effect=lambda uuid: (
                Mock() if uuid == "00000002-0000-1001-8001-00805f9b07d0" else None
            )
        )

        with (
            patch(
                "custom_components.tuya_ble.tuya_ble.tuya_ble.establish_connection",
                return_value=client,
            ),
            patch.object(
                device, "_send_packet_while_connected", return_value=True
            ) as send_packet,
        ):
            await device._ensure_connected()

        client.start_notify.assert_awaited_once_with(
            "00000002-0000-1001-8001-00805f9b07d0",
            device._notification_handler,
            bluez={"use_start_notify": True},
        )
        assert send_packet.await_args_list[0] == call(
            TuyaBLECode.FUN_SENDER_DEVICE_INFO,
            b"\x00\xf3",
            0,
            True,
        )

        packets = device._build_packets(
            1,
            TuyaBLECode.FUN_SENDER_DEVICE_INFO,
            b"\x00\xf3",
        )
        assert packets[0][2] == 0x20
