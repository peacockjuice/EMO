---
title: "Handoff: BMO robot face on ESP32-S2 (2026-11-14)"
tags: [bmo, esp32, oled, micropython]
---

# Handoff: BMO robot face on ESP32-S2 (2026-11-14)

The user is building a small robot with an animated BMO face on an OLED, driven by an
ESP32-S2 board running MicroPython and controlled from a web page. The full Figma face set is deployed; verification details are recorded below. The user writes in Russian; reply in Russian.

Source threads: `thr_idubxh5c6k` (first attempt, wiring research) and `thr_psix2q4mn2`
(initial firmware), and `thr_rxakmvqqxy` (Figma adaptation and full gallery). Read them with `bb thread log <id> --all` only if a detail here is not enough.

## Where things are

Project folder (durable copy, the source of truth on the Mac):
`/Users/vpavlin/.bb/thread-storage/thr_psix2q4mn2/bmo/`

| Path | What it is |
|---|---|
| `main.py` | Two lines: `import bmo; bmo.run()` |
| `bmo.py` | Wi-Fi bring-up, asyncio web server, emotion loop. Read this first. |
| `emotions.py` | Streams one animation frame into the OLED buffer, including auto and aliases |
| `emotion_sequences.py` | Generated timelines for `rosto01`…`rosto30`, look, wink, sleep and three speech styles |
| `emotions.bin` | 104 unique SSD1306 frames, 106,496 bytes; kept in flash |
| `face.py` | Legacy renderer retained for rollback; no longer imported by runtime |
| `assets/figma/` | Original 30 SVGs and source board PNG |
| `tools/build_faces.py` | SVG monochrome adaptation and static board |
| `tools/face_layout.py` | Shared fixed per-face scaling, including animation frames |
| `tools/build_animations.py` | Three approved reference animation samples |
| `tools/build_all.py` | Full animation bank, timelines, thumbnails and GIFs |
| `tools/index.template.html` | Editable control-page template |
| `tools/build_web.py` | Generates index.html with 30 embedded thumbnails |
| `tools/upload_release.py` | Stages specified files, checks SHA256, activates, resets |
| `tools/run_full_test.py` | Fresh raw-REPL test run with full cycles and HTTP polling |
| `tools/check_web.mjs` | Handler tests using a DOM model, optionally real device HTTP |
| `preview/` | Boards, GIFs, manifests and test evidence |
| `backups/` | Original firmware files and pre-release snapshots |
| `index.html` | The control page served by the board |
| `ssd1306.py` | Unmodified micropython-lib driver |
| `tools/mp.py` | Minimal raw-REPL client: upload files, run code on the board |
| `tools/ser.py` | Reset the board and print 3 s of serial output |
| `tools/enter_boot.py` | Puts the chip into ROM download mode for esptool |
| `tools/selftest.py` | Legacy test; use `tools/run_full_test.py` for current runtime |
| `tools/shot.py` | Legacy renderer preview; new runtime uses the verified frame bank |
| `firmware/` | MicroPython 1.29.0 image for ESP32_GENERIC_S2 and the board schematic PDF |

Only runtime files are deployed: main.py, bmo.py, ssd1306.py, emotions.py, emotion_sequences.py, emotions.bin and index.html, plus board-only wifi_cfg.py. Earlier sample/legacy files may remain but are not imported.

A working copy with a Python venv (esptool 5.6.0, mpremote 1.29.0) is in
`/private/tmp/claude-501/esp/`. It is a temp directory and may be gone. To recreate:
`python3 -m venv venv && PIP_USE_DEPRECATED=legacy-certs ./venv/bin/pip install esptool mpremote`
(the env var is needed inside the Bash sandbox, where pip's default certificate check fails).
`mp.py` and `ser.py` use only the standard library, so they run with any python3.

## Hardware

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

## How to work with the board

Serial access needs an approved sandbox escalation; otherwise `/dev/cu.*` returns
"Operation not permitted". Local-network HTTP currently works with `--noproxy '*'`.
Use `rtk` for shell commands. Run the following from the project folder.

```sh
rtk proxy python3 tools/upload_release.py /dev/cu.usbserial-210 emotions.bin emotion_sequences.py emotions.py index.html bmo.py
rtk proxy python3 tools/run_full_test.py /dev/cu.usbserial-210
rtk proxy env BMO_TEST_URL=http://192.168.1.43 node tools/check_web.mjs
```

- The uploader verifies staged `.new` files before activation; bmo.py must be last.
  Activation is sequential, not an atomic multi-file transaction. Always preserve a backup.
- The uploader and full-test runner reset in `finally`. With raw `mp.py` commands,
  always finish with `tools/ser.py`; otherwise animations stay stopped at the REPL.
- Ctrl-C does not reliably release the old HTTP socket. The full-test runner performs
  a soft reset in raw REPL before starting its server; this avoids `EADDRINUSE`.
- Buffer SHA256 confirms data transfer, not physical OLED visibility. User photos are
  the evidence for physical readability; local PNG/GIFs show generated pixel data.
- Reflash from scratch: `enter_boot.py`, then
  `esptool --chip esp32s2 --port $P --baud 460800 --before no-reset --after hard-reset write-flash --erase-all 0x1000 firmware/ESP32_GENERIC_S2-20260824-v1.29.0.bin`,
  then upload all files again. This also erases `wifi_cfg.py`.

## How the software works

`bmo.py` runs one asyncio loop with two parts:

- **Web server** on port 80. `GET /` serves `index.html`; `GET /set?e=<mood>` switches the
  emotion and returns `{"ok":..., "mood":...}`; `GET /state` returns the current one.
  Any program on the network can drive the face through `/set`.
- **Emotion loop** (`animate`). `S["mood"]` selects a function from `MOODS`;
  `S["ver"]` changes on every command. `emotions.play()` reads each 1024-byte frame
  directly into `oled.buffer`, then yields in at most 40 ms slices. Transfer time counts
  toward frame duration. A changed version interrupts the sequence and closes its file.

Canonical faces are `rosto01` through `rosto30`. Extra modes: `auto`, `look`, `wink`,
`sleep`, `talk_calm`, `talk_fast`, `talk_excited`. Auto alternates the smile with a random face from the full set.
Old keys remain aliases: smile→01, happy/talk→02, love→21, wow→13, sad→03.
Sample aliases remain valid too. The web page exposes 33 numbered cards, a separate seven-card speech section and auto,
uses embedded PNG thumbnails, serializes selection requests and displays connection errors.
An unconfirmed selection is retained for manual retry; the latest selection wins.
After an error, automatic polling pauses until retry or a new selection. The status says
"Выбрано", because the API confirms selection rather than physical OLED visibility.

## Behaviour update (2026-11-15)

The grid now contains the original 30 faces plus look (31), wink (32), sleep (33).
Auto is separate; all speech variants live under the "Разговор" heading. Card count is generated from the
catalog. Rosto08 moves only its pupils within the fixed eyelids. Sleep builds up three
Z glyphs above the right eye. talk_excited is now angry speech based on rosto07;
its API name is retained for compatibility.

The USB port changed from usbserial-110 to usbserial-210. If it changes again, inspect
/dev/cu.* instead of assuming the old name. tools/check_behaviour_update.py compares
unaffected timelines by frame content (indices can change when the bank is rebuilt),
and checks pupil-only motion, Z progression and the extra catalog entries.
Device regression: tools/run_behaviour_test.py; evidence: preview/behaviour-board.log.

## Speech variants

The panel adds "Рассказывает" (`talk_calm`), "Болтает" (`talk_fast`) and
"Сердится и говорит" (`talk_excited`, preserved API name). The first two use the enlarged smile; the third uses
the angry rosto07 face with fixed eyebrows. Five mouth poses form different phrase rhythms and pauses.
The existing `talk` alias still selects rosto02. Extra speech modes are selected manually;
auto still chooses among the 30 original faces. Build definitions live in tools/build_all.py.
Run tools/check_speech.py locally and tools/run_speech_test.py on the board.
The local check covers every pixel outside the mouth and active-pose/pause timing.
Unchanged animations are checked against the most recent change baseline by tools/check_behaviour_update.py. The latter
checks completed cycles with inversion off/on, concurrent HTTP, mode switches and aliases.
Preview GIFs: preview/talk_calm.gif, preview/talk_fast.gif, preview/talk_excited.gif.

## Repeated-syllable modes

The "Разговор" section uses the same visual card grid as the emotion list.
Its PNG thumbnails are generated from actual OLED frames by tools/build_web.py;
selection highlighting and inversion are shared with emotion cards.
The "Разговор" section contains the three existing speech styles plus "Бобобо"
(talk_bobo), "Бебебе" (talk_bebe), "Бабаба" (talk_baba) and "Бибиби" (talk_bibi).
These are mouth animations, with lip closure followed by distinct round, wide, open
and narrow vowel shapes. Each mode continuously repeats a two-frame closure/vowel loop with no rest pause until another mode is selected. No audio is generated.
The 33-card emotion grid remains separate. Tests: tools/check_syllables.py and
 tools/run_syllables_test.py; evidence: preview/syllables-board.log.

## OLED inversion

The web panel has an "Инвертировать цвета экрана" checkbox. `/invert?value=1` enables
native SSD1306 inversion; value=0 disables it. `/state`, `/set` and `/invert` return
an `invert` boolean alongside the selected mood. Commands set an explicit value, so
retrying is safe. Inversion does not restart the animation or change the mood. It is
reapplied when the display reconnects, and resets to false on board reboot.
Thumbnails reflect the confirmed inversion state. Failed requests retain their desired
value for manual retry. Tests: tools/check_invert.py and tools/check_web.mjs.

## Rebuild and verify

Use the project `.venv` (Pillow/CairoSVG, pinned in tools/requirements-faces.txt).
macOS Cairo is installed under /opt/homebrew/lib. No conversion libraries run on ESP32.

```sh
rtk proxy env DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib .venv/bin/python tools/build_faces.py
rtk proxy .venv/bin/python tools/build_animations.py
rtk proxy .venv/bin/python tools/build_all.py
rtk proxy python3 tools/build_web.py
rtk proxy python3 tools/check_faces.py
rtk proxy .venv/bin/python tools/check_layout.py
rtk proxy python3 tools/check_full.py
rtk proxy node tools/check_web.mjs
```

Source SVGs stay unchanged. The converter preserves mask/clip coverage, uses cheek
hatching and outlined tears, and keeps large eye highlights light. Sparse faces are
scaled up using a fixed transform shared across their entire animation; dense faces
retain their size. The user approved this size on a physical-screen photo.
Edit timelines/effects in tools/build_all.py; edit page layout in tools/index.template.html.
Regenerate artifacts, run checks, then upload using the explicit release command above.

## Rollback

The original working renderer and page are in `backups/before-figma/`.
To restore that version without erasing flash or touching wifi_cfg.py:

```sh
rtk proxy python3 tools/mp.py /dev/cu.usbserial-210 put backups/before-figma/face.py backups/before-figma/index.html backups/before-figma/bmo.py
rtk proxy python3 tools/ser.py /dev/cu.usbserial-210
```

Restore is manual; run ser.py even if the upload fails. Extra animation-bank files can
remain unused. The board firmware image and Wi-Fi settings do not need to change.

### Wi-Fi

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

## State at handoff

- User approved static adaptation, sample animation timing and enlargement of sparse faces.
- Full 30-face bank and new web gallery are deployed at http://192.168.1.43/.
- Local checks cover exact static starting poses, valid frame offsets, all 30 animated,
  compatibility aliases, stable mouth during blinking and layout margins.
- Deployment verifies SHA256 of every runtime file. Served HTML was byte-for-byte
  identical to index.html and contained all 30 catalog entries.
- Full device regression before the speech additions PASSED: every face and behaviour completed a cycle with
  concurrent HTTP polling; aliases, auto, rapid switching and invalid commands passed.
  Final free heap in the instrumented test was 57,520 bytes.
  The test waits for each completed cycle and logs/retries external selections.
  Results: preview/full-board.log and preview/web-tests.json. Speech additions use
  preview/speech-board.log. Current changes are checked by tools/check_behaviour_update.py
  against backups/before-behaviour-update, excluding the three deliberately changed timelines.
- Browser visual QA is unavailable because the computer-use browser host did not connect.
  The JavaScript handler test uses a DOM model, not a real browser or CSS renderer.
- Background-signal control (presence, weather, touch, agent events) remains outside scope.

## Constraints to respect

- The original firmware had about 73 KB free RAM. Consult preview/full-board.log for
  current memory with the full set and active server. Keep new features small; poll at most
  one or two internet sources, and prefer computing on the Mac and pushing a mood via `/set`.
- The previous firmware on the board (`esp32-csi-node` 0.6.4) was erased with the user's
  consent and without a backup; it cannot be restored from here.
- Flashing or erasing the board destroys `wifi_cfg.py`; confirm with the user first.

## Suggested skills

- `ponytail` — the user had it active in the first thread; keep solutions minimal.
- `superpowers:brainstorming` — before designing the "emotions from background signals" feature.
- `superpowers:systematic-debugging` or `mattpocock-skills:diagnosing-bugs` — for any
  "board not visible" / "screen is dark" problem; start from the traps list above.
- `superpowers:verification-before-completion` — check on the board (serial log, `/state`,
  rendered frames) before saying something works; the agent cannot see the physical screen.
- `bb-global-skills:secrets` — if Wi-Fi or API credentials have to be supplied again.
