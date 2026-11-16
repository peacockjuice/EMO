---
title: "EMO: build, deployment and verification"
tags: [emo, esp32, oled, handoff]
---

# EMO: build, deployment and verification

Work from `/Users/vpavlin/.bb/thread-storage/thr_psix2q4mn2/bmo`. Prefix shell commands with `rtk` per `/Users/vpavlin/.codex/RTK.md`.

## Source map and runtime

- `main.py` imports bmo and calls run; `bmo.py` owns network setup, display connection, HTTP and asyncio animation loop.
- `emotions.py` streams one 1024-byte frame into the existing OLED buffer; transfer counts toward duration. It yields in at most 40 ms slices, detects S.ver changes and closes the bank on cancellation.
- `emotion_sequences.py` and `emotions.bin` are generated matching timelines/frame bank. Do not mix revisions.
- `tools/build_faces.py` adapts 30 original SVGs; source art in assets/figma stays unchanged. Masks/clips are preserved, cheeks hatched, highlights light, tears outlined.
- `tools/face_layout.py` computes a fixed reference-face transform shared across all animation frames: target at most 104×50, scale at most 1.65, enlarge only at least 1.08. This enlarged 23 sparse faces without per-frame jitter.
- `tools/build_animations.py` makes approved blink/talk/cry samples used as build inputs. samples.py is not imported by runtime.
- `tools/build_all.py` builds 40 timelines, deduplicated bank, 33-face catalog and animation previews.
- `tools/index.template.html` is the editable UI source; `tools/build_web.py` generates index.html and seven speech thumbnails directly from actual bank frames, using stdlib PNG encoding.
- `ssd1306.py` is the unchanged driver. `face.py` is the legacy renderer, retained for rollback only.
- Runtime deployment: main.py, bmo.py, behaviour.py, showcase.py, ssd1306.py, emotions.py, emotion_sequences.py, emotions.bin, index.html. wifi_cfg.py lives only on the board. Older sample files on the board are unused.

## Character development

behaviour.py owns mood rules and six scenes. emotions.py installs their modes into the existing executor. build_web.py derives six thumbnails from the scene definitions. Bank bytes and indices are unchanged. Run tools/check_character.py, tools/check_character_runtime.py, tools/check_invert.py and tools/check_web.mjs. Hardware runner: tools/run_character_test.py PORT defaults to a short scenes-only test (about two minutes). It checks actual displayed frame hashes in order in both inversion states. Explicit --mode soak or --mode full enables the deferred 30-minute soak. Do not click modes during a run. Logs/results are separate by mode; the runner resets and restores prior mood/inversion afterward (a scene restarts). The physical display appearance still needs user observation.

## Panel palette

Warm beige/brown CSS tokens live in tools/index.template.html (:root). Keep monochrome thumbnail pixels faithful to OLED output; inversion still uses invert(1). The palette update changes only the page, so deploy index.html alone. Backup: backups/before-warm-palette.

## Build

Project .venv has Pillow/CairoSVG pinned in tools/requirements-faces.txt; native Cairo is under /opt/homebrew/lib. Conversion runs on the Mac, never on the board.

```sh
rtk proxy env DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib .venv/bin/python tools/build_faces.py
rtk proxy .venv/bin/python tools/build_animations.py
rtk proxy .venv/bin/python tools/build_all.py
rtk proxy python3 tools/build_web.py
```

For HTML-only changes run only build_web.py. Timeline-only changes can leave the bank unchanged; compare hashes. If indices or frame content change, upload both bank and timelines.

## Local checks

```sh
rtk proxy python3 tools/check_faces.py
rtk proxy .venv/bin/python tools/check_layout.py
rtk proxy python3 tools/check_full.py
rtk proxy python3 tools/check_speech.py
rtk proxy python3 tools/check_syllables.py
rtk proxy python3 tools/check_behaviour_update.py
rtk proxy python3 tools/check_invert.py
rtk proxy node tools/check_web.mjs
```

check_faces checks review IDs and bank correspondence; check_layout checks fixed transforms and stable mouth during blinking; check_full checks 30 original animations, exact first poses, offsets, aliases and catalog. Speech checks compare every pixel outside the mouth and active-pose/pause timing. Behaviour checks compare frame content, not unstable deduplicated indices, against backups/before-behaviour-update except intentional changes; they check pupil-only motion and progressive Zs. Syllable checks use backups/before-syllables and verify four distinct vowel loops. Preserve these backup fixtures.
check_invert covers explicit idempotent values, unchanged mood/version and failed-driver state. check_web uses Node VM and a mock DOM: card counts, distinct thumbnails, exclusive selection, latest-wins request serialization and retries. It is NOT browser rendering or visual QA.

## Deploy and device regression

The board now has an A/B updater. Use the [Wi-Fi update procedure](./wifi-updates.md). The partial USB commands below are historical and must not be applied to an OTA slot without rebuilding its manifest and journal.

Read /state before resetting, then restore the user's mood/invert afterward. Verify the current USB path; it changed from -110 to -210. Serial access must be available to the current process; do not interpret a permission failure as a broken board.

```sh
rtk proxy python3 tools/upload_release.py /dev/cu.usbserial-210 emotions.bin emotion_sequences.py emotions.py index.html bmo.py
rtk proxy python3 tools/run_full_test.py /dev/cu.usbserial-210
rtk proxy env BMO_TEST_URL=http://192.168.1.43 node tools/check_web.mjs
```

Upload only changed files (HTML-only: index.html). Uploader refuses wifi_cfg.py, stages .new files in chunks, verifies SHA256, then renames sequentially and resets in finally. This is NOT atomic multi-file activation. Keep bmo.py last and preserve a matching backup.
Raw tools/mp.py interrupts the program: always finish with tools/ser.py, including after an error. Ctrl-C may leave an HTTP socket bound; test runners soft-reset in raw REPL to prevent EADDRINUSE and cached-module tests.
Scoped runners: run_speech_test.py, run_behaviour_test.py, run_syllables_test.py. They complete cycles with normal/inverted display, HTTP polling and switches. Full run takes roughly two minutes. Do not run device tests simultaneously or click modes during them; external selection can interfere. Runners log/retry external mode changes a bounded number of times.
check_web with BMO_TEST_URL drives the real device and ends auto/inversion off: restore prior state. Local HTTP works with curl --noproxy '*'.

## Evidence and limits

- preview/full-board.log is the successful full regression BEFORE later speech additions. Do not claim it tests the entire latest release.
- preview/speech-board.log, behaviour-board.log and syllables-board.log cover subsequent scopes. Latest syllable loop run completed at least 16 cycles per new mode across both inversion states; final free heap was 57,424 bytes.
- preview/*-tests.json and review JSON record individual stages; timestamps and scope matter. Some review reports are historical resolved findings.
- preview/full-manifest.json, catalog.json, speech-cards.json describe generated assets. Current bank has 104 frames / 106,496 bytes; 33 emotion thumbnails and seven speech thumbnails.
- preview/comparison.png, detail before/after images, rostoXX.gif, look/wink/sleep.gif and talk_*.gif show generated pixel data. Some comparison images are earlier layout stages.
- Device buffer hashes and driver show calls prove transfer/execution, not optical visibility. User photographs validated the enlargement on the physical display.
- Real-browser QA was unavailable: computer-use browser host failed to connect. Mock DOM tests do not prove CSS/layout appearance.
- preview/handoff-snapshot.json records current local hashes and live HTML equality. It does not re-read every runtime file on the board or rerun the hardware suite.

## Rollback

Snapshots: backups/before-figma, before-enlargement, before-full-set, before-inversion, before-speech, before-behaviour-update, before-syllables. Choose a consistent set. Original working renderer rollback:

```sh
rtk proxy python3 tools/mp.py /dev/cu.usbserial-210 put backups/before-figma/face.py backups/before-figma/index.html backups/before-figma/bmo.py
rtk proxy python3 tools/ser.py /dev/cu.usbserial-210
```

Reset even on upload failure. Extra unused banks may remain. No erase or Wi-Fi rewrite is needed. The pre-consolidation handoff is archived at backups/handoff-before-consolidation.md and is historical, not current guidance.
