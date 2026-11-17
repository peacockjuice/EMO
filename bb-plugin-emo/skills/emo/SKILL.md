---
name: emo
description: Inspect or configure the EMO robot OLED session monitor in BB, troubleshoot delivery, or select tracked projects.
---

# EMO session monitor

Run `bb emo status` to inspect source health, delivery, stable session aliases and selected projects. This command returns no secrets. The EMO sidebar page opens sessions and controls project selection, session exclusions and dismissal of one failure.

`bb emo projects <project-id>...` replaces the selected project set. An empty list disables monitoring. New visible root threads in selected projects join automatically; hidden, archived, deleted and child threads are excluded.

On the Mac with the device updater key, `bb emo provision` derives a notification-only key from `~/.config/emo/update.key` and stores it in BB secret settings. The command prints only success. Never print either key. Set the robot URL with `bb plugin config emo set url http://<device-ip>`.

Delivery `mode_disabled` means choose «Уведомления BB» in the robot web panel. Incoming notifications never select that mode, including after a reboot. `unknown` means the BB source needs reconciliation; `offline` means delivery is unconfirmed. Heartbeats are ten seconds apart; the robot expires snapshots after thirty seconds.

The display header counts working threads, pending questions, errors and unread completions independently. A completion means the agent ended its turn, not that the task succeeded. Opening the BB thread clears its unread completion; pending questions require an actual answer or cancellation. Excluding a thread does not stop its work.
