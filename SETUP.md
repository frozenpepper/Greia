# Greia Setup Index

**Status:** LIVING workstation / contributor / operator setup router  
**Reviewed:** 2026-10-30
**Canonical repository:** `frozenpepper/Greia`

This file answers one question: **what does this workstation/operator role need to read and install?** It does not replace the narrower manuals that own exact procedures. New contributors should start with `CONTRIBUTING.md`; this file covers the heavier roles.

## 1. Read before installing anything

From the repository root:

```text
AGENTS.md
SETUP.md
docs/DOCUMENTATION.md
CHANGELOG.md
docs/agents/README.md
```

Then read the task/role-specific skill below.

Do not install heavy model stacks, enable SSH, write removable media, add privileged host packages or perform destructive installation merely because a Greia tool exists.

## 2. Setup principles

1. **Use the active checkout.** Repository-local skills/docs are authoritative for that source state.
2. **Choose a role.** An Activity author does not need the raw-image build stack; an OS builder does not automatically need voice models.
3. **One voice-production boundary.** New prerecorded speech goes through `tools/greia_voice.py`; callers do not operate Chatterbox/MLX/Whisper/native TTS/FFmpeg directly.
4. **Authoring models are optional workstation tooling.** No normal narration TTS/ASR model belongs on the child device.
5. **Asset acceptance and runtime integration are separate.** A reviewed audio/image set may exist while a runtime resolver or final product placement is still pending.
6. **Keep machine-local material outside Git.** Venvs, model weights, caches, private keys, scratch audio, Simulator state and bulky evidence/build roots are local material.
7. **Do not silently auto-install privileged/heavy dependencies.** Inspect and obtain owner approval where required.
8. **Record exact SHA for retained evidence.** Source, Simulator, VM/image, provider+human and physical evidence are different lanes.
9. **Developer remote access is opt-in.** Normal/release Greia keeps SSH off.
10. **Setup success is not release evidence.** A tool starting successfully proves only its own setup scope.

## 3. Common bootstrap

```bash
git clone https://github.com/frozenpepper/Greia.git
cd Greia
python3 -m pip install -r requirements-dev.txt

git status --short
git rev-parse HEAD
python3 --version
git --version
make --version
```

When the role's host dependencies are available:

```bash
make verify
```

Run the gate on the exact checkout whose result you intend to retain; do not copy old PASS counts from documentation.

## 4. Repository-local task routers

```text
skills/greia-os-work/SKILL.md
skills/greia-activity-authoring/SKILL.md
skills/greia-visual-authoring/SKILL.md
skills/greia-voice-production/SKILL.md
```

Repository `skills/` files are canonical. Some workstations keep ignored installed
copies under `.agents/skills/`; refresh the affected skill directories from
`skills/` after changes (for example `rsync -a skills/greia-voice-production/ .agents/skills/greia-voice-production/`). Do not treat an older installed copy as a second authority.

For current testing/evidence routing use:

```text
docs/testing/HARDWARE_COMPATIBILITY_MATRIX.md
```

Use the public hardware and development guides for reproducible checks; maintain private session notes separately.

## 5. Activity creator — standard profile

The practical human overview is [Create an Activity](docs/development/CREATE_AN_ACTIVITY.md). Agent authors should still follow the current source-owned [Activity skill](skills/greia-activity-authoring/SKILL.md); this page only routes tooling installation.

Read:

```text
skills/greia-activity-authoring/SKILL.md
docs/development/GREIA_ACTIVITY_SIMULATOR.md
docs/development/GREIA_ACTIVITY_TEXT_TYPOGRAPHY_AND_EMOJI.md
docs/product/ACTIVITY_INPUT_STANDARDS.md
docs/product/ACTIVITY_SYSTEM_NAVIGATION.md
```

Typical host needs:

```text
Python 3.11+
requirements-dev.txt (pygame, Pillow, zstandard; regex optional)
Tk support for Simulator control plane
make
```

Start the Simulator:

```bash
python3 tools/greia_simulator.py
```

Validate one Activity:

```bash
PYTHONPATH=src python3 tools/validate_activity.py activities/<activity-directory>
```

If new prerecorded speech is required, switch to the Voice Production profile rather than invoking a TTS backend directly.

## 6. Visual author — optional extension

Read:

```text
skills/greia-visual-authoring/SKILL.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
docs/design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
docs/design/GREIA_SCENE_COMPOSITION_RUNTIME.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
```

Build/validate declared visual renditions:

```bash
make visual-assets
make visual-assets-check
```

Do not infer physical readability/performance from desktop rendering alone.

## 7. Voice Production Engine / authoring Voice Studio

**Same TTS and ASR on macOS, Windows and Linux:** generate with
`openbmb/VoxCPM2` (PyTorch CPU/CUDA/MPS) and review with NVIDIA
`parakeet-tdt-0.6b-v3` (ONNX Runtime). This is authoring-time software only.

1. Read [the shared setup](docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md)
   and the [Windows](docs/agents/voice-platforms/WINDOWS.md),
   [macOS](docs/agents/voice-platforms/MACOS.md) or
   [Linux](docs/agents/voice-platforms/LINUX.md) guide.
2. Install both models once with `tools/setup_voice_models.py` using a
   host-specific voice-authoring Python environment outside the repository.
3. Run `tools/greia_voice.py doctor`; inspect **both** the VoxCPM2 provider
   and Parakeet v3 status. The command never downloads models or creates audio.
4. Generate using `tools/greia_voice.py`; `verification=auto` runs Parakeet
   by default, and the user can disable it with `--verification off`.
   A WARN or unavailable Parakeet is a human-review note, not an automatic
   rejection in normal mode.
5. Human listening determines acceptance. Keep new output and receipts in
   external review staging; do not replace already approved audio or receipts
   during setup.

The older Mac VoxStage worker uses an MLX/8-bit build of **the same VoxCPM2
model family**. It remains selectable explicitly with
`--character-provider voxstage`, not a requirement on Windows/Linux.
Other historical models, provider evidence and frozen corpus plans are not
relabeled. Greia's canonical v0.3 voice masters are not regenerated.

[Voice production skill](skills/greia-voice-production/SKILL.md) ·
[VoiceEngine CLI](tools/greia_voice_core/README.md) ·
[Canonical voice design](docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md)

## 8. Parent App developer

For parent-facing usage, rather than client development, use [Greia Parents](docs/user/GREIA_PARENTS.md). The on-device **S + T** shortcut and browser connection belong in that simple guide.

The browser client source is in this repository, under `parent-app/` (no second checkout). Read:

```text
parent-app/README.md
parent-app/AGENTS.md
docs/architecture/PARENT_APP_SOURCE_INTEGRATION.md
docs/architecture/GREIA_PARENT_MANAGEMENT.md
docs/product/PARENT_MANAGEMENT.md
docs/adr/0022-parent-management-api-client-pairing-and-privilege-boundary.md
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
```

Client tests need Node.js >= 18 (`make parent-app-test`, also part of `make verify`, skipped when Node is absent). After committing `parent-app/`, run `python3 tools/update_parent_client_pin.py` and commit the pin, manifest and overlay it rewrites.

Installed Greia serves the Parent browser and API over self-signed HTTPS on LAN port 8766; the local S+T Parent panel uses loopback-only HTTP at 127.0.0.1:8767. The on-device TLS certificate is generated with OpenSSL (included in the image base package set). Browser certificate warnings on first visit are expected. See the Parent user guide and the exact transport acceptance note in docs/testing.

The browser client must not invent an SSH/shell fallback for an unavailable semantic Parent API feature.

## 9. Developer-device operator

Use only with an explicit developer image.

Read:

```text
docs/agents/README.md
docs/development/GREIA_DEVELOPER_BOOT_DIAGNOSTICS.md
docs/development/GREIA_DEVELOPER_BOOT_DIAGNOSTICS.md
```

Typical operator flow:

```bash
python3 tools/greia_remote.py wait --timeout 180
python3 tools/greia_remote.py status
python3 tools/greia_remote.py screenshot out/screen.png
```

Never commit the operator private key. Never turn developer SSH into a normal/release dependency.

For acceptance, select tests appropriate to the changed subsystem and record exact commands, device and commit in the pull request.

## 10. OS image / installer builder

For an overview, see [Build a Greia image](docs/development/BUILD_A_GREIA_IMAGE.md); agents following a human-authorized image build should use the linked [image-building agent runbook](docs/agents/GREIA_IMAGE_BUILD_AGENT.md). The specialist manuals below remain authoritative for exact commands. For ordinary Windows/Mac USB writing and installation, use [the nontechnical guide](docs/user/INSTALL_FROM_USB.md) instead.

Not required for ordinary Activity work.

Read:

```text
skills/greia-os-work/SKILL.md
skills/greia-os-work/BOOT.md
docs/agents/README.md
docs/engineering/boot/INSTALLER_IMAGE_CREATION_AND_BOOT.md
docs/engineering/BOOT_PIPELINE_AGENT_GUIDE.md
```

Raw-image/current backend evidence requires an owner-controlled compatible Linux environment with root access and the prerequisites named by the exact build/test procedure.

Developer target entry point currently includes:

```bash
sudo bash build/build-developer-image.sh out
```

Reference-Acer USB front door (diagnostic developer image, or the quiet release candidate):

```bash
sudo bash tools/build-and-flash-development-usb.sh legacy-x86-i686-dev /dev/sdX
sudo bash tools/build-and-flash-development-usb.sh legacy-x86-i686-rc /dev/sdX ./out --operator-key ~/greia-operator.pub
```

The release-candidate runbook (frozen SHA, operator public key, USB identification, required PASS lines, pre-build gates G1–G11) is `docs/engineering/boot/INSTALLER_IMAGE_CREATION_AND_BOOT.md` §13. Boot console policy (`diagnostic` vs `quiet`, hidden verbose paths) is §7 there.

Do not add destructive disk/removable-media writes to a generic setup helper.

## 11. Setup map

| Need | Entry point |
|---|---|
| Current implementation/evidence | `CHANGELOG.md` |
| Current testing route | `docs/testing/HARDWARE_COMPATIBILITY_MATRIX.md` |
| Repository/agent operations | `docs/agents/README.md` |
| OS/platform work | `skills/greia-os-work/SKILL.md` |
| Activity authoring | `skills/greia-activity-authoring/SKILL.md` |
| Activity Simulator | `docs/development/GREIA_ACTIVITY_SIMULATOR.md` |
| Visual authoring | `skills/greia-visual-authoring/SKILL.md` |
| Visual architecture | `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` |
| Voice production | `skills/greia-voice-production/SKILL.md` |
| Voice engine quick use | `tools/greia_voice_core/README.md` |
| Voice architecture | `docs/architecture/GREIA_VOICE_PRODUCTION_ENGINE.md` |
| Voice policy/status | `docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md` |
| Parent source/API | `docs/architecture/GREIA_PARENT_MANAGEMENT.md` |
| Developer remote | `docs/agents/README.md` |
| Installer/image creation | `docs/engineering/boot/INSTALLER_IMAGE_CREATION_AND_BOOT.md` |
| Public-release gate | `NOTICE.md` |

## 12. Current readiness ledger

| Surface | Current state |
|---|---|
| Repository source verification | `make verify`; execute on exact current checkout before claiming PASS |
| Activity Simulator | implemented/documented; desktop development dependencies required |
| Developer remote | implemented for explicit developer images only |
| Voice Production Engine | implemented/canonical; provider readiness is workstation-specific and reported by `doctor` |
| Character production (all six) | VoxCPM2 via PyTorch across Windows/macOS/Linux; VoxStage is explicit historical Mac alternative |
| Pedagogical production | VoxCPM2 via existing Leo reference; no OS-specific TTS default |
| ASR verification | Parakeet-TDT v3 via ONNX across platforms, enabled in auto mode; owner can turn off |
| Shared reactions | **180 EN/IT recordings were owner-accepted in the v0.2 baseline**; selected Dani/Momo/Tito rows included in the 2026-10-21 v3 corpus replacement are now pending fresh listening, with prior bytes/receipts backed up externally |
| Character introductions | **12 EN/IT introductions were owner-accepted in the v0.2 baseline**; selected Dani/Momo/Tito introductions included in the 2026-10-21 v3 replacement are now pending fresh listening; product placement separate |
| Shared runtime resolver | separate integration task where still pending |
| Public-source legal/provenance gate | root entry points added 2026-10-16 (`LICENSE`, `NOTICE.md`, `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`); audit still pending, see `NOTICE.md` |

## 13. Maintenance rule

When a change materially alters a required tool, role, external repository, connection path, Simulator prerequisite, voice workflow/provider, image-build prerequisite or setup verification command:

1. update the narrower owner document;
2. update this router if setup/navigation changed;
3. update `AGENTS.md` only if repository-wide mandatory behavior changed;
4. keep private maintainer continuation records outside the public repository;
5. preserve evidence scope honestly.

A future setup assistant may automate role bootstrap, but it must consume rather than replace these authorities and must never silently install heavy/privileged dependencies.
