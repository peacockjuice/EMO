---
title: "EMO: hardware, network and recovery"
tags: [emo, esp32, oled, handoff]
---

# EMO: hardware, network and recovery

- Board: LILYGO ESP32-S2 WOOR V1.1 (ESP32-S2-WROOM, 4 MB flash, no PSRAM, **no Bluetooth**).
  Schematic: `firmware/SchematicV1_1.pdf`. USB goes through a CH340C bridge.
- Mac serial port: `/dev/cu.usbserial-210` (name can change with the USB port used).
- Display: GM009605 OLED, SSD1306, 128x64, I2C address found by scan (0x3C/0x3D).
  Display pins left to right: GND, VDD, SCK, SDA.
- Wiring (breadboard hole → board pin → wire colour):
  j1 → V3V (3.3 V) → blue (VDD); j3 → GND → green; j12 → IO9 → crimson (SCK);
  j13 → IO8 → grey (SDA). j2 is +5 V, keep it empty.
  Board sits with the USB connector at row 1, pins in columns b and i.
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
  point; the name and password are the `AP_NAME`/`AP_PASS` constants in `bmo.py`
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
