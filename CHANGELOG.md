# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog],
and this project adheres to [Semantic Versioning].

## [0.7.1](https://github.com/ha-tuya-ble/ha_tuya_ble/releases/tag/0.7.1) - 2026-07-20

### Features
* Add Home Assistant vacuum platform support for Tuya BLE devices via @buliaksk by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/237

### Devices
* Add support for HU06 Smart Lock (stugc8dl) by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/231
* Add YZD05 water valve (d4vpmigg) support via @hippich by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/198
* Add support for robotic window cleaner (cxjmb / product pnxl0r3l) by @buliaksk in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/159
* fix: Add support for TH05 Temperature Sensor (vyfoip9h, 1jvidcsf) by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/238

### Misc
* Add release-please GitHub action by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/239
* fix: Update CHANGELOG for version 0.3.1 by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/240
* Update translations to sync with en.json by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/233

### New Contributors
* @buliaksk made their first contribution in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/159

**Full Changelog**: https://github.com/ha-tuya-ble/ha_tuya_ble/compare/0.7.0...0.7.1

## [0.7.0](https://github.com/ha-tuya-ble/ha_tuya_ble/releases/tag/0.7.0) - 2026-07-19

### What's Changed
* Pin pytest-homeassistant-custom-component version by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/195
* Report zwjcy soil sensor humidity DP as soil moisture by @sytchi in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/196
* Terminate 'ensure connected' and reconnect tasks on "Bluetooth is already shutdown" by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/201
* Add support and enhancements for Aldi Gardenline (16wgjvck) water valve mappings. And added support for Atomic Multi-Datapoint Payloads (simultaneous DP dispatch). by @ProfessorQuantumUniverse in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/151
* Add support for Primebras Athenas (6fibxtph) and Foxgard (99gv5nmz) locks by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/226
* Fix support for B16 (ajk32biq) lock (#121) by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/225
* Add translations for multiple languages by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/229
* Add Arlec Smart Button support by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/228
* Add support for Gainsborough Liberty Lock (yfqp0shy) via @deg3n by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/230

### New Contributors
* @ProfessorQuantumUniverse made their first contribution in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/151

**Full Changelog**: https://github.com/ha-tuya-ble/ha_tuya_ble/compare/0.6.0...0.7.0

## [0.6.0](https://github.com/ha-tuya-ble/ha_tuya_ble/releases/tag/0.6.0) - 2026-07-18

### Breaking change
* Fix entity ID wrong domain issue by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/193

  Previously, a bug generated the entity_ids all in the sensor domain. This has now been corrected, but means all existing entity ids will be regenerated in the correct domain on upgrade; ie "button.xyz"

  If you have automations that rely on specific entity ids; ensure you plan out time to migrate.

### What's Changed
* Add support for CS-9 Smart Fingerprint Lock by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/189
* Add support for A1 Ultra-JM (hc7n0urm) smart lock by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/190
* Add basic CI by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/7
* Implement minimal passing test coverage for all basic entities by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/194

**Full Changelog**: https://github.com/ha-tuya-ble/ha_tuya_ble/compare/0.5.0...0.6.0

## [0.5.0](https://github.com/ha-tuya-ble/ha_tuya_ble/releases/tag/0.5.0) - 2026-07-18

### What's Changed
* Reformat supported devices list in README.md by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/187
* Update README.md with missing product IDs and remove 'not up to date' wording by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/188
* Fix Tuya BLE connection / notification packet handling issue after reconnect by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/174

**Full Changelog**: https://github.com/ha-tuya-ble/ha_tuya_ble/compare/0.4.9...0.5.0

## [0.4.9](https://github.com/ha-tuya-ble/ha_tuya_ble/releases/tag/0.4.9) - 2026-07-18

### What's Changed
* Add support for RESTMO BT Water Meter (FML026A) by @phoenixxx-1 in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/165
* Add support for Rainpoint TTV102B smart irrigation controller by @edmcman in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/156
* Add support for Tuya BLE Fingerbot SM-FB-01B by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/167
* AOK AM25 Roller Blinds Motor (v3fzfd2y) via @cpw in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/126
* Add support for Temperature Humidity Sensor SS302 (6lbesej0) via @Sathen in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/186
* Add support for Lock P1 (product_id 7a4xvbtt) via @jpmreis in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/185

### New Contributors
* @phoenixxx-1 made their first contribution in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/165
* @edmcman made their first contribution in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/156

**Full Changelog**: https://github.com/ha-tuya-ble/ha_tuya_ble/compare/0.4.8...0.4.9

## [0.4.8](https://github.com/ha-tuya-ble/ha_tuya_ble/releases/tag/0.4.8) - 2026-07-17

### What's Changed
* Add support to ZX-7378 Smart Irrigation Controller (product: ldcdnigc) by @Zoatik in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/146
* Fix 'Device is not registered in Tuya cloud' when factory-infos returns colon-separated MACs by @sytchi in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/164
* Add support for jtmspro kholoaew smart lock by @Test-subj in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/155

### New Contributors
* @Zoatik made their first contribution in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/146
* @sytchi made their first contribution in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/164
* @Test-subj made their first contribution in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/155

**Full Changelog**: https://github.com/ha-tuya-ble/ha_tuya_ble/compare/0.4.7...0.4.8

## [0.4.7](https://github.com/ha-tuya-ble/ha_tuya_ble/releases/tag/0.4.7) - 2026-04-21

### What's Changed
* Fix documentation URL in manifest.json by @agarthand in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/142
* Add support for Switch Robot (kg / 4ctjfrzq) by @michelhn in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/141
* Add support for jtmspro hs21i377 smart lock by @agarthand in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/143
* Remove redundant imports by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/144
* Docs by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/145

### New Contributors
* @agarthand made their first contribution in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/142
* @michelhn made their first contribution in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/141

**Full Changelog**: https://github.com/ha-tuya-ble/ha_tuya_ble/compare/0.4.6...0.4.7

## [0.4.6](https://github.com/ha-tuya-ble/ha_tuya_ble/releases/tag/0.4.6) - 2026-03-08

### What's Changed
* fix for HA 2026.3 by @tabascoz in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/129
* Add a6nttc41 lock (Orion Smart Door Handle Lock) by @hcoohb in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/134

### New Contributors
* @hcoohb made their first contribution in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/134

**Full Changelog**: https://github.com/ha-tuya-ble/ha_tuya_ble/compare/0.4.5.1...0.4.6

## [0.4.5.1](https://github.com/ha-tuya-ble/ha_tuya_ble/releases/tag/0.4.5.1) - 2026-02-14

### What's Changed
* Fix translation validation errors for URLs by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/123
* Fix minor typo by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/125
* Ensure we pass a LockEntityDescription by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/127

**Full Changelog**: https://github.com/ha-tuya-ble/ha_tuya_ble/compare/0.4.5...0.4.5.1

## [0.4.5](https://github.com/ha-tuya-ble/ha_tuya_ble/releases/tag/0.4.5) - 2025-12-28

* Remove doorbell for the moment by @CloCkWeRX

**Full Changelog**: https://github.com/ha-tuya-ble/ha_tuya_ble/compare/0.4.4...0.4.5

## [0.4.4](https://github.com/ha-tuya-ble/ha_tuya_ble/releases/tag/0.4.4) - 2025-12-28

### What's Changed
* Fix lock platform by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/113

**Full Changelog**: https://github.com/ha-tuya-ble/ha_tuya_ble/compare/0.4.3...0.4.4

## [0.4.3](https://github.com/ha-tuya-ble/ha_tuya_ble/releases/tag/0.4.3) - 2025-12-28

### What's Changed
* Remove duplicate const by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/112

**Full Changelog**: https://github.com/ha-tuya-ble/ha_tuya_ble/compare/0.4.2...0.4.3

## [0.4.2](https://github.com/ha-tuya-ble/ha_tuya_ble/releases/tag/0.4.2) - 2025-12-28

### What's Changed
* Add support for AOK AM24 Venetian Blinds Motor (product_id 'dy4dh1q0') - Experimental by @google-labs-jules[bot] in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/85
* Add generic smart lock 'sidhzylo' based on @akelmanson 's work by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/104
* Create CONTRIBUTING.md by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/77
* feat: Add support for SRB-PM01 soil moisture device by @google-labs-jules[bot] in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/91
* Add support for MHO-C402 'tr0kabuq' - experimental by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/106
* Add experimental support for RGB Strip Light '0qgrjxum' by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/107
* Add basic Smart Lock (product_id 'mqc2hevy') support - experimental by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/108

**Full Changelog**: https://github.com/ha-tuya-ble/ha_tuya_ble/compare/0.4.1...0.4.2

## [0.4.1](https://github.com/ha-tuya-ble/ha_tuya_ble/releases/tag/0.4.1) - 2025-12-28

Adds a number of new locks, however items marked experimental have not had their DPs properly checked.

### What's Changed
* Add support for Gimdow A1 Pro Max smart lock (experimental) by @google-labs-jules[bot] in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/93
* feat: Add support for LA-01 Smart lock (experimental) by @google-labs-jules[bot] in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/102
* Add support for B16 smart lock by @google-labs-jules[bot] in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/99
* Add support for Smart Cylinder Lock (product_id 'Z7lj676i') - Experimental by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/103

**Full Changelog**: https://github.com/ha-tuya-ble/ha_tuya_ble/compare/0.4.0...0.4.1

## [0.4.0](https://github.com/ha-tuya-ble/ha_tuya_ble/releases/tag/0.4.0) - 2025-12-28

Adds proof of concept lock platform.
* Flags "ludzroix", "isk2p555", "gumrixyt", "uamrw6h3" as locks
* Amends all existing locks to support the async lock/unlock features

### What's Changed
* Return UUID for devices if found in advertisement and cloud data not available.
* Refactoring: Clean up lock_motor_state, alarm_lock and temperature mapping by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/100
* Add lock platform by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/101

**Full Changelog**: https://github.com/ha-tuya-ble/ha_tuya_ble/compare/0.3.7...0.4.0

## [0.3.7](https://github.com/ha-tuya-ble/ha_tuya_ble/releases/tag/0.3.7) - 2025-11-07

### What's Changed
* feat: Add support for Nedis SmartLife Finger Robot by @google-labs-jules[bot] in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/78
* Drop unused constants for HA 2025.11.0 by @CloCkWeRX and @tabascoz in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/89

### New Contributors
* @google-labs-jules[bot] made their first contribution in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/78

**Full Changelog**: https://github.com/ha-tuya-ble/ha_tuya_ble/compare/0.3.6...0.3.7

## [0.3.6](https://github.com/ha-tuya-ble/ha_tuya_ble/releases/tag/0.3.6) - 2025-09-27

### What's Changed
* Add support for Amazon HeyBlinds blinds by @jiriappl in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/80

### New Contributors
* @jiriappl made their first contribution in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/80

**Full Changelog**: https://github.com/ha-tuya-ble/ha_tuya_ble/compare/0.3.5...0.3.6

## [0.3.5](https://github.com/ha-tuya-ble/ha_tuya_ble/releases/tag/0.3.5) - 2025-08-24

Review and consolidation of all of the active forks.
* Add ulughw4g blind robot by @l3enjamin in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/63
* Add k53ok3u9 Fingerprint Smart Lock by @square-spade in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/65
* Add dependabot by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/67
* Add T55d padlock (bvclwu9b) via @szupi-ipuzs in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/66
* Add umzu0c2y, 6jxcdae1 via @elijahr in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/73

**Full Changelog**: https://github.com/ha-tuya-ble/ha_tuya_ble/compare/0.3.4...0.3.5

## [0.3.4](https://github.com/ha-tuya-ble/ha_tuya_ble/releases/tag/0.3.4) - 2025-08-24

### What's Changed
* add jm6iasmb Bluetooth Temperature Humidity Sensor by @zalsader in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/59

### New Contributors
* @zalsader made their first contribution in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/59

**Full Changelog**: https://github.com/ha-tuya-ble/ha_tuya_ble/compare/0.3.3...0.3.4

## [0.3.3](https://github.com/ha-tuya-ble/ha_tuya_ble/releases/tag/0.3.3) - 2025-07-08

### What's Changed
* Add support for Parkside Performance Smart Battery 4Ah and 8Ah by @Koky05 in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/54

### New Contributors
* @Koky05 made their first contribution in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/54

**Full Changelog**: https://github.com/ha-tuya-ble/ha_tuya_ble/compare/0.3.2...0.3.3

## [0.3.2](https://github.com/ha-tuya-ble/ha_tuya_ble/releases/tag/0.3.2) - 2025-06-20

### What's Changed
* Water Valve - Add Device Functionality - [svhikeyq] by @square-spade in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/52

### New Contributors
* @square-spade made their first contribution in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/52

**Full Changelog**: https://github.com/ha-tuya-ble/ha_tuya_ble/compare/0.3.1...0.3.2

## [0.3.1](https://github.com/ha-tuya-ble/ha_tuya_ble/releases/tag/0.3.1) - 2025-05-14

### What's Changed
* Add hassfest validation by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/36
* Fix hassfest errors by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/44
* Attempt to bring back eslint by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/45
* add support for '46zia2nz' and '1fcnd8xk' water valve controllers by @tabascoz in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/49

### New Contributors
* @tabascoz made their first contribution in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/49

**Full Changelog**: https://github.com/ha-tuya-ble/ha_tuya_ble/compare/0.3.0...0.3.1

## [0.3.0](https://github.com/ha-tuya-ble/ha_tuya_ble/releases/tag/0.3.0) - 2025-04-01

Work in progress release, integrating all of the forks.

Be warned, this is still very much an unstable quality project

### What's Changed
#### Code style and cleanup:
* Remove dud constants by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/8
* Fix spelling by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/9
* Add debugging for when a light device isn't found by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/12
* Fix ATTR_COLOR_TEMP by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/14
* Smartoctopus's Fork - merge (1 of many) by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/15
* Smartoctopus merge (part 2 of many) by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/16
* Smartoctopus merge (part 3 of many) by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/17
* Smartoctopus merge (4 of many) by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/18
* Smartoctopus merge (part 5 of many) by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/19
* Black by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/20
* Check linting by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/31

#### Bug fixes:
* Revert "Update Reconnect" by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/39
* Fix spelling of debug message by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/40
* Fix/reconcile strings.json and translations/en.json by @pauln in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/34

#### Features:
* Add support for Fingerbot Plus with product_id h8kdwywx by @jhthorsen in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/37
* Improve debug logging of cloud API details by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/41
* Add basic device Diagnostics by @CloCkWeRX in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/43

### New Contributors
* @pauln made their first contribution in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/34
* @jhthorsen made their first contribution in https://github.com/ha-tuya-ble/ha_tuya_ble/pull/37

**Full Changelog**: https://github.com/ha-tuya-ble/ha_tuya_ble/commits/0.3.0


## [0.2.0] - 2025-02-01

- Add support for kg family and model bs3ubslo

## [0.1.0] - 2023-04-22

- Initial release


## [0.1.1] - 2023-04-26

### Added

- Added new product_id for Fingerbot Plus (#1)

### Fixed

- Fixed problem in options flow.

### Changed

- Updated strings.json


## [0.1.2] - 2023-04-26

### Changed

- Changed a way to obtain device credentials from Tuya IOT cloud, possible fix to (#2)

## [0.1.4] - 2023-04-30

### Added

- Added support of CUBETOUCH 1s, thanks @damiano75
- Added new product_ids for Fingerbot.
- Added new product_ids for Fingerbot Plus.
- First attempt to support Smart Lock device.

### Fixed

- Fixed possible disconnect of BLE device.

## [0.1.5] - 2023-06-01

### Added

- Added new product_ids for Fingerbot.
- Added event "fingerbot_button_pressed" which is fired on Fingerbot Plus touch button press.
- First attempt to add support of climate entity.

## [0.1.6] - 2023-06-01

### Added

- Added new product_ids for Fingerbot and Fingerbot Plus.

### Changed

- Updated sources to conform Python 3.11

## [0.1.7] - 2023-06-01

### Added

- Added new product_ids.
- Added full support of BLE TRV provided by @forabi
- Added support of programming mode for Fingerbot Plus, thanks @redphx for information.

### Changed

- Improved connection stability.

## [0.1.8] - 2023-07-09

### Added

- Added support of 'Irrigation computer', thanks to @SanMiggel.
- Added new product_ids for Smart locks, thanks to @drewpo28.

### Changed

- Connection to the device is postponed now. Previously some out of range device might prevents HA from fully booting.
- Improved connection stability.


## [0.2.0] - 2024-03-21

### Added

- Add sfkzq/nxquc5lb device

### Changed

- Update readme (forked from)

### Fixed

- fix: Compatibility with HA 2024.1
- Fix deprecated

## [0.2.1] - 2025-03-26

### Added

- Add ggq/hfgdqhho device

### Fixed

- fix: Compatibility with HA 2025.3
- Fix deprecated

## [0.2.2] - 2025-04-16

### Fixed

- Fix deprecated with Home assistant 2025.4.2

### Update

- Update README about device support

## [0.2.3] - 2025-04-25

### Added

- Add ggq/fnlw6npo device
- Add jtmspro/ebd5e0uauqx0vfsp device
