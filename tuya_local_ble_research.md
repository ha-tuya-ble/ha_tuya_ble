# Tuya Bluetooth Support Research Report

This report provides a comparative analysis of Bluetooth (BLE) device support and architecture between this direct BLE repository (`custom_components/tuya_ble` fork) and the local LAN repository `make-all/tuya-local`.

---

## 1. Executive Summary

- **This Repository (`tuya_ble`)**: A direct, local Bluetooth Low Energy (BLE) integration. It communicates with Tuya BLE devices natively from the Home Assistant host (using local Bluetooth adapters, USB dongles, or ESPHome Bluetooth proxies). It retrieves encryption credentials from the Tuya IoT Cloud during setup but operates entirely locally thereafter.
- **Tuya Local (`tuya-local`)**: A local LAN integration that communicates over TCP/IP (using the `tinytuya` library) directly to WiFi-based Tuya devices. It cannot speak Bluetooth natively. Instead, it supports Bluetooth/BLE devices **indirectly** when they are paired as sub-devices to a **Tuya WiFi/Bluetooth multi-mode Gateway (Hub)**. The Gateway acts as a TCP-to-BLE proxy.

---

## 2. Comparison of Bluetooth Device Support

In `make-all/tuya-local`, Bluetooth devices are listed under the **"Devices supported via Bluetooth hubs"** section in `DEVICES.md`.

Below is a detailed cross-reference comparison of these devices, showing their support status in both integrations:

| Category / Device Name | Status in `make-all/tuya-local` | Status in this `tuya_ble` Repository | Notes / Product IDs |
| :--- | :--- | :--- | :--- |
| **Soil Moisture / Plant Sensors** | Supported | **Supported** | `SGS01` (product ID `gvygg3m8`) and `TCS024B` are supported in `tuya_ble` under the `zwjcy` category. `SRB-PM01` (`jabotj1z`) is also supported. |
| **Water Meters** | Supported | **Supported** | `RESTMO FML026A` (product ID `mqqna0px`) is supported in `tuya_ble` under the `slj` category. |
| **Fingerbots / Switch Robots** | Supported | **Supported** | Adaprox Fingerbot Plus and basic Fingerbots are supported under categories `szjqr` and `kg` in `tuya_ble`. |
| **Raykube A1 Pro Max Lock** | Supported | **Supported** | This is a "jtmspro" category lock (product ID `rlyxv7pe`). Supported in both integrations. |
| **AM24 Venetian Blinds Motor** | Supported | **Supported** | Supported in `tuya_ble` under category `cl` (product ID `dy4dh1q0`). |
| **Parkside PBB-A1 Water Timer** | Supported via Bluetooth hub | **Not Supported** | Mapped in `tuya-local`. `tuya_ble` supports other Parkside devices (such as smart batteries `z5ztlw3k` and `ajrhf1aj`) and other irrigation computers (`6pahkcau`, `hfgdqhho`), but lacks `PBB-A1` specific BLE mapping. |
| **Ailrinni Fingerprint Door Lock** | Supported via Bluetooth hub | **Not Supported** | Lock supported via gateway in `tuya-local`. Not in `devices.py` of `tuya_ble`. |
| **Arlec Smart Button & USB Strip** | Supported via Bluetooth hub | **Not Supported** | Mapped in `tuya-local` as a subdevice. Not in `tuya_ble`. |
| **BSTUOKEY Invisible Lock** | Supported via Bluetooth hub | **Not Supported** | Supported in `tuya-local`. Missing in `tuya_ble`. |
| **Diivoo DWV010, WT05 Timers** | Supported via Bluetooth hub | **Not Supported** | Dual water timers supported via gateway in `tuya-local`. `tuya_ble` supports other Diivoo timers but doesn't have explicit BLE definitions for `DWV010` and `WT05`. |
| **Dituo DT-T2190A Aroma Diffuser**| Supported via Bluetooth hub | **Not Supported** | Supported in `tuya-local`. `tuya_ble` does not support any Tuya BLE aroma diffusers. |
| **Gainsborough Liberty Lock** | Supported via Bluetooth hub | **Not Supported** | Lock supported in `tuya-local`. Missing in `tuya_ble`. |
| **HCT-611 & HCT-626 Timers** | Supported via Bluetooth hub | **Not Supported** | Single and dual water timers. Supported in `tuya-local`, missing in `tuya_ble`. |
| **HU06 Smart Lock** | Supported via Bluetooth hub | **Not Supported** | Supported in `tuya-local`. Missing in `tuya_ble`. |
| **imitOS Square Downlight** | Supported via Bluetooth hub | **Not Supported** | Supported in `tuya-local`. Missing in `tuya_ble`. |
| **Ironzon / KB150A / Nice Digi Locks**| Supported via Bluetooth hub | **Not Supported** | Various BLE secure locks supported via gateway in `tuya-local`. Missing in `tuya_ble`. |
| **MoistenLand Water Timer** | Supported via Bluetooth hub | **Not Supported** | Supported in `tuya-local`. Missing in `tuya_ble`. |
| **O'TU R1O1 / Primebras / YSG Locks** | Supported via Bluetooth hub | **Not Supported** | Secure locks supported via gateway in `tuya-local`. Missing in `tuya_ble`. |
| **Smart Ape Solar Garden Light** | Supported via Bluetooth hub | **Not Supported** | Supported in `tuya-local`. Missing in `tuya_ble`. |
| **SOP10 Water Sprinkler** | Supported via Bluetooth hub | **Not Supported** | Supported in `tuya-local`. Missing in `tuya_ble`. |
| **TH05 & THB2 Temperature Sensors** | Supported via Bluetooth hub | **Not Supported** | Supported in `tuya-local`. While `tuya_ble` has many temperature sensors, these specific models are not in `devices.py`. |
| **Unistyle WT-04W Water Timer** | Supported via Bluetooth hub | **Not Supported** | Supported in `tuya-local`. Missing in `tuya_ble`. |
| **XCase NX-4964 Lock Box** | Supported via Bluetooth hub | **Not Supported** | Supported in `tuya-local`. Missing in `tuya_ble`. |
| **YL01 Water Quality Tester** | Supported via Bluetooth hub | **Not Supported** | Supported in `tuya-local`. Missing in `tuya_ble`. |

---

## 3. Review of Tuya Protocol Versions & Architecture for Bluetooth

### 3.1 Proxy Gateway Architecture
In `make-all/tuya-local`, Bluetooth support is implemented through a local LAN-to-BLE proxy architecture:
1. **Physical Link**: The BLE sub-device (e.g. a water timer or lock) connects via Bluetooth Low Energy directly to a nearby physical **Tuya WiFi/Bluetooth multi-mode Gateway**.
2. **Local TCP/IP**: The Home Assistant host running `tuya-local` connects to the Gateway's local IP address over WiFi/Ethernet on TCP port `6668`.
3. **Encrypted Payload**: The TCP packets are encrypted using the Gateway's `local_key`.
4. **Addressing Sub-devices**: Because multiple BLE sub-devices are connected to a single gateway, `tuya-local` targets a specific sub-device by including a `cid` (sub-device / node ID) field in the TCP command payload.
5. **Command Forwarding**: The Gateway decrypts the LAN payload, extracts the Data Point (DP) command, and relays it locally over Bluetooth to the sub-device.
6. **Status Report**: When a sub-device state changes, it broadcasts over Bluetooth to the Gateway, which then forwards the state update over TCP back to Home Assistant.

### 3.2 Supported Protocol Versions
The local Tuya LAN protocol versions supported by `tuya-local` (via `tinytuya`) include:
- **`3.1` and `3.2`**: Used by older WiFi devices and early hubs.
- **`3.3`**: The most common protocol version for standard multi-mode gateways and sub-devices.
- **`3.4`**: Used by newer secure gateways (utilizes enhanced session-based security, requiring a handshake exchange before payload transmission).
- **`3.5`**: The latest local protocol version, featuring heavier payload encryption and improved handshake patterns.
- **`3.22`**: A special protocol designation used in `tuya-local` to force `tinytuya`'s "device22" auto-detection mode over version `3.3` (preventing misdetection issues).

---

## 4. Comparison of Direct BLE vs. Gateway Architectures

| Comparison Metric | Direct BLE (`tuya_ble`) | Gateway Proxy (`tuya-local`) |
| :--- | :--- | :--- |
| **Hardware Required** | HA Host Bluetooth (USB, built-in, or ESP32 Proxies) | Physical Tuya Bluetooth/WiFi Gateway / Hub |
| **Range & Coverage** | Limited by host Bluetooth range (mitigated by ESPHome Proxies) | Flexible; gateway can be placed anywhere on local WiFi near devices |
| **Local Protocol** | Direct BLE GATT service/characteristic read/writes | Encrypted LAN TCP/IP packets (Protocol 3.1 - 3.5) |
| **Secure Lock Control** | **Fully Local Unlock**: Directly handles anti-replay key exchange locally. | **Lock-only / Cloud-required**: Cannot handle lock pairing/key-exchange natively over TCP; requires Tuya Cloud or pre-sniffed keys. |
| **Power Consumption** | Extremely optimized for battery-powered Bluetooth sensors. | Relies on gateway to manage battery wake-ups. |
| **Local Responsiveness**| Very fast direct connection. | Double-hop latency (HA host -> Gateway -> BLE subdevice). |
