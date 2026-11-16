---
title: "EMO: hardware, network and recovery"
tags: [emo, esp32, oled, handoff]
---

# EMO: hardware, network and recovery

- Board: LILYGO ESP32-S2 WOOR V1.1 (ESP32-S2-WROOM, 4 MB flash, no PSRAM, **no Bluetooth**).
  Schematic: `firmware/SchematicV1_1.pdf`. USB goes through a CH340C bridge.
- Last working Mac serial port: `/dev/cu.usbserial-10` (previously -210, then -110). On 2026-11-16 the user disconnected the robot from the Mac. Re-discover /dev/cu.* after reconnecting; do not assume that a remembered port exists.
- Display: GM009605 OLED, SSD1306, 128x64, I2C address found by scan (0x3C/0x3D).
  Display pins left to right: GND, VDD, SCK, SDA.
- Board sits with USB at row 1; board pin rows are in breadboard columns b and i. The table below applies to that exact orientation.

| Breadboard hole | Board pin | Wire colour | OLED pin | Purpose |
|---|---|---|---|---|
| j1 | V3V (3.3 V) | Blue | VDD | Display power |
| j3 | GND | Green | GND | Common ground |
| j12 | IO9 / GPIO9 | Crimson | SCK | I2C clock (SCL) |
| j13 | IO8 / GPIO8 | Grey | SDA | I2C data |
| j2 | +5 V | None | Not connected | Keep empty for the OLED |

Pin labels are authoritative; breadboard hole numbers are valid only if the board has not moved. Firmware agrees: SDA=8, SCL=9. Do not interpret the board drawing without checking which side it shows.

- The display is mounted **upside down** in the robot. Code handles it with `FLIP = True`
  in `bmo.py` (`oled.rotate(not FLIP)`). Draw in normal coordinates.

### Hardware traps already hit (do not rediscover)

1. **DIP switches.** The block nearest the USB-C connector selects the USB path:
   1 ON, 2 OFF, 3 ON, 4 OFF = CH340 bridge (current, correct). All four ON makes the board
   invisible to the Mac. The other block only switches the 32 kHz crystal vs IO15/IO16.
2. **Pin map is drawn from the back of the board.** Looking at the component side, left and
   right are swapped. A mirrored display wiring earlier collapsed the 3.3 V rail, which made
   the board vanish from USB. Symptom of that: Mac sees the port powered, no USB device.
3. **Header pins are not soldered.** Contact through the breadboard is intermittent. The
   code reconnects to the display on `OSError`. Any new sensor on wires will be flaky until
   the headers are soldered.
4. **esptool auto-reset does not work on this board** (EN rises slowly). Run
   `tools/enter_boot.py <port>` first, then esptool with `--before no-reset`.
   Manual fallback: hold BOT, tap RST, release BOT.
5. **mpremote cannot enter the raw REPL** here (it resets the board on open). Use `tools/mp.py`.


## Network and credentials


- `net_up()` imports `wifi_cfg.py` from the board (`SSID`, `PASSWORD`) and joins the home
  network. If that fails within 15 s, or the file is missing, it starts its own access
  point. The deployed working copy has AP_NAME/AP_PASS in bmo.py; the sanitized Git copy imports them from private ignored ap_cfg.py
  (address `192.168.4.1`).
- Currently on the home network at `http://192.168.1.43/`, also `http://bmo.local/`
  (first request to `.local` from the Mac takes about 5 s; the IP is instant, but may change).
- `wifi_cfg.py` exists **only on the board**. The user asked for the Mac copy to be deleted.
  Do not copy it back to the Mac or print it. If credentials are needed again, ask the user
  to supply them through a file (or the `bb-global-skills:secrets` skill), not in chat.
- The board supports 2.4 GHz only.
- On boot the screen shows the network name and address for 5 s, then the face.


## Firmware and recovery constraints

MicroPython 1.29.0, ESP32_GENERIC_S2. Image and schematic are under `../firmware/`.
The previous esp32-csi-node 0.6.4 firmware was erased with explicit user consent, without a backup; it cannot be restored here.
Do not erase/reflash for normal updates. Erasing destroys board-only wifi_cfg.py and requires fresh user confirmation.
Use tools/enter_boot.py before esptool with --before no-reset when recovery actually requires flashing.
The current UI name is EMO; firmware filenames, AP constants and hostname bmo.local remain unchanged. Do not mass-rename them as an unfinished task.
The old /private/tmp/claude-501/esp environment is disposable and may no longer exist. tools/mp.py and tools/ser.py use standard-library Python.
The physical wiring and readability were checked in earlier work, not re-measured during this documentation handoff.

## Audio investigation: not connected

User has a small dynamic speaker from a toy, marked TL 5 / 4414230000198, wired to its toy board by two yellow wires. The toy sounds when its white button is pressed. Battery compartment says 3× LR44/AG13, 1.5 V each (nominal 4.5 V in series). Speaker impedance and power are unknown. The user has no multimeter, soldering iron, resistors, capacitors or amplifier and declined an amplifier module. No speaker wiring or sound firmware has been implemented; do not assume either yellow wire is ground.

Do not connect this unknown low-impedance speaker directly to GPIO or power. Software off buttons cannot limit instantaneous current. A resistor-limited quiet-beep experiment was discussed (330 Ω or a larger value), but no resistor is available and no pin was selected. Toy-button emulation also remains unverified: supply voltage does not establish button voltage or polarity. No other peripherals are confirmed connected.

## Current power and connectivity

The robot is unplugged from the Mac but responds over Wi-Fi as of the latest network check. Its present external power source was not identified; do not assume a battery or a particular adapter. USB was previously both power and serial. Wi-Fi currently supports control only, not firmware/file upload. A future Wi-Fi updater or notification receiver needs initial installation over USB. No flash erase is required for those normal file updates.
