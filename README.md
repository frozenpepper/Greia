# Greia OS

Greia is an educational operating system for young children. It turns old
and low-cost computers, from a first-generation Acer Aspire One netbook to a
Raspberry Pi 400/500, into something closer to a small learning console than
a desktop PC.

```text
power on
  -> Greia
  -> choose your profile
  -> choose an Activity
  -> play / learn / create
  -> return safely to Greia
```

Linux is the substrate, not the product. A child never sees a terminal,
desktop, login prompt, file manager, package manager or browser chrome.
**Greia Shell is the child's operating system.**

> **Status: pre-release (`0.13.0-phase0-dev`).** There is no supported
> download for families yet. The source is being prepared for public
> development; hardware certification, production Parent pairing, safe
> updates and the licensing audit are still open. See
> [docs/release/GREIA_PUBLIC_RELEASE_READINESS.md](docs/release/GREIA_PUBLIC_RELEASE_READINESS.md).

## What is in the box

- **45 built-in Activities**, mostly for ages 3–7: painting and writing
  studios, numbers, letters and phonics, music, stories, a puppet theatre, a
  children's encyclopedia and more. Four languages can be selected: English, Italian, Spanish and French;
  release voice review and device acceptance are still being completed.
- **A child Shell** with explicit child profiles, Collections and a
  platform-owned Home button that every Activity keeps.
- **A Creations Library** (in progress) where each child's drawings, writing
  and recordings are saved and can be reopened across Activities.
- **Greia Parents**, a web client on the local network for profiles, time
  limits, Activity visibility, settings and updates. No cloud account needed.
- **An Activity Simulator** that runs the real Shell and platform services on
  a developer's desktop.
- **Image build tooling** that composes OS images from declarative profiles.
  x86 targets build today; Raspberry Pi images are in progress.

## Design principles

- **Activities are the universal abstraction.** Python today, Web and other
  runtimes later, all behind the same lifecycle, storage, permission,
  progression and input contracts. Activities report events; the platform
  owns rewards, child data and navigation.
- **Built for the weakest machine first.** The first-generation Acer Aspire
  One (Intel Atom, at most 1 GB of RAM, 1024×600) is the reference floor, and
  ARM devices are first-class targets. Bounded memory and cheap rendering are
  correctness requirements.
- **Offline and child-owned.** Core use works without the internet. Child
  data stays on the device, is profile-scoped and is portable between
  architectures. No advertising or engagement tricks.
- **Learned input, not device logic.** Activities declare an interaction
  profile (pointer, directional, game, text and so on). The platform maps
  keyboard, mouse, touch and game controllers onto it.
- **Pre-readers first.** Symbols, colour, position, animation and prerecorded
  speech carry navigation; text appears when it is part of the learning.
- **Safe by construction.** Activities run sandboxed, removable media never
  autoruns, and installation is graphical and fails closed.

## Guides for families

- [Install Greia from a download and USB stick (Windows or Mac)](docs/user/INSTALL_FROM_USB.md)
- [Greia Parents: the on-device S + T shortcut and browser controls](docs/user/GREIA_PARENTS.md)

**No supported public installer is available yet.** These guides are release preparations, not an invitation to install a development image on a family computer. See the [guide home](docs/user/README.md) for the current starting point.

## Getting started (developers)

You need Python 3.11+, `git` and `make`.

```bash
git clone https://github.com/frozenpepper/Greia.git
cd Greia
python3 -m pip install -r requirements-dev.txt
```

Run the Shell and Activities in the Simulator, validate an Activity, and run
the full test and validation gate:

```bash
python3 tools/greia_simulator.py
PYTHONPATH=src python3 tools/validate_activity.py activities/painting
make verify
```

[CONTRIBUTING.md](CONTRIBUTING.md) explains the workflow, the checks and the
rules every change must respect. [SETUP.md](SETUP.md) covers the heavier
roles: building OS images, recording voices and operating test devices.

## Repository map

```text
src/greia_platform/    shared platform services and contracts
src/greia_launcher/    child Shell and Activity session orchestration
src/greia_parent/      Parent API server
src/greia_installer/   graphical installer
src/greia_simulator/   development-only Simulator composition
activities/            built-in Activities
activity_incubator/    Activities still in development
encyclopedia/          Encyclopedia content authoring sources
assets/                shared art, audio, fonts and catalogues
runtime/               runtime and policy declarations
build/                 image profiles, package sets, overlays and builders
tools/                 validation, Simulator, voice, release and device tools
vendor/parent-app/     pinned copy of the Greia Parents web client
website/               the public project website
docs/                  architecture, product, engineering and test docs
skills/                task guides for contributors and coding agents
tests/                 the unittest suite
```

## Documentation

| Start here for… | Read |
|---|---|
| Friendly parent and installer guides | [docs/user/README.md](docs/user/README.md) |
| Create an Activity | [docs/development/CREATE_AN_ACTIVITY.md](docs/development/CREATE_AN_ACTIVITY.md) |
| Add/translate a language (including Voice Studio) | [docs/development/ADD_A_GREIA_LANGUAGE.md](docs/development/ADD_A_GREIA_LANGUAGE.md) |
| Build an OS image (human guide + linked agent runbook) | [docs/development/BUILD_A_GREIA_IMAGE.md](docs/development/BUILD_A_GREIA_IMAGE.md) |
| How the docs fit together | [docs/DOCUMENTATION.md](docs/DOCUMENTATION.md) |
| Architecture overview | [docs/architecture/GREIA_ARCHITECTURE.md](docs/architecture/GREIA_ARCHITECTURE.md) |
| Architecture decisions | [docs/adr/](docs/adr/) (start with ADR 0012, the platform constitution) |
| Product requirements | [docs/product/](docs/product/) |
| Engineering practice | [docs/engineering/ENGINEERING_FOUNDATIONS.md](docs/engineering/ENGINEERING_FOUNDATIONS.md) |
| Writing an Activity | [skills/greia-activity-authoring/SKILL.md](skills/greia-activity-authoring/SKILL.md) |
| OS, Shell, Parent and installer work | [skills/greia-os-work/SKILL.md](skills/greia-os-work/SKILL.md) |
| Art and visual assets | [skills/greia-visual-authoring/SKILL.md](skills/greia-visual-authoring/SKILL.md) |
| Recorded speech | [VoiceEngine usage](tools/greia_voice_core/README.md) · [agent skill](skills/greia-voice-production/SKILL.md) |
| The Simulator | [docs/development/GREIA_ACTIVITY_SIMULATOR.md](docs/development/GREIA_ACTIVITY_SIMULATOR.md) |
| Current work and next steps | [HANDOVER.md](HANDOVER.md) |
| Lessons from earlier work | [docs/archive/README.md](docs/archive/README.md) |
| Rules for contributors and coding agents | [AGENTS.md](AGENTS.md) |

## Contributing, conduct and security

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) first,
follow the [Code of Conduct](CODE_OF_CONDUCT.md), and report security
problems privately as described in [SECURITY.md](SECURITY.md).

## License

Greia-owned source code is licensed under the
[Mozilla Public License 2.0](LICENSE). Documentation is intended for
CC BY 4.0, and third-party fonts and media keep their own licenses. The
licensing audit is still in progress: [NOTICE.md](NOTICE.md) lists the
default terms, the third-party material and the media whose provenance is
under review. The Greia name and distinctive logo are governed separately by the
[trademark guide](TRADEMARK.md) and
[full policy](docs/governance/LICENSING_AND_TRADEMARK.md). Greia may be
redistributed commercially under its open-source licenses, and sellers may
truthfully identify the software they include. Official product co-branding,
certification and endorsement are separate optional agreements; no
registration or certification programme is claimed yet.
