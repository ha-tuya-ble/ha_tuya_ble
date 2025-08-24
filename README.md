# Home Assistant support for Tuya BLE devices

## Overview

This integration is an almalgamation of a number of community maintained forks. It should be considered **unstable** quality at this time.

See full list of forks:
https://github.com/ha-tuya-ble/ha_tuya_ble/issues/1


_Inspired by code of [@redphx](https://github.com/redphx/poc-tuya-ble-fingerbot) & forked from https://github.com/PlusPlus-ua/ha_tuya_ble_ 

_Original HASS component forked from https://github.com/PlusPlus-ua/ha_tuya_ble_

_This forks base is from https://github.com/markusg1234/ha_tuya_ble_


## Installation

Place the `custom_components` folder in your configuration directory (or add its contents to an existing `custom_components` folder). Alternatively install via [HACS](https://hacs.xyz/).

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ha-tuya-ble&repository=ha_tuya_ble&category=integration)

## Usage

After adding to Home Assistant integration should discover all supported Bluetooth devices, or you can add discoverable devices manually.

The integration works locally, but connection to Tuya BLE device requires device ID and encryption key from Tuya IOT cloud. It could be obtained using the same credentials as in the previous official Tuya integration. To obtain the credentials, please refer to official Tuya integration [documentation](https://web.archive.org/web/20231228044831/https://www.home-assistant.io/integrations/tuya/) [[1]](https://github.com/home-assistant/home-assistant.io/blob/a4e6d4819f1db584cc66ba2082508d3978f83f7e/source/_integrations/tuya.markdown)

## Supported devices list (not up to date)

* Fingerbots (category_id 'szjqr')
  + Fingerbot (product_ids 'ltak7e1p', 'y6kttvd6', 'yrnk7mnn', 'nvr2rocq', 'bnt7wajf', 'rvdceqjh', '5xhbk964'), original device, first in category, powered by CR2 battery.
  + Adaprox Fingerbot (product_id 'y6kttvd6'), built-in battery with USB type C charging.
  + Fingerbot Plus (product_ids 'blliqpsj', 'ndvkgsrm', 'yiihr7zh', 'neq16kgd', 'mknd4lci', 'riecov42', 'bs3ubslo'), almost same as original, has sensor button for manual control.
  + CubeTouch 1s (product_id '3yqdo5yt'), built-in battery with USB type C charging.
  + CubeTouch II (product_id 'xhf790if'), built-in battery with USB type C charging.

  All features available in Home Assistant, programming (series of actions) is implemented for Fingerbot Plus.
  For programming exposed entities 'Program' (switch), 'Repeat forever', 'Repeats count', 'Idle position' and 'Program' (text). Format of program text is: 'position\[/time\];...' where position is in percents, optional time is in seconds (zero if missing).

* Temperature and humidity sensors (category_id 'wsdcg')
  + Soil moisture sensor (product_id 'ojzlzzsw').
  + Bluetooth Temperature Humidity Sensor (product_id 'jm6iasmb')

* CO2 sensors (category_id 'co2bj')
  + CO2 Detector (product_id '59s19z5m').

* Smart Locks (category_id 'ms', 'jtmspro')
  + Smart Lock (product_id 'ludzroix', 'isk2p555', 'gumrixyt').
  + Raybuke K7 Pro+ (product_id 'xicdxood'), supports ble unlock and other small features.
  + Fingerprint Smart Lock (product_id 'k53ok3u9')

* Climate (category_id 'wk')
  + Thermostatic Radiator Valve (product_ids 'drlajpqc', 'nhj2j7su').

* Smart water bottle (category_id 'znhsb')
  + Smart water bottle (product_id 'cdlandip')

* Irrigation computer (category_id 'ggq')
  + Irrigation computer (product_id '6pahkcau')
  + 2-outlet irrigation computer (product_ids 'hfgdqhho', 'fnlw6npo', 'qycalacn', 'jjqi2syk')
    - also known as: SGW02, SGW08, MOES BWV-YC02-EU-GY, Kogan SmarterHome KASMWATMRDA / KASMWTV2LVA


* Covers (category_id 'cl')
  + Moes Roller Blind Motor (product_id '4pbr8eig')

* Water valve controller (category_id 'sfkzq')
  + Water valve controller (product_id 'nxquc5lb')
  + NOUS L11 Bluetooth Smart Garden Water Timer (product_id '46zia2nz')
  + WT-03W Diivoo Smart Water Timer for Garden Hose (product_id '1fcnd8xk')
  
  
* Lights
  + Most BLE light products should be supported as the Light class tries to get device description from the cloud when there are added but only Strip Lights (category_id 'dd') Magiacous RGB light bar (product_id 'nvfrtxlq') has has been tested
    
    *Note that some light products are using Bluetooth Mesh protocols and not BLE and so aren't compatible with this integration. That's probably the case if your product isn't at least found (even if non-working) by this integration*


* Battery (category_id 'dcb')
  + Parkside Performace Smart Battery 4Ah (product_id 'z5ztlw3k')
  + Parkside Performace Smart Battery 8Ah (product_id 'ajrhf1aj')

## Note that the original hasn't been updated in a long time, still, Support original developer @PlusPlus-ua:

I am working on this integration in Ukraine. Our country was subjected to brutal aggression by Russia. The war still continues. The capital of Ukraine - Kyiv, where I live, and many other cities and villages are constantly under threat of rocket attacks. Our air defense forces are doing wonders, but they also need support. So if you want to help the development of this integration, donate some money and I will spend it to support our air defense.
<br><br>
<p align="center">
  <a href="https://www.buymeacoffee.com/3PaK6lXr4l"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy me an air defense"></a>
</p>
