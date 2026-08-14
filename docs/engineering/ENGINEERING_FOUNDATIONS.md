# Greia Engineering Foundations

**Status:** mandatory repository engineering guidance  
**Audience:** maintainers, contributors, coding agents, reviewers  
**Normative architecture:** accepted ADRs remain authoritative; this document explains how to implement them cleanly.

## 1. Goal

Greia is intended to become a long-lived open-source project that other people can understand, modify and extend safely.

The codebase therefore optimizes for all of the following together:

- clear architecture;
- strong object-oriented structure where domain objects and substitutable implementations genuinely exist;
- purposeful polymorphism;
- explicit ownership and lifecycle;
- small, cohesive modules;
- low coupling and high testability;
- excellent low-resource behavior;
- documentation good enough that contributors do not need chat history or archaeology to find the right extension point.

Performance and maintainability are not competing goals. On Greia, unnecessary allocation, hidden ownership and duplicated architecture are often both performance problems and design problems.

## 2. OOP rules

### Model stable concepts as objects

Prefer classes/dataclasses for stable concepts that own invariants, state, lifecycle or behavior. Examples include Activity manifests, profile contexts, storage/session objects, display backends, system-chrome coordinators, input mappings/controller owners, UI Screens, Collections, runtime adapters, hardware adapters and bounded caches.

Do not create classes merely to wrap one stateless function. Small pure functions remain appropriate for local calculations and transformations.

### Use polymorphism at genuine variation points

When callers need one behavior with multiple implementations, define one narrow typed contract and inject an implementation.

Good examples:

```text
DisplaySessionBackend
  ├── LegacyXDisplaySessionBackend
  └── future direct/compositor backend

SystemChromeBackend
  └── future selected trusted overlay/input backend

InputHAL / trusted input backend
  ├── provisional legacy-X + Linux controller probing
  └── future direct/session input implementation

RuntimeAdapter
  ├── PythonRuntimeAdapter
  └── future WebRuntimeAdapter

Screen
  ├── ProfilePickerScreen
  ├── ActivityCollectionScreen
  └── SettingsScreen
```

Prefer that structure over repeated backend/type checks spread through callers.

A growing conditional such as:

```python
if backend == "x11": ...
elif backend == "kms": ...
elif backend == "wayland": ...
```

is a signal to look for a missing polymorphic seam when the branches represent substitutable implementations.

### Prefer composition over inheritance

Use inheritance when the subtype is genuinely substitutable for the base contract.

Use composition when an object is assembled from capabilities/services. Avoid deep inheritance trees and mixin webs.

### Keep interfaces narrow

A protocol/base class should expose only what callers need. Do not create universal manager interfaces containing unrelated storage, rendering, input, network and lifecycle methods.

### Make ownership obvious

Long-lived resources must have an identifiable owner and cleanup path. This includes subprocesses, display leases, system-chrome leases, controller handles, storage sessions, temporary mounts, threads, caches, renderer surfaces and hardware authority.

A trusted controller backend that opens devices must have explicit device-count bounds, reconnect behavior and teardown. An Activity must not become the accidental owner of system input merely because a runtime library can open a device.

Global mutable singletons are strongly discouraged. Pass dependencies explicitly at architectural seams.

## 3. Module and dependency direction

Keep the existing major boundaries clear:

```text
greia_platform
    stable platform services/contracts/shared primitives

        ↑ consumed by

greia_launcher
    child Shell/session orchestration

greia_parent
    parent authority surface

greia_installer
    installation UI + destructive engine boundary

activities/*
    supervised Activity implementations using public platform APIs
```

Renderer/runtime/hardware-specific implementations sit behind interfaces rather than leaking upward into platform semantics.

Do not create parallel implementations of storage, profiles, progression, backup, permission policy or standard input mappings inside a UI/runtime just because it is convenient locally.

Circular package dependencies are architecture defects unless there is an exceptional documented reason.

## 4. UI and input architecture

ADR 0018 owns the lightweight UI architecture. ADR 0019 owns platform-controlled Activity Home/Back chrome. ADR 0020 owns runtime-neutral Activity input profiles and controller support.

Core UI semantic vocabulary:

```text
Screen
Overlay
Control
Collection
PagedGrid
Invalidation
BoundedCache
```

A Screen is the full logical surface. Overlay/Sheet is bounded transient UI. Collection is the child-facing grouping abstraction and is not a filesystem folder.

### Trusted Activity system chrome

System Home/Back is **not an Activity Overlay** and is not an Activity widget. It belongs to a higher-trust display/input layer above the Activity surface.

The architecture must preserve this dependency direction:

```text
Greia display/session authority
├── SystemChromeBackend / protected input
└── Activity runtime surface
```

Do not implement mandatory Home by asking Python Activities to draw a helper or by injecting a removable DOM element into Web content. That would invert ownership and violate ADR 0019.

`src/greia_platform/system_chrome.py` owns renderer-neutral geometry/actions. `src/greia_launcher/system_chrome.py` owns the backend-neutral trusted chrome lifecycle seam. Concrete display/input implementations remain below those contracts.

### Runtime-neutral input semantics

`src/greia_platform/input_core.py` owns the common interaction-profile/action vocabulary, central analog normalization and Greia virtual-pointer semantics. `src/greia_platform/pygame_input.py` is a current Pygame translation/trusted-controller helper, not the universal Activity input API.

Keep these concerns distinct:

```text
physical device capability / ownership
        ↓
trusted Greia input backend
        ↓
protected system input interception
        ↓
interaction-profile mapping
        ↓
runtime-neutral Activity semantics
        ↓
Python / Web / future adapter
```

Do not spread SDL button numbers, controller-brand labels, dead-zone constants, virtual-cursor acceleration or reconnect logic through Activities. They are shared platform concerns.

A controller used as a pointer must drive a Greia semantic virtual pointer. Do not create global OS-level mouse emulation merely to make one Activity convenient.

Text Activities must retain real text input: do not apply game/navigation mappings that steal Space, Enter or arrow keys from text editing simply because those keys have standard meanings in another profile.

Current renderer-specific Pygame helpers live beneath UI/input semantics. Future Web/native renderers can implement equivalent ordinary Activity UI/input concepts independently, while system chrome remains outside Activity authority entirely.

Do not create a desktop/window-manager abstraction, general retained scene graph, DOM clone, giant widget toolkit or generic input scripting framework without a new evidence-backed architecture decision.

## 5. Low-resource engineering rules

The first-generation Acer Aspire One class is a real design constraint.

### Allocation

Avoid allocations in hot frame/event paths when an object can be cached or reused safely. In particular:

- cache fonts;
- cache decoded/scaled icons;
- do not decode images per frame;
- do not create a backing surface for every button/card;
- avoid repeated large string/image copies;
- bound undo/history structures by both count and meaningful payload where appropriate;
- do not rebuild controller/device inventories every frame; refresh them only on explicit topology/lifecycle boundaries.

### Caches and device sets

Every persistent/in-memory cache must have an explicit maximum size or another demonstrable natural bound.

Prefer shared `BoundedCache` for general LRU-style UI resource caches rather than open-ended dictionaries.

Controller/device owners must also be bounded. The current trusted Pygame helper intentionally limits both candidate scanning and simultaneously opened controllers rather than assuming today's machine has only one device.

### Rendering and input loops

Static screens should eventually render on invalidation/input rather than burning a continuous frame loop while nothing changes.

Animations must be explicit, bounded and useful. Ordinary Shell animation should target at most about 30 Hz unless measurement shows a higher rate is needed.

The mandatory Activity Home/Back layer must stay tiny: one protected region, no general window tree, no independent high-frequency animation loop unless measurement proves one necessary. System chrome is not justification for a desktop compositor.

Controller polling, where a backend requires it, must avoid filesystem/device discovery in the frame loop. Open handles belong to a bounded owner; per-frame work should be limited to already-open state reads and cheap normalization.

### Collections

Render/layout only the visible page/items. Do not construct/render an unbounded list of hidden child cards merely because the dataset is small today.

### Storage and histories

Never use an unbounded history/cache as a convenience feature. Refusing a new creation because a deliberate product limit is reached is preferable to silently evicting child work.

## 6. Documentation rules for code

Public architectural classes, protocols and extension points require useful docstrings explaining:

- what the object owns;
- its lifecycle;
- the important invariants;
- what layer is allowed to depend on it;
- resource limits when relevant.

Non-obvious algorithms need comments explaining **why**, not comments that paraphrase each line.

When a new architecture seam is accepted, update the relevant ADR/living architecture/agent documentation in the same tranche.

Do not make contributors infer stable contracts from one implementation class.

## 7. Testing rules

Test contracts at the narrowest useful layer.

Prefer pure/provider-free tests for:

- paging/layout calculations;
- system-chrome protected geometry/action routing;
- input-profile mappings;
- analog dead-zone/normalization and virtual-pointer bounds;
- controller-owner resource bounds and cleanup semantics;
- state machines;
- lifecycle sequencing and stale-lease rejection;
- resource/cache bounds;
- serialization/validation;
- polymorphic dispatch behavior;
- failure/rollback invariants.

Then use VM/physical tests only for behavior that actually depends on the environment, display stack, controller hardware, timing or device drivers.

For ADR 0019 specifically, pure tests can prove geometry/coordinator contracts but **cannot** prove that an Activity cannot cover chrome or receive protected input. That requires real backend/runtime evidence.

For ADR 0020, pure tests can prove mappings and bounds but cannot prove controller latency, noisy-axis behavior, real disconnect/reconnect or protected system-input interception. Those require physical/backend evidence.

Do not replace hardware evidence with mocks, and do not make unit tests unnecessarily dependent on hardware.

## 8. Review checklist

A substantive code review should ask:

1. Is this concept in the correct module/layer?
2. Is there already an abstraction that should own it?
3. Does a variation point need a protocol/base class instead of another conditional branch?
4. Is inheritance being used only for real substitutability?
5. Are dependencies injected rather than discovered through hidden globals?
6. Is ownership/cleanup explicit?
7. Are caches, queues, histories, controller sets and collections bounded?
8. Does hot-path code avoid repeated decoding/allocation/IO/device discovery?
9. Could an outside contributor understand the extension point from names, docstrings and docs?
10. Are failure paths and rollback/reconnect semantics tested?
11. Does the change preserve architecture neutrality across runtimes and hardware?
12. Does the code stay simple enough for the problem actually being solved?
13. For Activity presentation/input changes, can Greia still preserve mandatory Home independently of Activity cooperation?
14. Are controller-brand/raw-device details confined below the runtime-neutral input contract?
15. Could a new input path accidentally grant an Activity access to reserved system input or `/dev/input`?

## 9. Anti-patterns

Avoid:

- god classes;
- giant `manager` objects owning unrelated domains;
- deep inheritance hierarchies;
- speculative generic frameworks;
- stringly-typed backend dispatch scattered across the codebase;
- copy/pasted runtime/platform service implementations;
- Activity-drawn or DOM-injected mandatory system Home controls;
- per-Activity controller button/dead-zone/reconnect implementations;
- controller-brand labels or raw joystick indices as Activity semantics;
- broad `/dev/input` grants to ordinary Activities;
- global controller-to-Linux-mouse emulation as the general pointer solution;
- unbounded dictionaries/device registries used as caches;
- per-frame file/image/font construction or device enumeration;
- hidden filesystem paths as product semantics;
- host/runtime details leaking into portable child state;
- long undocumented methods mixing business state, IO, rendering and privileged operations.

The standard is not maximal abstraction. The standard is **clear, extensible architecture with the smallest set of strong abstractions that actually own the problem**.
