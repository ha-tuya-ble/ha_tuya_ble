from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Optional
from enum import IntEnum
from typing import ClassVar, Final

import time
import struct
import logging
import asyncio

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.storage import Store
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity import (
    generate_entity_id,
    EntityDescription,
)

from homeassistant.components.lock import LockEntity, LockEntityDescription
from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.components.sensor import (
        SensorEntity,
        SensorEntityDescription,
        SensorDeviceClass,
        SensorStateClass
    )
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription

from homeassistant.components.text import TextEntity, TextEntityDescription

from ..tuya_ble import (
    TuyaBLEDataPoint,
    TuyaBLEDataPointType,
    TuyaBLEDevice,
)

from ..devices import get_device_info, TuyaBLECoordinator
from ..services import SERVICE_REGISTRY

STORAGE_VERSION = 1
STORAGE_KEY = "_lock_users"



_LOGGER = logging.getLogger(__name__)

@dataclass
class GeeksmartFingerprint:
    """Model for an individual fingerprint."""
    id: str
    name: str = "New Fingerprint"
    valid: bool = True

@dataclass
class GeeksmartLockUser:
    user_id: str  # Now a string
    name: str = "Unknown User"
    fingerprints: Dict[str, GeeksmartFingerprint] = field(default_factory=dict) # Now string keys

    def to_dict(self):
        return {
            "name": self.name,
            "fingerprints": {
                fid: asdict(fp) for fid, fp in self.fingerprints.items()
            }
        }
        
class GeeksmartEntity(CoordinatorEntity):
    """Tuya BLE base entity."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: TuyaBLECoordinator,
        device: TuyaBLEDevice,
        description: EntityDescription
    ) -> None:
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._device = device
        if description.translation_key is None:
            self._attr_translation_key = description.key
        self.entity_description = description
        self._attr_has_entity_name = True
        self._attr_device_info = get_device_info(self._device)
        self._attr_unique_id = f"{self._device.device_id}-{description.key}"
        self.entity_id = generate_entity_id(
            "sensor.{}", self._attr_unique_id, hass=hass
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._coordinator.connected

    @property
    def device(self) -> TuyaBLEDevice:
        """Return the associated BLE Device."""
        return self._device

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class GeeksmartRenameText(GeeksmartEntity, TextEntity):
    def __init__(self,
                 hass: HomeAssistant,
                 coordinator: TuyaBLECoordinator,
                 device: TuyaBLEDevice) -> None:
        super().__init__(hass, coordinator, device, TextEntityDescription(
                    key="name_buffer",  # Standard practice is snake_case for keys
                    translation_key="name_buffer",
                    entity_category=EntityCategory.DIAGNOSTIC
        ))
        self._state = ""  # Initialize the state here!

    @property
    def native_value(self):
        return self._state

    async def async_set_value(self, value: str) -> None:
        self._state = value
        self.async_write_ha_state()

class GeeksmartUserEditSelect(GeeksmartEntity, SelectEntity):
    """Select entity for managing lock users."""

    def __init__(self,
                 hass: HomeAssistant,
                 coordinator: TuyaBLECoordinator,
                 device: TuyaBLEDevice) -> None:
        super().__init__(hass, coordinator, device, SelectEntityDescription(
            key="edit_user",
            translation_key="edit_user",
            entity_category=EntityCategory.DIAGNOSTIC
        ))
        # Internal state to track what the user has currently selected in the UI
        self._attr_current_option: str | None = None

    @property
    def options(self) -> list[str]:
        """Return a dynamic list of user names formatted as 'Name (ID)'."""
        users: dict[str, GeeksmartLockUser] = self._coordinator.device_manager.users
        
        if not users:
            return []
            
        # Access the dataclass attributes directly
        return [f"{user.name} ({user.user_id})" for user in users.values()]

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""
        return self._attr_current_option

    async def async_select_option(self, option: str) -> None:
        """Update the internal selection when a user picks an item in the UI."""
        if option in self.options:
            self._attr_current_option = option
            
            self._coordinator.device_manager.edit_user = option.split('(')[-1].rstrip(')')
            self._coordinator.device_manager.edit_fingerprint = None

            # This ensures the UI updates immediately to show the new selection
            self.async_write_ha_state()
            self.coordinator.async_update_listeners()

class GeeksmartFingerprintEditSelect(GeeksmartEntity, SelectEntity):
    """Select entity for managing lock users."""

    def __init__(self,
                 hass: HomeAssistant,
                 coordinator: TuyaBLECoordinator,
                 device: TuyaBLEDevice) -> None:
        super().__init__(hass, coordinator, device, SelectEntityDescription(
            key="edit_fingerprint",
            translation_key="edit_fingerprint",
            entity_category=EntityCategory.DIAGNOSTIC
        ))
        # Internal state to track what the user has currently selected in the UI
        self._attr_current_option: str | None = None

    @property
    def options(self) -> list[str]:
        """Return a dynamic list of fingerprints for the selected user."""
        users = self._coordinator.device_manager.users
        edit_user_id = self._coordinator.device_manager.edit_user
        
        if not users or not edit_user_id or edit_user_id not in users:
            return []
        
        fingerprints = users[edit_user_id].fingerprints
        
        # Format: "Name (ID)"
        return [f"{fp.name} ({fp.id})" for fp in fingerprints.values()]

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option."""
        return self._attr_current_option

    async def async_select_option(self, option: str) -> None:
        """Update the internal selection."""
        # 1. Extract the ID from the string "Name (ID)"
        # This takes everything between the last set of parentheses
        fp_id = option.split('(')[-1].rstrip(')')
        
        # 2. Save the ID to your device manager
        self._coordinator.device_manager.edit_fingerprint = fp_id
        
        # 3. Inform HA that the state has changed
        self.async_write_ha_state()
        self.coordinator.async_update_listeners()


class GeeksmartAutolockSwitch(GeeksmartEntity, SwitchEntity):
    """Switch entity for autolock."""
    def __init__(self,
                 hass: HomeAssistant,
                 coordinator: TuyaBLECoordinator,
                 device: TuyaBLEDevice) -> None:
        super().__init__(hass, coordinator, device, SwitchEntityDescription(key="automatic_lock",
                                                        translation_key="automatic_lock",
                                                        entity_category=EntityCategory.CONFIG
                                                        ))

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self._coordinator.device_manager.autolock_enabled

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self._coordinator.device_manager.set_autolock_enabled(True)

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        self._coordinator.device_manager.set_autolock_enabled(False)

class GeeksmartBeepVolumeSelect(GeeksmartEntity, SelectEntity):
    """Select entity for beep volume."""
    def __init__(self,
                 hass: HomeAssistant,
                 coordinator: TuyaBLECoordinator,
                 device: TuyaBLEDevice) -> None:
        super().__init__(hass, coordinator, device, SelectEntityDescription(key="beep_volume",
                                                        options=["Mute", "Low", "Normal", "High"],
                                                        translation_key="beep_volume",
                                                        entity_category=EntityCategory.CONFIG
                                                        ))

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""
        # 1. Get the raw value from the manager
        volume_idx = self._coordinator.device_manager.beep_volume

        # 2. Guard against None or out-of-bounds
        if volume_idx is None:
            return None

        try:
            # Use the options defined in the description
            return self.entity_description.options[volume_idx]
        except IndexError:
            return None

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Use the options from the description to find the index
        if option in self.entity_description.options:
            int_value = self.entity_description.options.index(option)

            # Send the command via the manager
            self._coordinator.device_manager.set_beep_volume(int_value)

            # Update local state so UI updates immediately
            self._coordinator.device_manager.beep_volume = int_value
            self.async_write_ha_state()

class GeeksmartAlarmSensor(GeeksmartEntity, SensorEntity):
    """Sensor entity for alarm notice."""
    def __init__(self,
                 hass: HomeAssistant,
                 coordinator: TuyaBLECoordinator,
                 device: TuyaBLEDevice) -> None:
        super().__init__(hass, coordinator, device, SensorEntityDescription(key="alarm_lock",
                                                         icon="mdi:alarm-light-outline",
                                                         device_class=SensorDeviceClass.ENUM,
                                                         options=[
                                                            "wrong_finger",
                                                            "low_battery",
                                                            "power_off"
                                                            ]
                                                        ))

    @property
    def native_value(self):
        """Return the mapped string value from the options list."""
        # 1. Get the raw value (e.g., 0, 1, or 2)
        raw_val = self._coordinator.device_manager.get_sensor_value(
            self.entity_description.key, 
            self.coordinator.data
        )

        # 2. Guard against None
        if raw_val is None:
            return None

        # 3. Map the integer index to the string in your options
        try:
            # If raw_val is 1, this returns "low_battery"
            return self.entity_description.options[int(raw_val)]
        except (IndexError, ValueError, TypeError):
            # Fallback if the lock sends an ID we don't recognize
            return None
        
class GeeksmartLastUnlockedSensor(GeeksmartEntity, SensorEntity):
    """Sensor entity for last unlock method."""
    def __init__(self,
                hass: HomeAssistant,
                coordinator: TuyaBLECoordinator,
                device: TuyaBLEDevice) -> None:
        super().__init__(hass, coordinator, device, SensorEntityDescription(key="unlock_fingerprint",
                                                         icon="mdi:fingerprint"))

    @property
    def native_value(self):
        """Return the value from the manager via the coordinator data."""
        # We ask the manager to parse the raw data specifically for this sensor
        return self._coordinator.device_manager.get_sensor_value(
            self.entity_description.key,
            self.coordinator.data
            )


class GeeksmartBatterySensor(GeeksmartEntity, SensorEntity):
    """Sensor entity for battery level."""
    def __init__(self,
                hass: HomeAssistant,
                coordinator: TuyaBLECoordinator,
                device: TuyaBLEDevice) -> None:
        super().__init__(hass, coordinator, device, SensorEntityDescription(
                                key="battery",
                                device_class=SensorDeviceClass.BATTERY,
                                native_unit_of_measurement=PERCENTAGE,
                                entity_category=EntityCategory.DIAGNOSTIC,
                                state_class=SensorStateClass.MEASUREMENT,
                                icon="mdi:battery"))

    @property
    def native_value(self):
        """Return the value from the manager via the coordinator data."""
        # We ask the manager to parse the raw data specifically for this sensor
        return self._coordinator.device_manager.get_sensor_value(self.entity_description.key, self.coordinator.data)

class GeeksmartAutoLockTimeNumber(GeeksmartEntity, NumberEntity):
    """Number entity for autolock time."""
    def __init__(self,
                hass: HomeAssistant,
                coordinator: TuyaBLECoordinator,
                device: TuyaBLEDevice) -> None:
        super().__init__(hass, coordinator, device, NumberEntityDescription(
                            key="auto_lock_time",
                            icon="mdi:timer",
                            native_max_value=1800,
                            native_min_value=5,
                            native_step=1,
                            native_unit_of_measurement=UnitOfTime.SECONDS,
                            entity_category=EntityCategory.CONFIG,
                            mode=NumberMode.BOX
                            ))

    @property
    def native_value(self):
        """Return the value from the manager via the coordinator data."""
        # We ask the manager to parse the raw data specifically for this sensor
        return self._coordinator.device_manager.get_sensor_value(self.entity_description.key, self.coordinator.data)

    def set_native_value(self, value: float) -> None:
        """Update the current value."""
        self._coordinator.device_manager.set_autolock_time(int(value))

    # async def async_set_native_value(self, value: float) -> None:
    #     """Update the current value."""

class GeeksmartLock(GeeksmartEntity, LockEntity):
    """Lock entity for the device."""
    def __init__(self,
                hass: HomeAssistant,
                coordinator: TuyaBLECoordinator,
                device: TuyaBLEDevice) -> None:
        super().__init__(hass, coordinator, device, LockEntityDescription(key="lock_motor_state"))

    @property
    def is_locked(self) -> bool:
        """Return true if lock is locked."""
        state = self._coordinator.device_manager.locked

        if state is None:
            # If the device is offline, show previous state or None
            return getattr(self, "_attr_is_locked", None)

        return bool(state)

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the lock."""
        return self._coordinator.device_manager.extra_state_attributes()

    async def async_lock(self, **kwargs) -> None:
        """Lock all or specified locks. A code to lock the lock with may optionally be specified."""
        await self._coordinator.device_manager.async_lock()

    async def async_unlock(self, **kwargs) -> None:
        """Unlock all or specified locks. A code to unlock the lock with may optionally be specified."""
        await self._coordinator.device_manager.async_unlock()

class TuyaBLELockDP(IntEnum):
    """
    Data Point IDs for Tuya BLE Smart Locks.
    Reference: Tuya Developer Docs (K9ow3vcpn71ua / K9fwaai7m9wt3)
    """
    
    # --- UNLOCKING METHODS (Usually RAW) ---
    # Used for managing (create/delete/modify) and reporting specific unlocks
    UNLOCK_METHOD_CREATE = 1      # Raw: Cloud-to-device add user/method
    UNLOCK_METHOD_DELETE = 2      # Raw: Delete user/method
    UNLOCK_METHOD_MODIFY = 3      # Raw: Modify existing user/method
    
    # --- REAL-TIME STATUS & CONTROL ---
    BATTERY_PERCENT = 8           # Integer: 0-100%
    LOCKED_STATUS = 47            # Boolean: Lock state (locked/unlocked)
    LOCK_CONTROL = 71             # Raw: Lock/unlock command
    
    # --- RECORDS & LOGS ---
    RECORDS_FINGERPRINT = 12      # Raw: Last fingerprint unlock record
    RECORDS_LOCKING = 20          # Raw: Last lock/unlock action record
    RECORDS_ALARM = 21            # Enum: Reporting alerts (pry, wrong code, etc.)
    
    # --- SYNC USERS ---
    SYNC_USERS = 54               # Raw: Sync user/method data from lock to cloud

    # --- DEVICE CONFIGURATION ---
    REMOTE_UNLOCK_SWITCH = 60     # Boolean: Enable/Disable remote unlock ability
    REMOTE_UNLOCK_COMMAND = 61    # Boolean: Request/trigger remote unlock

    # --- LOCK SETTINGS ---
    BEEP_VOLUME = 31            # Integer: Beep volume level (0-3)
    AUTOLOCK_ENABLE = 33        # Boolean: Enable/Disable autolock
    AUTOLOCK_TIMER = 36         # Integer: Autolock time in seconds (5-1800s)    

@dataclass
class TuyaBLEGeeksmartK11():
    """Model a Geeksmart lock"""

    # Protocol Identifiers
    # The 'Random Number' found in your logs
    random_number: Optional[str] = None
    peripheral_id: str = "0001"
    central_id: str = "ffff"

    # Data Storage
    store: Any = None
    users: Dict[int, GeeksmartLockUser] = field(default_factory=dict)
    fingerprint_sync_active: bool = False

    # Device State
    beep_volume: Optional[int] = None
    battery_level: Optional[int] = None

    # Enrollment tracking
    enrollment_stage: Optional[str] = None
    enrollment_fingerprint_name: Optional[str] = None
    touches_remaining: int = 0

    # Lock Status
    locked: Optional[bool] = None
    opened_from_inside: Optional[bool] = None
    lock_status: str = "unknown"

    # History/Logs
    last_alarm_reason: Optional[str] = None
    last_action_method: Optional[str] = None
    last_action_user: Optional[int] = None
    last_fingerprint_id: Optional[int] = None

    # Settings
    autolock_enabled: Optional[bool] = None
    autolock_seconds: Optional[int] = None

    edit_user: Optional[str] = None
    edit_fingerprint: Optional[str] = None

    CATEGORY_ID: ClassVar[str] = "jtmspro"
    PRODUCT_ID: ClassVar[str] = "czybdhba"

    _device: TuyaBLEDevice = None
    _hass: HomeAssistant = None
    _coordinator: TuyaBLECoordinator = None

    def __post_init__(self):
        """Initialize the Geeksmart K11 lock."""
        # The Geeksmart K11 requires a 'Random Number' to be set before it can be used
        # Get the random number by unlocking the lock with the mobile app. Then get it from the Tuya IoT Cloud logs.
        # TODO: Update the readme with these instructions
        options = self._device.get_options_data()
        if "secret_code" in options:
            self.random_number = options["secret_code"].encode("ascii").hex()
        self.load_store()

        self._device.datapoints.get_or_create(TuyaBLELockDP.BATTERY_PERCENT, TuyaBLEDataPointType.DT_VALUE, 0)
        self._device.datapoints.get_or_create(TuyaBLELockDP.LOCKED_STATUS, TuyaBLEDataPointType.DT_BOOL, 0)
        self._device.datapoints.get_or_create(TuyaBLELockDP.RECORDS_ALARM, TuyaBLEDataPointType.DT_VALUE, 0)
        self._device.datapoints.get_or_create(TuyaBLELockDP.RECORDS_LOCKING, TuyaBLEDataPointType.DT_RAW, 0)
        self._device.datapoints.get_or_create(TuyaBLELockDP.RECORDS_FINGERPRINT, TuyaBLEDataPointType.DT_VALUE, 0)
        self._device.datapoints.get_or_create(TuyaBLELockDP.BEEP_VOLUME, TuyaBLEDataPointType.DT_VALUE, 0)
        self._device.datapoints.get_or_create(TuyaBLELockDP.AUTOLOCK_ENABLE, TuyaBLEDataPointType.DT_BOOL, 0)
        self._device.datapoints.get_or_create(TuyaBLELockDP.AUTOLOCK_TIMER, TuyaBLEDataPointType.DT_VALUE, 0)

        self._device.register_callback(self.handle_update)



    def get_entities(self,
                     hass: HomeAssistant,
                     coordinator: TuyaBLECoordinator,
                     device: TuyaBLEDevice):
        """Return a list of entity objects for this device."""
        entities = []

        entities.append(GeeksmartAutolockSwitch(hass, coordinator, device))
        entities.append(GeeksmartBeepVolumeSelect(hass, coordinator, device))
        entities.append(GeeksmartAlarmSensor(hass, coordinator, device))
        entities.append(GeeksmartLastUnlockedSensor(hass, coordinator, device))
        entities.append(GeeksmartBatterySensor(hass, coordinator, device))
        entities.append(GeeksmartAutoLockTimeNumber(hass, coordinator, device))
        entities.append(GeeksmartLock(hass, coordinator, device))
        entities.append(GeeksmartRenameText(hass, coordinator, device))
        entities.append(GeeksmartUserEditSelect(hass, coordinator, device))
        entities.append(GeeksmartFingerprintEditSelect(hass, coordinator, device))


        return entities

    def load_store(self):
        """Initialize the data store."""
        self.store = Store(self._hass, STORAGE_VERSION, f"{self._device.device_id}STORAGE_KEY")
        self._hass.create_task(self.async_load())

    async def async_load(self):
        """Load stored users from disk with type-safety enforcement."""
        raw_data = await self.store.async_load()
        if not raw_data:
            return

        for user_id, user_info in raw_data.items():
            try:
                # Force user_id to string to match our new architecture
                u_id_str = str(user_id)
                
                # 1. Reconstruct the Fingerprints Dict
                fingerprints = {}
                for fp_id, fp_info in user_info.get("fingerprints", {}).items():
                    # Force fp_id to string
                    f_id_str = str(fp_id)
                    fingerprints[f_id_str] = GeeksmartFingerprint(
                        id=f_id_str,
                        name=fp_info.get("name", "New Fingerprint"),
                        valid=fp_info.get("valid", True)
                    )

                # 2. Reconstruct the User
                self.users[u_id_str] = GeeksmartLockUser(
                    user_id=u_id_str,
                    name=user_info.get("name", "Unknown User"),
                    fingerprints=fingerprints
                )
            except Exception as e:
                _LOGGER.error("Error loading user %s: %s", user_id, e)


    async def async_save(self):
        """Save the current user map to disk."""
        # Convert the complex dataclass structure into a serializable dictionary
        data_to_save = {
            user_id: user.to_dict()
            for user_id, user in self.users.items()
        }
        await self.store.async_save(data_to_save)

    @callback
    def handle_update(self, updates: list[TuyaBLEDataPoint]) -> None:
        """Handles updates related to the lock."""
        for datapoint in updates:
            if datapoint.id == TuyaBLELockDP.BATTERY_PERCENT:
                self.battery_level = int(datapoint.value)

            if datapoint.id == TuyaBLELockDP.LOCKED_STATUS:
                self.locked = not bool(datapoint.value)

            # if datapoint.id == 18:
            #     self.opened_from_inside = bool(datapoint.value)

            # if datapoint.id == 70:
            #     # pairing info
            #     # Peripheral ID (2 bytes)	Central ID (2 bytes)	Random number (8 bytes)	Action (1 byte)	Central ID to pair (2 bytes)	Return value (1 byte)
            #     random_number_bytes = datapoint.value[4:12]
            #     self.random_number = struct.unpack(">Q", random_number_bytes)[0]

            if datapoint.id == TuyaBLELockDP.RECORDS_FINGERPRINT:
                self.last_fingerprint_id = datapoint.value

                for user_id, user in self.users.items():
                    if str(self.last_fingerprint_id) in user.fingerprints:
                        self.lock_status = f"Last unlocked using {user.name}'s {user.fingerprints[str(self.last_fingerprint_id)].name}"
                        break

            if datapoint.id == TuyaBLELockDP.RECORDS_LOCKING:
                self.last_action_method = datapoint.value[0]
                self.last_action_user = datapoint.value[1]
                if self.users[str(self.last_action_user)] is not None:
                    self.lock_status = f"Last used by user {self.users[str(self.last_action_user)].name} via method {self.last_action_method}"
                else:
                    self.lock_status = f"Last used by user {self.last_action_user} via method {self.last_action_method}"

            if datapoint.id == TuyaBLELockDP.RECORDS_ALARM:
                self.last_alarm_reason = datapoint.value

            if datapoint.id == TuyaBLELockDP.BEEP_VOLUME:
                self.beep_volume = int(datapoint.value)

            if datapoint.id == TuyaBLELockDP.AUTOLOCK_ENABLE:
                self.autolock_enabled = bool(datapoint.value)

            if datapoint.id == TuyaBLELockDP.AUTOLOCK_TIMER:
                self.autolock_seconds = int(datapoint.value)

            if datapoint.id == TuyaBLELockDP.UNLOCK_METHOD_CREATE:
                self.parse_enrollment(datapoint.value)

            if datapoint.id == TuyaBLELockDP.UNLOCK_METHOD_DELETE:
                self.parse_removal(datapoint.value)
                self._hass.create_task(self.async_save())

            if datapoint.id == TuyaBLELockDP.SYNC_USERS:
                # Sync fingerprints response
                if datapoint.value[0] == 0x00:
                    _LOGGER.info("Fingerprint sync in progress.")
                    for i in range(2, len(datapoint.value), 4):
                        # Extract the 4-byte group
                        group = datapoint.value[i : i + 4]

                        # Ensure we have a full 4-byte group (ignores trailing partial bytes)
                        if len(group) < 4:
                            break

                        fingerprint_id_raw = group[0]
                        method_type        = group[1]
                        user_id_raw        = group[2]
                        is_valid           = group[3] == 0x01  # Assuming 0x01 means valid

                        user_id = str(user_id_raw)
                        fingerprint_id = str(fingerprint_id_raw)

                        # 1. Ensure the user exists
                        if user_id not in self.users:
                            # This will now correctly find "253" instead of creating 253
                            self.users[user_id] = GeeksmartLockUser(user_id=user_id, name=f"User {user_id}")

                        user = self.users[user_id]

                        # 2. Check if the fingerprint already exists for this user
                        if fingerprint_id in user.fingerprints:
                            # Update existing (This preserves the NAME because you aren't touching the .name property!)
                            user.fingerprints[fingerprint_id].valid = is_valid
                        else:
                            # Create new entry if it's a truly new finger
                            user.fingerprints[fingerprint_id] = GeeksmartFingerprint(id=fingerprint_id, valid=is_valid)
    
                        _LOGGER.info(f"Index {i}: ID={fingerprint_id}, Type={method_type}, User={user_id}, Valid={is_valid}")
                elif datapoint.value[0] == 0x01:
                    _LOGGER.info("Fingerprint sync completed.")
                    self.fingerprint_sync_active = False
                    self._hass.create_task(self.async_save())
        self._coordinator.async_update_listeners()


    def set_autolock_enabled(self, enabled: bool) -> None:
        """Sets the autolock enabled state."""
        try:
            datapoint = self._device.datapoints.get_or_create(TuyaBLELockDP.AUTOLOCK_ENABLE, TuyaBLEDataPointType.DT_BOOL, 0)
            self._hass.create_task(datapoint.set_value(enabled))
        except Exception as err:
            _LOGGER.error("set_autolock_enabled Error: %s", err)

    def set_autolock_time(self, seconds: int) -> None:
        """Sets the autolock time in seconds."""
        self.autolock_seconds = seconds
        try:
            datapoint = self._device.datapoints.get_or_create(TuyaBLELockDP.AUTOLOCK_TIMER, TuyaBLEDataPointType.DT_VALUE, 0)
            self._hass.create_task(datapoint.set_value(seconds))
        except Exception as err:
            _LOGGER.error("set_autolock_time Error: %s", err)

    def set_beep_volume(self, volume_level: int) -> None:
        """Sets the beep volume level."""
        try:
            datapoint = self._device.datapoints.get_or_create(TuyaBLELockDP.BEEP_VOLUME, TuyaBLEDataPointType.DT_VALUE, 0)
            self._hass.create_task(datapoint.set_value(volume_level))
        except Exception as err:
            _LOGGER.error("set_beep_volume Error: %s", err)

    def get_sensor_value (self, sensor_key: str, data: Any) -> Any:
        """Returns the value for a specific sensor."""
        if sensor_key == "alarm_lock":
            return self.last_alarm_reason
        elif sensor_key == "unlock_fingerprint":
            for user_id, user in self.users.items():
                if self.last_fingerprint_id in user.fingerprints:
                    return f"{user.name}'s {user.fingerprints[self.last_fingerprint_id].name}"
            return "None"
        elif sensor_key == "battery":
            return self.battery_level
        elif sensor_key == "auto_lock_time":
            return self.autolock_seconds
        return None

    async def async_lock(self) -> None:
        """Sends the lock command to the device."""
        try:
            lock_payload = self.get_lock_payload()
            _LOGGER.info("Lock payload: %s", lock_payload.hex())
            datapoint = self._device.datapoints.get_or_create(TuyaBLELockDP.LOCK_CONTROL, TuyaBLEDataPointType.DT_RAW, 0)
            await datapoint.set_value(lock_payload)

        except Exception as err:
            _LOGGER.error("Sequence Error: %s", err)

    async def async_unlock(self) -> None:
        """Sends the unlock command to the device."""
        try:
            unlock_payload = self.get_unlock_payload()
            _LOGGER.info("Unlock payload: %s", unlock_payload.hex())
            datapoint = self._device.datapoints.get_or_create(TuyaBLELockDP.LOCK_CONTROL, TuyaBLEDataPointType.DT_RAW, 0)
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
            self.enrollment_stage = "In progress"
            self.touches_remaining = data[5]
            self.lock_status = f"Scan successful. Touches remaining: {self.touches_remaining}"
        elif stage == 0xff: # Success
            new_id = str(data[4])
            user_id = str(data[3])
            self.lock_status = f"Fingerprint added! ID: {new_id}"
            self.enrollment_stage = "Success"
            self.touches_remaining = 0

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

            self._hass.create_task(self.async_save())

        elif stage == 0xfd: # Fail
            self.lock_status = "Enrollment failed. Please try again."
            self.enrollment_stage = "Failed"
            self.touches_remaining = 0

    def parse_removal(self, data: bytes):
        """Parses DP 2 (Removal Status)."""
        if len(data) < 7:
            return

        user_id = str(data[3])
        fingerprint_id = str(data[4])
        method = data[5]
        status = data[6]

        if method == 0x00: # user
            if status == 0x00: # Failed
                self.lock_status = f"Failed to remove user {user_id}"
            elif status == 0xFF: # Success
                self.lock_status = f"User {user_id} removed successfully."
                if user_id in self.users:
                    self.users.pop(user_id)
                    self._hass.create_task(self.async_save())
        elif method == 0x01: # fingerprint
            if status == 0x00: # Failed
                self.lock_status = f"Failed to remove fingerprint {fingerprint_id} for user {user_id}"
            elif status == 0x01: # unlock method doesn't exist
                self.lock_status = f"Unlocking method does not exist."
            elif status == 0xFF: # Success
                self.lock_status = f"Fingerprint {fingerprint_id} for user {user_id} removed successfully."
                if user_id in self.users:
                    user = self.users.get(user_id)
                    if user and fingerprint_id in user.fingerprints:
                        user.fingerprints.pop(fingerprint_id)
                        self._hass.create_task(self.async_save())
        

    def extra_state_attributes(self):
        """Return the state attributes of the lock."""
        return {
            "users": {uid: user.to_dict() for uid, user in self.users.items()},
            "lock_status": self.lock_status,
            "enrollment_stage": self.enrollment_stage,
            "enrollment_fingerprint_name": self.enrollment_fingerprint_name,
            "touches_remaining": self.touches_remaining,
        }

    @SERVICE_REGISTRY.register_service("add_user", [PRODUCT_ID])
    async def async_add_user(self, call: ServiceCall, device: TuyaBLEDevice) -> None:
        """Service to enroll a fingerprint."""
        user_id = call.data.get("user_id")
        name = call.data.get("name")
        
        if not name:
            # Fetch from your newly created text entity
            buffer_state = self._hass.states.get(f"text.{device.device_id}_name_buffer")
            name = buffer_state.state if buffer_state else None

        # 2. Validation: Ensure we have a name
        if not name or name.strip() == "":
            _LOGGER.error("Failed to add user: No name provided in call or buffer")
            return

        # 3. Validation: Bounds Checking for User ID
        # If no user_id is provided, find the next available ID
        existing_users = self.users

        if user_id is None:
            # Find the first gap in IDs starting from 1 up to 255
            for i in range(1, 256):
                if str(i) not in existing_users:
                    user_id = i
                    break
        
        if user_id is None or not (1 <= int(user_id) <= 255):
            _LOGGER.error("Failed to add user: User ID %s is out of bounds (1-255)", user_id)
            return

        # 4. Collision Checking
        if str(user_id) in self.users:
            _LOGGER.warning("User ID %s already exists. Overwriting name to: %s", user_id, name)

        # 5. Logic: Inform the device / update state
        _LOGGER.info("Successfully validated: Adding User %s (%s)", user_id, name)

        self.users[user_id] = GeeksmartLockUser(user_id=str(user_id), name=f"User {user_id}")

        # 6. Clean up: Clear the buffer after successful validation
        await self._hass.services.async_call(
            "text", 
            "set_value", 
            {"entity_id": f"text.{device.device_id}_name_buffer", "value": ""},
            blocking=True
        )

        self.lock_status = f"Adding User {user_id} = {name}"
        await self.async_save()
        self._coordinator.async_update_listeners()

    @SERVICE_REGISTRY.register_service("enroll_fingerprint", [PRODUCT_ID])
    async def async_enroll_fingerprint(self, call: ServiceCall, device: TuyaBLEDevice) -> None:
        """Service to start the physical fingerprint enrollment process."""
        # 1. Retrieve and Cast IDs
        user_id = call.data.get("user_id")
        if user_id is None:
            if self.edit_user is None:
                _LOGGER.error("Enrollment failed: No user provided in call or buffer")
                return
            user_id = self.edit_user


        finger_name = call.data.get("finger_name")

        # 2. Fallback to name buffer if finger_name not provided
        if not finger_name:
            buffer_id = f"text.{device.device_id}_name_buffer"
            state = self._hass.states.get(buffer_id)
            finger_name = state.state if state else None

        # 3. Validation: Check for Name
        if not finger_name or finger_name.strip() == "":
            finger_name = "Finger"

        # 4. Validation: Bounds Check for User ID
        try:
            u_id_int = int(user_id)
            if not (0 <= u_id_int <= 255):
                raise ValueError
        except (TypeError, ValueError):
            _LOGGER.error("Enrollment failed: Invalid User ID %s (must be 0-255)", user_id)
            return

        # 5. Check if User exists in local state before starting
        if str(u_id_int) not in self.users:
            _LOGGER.error("Enrollment failed: User ID %s not found in local state", u_id_int)
            return

        _LOGGER.info("Starting fingerprint enrollment for user %s (%s) as '%s'", 
                     u_id_int, self.users[str(u_id_int)].name, finger_name)

        # 6. Prepare Payload
        # 03: Enroll, 00: Start, 00: Ordinary, [ID], FF: Auto-assign FP ID
        header = bytes.fromhex("030000")
        padding = bytes.fromhex("ff0000000000000000000000000000000000")
        payload = header + bytes([u_id_int]) + padding

        # 7. Store the name temporarily
        # This allows the 'success' callback from the lock to know what to name the new FP ID
        self.enrollment_fingerprint_name = finger_name.strip()

        # 8. Send Command
        datapoint = device.datapoints.get_or_create(
            TuyaBLELockDP.UNLOCK_METHOD_CREATE, 
            TuyaBLEDataPointType.DT_RAW, 
            0
        )
        
        if datapoint:
            try:
                await datapoint.set_value(payload)
                _LOGGER.debug("Enrollment payload sent successfully: %s", payload.hex())
            except Exception as err:
                _LOGGER.error("Failed to send enrollment command to lock: %s", err)
                return
        else:
            _LOGGER.error("Enrollment failed: Could not find UNLOCK_METHOD_CREATE datapoint")
            return

        # 9. Cleanup Buffer
        await self._hass.services.async_call(
            "text", 
            "set_value", 
            {"entity_id": f"text.{device.device_id}_name_buffer", "value": ""},
            blocking=False
        )

        self._coordinator.async_update_listeners()

    @SERVICE_REGISTRY.register_service("remove_fingerprint", [PRODUCT_ID])
    async def async_remove_fingerprint(self, call: ServiceCall, device: TuyaBLEDevice) -> None:
        """Service to remove a specific fingerprint or an entire user from the hardware."""
        # 1. Retrieve and Validate Inputs
        raw_user_id = call.data.get("user_id")
        if raw_user_id is None:
            if self.edit_user is None:
                _LOGGER.error("Enrollment failed: No user provided in call or buffer")
                return
            raw_user_id = self.edit_user

        raw_fp_id = call.data.get("fingerprint_id")
        if raw_fp_id is None:
            if self.edit_fingerprint is None:
                _LOGGER.error("Removal failed: No fingerprint id provided in call or buffer")
                return
            raw_fp_id = self.edit_fingerprint

        try:
            user_id = int(raw_user_id)
            fp_id = int(raw_fp_id)
        except (TypeError, ValueError):
            _LOGGER.error("Removal failed: Invalid IDs provided (User: %s, FP: %s)", raw_user_id, raw_fp_id)
            return

        # 2. logical Bounds Check
        if not (0 <= user_id <= 255):
            _LOGGER.error("Removal failed: User ID %s out of range (0-255)", user_id)
            return

        # 3. Check Local State (Optional but recommended)
        u_id_str = str(user_id)
        if u_id_str not in self.users:
            _LOGGER.warning("Sending removal command for User %s, but user not found in local state.", user_id)

        # 4. Construct Payload
        _LOGGER.info("Sending hardware command: Remove fingerprint %s for user %s", fp_id, user_id)
        # 030000 + UserID + FingerprintID + 01 (Delete single)
        # We use a try block here in case fp_id is > 255 (bytes() limit)
        try:
            payload = bytes.fromhex("030000") + bytes([user_id]) + bytes([fp_id]) + bytes.fromhex("01")
        except ValueError:
            _LOGGER.error("Removal failed: Fingerprint ID %s is too large for byte conversion", fp_id)
            return

        # 5. Send to Device
        # Using UNLOCK_METHOD_DELETE (often DP 52 or similar)
        datapoint = device.datapoints.get_or_create(
            TuyaBLELockDP.UNLOCK_METHOD_DELETE, 
            TuyaBLEDataPointType.DT_RAW, 
            0
        )

        if datapoint:
            try:
                await datapoint.set_value(payload)
                _LOGGER.debug("Removal payload sent: %s", payload.hex())
            except Exception as err:
                _LOGGER.error("Failed to send removal command to lock: %s", err)
                return
        else:
            _LOGGER.error("Removal failed: Could not find UNLOCK_METHOD_DELETE datapoint")
            return

        # 6. Local Cleanup (Optional)
        # You might want to remove it from your local self.users here 
        # OR wait for the lock to confirm via a separate DP response.
        
        self._coordinator.async_update_listeners()

    @SERVICE_REGISTRY.register_service("remove_user", [PRODUCT_ID])
    async def async_remove_user(self, call: ServiceCall, device: TuyaBLEDevice) -> None:
        """Service to remove a specific fingerprint or an entire user from the hardware."""
        # 1. Retrieve and Validate Inputs
        raw_user_id = call.data.get("user_id")
        if raw_user_id is None:
            if self.edit_user is None:
                _LOGGER.error("Enrollment failed: No user provided in call or buffer")
                return
            raw_user_id = self.edit_user

        try:
            user_id = int(raw_user_id)
        except (TypeError, ValueError):
            _LOGGER.error("Removal failed: Invalid ID provided (User: %s,)", raw_user_id)
            return

        # 2. logical Bounds Check
        if not (0 <= user_id <= 255):
            _LOGGER.error("Removal failed: User ID %s out of range (0-255)", user_id)
            return

        # 3. Check Local State (Optional but recommended)
        u_id_str = str(user_id)
        if u_id_str not in self.users:
            _LOGGER.warning("Sending removal command for User %s, but user not found in local state.", user_id)

        # 4. Construct Payload
        _LOGGER.info("Sending hardware command: Remove ALL fingerprints for user %s", user_id)
        # 000000 + UserID + FF00 (Delete user/all)
        payload = bytes.fromhex("000000") + bytes([user_id]) + bytes.fromhex("FF00")

        # 5. Send to Device
        # Using UNLOCK_METHOD_DELETE (often DP 52 or similar)
        datapoint = device.datapoints.get_or_create(
            TuyaBLELockDP.UNLOCK_METHOD_DELETE, 
            TuyaBLEDataPointType.DT_RAW, 
            0
        )

        if datapoint:
            try:
                await datapoint.set_value(payload)
                _LOGGER.debug("Removal payload sent: %s", payload.hex())
            except Exception as err:
                _LOGGER.error("Failed to send removal command to lock: %s", err)
                return
        else:
            _LOGGER.error("Removal failed: Could not find UNLOCK_METHOD_DELETE datapoint")
            return

        # 6. Local Cleanup (Optional)
        # You might want to remove it from your local self.users here 
        # OR wait for the lock to confirm via a separate DP response.
        
        self._coordinator.async_update_listeners()

    @SERVICE_REGISTRY.register_service("retrieve_fingerprints", [PRODUCT_ID])
    async def async_retrieve_fingerprints(self, call: ServiceCall, device: TuyaBLEDevice) -> None:
        """Service to retrieve fingerprints."""
        datapoint = self._device.datapoints.get_or_create(TuyaBLELockDP.SYNC_USERS, TuyaBLEDataPointType.DT_RAW)
        if datapoint:
            await datapoint.set_value(bytes([3]))  # 03 - Request fingerprint sync
            self.fingerprint_sync_active = True

            # 2. Wait for the lock to process
            # We use a timeout because Bluetooth can be flaky
            try:
                for _ in range(10):  # Wait up to 10 seconds
                    await asyncio.sleep(1)
                    if self.fingerprint_sync_active is False:
                        break
            finally:
                _LOGGER.info("Fingerprint sync process ended.")
                # 3. Schedule a permanent save
                await self.async_save()
        self._coordinator.async_update_listeners()

    @SERVICE_REGISTRY.register_service("rename_user", [PRODUCT_ID])
    async def async_rename_user(self, call: ServiceCall, device: TuyaBLEDevice) -> None:
        """Service to rename an existing user."""
        # 1. Retrieve ID and name
        user_id = call.data.get("user_id")
        if user_id is None:
            if self.edit_user is None:
                _LOGGER.error("Enrollment failed: No user provided in call or buffer")
                return
            user_id = self.edit_user

        new_name = call.data.get("new_name")
        if new_name is None:
            new_name = ""


        # 2. Fallback to buffer if new_name is not provided in call
        if not new_name:
            buffer_entity = f"text.{device.device_id}_name_buffer"
            buffer_state = self._hass.states.get(buffer_entity)
            new_name = buffer_state.state if buffer_state else None

        # 3. Validation: Check for Name
        if not new_name or new_name.strip() == "":
            _LOGGER.error("Rename failed: No name provided in call or buffer")
            return

        # 4. Validation: Check for User ID existence
        # Ensure user_id is a string for dictionary lookup
        u_id_str = str(user_id)
        if u_id_str not in self.users:
            _LOGGER.error("Rename failed: User ID %s not found in local state", u_id_str)
            return

        # 5. Logic: Perform the rename
        _LOGGER.info("Renaming user %s from '%s' to '%s'", 
                     u_id_str, self.users[u_id_str].name, new_name)
        
        self.users[u_id_str].name = new_name

        # 6. Persistence: Save to store
        data_to_save = {
            str(u_id): asdict(user) for u_id, user in self.users.items()
        }
        
        try:
            await self.store.async_save(data_to_save)
            _LOGGER.debug("User data successfully saved to store")
        except Exception as err:
            _LOGGER.error("Failed to save renamed user to store: %s", err)
            return

        # 7. Cleanup: Reset the buffer so it doesn't leak into the next action
        await self._hass.services.async_call(
            "text", 
            "set_value", 
            {"entity_id": f"text.{device.device_id}_name_buffer", "value": ""},
            blocking=False
        )

        # 8. Update UI
        self._coordinator.async_update_listeners()

    @SERVICE_REGISTRY.register_service("rename_fingerprint", [PRODUCT_ID])
    async def async_rename_fingerprint(self, call: ServiceCall, device: TuyaBLEDevice) -> None:
        """Service to rename an existing fingerprint in the local store."""
        # 1. Retrieve and Cast IDs
        user_id = call.data.get("user_id")
        if user_id is None:
            if self.edit_user is None:
                _LOGGER.error("Enrollment failed: No user provided in call or buffer")
                return
            user_id = self.edit_user

        fingerprint_id = call.data.get("fingerprint_id")
        if fingerprint_id is None:
            if self.edit_fingerprint is None:
                _LOGGER.error("Enrollment failed: No fingerprint id provided in call or buffer")
                return
            fingerprint_id = self.edit_fingerprint

        new_name = call.data.get("new_name")

        if not new_name:
            buffer_id = f"text.{device.device_id}_name_buffer"
            state = self._hass.states.get(buffer_id)
            new_name = state.state if state else None

        # 3. Validation: Check for Name
        if not new_name or new_name.strip() == "":
            _LOGGER.error("Rename Fingerprint failed: No name provided in call or buffer")
            return

        # 4. Validation: Check for User and Fingerprint existence
        # Ensure we are using strings for dictionary lookups
        u_id_str = str(user_id)
        fp_id_str = str(fingerprint_id)

        if u_id_str not in self.users:
            _LOGGER.error("Rename Fingerprint failed: User ID %s not found", u_id_str)
            return

        if fp_id_str not in self.users[u_id_str].fingerprints:
            _LOGGER.error("Rename Fingerprint failed: Fingerprint ID %s not found for user %s", fp_id_str, u_id_str)
            return

        # 5. Logic: Perform the rename
        old_name = self.users[u_id_str].fingerprints[fp_id_str].name
        _LOGGER.info("Renaming Fingerprint %s for User %s: '%s' -> '%s'", 
                     fp_id_str, u_id_str, old_name, new_name)
        
        self.users[u_id_str].fingerprints[fp_id_str].name = new_name.strip()

        # 6. Persistence: Save to store
        data_to_save = {
            str(u_id): asdict(user) for u_id, user in self.users.items()
        }
        
        try:
            await self.store.async_save(data_to_save)
        except Exception as err:
            _LOGGER.error("Failed to save renamed fingerprint to store: %s", err)
            return

        # 7. Cleanup: Reset the buffer
        await self._hass.services.async_call(
            "text", 
            "set_value", 
            {"entity_id": f"text.{device.device_id}_name_buffer", "value": ""},
            blocking=False
        )

        # 8. Update UI
        self._coordinator.async_update_listeners()