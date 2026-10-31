# Make an Activity for Greia

You can create your own Greia game, drawing tool, puzzle or learning experience. You do **not** need to build the whole operating system first: develop and play-test in Greia's desktop Simulator.

This is a friendly route into the tools, not a replacement for the detailed [Activity-creation skill](../../skills/greia-activity-authoring/SKILL.md). If you use a coding agent, **give it that skill** and let it load the focused companion files as needed. It describes the actual Greia lifecycle, creative/design rules, testing, localization and packaging.

## 1. Start with the child's experience

Before writing code, answer three questions: **What does the child do? What will they learn or explore? How will they know what to try without reading instructions?**

A good first Activity has a very small interaction loop: see a thing, try something, receive friendly feedback, and try again. Keep the first action obvious. Do not make children navigate tiny menus, read paragraphs or perform precise clicks.

Greia owns the Home/Back system controls. Use its shared Activity UI controls, art and feedback conventions, rather than creating a separate navigation scheme. The [design and teaching companion](../../skills/greia-activity-authoring/DESIGN_AND_TEACHING.md) and [pre-reader UX guide](../../skills/greia-activity-authoring/PRE_READER_UX.md) go deeper.

## 2. Prepare your computer

From the [Greia source repository](https://github.com/frozenpepper/Greia), install:

- **Python 3.11 or newer**, with Tk support if using the Simulator's graphical control interface.
- `git` and `make`.
- The repository's tested development packages (`requirements-dev.txt`), including **pygame**, **Pillow** and **zstandard**.
- A coding editor of your choice.

For a typical Python development workstation:

```bash
git clone https://github.com/frozenpepper/Greia.git
cd Greia
python3 -m pip install -r requirements-dev.txt
python3 tools/greia_simulator.py
```

If setup fails, use [SETUP.md's Activity creator profile](../../SETUP.md#5-activity-creator--standard-profile) and the [Simulator instructions](GREIA_ACTIVITY_SIMULATOR.md). **Do not install voice models** merely to work on a game; most Activities can reuse Greia's existing audio.

## 3. Give the Activity its own directory

Each Activity has a folder containing its `activity.toml` manifest, Python entry code and any Activity-owned resources. Use an existing small Activity as a working example rather than inventing manifest keys. A built-in source lives under `activities/<activity-id>/`; an external Activity can be developed outside that directory and loaded in the Simulator.

The Activity should use Greia's shared SDK for input, presentation, storage, locale, audio and events. It must not read other children's files, bypass Home, open a second package manager or depend on its own virtual environment on the Greia computer.

For visuals, start with [Greia's visual authoring skill](../../skills/greia-visual-authoring/SKILL.md) and shared catalogue. For buttons, prompts and completion feedback, follow [the Activity control kit](../../docs/adr/0037-shared-activity-control-kit.md). Design for the small **1024×600** reference netbook and check tighter **800×480** layouts too.

## 4. Add words and sounds the Greia way

Greia's current selectable system languages are **English, Italian, Spanish and French**. If your Activity has text, give the same semantic keys to its `locales/en.json`, `it.json`, `es.json` and `fr.json`. For prerecorded cues, use stable IDs with files such as `assets/audio/en/<cue>.wav` and `assets/audio/it/<cue>.wav`.

Use the shared `greia_platform.localization` resource resolver, not handwritten checks of language folders. The resolver chooses the selected language, then a relevant base language, then English, then silence if no recording exists. **Required spoken instructions should have real approved clips in each language advertised by your Activity.**

Greia already has shared character reactions, common picture words and numbers. Reuse them rather than copying the same recordings into every game.

### When you need a new voice line

Greia uses **prerecorded audio produced during Activity creation**. Nothing runs a heavy voice model on the child's computer. This helps Greia remain usable offline and on older hardware, while allowing human review of pronunciation and acting before children hear it.

The one production entry point is:

```bash
python3 tools/greia_voice.py doctor
```

This checks whether the optional voice-production workstation is ready. For actual generation, follow [VoiceEngine usage](../../tools/greia_voice_core/README.md) and [the voice production skill](../../skills/greia-voice-production/SKILL.md). The current authoring route uses the shared VoxStage/VoxCPM2 worker for natural character voices; pronunciation-authoritative **letters, syllables and phonics** use the separate `pedagogical_speech` route. Dani has a `dani_system_speech` route too.

**Why the separation?** A charming character voice is suitable for guidance and storytelling, but the exact target sound matters when teaching pronunciation. The canonical engine also manages short-cue extraction, verification, retries and output receipts. Don't call TTS, ASR, audio-cutting or FFmpeg backends directly from Activity code or an Activity-owned script.

Generate new takes into a separate review folder, **listen to them**, and only then integrate accepted files. Automated checks are useful screening, never human acceptance. Do not overwrite already accepted audio because a model generates something new.

The practical [Activity voice companion](../../skills/greia-activity-authoring/VOICE_GENERATION.md) explains speaker selection, cue IDs, shared resources, review and wiring. Existing accepted sounds need no new model install.

## 5. Test while you build

Start the real Greia Simulator early:

```bash
python3 tools/greia_simulator.py
```

For a built-in Activity, validate its directory:

```bash
PYTHONPATH=src python3 tools/validate_activity.py activities/my_activity
```

Run an Activity through the real headless Simulator (replace `my_activity` with your folder):

```bash
PYTHONPATH=src python3 tools/headless_greia_simulator.py \
  --activity-dir activities/my_activity \
  --workspace-dir /tmp/greia-sim-my_activity \
  --locale en --viewport 1024x600 \
  --survival-seconds 12 \
  --screenshot-prefix /tmp/greia-my_activity-en
```

Repeat with a meaningful key/click, in the other supported languages, and at 800×480. The headless test checks real launch/integration, but **does not prove the game is enjoyable or understandable**. Finally open the GUI Simulator, use the normal Activity list (or **Load Activity Folder…** for an external source) and play it. The [Simulator workflow](../../skills/greia-activity-authoring/SIMULATOR_WORKFLOW.md) and [launch acceptance checklist](../../skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md) cover the details.

## 6. Make a portable Activity file

Greia's distribution format is **`.greiaactivity`**. It is a ZIP file containing the **contents of the Activity directory at the ZIP root**. In particular, `activity.toml` must be at the archive root, not inside an extra folder.

After validation and GUI review, this Python example packages a source folder. Replace the path and output name:

```bash
python3 - <<'PY'
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

activity = Path("activities/my_activity")
output = Path("/tmp/my_activity.greiaactivity")
if not (activity / "activity.toml").is_file():
    raise SystemExit("Activity manifest missing")
with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
    for file in sorted(activity.rglob("*")):
        if file.is_symlink():
            raise SystemExit(f"Unsupported symlink: {file}")
        if not file.is_file():
            continue
        if "__pycache__" in file.parts or file.name in {".DS_Store"} or file.suffix == ".pyc":
            continue
        archive.write(file, file.relative_to(activity).as_posix())
print(output)
PY
```

The archive is only **a candidate**. Verify it with the Simulator's **Install Activity Package…** workflow, which exercises the package installation/validation path. A renamed arbitrary ZIP is not a validated Activity. Read the [package format contract](../architecture/GREIA_ACTIVITY_PACKAGE_FORMAT.md) before distributing it.

## 7. Install it on Greia

When the installed Greia device **advertises Activity installation as available** through its management capabilities, a parent can use the browser **Greia Parents → Activities → Install Activity**, select a `.greiaactivity` file and follow the confirmation. The device validates the contents and activates an accepted new package. Installed Activities appear through the normal child experience according to each child's visibility rules.

If ordinary **Install Activity** is unavailable, use the **Simulator** for
normal development or an expressly authorized developer-only deployment
procedure from agent operations (internal record archived) for
hardware testing. A device that advertises `system.update.package.install`
also supports typed `.greia_update` packages for selected Parent-source
Activity packages through **Greia Parents → System → Updates → Upload &
install**. That path retains Parent-source trust and requires the installed
software-update bootstrap; it does not promote an Activity to built-in. See
the [software-update package guide](GREIA_SOFTWARE_UPDATE_PACKAGES.md) for the
builder commands and offline/reconnect behavior. Never copy arbitrary code
into built-in Activity folders on a child's machine.

## Useful references

- [Activity creation skill](../../skills/greia-activity-authoring/SKILL.md) — the canonical practical guide for agents and serious authors.
- [Simulator workflow](../../skills/greia-activity-authoring/SIMULATOR_WORKFLOW.md) — correct execution and visual review.
- [Voice for Activities](../../skills/greia-activity-authoring/VOICE_GENERATION.md) · [VoiceEngine usage](../../tools/greia_voice_core/README.md) — spoken cues and review.
- [Visual authoring](../../skills/greia-visual-authoring/SKILL.md) — art and shared assets.
- [Package format](../architecture/GREIA_ACTIVITY_PACKAGE_FORMAT.md) — what to ship.
- [Setup index](../../SETUP.md) — optional host/voice/builder environments.
