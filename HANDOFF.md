---
title: "EMO: handoff for the next agent (2026-11-15)"
tags: [emo, esp32, oled, handoff]
---

# EMO: handoff for the next agent (2026-11-15)

The user is building an animated monochrome OLED robot face on ESP32-S2, controlled from a local web panel. Reply in Russian. This is the current entrypoint covering all three related conversations; follow the topic links below before changing the relevant part.

## Private repository v0.1

Sanitized snapshot: https://github.com/peacockjuice/EMO (private), tag v0.1; local checkout /Users/vpavlin/Projects/EMO. Read its README.md and SECURITY.md before deploying: its current/backup bmo.py import AP settings from ignored ap_cfg.py instead of embedding a password. This original working folder and board were not changed. Raw serial logs and private configurations were excluded from Git. Live character/scenes are future work, recorded in repository ROADMAP.md.

## Sanitized repository deployment

Current and backup bmo.py here require private ignored ap_cfg.py (see README.md). Do not upload repository bmo.py without that config. The source handoff snapshot hashes describe the working-board version before credential extraction. Raw serial logs are intentionally excluded; structured reports are included.

## Start here

Project source of truth: `/Users/vpavlin/.bb/thread-storage/thr_psix2q4mn2/bmo/`.
Live panel: http://192.168.1.43/ (DHCP address can change). Current serial device: `/dev/cu.usbserial-10` (previously -210 and -110).
Last requested changes are complete: visible branding EMO, main 33-card emotion grid, and seven visual speech cards under Разговор BELOW that grid. Auto and inversion controls remain above the grids. The panel now uses a warm cream/beige background, chocolate cards and caramel selection accents; OLED thumbnails remain monochrome. Character/scenes are implemented; see the behaviour section below for release validation status.
At the latest handoff, live state is auto with inversion off; the served HTML matches local index.html. See [snapshot](./preview/handoff-snapshot.json) for the actual observation time, hashes and state. A reboot starts auto with inversion off; selected mode and inversion are not persisted.

## Current behaviour and API

- Main grid: rosto01–rosto30 plus look (31), wink (32), sleep (33).
- Speech: talk_calm (Рассказывает), talk_fast (Болтает), talk_excited (Сердится и говорит, angry rosto07 despite the legacy key), talk_bobo, talk_bebe, talk_baba, talk_bibi.
- Four syllable modes repeat closure/vowel without a rest until mode changes; no audio. All selected sequences repeat. Sleep has progressive Zs; rosto08 moves only pupils.
- auto now runs a calm/curious character with four moods and six defined scenes (anger is manual-only); it no longer picks random original faces.
- Aliases: smile→rosto01; happy/talk→rosto02; love→rosto21; wow→rosto13; sad→rosto03; sample_blink→rosto01; sample_talk→rosto02; sample_cry→rosto12.
- GET / serves index.html. GET /state returns mood and invert. GET /set?e=<key> returns ok, mood, invert and changes the animation version for a valid selection.
- GET /invert?value=1 or 0 sets an explicit native OLED inversion value; returns ok/mood/invert, preserves mood and animation version. Invalid values fail. Inversion survives display reconnect, not reboot.
- UI serializes requests, keeps the latest unconfirmed intent for retry and pauses polling after an error. Status says Выбрано; it does not claim physical display confirmation.

There are 40 frame timelines, six composite scenes and auto, 104 unique 1024-byte frames (106,496 bytes). The bank stays in flash; only one frame is read into the display buffer. There is no PSRAM. Keep future changes small.

## Live character and scenes

Implemented after v0.1 in behaviour.py, using existing frames. Four feelings: calm, curious, joy, sleepy. Mood changes every 2–4 minutes through allowed transitions. Scenes: scene_curious, scene_greeting, scene_shy, scene_drowsy, scene_wake, scene_grumpy (manual only). Main catalog and speech remain unchanged. Scene cards appear below speech.

A manual scene runs once, then repeats its ending animation in phase hold. Re-selecting restarts it. A mode command cancels via S.ver; only selecting auto resumes autonomous behaviour. Inversion does not cancel. API retains mood/invert and adds scene (nullable), phase (idle/scene/hold), feeling (nullable). Mood is the user-selected mode; auto stays selected while scene/feeling change. Sleep and wake are distinct scenes.

Auto starts with 20–40 seconds of calm; scene cooldown is 30–90 seconds after completion. No consecutive scene repeats; sleep has a five-minute cooldown. On display reconnect manual scenes restart and auto starts a fresh character. A later user command always wins. State is not persisted across reboot.

Local cancellation, transition, wraparound, inversion and web-handler checks passed. All six manual scenes completed on hardware in both inversion states; the review run also checked exact displayed frame hashes in order; cancellation samples measured 15 ms initially and 25 ms in the review run (not a latency guarantee). The 30-minute auto soak was interrupted by external manual selection; the user explicitly deferred it. It is not complete. Evidence: preview/character-tests.json; raw logs remain local. Physical visual acceptance is still required. Rollback snapshot: backups/before-personality; runtime now also requires behaviour.py.

## Hardware, network and recovery

Read before connecting peripherals, debugging a dark screen, touching serial, Wi-Fi or flashing. Includes exact wiring, DIP switches, rotation and known failure modes. wifi_cfg.py must stay ONLY on the board: never read it back, print it or copy it to the Mac. Normal updates do not require erasing flash.

Source: [Hardware, network and recovery](./handoff/hardware.md)

## Development and release

Read before edits or deployments. Covers source vs generated files, build commands, tests, upload/reset rules, backups and evidence limits. Edit tools/index.template.html, not generated index.html. Internal BMO filenames and hostname remain intentionally unchanged.

Source: [Build, deployment and verification](./handoff/development.md)

## Conversation history and decisions

Read to understand user approvals, rejected approaches, design choices and ideas that were discussed but never commissioned. Covers thr_idubxh5c6k, thr_psix2q4mn2 and thr_rxakmvqqxy.

Source: [Decisions across the three conversations](./handoff/history.md)

## Verification boundary

The original complete bank received device regression; later additions received scoped device/local checks. Do not claim one full current-release hardware run. The current handoff only rechecks live HTTP/state and documentation; it does not reflash or rerun hardware tests.
Real-browser rendering was not verified because the computer-use host was unavailable. Mock DOM tests are not browser screenshots. Device buffer hashes prove data/execution, not optical appearance; user photographs supplied physical size/readability approval.
The source and live HTML match at this handoff. Remaining limitations are documented, not hidden unfinished feature requests.
