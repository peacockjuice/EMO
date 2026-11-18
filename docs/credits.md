---
title: "EMO credits and reuse status"
tags: [emo, credits, publication]
---

# EMO credits and reuse status

This page records what the checkout contains. It does not grant reuse rights for material whose license has not been established.

## Project code

The repository contains the EMO application, BB plugin, build tools, and documentation. A project-wide license has not been selected. Public visibility alone does not supply an open-source license. See [GitHub’s licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository).

The repository owner needs to choose the terms for the code they own before calling the project open source.

## Face artwork

The original face files are in `assets/figma/Rosto-*.svg`. The build tools adapt them into the frame bank and previews. The README covers, demo, and character strip reuse those frame pixels.

The checkout does not identify the original artwork author or provide its license. Before public redistribution, record the source, author, license, and any required attribution. If permission cannot be established, replace both the source art and its derived assets.

## Display driver and firmware

`ssd1306.py` identifies itself as a MicroPython SSD1306 driver. Its local header does not state an author or license. Confirm the exact upstream source and applicable notice before redistribution.

The repository also contains a MicroPython binary and a board schematic in `firmware/`. Check their upstream notices and redistribution terms. The official MicroPython board page is linked from the build guide.

## README presentation

`tools/build_readme.py` creates the covers and demo from the current frame bank and display renderer. The scene is staged; no real BB messages are used. The panel image shows the real local HTML with example state.

SVG covers use system font fallbacks. Demo captions use a local font supplied to the build tool. No font file is included in the media bundle. Dependencies retain their own licenses.

## Publication checklist

- Select a license for project-owned code.
- Establish artwork provenance and permissions, including derived previews.
- Verify driver, binary, and schematic notices.
- Review tracked files and Git history for private data.
- Resolve the findings in [security and publication status](../SECURITY.md).

The README redesign does not change repository visibility or rewrite Git history.

## Dependencies

| Document | Purpose |
|---|---|
| [Security and publication status](../SECURITY.md) | Privacy review scope and remaining publication work |
