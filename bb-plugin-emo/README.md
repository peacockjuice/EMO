---
title: "EMO BB plugin"
tags: [emo, bb, plugin]
---

# EMO BB plugin

EMO version **0.3**.

Monitors visible root threads in selected BB projects and sends an authenticated snapshot to the EMO OLED over the LAN. Existing projects are selected on first install; new threads within them join automatically. The EMO sidebar page changes this selection, excludes individual threads and opens a thread by its stable alias.

## Install and update

From this directory, run `npm ci`, `npm run check`, `npm test`, then `bb plugin build .`. Install the resulting local package with `bb plugin install . --yes`. After source changes, build again and reload with `bb plugin reload emo`.

On the Mac holding the robot updater key, run `bb emo provision`. It stores a domain-separated derived key in BB secret settings; neither key is printed. Configure a changed LAN address with `bb plugin config emo set url http://<device-ip>`. The robot starts in BB mode after power-on or restart. If you selected a different mode, choose «Уведомления BB» in the robot panel to return to BB.

## Runtime rules

One event subscription plus startup/reconnect reconciliation; no steady polling of thread lists. Pending questions and background work are independent. Questions and errors rotate in complete eight-second slots. Unread root replies get wink/smile and «ЕСТЬ ОТВЕТ», immediately and then at least sixty seconds apart until BB marks them read or a new turn starts. A due reply can follow an urgent slot, so neither queue starves. A new urgent event replaces a background face immediately but does not cut an attention slot. Display timestamps are persisted independently of unread state. Old seen fields are not read receipts. Work, queue and idle show faces only. An interrupted turn creates no reply notice. A retry must reference the failed request.

The device heartbeat is ten seconds, snapshot TTL thirty seconds. A lost BB subscription sends unknown state; failed delivery lets the last snapshot expire. Manual mode commands win over in-flight packets. Authentication covers a single-use boot challenge, sender epoch, increasing sequence and the response. Delivery does not require or send transcript/error text.

## Tests

Node 22.18+ with built-in TypeScript stripping runs the policy, signed transport and SDK fake-host tests. Device-side protocol and frame checks are in `../tools/check_bb.py`. CPU tests do not prove physical OLED readability or Wi-Fi reliability.

## Dependencies

| Document | Purpose |
|---|---|
| [Operator skill](./skills/emo/SKILL.md) | Commands and delivery diagnosis |
| [Design and acceptance](../handoff/bb-notifications-plan.md) | Display, queue and deployment contracts |
