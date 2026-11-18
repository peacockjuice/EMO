---
title: "EMO: build, deployment and verification"
tags: [emo, esp32, oled, handoff]
---

# EMO: build, deployment and verification

Work from `/Users/vpavlin/projects/EMO`. The older thread-storage copy is a historical snapshot. Prefix shell commands with `rtk` per `/Users/vpavlin/.codex/RTK.md`.

## Source map and runtime

- Root `main.py` starts the OTA supervisor, which selects and starts the application; `bmo.py` owns network setup, display connection, HTTP and asyncio animation loop. See the Wi-Fi updater guide before deployment.
- `emotions.py` streams one 1024-byte frame into the existing OLED buffer; transfer counts toward duration. It yields in at most 40 ms slices, detects S.ver changes and closes the bank on cancellation.
- `emotion_sequences.py` and `emotions.bin` are generated matching timelines/frame bank. Do not mix revisions.
- `tools/build_faces.py` adapts 30 original SVGs; source art in assets/figma stays unchanged. Masks/clips are preserved, cheeks hatched, highlights light, tears outlined.
- `tools/face_layout.py` computes a fixed reference-face transform shared across all animation frames: target at most 104×50, scale at most 1.65, enlarge only at least 1.08. This enlarged 23 sparse faces without per-frame jitter.
- `tools/build_animations.py` makes approved blink/talk/cry samples used as build inputs. samples.py is not imported by runtime.
- `tools/build_all.py` builds 40 timelines, the 104-frame deduplicated bank, 33-face catalog and animation previews. The obsolete compact BB generator/module and 18-frame tail are removed. `tools/check_assets.py` checks active bytes, indices, timings, aliases, scenes and demo against a frozen fixture from 1d180f6; `tools/check_full.py` rejects a legacy tail/module in the current package.
- `tools/index.template.html` is the editable UI source; `tools/build_web.py` generates index.html and seven speech thumbnails directly from actual bank frames, using stdlib PNG encoding.
- `emo_bb.py` owns snapshot state, `emo_bb_http.py` handles signed requests and `emo_bb_view.py` owns face/speech/text phases and warning cadence; `emo_bb_display.py` owns the display loop, counters and scaled text. Load scene, font and renderer separately with GC between them after preparing HTTP. The cycle reuses already-loaded emotion_sequences.py and the original full-size frames, without a shift or header during faces; the enlarged counters appear only during the text phase. Keep these compilation units separate: importing the former monolithic module exhausted native Wi-Fi memory on ESP32-S2; `emo_font.py` contains an original Cyrillic font, and `emo_http.py` bounds HTTP headers with one deadline and reads sockets in 128-byte chunks, preserving buffered body bytes. Run tools/check_bb.py and bb-plugin-emo npm check/test/build after relevant changes.
- `ssd1306.py` is the unchanged driver. `face.py` is the legacy renderer, retained for rollback only.
- Application deployment uses the complete bundle selected by the Wi-Fi updater client, including the BB modules and font. Root main.py/supervisor and board-only wifi_cfg.py are outside normal application updates. Older sample files on the board are unused.

## Character development

behaviour.py owns mood rules and six scenes. emotions.py installs their modes into the existing executor. build_web.py derives six thumbnails from the scene definitions. Bank bytes and indices are unchanged. Run tools/check_character.py, tools/check_character_runtime.py, tools/check_invert.py and tools/check_web.mjs. Hardware runner: tools/run_character_test.py PORT defaults to a short scenes-only test (about two minutes). It checks actual displayed frame hashes in order in both inversion states. Explicit --mode soak or --mode full enables the deferred 30-minute soak. Do not click modes during a run. Logs/results are separate by mode; the runner resets and restores prior mood/inversion afterward (a scene restarts). The physical display appearance still needs user observation.

## Panel palette

Warm beige/brown CSS tokens live in tools/index.template.html (:root). Keep monochrome thumbnail pixels faithful to OLED output; inversion still uses invert(1). A page-only edit needs only build_web.py locally, but the installed OTA updater still requires a complete application bundle. Backup: backups/before-warm-palette.

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

For release labels, startup fallback and the frozen measurement inventory, run `rtk proxy python3 tools/check_release.py`. The 0.3 installation and checks are recorded under [release evidence](../preview/release-0.3/checks.json). A source test does not prove optical OLED acceptance.

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

The board now has an A/B updater. Use the [Wi-Fi update procedure](./wifi-updates.md). Do not use partial USB writes inside an OTA slot: they invalidate the manifest. For BB-specific startup and memory failures, follow the [diagnostic guide](./bb-troubleshooting.md).

Read /state before resetting, then restore the user's mood/invert afterward. Verify the current USB path. The latest connected path is /dev/cu.usbserial-110 (2026-11-17); always enumerate it again. Serial access must be available to the current process; do not interpret a permission failure as a broken board.

```sh
rtk proxy python3 tools/run_full_test.py PORT
rtk proxy env BMO_TEST_URL=http://192.168.1.43 node tools/check_web.mjs
```

Historical pre-OTA behaviour: upload only changed files (HTML-only: index.html). The legacy uploader refuses wifi_cfg.py, stages .new files in chunks, verifies SHA256, then renames sequentially and resets in finally. This is NOT atomic multi-file activation. It now refuses partial updates when OTA is installed; use the full-bundle Wi-Fi path instead.
Raw tools/mp.py interrupts the program: always finish with tools/ser.py, including after an error. Ctrl-C may leave an HTTP socket bound; test runners soft-reset in raw REPL to prevent EADDRINUSE and cached-module tests.
Scoped runners: run_speech_test.py, run_behaviour_test.py, run_syllables_test.py. They complete cycles with normal/inverted display, HTTP polling and switches. Full run takes roughly two minutes. Do not run device tests simultaneously or click modes during them; external selection can interfere. Runners log/retry external mode changes a bounded number of times.
check_web with BMO_TEST_URL drives the real device and ends auto/inversion off: restore prior state. Local HTTP works with curl --noproxy '*'.

## Evidence and limits

- `tools/check_bb_memory_board.py PORT` measures Python and native heap around each BB import, then resets into the normal app. It interrupts the runtime; stop the sender first and restore BB mode afterward. It reads no Wi-Fi configuration or keys. `preview/bb-memory-diagnosis.json` records the monolithic import exhausting the main native pool; `preview/bb-memory-after.json` records the split modules preserving it.
- `tools/check_bb_live.py` checks complete HTML equality alongside live BB delivery and frame/sequence progress. Run with the plugin enabled and BB mode already live; the result is saved to `preview/bb-acceptance.json`.

- preview/full-board.log is the successful full regression BEFORE later speech additions. Do not claim it tests the entire latest release.
- preview/speech-board.log, behaviour-board.log and syllables-board.log cover subsequent scopes. Latest syllable loop run completed at least 16 cycles per new mode across both inversion states; final free heap was 57,424 bytes.
- preview/*-tests.json and review JSON record individual stages; timestamps and scope matter. Some review reports are historical resolved findings.
- preview/full-manifest.json, catalog.json, speech-cards.json describe generated assets. Current bank has 104 frames / 106,496 bytes (all active offsets remain intact); 33 emotion thumbnails and seven speech thumbnails.
- preview/comparison.png, detail before/after images, rostoXX.gif, look/wink/sleep.gif and talk_*.gif show generated pixel data. Some comparison images are earlier layout stages.
- Device buffer hashes and driver show calls prove transfer/execution, not optical visibility. User photographs validated the enlargement on the physical display.
- Real-browser QA was unavailable: computer-use browser host failed to connect. Mock DOM tests do not prove CSS/layout appearance.
- preview/handoff-snapshot.json records current local hashes and live HTML equality. It does not re-read every runtime file on the board or rerun the hardware suite.

## Small plugin simplification (2026-11-18)

The panel now reuses model.counts, and urgent-ring rotation is inline at its single call site. Firmware is unchanged. Baseline, fixed source inventory, before/after measurements and verification limits are recorded separately.
Source: [Plugin simplification and measurements](./optimization-2026-11-18.md)

## Resource and notification cleanup (2026-11-18)

Unused legacy BB assets are removed from the installed bundle. Carousel returns an optional reminder-history update; the server persists it before delivery. The original plan now records implementation evidence, measurements and verification limits alongside its acceptance criteria.
Source: [Resource and notification cleanup: plan and results](./optimization-plan.md)

## Public build guide and README media

The product README is the visitor-facing entrypoint. This agent context tree remains rooted at HANDOFF.md. The public setup guide separates first installation from updates and links to the existing hardware and updater references.
Source: [Build your EMO](../docs/build.md)

README covers and the staged demo come from tools/build_readme.py. Run it with the existing Pillow environment; --font can select a local TrueType font. It samples the actual BB renderer without contacting a device. The panel screenshot uses local index.html with example state. Do not use the demo as evidence of live message delivery.

## Credits and publication preparation

The code license, artwork provenance and redistribution notices require a separate publication decision. The credits page records the current evidence and its limits.
Source: [Credits and reuse status](../docs/credits.md)

## Rollback

Use the confirmed A/B rollback procedure in [Wi-Fi updater and recovery](./wifi-updates.md). Never copy individual old files over the active slot. Historical snapshots under backups/before-figma, before-enlargement, before-full-set, before-inversion, before-speech, before-behaviour-update and before-syllables are fixtures and source references; port a consistent set into a complete validated bundle when needed.

Reset even after failed USB diagnostics and restore the prior mode/inversion. No erase or Wi-Fi rewrite is needed. The pre-consolidation handoff at backups/handoff-before-consolidation.md is historical, not current guidance.
