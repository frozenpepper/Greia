# Agent index: which manual for which task

Read in this order, then pick the row that matches your task.

1. [AGENTS.md](../../AGENTS.md): rules and product contracts. Always.
   The owner's core agents also read [CORE_TEAM.md](CORE_TEAM.md).
2. [SETUP.md](../../SETUP.md): what to install for your role.
3. [HANDOVER.md](../../HANDOVER.md): current state and next step.
4. [GREIA_AGENT_OPERATIONS.md](GREIA_AGENT_OPERATIONS.md): how to work in this
   repo and on test hardware.

When two documents disagree, [DOCUMENTATION.md](../DOCUMENTATION.md) says
which one owns the fact. Do not pick the convenient one.

## Skills (task routers in `skills/`)

| Task | Load |
|---|---|
| Create, change, validate or package an Activity | [greia-activity-authoring](../../skills/greia-activity-authoring/SKILL.md) |
| OS, Shell, Parent API, installer, simulator, build or hardware services | [greia-os-work](../../skills/greia-os-work/SKILL.md) |
| Parent web app (phone/browser client) | [parent-app/README.md](../../parent-app/README.md), [parent-app/AGENTS.md](../../parent-app/AGENTS.md), then [PARENT_APP_SOURCE_INTEGRATION.md](../architecture/PARENT_APP_SOURCE_INTEGRATION.md) |
| Boot, initramfs, GRUB, first boot, recovery | [BOOT.md](../../skills/greia-os-work/BOOT.md) (after greia-os-work) |
| Art, icons, scenes, characters, Activity visuals | [greia-visual-authoring](../../skills/greia-visual-authoring/SKILL.md) |
| Add, translate, stage or retire a language | [greia-language-expansion](../../skills/greia-language-expansion/SKILL.md) |
| New recorded speech (characters, narration) | [greia-voice-production](../../skills/greia-voice-production/SKILL.md) |

How the skills are structured: [skills/README.md](../../skills/README.md).
Activity work also has companion files in `skills/greia-activity-authoring/`
(design, pre-reader UX, simulator workflow, launch acceptance, achievements,
microphone, voice and more). The skill names the one you need.

## Manuals in `docs/agents/`

| Task | Read |
|---|---|
| Build an installer image | [GREIA_IMAGE_BUILD_AGENT.md](GREIA_IMAGE_BUILD_AGENT.md) (human guide: [BUILD_A_GREIA_IMAGE.md](../development/BUILD_A_GREIA_IMAGE.md)) |
| Set up a voice production workstation | [GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md](GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md) |
| Review generated speech automatically | [GREIA_AUTOMATED_VOICE_REVIEW.md](GREIA_AUTOMATED_VOICE_REVIEW.md) |
| Record the shared character utterance library | [GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md](GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md) |
| Use the Chatterbox voice provider (alternative provider only) | [GREIA_CHATTERBOX_PRODUCTION_FIELD_GUIDE.md](GREIA_CHATTERBOX_PRODUCTION_FIELD_GUIDE.md) |
| Cut spoken words out of existing recordings | [GREIA_SPOKEN_CARRIER_EXTRACTION.md](GREIA_SPOKEN_CARRIER_EXTRACTION.md) |
| Regenerate the existing speech corpus (owner-authorized work order) | [GREIA_VOICE_CORPUS_REGENERATION.md](GREIA_VOICE_CORPUS_REGENERATION.md) |
| Finish the remaining recordings (owner-authorized work order) | [GREIA_NATURAL_VOICE_COMPLETION.md](GREIA_NATURAL_VOICE_COMPLETION.md) |

## Other documents agents often need

| Task | Read |
|---|---|
| Code structure, classes, extension points | [ENGINEERING_FOUNDATIONS.md](../engineering/ENGINEERING_FOUNDATIONS.md) |
| Speed and memory on old machines | [GREIA_PERFORMANCE_BEST_PRACTICES.md](../engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md) |
| Boot and display pipeline | [BOOT_PIPELINE_AGENT_GUIDE.md](../engineering/BOOT_PIPELINE_AGENT_GUIDE.md), [engineering/boot/](../engineering/boot/) |
| Which test or evidence procedure applies | [LOCAL_AGENT_START_HERE.md](../testing/LOCAL_AGENT_START_HERE.md) |
| Update and A/B acceptance | [GREIA_UPDATE_RELEASE_ACCEPTANCE.md](../testing/GREIA_UPDATE_RELEASE_ACCEPTANCE.md) |
| Hardware support claims | [HARDWARE_COMPATIBILITY_MATRIX.md](../testing/HARDWARE_COMPATIBILITY_MATRIX.md) |
| Visual test evidence | [VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md](../testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md) |
| Release state and blockers | [FIRST_PUBLIC_RELEASE_EXECUTION.md](../release/FIRST_PUBLIC_RELEASE_EXECUTION.md), [GREIA_PUBLIC_RELEASE_READINESS.md](../release/GREIA_PUBLIC_RELEASE_READINESS.md) |
| Run the Simulator | [GREIA_ACTIVITY_SIMULATOR.md](../development/GREIA_ACTIVITY_SIMULATOR.md) |
| Find any other document | [docs/README.md](../README.md) |

## Before you finish

- Run `make verify` and say where each check ran (desktop, Simulator, VM or device).
- Update the document, skill or ADR your change made wrong.
- Core-team agents: update HANDOVER.md and the active plan, as [CORE_TEAM.md](CORE_TEAM.md) requires. Outside agents: follow "Sharing what you found" in AGENTS.md.
- Do not claim a result that did not run on the stated commit.
