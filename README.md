# EMO

Private snapshot of the ESP32-S2 / SSD1306 animated face robot. 33 emotion cards, seven speech modes, auto mode, inversion and a warm beige/brown local web panel.

Start with [HANDOFF.md](HANDOFF.md) for hardware, development, deployment and decision history. This repository is a portable sanitized snapshot of the working project. Absolute Mac paths in historical documentation describe the original environment; run commands from your checkout instead.

## Before deploying this snapshot

The board now has a USB-installed authenticated app updater. Its Wi-Fi configuration remains board-only. See [Wi-Fi updates and recovery](handoff/wifi-updates.md) before deployment. Use the full-bundle updater; legacy partial USB uploads do not maintain slot manifests.

The hardcoded fallback access-point password has been removed from bmo.py and historical backup copies. These now import `AP_NAME` and `AP_PASS` from **ap_cfg.py**. Create that ignored file from ap_cfg.example.py, choose a unique password and upload it separately before deploying bmo.py from this repository. Before OTA provisioning, the staging uploader supports ap_cfg.py when explicitly named; it refuses partial uploads once OTA is installed. Never commit ap_cfg.py or wifi_cfg.py. Historical rollback instructions also require ap_cfg.py because archived source was sanitized.

No virtual environments, raw serial logs, credentials or unrelated conversation transcripts are included. Generated assets, firmware image, SVG originals, previews, structured test reports, tools and backup fixtures are included. Historical test records describe the working build before this security-only config extraction; the updater has separate local and hardware evidence in the current handoff.

## Release scope

The v0.1 tag preserves the original release. Current main (0.3-dev) adds four moods, six scenes and authenticated Wi-Fi app updates. Local and live-panel tests passed; all six scenes completed on hardware in both inversion states. The 30-minute soak was explicitly deferred by the user. See HANDOFF.md and preview/character-tests.json.

See [SECURITY.md](SECURITY.md) for review scope and remaining limitations. Original third-party artwork and driver notices are retained; private storage does not establish redistribution rights.
