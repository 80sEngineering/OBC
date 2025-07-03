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
Below is a list of accessible pins on the top of the Raspberry Pi Pico used in the OBC, along with their default roles:

| Pin| Label         | Function / Description              |
|----|---------------|-------------------------------------|
| P1 | GND           | Ground                              |
| P2 | IO            | Custom digital 3.3V input/output    |
| P3 | SDA           | I2C data line                       |
| P4 | SCL           | I2C clock line                      |
| P5 | ANALOG_IN     | Analog sensor input (0-3.3V)        |
| P6 | I2C_SCL       | I2C clock line                      |
| P7 | I2C_SDA       | I2C data line                       |
| P8 | I2C_SDA       | I2C data line                       |
| P9 | I2C_SDA       | I2C data line                       |
| P10 | I2C_SDA      | I2C data line                      |

![Pinout Diagram](insert-your-pinout-image-url-here)

---

## 📁 File Structure

| File         | Description                                                                 |
|--------------|-----------------------------------------------------------------------------|
| `main.py`    | Core logic of the OBC. Handles menu navigation, display rendering, timers, and sensor logic. Fully commented. |
| `config.py`  | Central configuration file. Set default values, language options, hardware settings. |
| `sensors.py` | Interfaces for temperature, GPS, pressure, voltage sensors, etc.           |
| `display.py` | UI drawing functions and font rendering on the OBC screen.                 |
| `utils.py`   | Helper functions (math, string formatting, conversions, etc.)              |
| `wifi.py`    | Handles OTA update support and basic WiFi communication.                   |
| `debug.py`   | Debugging and serial output utilities for development purposes.            |

---

## 🔧 Modify or Extend the Firmware

If you'd like to customize the OBC with new features, integrations, or improvements:

- All core logic is in `main.py`, and is clearly commented.
- Feel free to fork the repo and start experimenting.
- If you'd like your contribution included in future firmware updates, reach out to me at:

📧 **contact@80s.engineering**

I'd be happy to review your changes and merge improvements into the official release.

---

## 📷 More

For build logs, product images, and community projects using the OBC, follow me on Instagram:  
**[@80s.engineering](https://instagram.com/80s.engineering)**

---

Thank you for your interest in the OBC project!
