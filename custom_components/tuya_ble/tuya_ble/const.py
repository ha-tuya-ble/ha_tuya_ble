from __future__ import annotations

from enum import Enum, StrEnum

GATT_MTU = 20

DEFAULT_ATTEMPTS = 0xFFFF

CHARACTERISTIC_NOTIFY = "00002b10-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_WRITE = "00002b11-0000-1000-8000-00805f9b34fb"

SERVICE_UUID = "0000a201-0000-1000-8000-00805f9b34fb"

MANUFACTURER_DATA_ID = 0x07D0

RESPONSE_WAIT_TIMEOUT = 60


class TuyaBLECode(Enum):
    """Enumeration of Tuya BLE function codes used for device communications and control.

    This class defines various function codes that represent different operations in the Tuya BLE protocol,
    including device information transmission, pairing, data point (DPS) handling, OTA updates, and device control
    commands. The codes are split into sender functions (codes in the 0x0000-0x0027 range) and receiver functions
    (codes in the 0x8001-0x8012 range), which handle incoming data or requests from devices.

    Attributes:
        FUN_SENDER_DEVICE_INFO (int): 0x0000 - Transmit device information.
        FUN_SENDER_PAIR (int): 0x0001 - Initiate device pairing.
        FUN_SENDER_DPS (int): 0x0002 - Send data points (DPS) data.
        FUN_SENDER_DEVICE_STATUS (int): 0x0003 - Transmit device status updates.
        FUN_SENDER_UNBIND (int): 0x0005 - Command to unbind or deauthorize the device.
        FUN_SENDER_DEVICE_RESET (int): 0x0006 - Reset the device settings.
        FUN_SENDER_OTA_START (int): 0x000C - Start the Over-The-Air (OTA) update process.
        FUN_SENDER_OTA_FILE (int): 0x000D - Transmit a segment of the OTA file.
        FUN_SENDER_OTA_OFFSET (int): 0x000E - Specify the offset for the OTA file transmission.
        FUN_SENDER_OTA_UPGRADE (int): 0x000F - Execute the OTA upgrade procedure.
        FUN_SENDER_OTA_OVER (int): 0x0010 - Indicate completion of the OTA process.
        FUN_SENDER_DPS_V4 (int): 0x0027 - Send version 4 DPS data.
        FUN_RECEIVE_DP (int): 0x8001 - Receive standard DPS data.
        FUN_RECEIVE_TIME_DP (int): 0x8003 - Receive DPS data with associated timestamp.
        FUN_RECEIVE_SIGN_DP (int): 0x8004 - Receive signed DPS data.
        FUN_RECEIVE_SIGN_TIME_DP (int): 0x8005 - Receive signed DPS data with timestamp.
        FUN_RECEIVE_DP_V4 (int): 0x8006 - Receive version 4 DPS data.
        FUN_RECEIVE_TIME_DP_V4 (int): 0x8007 - Receive version 4 DPS data with time information.
        FUN_RECEIVE_TIME1_REQ (int): 0x8011 - Handle the first type of time request.
        FUN_RECEIVE_TIME2_REQ (int): 0x8012 - Handle the second type of time request.

    """

    FUN_SENDER_DEVICE_INFO = 0x0000
    FUN_SENDER_PAIR = 0x0001
    FUN_SENDER_DPS = 0x0002
    FUN_SENDER_DEVICE_STATUS = 0x0003

    FUN_SENDER_UNBIND = 0x0005
    FUN_SENDER_DEVICE_RESET = 0x0006

    FUN_SENDER_OTA_START = 0x000C
    FUN_SENDER_OTA_FILE = 0x000D
    FUN_SENDER_OTA_OFFSET = 0x000E
    FUN_SENDER_OTA_UPGRADE = 0x000F
    FUN_SENDER_OTA_OVER = 0x0010

    FUN_SENDER_DPS_V4 = 0x0027

    FUN_RECEIVE_DP = 0x8001
    FUN_RECEIVE_TIME_DP = 0x8003
    FUN_RECEIVE_SIGN_DP = 0x8004
    FUN_RECEIVE_SIGN_TIME_DP = 0x8005

    FUN_RECEIVE_DP_V4 = 0x8006
    FUN_RECEIVE_TIME_DP_V4 = 0x8007

    FUN_RECEIVE_TIME1_REQ = 0x8011
    FUN_RECEIVE_TIME2_REQ = 0x8012


class TuyaBLEDataPointType(Enum):
    """Enum representing the different data point types for the Tuya BLE protocol.

    Attributes:
        DT_RAW (int): Represents raw data.
        DT_BOOL (int): Represents a boolean value.
        DT_VALUE (int): Represents a numerical value.
        DT_STRING (int): Represents a string.
        DT_ENUM (int): Represents an enumerated type.
        DT_BITMAP (int): Represents a bitmap value.

    """

    DT_RAW = 0
    DT_BOOL = 1
    DT_VALUE = 2
    DT_STRING = 3
    DT_ENUM = 4
    DT_BITMAP = 5


class TuyaDataPointCode(StrEnum):
    """Data Point Codes used by Tuya.

    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq
    """

    AIR_QUALITY = "air_quality"
    AIR_QUALITY_INDEX = "air_quality_index"
    ALARM_SWITCH = "alarm_switch"  # Alarm switch
    ALARM_TIME = "alarm_time"  # Alarm time
    ALARM_VOLUME = "alarm_volume"  # Alarm volume
    ALARM_MESSAGE = "alarm_message"
    ANGLE_HORIZONTAL = "angle_horizontal"
    ANGLE_VERTICAL = "angle_vertical"
    ANION = "anion"  # Ionizer unit
    ARM_DOWN_PERCENT = "arm_down_percent"
    ARM_UP_PERCENT = "arm_up_percent"
    BASIC_ANTI_FLICKER = "basic_anti_flicker"
    BASIC_DEVICE_VOLUME = "basic_device_volume"
    BASIC_FLIP = "basic_flip"
    BASIC_INDICATOR = "basic_indicator"
    BASIC_NIGHTVISION = "basic_nightvision"
    BASIC_OSD = "basic_osd"
    BASIC_PRIVATE = "basic_private"
    BASIC_WDR = "basic_wdr"
    BATTERY = "battery"  # Used by non-standard contact sensor implementations
    BATTERY_PERCENTAGE = "battery_percentage"  # Battery percentage
    BATTERY_STATE = "battery_state"  # Battery state
    BATTERY_VALUE = "battery_value"  # Battery value
    BRIGHT_CONTROLLER = "bright_controller"
    BRIGHT_STATE = "bright_state"  # Brightness status
    BRIGHT_VALUE = "bright_value"  # Brightness
    BRIGHT_VALUE_1 = "bright_value_1"
    BRIGHT_VALUE_2 = "bright_value_2"
    BRIGHT_VALUE_3 = "bright_value_3"
    BRIGHT_VALUE_V2 = "bright_value_v2"
    BRIGHTNESS_MAX_1 = "brightness_max_1"
    BRIGHTNESS_MAX_2 = "brightness_max_2"
    BRIGHTNESS_MAX_3 = "brightness_max_3"
    BRIGHTNESS_MIN_1 = "brightness_min_1"
    BRIGHTNESS_MIN_2 = "brightness_min_2"
    BRIGHTNESS_MIN_3 = "brightness_min_3"
    C_F = "c_f"  # Temperature unit switching
    CH2O_STATE = "ch2o_state"
    CH2O_VALUE = "ch2o_value"
    CH4_SENSOR_STATE = "ch4_sensor_state"
    CH4_SENSOR_VALUE = "ch4_sensor_value"
    CHILD_LOCK = "child_lock"  # Child lock
    CISTERN = "cistern"
    CLEAN_AREA = "clean_area"
    CLEAN_TIME = "clean_time"
    CLICK_SUSTAIN_TIME = "click_sustain_time"
    CLOUD_RECIPE_NUMBER = "cloud_recipe_number"
    CLOSED_OPENED_KIT = "closed_opened_kit"
    CO_STATE = "co_state"
    CO_STATUS = "co_status"
    CO_VALUE = "co_value"
    CO2_STATE = "co2_state"
    CO2_VALUE = "co2_value"  # CO2 concentration
    COLLECTION_MODE = "collection_mode"
    COLOR_DATA_V2 = "color_data_v2"
    COLOUR_DATA = "colour_data"  # Colored light mode
    COLOUR_DATA_HSV = "colour_data_hsv"  # Colored light mode
    COLOUR_DATA_V2 = "colour_data_v2"  # Colored light mode
    COOK_TEMPERATURE = "cook_temperature"
    COOK_TIME = "cook_time"
    CONCENTRATION_SET = "concentration_set"  # Concentration setting
    CONTROL = "control"
    CONTROL_2 = "control_2"
    CONTROL_3 = "control_3"
    CONTROL_BACK = "control_back"
    CONTROL_BACK_MODE = "control_back_mode"
    COUNTDOWN = "countdown"  # Countdown
    COUNTDOWN_LEFT = "countdown_left"
    COUNTDOWN_SET = "countdown_set"  # Countdown setting
    CRY_DETECTION_SWITCH = "cry_detection_switch"
    CUP_NUMBER = "cup_number"  # NUmber of cups
    CUR_CURRENT = "cur_current"  # Actual current
    CUR_NEUTRAL = "cur_neutral"  # Total reverse energy
    CUR_POWER = "cur_power"  # Actual power
    CUR_VOLTAGE = "cur_voltage"  # Actual voltage
    DECIBEL_SENSITIVITY = "decibel_sensitivity"
    DECIBEL_SWITCH = "decibel_switch"
    DEHUMIDITY_SET_ENUM = "dehumidify_set_enum"
    DEHUMIDITY_SET_VALUE = "dehumidify_set_value"
    DISINFECTION = "disinfection"
    DO_NOT_DISTURB = "do_not_disturb"
    DOORCONTACT_STATE = "doorcontact_state"  # Status of door window sensor
    DOORCONTACT_STATE_2 = "doorcontact_state_2"
    DOORCONTACT_STATE_3 = "doorcontact_state_3"
    DUSTER_CLOTH = "duster_cloth"
    ECO2 = "eco2"
    EDGE_BRUSH = "edge_brush"
    ELECTRICITY_LEFT = "electricity_left"
    FAN_BEEP = "fan_beep"  # Sound
    FAN_COOL = "fan_cool"  # Cool wind
    FAN_DIRECTION = "fan_direction"  # Fan direction
    FAN_HORIZONTAL = "fan_horizontal"  # Horizontal swing flap angle
    FAN_SPEED = "fan_speed"
    FAN_SPEED_ENUM = "fan_speed_enum"  # Speed mode
    FAN_SPEED_PERCENT = "fan_speed_percent"  # Stepless speed
    FAN_SWITCH = "fan_switch"
    FAN_MODE = "fan_mode"
    FAN_VERTICAL = "fan_vertical"  # Vertical swing flap angle
    FAR_DETECTION = "far_detection"
    FAULT = "fault"
    FEED_REPORT = "feed_report"
    FEED_STATE = "feed_state"
    FILTER = "filter"
    FILTER_LIFE = "filter"
    FILTER_RESET = "filter_reset"  # Filter (cartridge) reset
    FLOODLIGHT_LIGHTNESS = "floodlight_lightness"
    FLOODLIGHT_SWITCH = "floodlight_switch"
    FORWARD_ENERGY_TOTAL = "forward_energy_total"
    GAS_SENSOR_STATE = "gas_sensor_state"
    GAS_SENSOR_STATUS = "gas_sensor_status"
    GAS_SENSOR_VALUE = "gas_sensor_value"
    HUMIDIFIER = "humidifier"  # Humidification
    HUMIDITY = "humidity"  # Humidity
    HUMIDITY_CURRENT = "humidity_current"  # Current humidity
    HUMIDITY_INDOOR = "humidity_indoor"  # Indoor humidity
    HUMIDITY_SET = "humidity_set"  # Humidity setting
    HUMIDITY_VALUE = "humidity_value"  # Humidity
    IPC_WORK_MODE = "ipc_work_mode"
    LED_TYPE_1 = "led_type_1"
    LED_TYPE_2 = "led_type_2"
    LED_TYPE_3 = "led_type_3"
    LEVEL = "level"
    LEVEL_CURRENT = "level_current"
    LIGHT = "light"  # Light
    LIGHT_MODE = "light_mode"
    LOCK = "lock"  # Lock / Child lock
    MASTER_MODE = "master_mode"  # alarm mode
    MACH_OPERATE = "mach_operate"
    MANUAL_FEED = "manual_feed"
    MATERIAL = "material"  # Material
    MODE = "mode"  # Working mode / Mode
    MOODLIGHTING = "moodlighting"  # Mood light
    MOTION_RECORD = "motion_record"
    MOTION_SENSITIVITY = "motion_sensitivity"
    MOTION_SWITCH = "motion_switch"  # Motion switch
    MOTION_TRACKING = "motion_tracking"
    MOVEMENT_DETECT_PIC = "movement_detect_pic"
    MUFFLING = "muffling"  # Muffling
    NEAR_DETECTION = "near_detection"
    OPPOSITE = "opposite"
    PAUSE = "pause"
    PERCENT_CONTROL = "percent_control"
    PERCENT_CONTROL_2 = "percent_control_2"
    PERCENT_CONTROL_3 = "percent_control_3"
    PERCENT_STATE = "percent_state"
    PERCENT_STATE_2 = "percent_state_2"
    PERCENT_STATE_3 = "percent_state_3"
    POSITION = "position"
    PHASE_A = "phase_a"
    PHASE_B = "phase_b"
    PHASE_C = "phase_c"
    PIR = "pir"  # Motion sensor
    PM1 = "pm1"
    PM10 = "pm10"
    PM25 = "pm25"
    PM25_STATE = "pm25_state"
    PM25_VALUE = "pm25_value"
    POWDER_SET = "powder_set"  # Powder
    POWER = "power"
    POWER_GO = "power_go"
    POWER_TOTAL = "power_total"
    PRESENCE_STATE = "presence_state"
    PRESSURE_STATE = "pressure_state"
    PRESSURE_VALUE = "pressure_value"
    PUMP = "pump"
    PUMP_RESET = "pump_reset"  # Water pump reset
    OXYGEN = "oxygen"  # Oxygen bar
    RECORD_MODE = "record_mode"
    RECORD_SWITCH = "record_switch"  # Recording switch
    RELAY_STATUS = "relay_status"
    REMAIN_TIME = "remain_time"
    RESET_DUSTER_CLOTH = "reset_duster_cloth"
    RESET_EDGE_BRUSH = "reset_edge_brush"
    RESET_FILTER = "reset_filter"
    RESET_MAP = "reset_map"
    RESET_ROLL_BRUSH = "reset_roll_brush"
    REVERSE_ENERGY_TOTAL = "reverse_energy_total"
    ROLL_BRUSH = "roll_brush"
    SEEK = "seek"
    SENSITIVITY = "sensitivity"  # Sensitivity
    SENSOR_HUMIDITY = "sensor_humidity"
    SENSOR_TEMPERATURE = "sensor_temperature"
    SHAKE = "shake"  # Oscillating
    SHOCK_STATE = "shock_state"  # Vibration status
    SIREN_SWITCH = "siren_switch"
    SITUATION_SET = "situation_set"
    SLEEP = "sleep"  # Sleep function
    SLOW_FEED = "slow_feed"
    SMOKE_SENSOR_STATE = "smoke_sensor_state"
    SMOKE_SENSOR_STATUS = "smoke_sensor_status"
    SMOKE_SENSOR_VALUE = "smoke_sensor_value"
    SOS = "sos"  # Emergency State
    SOS_STATE = "sos_state"  # Emergency mode
    SPEED = "speed"  # Speed level
    SPRAY_MODE = "spray_mode"  # Spraying mode
    START = "start"  # Start
    STATUS = "status"
    STERILIZATION = "sterilization"  # Sterilization
    SUCTION = "suction"
    SWING = "swing"  # Swing mode
    SWITCH = "switch"  # Switch
    SWITCH_1 = "switch_1"  # Switch 1
    SWITCH_2 = "switch_2"  # Switch 2
    SWITCH_3 = "switch_3"  # Switch 3
    SWITCH_4 = "switch_4"  # Switch 4
    SWITCH_5 = "switch_5"  # Switch 5
    SWITCH_6 = "switch_6"  # Switch 6
    SWITCH_7 = "switch_7"  # Switch 7
    SWITCH_8 = "switch_8"  # Switch 8
    SWITCH_BACKLIGHT = "switch_backlight"  # Backlight switch
    SWITCH_CHARGE = "switch_charge"
    SWITCH_CONTROLLER = "switch_controller"
    SWITCH_DISTURB = "switch_disturb"
    SWITCH_FAN = "switch_fan"
    SWITCH_HORIZONTAL = "switch_horizontal"  # Horizontal swing flap switch
    SWITCH_LED = "switch_led"  # Switch
    SWITCH_LED_1 = "switch_led_1"
    SWITCH_LED_2 = "switch_led_2"
    SWITCH_LED_3 = "switch_led_3"
    SWITCH_NIGHT_LIGHT = "switch_night_light"
    SWITCH_SAVE_ENERGY = "switch_save_energy"
    SWITCH_SOUND = "switch_sound"  # Voice switch
    SWITCH_SPRAY = "switch_spray"  # Spraying switch
    SWITCH_USB1 = "switch_usb1"  # USB 1
    SWITCH_USB2 = "switch_usb2"  # USB 2
    SWITCH_USB3 = "switch_usb3"  # USB 3
    SWITCH_USB4 = "switch_usb4"  # USB 4
    SWITCH_USB5 = "switch_usb5"  # USB 5
    SWITCH_USB6 = "switch_usb6"  # USB 6
    SWITCH_VERTICAL = "switch_vertical"  # Vertical swing flap switch
    SWITCH_VOICE = "switch_voice"  # Voice switch
    TARGET_DIS_CLOSEST = "target_dis_closest"  # Closest target distance
    TEMP = "temp"  # Temperature setting
    TEMP_BOILING_C = "temp_boiling_c"
    TEMP_BOILING_F = "temp_boiling_f"
    TEMP_CONTROLLER = "temp_controller"
    TEMP_CURRENT = "temp_current"  # Current temperature in °C
    TEMP_CURRENT_F = "temp_current_f"  # Current temperature in °F
    TEMP_INDOOR = "temp_indoor"  # Indoor temperature in °C
    TEMP_SET = "temp_set"  # Set the temperature in °C
    TEMP_SET_F = "temp_set_f"  # Set the temperature in °F
    TEMP_UNIT_CONVERT = "temp_unit_convert"  # Temperature unit switching
    TEMP_VALUE = "temp_value"  # Color temperature
    TEMP_VALUE_V2 = "temp_value_v2"
    TEMPER_ALARM = "temper_alarm"  # Tamper alarm
    TIME_TOTAL = "time_total"
    TIME_USE = "time_use"  # Total seconds of irrigation
    TOTAL_CLEAN_AREA = "total_clean_area"
    TOTAL_CLEAN_COUNT = "total_clean_count"
    TOTAL_CLEAN_TIME = "total_clean_time"
    TOTAL_FORWARD_ENERGY = "total_forward_energy"
    TOTAL_TIME = "total_time"
    TOTAL_PM = "total_pm"
    TOTAL_POWER = "total_power"
    TVOC = "tvoc"
    UPPER_TEMP = "upper_temp"
    UPPER_TEMP_F = "upper_temp_f"
    UV = "uv"  # UV sterilization
    VA_BATTERY = "va_battery"
    VA_HUMIDITY = "va_humidity"
    VA_TEMPERATURE = "va_temperature"
    VOC_STATE = "voc_state"
    VOC_VALUE = "voc_value"
    VOICE_SWITCH = "voice_switch"
    VOICE_TIMES = "voice_times"
    VOLUME_SET = "volume_set"
    WARM = "warm"  # Heat preservation
    WARM_TIME = "warm_time"  # Heat preservation time
    WATER = "water"
    WATER_RESET = "water_reset"  # Resetting of water usage days
    WATER_SET = "water_set"  # Water level
    WATERSENSOR_STATE = "watersensor_state"
    WEATHER_DELAY = "weather_delay"
    WET = "wet"  # Humidification
    WINDOW_CHECK = "window_check"
    WINDOW_STATE = "window_state"
    WINDSPEED = "windspeed"
    WIRELESS_BATTERYLOCK = "wireless_batterylock"
    WIRELESS_ELECTRICITY = "wireless_electricity"
    WORK_MODE = "work_mode"  # Working mode
    WORK_POWER = "work_power"


class TuyaDataPointType(StrEnum):
    """Data point types."""

    BOOLEAN = "Boolean"
    ENUM = "Enum"
    INTEGER = "Integer"
    JSON = "Json"
    RAW = "Raw"
    STRING = "String"


class TuyaWorkMode(StrEnum):
    """Work modes."""

    COLOUR = "colour"
    MUSIC = "music"
    SCENE = "scene"
    WHITE = "white"
