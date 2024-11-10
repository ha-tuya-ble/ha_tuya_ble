# from homeassistant.components.switch import (
#     SwitchEntityDescription,
# )
# from homeassistant.helpers.entity import EntityCategory

# from custom_components.tuya_ble.switch import (
#     TuyaBLECategorySwitchMapping,
#     TuyaBLESwitchMapping,
# )

# mapping: dict[str, TuyaBLECategorySwitchMapping] = {
#     "co2bj": TuyaBLECategorySwitchMapping(
#         products={
#             "59s19z5m": [  # CO2 Detector
#                 TuyaBLESwitchMapping(
#                     dp_id=11,
#                     description=SwitchEntityDescription(
#                         key="carbon_dioxide_severely_exceed_alarm",
#                         icon="mdi:molecule-co2",
#                         entity_category=EntityCategory.CONFIG,
#                         entity_registry_enabled_default=False,
#                     ),
#                     bitmap_mask=b"\x01",
#                 ),
#                 TuyaBLESwitchMapping(
#                     dp_id=11,
#                     description=SwitchEntityDescription(
#                         key="low_battery_alarm",
#                         icon="mdi:battery-alert",
#                         entity_category=EntityCategory.CONFIG,
#                         entity_registry_enabled_default=False,
#                     ),
#                     bitmap_mask=b"\x02",
#                 ),
#                 TuyaBLESwitchMapping(
#                     dp_id=13,
#                     description=SwitchEntityDescription(
#                         key="carbon_dioxide_alarm_switch",
#                         icon="mdi:molecule-co2",
#                         entity_category=EntityCategory.CONFIG,
#                     ),
#                 ),
#             ],
#         },
#     ),
# }
