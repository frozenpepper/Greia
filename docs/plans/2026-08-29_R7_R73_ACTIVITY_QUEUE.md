# R7.3 Activity Queue — flat reference

**Date:** 2026-08-29
**Companion to:** `docs/plans/2026-08-29_R7_R73_ACTIVITY_MODERNIZATION.md`
**Source of truth:** `PYTHONPATH=src python3 tools/audit_activity_system_chrome_ownership.py --strict`
**Status on the current SHA (`5ef785085d106fdcf8e876323f6e7ab3ca2e0d7c`):** strict audit `blockers=62` across 16 non-exemplar Activities + the 6 first-wave exemplars already clean.

## A. Strict-queue (mandatory R7.3 migration, items 1–17 of the plan)

These Activities still own the retired cooperative Home helper / `PygameReferenceCanvas.present(system_chrome=...)` pattern. **Process in this order; one Activity per coherent commit.**

```text
1.  clinica_cuccioli          (reference / calibration target; confirm clean)
2.  la_discesa_della_biglia   (ramp_app.py:28, is_home_clicked import)
3.  labirinto_magico          (maze_renderer.py:9, ActivitySystemChromeLayout import — first-wave exemplar; investigate first)
4.  luci_di_momo              (firefly_app.py:13, is_home_clicked import)
5.  memory_meraviglie         (main.py:24, is_home_clicked import)
6.  nascondino_bosco          (woodland_app.py:17 import, :171 call)
7.  officina_dei_suoni        (sound_app.py:14 import, :230/:366 calls)
8.  orchestra_animali         (main.py:21 import, :421 call)
9.  pasticceria_magica        (main.py:22 import, :261 call)
10. piccola_serra             (main.py:23 import, :291 call)
11. posta_di_leo              (postcard_app.py:13 import, :185 call)
12. sillabe_magiche           (main.py:22 import, :850/:855 calls)
13. specchi_magici            (mirror_app.py:13 import, :169/:304 calls)
14. teatrino_fiabe            (main.py:38 two imports, :1163 call)
15. treno_numeri              (main.py:23 import, :317 call)
16. viaggio_delfino           (delfino_app.py:22 import, :372 call)
17. workshop_settings         (main.py:26 two imports + ActivitySystemChromeLayout import, :158/:277 calls; parent-only surface)
```

## B. First-wave exemplars (R7.3 confirmation only)

These are already migrated to the trusted-chrome pattern. They are not in the strict queue; the plan only re-confirms them in Simulator launch.

```text
- writing
- painting
- labirinto_magico   (also in section A — overlap; resolve the maze_renderer.py hit)
- volo_draghetto
- shape_garden
- storie_della_mia_voce
```

## C. Lighter architecture/performance pass

Process only if the Activity is a giant procedural `main.py` (clearly > 250 lines with mixed responsibilities), has an obvious hot-path issue, or has an obvious pre-reader UX failure. Healthy small Activities are left alone.

```text
- acquario_magico            (performance case-study precedent; confirm not regressed)
- baia_delle_orche           (orca subject; Tito presenter + curiosity candidate)
- bottega_delle_misure       (Dani affinity)
- casa_del_dieci             (Dani affinity)
- costruiamo_ponti           (Dani affinity; performance case-study precedent)
- cucciolo_mio               (Lilli affinity)
- festa_delle_rime           (Leo affinity)
- foresta_parole             (Leo affinity)
- morbidi_mostriciattoli     (Lilli/Momo affinity)
- nanna_delle_nuvolette      (Momo/Lilli affinity)
- shape_garden               (see section B)
- stelle_incantate           (Tito/Leo affinity)
- storie_della_mia_voce      (see section B)
- volo_draghetto             (see section B)
- writing                    (see section B)
- painting                   (see section B)
```

## D. Out of scope (managed by other plans)

```text
- enciclopedia_greia         -> docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md
- workshop_settings          -> section A but parent-only; not a child Activity
```

## E. Per-Activity execution steps (reproduced from the plan)

```text
2.1 inspect activity.toml, entrypoint, all source modules, tests, assets,
    locales, audio, storage, events, research/facts
2.2 fill in the modernization ledger row
2.3 R7.3 Home/Back migration (remove cooperative Home helper usage; keep
    renderer-neutral safe/protected geometry; preserve mark_activity_ready,
    activity_stop_requested, normal graceful cleanup)
2.4 architecture review (thin main.py, OOP where ownership/state/lifecycle exist)
2.5 child UX / intelligibility review (pre-reader-first)
2.6 canonical Greia character decision
2.7 voice / audio review
2.8 assets and visual cleanup
2.9 performance review (no per-frame decode/scale/font/IO)
2.10 general correctness / cleanup
2.11 tests (focused + validate_project.py + the two audits + Simulator launch)
2.12 commit (one Activity per coherent commit)
2.13 append ledger row; update HANDOVER at session boundaries
```

## F. Total work estimate (at the time of writing)

```text
Stage A (source-gate repair, not Activity work): 1-2 commits
Stage B (strict-queue 17 Activities):           17 commits (one per Activity)
Stage B (lighter pass, only flagged Activities):  0-N additional commits
Stage C (final gate, no code):                    0 commits (just verification)

Minimum commits to clear the strict queue: 17.
Expected total: ~17-25 commits across the full plan.
```

## G. Per-Activity ledger template

For each Activity, fill in this template and append to the plan's Section 3:

```text
Activity: <name>
R7.3 migration: done
Architecture: unchanged / refactored
Main entrypoint: thin / acceptable / remaining debt
Presenter: <character / deliberate none>
Voice: existing / changed / recording required
Pre-reader UX: pass / issue fixed / remaining issue
Assets: pass / cleanup performed
Performance: reviewed + concrete changes
Manifest/localization/storage/events: pass / repairs
Simulator: PASS/FAIL
Commit: <sha>
Notes: <one short paragraph>
```
