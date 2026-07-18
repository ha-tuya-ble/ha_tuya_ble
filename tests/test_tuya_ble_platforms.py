import sys
import types
from dataclasses import dataclass

# Helper to create mock modules
def mock_module(name, **kwargs):
    mod = types.ModuleType(name)
    for k, v in kwargs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod

# Create a mock Platform class/enum
class MockPlatform:
    BINARY_SENSOR = "binary_sensor"
    BUTTON = "button"
    CLIMATE = "climate"
    COVER = "cover"
    LIGHT = "light"
    LOCK = "lock"
    NUMBER = "number"
    SELECT = "select"
    SENSOR = "sensor"
    SWITCH = "switch"
    TEXT = "text"

# Define mock base classes to avoid metaclass conflicts and handle dynamic kwargs
class FlexibleDummy:
    def __init__(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class GenericDummy(FlexibleDummy):
    def __class_getitem__(cls, item):
        return cls

class MetaMock(type):
    def __getattr__(cls, name):
        if name == "Platform":
            return MockPlatform
        # Recursively return a mock class that is a subclass of FlexibleDummy
        return MetaMock(name, (FlexibleDummy,), {})

    def __str__(cls):
        return cls.__name__.lower()

class MockConst(metaclass=MetaMock):
    pass

class MockTuyaCloudOpenAPIEndpoint(metaclass=MetaMock):
    pass

class MockTuyaIoT(metaclass=MetaMock):
    pass

class MockDeviceClass(metaclass=MetaMock):
    pass

# Setup dynamic EntityDescription dataclass
@dataclass
class MockEntityDescription:
    key: str = ""
    name: str | None = None
    icon: str | None = None
    device_class: str | None = None
    entity_category: str | None = None
    state_class: str | None = None
    translation_key: str | None = None
    unit_of_measurement: str | None = None
    options: list | None = None
    pattern: str | None = None
    brightness_max: str | None = None
    brightness_min: str | None = None
    brightness: str | None = None
    color_data: str | None = None
    color_mode: str | None = None
    color_temp: str | None = None
    default_color_type: str | None = None
    values_overrides: dict | None = None
    values_defaults: dict | None = None
    function: list | None = None
    status_range: list | None = None
    native_max_value: float | None = None
    native_min_value: float | None = None
    native_step: float | None = None
    native_unit_of_measurement: str | None = None
    entity_registry_enabled_default: bool | None = None
    suggested_display_precision: int | None = None
    mode: str | None = None

# Setup mock modules
mock_module("homeassistant")
sys.modules["homeassistant.const"] = MockConst
mock_module("homeassistant.core", CALLBACK_TYPE=FlexibleDummy, HomeAssistant=FlexibleDummy, callback=lambda x: x, Event=FlexibleDummy)
mock_module("homeassistant.helpers", entity=FlexibleDummy)
mock_module("homeassistant.helpers.entity", EntityDescription=MockEntityDescription, DeviceInfo=FlexibleDummy, generate_entity_id=lambda *args, **kwargs: "dummy_id", EntityCategory=MockDeviceClass)
mock_module("homeassistant.helpers.event", async_call_later=FlexibleDummy)
mock_module("homeassistant.helpers.update_coordinator", CoordinatorEntity=GenericDummy, DataUpdateCoordinator=GenericDummy)
mock_module("homeassistant.helpers.device_registry", CONNECTION_BLUETOOTH="bluetooth")
mock_module("homeassistant.helpers.entity_platform", AddEntitiesCallback=FlexibleDummy)

mock_module("homeassistant.components")
mock_module("homeassistant.components.binary_sensor", BinarySensorDeviceClass=MockDeviceClass, BinarySensorEntity=FlexibleDummy, BinarySensorEntityDescription=MockEntityDescription)
mock_module("homeassistant.components.button", ButtonEntityDescription=MockEntityDescription, ButtonEntity=FlexibleDummy, ButtonDeviceClass=MockDeviceClass)
mock_module("homeassistant.components.climate", ClimateEntityDescription=MockEntityDescription, ClimateEntity=FlexibleDummy)
mock_module("homeassistant.components.climate.const", ClimateEntityFeature=MockDeviceClass, HVACMode=MockDeviceClass, HVACAction=MockDeviceClass, PRESET_AWAY="away", PRESET_NONE="none")
mock_module("homeassistant.components.cover", CoverEntityDescription=MockEntityDescription, CoverEntityFeature=MockDeviceClass, CoverEntity=FlexibleDummy, ATTR_POSITION="position", ATTR_TILT_POSITION="tilt_position")
mock_module("homeassistant.components.light", ATTR_BRIGHTNESS="brightness", ATTR_COLOR_TEMP_KELVIN="color_temp_kelvin", ATTR_HS_COLOR="hs_color", ColorMode=MockDeviceClass, LightEntity=FlexibleDummy, LightEntityDescription=MockEntityDescription)
mock_module("homeassistant.components.lock", LockEntity=FlexibleDummy, LockEntityFeature=MockDeviceClass, LockEntityDescription=MockEntityDescription)
mock_module("homeassistant.components.number", NumberEntityDescription=MockEntityDescription, NumberEntity=FlexibleDummy)
mock_module("homeassistant.components.number.const", NumberDeviceClass=MockDeviceClass, NumberMode=MockDeviceClass)
mock_module("homeassistant.components.select", SelectEntityDescription=MockEntityDescription, SelectEntity=FlexibleDummy)
mock_module("homeassistant.components.sensor", SensorDeviceClass=MockDeviceClass, SensorEntity=FlexibleDummy, SensorEntityDescription=MockEntityDescription, SensorStateClass=MockDeviceClass)
mock_module("homeassistant.components.switch", SwitchEntityDescription=MockEntityDescription, SwitchEntity=FlexibleDummy, SwitchDeviceClass=MockDeviceClass)
mock_module("homeassistant.components.text", TextEntity=FlexibleDummy, TextEntityDescription=MockEntityDescription)

mock_module("homeassistant.util", color=FlexibleDummy)
mock_module("homeassistant.util.color", color_temperature_mired_to_kelvin=lambda x: x, color_hsv_to_RGB=lambda *args: (255, 255, 255))
mock_module("homeassistant.config_entries", ConfigEntry=FlexibleDummy)
mock_module("homeassistant.exceptions", ConfigEntryNotReady=Exception)

mock_bluetooth = mock_module("homeassistant.components.bluetooth", BluetoothServiceInfoBleak=FlexibleDummy, BluetoothCallbackMatcher=FlexibleDummy, async_register_callback=lambda *args, **kwargs: None, BluetoothScanningMode=FlexibleDummy)
sys.modules["homeassistant.components"].bluetooth = mock_bluetooth

mock_match = mock_module("homeassistant.components.bluetooth.match", ADDRESS="address", BluetoothCallbackMatcher=FlexibleDummy)
sys.modules["homeassistant.components.bluetooth"].match = mock_match

# Other 3rd party libraries
mock_module("bleak")
mock_module("bleak.exc", BleakDBusError=Exception)
mock_module("bleak.backends")
mock_module("bleak.backends.device", BLEDevice=FlexibleDummy)
mock_module("bleak.backends.scanner", AdvertisementData=FlexibleDummy)
mock_module(
    "bleak_retry_connector",
    BLEAK_RETRY_EXCEPTIONS=(),
    get_device=FlexibleDummy,
    BLEAK_BACKOFF_TIME=0.25,
    BleakClientWithServiceCache=FlexibleDummy,
    check_connected_bleak_client=FlexibleDummy,
    BleakError=Exception,
    BleakNotFoundError=Exception,
    establish_connection=FlexibleDummy,
)
mock_module("home_assistant_bluetooth", BluetoothServiceInfoBleak=FlexibleDummy)
mock_module("cryptography")
mock_module("cryptography.hazmat")
mock_module("cryptography.hazmat.primitives")
mock_module("cryptography.hazmat.primitives.ciphers")
mock_module("cryptography.hazmat.primitives.ciphers.algorithms")
mock_module("cryptography.hazmat.primitives.ciphers.modes")
mock_module("Crypto")
mock_module("Crypto.Cipher", AES=FlexibleDummy)
sys.modules["tuya_iot"] = MockTuyaIoT
mock_module("typing_extensions", Final=FlexibleDummy)

# Pre-import TuyaBLEEntityDescription to dynamically patch its __init__
from custom_components.tuya_ble.tuya_ble.tuya_ble import TuyaBLEEntityDescription
def dynamic_init(self, *args, **kwargs):
    for k, v in kwargs.items():
        setattr(self, k, v)
TuyaBLEEntityDescription.__init__ = dynamic_init

# Now we can import the classes safely
from custom_components.tuya_ble.devices import TuyaBLEEntity
from custom_components.tuya_ble.binary_sensor import TuyaBLEBinarySensor
from custom_components.tuya_ble.button import TuyaBLEButton
from custom_components.tuya_ble.climate import TuyaBLEClimate
from custom_components.tuya_ble.cover import TuyaBLECover
from custom_components.tuya_ble.light import TuyaBLELight
from custom_components.tuya_ble.lock import TuyaBLELock
from custom_components.tuya_ble.number import TuyaBLENumber
from custom_components.tuya_ble.select import TuyaBLESelect
from custom_components.tuya_ble.sensor import TuyaBLESensor
from custom_components.tuya_ble.switch import TuyaBLESwitch
from custom_components.tuya_ble.text import TuyaBLEText

def test_tuya_ble_platforms():
    assert TuyaBLEEntity.platform == MockPlatform.SENSOR
    assert TuyaBLEBinarySensor.platform == MockPlatform.BINARY_SENSOR
    assert TuyaBLEButton.platform == MockPlatform.BUTTON
    assert TuyaBLEClimate.platform == MockPlatform.CLIMATE
    assert TuyaBLECover.platform == MockPlatform.COVER
    assert TuyaBLELight.platform == MockPlatform.LIGHT
    assert TuyaBLELock.platform == MockPlatform.LOCK
    assert TuyaBLENumber.platform == MockPlatform.NUMBER
    assert TuyaBLESelect.platform == MockPlatform.SELECT
    assert TuyaBLESensor.platform == MockPlatform.SENSOR
    assert TuyaBLESwitch.platform == MockPlatform.SWITCH
    assert TuyaBLEText.platform == MockPlatform.TEXT
    print("All platform attributes are correctly verified!")

if __name__ == "__main__":
    test_tuya_ble_platforms()
