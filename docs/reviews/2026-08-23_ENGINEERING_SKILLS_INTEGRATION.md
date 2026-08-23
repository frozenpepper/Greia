# Greia Engineering Skills Integration Review — 2026-08-23

**Scope:** documentation/authoring-contract review only  
**Runtime/source behavior changed:** no  
**Primary input:** `docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md` plus current engineering/audio/agent-operation authorities

## Reviewed lessons

The new measured performance work established several lessons that need to affect everyday authoring rather than remain a specialist optimization document:

1. Greia performance is a correctness constraint on the Acer-class floor.
2. Large per-pixel-alpha area is much more important than draw-call count in the measured software-rendered path.
3. Image decode, large scaling, repeated font/text creation, filesystem/device/subprocess/config work and durable writes do not belong in frame/event hot paths.
4. Static presentation should be precomposed/prepared; reusable transforms should be cached by semantic state.
5. Cache size must match the real working set while remaining bounded.
6. Every cache needs a complete key and explicit invalidation/re-key story.
7. Static/turn-based UI should redraw on invalidation rather than continuously repaint unchanged pixels.
8. Performance fast paths must fail back to a correct path and should be tested against the naive/correct rendering path.
9. Low idle CPU must not purchase perceptible input latency; current Activity-facing target remains <=50 ms added input latency and ~30 fps on the Atom-class floor.
10. Desktop/simulator timing does not prove Acer/Pi performance; hardware claims require named hardware and exact source SHA.

## Architecture/maintainability gap found

Repository-wide `ENGINEERING_FOUNDATIONS.md` already contains strong OOP/polymorphism, explicit ownership, composition, bounded resources and comment/docstring rules.

The Activity authoring skill did not operationalize those rules strongly enough. In particular, its package examples and general flow did not prevent contributors from treating `main.py` as the entire Activity implementation. Several first-party Activities have historically grown into very large entry scripts, making rendering, game state, persistence, audio and input difficult to reason about and reuse.

The required correction is not more abstract framework code. It is a clearer responsibility protocol:

- `main.py` is a composition/bootstrap root;
- stable state/lifecycle/invariants become cohesive model/application objects;
- rendering/presentation owns prepared visual resources;
- audio sequencing/persistence/challenge generation are collaborators when non-trivial;
- real substitution points use narrow Protocol/ABC seams;
- composition is preferred to inheritance;
- Greia shared services/primitives are reused before Activity-local infrastructure is written.

Review thresholds are deliberately guidance rather than mechanical style law: roughly >150 lines in `main.py` triggers explanation/splitting review, >250 normally requires decomposition for first-party code, >500-line modules and >60–80-line methods trigger responsibility review. Contributors must split by ownership rather than game line counts.

## OS contributor skill decision

A dedicated derived OS-development skill is useful because the repository already has many correct authorities, but contributors otherwise spend significant time rediscovering:

- the required read order;
- module/layer ownership;
- the intended direct/appliance architecture direction;
- OOP/polymorphic extension rules;
- how to choose where reusable classes belong;
- display/input/system-chrome trust boundaries;
- performance patterns/evidence rules;
- microphone/audio ownership;
- simulator boundaries;
- install/update/trust rules;
- documentation and evidence obligations.

The new OS skill therefore acts as a practical router/implementation protocol while remaining explicitly subordinate to ADRs and exact source contracts.

## Changes made

Created:

```text
skills/greia-activity-authoring/ENGINEERING.md
skills/greia-os-work/SKILL.md
```

Updated:

```text
skills/greia-activity-authoring/SKILL.md
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
AGENTS.md
HANDOVER.md
```

The Activity skill now makes `ENGINEERING.md` mandatory for new/substantively changed first-party implementation work and exposes the code-structure/performance summary directly from its index.

The performance manual now records Activity-skill integration as complete and points to the Activity engineering companion as the practical normative authoring location while retaining measured rationale/case studies.

`AGENTS.md` now requires the OS work skill for substantive platform/Shell/Parent/installer/simulator/build/runtime/hardware-service work and requires future changes to keep the skill aligned.

## Deliberate non-changes

- No runtime API, package schema or source behavior was changed.
- No new generic Activity base class was invented; exact reusable APIs remain source-owned.
- No static regex linter was introduced for hot-loop behavior. Such tooling may be useful later, but profiling/review cannot be replaced by simplistic text matching.
- No line-count build failure was introduced; thresholds remain architecture-review triggers.
- No GitHub-hosted Actions were queried or run.

## Verification scope

Because this tranche changes documentation/skills only, verification consists of repository re-read of the created/updated files and cross-reference consistency. It does not create a new runtime PASS claim.