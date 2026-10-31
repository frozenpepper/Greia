# Map of the docs

Find what you need, then open it. For the rules about which document is the
authority for which fact, read [DOCUMENTATION.md](DOCUMENTATION.md). Old dated
reports and reviews are not in the tree any more; they live in git history.

## Using Greia

| Document | What it is for |
|---|---|
| [user/README.md](user/README.md) | Friendly starting page for families |
| [user/INSTALL_FROM_USB.md](user/INSTALL_FROM_USB.md) | Put Greia on a USB stick and install it |
| [user/GREIA_PARENTS.md](user/GREIA_PARENTS.md) | Open the parent settings and manage Greia from a phone |

## Parents

| Document | What it is for |
|---|---|
| [product/PARENT_MANAGEMENT.md](product/PARENT_MANAGEMENT.md) | What parents can do and how it should feel |
| [../parent-app/README.md](../parent-app/README.md) | The Parents web client (phone/browser) source in this repository |
| [product/SYSTEM_UPDATES.md](product/SYSTEM_UPDATES.md) | How system and Activity updates look to a parent |
| [product/FIRST_BOOT_PROFILE_SETUP.md](product/FIRST_BOOT_PROFILE_SETUP.md) | The voiced first-start wizard that creates the first child profile |
| [product/MY_GREIA_SETTINGS.md](product/MY_GREIA_SETTINGS.md) | Child-friendly My Greia settings for personalizing their own space |
| [product/CHILD_TIME_AND_ROUTINES.md](product/CHILD_TIME_AND_ROUTINES.md) | Proposal: child-friendly lessons on clocks, timers and days |
| [design/PARENT_CONTROLS_USAGE_LIMITS_AND_ACTIVITY_VISIBILITY.md](design/PARENT_CONTROLS_USAGE_LIMITS_AND_ACTIVITY_VISIBILITY.md) | Design of limits and Activity visibility |
| [../PRIVACY.md](../PRIVACY.md) | What Greia does and does not do with data |

## Building and contributing

| Document | What it is for |
|---|---|
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | How to set up, check and submit a change |
| [../SETUP.md](../SETUP.md) | What each contributor or operator role must install |
| [development/README.md](development/README.md) | Index of developer manuals |
| [development/CREATE_AN_ACTIVITY.md](development/CREATE_AN_ACTIVITY.md) | Make your first Activity |
| [development/GREIA_ACTIVITY_SIMULATOR.md](development/GREIA_ACTIVITY_SIMULATOR.md) | Run the real Shell on a desktop |
| [development/ADD_A_GREIA_LANGUAGE.md](development/ADD_A_GREIA_LANGUAGE.md) | Add, translate or retire a language |
| [development/GREIA_ACTIVITY_TEXT_TYPOGRAPHY_AND_EMOJI.md](development/GREIA_ACTIVITY_TEXT_TYPOGRAPHY_AND_EMOJI.md) | Text, fonts and emoji in Activities |
| [development/BUILD_A_GREIA_IMAGE.md](development/BUILD_A_GREIA_IMAGE.md) | Build an installer image (human guide) |
| [development/GREIA_DEVELOPER_BOOT_DIAGNOSTICS.md](development/GREIA_DEVELOPER_BOOT_DIAGNOSTICS.md) | Diagnose an installed development machine that never reaches the launcher |
| [development/GREIA_SOFTWARE_UPDATE_PACKAGES.md](development/GREIA_SOFTWARE_UPDATE_PACKAGES.md) | Build `.greia_update` application packages |
| [development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md](development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md) | Build a full-system `.greiaupdate` |
| [release/INSTALLER_FAILURE_LOGS_ON_USB.md](release/INSTALLER_FAILURE_LOGS_ON_USB.md) | Where installer failure logs are saved on the USB key |
| [testing/HARDWARE_COMPATIBILITY_MATRIX.md](testing/HARDWARE_COMPATIBILITY_MATRIX.md) | How hardware support is classified and proven |
| [testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md](testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md) | What counts as visual test evidence |

Installer and boot lessons live in [engineering/boot/](engineering/boot/):

| Document | What it is for |
|---|---|
| [engineering/boot/INSTALLER_IMAGE_CREATION_AND_BOOT.md](engineering/boot/INSTALLER_IMAGE_CREATION_AND_BOOT.md) | How installer images are made and boot |
| [engineering/boot/INSTALLED_OS_BOOT_POSTMORTEM.md](engineering/boot/INSTALLED_OS_BOOT_POSTMORTEM.md) | Why installed systems failed to boot, and the fixes |
| [engineering/boot/INSTALLATION_USB_BOOT_POSTMORTEM.md](engineering/boot/INSTALLATION_USB_BOOT_POSTMORTEM.md) | Why installer USB sticks failed to boot, and the fixes |
| [engineering/boot/INSTALLATION_ISSUES_LOG.md](engineering/boot/INSTALLATION_ISSUES_LOG.md) | Installation problems met on legacy hardware, and the rules learned |

## Architecture and decisions (adr)

| Document | What it is for |
|---|---|
| [architecture/GREIA_ARCHITECTURE.md](architecture/GREIA_ARCHITECTURE.md) | Living overview of the whole system |
| [adr/](adr/) | One file per accepted decision. Start with [0012, the platform constitution](adr/0012-platform-architecture-constitution.md) |
| [adr/0018-lightweight-ui-foundation.md](adr/0018-lightweight-ui-foundation.md) | Screens, overlays and collections |
| [adr/0019-platform-owned-activity-system-navigation.md](adr/0019-platform-owned-activity-system-navigation.md) | The Home button no Activity can hide |
| [adr/0020-runtime-neutral-input-profiles-and-controller-support.md](adr/0020-runtime-neutral-input-profiles-and-controller-support.md) | Keyboard, touch and controller handling |
| [adr/0024-project-licensing-and-trademark-boundary.md](adr/0024-project-licensing-and-trademark-boundary.md) | Licensing decisions |
| [adr/0036-unified-system-slot-releases-and-platform-install-media.md](adr/0036-unified-system-slot-releases-and-platform-install-media.md) | A/B system updates and install media |
| [adr/0037-shared-activity-control-kit.md](adr/0037-shared-activity-control-kit.md) | The shared buttons and HUD for Activities |
| [adr/0038-lightweight-application-update-packages.md](adr/0038-lightweight-application-update-packages.md) | Small application update packages |
| [architecture/GREIA_ACTIVITY_ECOSYSTEM.md](architecture/GREIA_ACTIVITY_ECOSYSTEM.md) | How Activities are made, shared and trusted |
| [architecture/GREIA_ACTIVITY_PACKAGE_FORMAT.md](architecture/GREIA_ACTIVITY_PACKAGE_FORMAT.md) | The `.greiaactivity` file format |
| [architecture/GREIA_AUDIO_SERVICE.md](architecture/GREIA_AUDIO_SERVICE.md) | Sound and microphone service |
| [architecture/GREIA_PARENT_MANAGEMENT.md](architecture/GREIA_PARENT_MANAGEMENT.md) | How the Parent API is built |
| [architecture/PARENT_APP_SOURCE_INTEGRATION.md](architecture/PARENT_APP_SOURCE_INTEGRATION.md) | How the Parents web client (`parent-app/`) is pinned into the image |
| [../parent-app/README.md](../parent-app/README.md) | The Parents web client source: run, test and ship it (rules in [parent-app/AGENTS.md](../parent-app/AGENTS.md)) |
| [architecture/GREIA_VOICE_PRODUCTION_ENGINE.md](architecture/GREIA_VOICE_PRODUCTION_ENGINE.md) | Authoring-time engine for all recorded speech; never shipped to devices |
| [architecture/UNIVERSAL_GREIA_SETUP_MEDIA_ARCHITECTURE.md](architecture/UNIVERSAL_GREIA_SETUP_MEDIA_ARCHITECTURE.md) | Plan for one setup image for many machines |
| [governance/LICENSING_AND_TRADEMARK.md](governance/LICENSING_AND_TRADEMARK.md) | Full licensing and trademark policy |

## Product requirements

What Greia must do, written from the child's and parent's point of view.

| Document | What it is for |
|---|---|
| [product/ACTIVITY_SYSTEM_NAVIGATION.md](product/ACTIVITY_SYSTEM_NAVIGATION.md) | The Home control every Activity must keep, and when Back appears |
| [product/ACTIVITY_INPUT_STANDARDS.md](product/ACTIVITY_INPUT_STANDARDS.md) | Keyboard, mouse, touch and controller rules |
| [product/PHASE0_CORE_CREATION_ACTIVITIES.md](product/PHASE0_CORE_CREATION_ACTIVITIES.md) | Writing and painting studios |
| [product/INSTALLER_EXPERIENCE.md](product/INSTALLER_EXPERIENCE.md) | The graphical installer, screen by screen |
| [product/INSTALLER_WIFI_SETUP.md](product/INSTALLER_WIFI_SETUP.md) | Wi-Fi during installation |
| [product/SYSTEM_LANGUAGE_AND_LOCALIZATION.md](product/SYSTEM_LANGUAGE_AND_LOCALIZATION.md) | How the device language is set in the installer, Parents and Shell |
| [product/RESPONSIVE_UI_AND_DISPLAY_LAYOUT.md](product/RESPONSIVE_UI_AND_DISPLAY_LAYOUT.md) | Layout on different screen sizes |
| [product/AWARDS_BADGES_AND_CELEBRATIONS.md](product/AWARDS_BADGES_AND_CELEBRATIONS.md) | Child-facing awards, badges and celebrations for real achievements |
| [product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md](product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md) | How children find Activities by age |
| [product/CHILD_ACTIVITY_DISCOVERY_IMPLEMENTATION_STATUS.md](product/CHILD_ACTIVITY_DISCOVERY_IMPLEMENTATION_STATUS.md) | Which discovery features are built, and what is still pending |
| [product/CHILD_CREATIONS_LIBRARY_AND_MEDIA_INTEROPERABILITY.md](product/CHILD_CREATIONS_LIBRARY_AND_MEDIA_INTEROPERABILITY.md) | Saving, reopening and reusing a child's drawings, recordings and text |
| [product/ACTIVITY_CATALOGUE_AGES_3_5_STRATEGY.md](product/ACTIVITY_CATALOGUE_AGES_3_5_STRATEGY.md) | Catalogue audit and curriculum strategy for ages 3 to 5 |
| [product/ACTIVITY_ECOSYSTEM_AND_DISTRIBUTION.md](product/ACTIVITY_ECOSYSTEM_AND_DISTRIBUTION.md) | Sharing and installing Activities |

## Design and art

| Document | What it is for |
|---|---|
| [design/GREIA_ART_GRAPHICS_SYSTEM.md](design/GREIA_ART_GRAPHICS_SYSTEM.md) | Main entry point for all art and graphics |
| [design/GREIA_VISUAL_STYLE_GUIDE.md](design/GREIA_VISUAL_STYLE_GUIDE.md) | The look of Greia |
| [design/GREIA_SVG_AUTHORING_RULES.md](design/GREIA_SVG_AUTHORING_RULES.md) | How to draw an SVG asset |
| [design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md](design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md) | Which core assets must exist |
| [design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md](design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md) | How the bundled art library is kept, and how authors use it |
| [design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md](design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md) | How the shared art library is organised |
| [design/GREIA_SCENE_COMPOSITION_RUNTIME.md](design/GREIA_SCENE_COMPOSITION_RUNTIME.md) | Building scenes from parts at run time |
| [design/GREIA_CANONICAL_CAST_SYSTEM.md](design/GREIA_CANONICAL_CAST_SYSTEM.md) | The recurring characters |
| [design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md](design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md) | Character faces and movement |
| [design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md](design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md) | Rules for drawing characters |
| [design/GREIA_ACHIEVEMENTS_AND_BADGE_LIBRARY.md](design/GREIA_ACHIEVEMENTS_AND_BADGE_LIBRARY.md) | How achievements are earned, remembered and shown |
| [design/GREIA_ACTIVITY_ACHIEVEMENT_ART.md](design/GREIA_ACTIVITY_ACHIEVEMENT_ART.md) | Badge art for Activities |
| [design/GREIA_ACTIVITY_CANVAS_AND_VIEWPORT_AUTHORING.md](design/GREIA_ACTIVITY_CANVAS_AND_VIEWPORT_AUTHORING.md) | Canvas and camera for Activities |
| [design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md](design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md) | How the Shell lists Activities |
| [design/GREIA_BOOT_EXPERIENCE.md](design/GREIA_BOOT_EXPERIENCE.md) | What the child sees at start-up |
| [design/GREIA_BOOT_PROGRESS.md](design/GREIA_BOOT_PROGRESS.md) | Retired boot progress bar: compatibility notes and history |
| [design/GREIA_SHARED_CHARACTER_UTTERANCES.md](design/GREIA_SHARED_CHARACTER_UTTERANCES.md) | Shared spoken lines for characters |
| [design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md](design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md) | Voice policy and how character voices are produced |

## Engineering

| Document | What it is for |
|---|---|
| [engineering/ENGINEERING_FOUNDATIONS.md](engineering/ENGINEERING_FOUNDATIONS.md) | Code structure and extension rules |
| [engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md](engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md) | Keeping Greia fast on old machines |
| [engineering/BOOT_PIPELINE_AGENT_GUIDE.md](engineering/BOOT_PIPELINE_AGENT_GUIDE.md) | Boot and display pipeline operating guide |

## Agents and skills

See the [agent index](agents/README.md). The short version:
[../AGENTS.md](../AGENTS.md), then [../SETUP.md](../SETUP.md), then a skill in
[../skills/](../skills/README.md).

## Public documentation boundary

Technical decisions, how-to guides and contributor contracts belong here. Owner work orders, historical acceptance journals and private release coordination are maintained outside the public tree. Git history retains prior versions; removing a file from the current tree does not erase an earlier public copy.
