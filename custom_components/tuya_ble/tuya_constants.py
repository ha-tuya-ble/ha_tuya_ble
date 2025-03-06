"""Constants previously imported from the Tuya component."""

from __future__ import annotations

from typing import Final  # Add this import

# App type
SMARTLIFE_APP = "smartlife"
TUYA_SMART_APP = "tuyaSmart"

# Configuration keys
CONF_ACCESS_ID = "access_id"
CONF_ACCESS_SECRET = "access_secret"
CONF_APP_TYPE = "tuya_app_type"
CONF_AUTH_TYPE = "auth_type"
CONF_COUNTRY_CODE = "country_code"
CONF_ENDPOINT = "endpoint"
CONF_PASSWORD = "password"
CONF_USERNAME = "username"

# API Response keys
TUYA_RESPONSE_CODE = "code"
TUYA_RESPONSE_MSG = "msg"
TUYA_RESPONSE_RESULT = "result"
TUYA_RESPONSE_SUCCESS = "success"

# API URLs
TUYA_API_DEVICES_URL: Final = "/v1.0/users/%s/devices"
TUYA_API_FACTORY_INFO_URL: Final = "/v1.0/iot-03/devices/factory-infos?device_ids=%s"
TUYA_FACTORY_INFO_MAC: Final = "mac"
