---
title: "EMO: handoff for the next agent (2026-11-17)"
tags: [emo, esp32, oled, handoff]
---

# EMO: handoff for the next agent (2026-11-17)

The user is building an animated monochrome OLED robot face on ESP32-S2, controlled from a local web panel. Reply in Russian. This is the current entrypoint covering all three related conversations; follow the topic links below before changing the relevant part.

## Repository and deployment differences

Private repository: https://github.com/peacockjuice/EMO. Local checkout: /Users/vpavlin/Projects/EMO. Tag v0.1 is the original release; main contains the implemented character, scenes and 500 ms showcase. VERSION is 0.4-dev. Do not overwrite v0.1.

The canonical working/deployment source is now /Users/vpavlin/projects/EMO/. The older /Users/vpavlin/.bb/thread-storage/thr_psix2q4mn2/bmo/ snapshot is historical. Repository bmo.py and archived copies are sanitized: they import AP_NAME/AP_PASS from ignored private ap_cfg.py. Read README.md before deploying repository code. The board now imports its private ap_cfg.py; Wi-Fi credentials remain unchanged. Never copy the old embedded AP password into Git.

wifi_cfg.py is board-only; never read it back, print it or copy it to the Mac. Raw serial logs, private configs and virtual environments are excluded from Git. Source snapshot hashes describe working files before credential extraction. Structured test reports, graphics, firmware, build tools and backup fixtures are included.

## Start here

Project source of truth: `/Users/vpavlin/projects/EMO/`.
Live panel: http://192.168.1.43/ (DHCP address can change). Current serial device: `/dev/cu.usbserial-110` (USB data reconnected 2026-11-17; previously -10 and -210).
Last requested changes are complete: visible branding EMO, main 33-card emotion grid, and seven visual speech cards under Разговор BELOW that grid. Auto and inversion controls remain above the grids. The panel now uses a warm cream/beige background, chocolate cards and caramel selection accents; OLED thumbnails remain monochrome. Character/scenes are implemented; see the behaviour section below for release validation status.
On 2026-11-16 the user disconnected USB from the Mac; the robot still responds over home Wi-Fi. The read-only check reported auto, sleepy, inversion off. This is a point-in-time observation, not a persistent setting. An authenticated app updater is now installed on port 8080. A full LAN upload and healthy boot confirmation passed; see the Wi-Fi update section below. See [historical network check (2026-11-16)](./preview/handoff-network-check.json) and [previous deployment snapshot](./preview/handoff-snapshot.json) for scope and timestamps. A reboot starts BB with inversion off; selected mode and inversion are not persisted.

## Current behaviour and API

- Main grid: rosto01–rosto30 plus look (31), wink (32), sleep (33).
- Speech: talk_calm (Рассказывает), talk_fast (Болтает), talk_excited (Сердится и говорит, angry rosto07 despite the legacy key), talk_bobo, talk_bebe, talk_baba, talk_bibi.
- Four syllable modes repeat closure/vowel without a rest until mode changes; no audio. All selected sequences repeat. Sleep has progressive Zs; rosto08 moves only pupils.
- auto now runs a calm/curious character with four moods and six defined scenes (anger is manual-only); it no longer picks random original faces.
- Aliases: smile→rosto01; happy/talk→rosto02; love→rosto21; wow→rosto13; sad→rosto03; sample_blink→rosto01; sample_talk→rosto02; sample_cry→rosto12.
- GET / serves index.html. GET /state returns mood and invert. GET /set?e=<key> returns ok, mood, invert and changes the animation version for a valid selection.
- GET /invert?value=1 or 0 sets an explicit native OLED inversion value; returns ok/mood/invert, preserves mood and animation version. Invalid values fail. Inversion survives display reconnect, not reboot.
- UI serializes requests, keeps the latest unconfirmed intent for retry and pauses polling after an error. Status says Выбрано; it does not claim physical display confirmation.

There are 40 frame timelines, six composite scenes, auto and demo, 104 unique 1024-byte frames (106,496 bytes). The unused 18-frame compact BB tail and its generator/module were removed; active bytes, indices and timings are unchanged. The bank stays in flash; only one frame is read into the display buffer. There is no PSRAM. Keep future changes small.

## Live character and scenes

Implemented after v0.1 in behaviour.py, using existing frames. Four feelings: calm, curious, joy, sleepy. Mood changes every 2–4 minutes through allowed transitions. Scenes: scene_curious, scene_greeting, scene_shy, scene_drowsy, scene_wake, scene_grumpy (manual only). Main catalog and speech remain unchanged. Scene cards appear below speech.

A manual scene runs once, then repeats its ending animation in phase hold. Re-selecting restarts it. A mode command cancels via S.ver; only selecting auto resumes autonomous behaviour. Inversion does not cancel. API retains mood/invert and adds scene (nullable), phase (idle/scene/hold), feeling (nullable). Mood is the user-selected mode; auto stays selected while scene/feeling change. Sleep and wake are distinct scenes.

Auto starts with 20–40 seconds of calm; scene cooldown is 30–90 seconds after completion. No consecutive scene repeats; sleep has a five-minute cooldown. On display reconnect manual scenes restart and auto starts a fresh character. A later user command always wins. State is not persisted across reboot.

Local cancellation, transition, wraparound, inversion and web-handler checks passed. All six manual scenes completed on hardware in both inversion states; the review run also checked exact displayed frame hashes in order; cancellation samples measured 15 ms initially and 25 ms in the review run (not a latency guarantee). The 30-minute auto soak was interrupted by external manual selection; the user explicitly deferred it. It is not complete. Evidence: preview/character-tests.json; raw logs remain local. Physical visual acceptance is still required. Rollback snapshot: backups/before-personality; runtime now also requires behaviour.py and showcase.py.

## Fast showcase mode

The Все подряд button selects demo. showcase.py loops through all 40 canonical frame animations and six composite scenes; each is shown normally then inverted. Aliases are omitted because they repeat the same content; auto is a scheduler, not an additional visual variant. Each animation and scene is sampled into a 500 ms preview per polarity: ten 50 ms samples with matching neighbours merged. Long scenes are abbreviated, not fully played. A complete 46-variant paired cycle targets 46 seconds plus command overhead. Loop repeats indefinitely. API showing identifies the current variant; mood remains demo. UI displays the variant and inversion, disables the inversion checkbox during the tour.

Selecting another mode cancels demo and restores pre-demo inversion. Explicit API inversion changes during demo update that restored preference. Re-entering demo restarts it; reconnection restarts the tour. Local checks: tools/check_showcase.py, tools/check_web.mjs. The normal frame bank is unchanged.

## Immediate wiring reference

OLED power: j1 / V3V / 3.3 V → blue wire → VDD. OLED ground: j3 / GND → green → GND. OLED clock: j12 / IO9 → crimson → SCK. OLED data: j13 / IO8 → grey → SDA. j2 is +5 V and must remain unconnected to the OLED. These hole numbers apply only to the previously photographed breadboard orientation (USB at row 1, board pins in columns b and i). Confirm orientation before rewiring; a mirrored pin map previously caused loss of power/USB.

## Hardware, network and recovery

Read before connecting peripherals, debugging a dark screen, touching serial, Wi-Fi or flashing. Includes exact wiring, DIP switches, rotation and known failure modes. wifi_cfg.py must stay ONLY on the board: never read it back, print it or copy it to the Mac. Normal updates do not require erasing flash.

Source: [Hardware, network and recovery](./handoff/hardware.md)

## Development and release

Read before edits or deployments. Covers source vs generated files, build commands, tests, upload/reset rules, backups and evidence limits. Edit tools/index.template.html, not generated index.html. Internal BMO filenames and hostname remain intentionally unchanged.

Source: [Build, deployment and verification](./handoff/development.md)

## Conversation history and decisions

Read to understand user approvals, rejected approaches, design choices and ideas that were discussed but never commissioned. Covers thr_idubxh5c6k, thr_psix2q4mn2 and thr_rxakmvqqxy.

Source: [Decisions across the three conversations](./handoff/history.md)

## Current attention scenarios (2026-11-18)

Current bundle `d7d80f81a6d61ad36f62f80113ddf5aec98cc485c3310a02b80d601ada8d9dda` (169,600 bytes) starts in BB mode and scrolls text another 10% faster (about 1878 ms per traversal). It preserves the smaller 104-frame bank and the accepted attention policy. Startup prepares BB HTTP before scenes/font/renderer via set_mood. Automatic BB selection was observed after the OTA reboot, before any mode command or sender startup (preview/bb-default-start/automatic-start.json). Questions: shock/bobo; unread replies: wink/smile plus «ЕСТЬ ОТВЕТ», once per minute until BB read; errors: confusion/sadness. Work/queue/idle show only faces. Connection warnings repeat once per minute, with a 30s startup grace. Display history is separate from read state and survives plugin restart. Urgent and reply rings share complete 8s slots without starvation. The notification document's “Экран и очередь” section is canonical; older checkpoints below are historical.

The first attempt confirmed in auto but lost network after selecting BB (preview/bb-attention-first-attempt.json). After power recovery, extracting emo_bb_view.py and collecting between scene/font/renderer imports restored mode-first startup and live delivery, with about 40 KB native free in signed receipts. No USB diagnostics were available, so the exact memory cause is an inference, not a measured before/after allocation trace. The sender remains off during updates. Evidence: preview/bb-attention-mode-first.json and preview/bb-attention-acceptance.json. The intended live unread-minute check is recorded as skipped in preview/bb-attention-reminders.json because the user had already read the available reply; deterministic policy tests cover the cadence, restart and actual-read distinction. tools/check_bb_reminders.py can observe a future real unread reply without mutating it.

## Resource and reminder-history cleanup (2026-11-18)

The smaller full bundle is confirmed after normal startup, with no pending/trial release. Three separate 12-round panel/live series passed: before cleanup, after assets with the old plugin, and after plugin reload on the same smaller firmware. Carousel now returns an explicit optional notice; the server saves it before delivery, keeping unread state independent. Source totals and scoped verification are recorded in the [completed-change measurements](./handoff/optimization-plan.md). No optical OLED acceptance or deferred 30-minute soak was performed.

## Previous quiet-idle adjustment (2026-11-17)

Bundle `1f13c37023cc468bfb3e1f400abdaf6ff50d0d86cb7daf7806e8811c0ad12cb4`: a live idle card shows only the calm face, without counters or text cycling. Match card=idle and face=idle, not face alone: an older completion also uses the idle face and must retain its message. Offline/unknown states remain visible. Seventeen local tests; live evidence: preview/bb-quiet-acceptance.json.

## Previous scrolling adjustment (2026-11-17)

Bundle `7e26f16d77ffc0281b6e54a7f4d15b3cf638dff2d9f4a0053823d23538cacfa4`: text traversal is another 10% faster, 2500/1.21 ≈ 2066 ms. Layout, accents, 0.5s lead and 8s card slot are unchanged. Updated preview/bb-cycle.gif; live evidence: preview/bb-speed-acceptance.json.

## Previous font refinement (2026-11-17)

Bundle `68e374644986639372dce0119a3de106cf9b70f93f7cad5ef9ed37a15c693dea` (187525 bytes): large Ё and Й reuse full-height Е/И bodies and draw separate dots/breve above the baseline, inside y=20…27. Counters end at y=17 and letter bodies start at y=32. Small glyphs retain their compact form. Sixteen local tests cover body preservation, mark separation and clipping at both screen edges. Preview: preview/bb-accents.png; live check: preview/bb-accents-acceptance.json.

## Previous OLED layout refinement (2026-11-17)

Bundle `07942e4a1b7077632cb5d8f005fab8bc6c45e22ae6a89ffedb508caa078fbef0` (187260 bytes): counters move down to y=4; text grows to 20×28 px at y=32. Complete traversal takes 2500/1.1 ms, with the existing 0.5s lead and 8s card slot. Faces still have no counters. Verification: preview/bb-layout-v3-acceptance.json.

## Previous OLED layout update (2026-11-17)

Installed and confirmed `3d79dd06a8d70f50e9375757786ffa298dc313cf1e094be069b023125a2f90e4` (187258 bytes). Faces have no overlay or shift. Counters appear only with text; numbers are 2x (10×14; 99+ stays compact). The 3x line starts at y=40 and traverses in 2.5s instead of 5s after a 0.5s lead, holding its end for the remainder of the same 8s slot. Preview: preview/bb-layout.png and preview/bb-cycle.gif. Live verification: preview/bb-layout-v2-acceptance.json. Previous release evidence below remains historical.

## Previous OLED cycle update (2026-11-17)

Previously installed and confirmed `4c396d2e4a5b567f3df8aed0d891377c204793fb599c9e691d013af553f57679`: pending questions show shock for 1s, bobo speech for 1s, then 3x scrolling text for 6s, repeating. The footer is removed; top counters remain. The renderer reuses the original full-size frames and shifts them down four pixels. The font is a 460-byte packed table with no glyph dictionary, reducing persistent RAM. Fifteen receiver/render tests passed. Earlier cycle builds exhausted native memory despite isolated import tests; their reports are historical. Twelve full panel transfers alongside live BB passed (preview/bb-cycle-acceptance.json); local and installed hashes match (preview/bb-cycle-final-release.json). A clean restart and three more panel/live checks also passed (preview/bb-cycle-cold-boot.json). Final state: plugin enabled, BB live, inversion off (preview/bb-cycle-final-state.json). See the notification checkpoint for scope and physical visual limits.

## Previous BB recovery checkpoint (2026-11-17)

USB diagnostics identified native Wi-Fi memory exhaustion during import of the monolithic BB module. The module is now split into state, HTTP and display units; the main native pool retains 34,116 bytes after all imports. The complete application release `6af4e5ebad131a5bbea2fd131648f71c6b4c6dd48e80bbba86609d85c202e84d` was installed and confirmed at this earlier checkpoint; the OLED cycle release above supersedes it. No root updater, MicroPython core, Wi-Fi configuration or key was changed.

Twelve complete HTML transfers alongside live signed notifications and increasing frame/sequence counters passed over 172 seconds. Overlapping nonce reuse was rejected on hardware. OTA status timed out during concurrent panel/BB load but succeeded with the sender stopped and auto selected; use that quiet condition for updates. This is scoped verification, not a long soak or physical OLED visual acceptance. Sender expiry/restart, manual mode priority, BB resume and inversion passed on this release. Final state: emo plugin enabled, BB live, inversion off (`preview/bb-final-state.json`). Read [notification checkpoint](./handoff/bb-notifications-plan.md) for evidence and remaining limits.

## Notifications from BB

Implemented on 2026-11-17: local plugin bb-plugin-emo, signed /bb/challenge and /bb/state, separate bb mode, a repeating face/speech/large Cyrillic text cycle and independent counters. The local plugin is installed as emo; existing projects were selected on install. Normal control is the EMO sidebar page and the robot’s «Уведомления BB» button. Power-on and reboot start BB; manual mode selection remains available. Read the notification document for protocol, tests and remaining physical verification limits.

Source: [BB notification implementation plan](./handoff/bb-notifications-plan.md)

## Verification boundary

The original complete bank received device regression; later additions received scoped device/local checks. Do not claim one full current-release hardware run. The latest BB checkpoint includes full app installation and scoped hardware checks; earlier reports retain their original coverage.
Real-browser rendering was not verified because the computer-use host was unavailable. Mock DOM tests are not browser screenshots. Device buffer hashes prove data/execution, not optical appearance; user photographs supplied physical size/readability approval.
The latest network check records whether served HTML matches the current local page. Remaining limitations are documented, not hidden unfinished feature requests.

## Safe Wi-Fi app updates

USB-installed supervisor, authenticated bundles, trial boot and recovery checks. Read this before any further deployment: the legacy partial USB upload path can invalidate slot manifests.
Source: [Wi-Fi updater and recovery](./handoff/wifi-updates.md)
