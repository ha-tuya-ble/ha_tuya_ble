from __future__ import annotations
from dataclasses import dataclass
from typing import Any

import time
import struct
import logging
import asyncio
import hashlib
import binascii
from Crypto.Cipher import AES

import logging

from dataclasses import dataclass, field, asdict
from typing import List

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.storage import Store

from ..tuya_ble import (
    AbstaractTuyaBLEDeviceManager,
    TuyaBLEDataPoint,
    TuyaBLEDataPointType,
    TuyaBLEDevice,
    TuyaBLEDeviceCredentials,
)
from ..tuya_ble.productinfo import TuyaBLEProductInfo

from ..base import IntegerTypeData, EnumTypeData

from ..services import SERVICE_REGISTRY
        
STORAGE_VERSION = 1
STORAGE_KEY = "geeksmart_lock_users"

_LOGGER = logging.getLogger(__name__)

@dataclass
class GeeksmartFingerprint:
    """Model for an individual fingerprint."""
    id: int
    name: str = "New Fingerprint"
    valid: bool = True

@dataclass
class GeeksmartLockUser:
    user_id: int
    name: str = "Unknown User"
    fingerprints: Dict[int, GeeksmartFingerprint] = field(default_factory=dict)

    def to_dict(self):
        """Transform user data to a JSON-serializable dictionary for Home Assistant."""
        return {
            "name": self.name,
            "fingerprints": {
                fp_id: {
                    "name": fp.name, 
                    "valid": fp.valid
                } for fp_id, fp in self.fingerprints.items()
            }
        }

@dataclass
class TuyaBLEGeeksmartLockInfo(TuyaBLEProductInfo):
    """Model a Geeksmart lock"""

    # The 'Random Number' found in your logs
    random_number = None
    peripheral_id = "0001"
    central_id = "ffff"
    
    store = None
    users: Dict[int, GeeksmartLockUser] = field(default_factory=dict)
    fingerprint_sync_active = False

    battery_level = None

    # Enrollment tracking
    enrollment_stage = None
    enrollment_fingerprint_name = None
    touches_remaining = 0

    locked = None
    opened_from_inside = None

    last_alarm_reason = None
    last_action_method = None

    last_action_user = None
    last_fingerprint_id = None

    autolock_enabled = None
    autolock_seconds = None

    lock_status = "unknown"

    def load_store(self, hass: HomeAssistant):
        """Initialize the data store."""
        self.store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        hass.create_task(self.async_load())

    async def async_load(self):
        """Load stored users from disk."""
        raw_data = await self.store.async_load()
        if not raw_data:
            return

        for user_id_str, user_info in raw_data.items():
            user_id = int(user_id_str)
            
            try:
                # 1. Reconstruct the Fingerprints Dict
                fingerprints = {}
                for fp_id_str, fp_info in user_info.get("fingerprints", {}).items():
                    fp_id = int(fp_id_str)
                    fingerprints[fp_id] = GeeksmartFingerprint(
                        id=fp_id,
                        name=fp_info["name"],
                        valid=fp_info["valid"]
                    )

                # 2. Reconstruct the User
                self.users[user_id] = GeeksmartLockUser(
                    user_id=user_id,
                    name=user_info["name"],
                    fingerprints=fingerprints
                )
            except Exception as e:
                _LOGGER.error("Error loading user %s: %s", user_id_str, e)

    async def async_save(self):
        """Save the current user map to disk."""
        # Convert the complex dataclass structure into a serializable dictionary
        data_to_save = {
            user_id: user.to_dict() 
            for user_id, user in self.users.items()
        }
        await self.store.async_save(data_to_save)

    def handle_update(self, datapoint: TuyaBLEDataPoint):
        """Handles updates related to the lock."""
        if datapoint.id == 8:
            self.battery_level = int(datapoint.value)

        if datapoint.id == 47:
            self.locked = not bool(datapoint.value)
            
        if datapoint.id == 18:
            self.opened_from_inside = bool(datapoint.value)

        if datapoint.id == 70:
            # pairing info
            # Peripheral ID (2 bytes)	Central ID (2 bytes)	Random number (8 bytes)	Action (1 byte)	Central ID to pair (2 bytes)	Return value (1 byte)
            random_number_bytes = datapoint.value[4:12]
            self.random_number = struct.unpack(">Q", random_number_bytes)[0]

        if datapoint.id == 21:
            self.last_alarm_reason = datapoint.value

        if datapoint.id == 20:
            self.last_action_method = datapoint.value[0]
            self.last_action_user = datapoint.value[1]
            self.lock_status = f"Last used by user {self.last_action_user} via method {self.last_action_method}"
            
        if datapoint.id == 12:
            self.last_fingerprint_id = datapoint.value

            for user_id, user in self.users.items():
                if self.last_fingerprint_id in user.fingerprints:
                    self.lock_status = f"Last unlocked using {user.name}'s {user.fingerprints[self.last_fingerprint_id].name}"
                    break

        if datapoint.id == 33:
            self.autolock_enabled = bool(datapoint.value)

        if datapoint.id == 1:
            self.parse_enrollment(datapoint.value)

        if datapoint.id == 54:
            # Sync fingerprints response
            if datapoint.value[0] == 0x00:
                _LOGGER.info("Fingerprint sync in progress.")
                for i in range(2, len(datapoint.value), 4):
                    # Extract the 4-byte group
                    group = datapoint.value[i : i + 4]

                    # Ensure we have a full 4-byte group (ignores trailing partial bytes)
                    if len(group) < 4:
                        break

                    fingerprint_id = group[0] 
                    method_type    = group[1] 
                    user_id        = group[2]
                    is_valid       = group[3] == 0x01  # Assuming 0x01 means valid


                    # 1. Ensure the user exists
                    if user_id not in self.users:
                        self.users[user_id] = GeeksmartLockUser(user_id=user_id, name=f"User {user_id}")
                    
                    user = self.users[user_id]
                    
                    # 2. Check if the fingerprint already exists for this user
                    if fingerprint_id in user.fingerprints:
                        # Update existing
                        user.fingerprints[fingerprint_id].valid = is_valid
                    else:
                        # Create new entry
                        user.fingerprints[fingerprint_id] = GeeksmartFingerprint(id=fingerprint_id, valid=is_valid)

                    _LOGGER.info(f"Index {i}: ID={fingerprint_id}, Type={method_type}, User={user_id}, Valid={is_valid}")
            elif datapoint.value[0] == 0x01:
                _LOGGER.info("Fingerprint sync completed.")
                self.fingerprint_sync_active = False
            
        if datapoint.id == 36:
            self.autolock_seconds = int(datapoint.value)
        
    async def async_lock(self, device: TuyaBLEDevice) -> None:
        """Sends the lock command to the device."""
        try:
            # Preparation
            # Not sure, but requesting phone unlock might be needed before sending lock/unlock command
            # phone_unlock_dp = device.datapoints.get_or_create(62, TuyaBLEDataPointType.DT_BOOL, False)
            # await phone_unlock_dp.set_value(True)

            lock_payload = self.get_lock_payload()
            _LOGGER.info("Lock payload: %s", lock_payload.hex())
            datapoint = device.datapoints.get_or_create(71, TuyaBLEDataPointType.DT_RAW, 0)
            await datapoint.set_value(lock_payload)

        except Exception as err:
            _LOGGER.error("Sequence Error: %s", err)
    
    async def async_unlock(self, device: TuyaBLEDevice) -> None:
        """Sends the unlock command to the device."""
        try:
            # Preparation
            # Not sure, but requesting phone unlock might be needed before sending lock/unlock command
            # phone_unlock_dp = device.datapoints.get_or_create(62, TuyaBLEDataPointType.DT_BOOL, False)
            # await phone_unlock_dp.set_value(True)

            unlock_payload = self.get_unlock_payload()
            _LOGGER.info("Unlock payload: %s", unlock_payload.hex())
            datapoint = device.datapoints.get_or_create(71, TuyaBLEDataPointType.DT_RAW, 0)
            await datapoint.set_value(unlock_payload)

        except Exception as err:
            _LOGGER.error("Sequence Error: %s", err)


    def get_unlock_payload(self) -> bytes:
        """Generates the DP 71 payload using the stored random number."""
        # Format: CentralID(2) + PeripheralID(2) + Random(8) + Action(1) + Timestamp(4) + Method(1)
        # We reuse your verified Random Number hex
        current_time = int(time.time())
        # Convert to 4-byte Big Endian Hex
        timestamp_hex = struct.pack(">I", current_time).hex()

        return bytes.fromhex(
            f"{self.central_id}{self.peripheral_id}{self.random_number}01{timestamp_hex}000000"
        )

    def get_lock_payload(self) -> bytes:
        """Generates the DP 71 payload using the stored random number."""
        # Format: CentralID(2) + PeripheralID(2) + Random(8) + Action(1) + Timestamp(4) + Method(1)
        # We reuse your verified Random Number hex
        current_time = int(time.time())
        # Convert to 4-byte Big Endian Hex
        timestamp_hex = struct.pack(">I", current_time).hex()

        return bytes.fromhex(
            f"{self.central_id}{self.peripheral_id}{self.random_number}00{timestamp_hex}000000"
        )

    def parse_enrollment(self, data: bytes):
        """Parses DP 1 (Enrollment Progress)."""
        if len(data) < 5:
            return
        
        stage = data[1]
        if stage == 0xfc: # In Progress
            self.touches_remaining = data[5]
            self.lock_status = f"Scan successful. Touches remaining: {self.touches_remaining}"
        elif stage == 0xff: # Success
            new_id = data[4]
            user_id = data[3]
            self.lock_status = f"Fingerprint added! ID: {new_id}"

            # 1. Ensure the user exists
            if user_id not in self.users:
                self.users[user_id] = GeeksmartLockUser(user_id=user_id, name=f"User {user_id}")
            
            user = self.users[user_id]
            
            # 2. Check if the fingerprint already exists for this user
            if new_id in user.fingerprints:
                # Update existing
                user.fingerprints[new_id].valid = True
            else:
                # Create new entry
                user.fingerprints[new_id] = GeeksmartFingerprint(id=new_id, valid=True)

            user.fingerprints[new_id].name = self.enrollment_fingerprint_name

        elif stage == 0xfd: # Fail
            self.lock_status = "Enrollment failed. Please try again."        


    def extra_state_attributes(self):
        """Return the state attributes of the lock."""
        return {
            "users": {uid: user.to_dict() for uid, user in self.users.items()}
        }

    @SERVICE_REGISTRY.register_service("enroll_fingerprint", ["czybdhba"])
    async def async_enroll_fingerprint(self, call: ServiceCall, device: TuyaBLEDevice) -> None:
        user_id = call.data.get("user_id")
        finger_name = call.data.get("finger_name")
        _LOGGER.info("Starting fingerprint enrollment process for user %s on finger %s", user_id, finger_name)

        payload = bytes.fromhex("030000") + bytes([user_id]) + bytes.fromhex("ff0000000000000000000000000000000000")
        enrollment_fingerprint_name = finger_name

        # 03 - enroll fingerprint
        # 00 - start enrollment
        # 00 - ordinary user
        # user_id
        # FF - no fingerprint ID specified
        
        datapoint = device.datapoints.get_or_create(1, TuyaBLEDataPointType.DT_RAW, 0)
        if datapoint:
          await(datapoint.set_value(payload))

    @SERVICE_REGISTRY.register_service("remove_fingerprint", ["czybdhba"])
    async def async_remove_fingerprint(self, call: ServiceCall, device: TuyaBLEDevice) -> None:
        user_id = call.data.get("user_id")
        fingerprint_id = call.data.get("fingerprint_id")
        _LOGGER.info("Starting fingerprint removal process for user %s on finger %s", user_id, fingerprint_id)

        # 03 - remove fingerprint
        # 00 - start removal
        # 00 - ordinary user
        # user_id
        # fingerprint_id
        
        # datapoint = device.datapoints.get_or_create(2, TuyaBLEDataPointType.DT_RAW, 0)
        # if datapoint:
        #   await(datapoint.set_value(new_value))
        return

    @SERVICE_REGISTRY.register_service("retrieve_fingerprints", ["czybdhba"])
    async def async_retrieve_fingerprints(self, call: ServiceCall, device: TuyaBLEDevice) -> None:
        datapoint = device.datapoints.get_or_create(54, TuyaBLEDataPointType.DT_RAW)
        if datapoint:
            await datapoint.set_value(bytes([3]))  # 03 - Request fingerprint sync
            self.fingerprint_sync_active = True

            # 2. Wait for the lock to process
            # We use a timeout because Bluetooth can be flaky
            try:
                for _ in range(10):  # Wait up to 10 seconds
                    await asyncio.sleep(1)
                    if self.fingerprint_sync_active == False :
                        break
            finally:
                _LOGGER.info("Fingerprint sync process ended.")
                # 3. Schedule a permanent save
                await self.async_save()


    @SERVICE_REGISTRY.register_service("rename_user", ["czybdhba"])
    async def async_rename_user(self, call: ServiceCall, device: TuyaBLEDevice) -> None:
        user_id = call.data.get("user_id")
        new_name = call.data.get("new_name")
        _LOGGER.info("renaming user %s to %s", user_id, new_name)

        if user_id in self.users:
            self.users[user_id].name = new_name

        data_to_save = {
            str(u_id): asdict(user) for u_id, user in self.users.items()
        }
        await self.store.async_save(data_to_save)

    @SERVICE_REGISTRY.register_service("rename_fingerprint", ["czybdhba"])
    async def async_rename_fingerprint(self, call: ServiceCall, device: TuyaBLEDevice) -> None:
        user_id = call.data.get("user_id")
        fingerprint_id = call.data.get("fingerprint_id")
        new_name = call.data.get("new_name")
        _LOGGER.info("renaming fingerprint for user %s on finger %s to %s", user_id, fingerprint_id, new_name)

        if user_id in self.users:
            if fingerprint_id in self.users[user_id].fingerprints:
                self.users[user_id].fingerprints[fingerprint_id].name = new_name

        data_to_save = {
            str(u_id): asdict(user) for u_id, user in self.users.items()
        }
        await self.store.async_save(data_to_save)