# Session 13 — Acer physical acceptance and portfolio closure

**Provider calls:** forbidden
**Prerequisite:** Session 12 simulator acceptance bound to the same source SHA
**Production edits:** forbidden; owner-controlled developer-image evidence/docs only

## Outcome

All ten Activities pass child-surface, pointer/keyboard, audio-fallback, persistence, lifecycle, and resource checks on the physical 1024×600 Acer-class reference machine. The plan closes only for this Activity portfolio and does not close R7, ARM parity, production display selection, boot, sandbox, controller, touch, or learning efficacy.

## Preconditions

- Obtain the owner's already-installed developer image and approved `greia-dev.local` access; do not install, repartition, image, reboot, or power off hardware in this session.
- Pull current `main`; require the Session 12 SHA and clean source tree. Read the agent operations remote-control boundary, responsive UI acceptance, current handover, and the developer machine's status before deployment.
- Record device model, RAM, display 1024×600, image/profile identity, deployed Git SHA, transport, locale, and whether each observation is remote screenshot/log or direct physical observation.

## Allowed files

```text
docs/reviews/2026-08-24_EARLY_LEARNING_ACTIVITY_ACER_ACCEPTANCE.md
docs/plans/2026-08-24_EARLY_LEARNING_ACTIVITY_EXPANSION/README.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
tmp/early-learning-activity-acer/**
```

## Forbidden changes

- No source/package/art/test edits, arbitrary privileged shell mutation, unattended install, disk write, root login, release SSH enablement, GitHub Actions, or unsupported physical evidence claim.
- Remote keyboard/pointer injection cannot prove controller/touch behavior. This session does not exercise or claim those inputs.

## Evidence and source decisions

The Acer reference is the extreme low-resource product floor. Remote commands provide repeatability, while display clarity, sound comfort, pointer response, keyboard entry, and absence of visible Linux surfaces require direct observation by the owner/operator. Current developer-image Xorg evidence is `PHYSICAL VISUAL REVIEW` of the provisional backend, not R7 production selection.

## Exact implementation

1. Run remote status and snapshot before deployment. Deploy each source package with `python3 tools/greia_remote.py deploy activities/<directory> --replace-system`; record the generated recovery backup for every built-in replacement. If replacement is unnecessary because the image already contains the exact SHA, record that identity instead.
2. Restart Greia through the bounded remote command, select a disposable explicit child profile through visible UI, and verify the ten distinct catalogue cards. No child-facing Linux console, desktop, terminal, or browser chrome may appear.
3. Repeat the exact Session 12 core concept path for all ten packages in Italian, then a shorter English launch/audio/text path for all speech/writing packages. Use a real physical pointer and keyboard for at least one run of every declared pointer/hybrid/text profile; remote injection may repeat but not replace those observations.
4. For Luci/Casa/Bottega/Specchi, observe quantity/number/unit/piece target clarity at normal viewing distance and verify pointer response during active motion. For Festa/Officina, listen directly for intelligible, comfortable, non-overlapping reviewed speech and verify the visible fallback once with audio disabled. For Posta/Tre Carte, type accented Italian plus one emoji, save, Home, relaunch, and verify grapheme-safe recovery. For Nanna/Morbidi, verify a three-year-old-sized target can be selected without precision dragging and no correctness pressure appears.
5. During each Activity capture one start, core, and end screenshot, one launcher screenshot, logs, and current status. Directly record visible/audio observations that screenshots cannot prove. Require protected Home to stop each Activity cleanly; force Home once during active animation and once during speech.
6. Measure each Activity after 60 seconds settled idle and during a 60-second representative active loop. Record process RSS and CPU samples once per second, input-to-visible-response from 30 high-frame-rate video trials, start request to READY from 10 launches, and residual Activity processes/audio after 20 launch/Home cycles across the portfolio.
7. Acceptance thresholds: no increasing RSS trend greater than 5 MiB between the first and twentieth same-Activity restart; zero orphan Activity/audio processes; settled idle median CPU at or below 5% of one core; active-loop 95th-percentile frame interval at or below 33.3 ms; input-to-visible-response 95th percentile at or below 50 ms; READY median at or below 2.0 seconds and maximum at or below 3.0 seconds. A threshold miss is a failed evidence row, not permission to edit in place.
8. Exercise storage caps by importing prepared source-valid fixtures through the Activity's public Storage test seam before deployment, then visibly verify each full-gallery/full-library sheet. Do not type 24 child artifacts manually and do not mutate `/var/lib/greia-profiles` with arbitrary shell commands.
9. Restore every replaced built-in package with `python3 tools/greia_remote.py restore <activity-id>` after evidence capture unless the owner explicitly elects to keep the tested packages. Verify launcher status and backups after restoration. Do not delete profile data without owner authorization.
10. Write the acceptance report with raw sample table, calculations, screenshot/video/log hashes, direct-observation signatures, failures, and exact evidence boundary. Only if every required row passes: mark this portfolio plan `COMPLETE`, append final evidence without rewriting history, update visual plan/resume and `HANDOVER.md`, and state that R7 plus other device/input/runtime/effectiveness evidence remains open.

## Tests

- Exact package/source/device/image identity, ten launcher cards, Italian core paths, English speech/writing paths, physical pointer/keyboard observations, and protected Home are recorded.
- Audio comfort/non-overlap, audio-off fallback, Unicode persistence, full-gallery sheets, no-pressure age-three paths, and absence of Linux UI pass.
- Resource, frame, latency, READY, restart/leak, screenshot, video, and log rows satisfy the numeric thresholds.
- Replacement backups are named; restoration or explicit owner keep decision is recorded.

## Local gate

```bash
python3 tools/greia_remote.py wait --timeout 180
python3 tools/greia_remote.py status
python3 tools/greia_remote.py snapshot tmp/early-learning-activity-acer/pre-deploy
```

Expected: the explicitly approved developer machine is reachable, reports the intended image/device state, and yields a pre-deploy snapshot without modifying release access policy.

## Cumulative gate

```bash
python3 tools/greia_remote.py status
python3 tools/greia_remote.py logs --service launcher --lines 500
PYTHONPATH=src:tests:. python3 -m unittest tests.test_early_learning_activity_portfolio -v
git diff --check
```

Expected: restored/approved device status is healthy, logs contain no Activity traceback or lifecycle leak, source test and diff check exit 0, and every physical report row is PASS.

## Stop conditions

- Hardware/access/image/source identity is unavailable, destructive installation would be required, or the owner has not approved the target developer machine.
- Any visual, audio, lifecycle, persistence, privacy, Linux-surface, or numeric threshold row fails; retain evidence and return to the owning session without marking this plan complete.

## Handoff

Return the standard packet plus hardware/image/source identity, deployment/backup/restore records, direct-observation checklist, raw resource/latency/READY samples, calculations, screenshot/video/log hash manifest, report link, exact open platform gaps, and the bounded `COMPLETE for Acer Activity portfolio only` claim.
