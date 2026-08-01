"""Tests for Tuya BLE classic and protocol-v2 security."""

from unittest.mock import AsyncMock, Mock

from bleak.backends.device import BLEDevice
from homeassistant.const import (
    CONF_COUNTRY_CODE,
    CONF_DEVICE_ID,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
import pytest

from custom_components.tuya_ble.cloud import HASSTuyaBLEDeviceManager
from custom_components.tuya_ble.config_flow import _try_login
from custom_components.tuya_ble.const import (
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_CATEGORY,
    CONF_DEVICE_NAME,
    CONF_LOCAL_KEY,
    CONF_PRODUCT_ID,
    CONF_PRODUCT_MODEL,
    CONF_PRODUCT_NAME,
    CONF_SEC_KEY,
    CONF_UUID,
    TUYA_COUNTRIES,
)
from custom_components.tuya_ble.diagnostics import TO_REDACT
from custom_components.tuya_ble.tuya_ble import (
    TuyaBLEDevice,
    TuyaBLEDeviceCredentials,
)
from custom_components.tuya_ble.tuya_ble.const import TuyaBLECode
from custom_components.tuya_ble.tuya_ble.security import TuyaBLESecurityMaterial


LOCAL_KEY = "0123456789abcdef"
SEC_KEY = "fedcba9876543210"
DEVICE_RANDOM = bytes.fromhex("010203040506")


def _make_device() -> TuyaBLEDevice:
    ble_device = BLEDevice(
        name="security-test",
        address="11:22:33:44:55:66",
        details="",
        rssi=-50,
    )
    return TuyaBLEDevice(Mock(), ble_device)


def test_protocol_v2_security_material() -> None:
    """A SecKey enables protocol-v2 derivation and security levels 14/15."""
    material = TuyaBLESecurityMaterial(LOCAL_KEY, SEC_KEY)

    assert material.protocol_v2
    assert material.login_flag == 14
    assert material.session_flag == 15
    assert material.pairing_login_key == b"012345"
    assert material.login_key.hex() == "957b49743a06a938c9246950faadbaa9"
    assert (
        material.session_key(DEVICE_RANDOM).hex() == "316fa9b0eab1ca83b7ffff2e97379659"
    )


def test_classic_security_material() -> None:
    """Devices without a SecKey keep the classic derivation and levels 4/5."""
    material = TuyaBLESecurityMaterial(LOCAL_KEY)

    assert not material.protocol_v2
    assert material.login_flag == 4
    assert material.session_flag == 5
    assert material.pairing_login_key == b"012345"
    assert material.login_key.hex() == "d6a9a933c8aafc51e55ac0662b6e4d4a"
    assert (
        material.session_key(DEVICE_RANDOM).hex() == "a776a41c02fd75d3831a926549482d93"
    )


@pytest.mark.parametrize(
    ("local_key", "sec_key"),
    (
        ("short", None),
        (LOCAL_KEY, "too-short"),
        ("clé-non-ascii", None),
    ),
)
def test_security_material_validates_key_lengths_and_encoding(
    local_key: str, sec_key: str | None
) -> None:
    """Invalid key material is rejected instead of silently downgrading."""
    with pytest.raises(ValueError):
        TuyaBLESecurityMaterial(local_key, sec_key)


def test_protocol_v2_packets_use_security_levels_14_and_15() -> None:
    """Outgoing and incoming packet key selection supports levels 14/15."""
    device = _make_device()
    material = TuyaBLESecurityMaterial(LOCAL_KEY, SEC_KEY)
    device._security_material = material
    device._login_key = material.login_key
    device._session_key = material.session_key(DEVICE_RANDOM)
    device._protocol_version = 2

    login_packets = device._build_packets(
        1, TuyaBLECode.FUN_SENDER_DEVICE_INFO, bytes()
    )
    session_packets = device._build_packets(
        2, TuyaBLECode.FUN_SENDER_DEVICE_STATUS, bytes()
    )

    assert login_packets[0][3] == 14
    assert session_packets[0][3] == 15
    assert device._get_key(14) == device._login_key
    assert device._get_key(15) == device._session_key


def test_device_info_uses_protocol_v2_session_derivation() -> None:
    """The device random is combined with both stored keys for the session."""
    device = _make_device()
    material = TuyaBLESecurityMaterial(LOCAL_KEY, SEC_KEY)
    device._security_material = material
    response = bytearray(46)
    response[6:12] = DEVICE_RANDOM

    device._handle_command_or_response(
        3, 0, TuyaBLECode.FUN_SENDER_DEVICE_INFO, response
    )

    assert device._session_key == material.session_key(DEVICE_RANDOM)


async def test_sec_key_is_loaded_from_saved_device_options(
    hass: HomeAssistant,
) -> None:
    """The optional device SecKey reaches the runtime credentials object."""
    data = {
        CONF_UUID: "1234567890abcdef",
        CONF_LOCAL_KEY: LOCAL_KEY,
        CONF_SEC_KEY: SEC_KEY,
        CONF_DEVICE_ID: "12345678901234567890",
        CONF_CATEGORY: "test",
        CONF_PRODUCT_ID: "test-product",
        CONF_DEVICE_NAME: "Security test",
        CONF_PRODUCT_MODEL: "TEST",
        CONF_PRODUCT_NAME: "Security test",
    }
    manager = HASSTuyaBLEDeviceManager(hass, data)

    credentials = await manager.get_device_credentials("11:22:33:44:55:66")

    assert credentials is not None
    assert credentials.sec_key == SEC_KEY


async def test_login_flow_preserves_optional_sec_key() -> None:
    """The password-style config field is persisted with device options."""
    manager = Mock(spec=HASSTuyaBLEDeviceManager)
    manager._login = AsyncMock(return_value={"success": True})
    errors = {}
    placeholders = {}
    country = TUYA_COUNTRIES[0]

    data = await _try_login(
        manager,
        {
            CONF_COUNTRY_CODE: country.name,
            CONF_ACCESS_ID: "test-access-id",
            CONF_ACCESS_SECRET: "test-access-secret",
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "test-password",
            CONF_SEC_KEY: SEC_KEY,
        },
        errors,
        placeholders,
    )

    assert data is not None
    assert data[CONF_SEC_KEY] == SEC_KEY
    assert not errors


def test_credentials_and_diagnostics_redact_both_keys() -> None:
    """Neither credential rendering nor diagnostics expose key material."""
    credentials = TuyaBLEDeviceCredentials(
        uuid="1234567890abcdef",
        local_key=LOCAL_KEY,
        device_id="12345678901234567890",
        category="test",
        product_id="test-product",
        device_name="Security test",
        product_model="TEST",
        product_name="Security test",
        functions=[],
        status_range=[],
        sec_key=SEC_KEY,
    )

    for rendered in (str(credentials), repr(credentials)):
        assert LOCAL_KEY not in rendered
        assert SEC_KEY not in rendered
    material = TuyaBLESecurityMaterial(LOCAL_KEY, SEC_KEY)
    for rendered in (str(material), repr(material)):
        assert LOCAL_KEY not in rendered
        assert SEC_KEY not in rendered
    assert CONF_LOCAL_KEY in TO_REDACT
    assert CONF_SEC_KEY in TO_REDACT
    assert CONF_ACCESS_SECRET in TO_REDACT
