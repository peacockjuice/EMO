# Security review — v0.1

- Git repository starts with a new history; no old commits containing credentials are imported.
- Removed embedded fallback AP password from current and backup firmware sources; replaced with ignored board-local ap_cfg.py.
- No home Wi-Fi configuration was read from the board. wifi_cfg.py and ap_cfg.py are excluded; no such files are present in the exported tree.
- Virtual environments, caches and raw serial logs were excluded. Serial logs can disclose SSID; structured reports and visual artifacts remain.
- Reviewed credential-like filenames and source lines; scanned exported content for known removed AP password and common token/private-key patterns. This is a bounded secret review, not a guarantee against every possible secret format.
- Local IP addresses, original Mac paths and BB thread identifiers remain in private operational documentation. Do not make the repository public without another privacy/license review.
- The robot HTTP API has no authentication or TLS and changes state through GET. Treat it as a trusted-LAN device; do not expose it directly to the internet. Repository privacy does not secure the device network.
- Hardware was not changed during repository preparation. Existing board AP password has not been rotated; the snapshot requires a private ap_cfg.py before flashing its bmo.py.

## Wi-Fi app updates — 0.3-dev

The update port 8080 requires HMAC-SHA256 with a random 32-byte key, a single-use expiring challenge, body hash and per-file hashes. Successful replies are authenticated. The bundle filename allowlist excludes private keys and boot/config files. This is not filesystem isolation: once running, application Python code can write root files. The key is local to Mac and board, not in Git.

Uploads write the inactive application slot. A flushed journal rename selects a verified trial. Failed/unconfirmed trial boots revert; a 60-second watchdog handles a startup hang. The client requires advancing frames and at least ten seconds uptime before confirmation. See handoff/wifi-updates.md for precise limits and recovery.

No TLS, secure boot or encryption at rest is claimed. A shared-key holder can install arbitrary application code. LAN denial of service and physical flash failure are not prevented. Port 80 remains unauthenticated. Do not forward either port to the internet. Physical power-cut fault injection and long-term OTA soak remain untested.
