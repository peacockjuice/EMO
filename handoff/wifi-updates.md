---
title: "EMO: Wi-Fi updates and recovery"
tags: [emo, wifi, security, deployment]
---

# EMO: Wi-Fi updates and recovery

Updates cover Python application code, OLED assets and the web panel. MicroPython core, the boot supervisor and Wi-Fi credentials still require USB. Application update transport and initial boot health are tested separately from long-term character behaviour.

## Current checkpoint

Installed through USB on 2026-11-16. A full application bundle was subsequently uploaded over real Wi-Fi, rebooted into /ota_a and confirmed after frame progress. That checkpoint used VERSION 0.3-dev; current source is the 0.3 release candidate; source labels do not establish what is installed. The v0.1 Git tag remains unchanged. Follow-up network security and rollback evidence is in preview/wifi-live-tests.json; USB-triggered integrity/crash/watchdog checks are in preview/wifi-recovery-board.json. The USB tests alone do not prove network transport. preview/wifi-installed-files.json verifies the active bundle and root loader against local hashes; preview/wifi-final-check.json records the signed status and exact panel content after a hardware reset. Manual rollback selection is covered by local integrity/state tests; the live failure test checks automatic rollback.

A startup memory regression temporarily broke the panel during development. Root cause: importing the updater before network startup allowed the MicroPython heap to expand, leaving very little ESP-IDF heap for networking. Root main.py now sets gc.threshold(4096) before imports and activates STA early. This preserved roughly 42 KB total free native heap in a diagnostic snapshot, versus roughly 8 KB before (not a permanent guarantee). Do not remove this early GC policy. Both the panel and signed update status worked after the fix. The user's Chrome AdGuard extension remains enabled and was not the cause.

The 30-minute character soak remains deferred by the user and is unrelated to update tests.

## Commands

Run from the project root on the Mac. Keep robot power on throughout an update.

```sh
rtk proxy python3 tools/wifi_update.py status
rtk proxy python3 tools/wifi_update.py upload
rtk proxy python3 tools/wifi_update.py rollback
```

Default address: http://192.168.1.43:8080. Override with --url when DHCP changes. upload skips a release whose manifest already matches active (no flash write or reboot); otherwise it sends a full matching application bundle; --source selects a different source directory. rollback requests the previous verified slot and runs the same trial/confirmation sequence. If communication fails, do not assume success: inspect status. resume retries a staged update; cancel discards a staged update before trial. An unconfirmed trial is reverted after reset/watchdog. A lost reboot/confirmation reply is followed by signed status checks. If status cannot be read, the client reports an unknown result; it must not promise that rollback occurred. Identical release hashes in both slots do not turn a rejected trial into success.

## Authentication and privacy

A 32-byte random shared key exists only at ~/.config/emo/update.key on the Mac (0600) and /.ota_key on the board. Never print, commit, embed in a URL or upload this key to a service. Losing it requires deliberate USB reprovisioning; do not bypass authentication. There is no browser upload button: the key stays outside the web panel.

Each command uses HMAC-SHA256 over method, path, a fresh single-use challenge and body SHA256. Successful responses are authenticated too. The client verifies release identity before confirmation. Each file and full upload body are checked. Expired/replayed requests and protected filenames are rejected.

This is authenticated HTTP, not TLS: application code is observable on the LAN. Traffic analysis and denial of service remain possible. Use a trusted LAN and no internet port forwarding. The existing panel on port 80 remains unauthenticated. This is not secure boot or protection against a person with USB/flash access or a compromised signing key.

## Boot and slot layout

Excluded from normal update bundles: /main.py, /ota_boot.py, /ota_http.py, /ota_protocol.py, /.ota_key, /.ota_state.json, /wifi_cfg.py, /ap_cfg.py. Root is the original application baseline. New full applications go to /ota_a or /ota_b; only the inactive target is written. Each contains ota_manifest.json. The current working directory is the running slot; root remains on sys.path for private configuration and the updater. These files are not hardware write-protected: application Python code has filesystem access. An authorised but faulty or malicious app can modify them. The allowlist protects the upload path, not arbitrary code after execution.

The journal uses a flushed temporary file and rename on the same filesystem. The active pointer is unchanged until all bytes verify. Before a trial import, the supervisor marks the trial in the journal and starts a 60-second watchdog. A crash, hang, power loss or reset before confirmation returns to the old active slot on the next boot. Confirmation requires at least 10 seconds uptime and rendered frames; the client also checks that the frame count advances between polls. This is an initial health check, not a guarantee of future correctness.

After confirmation, a subsequent application failure does not automatically select the previous release; the watchdog can restart the confirmed version. Use a verified manual rollback or USB recovery when necessary. Normal operation feeds the watchdog every two seconds. Uploads use bounded chunks and limits. An interrupted upload can damage the inactive/previous slot but must not modify the current active slot; manual rollback verifies the previous slot before selection. Physical power-cut fault injection has not been performed. Do not promise immunity from flash damage or arbitrary hardware failure.

## USB bootstrap and recovery

One-time setup: tools/bootstrap_wifi.py PORT. It stages and hashes files, writes main.py last, and refuses to provision when an OTA key or journal already exists. Existing board-only wifi_cfg.py is never read. If private ap_cfg.py is missing on a new board, provision it privately first (or supply an ignored local ap_cfg.py). No credentials are recovered from Git backups.

After provisioning, upload_release.py refuses partial USB updates when the OTA key or journal exists, before writing any files. This prevents bypassing slot manifest/journal consistency; its refusal still resets the board after interrupting raw REPL. Do not blindly rerun bootstrap or erase the device. For recovery, connect USB, interrupt into raw REPL, inspect only journal/status and slot hashes, select a known verified complete slot in the journal, and reset. Do not read wifi_cfg.py or .ota_key into tool output. Updater changes need an explicitly reviewed USB deployment with a consistent root baseline.

Local checks: tools/check_wifi_update.py and tools/check_wifi_client.py. The client review covers lost reboot/confirmation replies, same-release rollback classification, uncertain timeout, no-op upload and the legacy USB guard. preview/wifi-client-review-live.json records a real no-op upload with unchanged boot state and continuous uptime; these host-only fixes did not require flashing the board. Live network regression: tools/check_wifi_live.py (intentionally uploads a crashing test app, verifies automatic recovery, and leaves the confirmed release active). Hardware recovery probe: tools/check_wifi_recovery_board.py PORT (requires original root baseline active and no pending update; temporarily stages intentionally broken applications, then restores the baseline). It checks integrity rejection, import failure rollback and watchdog recovery; it is not the normal updater.

## Dependencies

| Document | Purpose |
|---|---|
| [Hardware](./hardware.md) | Exact board, OLED pins and USB wiring |
| [Development](./development.md) | Asset builds and existing regression checks |
