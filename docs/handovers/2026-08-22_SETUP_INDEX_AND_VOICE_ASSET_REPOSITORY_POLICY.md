# Greia Setup Index and Canonical Voice Asset Repository Policy — Handover

**Date:** 2026-08-22  
**Scope:** documentation/setup architecture only; no host package installation or runtime verification executed

## Completed

1. Added root `SETUP.md` as the canonical workstation, agent and operator setup router.
2. Added role-based setup profiles for:
   - Activity creation;
   - visual authoring;
   - local voice production;
   - Parent App development;
   - developer-device remote operation;
   - privileged OS/image building.
3. Indexed the existing setup-relevant manuals, skills, commands and external Parent App repository.
4. Added a readiness ledger that distinguishes documented/implemented surfaces from missing automation.
5. Defined the next setup-system implementation target as a non-destructive `tools/greia_setup.py` profile inspector/verifier.
6. Updated root `AGENTS.md` so every agent must read `SETUP.md` before installing or configuring Greia toolchains, skills, simulator dependencies, Parent App work, voice backends, remote-control environments or image-build hosts.
7. Corrected canonical voice asset policy:
   - WAV source masters and FLAC production anchors are canonical private-project repository assets;
   - unresolved public redistribution licensing is a separate governance concern;
   - an undocumented external owner pack is no longer the intended source-of-truth mechanism;
   - a fresh clone missing the bytes is explicitly incomplete for voice production.

## Current voice asset blocker

Current GitHub `main` contains:

```text
assets/audio/characters/canonical/v0.1/README.md
assets/audio/characters/canonical/v0.1/manifest.toml
assets/source/audio/character-voice-masters/v0.1/README.md
```

It does not contain the registered binaries:

```text
assets/audio/characters/canonical/v0.1/lilli-reference-v1.flac
assets/audio/characters/canonical/v0.1/leo-reference-v1.flac
assets/audio/characters/canonical/v0.1/flash-reference-v1.flac
assets/audio/characters/canonical/v0.1/tito-reference-v1.flac
assets/audio/characters/canonical/v0.1/momo-reference-v1.flac

assets/source/audio/character-voice-masters/v0.1/lilli-source-v1.wav
assets/source/audio/character-voice-masters/v0.1/leo-source-v1.wav
assets/source/audio/character-voice-masters/v0.1/flash-source-v1.wav
assets/source/audio/character-voice-masters/v0.1/tito-source-v1.wav
assets/source/audio/character-voice-masters/v0.1/momo-source-v1.wav
```

There is no repository size or `.gitignore` blocker for these files. This session had only their manifest metadata and SHA-256 values, not the binary bytes. Hashes cannot reconstruct audio.

## Required next voice action

From an authorized working copy that still contains the actual reviewed WAV/FLAC files:

1. verify every path, byte count, duration/format and SHA-256 against `manifest.toml`;
2. add the ten files to Git;
3. inspect `git status --short` and staged file sizes;
4. commit them as canonical private-project voice assets;
5. verify a clean clone contains and hashes all registered files;
6. run the local voice smoke procedure from `docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md` on an approved authoring machine;
7. record public-release licensing separately before making the repository or assets public.

Do not regenerate approximations merely to satisfy filenames.

## Required next setup-system action

Implement the first non-destructive setup assistant tranche:

```text
tools/greia_setup.py
```

Recommended initial scope:

```text
inspect host
select explicit role profile
report available/missing commands
verify repository-local skill paths
verify optional canonical asset manifests
print exact narrower setup documents
emit JSON + human report
make no privileged changes
```

Only after that inspector is reviewed should installation actions be considered. Any future installer must require explicit approval before package-manager/root changes and must never enable SSH or perform disk writes as an incidental setup step.

## Commits

```text
cb421f99ffca08df530ce239c3a6d59e2db2f009  docs(setup): add role-based Greia setup index
ac0a8765d37cc18ce845bda743982897cd6b348b  docs(setup): make SETUP.md mandatory from AGENTS
d8f076d978a2df40f80f912f376fea74b5796045  docs(voice): make canonical anchors repository-owned
c8dbf941f6dcd5dc4bbf1ab1bd2513dfaf6ff484  docs(voice): keep source masters in canonical repository
```

## Verification status

Documentation/source inspection only. No `make verify`, simulator, Parent App test, voice generation, image build or physical-device command was executed in this session.
