# Contributing Guide

Thank you for your interest in contributing!  
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

