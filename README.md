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

## Supported devices list

<table>
  <thead>
    <tr>
      <th>Category</th>
      <th>Category ID</th>
      <th>Device / Model</th>
      <th>Product ID</th>
      <th>Notes</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td rowspan="8"><strong>Fingerbots</strong></td>
      <td rowspan="8"><code>szjqr</code></td>
      <td>Fingerbot</td>
      <td><code>ltak7e1p</code>, <code>y6kttvd6</code>, <code>yrnk7mnn</code>, <code>nvr2rocq</code>, <code>bnt7wajf</code>, <code>rvdceqjh</code>, <code>5xhbk964</code></td>
      <td>Original device, first in category, powered by CR2 battery.</td>
    </tr>
    <tr>
      <td>Adaprox Fingerbot</td>
      <td><code>y6kttvd6</code></td>
      <td>Built-in battery with USB type C charging.</td>
    </tr>
    <tr>
      <td>Fingerbot Plus</td>
      <td><code>blliqpsj</code>, <code>ndvkgsrm</code>, <code>yiihr7zh</code>, <code>neq16kgd</code>, <code>mknd4lci</code>, <code>riecov42</code>, <code>bs3ubslo</code>, <code>6jcvqwh0</code>, <code>h8kdwywx</code></td>
      <td>Almost same as original, has sensor button for manual control. See programming note below.</td>
    </tr>
    <tr>
      <td>CubeTouch 1s</td>
      <td><code>3yqdo5yt</code></td>
      <td>Built-in battery with USB type C charging.</td>
    </tr>
    <tr>
      <td>CubeTouch II</td>
      <td><code>xhf790if</code></td>
      <td>Built-in battery with USB type C charging.</td>
    </tr>
    <tr>
      <td>Tuya BLE Switch Robot (SB02)</td>
      <td><code>4ctjfrzq</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>Tuya BLE Fingerbot SM-FB-01B</td>
      <td><code>gnpbj0bq</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>Nedis SmartLife Finger Robot</td>
      <td><code>yn4x5fa7</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td rowspan="6"><strong>Temperature and humidity sensors</strong></td>
      <td rowspan="6"><code>wsdcg</code>, <code>zwjcy</code></td>
      <td>Soil moisture sensor</td>
      <td><code>ojzlzzsw</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>SRB-PM01 Soil Moisture Sensor</td>
      <td><code>jabotj1z</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>Temperature Humidity Sensor</td>
      <td><code>jm6iasmb</code>, <code>tr0kabuq</code>, <code>iv7hudlj</code>, <code>vlzqwckk</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>Temperature Humidity Sensor SS302</td>
      <td><code>6lbesej0</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>TH05 Temperature Sensor</td>
      <td><code>vyfoip9h</code>, <code>1jvidcsf</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>Soil Thermo-Hygrometer</td>
      <td><code>tv6peegl</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td><strong>CO2 sensors</strong></td>
      <td><code>co2bj</code></td>
      <td>CO2 Detector</td>
      <td><code>59s19z5m</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td rowspan="20"><strong>Smart Locks</strong></td>
      <td rowspan="20"><code>ms</code>, <code>jtmspro</code></td>
      <td>Smart Lock</td>
      <td><code>ludzroix</code>, <code>isk2p555</code>, <code>gumrixyt</code>, <code>uamrw6h3</code>, <code>sidhzylo</code>, <code>mqc2hevy</code>, <code>7a4xvbtt</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>Primebras Athenas Lock</td>
      <td><code>6fibxtph</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>Foxgard Smart Fingerprint Door Lock</td>
      <td><code>99gv5nmz</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>HU06 Smart Lock</td>
      <td><code>stugc8dl</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>Raybuke K7 Pro+</td>
      <td><code>xicdxood</code></td>
      <td>Supports BLE unlock and other small features.</td>
    </tr>
    <tr>
      <td>Fingerprint Smart Lock</td>
      <td><code>k53ok3u9</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>T55D</td>
      <td><code>bvclwu9b</code></td>
      <td>Battery &amp; Door status.</td>
    </tr>
    <tr>
      <td>Gimdow A1 Pro Max</td>
      <td><code>rlyxv7pe</code></td>
      <td>Experimental.</td>
    </tr>
    <tr>
      <td>A1 Ultra-JM</td>
      <td><code>hc7n0urm</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>LA-01 Smart lock</td>
      <td><code>oyqux5vv</code></td>
      <td>Experimental.</td>
    </tr>
    <tr>
      <td>B16</td>
      <td><code>ajk32biq</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>CS-9 Smart Fingerprint Lock</td>
      <td><code>pyawczjj</code></td>
      <td>Experimental.</td>
    </tr>
    <tr>
      <td>Smart Cylinder Lock</td>
      <td><code>z7lj676i</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>TEKXDD Fingerprint Smart Lock</td>
      <td><code>okkyfgfs</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>Orion Smart Door Handle Lock</td>
      <td><code>a6nttc41</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>Smart Cylinder Lock (LVD11_BK)</td>
      <td><code>hs21i377</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>Smart Lock</td>
      <td><code>kholoaew</code></td>
      <td>Partial.</td>
    </tr>
    <tr>
      <td>CentralAcesso</td>
      <td><code>ebd5e0uauqx0vfsp</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>Gainsborough Liberty BLE Lock (GGC01HA)</td>
      <td><code>yfqp0shy</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>BSTUOKEY Invisible Lock</td>
      <td><code>kpn4zaf7</code></td>
      <td>Invisible induction lock.</td>
    </tr>
    <tr>
      <td><strong>Climate</strong></td>
      <td><code>wk</code></td>
      <td>Thermostatic Radiator Valve</td>
      <td><code>drlajpqc</code>, <code>nhj2j7su</code>, <code>zmachryv</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td><strong>Smart water bottle</strong></td>
      <td><code>znhsb</code></td>
      <td>Smart water bottle</td>
      <td><code>cdlandip</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td rowspan="3"><strong>Irrigation computer</strong></td>
      <td rowspan="3"><code>ggq</code>, <code>slj</code></td>
      <td>Irrigation computer</td>
      <td><code>6pahkcau</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>2-outlet irrigation computer</td>
      <td><code>hfgdqhho</code>, <code>fnlw6npo</code>, <code>qycalacn</code>, <code>jjqi2syk</code></td>
      <td>Also known as: SGW02, SGW08, MOES BWV-YC02-EU-GY, Kogan SmarterHome KASMWATMRDA / KASMWTV2LVA.</td>
    </tr>
    <tr>
      <td>RESTMO BT Water Meter (FML026A)</td>
      <td><code>mqqna0px</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td rowspan="6"><strong>Covers</strong></td>
      <td rowspan="6"><code>cl</code></td>
      <td>Moes Roller Blind Motor</td>
      <td><code>4pbr8eig</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>Amazon HeyBlinds</td>
      <td><code>vlwf3ud6</code>, <code>v3fzfd2y</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>Tuya Smart Curtain Robot</td>
      <td><code>kcy0x4pi</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>Blinds Drive</td>
      <td><code>qqdxfdht</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>LY Curtain Motor Robot</td>
      <td><code>ulughw4g</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>AOK AM24 Venetian Blinds Motor</td>
      <td><code>dy4dh1q0</code></td>
      <td>Experimental.</td>
    </tr>
    <tr>
      <td rowspan="6"><strong>Water valve controller</strong></td>
      <td rowspan="6"><code>sfkzq</code></td>
      <td>Water valve controller</td>
      <td><code>nxquc5lb</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>NOUS L11 Bluetooth Smart Garden Water Timer</td>
      <td><code>46zia2nz</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>WT-03W Diivoo Smart Water Timer for Garden Hose</td>
      <td><code>1fcnd8xk</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>ZX-7378 Smart Irrigation Controller</td>
      <td><code>ldcdnigc</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>Rainpoint TTV102B</td>
      <td><code>e1poaiwa</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>Valve controller</td>
      <td><code>svhikeyq</code>, <code>0axr5s0b</code>, <code>d4vpmigg</code></td>
      <td>Also known as YZD05 water valve/irrigation timer.</td>
    </tr>
    <tr>
      <td rowspan="4"><strong>Lights</strong></td>
      <td rowspan="4">Multiple (e.g. <code>dd</code> for Strip Lights)</td>
      <td>Strip Lights / Magiacous RGB light bar</td>
      <td><code>nvfrtxlq</code></td>
      <td rowspan="4">Most BLE light products should be supported as the Light class tries to get device description from the cloud when they are added. But only Strip Lights (category_id 'dd') Magiacous RGB light bar (product_id 'nvfrtxlq') has been tested.<br><br>See note on Bluetooth Mesh light compatibility below.</td>
    </tr>
    <tr>
      <td>Magiacous Floor Lamp</td>
      <td><code>umzu0c2y</code></td>
    </tr>
    <tr>
      <td>Comfamoli Sunset Lamp</td>
      <td><code>6jxcdae1</code></td>
    </tr>
    <tr>
      <td>RGB Strip Light</td>
      <td><code>0qgrjxum</code></td>
    </tr>
    <tr>
      <td><strong>Wireless switches</strong></td>
      <td><code>wxkg</code></td>
      <td>Arlec Smart Button</td>
      <td><code>kpzc6pm8</code>, <code>ja5osu5g</code></td>
      <td>Single/Double click and Long press support via events.</td>
    </tr>
    <tr>
      <td rowspan="2"><strong>Battery</strong></td>
      <td rowspan="2"><code>dcb</code></td>
      <td>Parkside Performance Smart Battery 4Ah</td>
      <td><code>z5ztlw3k</code></td>
      <td>—</td>
    </tr>
    <tr>
      <td>Parkside Performance Smart Battery 8Ah</td>
      <td><code>ajrhf1aj</code></td>
      <td>—</td>
    </tr>
  </tbody>
</table>

### Fingerbots Programming Note
All features available in Home Assistant, programming (series of actions) is implemented for Fingerbot Plus.
For programming exposed entities: 'Program' (switch), 'Repeat forever', 'Repeats count', 'Idle position' and 'Program' (text). Format of program text is: `position[/time];...` where position is in percents, optional time is in seconds (zero if missing).

### Lights Compatibility Note
Note that some light products are using Bluetooth Mesh protocols and not BLE and so aren't compatible with this integration. That's probably the case if your product isn't at least found (even if non-working) by this integration.

## Note that the original hasn't been updated in a long time, still, Support original developer @PlusPlus-ua:

I am working on this integration in Ukraine. Our country was subjected to brutal aggression by Russia. The war still continues. The capital of Ukraine - Kyiv, where I live, and many other cities and villages are constantly under threat of rocket attacks. Our air defense forces are doing wonders, but they also need support. So if you want to help the development of this integration, donate some money and I will spend it to support our air defense.
<br><br>
<p align="center">
  <a href="https://www.buymeacoffee.com/3PaK6lXr4l"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy me an air defense"></a>
</p>
