# Home Assistant support for Tuya BLE devices

## Overview

This integration supports Tuya devices connected via BLE.

_Inspired by code of [@redphx](https://github.com/redphx/poc-tuya-ble-fingerbot)_

## Installation

Place the `custom_components` folder in your configuration directory (or add its contents to an existing `custom_components` folder). Alternatively install via [HACS](https://hacs.xyz/).

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=markusg1234&repository=ha_tuya_ble&category=integration)

## Usage

After adding to Home Assistant integration should discover all supported Bluetooth devices, or you can add discoverable devices manually.

The integration works locally, but connection to Tuya BLE device requires device ID and encryption key from Tuya IOT cloud. It could be obtained using the same credentials as in the previous official Tuya integration. To obtain the credentials, please refer to official Tuya integration [documentation](https://web.archive.org/web/20231228044831/https://www.home-assistant.io/integrations/tuya/) [[1]](https://github.com/home-assistant/home-assistant.io/blob/a4e6d4819f1db584cc66ba2082508d3978f83f7e/source/_integrations/tuya.markdown)

## Supported devices list

- Fingerbots (category_id 'szjqr')

  - Fingerbot (product_ids 'ltak7e1p', 'y6kttvd6', 'yrnk7mnn', 'nvr2rocq', 'bnt7wajf', 'rvdceqjh', '5xhbk964'), original device, first in category, powered by CR2 battery.
  - Adaprox Fingerbot (product_id 'y6kttvd6'), built-in battery with USB type C charging.
  - Fingerbot Plus (product_ids 'blliqpsj', 'ndvkgsrm', 'yiihr7zh', 'neq16kgd'), almost same as original, has sensor button for manual control.
  - CubeTouch 1s (product_id '3yqdo5yt'), built-in battery with USB type C charging.
  - CubeTouch II (product_id 'xhf790if'), built-in battery with USB type C charging.

  All features available in Home Assistant, programming (series of actions) is implemented for Fingerbot Plus.
  For programming exposed entities 'Program' (switch), 'Repeat forever', 'Repeats count', 'Idle position' and 'Program' (text). Format of program text is: 'position\[/time\];...' where position is in percents, optional time is in seconds (zero if missing).

- Temperature and humidity sensors (category_id 'wsdcg')

  - Soil moisture sensor (product_id 'ojzlzzsw').

- Temperature and humidity sensors (category_id 'zwjcy')

  - Smartlife Plant Sensor SGS01 (product_id 'gvygg3m8').

- CO2 sensors (category_id 'co2bj')

  - CO2 Detector (product_id '59s19z5m').

- Smart Locks (category_id 'ms')

  - Smart Lock (product_id 'ludzroix', 'isk2p555').

- Climate (category_id 'wk')

  - Thermostatic Radiator Valve (product_ids 'llflaywg').

- Smart water bottle (category_id 'znhsb')

  - Smart water bottle (product_id 'cdlandip')

- Irrigation computer (category_id 'ggq')
  - Irrigation computer (product_id '6pahkcau')
  - 2-outlet irrigation computer SGW02 (product_id 'hfgdqhho'), also known as MOES BWV-YC02-EU-GY

## Support project

I am working on this integration in Ukraine. Our country was subjected to brutal aggression by Russia. The war still continues. The capital of Ukraine - Kyiv, where I live, and many other cities and villages are constantly under threat of rocket attacks. Our air defense forces are doing wonders, but they also need support. So if you want to help the development of this integration, donate some money and I will spend it to support our air defense.
<br><br>

<p align="center">
  <a href="https://www.buymeacoffee.com/3PaK6lXr4l"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy me an air defense"></a>
</p>
