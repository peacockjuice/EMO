---
title: "Build your EMO"
tags: [emo, setup, hardware]
---

# Build your EMO

This guide follows the tested ESP32-S2 build on macOS. It separates a new device from an existing device with the Wi-Fi updater installed.

## What you need

| Part or tool | Tested setup |
|---|---|
| Board | LILYGO ESP32-S2 WOOR V1.1; 4 MB flash |
| Display | SSD1306 I²C OLED; 128 × 64 pixels |
| Connections | Breadboard and jumper wires; secure header contacts |
| Power and first install | USB power and a USB data cable |
| Computer | macOS, Python 3, Git, Node.js 22.18 or later |
| BB | BB 0.49 or later, with the `bb` command available |
| Network | A trusted 2.4 GHz Wi-Fi network |
| Board software | MicroPython 1.29.0 for ESP32-S2 |

Other boards and host platforms need their own checks. The USB tools use POSIX serial interfaces. The build has no speaker or audio output.

## Get the project

Clone the repository, then run commands from its root directory:

```sh
git clone https://github.com/peacockjuice/EMO.git
cd EMO
```

Generated frames and the web panel are included. You do not need Pillow or CairoSVG to install the existing build. Those tools are for changing the artwork.

## Wire the display

Disconnect power before wiring. Use the pin labels on the board.

| Board pin | Display pin |
|---|---|
| 3.3 V | VDD |
| GND | GND |
| GPIO9 | SCK / SCL |
| GPIO8 | SDA |

Leave the board's 5 V pin disconnected from the OLED. The tested display is mounted upside down; `FLIP = True` in `bmo.py` accounts for this.

The [hardware notes](../handoff/hardware.md) show the tested board's switch positions and connector orientation. Breadboard hole numbers apply only to that recorded layout.

## Install a new device

These steps are for a board that does not yet have the EMO updater. To update a working EMO, use [the existing-device procedure](#update-an-existing-device).

1. Install ESP32-S2 MicroPython using the [official board instructions](https://micropython.org/download/ESP32_GENERIC_S2/). The tested version is 1.29.0. On the WOOR board, automatic boot entry can fail; use the board-specific [hardware notes](../handoff/hardware.md). Flash erasure removes any existing device files and credentials.
2. Find the current serial port. On macOS, list `/dev/cu.*` and identify the connected board. Use that path wherever `PORT` appears below. Close other programs that use the port.
3. Copy `ap_cfg.example.py` to the ignored file `ap_cfg.py`. Set an access-point name and a unique password of at least eight characters. The installer copies this file when the board has no access-point configuration.
4. Use your MicroPython editor to create `wifi_cfg.py` directly on the board. Define `SSID` and `PASSWORD` for your 2.4 GHz network. Keep this file on the board. Without it, EMO starts its fallback access point instead of joining your network.
5. Close the editor's serial connection. Run the one-time installer with the current port:

```sh
python3 tools/bootstrap_wifi.py PORT
```

The installer writes the complete application and updater. It creates an update key on the Mac and board, then resets the board. It refuses a board with an existing updater.

Keep the Mac key at `~/.config/emo/update.key` private and backed up securely. Losing it requires deliberate USB recovery. Never add device credentials or keys to Git.

After startup, the OLED briefly shows the network address. Open that address in a browser. Check that the panel loads and the display renders faces. EMO then starts in BB mode. Until BB connects, it shows the existing waiting and connection-warning sequence.

## Connect BB

Follow the [plugin installation guide](../bb-plugin-emo/README.md#install-and-update). It covers dependency installation, local checks, plugin installation, and key provisioning.

Set the robot address in the plugin. Select the projects you want EMO to follow in the EMO sidebar page. Then run:

```sh
bb emo status
```

Wait for `sourceReady: true` and `delivery: live`. The robot's `/state` response should show `mood: bb` and `bb: live`.

The panel can select another mode at any time. Notifications do not override that manual choice. A restart selects BB again.

## Update an existing device

Use the same Mac key that provisioned the device. Replace `DEVICE_IP` with the address shown by your robot. The panel uses port 80; the updater uses port 8080.

1. Keep the robot powered. Note its current mode and inversion setting.
2. Stop the sender with `bb plugin disable emo`. Choose **auto** in the robot's web panel.
3. Read the signed update status. Resolve an existing pending update before uploading another one.

```sh
python3 tools/wifi_update.py status --url http://DEVICE_IP:8080
python3 tools/wifi_update.py upload --url http://DEVICE_IP:8080
```

4. Wait for the client to report a confirmed healthy release. After a timeout, read `status` before taking another action. A timeout does not prove success or rollback.
5. Check that the robot started in BB mode. Enable the sender with `bb plugin enable emo`. Restore your inversion setting, then check `bb emo status`.

Use complete bundles for application updates. Partial USB writes can invalidate an installed slot. The [updater guide](../handoff/wifi-updates.md) covers pending updates, rollback, and USB recovery.

## Make it yours

The web panel selects faces, scenes, **auto**, and **demo**. The EMO sidebar page selects BB projects and excludes individual sessions.

To change frame artwork or firmware, use the [development guide](../handoff/development.md). To return to the product overview, open the [README](../README.md).

## Dependencies

| Document | Purpose |
|---|---|
| [Hardware notes](../handoff/hardware.md) | Exact tested wiring, board switches, and recovery constraints |
| [Plugin guide](../bb-plugin-emo/README.md) | BB installation, configuration, and runtime rules |
| [Wi-Fi updates](../handoff/wifi-updates.md) | Full-bundle installation and recovery |
