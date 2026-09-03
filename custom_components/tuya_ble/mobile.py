"""Helpers for Tuya mobile credential retrieval."""

from __future__ import annotations

from tuya_mobile import TuyaMobileEndpointUnsupported


MOBILE_ENDPOINTS = {
    "openapi.tuyacn.com": "https://a1.tuyacn.com/api.json",
    "openapi.tuyain.com": "https://a1.tuyain.com/api.json",
    "openapi.tuyaus.com": "https://a1.tuyaus.com/api.json",
    "openapi.tuyaeu.com": "https://a1.tuyaeu.com/api.json",
    "openapi-ueaz.tuyaus.com": "https://a1.tuyaus.com/api.json",
    "openapi-weaz.tuyaeu.com": "https://a1.tuyaeu.com/api.json",
    "openapi-ueaz.iotbing.com": "https://a1-sg.iotbing.com/api.json",
}


def get_mobile_endpoint(cloud_endpoint: str) -> str:
    """Return the mobile API endpoint matching the Tuya OpenAPI data center."""
    endpoint = cloud_endpoint.lower()
    for openapi_host, mobile_endpoint in MOBILE_ENDPOINTS.items():
        if openapi_host in endpoint:
            return mobile_endpoint
    raise TuyaMobileEndpointUnsupported
