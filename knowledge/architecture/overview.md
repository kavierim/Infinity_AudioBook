---
type: Architecture
title: Project overview
description: InfinityAudioBook goals, platform targets, and scope of the current proof of concept.
tags: [architecture, overview]
timestamp: 2026-07-05T08:30:00Z
---

# Goal

Build a Python-based, seamlessly playing **infinite audiobook** that generates new content dynamically during playback. The user can enter manual story-direction instructions in the terminal; they are applied to the next section generation without interrupting audio playback.

# Platform

| | |
|---|---|
| **Primary dev** | Windows (NVIDIA GeForce RTX 5060 Ti, CUDA 12.8) |
| **Runtime** | Cross-platform Python 3.10+ |

# Future vision (not in this PoC)

Integration of heart-rate sensors for biometric control of pacing or story direction.

# Related concepts

* [Pipeline](pipeline.md) — four-stage async architecture
* [Quick start](/playbooks/quick-start.md) — install and first run
* [Implementation phases](implementation-phases.md) — build order for agents and developers
