"""Tests for one-shot Tuya mobile protocol-v2 credential retrieval."""

from dataclasses import replace
from importlib.metadata import version
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.const import (
    CONF_ADDRESS,
    CONF_COUNTRY_CODE,
    CONF_DEVICE_ID,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from tuya_mobile import (
    TuyaDeviceCredentials,
    TuyaMobileAccountLocked,
    TuyaMobileCaptchaRequired,
    TuyaMobileDeviceNotFound,
    TuyaMobileEndpointUnsupported,
    TuyaMobileInvalidAuth,
    TuyaMobileInvalidCredentials,
    TuyaMobileMFARequired,
    TuyaMobileProfileExpired,
    TuyaMobileTransportError,
)

from custom_components.tuya_ble import _async_update_listener, cloud as cloud_module
from custom_components.tuya_ble.cloud import (
    HASSTuyaBLEDeviceManager,
    TuyaCloudCacheItem,
    TuyaMobileIdentityMismatch,
)
from custom_components.tuya_ble.config_flow import (
    TuyaBLEConfigFlow,
    TuyaBLEOptionsFlow,
    _has_complete_protocol_v2_pair,
    _mobile_error_key,
)
from custom_components.tuya_ble.const import (
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_CATEGORY,
    CONF_DEVICE_NAME,
    CONF_ENDPOINT,
    CONF_IDLE_DISCONNECT_DELAY,
    CONF_KEEP_CONNECTION,
    CONF_LOCAL_KEY,
    CONF_MOBILE_APP,
    CONF_PRODUCT_ID,
    CONF_PRODUCT_MODEL,
    CONF_PRODUCT_NAME,
    CONF_SEC_KEY,
    CONF_UUID,
    DOMAIN,
)
from custom_components.tuya_ble.mobile import get_mobile_endpoint
from custom_components.tuya_ble.tuya_ble import TuyaBLEDeviceCredentials


ADDRESS = "11:22:33:44:55:66"
UUID = "fixture-uuid"
DEVICE_ID = "fixture-device"
PRODUCT_ID = "fixture-product"
CATEGORY = "fixture-category"
OLD_LOCAL_KEY = "0123456789abcdef"
OLD_SEC_KEY = "fedcba9876543210"
NEW_LOCAL_KEY = "1111111111111111"
NEW_SEC_KEY = "2222222222222222"


def _login_data() -> dict[str, str]:
    """Return non-sensitive, representative Tuya Cloud login fields."""
    return {
        CONF_ENDPOINT: "https://openapi.tuyaeu.com",
        CONF_ACCESS_ID: "fixture-access-id",
        CONF_ACCESS_SECRET: "fixture-access-secret",
        CONF_USERNAME: "owner@example.com",
        CONF_PASSWORD: "fixture-password",
        CONF_COUNTRY_CODE: "33",
    }


def _device_data(
    *,
    local_key: str = OLD_LOCAL_KEY,
    sec_key: str | None = None,
) -> dict[str, str]:
    """Return the fields returned by a Tuya Cloud device lookup."""
    data = {
        CONF_UUID: UUID,
        CONF_LOCAL_KEY: local_key,
        CONF_DEVICE_ID: DEVICE_ID,
        CONF_CATEGORY: CATEGORY,
        CONF_PRODUCT_ID: PRODUCT_ID,
        CONF_DEVICE_NAME: "Fixture device",
        CONF_PRODUCT_MODEL: "Fixture model",
        CONF_PRODUCT_NAME: "Fixture product",
    }
    if sec_key:
        data[CONF_SEC_KEY] = sec_key
    return data


def _manager_data(
    *,
    local_key: str = OLD_LOCAL_KEY,
    sec_key: str | None = None,
    mobile_app: str | None = None,
) -> dict[str, str]:
    """Return an integration options payload with Cloud and device fields."""
    data = {**_login_data(), **_device_data(local_key=local_key, sec_key=sec_key)}
    if mobile_app:
        data[CONF_MOBILE_APP] = mobile_app
    return data


def _cloud_credentials(
    *,
    local_key: str = OLD_LOCAL_KEY,
    sec_key: str | None = None,
    device_id: str = DEVICE_ID,
    uuid: str = UUID,
    product_id: str = PRODUCT_ID,
) -> TuyaBLEDeviceCredentials:
    """Return a protocol-v2 credential candidate from the Tuya OpenAPI."""
    return TuyaBLEDeviceCredentials(
        uuid=uuid,
        local_key=local_key,
        device_id=device_id,
        category=CATEGORY,
        product_id=product_id,
        device_name="Fixture device",
        product_model="Fixture model",
        product_name="Fixture product",
        functions=[],
        status_range=[],
        sec_key=sec_key,
    )


def _mobile_credentials(
    *,
    local_key: str = NEW_LOCAL_KEY,
    sec_key: str = NEW_SEC_KEY,
    device_id: str = DEVICE_ID,
    uuid: str | None = UUID,
    product_id: str | None = PRODUCT_ID,
) -> TuyaDeviceCredentials:
    """Return a validated mobile API credential response."""
    return TuyaDeviceCredentials(
        device_id=device_id,
        local_key=local_key,
        sec_key=sec_key,
        uuid=uuid,
        product_id=product_id,
    )


def _login_input() -> dict[str, str]:
    """Return arbitrary login form input; Cloud login is mocked in flow tests."""
    return {
        CONF_COUNTRY_CODE: "France",
        CONF_ACCESS_ID: "new-access-id",
        CONF_ACCESS_SECRET: "new-access-secret",
        CONF_USERNAME: "new-owner@example.com",
        CONF_PASSWORD: "new-password",
    }


def _manual_input(*, include_address: bool = False) -> dict[str, str]:
    """Return a complete upstream manual credential form submission."""
    data = {
        CONF_UUID: UUID,
        CONF_LOCAL_KEY: NEW_LOCAL_KEY,
        CONF_SEC_KEY: NEW_SEC_KEY,
        CONF_DEVICE_ID: DEVICE_ID,
        CONF_PRODUCT_ID: PRODUCT_ID,
        CONF_CATEGORY: CATEGORY,
        CONF_DEVICE_NAME: "Manual fixture",
    }
    if include_address:
        data[CONF_ADDRESS] = ADDRESS
    return data


def _schema_defaults(schema) -> dict[str, object]:
    """Extract field defaults from a voluptuous schema used by HA forms."""
    return {
        field.schema: field.default()
        for field in schema.schema
        if hasattr(field, "default")
    }


def test_released_tuya_mobile_distribution_is_installed() -> None:
    """The test environment uses the published dependency, not a local checkout."""
    assert version("tuya-mobile") == "1.2.0"


@pytest.mark.parametrize("mobile_app", ("smart_life", "tuya_smart"))
async def test_mobile_retrieval_uses_selected_profile_and_imports_pair_atomically(
    hass: HomeAssistant,
    mobile_app: str,
) -> None:
    """Both supported app selectors import a complete protocol-v2 pair."""
    manager = HASSTuyaBLEDeviceManager(
        hass,
        _manager_data(mobile_app=mobile_app),
    )
    client = Mock()
    client.login_with_password = AsyncMock()
    client.get_device_credentials = AsyncMock(return_value=_mobile_credentials())
    session = Mock()

    with (
        patch(
            "custom_components.tuya_ble.cloud.TuyaPasswordClient.for_application",
            return_value=client,
        ) as factory,
        patch(
            "custom_components.tuya_ble.cloud.async_get_clientsession",
            return_value=session,
        ),
    ):
        result = await manager.get_mobile_device_credentials(
            _cloud_credentials(), save_data=True
        )

    assert result.local_key == NEW_LOCAL_KEY
    assert result.sec_key == NEW_SEC_KEY
    assert manager.data[CONF_LOCAL_KEY] == NEW_LOCAL_KEY
    assert manager.data[CONF_SEC_KEY] == NEW_SEC_KEY
    factory.assert_called_once_with(
        mobile_app,
        session,
        username="owner@example.com",
        endpoint="https://a1.tuyaeu.com/api.json",
    )
    client.login_with_password.assert_awaited_once_with("fixture-password", "33")
    client.get_device_credentials.assert_awaited_once_with(DEVICE_ID)


async def test_mobile_failure_does_not_mutate_candidate_or_log_server_detail(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A mobile authentication error leaves both candidate keys untouched."""
    data = _manager_data(mobile_app="smart_life")
    before = data.copy()
    manager = HASSTuyaBLEDeviceManager(hass, data)
    client = Mock()
    raw_error = "server-token-and-password-must-not-be-shown"
    client.login_with_password = AsyncMock(side_effect=TuyaMobileInvalidAuth(raw_error))

    with (
        patch(
            "custom_components.tuya_ble.cloud.TuyaPasswordClient.for_application",
            return_value=client,
        ),
        patch(
            "custom_components.tuya_ble.cloud.async_get_clientsession",
            return_value=Mock(),
        ),
        pytest.raises(TuyaMobileInvalidAuth),
    ):
        await manager.get_mobile_device_credentials(
            _cloud_credentials(), save_data=True
        )

    assert manager.data == before
    assert raw_error not in caplog.text


@pytest.mark.parametrize(
    ("device_id", "uuid", "product_id"),
    (
        ("another-device", UUID, PRODUCT_ID),
        (DEVICE_ID, "another-uuid", PRODUCT_ID),
        (DEVICE_ID, UUID, "another-product"),
    ),
)
async def test_mobile_retrieval_rejects_identity_mismatch_without_replacing_keys(
    hass: HomeAssistant,
    device_id: str,
    uuid: str,
    product_id: str,
) -> None:
    """The mobile pair must belong to the same OpenAPI device."""
    data = _manager_data(mobile_app="smart_life", sec_key=OLD_SEC_KEY)
    before = data.copy()
    manager = HASSTuyaBLEDeviceManager(hass, data)
    client = Mock()
    client.login_with_password = AsyncMock()
    client.get_device_credentials = AsyncMock(
        return_value=_mobile_credentials(
            device_id=device_id,
            uuid=uuid,
            product_id=product_id,
        )
    )

    with (
        patch(
            "custom_components.tuya_ble.cloud.TuyaPasswordClient.for_application",
            return_value=client,
        ),
        patch(
            "custom_components.tuya_ble.cloud.async_get_clientsession",
            return_value=Mock(),
        ),
        pytest.raises(TuyaMobileIdentityMismatch),
    ):
        await manager.get_mobile_device_credentials(
            _cloud_credentials(), save_data=True
        )

    assert manager.data == before


@pytest.mark.parametrize(
    ("error", "key"),
    (
        (TuyaMobileInvalidAuth("server-secret"), "mobile_invalid_auth"),
        (TuyaMobileMFARequired("server-secret"), "mobile_mfa_required"),
        (TuyaMobileCaptchaRequired("server-secret"), "mobile_captcha_required"),
        (TuyaMobileAccountLocked("server-secret"), "mobile_account_locked"),
        (TuyaMobileProfileExpired("server-secret"), "mobile_profile_expired"),
        (TuyaMobileDeviceNotFound("server-secret"), "mobile_device_not_found"),
        (TuyaMobileTransportError("server-secret"), "mobile_transport_error"),
        (TuyaMobileInvalidCredentials("server-secret"), "mobile_invalid_credentials"),
        (
            TuyaMobileEndpointUnsupported("server-secret"),
            "mobile_endpoint_unsupported",
        ),
        (TuyaMobileIdentityMismatch("server-secret"), "mobile_identity_mismatch"),
    ),
)
def test_mobile_errors_expose_only_stable_translation_keys(error, key: str) -> None:
    """Config forms never interpolate an upstream exception message."""
    assert _mobile_error_key(error) == key
    assert "server-secret" not in _mobile_error_key(error)


@pytest.mark.parametrize(
    ("cloud_endpoint", "mobile_endpoint"),
    (
        ("https://openapi.tuyaeu.com", "https://a1.tuyaeu.com/api.json"),
        ("https://openapi-weaz.tuyaeu.com", "https://a1.tuyaeu.com/api.json"),
        ("https://openapi.tuyaus.com", "https://a1.tuyaus.com/api.json"),
        ("https://openapi-ueaz.tuyaus.com", "https://a1.tuyaus.com/api.json"),
        ("https://openapi.tuyacn.com", "https://a1.tuyacn.com/api.json"),
        ("https://openapi.tuyain.com", "https://a1.tuyain.com/api.json"),
        ("https://openapi-ueaz.iotbing.com", "https://a1-sg.iotbing.com/api.json"),
    ),
)
def test_mobile_endpoint_tracks_openapi_data_center(
    cloud_endpoint: str,
    mobile_endpoint: str,
) -> None:
    """The mobile call starts in the same Tuya data-center family as Cloud."""
    assert get_mobile_endpoint(cloud_endpoint) == mobile_endpoint


def test_unknown_openapi_data_center_is_not_silently_sent_to_europe() -> None:
    """An unknown Cloud endpoint cannot select a different mobile backend."""
    with pytest.raises(TuyaMobileEndpointUnsupported):
        get_mobile_endpoint("https://unknown.example")


@pytest.mark.parametrize(
    ("local_key", "sec_key", "complete"),
    (
        (OLD_LOCAL_KEY, OLD_SEC_KEY, True),
        ("short", OLD_SEC_KEY, False),
        (OLD_LOCAL_KEY, "short", False),
        ("0123456789abcdeé", OLD_SEC_KEY, False),
        (OLD_LOCAL_KEY, None, False),
    ),
)
def test_only_a_complete_ascii_pair_bypasses_mobile(
    local_key: str,
    sec_key: str | None,
    complete: bool,
) -> None:
    """A non-empty but malformed OpenAPI key is not treated as complete."""
    assert (
        _has_complete_protocol_v2_pair(
            _cloud_credentials(local_key=local_key, sec_key=sec_key)
        )
        is complete
    )


async def test_forced_cloud_refresh_drops_device_missing_from_fresh_response(
    hass: HomeAssistant,
) -> None:
    """A forced lookup cannot return a device left behind in the old cache."""
    manager = HASSTuyaBLEDeviceManager(hass, _manager_data())
    cache_item = TuyaCloudCacheItem(
        api=Mock(),
        login=_login_data(),
        credentials={ADDRESS: _device_data(sec_key=OLD_SEC_KEY)},
    )

    with (
        patch.object(manager, "_has_login", return_value=True),
        patch.object(manager, "_get_cache_key", return_value="fixture-cache"),
        patch.dict(
            cloud_module._cache,
            {"fixture-cache": cache_item},
            clear=True,
        ),
        patch.object(
            manager,
            "login",
            new=AsyncMock(return_value={"success": True}),
        ),
        patch.object(manager, "_fill_cache_item", new=AsyncMock()),
    ):
        result = await manager.get_device_credentials(
            ADDRESS,
            force_update=True,
        )

    assert result is None
    assert cache_item.credentials == {}


async def test_forced_cloud_refresh_drops_stale_sec_key(
    hass: HomeAssistant,
) -> None:
    """A fresh OpenAPI localKey cannot inherit the cached protocol-v2 secKey."""
    manager = HASSTuyaBLEDeviceManager(hass, _manager_data())
    cache_item = TuyaCloudCacheItem(
        api=Mock(),
        login=_login_data(),
        credentials={ADDRESS: _device_data(sec_key=OLD_SEC_KEY)},
    )

    async def fill_fresh_cache(item: TuyaCloudCacheItem) -> None:
        item.credentials[ADDRESS] = _device_data(local_key=NEW_LOCAL_KEY)

    with (
        patch.object(manager, "_has_login", return_value=True),
        patch.object(manager, "_get_cache_key", return_value="fixture-cache"),
        patch.dict(
            cloud_module._cache,
            {"fixture-cache": cache_item},
            clear=True,
        ),
        patch.object(
            manager,
            "login",
            new=AsyncMock(return_value={"success": True}),
        ),
        patch.object(manager, "_fill_cache_item", new=fill_fresh_cache),
    ):
        result = await manager.get_device_credentials(
            ADDRESS,
            force_update=True,
        )

    assert result is not None
    assert result.local_key == NEW_LOCAL_KEY
    assert result.sec_key is None
    assert CONF_SEC_KEY not in cache_item.credentials[ADDRESS]


async def test_options_cloud_pair_bypasses_mobile_retrieval(
    hass: HomeAssistant,
) -> None:
    """A complete OpenAPI pair wins before the mobile API is considered."""
    old_options = {
        **_manager_data(sec_key=OLD_SEC_KEY),
        CONF_KEEP_CONNECTION: False,
        CONF_IDLE_DISCONNECT_DELAY: 123,
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_ADDRESS: ADDRESS},
        options=old_options,
        title="Fixture",
    )
    flow = TuyaBLEOptionsFlow(entry)
    flow.hass = hass

    async def cloud_lookup(
        manager: HASSTuyaBLEDeviceManager,
        address: str,
        force_update: bool,
        save_data: bool,
    ) -> TuyaBLEDeviceCredentials:
        assert address == ADDRESS
        assert force_update is True
        assert save_data is True
        manager.data.update(_device_data(local_key=NEW_LOCAL_KEY, sec_key=NEW_SEC_KEY))
        return _cloud_credentials(local_key=NEW_LOCAL_KEY, sec_key=NEW_SEC_KEY)

    with (
        patch(
            "custom_components.tuya_ble.config_flow._try_login",
            new=AsyncMock(return_value=_login_data()),
        ),
        patch.object(
            HASSTuyaBLEDeviceManager,
            "get_device_credentials",
            new=cloud_lookup,
        ),
        patch.object(
            HASSTuyaBLEDeviceManager,
            "get_mobile_device_credentials",
            new=AsyncMock(),
        ) as mobile_lookup,
    ):
        result = await flow.async_step_login(_login_input())

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_LOCAL_KEY] == NEW_LOCAL_KEY
    assert result["data"][CONF_SEC_KEY] == NEW_SEC_KEY
    assert result["data"][CONF_KEEP_CONNECTION] is False
    assert result["data"][CONF_IDLE_DISCONNECT_DELAY] == 123
    mobile_lookup.assert_not_awaited()
    assert entry.options == old_options


async def test_options_mobile_refresh_is_transactional_and_reuses_saved_app(
    hass: HomeAssistant,
) -> None:
    """An explicit refresh replaces both keys only in the saved candidate."""
    old_options = {
        **_manager_data(sec_key=OLD_SEC_KEY, mobile_app="smart_life"),
        CONF_KEEP_CONNECTION: False,
        CONF_IDLE_DISCONNECT_DELAY: 123,
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_ADDRESS: ADDRESS},
        options=old_options,
        title="Fixture",
    )
    flow = TuyaBLEOptionsFlow(entry)
    flow.hass = hass

    async def cloud_lookup(
        manager: HASSTuyaBLEDeviceManager,
        address: str,
        force_update: bool,
        save_data: bool,
    ) -> TuyaBLEDeviceCredentials:
        manager.data.update(_device_data())
        return _cloud_credentials()

    async def mobile_lookup(
        manager: HASSTuyaBLEDeviceManager,
        credentials: TuyaBLEDeviceCredentials,
        save_data: bool,
    ) -> TuyaBLEDeviceCredentials:
        assert manager.data[CONF_MOBILE_APP] == "smart_life"
        assert save_data is True
        manager.data.update({CONF_LOCAL_KEY: NEW_LOCAL_KEY, CONF_SEC_KEY: NEW_SEC_KEY})
        return replace(
            credentials,
            local_key=NEW_LOCAL_KEY,
            sec_key=NEW_SEC_KEY,
        )

    with (
        patch(
            "custom_components.tuya_ble.config_flow._try_login",
            new=AsyncMock(return_value=_login_data()),
        ),
        patch.object(
            HASSTuyaBLEDeviceManager,
            "get_device_credentials",
            new=cloud_lookup,
        ),
        patch.object(
            HASSTuyaBLEDeviceManager,
            "get_mobile_device_credentials",
            new=mobile_lookup,
        ),
    ):
        result = await flow.async_step_login(_login_input())

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_LOCAL_KEY] == NEW_LOCAL_KEY
    assert result["data"][CONF_SEC_KEY] == NEW_SEC_KEY
    assert result["data"][CONF_MOBILE_APP] == "smart_life"
    assert result["data"][CONF_KEEP_CONNECTION] is False
    assert result["data"][CONF_IDLE_DISCONNECT_DELAY] == 123
    assert entry.options == old_options


async def test_options_refresh_uses_saved_identity_when_cloud_loses_device(
    hass: HomeAssistant,
) -> None:
    """A Cloud-missing device can recover with mobile keys and old identity only."""
    old_options = {
        **_manager_data(sec_key=OLD_SEC_KEY, mobile_app="smart_life"),
        CONF_KEEP_CONNECTION: False,
        CONF_IDLE_DISCONNECT_DELAY: 123,
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_ADDRESS: ADDRESS},
        options=old_options,
        title="Fixture",
    )
    flow = TuyaBLEOptionsFlow(entry)
    flow.hass = hass
    observed: dict[str, TuyaBLEDeviceCredentials] = {}

    async def mobile_lookup(
        manager: HASSTuyaBLEDeviceManager,
        credentials: TuyaBLEDeviceCredentials,
        save_data: bool,
    ) -> TuyaBLEDeviceCredentials:
        observed["credentials"] = credentials
        assert credentials.device_id == DEVICE_ID
        assert credentials.uuid == UUID
        assert credentials.product_id == PRODUCT_ID
        assert credentials.category == CATEGORY
        assert credentials.local_key != OLD_LOCAL_KEY
        assert credentials.sec_key != OLD_SEC_KEY
        assert save_data is True
        manager.data.update(
            {
                CONF_LOCAL_KEY: NEW_LOCAL_KEY,
                CONF_SEC_KEY: NEW_SEC_KEY,
            }
        )
        return replace(
            credentials,
            local_key=NEW_LOCAL_KEY,
            sec_key=NEW_SEC_KEY,
        )

    with (
        patch(
            "custom_components.tuya_ble.config_flow._try_login",
            new=AsyncMock(return_value=_login_data()),
        ),
        patch.object(
            HASSTuyaBLEDeviceManager,
            "get_device_credentials",
            new=AsyncMock(return_value=None),
        ) as cloud_lookup,
        patch.object(
            HASSTuyaBLEDeviceManager,
            "get_mobile_device_credentials",
            new=mobile_lookup,
        ),
    ):
        result = await flow.async_step_login(_login_input())

    assert observed["credentials"].local_key != OLD_LOCAL_KEY
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_LOCAL_KEY] == NEW_LOCAL_KEY
    assert result["data"][CONF_SEC_KEY] == NEW_SEC_KEY
    assert result["data"][CONF_UUID] == UUID
    assert result["data"][CONF_DEVICE_ID] == DEVICE_ID
    assert result["data"][CONF_PRODUCT_ID] == PRODUCT_ID
    assert result["data"][CONF_CATEGORY] == CATEGORY
    assert result["data"][CONF_KEEP_CONNECTION] is False
    assert result["data"][CONF_IDLE_DISCONNECT_DELAY] == 123
    cloud_lookup.assert_awaited_once_with(ADDRESS, True, True)
    assert entry.options == old_options


async def test_options_mobile_failure_shares_prefilled_manual_fallback(
    hass: HomeAssistant,
) -> None:
    """A failed refresh exposes the upstream manual form without touching entry data."""
    old_options = {
        **_manager_data(sec_key=OLD_SEC_KEY),
        CONF_KEEP_CONNECTION: False,
        CONF_IDLE_DISCONNECT_DELAY: 123,
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_ADDRESS: ADDRESS},
        options=old_options,
        title="Fixture",
    )
    flow = TuyaBLEOptionsFlow(entry)
    flow.hass = hass

    async def cloud_lookup(
        manager: HASSTuyaBLEDeviceManager,
        address: str,
        force_update: bool,
        save_data: bool,
    ) -> TuyaBLEDeviceCredentials:
        manager.data.update(_device_data())
        return _cloud_credentials()

    raw_error = "raw-server-response-token"
    with (
        patch(
            "custom_components.tuya_ble.config_flow._try_login",
            new=AsyncMock(return_value=_login_data()),
        ),
        patch.object(
            HASSTuyaBLEDeviceManager,
            "get_device_credentials",
            new=cloud_lookup,
        ),
    ):
        selector = await flow.async_step_login(_login_input())

        assert selector["type"] is FlowResultType.FORM
        assert selector["step_id"] == "mobile_app"
        assert entry.options == old_options

        assert flow._candidate_manager is not None
        with patch.object(
            flow._candidate_manager,
            "get_mobile_device_credentials",
            new=AsyncMock(side_effect=TuyaMobileInvalidAuth(raw_error)),
        ):
            fallback = await flow.async_step_mobile_app({CONF_MOBILE_APP: "tuya_smart"})

    assert fallback["type"] is FlowResultType.FORM
    assert fallback["step_id"] == "manual"
    assert fallback["errors"] == {"base": "mobile_invalid_auth"}
    assert raw_error not in repr(fallback)
    defaults = _schema_defaults(fallback["data_schema"])
    assert defaults[CONF_LOCAL_KEY] == OLD_LOCAL_KEY
    assert defaults[CONF_SEC_KEY] == ""
    assert defaults[CONF_DEVICE_ID] == DEVICE_ID
    assert entry.options == old_options

    manual = await flow.async_step_manual(_manual_input())
    assert manual["type"] is FlowResultType.CREATE_ENTRY
    assert manual["data"][CONF_LOCAL_KEY] == NEW_LOCAL_KEY
    assert manual["data"][CONF_SEC_KEY] == NEW_SEC_KEY
    assert manual["data"][CONF_MOBILE_APP] == "tuya_smart"
    assert manual["data"][CONF_KEEP_CONNECTION] is False
    assert entry.options == old_options


async def test_initial_cloud_flow_shows_selector_only_when_sec_key_is_missing(
    hass: HomeAssistant,
) -> None:
    """Initial Cloud setup invokes mobile lookup only for a missing secKey."""
    flow = TuyaBLEConfigFlow()
    flow.hass = hass
    flow._data = _manager_data()
    manager = HASSTuyaBLEDeviceManager(hass, flow._data)
    flow._manager = manager
    flow._discovered_devices[ADDRESS] = SimpleNamespace(
        address=ADDRESS,
        name="Fixture BLE",
    )

    async def mobile_lookup(
        credentials: TuyaBLEDeviceCredentials,
        save_data: bool,
    ) -> TuyaBLEDeviceCredentials:
        assert save_data is True
        manager.data.update({CONF_LOCAL_KEY: NEW_LOCAL_KEY, CONF_SEC_KEY: NEW_SEC_KEY})
        return replace(
            credentials,
            local_key=NEW_LOCAL_KEY,
            sec_key=NEW_SEC_KEY,
        )

    with (
        patch(
            "custom_components.tuya_ble.config_flow.get_device_readable_name",
            new=AsyncMock(return_value="Fixture BLE"),
        ),
        patch.object(
            manager,
            "get_device_credentials",
            new=AsyncMock(return_value=_cloud_credentials()),
        ) as cloud_lookup,
        patch.object(flow, "async_set_unique_id", new=AsyncMock()),
        patch.object(flow, "_abort_if_unique_id_configured", new=Mock()),
    ):
        selector = await flow.async_step_device({CONF_ADDRESS: ADDRESS})
        assert selector["type"] is FlowResultType.FORM
        assert selector["step_id"] == "mobile_app"

        with patch.object(
            manager,
            "get_mobile_device_credentials",
            new=AsyncMock(side_effect=mobile_lookup),
        ):
            created = await flow.async_step_mobile_app({CONF_MOBILE_APP: "smart_life"})

    cloud_lookup.assert_awaited_once_with(ADDRESS, True, True)
    assert created["type"] is FlowResultType.CREATE_ENTRY
    assert created["options"][CONF_LOCAL_KEY] == NEW_LOCAL_KEY
    assert created["options"][CONF_SEC_KEY] == NEW_SEC_KEY
    assert created["options"][CONF_MOBILE_APP] == "smart_life"


async def test_initial_login_discards_cached_device_data_before_fresh_lookup(
    hass: HomeAssistant,
) -> None:
    """A new login cannot carry a cached pair into the next device lookup."""
    flow = TuyaBLEConfigFlow()
    flow.hass = hass
    flow._data = _manager_data(sec_key=OLD_SEC_KEY)
    flow._manager = HASSTuyaBLEDeviceManager(hass, flow._data)
    next_step = {"type": FlowResultType.FORM, "step_id": "device"}

    with (
        patch(
            "custom_components.tuya_ble.config_flow._try_login",
            new=AsyncMock(return_value=_login_data()),
        ),
        patch.object(
            flow,
            "async_step_device",
            new=AsyncMock(return_value=next_step),
        ) as device_step,
    ):
        result = await flow.async_step_login(_login_input())

    assert result == next_step
    device_step.assert_awaited_once_with()
    for key in (
        CONF_UUID,
        CONF_LOCAL_KEY,
        CONF_SEC_KEY,
        CONF_DEVICE_ID,
        CONF_CATEGORY,
        CONF_PRODUCT_ID,
    ):
        assert key not in flow._data
    assert flow._data[CONF_USERNAME] == "owner@example.com"


async def test_initial_login_preserves_only_new_explicit_sec_key(
    hass: HomeAssistant,
) -> None:
    """A secKey submitted in the current login form survives stale-data cleanup."""
    flow = TuyaBLEConfigFlow()
    flow.hass = hass
    flow._data = _manager_data(sec_key=OLD_SEC_KEY)
    flow._manager = HASSTuyaBLEDeviceManager(hass, flow._data)
    fresh_login = {**_login_data(), CONF_SEC_KEY: NEW_SEC_KEY}

    with (
        patch(
            "custom_components.tuya_ble.config_flow._try_login",
            new=AsyncMock(return_value=fresh_login),
        ),
        patch.object(
            flow,
            "async_step_device",
            new=AsyncMock(
                return_value={"type": FlowResultType.FORM, "step_id": "device"}
            ),
        ),
    ):
        await flow.async_step_login({**_login_input(), CONF_SEC_KEY: NEW_SEC_KEY})

    assert flow._data[CONF_SEC_KEY] == NEW_SEC_KEY
    assert CONF_LOCAL_KEY not in flow._data


async def test_initial_invalid_nonempty_cloud_sec_key_still_uses_mobile(
    hass: HomeAssistant,
) -> None:
    """A truncated OpenAPI secKey cannot suppress automatic recovery."""
    flow = TuyaBLEConfigFlow()
    flow.hass = hass
    flow._data = _manager_data(sec_key="short")
    manager = HASSTuyaBLEDeviceManager(hass, flow._data)
    flow._manager = manager
    flow._discovered_devices[ADDRESS] = SimpleNamespace(
        address=ADDRESS,
        name="Fixture BLE",
    )

    with (
        patch(
            "custom_components.tuya_ble.config_flow.get_device_readable_name",
            new=AsyncMock(return_value="Fixture BLE"),
        ),
        patch.object(
            manager,
            "get_device_credentials",
            new=AsyncMock(return_value=_cloud_credentials(sec_key="short")),
        ),
        patch.object(flow, "async_set_unique_id", new=AsyncMock()),
        patch.object(flow, "_abort_if_unique_id_configured", new=Mock()),
    ):
        result = await flow.async_step_device({CONF_ADDRESS: ADDRESS})

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "mobile_app"


async def test_initial_cloud_flow_bypasses_mobile_for_complete_pair(
    hass: HomeAssistant,
) -> None:
    """A secKey supplied by the OpenAPI completes initial setup directly."""
    flow = TuyaBLEConfigFlow()
    flow.hass = hass
    flow._data = _manager_data(sec_key=OLD_SEC_KEY)
    manager = HASSTuyaBLEDeviceManager(hass, flow._data)
    flow._manager = manager
    flow._discovered_devices[ADDRESS] = SimpleNamespace(
        address=ADDRESS,
        name="Fixture BLE",
    )

    with (
        patch(
            "custom_components.tuya_ble.config_flow.get_device_readable_name",
            new=AsyncMock(return_value="Fixture BLE"),
        ),
        patch.object(
            manager,
            "get_device_credentials",
            new=AsyncMock(return_value=_cloud_credentials(sec_key=OLD_SEC_KEY)),
        ),
        patch.object(
            manager,
            "get_mobile_device_credentials",
            new=AsyncMock(),
        ) as mobile_lookup,
        patch.object(flow, "async_set_unique_id", new=AsyncMock()),
        patch.object(flow, "_abort_if_unique_id_configured", new=Mock()),
    ):
        result = await flow.async_step_device({CONF_ADDRESS: ADDRESS})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"][CONF_SEC_KEY] == OLD_SEC_KEY
    mobile_lookup.assert_not_awaited()


async def test_direct_manual_setup_never_calls_cloud_or_mobile(
    hass: HomeAssistant,
) -> None:
    """The explicit manual path remains independent of Cloud and mobile APIs."""
    flow = TuyaBLEConfigFlow()
    flow.hass = hass
    flow._discovery_info = SimpleNamespace(address=ADDRESS, name="Fixture BLE")

    with (
        patch(
            "custom_components.tuya_ble.cloud.TuyaPasswordClient.for_application"
        ) as mobile_factory,
        patch.object(
            HASSTuyaBLEDeviceManager,
            "get_device_credentials",
            new=AsyncMock(),
        ) as cloud_lookup,
        patch.object(flow, "async_set_unique_id", new=AsyncMock()),
        patch.object(flow, "_abort_if_unique_id_configured", new=Mock()),
    ):
        result = await flow.async_step_manual(_manual_input(include_address=True))

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"][CONF_LOCAL_KEY] == NEW_LOCAL_KEY
    assert result["options"][CONF_SEC_KEY] == NEW_SEC_KEY
    mobile_factory.assert_not_called()
    cloud_lookup.assert_not_awaited()


async def test_legacy_entry_without_mobile_app_keeps_existing_pair(
    hass: HomeAssistant,
) -> None:
    """Existing protocol-v2 entries keep working without selecting a mobile app."""
    manager = HASSTuyaBLEDeviceManager(hass, _manager_data(sec_key=OLD_SEC_KEY))

    with patch(
        "custom_components.tuya_ble.cloud.TuyaPasswordClient.for_application"
    ) as mobile_factory:
        credentials = await manager.get_device_credentials(ADDRESS)

    assert credentials is not None
    assert credentials.local_key == OLD_LOCAL_KEY
    assert credentials.sec_key == OLD_SEC_KEY
    assert CONF_MOBILE_APP not in manager.data
    mobile_factory.assert_not_called()


async def test_credentials_option_change_reloads_active_entry(
    hass: HomeAssistant,
) -> None:
    """Saving an imported pair causes the live integration to reload once."""
    old_options = {
        **_manager_data(sec_key=OLD_SEC_KEY),
        CONF_KEEP_CONNECTION: True,
        CONF_IDLE_DISCONNECT_DELAY: 30,
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_ADDRESS: ADDRESS},
        options={**old_options, CONF_SEC_KEY: NEW_SEC_KEY},
        title="Fixture",
    )
    runtime = SimpleNamespace(
        title=entry.title,
        device=SimpleNamespace(keep_connection=True, idle_disconnect_delay=30),
        manager=SimpleNamespace(data=old_options),
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime

    with patch.object(
        hass.config_entries,
        "async_reload",
        new=AsyncMock(),
    ) as reload_entry:
        await _async_update_listener(hass, entry)

    reload_entry.assert_awaited_once_with(entry.entry_id)
