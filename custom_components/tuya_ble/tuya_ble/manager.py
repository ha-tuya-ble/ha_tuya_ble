from __future__ import annotations  # noqa: D100

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TuyaBLEDeviceCredentials:
    """Tuya BLE device credentials."""

    uuid: str
    local_key: str
    device_id: str
    category: str
    product_id: str
    device_name: str | None
    product_model: str | None
    product_name: str | None

    def __str__(self):
        """Return a string representation of the Tuya BLE device manager.

        This special method returns a formatted string summarizing key properties of the object,
        including masked values for uuid, local_key, and device_id, along with the actual values
        for category, product_id, device_name, product_model, and product_name.
        """
        return (
            "uuid: xxxxxxxxxxxxxxxx, "
            "local_key: xxxxxxxxxxxxxxxx, "
            "device_id: xxxxxxxxxxxxxxxx, "
            f"category: {self.category}, "
            f"product_id: {self.product_id}, "
            f"device_name: {self.device_name}, "
            f"product_model: {self.product_model}, "
            f"product_name: {self.product_name}"
        )


class AbstaractTuyaBLEDeviceManager(ABC):
    """Abstaract manager of the Tuya BLE devices credentials."""

    @abstractmethod
    async def get_device_credentials(
        self,
        address: str,
        force_update: bool = False,
        save_data: bool = False,
    ) -> TuyaBLEDeviceCredentials | None:
        """Get credentials of the Tuya BLE device."""

    @classmethod
    def check_and_create_device_credentials(
        cls,
        uuid: str | None,
        local_key: str | None,
        device_id: str | None,
        category: str | None,
        product_id: str | None,
        device_name: str | None,
        product_name: str | None,
    ) -> TuyaBLEDeviceCredentials | None:
        """Checks and creates credentials of the Tuya BLE device."""

        if uuid and local_key and device_id and category and product_id:
            return TuyaBLEDeviceCredentials(
                uuid,
                local_key,
                device_id,
                category,
                product_id,
                device_name,
                product_name,
            )
        return None
