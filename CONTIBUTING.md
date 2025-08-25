# Contributing Guide

I have a new device that isn't supported.

I have a similar device to one that is already supported.

## Vibe Coding Your Robotic Lawnmower

What could go wrong?

This guide explains how to generate a new PR for a set of **DPIDs** (Device Property IDs) using **Google Jules (Web UI)**, and how to collect the DPIDs from [Tuya IoT](https://iot.tuya.com).

---

## 1. Prerequisites

- Access to [Tuya IoT Platform](https://iot.tuya.com/) with a developer account.  
- Access to **Google Jules** in your browser (with permissions to create PRs on this repo).

---

## 2. Getting DPIDs from Tuya IoT

1. **Log in** to [Tuya IoT](https://iot.tuya.com/).  
2. Go to **Cloud → Development → Devices**.  
3. Select the device you want to support or update.  
4. Open the **Functions (DP)** tab.  
5. Copy the list of **DPIDs** and their descriptions:  

   Example:
   ```text
   DPID 1 → Switch (Boolean)
   DPID 2 → Brightness (Integer, 0–1000)
   DPID 3 → Mode (Enum: white, colour, scene)
```
6. Whangjangle this into google jules:

```
Add support for Example Product - SmartLife Finger Robot (category: szjqr - Product ID: yn4x5fa7)

{ "result": { "category": "szjqr", "functions": [ { "code": "switch", "dp_id": 1, "type": "Boolean", "values": "{}" }, { "code": "mode", "dp_id": 2, "type": "Enum", "values": "{"range":["click"]}" }, { "code": "click_sustain_time", "dp_id": 3, "type": "Integer", "values": "{"unit":"0.1s","min":3,"max":100,"scale":1,"step":1}" }
```

