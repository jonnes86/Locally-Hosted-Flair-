# CC1101 Wiring Guide for ESP32 DevKit

This guide explains how to connect an ESP32 DevKit to a TI CC1101 915 MHz RF Transceiver Module.

## Pin Mapping

| ESP32 Pin | CC1101 Pin | Function  |
|-----------|------------|-----------|
| GPIO 23   | MOSI       | SPI Data In |
| GPIO 19   | MISO       | SPI Data Out|
| GPIO 18   | SCK        | SPI Clock   |
| GPIO 5    | CSN/CS     | Chip Select |
| GPIO 22   | GDO0       | Digital Out 0 (Interrupt/Rx) |
| GPIO 21   | GDO2       | Digital Out 2 (Optional)     |
| 3.3V      | VCC        | Power (DO NOT CONNECT TO 5V) |
| GND       | GND        | Ground      |

> **WARNING**: The CC1101 is a 3.3V logic device. **DO NOT** connect VCC to 5V.

## Wiring Diagram

```text
    ESP32 DevKit                  CC1101 Module
  +----------------+           +------------------+
  |           3.3V |---------->| VCC              |
  |            GND |---------->| GND              |
  |                |           |                  |
  |        GPIO 23 |---------->| MOSI             |
  |        GPIO 19 |<----------| MISO             |
  |        GPIO 18 |---------->| SCK              |
  |        GPIO  5 |---------->| CSN              |
  |                |           |                  |
  |        GPIO 22 |<----------| GDO0             |
  |        GPIO 21 |<----------| GDO2             |
  +----------------+           +------------------+
```

## Hardware Requirements

If you need to purchase components, here are suggested Amazon search terms:

*   **ESP32**: `"ESP32 DevKit V1"` or `"ESP-WROOM-32 development board"`
*   **CC1101**: `"CC1101 wireless module 433 868 915"` (Make sure it has a coiled antenna or an SMA antenna connector)
*   **Jumper Wires**: `"Female to Female jumper wires dupont"`

## Module Appearance
The CC1101 modules usually come in a small rectangular blue or green PCB. They typically have 8 or 10 pins lined up on one edge and a large metal shield covering the main IC. Ensure you buy the module tuned for the 915 MHz frequency band if you are operating in the US (or compatible regions). 
