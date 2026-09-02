"""Config flow for Tuya BLE integration."""

from __future__ import annotations

import logging
import pycountry
from typing import Any

import voluptuous as vol
from tuya_iot import AuthType
from tuya_mobile import (
    TuyaMobileAccountLocked,
    TuyaMobileApp,
    TuyaMobileCaptchaRequired,
    TuyaMobileDeviceNotFound,
    TuyaMobileEndpointUnsupported,
    TuyaMobileError,
    TuyaMobileInvalidAuth,
    TuyaMobileInvalidCredentials,
    TuyaMobileMFARequired,
    TuyaMobileProfileExpired,
    TuyaMobileTransportError,
)

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    OptionsFlowWithConfigEntry,
)
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.const import (
    CONF_ADDRESS,
    CONF_COUNTRY_CODE,
    CONF_DEVICE_ID,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowHandler, FlowResult
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .tuya_ble import SERVICE_UUIDS, TuyaBLEDeviceCredentials

from .const import (
    TUYA_COUNTRIES,
    TUYA_SMART_APP,
    SMARTLIFE_APP,
    TUYA_RESPONSE_SUCCESS,
    TUYA_RESPONSE_CODE,
    TUYA_RESPONSE_MSG,
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_APP_TYPE,
    CONF_AUTH_TYPE,
    CONF_CATEGORY,
    CONF_DEVICE_NAME,
    CONF_ENDPOINT,
    CONF_FUNCTIONS,
    CONF_LOCAL_KEY,
    CONF_PRODUCT_ID,
    CONF_PRODUCT_MODEL,
    CONF_PRODUCT_NAME,
    CONF_IDLE_DISCONNECT_DELAY,
    CONF_KEEP_CONNECTION,
    CONF_MOBILE_APP,
    CONF_SEC_KEY,
    CONF_STATUS_RANGE,
    CONF_UUID,
    DEFAULT_IDLE_DISCONNECT_DELAY,
    DEFAULT_KEEP_CONNECTION,
    DOMAIN,
)
from .devices import get_device_readable_name
from .cloud import HASSTuyaBLEDeviceManager, TuyaMobileIdentityMismatch

_LOGGER = logging.getLogger(__name__)

MOBILE_APP_OPTIONS = {
    TuyaMobileApp.SMART_LIFE.value: "Smart Life",
    TuyaMobileApp.TUYA_SMART.value: "Tuya Smart",
}

DEVICE_DATA_KEYS = (
    CONF_UUID,
    CONF_LOCAL_KEY,
    CONF_SEC_KEY,
    CONF_DEVICE_ID,
    CONF_CATEGORY,
    CONF_PRODUCT_ID,
    CONF_DEVICE_NAME,
    CONF_PRODUCT_MODEL,
    CONF_PRODUCT_NAME,
    CONF_FUNCTIONS,
    CONF_STATUS_RANGE,
)

MOBILE_ERROR_KEYS = {
    TuyaMobileInvalidAuth: "mobile_invalid_auth",
    TuyaMobileMFARequired: "mobile_mfa_required",
    TuyaMobileCaptchaRequired: "mobile_captcha_required",
    TuyaMobileAccountLocked: "mobile_account_locked",
    TuyaMobileProfileExpired: "mobile_profile_expired",
    TuyaMobileDeviceNotFound: "mobile_device_not_found",
    TuyaMobileIdentityMismatch: "mobile_identity_mismatch",
    TuyaMobileTransportError: "mobile_transport_error",
    TuyaMobileInvalidCredentials: "mobile_invalid_credentials",
    TuyaMobileEndpointUnsupported: "mobile_endpoint_unsupported",
}


def _mobile_error_key(error: TuyaMobileError) -> str:
    """Map a typed mobile failure to a translated config-flow error."""
    for error_type, key in MOBILE_ERROR_KEYS.items():
        if isinstance(error, error_type):
            return key
    return "mobile_credentials_required"


def _has_complete_protocol_v2_pair(
    credentials: TuyaBLEDeviceCredentials,
) -> bool:
    """Return whether both protocol-v2 keys are valid 16-byte ASCII values."""
    if not credentials.sec_key:
        return False
    try:
        local_key = credentials.local_key.encode("ascii")
        sec_key = credentials.sec_key.encode("ascii")
    except UnicodeEncodeError:
        return False
    return len(local_key) == 16 and len(sec_key) == 16


def _stored_identity_candidate(
    options: dict[str, Any],
) -> TuyaBLEDeviceCredentials | None:
    """Build a keyless mobile lookup candidate from an existing entry."""
    device_id = options.get(CONF_DEVICE_ID)
    category = options.get(CONF_CATEGORY)
    product_id = options.get(CONF_PRODUCT_ID)
    if not device_id or not category or not product_id:
        return None
    return TuyaBLEDeviceCredentials(
        uuid=options.get(CONF_UUID, ""),
        local_key="",
        device_id=device_id,
        category=category,
        product_id=product_id,
        device_name=options.get(CONF_DEVICE_NAME),
        product_model=options.get(CONF_PRODUCT_MODEL),
        product_name=options.get(CONF_PRODUCT_NAME),
        functions=options.get(CONF_FUNCTIONS),
        status_range=options.get(CONF_STATUS_RANGE),
        sec_key=None,
    )


def _show_mobile_app_form(
    flow: FlowHandler,
    default: str | None = None,
) -> FlowResult:
    """Ask which official Tuya application owns the device."""
    field = (
        vol.Required(CONF_MOBILE_APP, default=default)
        if default in MOBILE_APP_OPTIONS
        else vol.Required(CONF_MOBILE_APP)
    )
    return flow.async_show_form(
        step_id="mobile_app",
        data_schema=vol.Schema({field: vol.In(MOBILE_APP_OPTIONS)}),
    )


async def _try_login(
    manager: HASSTuyaBLEDeviceManager,
    user_input: dict[str, Any],
    errors: dict[str, str],
    placeholders: dict[str, Any],
) -> dict[str, Any] | None:
    response: dict[Any, Any] | None
    data: dict[str, Any]

    country = [
        country
        for country in TUYA_COUNTRIES
        if country.name == user_input[CONF_COUNTRY_CODE]
    ][0]

    data = {
        CONF_ENDPOINT: country.endpoint,
        CONF_AUTH_TYPE: AuthType.CUSTOM,
        CONF_ACCESS_ID: user_input[CONF_ACCESS_ID],
        CONF_ACCESS_SECRET: user_input[CONF_ACCESS_SECRET],
        CONF_USERNAME: user_input[CONF_USERNAME],
        CONF_PASSWORD: user_input[CONF_PASSWORD],
        CONF_COUNTRY_CODE: country.country_code,
    }
    if sec_key := user_input.get(CONF_SEC_KEY):
        data[CONF_SEC_KEY] = sec_key

    for app_type in (TUYA_SMART_APP, SMARTLIFE_APP, ""):
        data[CONF_APP_TYPE] = app_type
        if app_type == "":
            data[CONF_AUTH_TYPE] = AuthType.CUSTOM
        else:
            data[CONF_AUTH_TYPE] = AuthType.SMART_HOME

        response = await manager._login(data, True)

        if response.get(TUYA_RESPONSE_SUCCESS, False):
            return data

    errors["base"] = "login_error"
    if response:
        placeholders.update(
            {
                TUYA_RESPONSE_CODE: response.get(TUYA_RESPONSE_CODE),
                TUYA_RESPONSE_MSG: response.get(TUYA_RESPONSE_MSG),
            }
        )

    return None


def _show_login_form(
    flow: FlowHandler,
    user_input: dict[str, Any],
    errors: dict[str, str],
    placeholders: dict[str, Any],
) -> FlowResult:
    """Shows the Tuya IOT platform login form."""
    if user_input is not None and user_input.get(CONF_COUNTRY_CODE) is not None:
        for country in TUYA_COUNTRIES:
            if country.country_code == user_input[CONF_COUNTRY_CODE]:
                user_input[CONF_COUNTRY_CODE] = country.name
                break

    def_country_name: str | None = None
    try:
        def_country = pycountry.countries.get(alpha_2=flow.hass.config.country)
        if def_country:
            def_country_name = def_country.name
    except:
        pass

    placeholders["url"] = "https://www.home-assistant.io/integrations/tuya/"

    return flow.async_show_form(
        step_id="login",
        data_schema=vol.Schema(
            {
                vol.Required(
                    CONF_COUNTRY_CODE,
                    default=user_input.get(CONF_COUNTRY_CODE, def_country_name),
                ): vol.In(
                    # We don't pass a dict {code:name} because country codes can be duplicate.
                    [country.name for country in TUYA_COUNTRIES]
                ),
                vol.Required(
                    CONF_ACCESS_ID, default=user_input.get(CONF_ACCESS_ID, "")
                ): str,
                vol.Required(
                    CONF_ACCESS_SECRET,
                    default=user_input.get(CONF_ACCESS_SECRET, ""),
                ): str,
                vol.Optional(
                    CONF_SEC_KEY,
                    default=user_input.get(CONF_SEC_KEY, ""),
                ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
                vol.Required(
                    CONF_USERNAME, default=user_input.get(CONF_USERNAME, "")
                ): str,
                vol.Required(
                    CONF_PASSWORD, default=user_input.get(CONF_PASSWORD, "")
                ): str,
            }
        ),
        errors=errors,
        description_placeholders=placeholders,
    )


def _manual_schema(
    defaults: dict[str, Any], address_choices: dict[str, str] | None
) -> vol.Schema:
    """Schema for entering device credentials manually."""
    fields: dict[Any, Any] = {}
    if address_choices:
        fields[
            vol.Required(
                CONF_ADDRESS,
                default=defaults.get(CONF_ADDRESS, next(iter(address_choices))),
            )
        ] = vol.In(address_choices)
    fields[vol.Required(CONF_UUID, default=defaults.get(CONF_UUID, ""))] = str
    fields[vol.Required(CONF_LOCAL_KEY, default=defaults.get(CONF_LOCAL_KEY, ""))] = (
        TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
    )
    fields[vol.Optional(CONF_SEC_KEY, default=defaults.get(CONF_SEC_KEY, ""))] = (
        TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
    )
    fields[vol.Required(CONF_DEVICE_ID, default=defaults.get(CONF_DEVICE_ID, ""))] = str
    fields[vol.Required(CONF_PRODUCT_ID, default=defaults.get(CONF_PRODUCT_ID, ""))] = (
        str
    )
    fields[
        vol.Required(CONF_CATEGORY, default=defaults.get(CONF_CATEGORY, "szjqr"))
    ] = str
    fields[
        vol.Optional(CONF_DEVICE_NAME, default=defaults.get(CONF_DEVICE_NAME, ""))
    ] = str
    return vol.Schema(fields)


def _validate_manual(
    user_input: dict[str, Any], errors: dict[str, str]
) -> dict[str, Any] | None:
    """Validate manual credentials; return an options dict or None."""
    uuid = user_input[CONF_UUID].strip()
    local_key = user_input[CONF_LOCAL_KEY].strip()
    sec_key = (user_input.get(CONF_SEC_KEY) or "").strip()
    device_id = user_input[CONF_DEVICE_ID].strip()
    product_id = user_input[CONF_PRODUCT_ID].strip()
    category = user_input[CONF_CATEGORY].strip()

    if len(uuid) < 8:
        errors[CONF_UUID] = "invalid_uuid"
    if len(local_key) < 6:  # only the first 6 chars form the login key
        errors[CONF_LOCAL_KEY] = "invalid_local_key"
    if not device_id:
        errors[CONF_DEVICE_ID] = "invalid_device_id"
    if not product_id:
        errors[CONF_PRODUCT_ID] = "invalid_product_id"
    if not category:
        errors[CONF_CATEGORY] = "invalid_category"
    if errors:
        return None

    result = {
        CONF_UUID: uuid,
        CONF_LOCAL_KEY: local_key,
        CONF_DEVICE_ID: device_id,
        CONF_PRODUCT_ID: product_id,
        CONF_CATEGORY: category,
        CONF_DEVICE_NAME: (user_input.get(CONF_DEVICE_NAME) or "").strip()
        or product_id,
        CONF_PRODUCT_NAME: "",
        CONF_PRODUCT_MODEL: "",
    }
    if sec_key:
        result[CONF_SEC_KEY] = sec_key
    return result


def _settings_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Schema for the connection policy."""
    return vol.Schema(
        {
            vol.Required(
                CONF_KEEP_CONNECTION,
                default=defaults.get(CONF_KEEP_CONNECTION, DEFAULT_KEEP_CONNECTION),
            ): bool,
            vol.Required(
                CONF_IDLE_DISCONNECT_DELAY,
                default=defaults.get(
                    CONF_IDLE_DISCONNECT_DELAY, DEFAULT_IDLE_DISCONNECT_DELAY
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600)),
        }
    )


class TuyaBLEOptionsFlow(OptionsFlowWithConfigEntry):
    """Handle a Tuya BLE options flow."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__(config_entry)
        self._candidate_manager: HASSTuyaBLEDeviceManager | None = None
        self._pending_credentials: TuyaBLEDeviceCredentials | None = None
        self._mobile_error: str | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["login", "manual", "settings"],
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Connection policy."""
        if user_input is not None:
            return self.async_create_entry(
                title=self.config_entry.title,
                data={**self.config_entry.options, **user_input},
            )
        return self.async_show_form(
            step_id="settings",
            data_schema=_settings_schema(dict(self.config_entry.options)),
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit the stored credentials manually."""
        errors: dict[str, str] = {}
        if user_input is not None:
            creds = _validate_manual(user_input, errors)
            if creds:
                new_options = dict(
                    self._candidate_manager.data
                    if self._candidate_manager
                    else self.config_entry.options
                )
                new_options.pop(CONF_SEC_KEY, None)
                new_options.update(creds)
                return self.async_create_entry(
                    title=self.config_entry.title,
                    data=new_options,
                )
        elif self._mobile_error:
            errors["base"] = self._mobile_error
        defaults = user_input or dict(
            self._candidate_manager.data
            if self._candidate_manager
            else self.config_entry.options
        )
        return self.async_show_form(
            step_id="manual",
            data_schema=_manual_schema(defaults, None),
            errors=errors,
        )

    async def _async_retrieve_mobile_credentials(self) -> FlowResult:
        """Complete the pending options refresh using the mobile API."""
        assert self._candidate_manager is not None
        assert self._pending_credentials is not None
        try:
            await self._candidate_manager.get_mobile_device_credentials(
                self._pending_credentials,
                save_data=True,
            )
        except TuyaMobileError as error:
            self._mobile_error = _mobile_error_key(error)
            return await self.async_step_manual()
        return self.async_create_entry(
            title=self.config_entry.title,
            data=self._candidate_manager.data,
        )

    async def async_step_mobile_app(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select the mobile application for the pending refresh."""
        assert self._candidate_manager is not None
        if user_input is not None:
            self._candidate_manager.data[CONF_MOBILE_APP] = user_input[CONF_MOBILE_APP]
            return await self._async_retrieve_mobile_credentials()
        return _show_mobile_app_form(
            self,
            self._candidate_manager.data.get(CONF_MOBILE_APP),
        )

    async def async_step_login(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the Tuya IOT platform login step."""
        errors: dict[str, str] = {}
        placeholders: dict[str, Any] = {}
        address: str | None = self.config_entry.data.get(CONF_ADDRESS)

        if user_input is not None:
            candidate_data = dict(self.config_entry.options)
            for key in DEVICE_DATA_KEYS:
                candidate_data.pop(key, None)
            candidate_manager = HASSTuyaBLEDeviceManager(self.hass, candidate_data)
            login_data = await _try_login(
                candidate_manager,
                user_input,
                errors,
                placeholders,
            )
            if login_data:
                candidate_manager.data.update(login_data)
                credentials = await candidate_manager.get_device_credentials(
                    address, True, True
                )
                if credentials is None:
                    credentials = _stored_identity_candidate(
                        dict(self.config_entry.options)
                    )
                    if credentials is None:
                        errors["base"] = "device_not_registered"
                    else:
                        for key in DEVICE_DATA_KEYS:
                            if key not in (CONF_LOCAL_KEY, CONF_SEC_KEY) and key in (
                                self.config_entry.options
                            ):
                                candidate_manager.data[key] = self.config_entry.options[
                                    key
                                ]
                if credentials and _has_complete_protocol_v2_pair(credentials):
                    return self.async_create_entry(
                        title=self.config_entry.title,
                        data=candidate_manager.data,
                    )
                if credentials:
                    self._candidate_manager = candidate_manager
                    self._pending_credentials = credentials
                    if candidate_manager.data.get(CONF_MOBILE_APP):
                        return await self._async_retrieve_mobile_credentials()
                    return await self.async_step_mobile_app()

        if user_input is None:
            user_input = dict(self.config_entry.options)
            user_input.pop(CONF_SEC_KEY, None)

        return _show_login_form(self, user_input, errors, placeholders)


class TuyaBLEConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tuya BLE."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        super().__init__()
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_devices: dict[str, BluetoothServiceInfoBleak] = {}
        self._data: dict[str, Any] = {}
        self._manager: HASSTuyaBLEDeviceManager | None = None
        self._pending_credentials: TuyaBLEDeviceCredentials | None = None
        self._pending_address: str | None = None
        self._pending_name: str | None = None
        self._mobile_error: str | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle the bluetooth discovery step."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery_info = discovery_info
        if self._manager is None:
            self._manager = HASSTuyaBLEDeviceManager(self.hass, self._data)
        try:
            await self._manager.build_cache()
        except Exception:
            _LOGGER.exception("Error building cloud cache during bluetooth step")
        self.context["title_placeholders"] = {
            "name": await get_device_readable_name(
                discovery_info,
                self._manager,
            )
        }
        return await self.async_step_user()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Choose between cloud lookup and manual credentials."""
        if self._manager is None:
            self._manager = HASSTuyaBLEDeviceManager(self.hass, self._data)
            try:
                await self._manager.build_cache()
            except Exception:
                _LOGGER.exception("Error building cloud cache during user step")
        return self.async_show_menu(
            step_id="user",
            menu_options=["login", "manual"],
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Enter device credentials manually (no cloud access needed)."""
        errors: dict[str, str] = {}

        self._collect_discovered_devices()
        if not self._discovered_devices:
            return self.async_abort(reason="no_unconfigured_devices")
        choices = {
            info.address: f"{info.name or 'Tuya BLE'} ({info.address})"
            for info in self._discovered_devices.values()
        }

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            creds = _validate_manual(user_input, errors)
            if creds:
                await self.async_set_unique_id(address, raise_on_progress=False)
                self._abort_if_unique_id_configured()
                if self._pending_credentials:
                    options = dict(self._data)
                    options.pop(CONF_SEC_KEY, None)
                    options.update(creds)
                    options[CONF_ADDRESS] = address
                    title = self._pending_name or creds[CONF_DEVICE_NAME]
                else:
                    options = {CONF_ADDRESS: address, **creds}
                    title = creds[CONF_DEVICE_NAME]
                return self.async_create_entry(
                    title=title,
                    data={CONF_ADDRESS: address},
                    options=options,
                )
        elif self._mobile_error:
            errors["base"] = self._mobile_error

        defaults = dict(
            user_input or (self._data if self._pending_credentials is not None else {})
        )
        if CONF_ADDRESS not in defaults:
            if self._pending_address:
                defaults[CONF_ADDRESS] = self._pending_address
            elif self._discovery_info:
                defaults[CONF_ADDRESS] = self._discovery_info.address
        return self.async_show_form(
            step_id="manual",
            data_schema=_manual_schema(defaults, choices),
            errors=errors,
        )

    async def _async_retrieve_mobile_credentials(self) -> FlowResult:
        """Complete initial setup using the selected mobile application."""
        assert self._manager is not None
        assert self._pending_credentials is not None
        assert self._pending_address is not None
        try:
            await self._manager.get_mobile_device_credentials(
                self._pending_credentials,
                save_data=True,
            )
        except TuyaMobileError as error:
            self._mobile_error = _mobile_error_key(error)
            return await self.async_step_manual()
        return self.async_create_entry(
            title=self._pending_name or self._pending_address,
            data={CONF_ADDRESS: self._pending_address},
            options=self._data,
        )

    async def async_step_mobile_app(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select the mobile application for initial credential retrieval."""
        assert self._manager is not None
        if user_input is not None:
            self._data[CONF_MOBILE_APP] = user_input[CONF_MOBILE_APP]
            return await self._async_retrieve_mobile_credentials()
        return _show_mobile_app_form(self, self._data.get(CONF_MOBILE_APP))

    def _collect_discovered_devices(self) -> None:
        """Collect connectable, not yet configured Tuya BLE devices."""
        if discovery := self._discovery_info:
            self._discovered_devices[discovery.address] = discovery
            return
        current_addresses = self._async_current_ids()
        for discovery in async_discovered_service_info(self.hass):
            if (
                discovery.address in current_addresses
                or discovery.address in self._discovered_devices
                or discovery.service_data is None
                or not any(uuid in discovery.service_data for uuid in SERVICE_UUIDS)
            ):
                continue
            self._discovered_devices[discovery.address] = discovery

    async def async_step_login(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the Tuya IOT platform login step."""
        data: dict[str, Any] | None = None
        errors: dict[str, str] = {}
        placeholders: dict[str, Any] = {}

        if user_input is not None:
            data = await _try_login(
                self._manager,
                user_input,
                errors,
                placeholders,
            )
            if data:
                for key in DEVICE_DATA_KEYS:
                    self._data.pop(key, None)
                self._data.update(data)
                return await self.async_step_device()

        if user_input is None:
            user_input = {}
            if self._discovery_info:
                await self._manager.get_device_credentials(
                    self._discovery_info.address,
                    False,
                    True,
                )
            if self._data is None or len(self._data) == 0:
                self._manager.get_login_from_cache()
            if self._data is not None and len(self._data) > 0:
                user_input.update(self._data)
                user_input.pop(CONF_SEC_KEY, None)

        return _show_login_form(self, user_input, errors, placeholders)

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the user step to pick discovered device."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            discovery_info = self._discovered_devices[address]
            local_name = await get_device_readable_name(discovery_info, self._manager)
            await self.async_set_unique_id(
                discovery_info.address, raise_on_progress=False
            )
            self._abort_if_unique_id_configured()
            credentials = await self._manager.get_device_credentials(
                discovery_info.address, True, True
            )
            self._data[CONF_ADDRESS] = discovery_info.address
            if credentials is None:
                errors["base"] = "device_not_registered"
            elif _has_complete_protocol_v2_pair(credentials):
                return self.async_create_entry(
                    title=local_name,
                    data={CONF_ADDRESS: discovery_info.address},
                    options=self._data,
                )
            else:
                self._pending_credentials = credentials
                self._pending_address = discovery_info.address
                self._pending_name = local_name
                if self._data.get(CONF_MOBILE_APP):
                    return await self._async_retrieve_mobile_credentials()
                return await self.async_step_mobile_app()

        self._collect_discovered_devices()

        if not self._discovered_devices:
            return self.async_abort(reason="no_unconfigured_devices")

        def_address: str
        if user_input:
            def_address = user_input.get(CONF_ADDRESS)
        else:
            def_address = list(self._discovered_devices)[0]

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ADDRESS,
                        default=def_address,
                    ): vol.In(
                        {
                            service_info.address: await get_device_readable_name(
                                service_info,
                                self._manager,
                            )
                            for service_info in self._discovered_devices.values()
                        }
                    ),
                },
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> TuyaBLEOptionsFlow:
        """Get the options flow for this handler."""
        return TuyaBLEOptionsFlow(config_entry)
