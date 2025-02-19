# Home Assistant support for Tuya BLE devices

## Overview

This integration supports Tuya devices connected via BLE.

## Installation

Place the `custom_components` folder in your configuration directory (or add its contents to an existing `custom_components` folder). Alternatively install via [HACS](https://hacs.xyz/).

## Usage

After adding to Home Assistant integration should discover all supported Bluetooth devices, or you can add discoverable devices manually.

## Supported devices list

* Fingerbots (category_id 'szjqr')
  + Fingerbot (product_ids 'ltak7e1p', 'y6kttvd6', 'yrnk7mnn', 'nvr2rocq', 'bnt7wajf', 'rvdceqjh', '5xhbk964')
  + Adaprox Fingerbot (product_id 'y6kttvd6')
  + Fingerbot Plus (product_ids 'blliqpsj', 'ndvkgsrm', 'yiihr7zh', 'neq16kgd')
  + CubeTouch 1s (product_id '3yqdo5yt')
  + CubeTouch II (product_id 'xhf790if')

* Small Home Appliances (category_id 'cl')
  + Bluetooth Rope Motor (product_id '4pbr8eig')

* Temperature and humidity sensors (category_id 'wsdcg')
  + Soil moisture sensor (product_id 'ojzlzzsw').

* CO2 sensors (category_id 'co2bj')
  + CO2 Detector (product_id '59s19z5m').

* Smart Locks (category_id 'ms')
  + Smart Lock (product_id 'ludzroix', 'isk2p555').

* Climate (category_id 'wk')
  + Thermostatic Radiator Valve (product_ids 'drlajpqc', 'nhj2j7su').

* Smart water bottle (category_id 'znhsb')
  + Smart water bottle (product_id 'cdlandip')

* Irrigation computer (category_id 'ggq')
  + Irrigation computer (product_id '6pahkcau')
  + Irrigation computer (product_id 'hfgdqhho')

* Water valve controller (category_id 'sfkzq')
  + Water valve controller (product_id 'nxquc5lb')

* Lights
  + Most light products should be supported as the Light class tries to get device description from the cloud when there are added but only Strip Lights (category_id 'dd') Magiacous RGB light bar (product_id 'nvfrtxlq') has has been tested