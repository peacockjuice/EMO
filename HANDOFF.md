---
title: "EMO: handoff for the next agent (2026-11-15)"
tags: [emo, esp32, oled, handoff]
---

# EMO: handoff for the next agent (2026-11-15)

The user is building an animated monochrome OLED robot face on ESP32-S2, controlled from a local web panel. Reply in Russian. This is the current entrypoint covering all three related conversations; follow the topic links below before changing the relevant part.

## Repository snapshot v0.1

This private Git snapshot removes embedded AP credentials. Read [README.md](./README.md) and [SECURITY.md](./SECURITY.md) BEFORE deploying or rolling back: current and backup bmo.py require an ignored board-local ap_cfg.py. The physical board is unchanged. Raw serial logs referenced below are intentionally not committed; structured reports remain. The original handoff snapshot hashes describe the pre-export working files, not the sanitized bmo.py. Live character/scenes remain a [plan](./ROADMAP.md), not shipped functionality.

## Start here

Project source of truth: `/Users/vpavlin/.bb/thread-storage/thr_psix2q4mn2/bmo/`.
Live panel: http://192.168.1.43/ (DHCP address can change). Current serial device: `/dev/cu.usbserial-210` (previously -110).
Last requested changes are complete: visible branding EMO, main 33-card emotion grid, and seven visual speech cards under Разговор BELOW that grid. Auto and inversion controls remain above the grids. The panel now uses a warm cream/beige background, chocolate cards and caramel selection accents; OLED thumbnails remain monochrome. No feature request is pending.
At handoff, live state is talk_bobo with inversion off; the served HTML matches local index.html. See [snapshot](./preview/handoff-snapshot.json) for the actual observation time, hashes and state. A reboot starts auto with inversion off; selected mode and inversion are not persisted.

## Current behaviour and API

- Main grid: rosto01–rosto30 plus look (31), wink (32), sleep (33).
- Speech: talk_calm (Рассказывает), talk_fast (Болтает), talk_excited (Сердится и говорит, angry rosto07 despite the legacy key), talk_bobo, talk_bebe, talk_baba, talk_bibi.
- Four syllable modes repeat closure/vowel without a rest until mode changes; no audio. All selected sequences repeat. Sleep has progressive Zs; rosto08 moves only pupils.
- auto alternates smile and random original rosto01–rosto30; it does not select extra behaviours or speech modes.
- Aliases: smile→rosto01; happy/talk→rosto02; love→rosto21; wow→rosto13; sad→rosto03; sample_blink→rosto01; sample_talk→rosto02; sample_cry→rosto12.
- GET / serves index.html. GET /state returns mood and invert. GET /set?e=<key> returns ok, mood, invert and changes the animation version for a valid selection.
- GET /invert?value=1 or 0 sets an explicit native OLED inversion value; returns ok/mood/invert, preserves mood and animation version. Invalid values fail. Inversion survives display reconnect, not reboot.
- UI serializes requests, keeps the latest unconfirmed intent for retry and pauses polling after an error. Status says Выбрано; it does not claim physical display confirmation.

There are 40 canonical timelines plus auto, 104 unique 1024-byte frames (106,496 bytes). The bank stays in flash; only one frame is read into the display buffer. There is no PSRAM. Keep future changes small.

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
