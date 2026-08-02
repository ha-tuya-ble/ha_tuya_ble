"""Tuya BLE login and session key derivation."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib


@dataclass(frozen=True, slots=True)
class TuyaBLESecurityMaterial:
    """Derive the keys and security flags used by a Tuya BLE device."""

    local_key: str = field(repr=False)
    sec_key: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        try:
            local_key = self.local_key.encode("ascii")
            sec_key = self.sec_key.encode("ascii") if self.sec_key else None
        except UnicodeEncodeError as err:
            raise ValueError(
                "Tuya BLE keys must contain only ASCII characters"
            ) from err

        if len(local_key) < 6:
            raise ValueError("Tuya BLE local_key must contain at least 6 bytes")
        if sec_key and len(sec_key) != 16:
            raise ValueError("Tuya BLE sec_key must contain exactly 16 bytes")

    @property
    def protocol_v2(self) -> bool:
        """Return whether protocol-v2 key derivation is enabled."""
        return bool(self.sec_key)

    @property
    def pairing_login_key(self) -> bytes:
        """Return the six-byte login key carried by the pair request."""
        return self.local_key.encode("ascii")[:6]

    @property
    def _derivation_material(self) -> bytes:
        if self.protocol_v2:
            return f"{self.local_key}{self.sec_key}".encode("ascii")
        return self.pairing_login_key

    @property
    def login_key(self) -> bytes:
        """Return the AES key used for the device-info exchange."""
        return hashlib.md5(self._derivation_material, usedforsecurity=False).digest()

    def session_key(self, device_random: bytes) -> bytes:
        """Return the AES key used after the device-info exchange."""
        if len(device_random) != 6:
            raise ValueError("Tuya BLE device random must contain exactly 6 bytes")
        return hashlib.md5(
            self._derivation_material + device_random,
            usedforsecurity=False,
        ).digest()

    @property
    def login_flag(self) -> int:
        """Return the Tuya security level for device-info packets."""
        return 14 if self.protocol_v2 else 4

    @property
    def session_flag(self) -> int:
        """Return the Tuya security level for authenticated packets."""
        return 15 if self.protocol_v2 else 5
