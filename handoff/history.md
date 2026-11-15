---
title: "EMO: decisions across the three conversations"
tags: [emo, esp32, oled, handoff]
---

# EMO: decisions across the three conversations

This is a decision and implementation history, not a verbatim transcript. No network credentials are copied here. User turns in both earlier threads were inspected for this handoff; implementation details were reconciled with the prior handoff and current project.

## Source conversations

- `thr_idubxh5c6k`: first wiring research, requested display Hello World, USB detection attempts.
- `thr_psix2q4mn2`: continued detection, successful wiring and MicroPython installation, first animated face, web control and home network.
- `thr_rxakmvqqxy`: Figma migration, full animation catalog, inversion, speech and EMO branding; this handoff.

If a specific historical detail is needed: `rtk proxy bb thread log <id> --all`. Earlier logs may contain sensitive network input: do not export raw transcripts into project files or quote credentials.

## Initial hardware and robot

The user connected ESP32-S2, breadboard and OLED, then asked for Hello World. USB discovery initially failed. The user tried DIP changes, cables, hub, boot/reset; removing incorrectly connected display wires restored discovery. The pin drawing was mirrored relative to the viewed board. Correct CH340 DIP routing and wiring are in the hardware guide.
The user explicitly authorized flashing without an original-firmware backup. MicroPython and the SSD1306 display worked. Requested kawaii BMO face was enlarged to fill more of the screen. The user installed the OLED upside down; firmware rotation compensates globally.
The user requested phone/computer emotion control, then home Wi-Fi. The configuration must remain board-only; the Mac copy was deleted by request. A wide-eye tweak was explicitly reverted before the first handoff; do not resurrect it as pending work.
Possible future signals were discussed (time/night sleep, presence, touch, weather, Mac/agent events). They were ideas, not implemented features or current requirements. The board has no Bluetooth.

## Figma import and static approval

The user supplied a screenshot of BMO Face Templates/Assets and exported 30 Rosto SVGs plus board PNG from `/Users/vpavlin/Downloads/BMO Face Templates_Assets (Community) (1)`. Originals were copied to assets/figma.
Plan was refined through requested self-review: adapt static set, verify representative OLED faces, approve sample motion, then complete the set. A first generic monochrome conversion was insufficient: cheeks looked like extra eyes, bright eye highlights became holes, masks were recolored incorrectly, review bank could become stale. Fixes preserved SVG mask/clip coverage, used cheek hatching, bright highlights and outlined tears, and built review IDs/frames together with manifests. Buffer verification was explicitly distinguished from physical visual proof.
User accepted static artwork and requested animations. Approved samples were rare blink (01), talking (02), crying (12).
A physical-screen photograph showed too much empty space. User requested enlargement wherever possible. Fixed per-face transforms enlarged 23 sparse faces while preserving dense faces and consistent animation geometry. User approved the resulting size/timing and requested the entire set on the website.

## Full catalog and reviews

All 30 original faces became animated with auto and legacy aliases. Visual review corrected clipped hearts/spirals/eyes and component masks. Full cycles ran with concurrent HTTP. Browser automation was unavailable, so handler tests used mock DOM plus optional real HTTP, not a visual-browser claim.
A retry bug discarded unconfirmed selections; fixed by retaining the latest requested mode and allowing explicit retry, pausing automatic polling after failure. Status wording is Выбрано because the API confirms selection, not optical display state.
User requested inversion: native SSD1306 command, immediate and independent of mode, reflected in thumbnails, reapplied after display reconnect. It is not saved across reboot.

## Speech and extra behaviours

Three speech styles were added: Рассказывает, Болтает, initially an excited/exclaiming style. Review shortened excessive pauses in fast speech, checked ALL non-mouth pixels rather than the first half of the buffer, and distinguished active-pose speed from whole-loop duration.
User then explicitly requested:
- Replace exclaiming speech with angry speech. UI is Сердится и говорит, based on rosto07; API key talk_excited retained for compatibility.
- Недовольство / rosto08: only pupils move left/right, eyelids fixed.
- Спит: progressively add three sleepy Z glyphs.
- Move Осматривается, Подмигивает, Спит into the main emotion grid: entries 31–33.

Speech was separated into its own section and four distinct mouth modes added: Бобобо, Бебебе, Бабаба, Бибиби. User asked for endless loops: removed rests between syllables; each continuously alternates lip closure (90 ms) and vowel (210/170/230/120 ms respectively) until a different mode is chosen. No audio is generated. Other selected animations also repeat through the runtime loop.
User requested visual cards like Все эмоции. All seven speech cards now use actual bank-frame PNG thumbnails with shared active/inversion treatment.
Latest UI request: replace BMO with EMO and move Разговор below the main grid. Implemented in title/header and section order. Internal filenames/hostname were not renamed.

## Warm palette update

After the consolidated handoff, the user requested refined beige/brown colours. Updated only panel CSS: cream #f2e8da background, espresso #38281f text, chocolate #513b2e cards, ivory #fff3e3 card labels, caramel #ead0a8 selection. Secondary labels use opaque #d7c2ac for readability. Native controls use light color-scheme; keyboard focus is visible on buttons and inversion checkbox. OLED frame pixels, animation data and behaviour remain unchanged. Source is tools/index.template.html; build_web.py regenerates index.html. Previous template/page are in backups/before-warm-palette.

The user subsequently moved the inversion checkbox to the right of Сам по себе in a shared controls row. The row wraps only when the viewport cannot fit both controls. HTML deployed and live equality verified; handler checks passed.

## Working preferences and remaining scope

Respond in Russian. User likes direct execution and explicit self-review, with real fixes rather than inflated completion claims. Preserve approved artwork and timing unless a new request changes them. Physical photographs are authoritative for readability; preview screenshots alone are insufficient. Keep memory use small and prefer simple Python/stdlib and Mac-side computation for future external signals.
At the original v0.1 handoff, no feature request remained unfinished. No audio, background-signal integration or complete internal BMO rename is implied by prior requests. Future hardware/browser verification may add confidence but must not be reported as already performed.

## Character and scenes after v0.1

User approved implementation of a real mood-based character and scenes. Four feelings have explicit allowed transitions, rather than replacing character with random reactions. Six scenes reuse the existing bank. Sleep/wake replace the duplicate idea/curiosity scene. Scene execution shares the existing animation task; mode changes cancel it. See root handoff for current validation status.

## Character review refinements

Review tightened verification rather than changing the approved personality: short hardware tests are now the default, long soak requires an explicit mode, frame order is verified against the bank, logs are separated by test scope, and prior mode/inversion are restored after reset. Scene cards use six distinct representative poses. The earlier 15 ms figure is one measurement, not a guaranteed upper bound.

## Fast all-variants showcase

User requested a fast endless tour including inverted variants. Added Все подряд (demo): 40 animations and six scenes, paired normal/inverse, with pre-demo inversion restored on exit. This is a user-facing preview mode, not the deferred 30-minute regression test.
