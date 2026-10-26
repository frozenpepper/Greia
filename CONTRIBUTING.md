# Contributing to Greia

Thanks for your interest in Greia. It is a child-first educational operating
system for very low-end and ARM hardware, and it is still pre-release: there
is no supported binary release yet, and much of the work is about making the
platform safe and solid before families use it.

This guide covers how to set up a checkout, how to run the checks, and what a
good change looks like. Repository-wide rules for both humans and coding
agents are in [AGENTS.md](AGENTS.md); the documentation map is
[docs/DOCUMENTATION.md](docs/DOCUMENTATION.md).

## Ground rules that shape every change

These come from the product contracts in `AGENTS.md`. A change that breaks
one of them will not be merged, however useful it is otherwise.

- **No Linux surface in the child path.** No terminal, desktop, login prompt,
  window manager, file manager or browser chrome may ever appear to a child.
- **Activities are the universal abstraction.** Games, tools and stories are
  Activities that run under platform-owned lifecycle, storage, permissions and
  input. Platform Home is always present and cannot be hidden or replaced by
  an Activity.
- **The first-generation Acer Aspire One is the floor** (Intel Atom, at most
  1 GB of RAM, a 1024×600 screen). Raspberry Pi 400/500 are first-class targets. Caches,
  histories and queues must be bounded; avoid per-frame decoding, font
  construction or filesystem work.
- **Offline first.** Core use, saves and parent management work without the
  cloud. Child data is profile-scoped and portable across architectures.
- **No private dependencies in Activities.** One curated Python runtime;
  Activities do not install, download or bundle packages.

## Setting up

You need Python 3.11 or newer, `git` and `make`. The Activity Simulator also
needs Tk support in your Python build.

```bash
git clone https://github.com/frozenpepper/Greia.git
cd Greia
python3 -m pip install -r requirements-dev.txt
```

Start the Activity Simulator. It runs the real Greia Shell and platform
services against a synthetic development device:

```bash
python3 tools/greia_simulator.py
```

Building OS images, installers and voice recordings needs extra tooling and
is not required for most contributions. [SETUP.md](SETUP.md) lists what each
role needs.

## Running the checks

The full gate is:

```bash
make verify
```

It runs the fast test lane, validates the project and every Activity, checks
shell-script syntax and measures the source footprint. `make verify-full` adds
the heavy end-to-end evidence suites listed in `tests/suite_lanes.py` (x8 QEMU
rigs, install memory gates, whole-repository sweeps). While you work, run the
modules you touched:

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_profiles.py' -v
```

Validate a single Activity:

```bash
PYTHONPATH=src python3 tools/validate_activity.py activities/<activity-directory>
```

Activity validation deliberately rejects cached bytecode inside Activity
folders; `make clean-bytecode` removes it.

Desktop tests and the Simulator do not prove behaviour on real hardware:
sandboxing, the production display session, boot, installation and Acer/Pi
performance need their own evidence. When you describe what you tested, say
where it ran.

## Documentation and repository cleanup

Before presenting new instructions as current, review `docs/DOCUMENTATION.md` and run `python3 tools/audit_repository_docs.py --scope maintained` on a full checkout. Keep family guides short, use `docs/development/ADD_A_GREIA_LANGUAGE.md` for language packs, and link current procedures instead of copying dated test transcripts into living guides. The audit checks relative Markdown links across documentation; it does not verify technical truth or require a runtime image build.

Do not commit generated test videos, screenshots, temporary outputs or local model caches. Do not delete source tests, provenance/accepted voice assets, unresolved A/B evidence or historical records still referenced by current plans merely because they look old. Old unneeded captures can be removed from the working tree after verifying references; Git history retains them. For the cleanup rules and historical archive, see `docs/DOCUMENTATION.md` §7.

## Making a change

- **Find the owner first.** `docs/DOCUMENTATION.md` maps each concern to the
  source file that owns it. Architecture decisions live in `docs/adr/`;
  product requirements in `docs/product/`.
- **Follow the engineering foundations.** Read
  [docs/engineering/ENGINEERING_FOUNDATIONS.md](docs/engineering/ENGINEERING_FOUNDATIONS.md):
  cohesive classes for real domain concepts, narrow protocols at genuine
  variation points, explicit ownership and cleanup of every long-lived
  resource, and no parallel copies of existing platform services.
- **Writing an Activity?** Start at
  [skills/greia-activity-authoring/SKILL.md](skills/greia-activity-authoring/SKILL.md).
  Use the shared Activity control kit (ADR 0037) instead of hand-drawn
  controls, and declare an interaction profile rather than reading devices.
- **Working on the OS, Shell, Parent API or installer?** Start at
  [skills/greia-os-work/SKILL.md](skills/greia-os-work/SKILL.md).
- **Art and visual assets** follow
  [skills/greia-visual-authoring/SKILL.md](skills/greia-visual-authoring/SKILL.md)
  and `docs/design/GREIA_SVG_AUTHORING_RULES.md`.
- **Speech.** New prerecorded speech goes through `tools/greia_voice.py` (see
  [skills/greia-voice-production/SKILL.md](skills/greia-voice-production/SKILL.md)).
  Committed recordings are owner-reviewed; do not regenerate them.
- **Adding, translating or maintaining a language?** Start at
  [Add a Greia Language](docs/development/ADD_A_GREIA_LANGUAGE.md)
  and [the language agent skill](skills/greia-language-expansion/SKILL.md).
  Scaffold UI and Activity JSON, translate, record/review voice assets, run the
  staged checker, and add the locale's manifest only after owner acceptance.
  Installer and OS language choosers use the manifest directory; no new Python
  language list is needed. Existing EN/IT/ES/FR remain released.
- **Add or update tests** for behaviour you change. Prefer tests that exercise
  behaviour over tests that search source text.
- **Update the documents your change makes wrong**: the relevant skill,
  `docs/DOCUMENTATION.md` owner map, ADR or product document.

## Pull requests

1. If you have access to the private Greia repository, create your own branch for the contribution (or use a private fork if GitHub permits it). External contributors must not commit directly to `main`.
2. Keep each pull request focused on one problem.
3. In the description, say what changed, why, and exactly which checks you
   ran and where (desktop, Simulator, VM or which device).
4. Run `make verify`, or at least the affected test modules, before asking
   for review.

GitHub-hosted Actions are manual-only in this repository; maintainers run
verification locally or on owner-approved machines.

## Repository approval policy

External contributors have access to the full repository so they can run Greia and test their work. They submit pull requests for owner review; `@frozenpepper` is named in `.github/CODEOWNERS`.

**Review rules and technical enforcement are different.** The owner asks external contributors to use branches and pull requests, and `.github/CODEOWNERS` documents the intended reviewer. On a private repository under a free personal GitHub account, branch protection may not be enforceable; collaborators who receive write access can technically push directly to `main` even though project policy forbids it. Only grant private write access to collaborators you trust to follow the PR workflow. If the repository's plan/settings later allow branch protection, the owner can enforce PR approval there. No paid subscription or repository transfer is a prerequisite for contributing under the present trust-based workflow.

## Coding agents

AI-assisted contributions are welcome. `AGENTS.md` is written for coding
agents as well as people, and the `skills/` directory holds task routers that
agents can load. You remain responsible for everything you submit: run the
checks, and do not claim results that did not execute.

## Licensing of contributions

Contributions are accepted under the license that already governs the file
or material you change: MPL-2.0 for Greia-owned source code, CC BY 4.0 for
documentation, as described in [NOTICE.md](NOTICE.md). There is no
contributor license agreement. Only submit work you have the right to
contribute, and do not paste third-party code, fonts, images or audio into
the repository without stating their origin and license.

## Conduct and security

Everyone taking part is expected to follow the
[Code of Conduct](CODE_OF_CONDUCT.md). Please report security problems
privately as described in [SECURITY.md](SECURITY.md), not in public issues.
