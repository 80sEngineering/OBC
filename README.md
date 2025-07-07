# 80s Engineering - Open Source OBC v2.0

This repository contains the open source firmware for **80s Engineering's On-Board Computer (OBC) v2.0**, which is a modern take on the original on-board computer found in premium BMWs
of the late 80s. 

It replicates most of the original functions and adds performance-oriented features, while maintaining its retro aesthetics.

![OBC Device](https://cdn.shopify.com/s/files/1/0904/5812/8763/files/OBCv2_front_render.png?v=1741215667)

The firmware is written in **MicroPython** and runs on a **Raspberry Pi Pico W**. 

This project is also a great base for **custom applications**, as the device offers multiple accessible **Input/Output Digital/Analog pins** for sensors, switches, or other hardware extensions.

It's mainly for this matter that this firmware is open-sourced.

---

## 🛠️ Hardware Overview
![Hardware Description](https://cdn.shopify.com/s/files/1/0904/5812/8763/files/Hardware_description.jpg?v=1751542300)

### Open I/O Pins
Below is a list and description of accessible pins on the top of the OBC v2.0

| Pin| Label         | Function / Description              |Pinout|
|----|---------------|-------------------------------------|-|
| P1 | GND           | Ground                              |GND |
| P2 | IO            | Custom digital 3.3V input/output    |Connected to GPIO 26 |
| P3 | SDA           | I2C data line                       |Connected to GPIO 2|
| P4 | SCL           | I2C clock line                      |Connected to GPIO 3|
| P5 | AIN1          | 0-5V Analog input                   |Connected to ADC's channel 5|
| P6 | AIN2          | 0-12V Analog input                  |Connected to ADC's channel 6 |
| P7 | AIN3          | 0-5V Analog input. Pulled up to 5V with 4.7kOhm|Connected to ADC's channel 7 |
| P8 | 12V           | Permanent 12V                       |12V|
| P9 | 5V            | Commuted 5V                         |5V |
| P10 | 3.3V         | Commuted 3.3V                       |RPi's 3.3VOUT| 



---

## 📁 File Structure

| File         | Description                                                                 |
|--------------|-----------------------------------------------------------------------------|
| `main.py`    | Main program. Core logic of the OBC. Handles system's functions (menu navigation, on/off...), application functions (hour, laptimer, oil pressure...), and setting functions.|
| `FOTA directory`  |Backend of the Firmware-Over-The-Air (wireless update) system|
| `buttons.py` | Handles press/long-press button detection, and debouncing|
| `dictionnary.py` |Stores all the displayed words and translations          |
| `fota-master.py`|Wireless update handler|
| `GPS_parser.py`| Parses GPS data               |
| `hardware_tester.py`   |Used to test components after board assembly|
| `ht16k33_driver.py`   |Display driver|
| `imu.py`   |Accelerometer driver|
| `injector_pulse_analyzer.py`   |Wild shit to analyze frequency and width of injector pulses|
| `logging.py`   |Used to log events for debug purposes|
| `mcp3208.py`   |Analog-to-digital converter driver|
| `memory.py`   |Used to get and set data in the non-volatile memory of the RPi|
| `temperatuy.py`   |Driver for oil/out/water/exhaust temperature sensors|
| `timer.py`   |Timer and laptimer handler|
| `unit.py`   |Handles the mess of imperial units|
| `vector3d.py`   |Dependency for the imu driver. Probably useless|
---

Some files contains derivatives of libraries found online.

## 🔧 Modify or Extend the Firmware

If you'd like to customize the OBC with new features, integrations, or improvements:

- feel free to reach me out at 📧 **contact@80s.engineering**.
- you can reprogram the OBC's board using Thonny IDE and a microUSB connected to the Raspberry Pi Pico W.
- I can release your changes so that you can wirelessly update them on your unit. 

I'd be happy to review your changes and merge improvements into the official release.

---
Do not hesitate to follow me on Instagram for more:  
**[@80s.engineering](https://instagram.com/80s.engineering)**

Thank you for your interest in the OBC project!