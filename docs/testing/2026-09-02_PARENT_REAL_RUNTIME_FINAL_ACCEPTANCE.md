# Parent real-runtime final acceptance — Acer physical gate

**Date:** 2026-09-03  
**Purpose:** prove the Greia Parent web app is the real installed production client and that Parent mutations reach actual Acer state.  
**Evidence lane:** SOURCE + IMAGE + PHYSICAL DEVICE + REAL BROWSER  
**Execution rule:** **STOP ON THE FIRST FAILURE. Do not repair, rerun around, or weaken a failed gate inside the frozen attempt.**

This procedure is written for a small local agent. Follow it literally. Do not substitute demo data or an easier environment.

---

## 0. Hard prohibitions

During this acceptance you MUST NOT:

- add `?demo=1` to the Parent URL;
- run the Parent browser client from localhost as acceptance evidence;
- fabricate profiles, Activities, usage, Wi-Fi networks, device facts or settings;
- edit Greia state/DB files merely to make the browser look populated;
- bypass pairing/authentication;
- copy files manually into `/usr/share/greia-parent-app`;
- edit `runtime/parent-app-client.toml` or `runtime/parent-app-client.manifest.json` during the run;
- disable or bypass the Parent-client integrity preflight;
- grant `greiapanel` ALSA, backlight, root, sudo or broad iwd privileges;
- invoke `amixer` from the Parent HTTP service;
- accept a browser control merely because the UI changed;
- accept a PUT merely because it returned HTTP 200;
- replace a failed numbered step with a later successful rerun;
- use GitHub Actions as test/evidence infrastructure;
- pull/merge/edit source after the candidate is frozen;
- delete, reset, clean or stash unrelated owner work.

If any prohibited action becomes necessary, verdict is **INCOMPLETE/FAILED**, stop, and return the evidence collected so far.

---

## 1. Expected architecture — do not “fix” it during testing

The intended speaker-volume path is:

```text
real Parent browser
  -> authenticated PUT /api/v1/settings/system-controls
  -> SystemControlSettingsStore shared desired state
  -> Greia Legacy-X hardware-session watcher
  -> ALSA Master/Speaker/PCM control
  -> physical Acer speaker
```

The Parent service itself remains unprivileged. That is intentional.

Production Wi-Fi is also fail-closed. If the unprivileged Parent service cannot genuinely manage real iwd state, `/api/v1` MUST advertise:

```text
network.manage = false
```

and the browser MUST show a polished unavailable state. It must never show sample SSIDs.

---

## 2. Required candidate

Work from the canonical repository:

```text
frozenpepper/Greia
branch: main
```

The frozen candidate MUST contain this integration commit or a descendant of it:

```text
0f152be9233a311e90d243d7ba4da70ee022b66f
```

That commit installs the frozen Parent runtime into the canonical image and adds installed-runtime integrity enforcement.

The Parent pin expected by that integration is:

```text
frozenpepper/Greia-Parent-App-Html
75ee275771c495dc187efb5275732ea10c10af4b
```

Create the evidence root from the Greia repository root:

```bash
set -euo pipefail
EVIDENCE="$PWD/tmp/PARENT_REAL_RUNTIME_FINAL_2026-09-03"
rm -rf "$EVIDENCE"
mkdir -p "$EVIDENCE"/{source,build,acer,browser,volume,screenshots}
```

The `rm -rf` above is allowed **only** for this exact project-local evidence directory that this procedure just names. Do not clean any other project path.

Freeze source identity:

```bash
git status --short > "$EVIDENCE/source/git-status.txt"
git rev-parse HEAD | tee "$EVIDENCE/source/HEAD.txt"
git rev-parse origin/main | tee "$EVIDENCE/source/origin-main.txt"
git merge-base --is-ancestor 0f152be9233a311e90d243d7ba4da70ee022b66f HEAD
git diff --check | tee "$EVIDENCE/source/git-diff-check.txt"
```

Expected:

- `git merge-base --is-ancestor ...` exits 0;
- the worktree contains no unexplained modifications relevant to this test;
- record any unrelated owner changes exactly; do not modify them.

If `HEAD != origin/main`, STOP unless the owner explicitly told you to test that exact local descendant.

Copy the pin and manifest into evidence:

```bash
cp runtime/parent-app-client.toml "$EVIDENCE/source/"
cp runtime/parent-app-client.manifest.json "$EVIDENCE/source/"
```

Confirm the pin:

```bash
grep -F 'revision = "75ee275771c495dc187efb5275732ea10c10af4b"' runtime/parent-app-client.toml
grep -F 'integration_state = "vendored-image-integrity-enforced"' runtime/parent-app-client.toml
```

Any mismatch: STOP.

---

## 3. Source gate — must pass before building

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_parent_app_staging.py' -v \
  |& tee "$EVIDENCE/source/test-parent-app-staging.log"

PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_parent_client_image_integration.py' -v \
  |& tee "$EVIDENCE/source/test-parent-client-image-integration.log"

PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_parent_production_api.py' -v \
  |& tee "$EVIDENCE/source/test-parent-production-api.log"

make verify |& tee "$EVIDENCE/source/make-verify.log"
```

All commands must exit 0. If any fails: STOP and return evidence. Do not build an image from failed source.

Also verify the committed vendor copy explicitly:

```bash
PYTHONPATH=src python3 -m greia_parent.parent_client_integrity \
  --root vendor/parent-app \
  --manifest runtime/parent-app-client.manifest.json \
  --pin runtime/parent-app-client.toml \
  | tee "$EVIDENCE/source/vendor-integrity.txt"
```

Expected output contains:

```text
Greia Parent client integrity OK: 75ee275771c495dc187efb5275732ea10c10af4b
```

---

## 4. Select the already-accepted Acer profile — do not guess

Use the physical Acer profile already selected by prior inventory/boot evidence. Valid normal candidates are:

```text
acer-aspire-one-i386
acer-aspire-one-i386-nonpae
acer-aspire-one-amd64
```

If you do not know which of those three is authoritative for the Acer in front of you, STOP and return `PROFILE_NOT_RESOLVED`. Do not choose one by convenience.

Set it once, for example:

```bash
PROFILE=acer-aspire-one-i386
printf '%s\n' "$PROFILE" | tee "$EVIDENCE/build/profile.txt"
```

Do not use a `*-dev` profile for the final production-browser pass below. Developer profiles may be used only for a separate diagnostic attempt after a failure, and that later attempt does not replace this acceptance.

Validate the selected profile:

```bash
python3 tools/build_profile.py validate "$PROFILE" |& tee "$EVIDENCE/build/profile-validate.log"
python3 tools/build_profile.py check-phase0-builder "$PROFILE" --scope target \
  |& tee "$EVIDENCE/build/profile-builder-check.log"
```

Both must exit 0.

---

## 5. Build the official installer image

Use the canonical installer builder. Do not manually assemble/copy the target filesystem.

```bash
sudo bash build/build-installer-image.sh "$PROFILE" out \
  |& tee "$EVIDENCE/build/installer-build.log"
```

Expected output image:

```text
out/greia-os-installer-${PROFILE}.img
```

Record hashes and reports:

```bash
sha256sum "out/greia-os-installer-${PROFILE}.img" \
  | tee "$EVIDENCE/build/installer-image.sha256"
cp -a out/greia-os-installer-${PROFILE}-report.txt "$EVIDENCE/build/" 2>/dev/null || true
cp -a out/greia-os-installer-${PROFILE}-image-profile.json "$EVIDENCE/build/" 2>/dev/null || true
cp -a out/greia-os-${PROFILE}-payload-image-profile.json "$EVIDENCE/build/" 2>/dev/null || true
```

If the official builder fails: STOP. Do not copy `vendor/parent-app` into an older image as a workaround.

Write/install that exact installer image using the repository's current sanctioned physical-install procedure for this Acer. Revalidate the destination disk before any destructive write. Do not improvise a disk target from memory.

Record the exact installer-image SHA-256 and physical target identity in:

```text
$EVIDENCE/build/INSTALLATION.txt
```

After installation, boot the Acer normally into Greia.

---

## 6. Acer service and installed-runtime integrity

Use an owner-approved maintenance console/TTY on the physical Acer. Do not enable a new remote service merely for this gate.

Record:

```bash
uname -a | tee acer-uname.txt
cat /etc/greia-os/build-info | tee acer-build-info.txt
cat /etc/greia-os/image-profile.json | tee acer-image-profile.json
systemctl status greia-parent --no-pager | tee greia-parent-status.txt
journalctl -u greia-parent -b --no-pager | tee greia-parent-journal.txt
```

Move those files into `$EVIDENCE/acer/` when collecting the bundle.

Run the installed integrity verifier exactly:

```bash
PYTHONPATH=/opt/greia-os/src python3 -m greia_parent.parent_client_integrity \
  --root /usr/share/greia-parent-app \
  --manifest /opt/greia-os/runtime/parent-app-client.manifest.json \
  --pin /opt/greia-os/runtime/parent-app-client.toml \
  | tee parent-client-integrity.txt
```

Expected:

```text
Greia Parent client integrity OK: 75ee275771c495dc187efb5275732ea10c10af4b
```

Now list installed files:

```bash
find /usr/share/greia-parent-app -type f -printf '%P\n' | LC_ALL=C sort \
  | tee parent-client-files.txt
```

The list must contain exactly the manifest files and MUST NOT contain:

```text
src/demo_api.js
src/demo_management_api.js
```

Confirm no manual/runtime drift:

```bash
find /usr/share/greia-parent-app -type l -print | tee parent-client-symlinks.txt
test ! -s parent-client-symlinks.txt
```

Check service log for integrity, traceback or static-client errors:

```bash
grep -Eai 'integrity failure|traceback|demo|sample|static.*(missing|error)' greia-parent-journal.txt \
  > parent-client-suspicious-log-lines.txt || true
```

Review that output manually. Any real integrity/static failure: STOP.

---

## 7. Open the real Parent URL and pair normally

From a second real browser device on the same network, open:

```text
http://<ACER-IP>:8766/
```

Do not append query parameters. In particular, do not use `?demo=1`.

Capture screenshot:

```text
screenshots/01-pairing.png
```

The page must be the polished Greia Parents pairing screen served by the Acer.

Pair using the normal Greia pairing token/flow shown by the actual device. Do not read or edit the credential database directly.

After pairing, capture:

```text
screenshots/02-home-real.png
screenshots/03-children-real.png
screenshots/04-activities-real.png
screenshots/05-device-real.png
```

The UI must show the real Acer/device name and actual child/profile/Activity data already present on the Acer. Cross-check at least:

- child/profile names against the Acer profile registry;
- Activity names/count against the actual installed catalogue;
- usage counters/limits against the current Greia state;
- device uptime/storage/memory against the running Acer.

If the UI contains sample/demo identities, invented SSIDs, obviously fabricated usage, or data that cannot be reconciled with Acer state: STOP.

---

## 8. Capture authenticated API evidence without leaking the credential

In browser DevTools on the paired browser, obtain the current per-device credential from the browser's own local storage only for this test session. The storage key begins:

```text
greia.parent.v1.credential:
```

Do NOT write the token into evidence files or the final ZIP.

Use it only in an ephemeral shell variable on the browser/test machine:

```bash
export ACER_ORIGIN='http://<ACER-IP>:8766'
read -rsp 'Paste paired browser credential: ' GREIA_PARENT_TOKEN; echo
```

Capture real API payloads with secrets absent from output:

```bash
curl -fsS -H "Authorization: Bearer $GREIA_PARENT_TOKEN" "$ACER_ORIGIN/api/v1" \
  | python3 -m json.tool > api-index.json
curl -fsS -H "Authorization: Bearer $GREIA_PARENT_TOKEN" "$ACER_ORIGIN/api/v1/system" \
  | python3 -m json.tool > api-system.json
curl -fsS -H "Authorization: Bearer $GREIA_PARENT_TOKEN" "$ACER_ORIGIN/api/v1/profiles" \
  | python3 -m json.tool > api-profiles.json
curl -fsS -H "Authorization: Bearer $GREIA_PARENT_TOKEN" "$ACER_ORIGIN/api/v1/activities" \
  | python3 -m json.tool > api-activities.json
curl -fsS -H "Authorization: Bearer $GREIA_PARENT_TOKEN" "$ACER_ORIGIN/api/v1/usage-limits" \
  | python3 -m json.tool > api-usage-limits.json
curl -fsS -H "Authorization: Bearer $GREIA_PARENT_TOKEN" "$ACER_ORIGIN/api/v1/settings/system-controls" \
  | python3 -m json.tool > api-system-controls-initial.json
```

Move these JSON files into `$EVIDENCE/browser/`.

Immediately clear the shell credential after API capture when not actively needed:

```bash
unset GREIA_PARENT_TOKEN
```

Never place request headers, browser local-storage dumps or the bearer token in the returned bundle.

---

## 9. Wi-Fi truthfulness gate

Inspect `browser/api-index.json`.

### If `network.manage` is false

This is the expected state on an image where the unprivileged Parent service cannot genuinely manage iwd state.

The Device page MUST visibly show a polished message equivalent to:

```text
Wi-Fi changes aren't available from Greia Parents on this device.
Use Greia's local network setup on the device instead.
```

Capture:

```text
screenshots/06-wifi-unavailable.png
```

There must be no fake SSID list and no usable Connect button.

### If `network.manage` is true

Do NOT accept the capability merely because it is true. The list must be a real scan of the environment. Verify at least one displayed SSID against a separately observed nearby network. Attempt connection only to an owner-approved real network and verify the Acer's actual network association changes.

Any synthetic/sample SSID or successful connection to an SSID that was not present in the real scan: STOP.

---

## 10. Identify the actual ALSA output control

On the Acer maintenance console, before changing volume from the browser:

```bash
amixer scontrols | tee alsa-scontrols.txt
for control in Master Speaker PCM; do
  {
    echo "===== $control ====="
    amixer get "$control" 2>&1 || true
  } >> alsa-before.txt
done
```

The Greia backend intentionally tries `Master`, then `Speaker`, then `PCM`. Do not hard-code a different control into source during acceptance.

Copy these files to `$EVIDENCE/volume/`.

---

## 11. Real browser -> API -> ALSA volume gate

Re-establish the ephemeral browser credential in the test-machine shell:

```bash
export ACER_ORIGIN='http://<ACER-IP>:8766'
read -rsp 'Paste paired browser credential: ' GREIA_PARENT_TOKEN; echo
```

For each target volume below, perform the change using the **visible Parent UI first**, not curl:

```text
0%
35%
70%
100%
```

For every target `N`:

1. set `N` in the Parent **Speaker output** card;
2. click the normal Apply/Save control;
3. wait 1 second only to allow the hardware-session watcher to converge;
4. on the Acer, record all three ALSA candidates;
5. from the paired API, perform a fresh GET;
6. confirm the physical speaker level actually changed when audible output is available.

Use these evidence commands after each UI submission:

```bash
# Acer console
for control in Master Speaker PCM; do
  {
    echo "===== $control ====="
    amixer get "$control" 2>&1 || true
  } >> "alsa-after-N.txt"
done

# paired browser/test machine
curl -fsS -H "Authorization: Bearer $GREIA_PARENT_TOKEN" \
  "$ACER_ORIGIN/api/v1/settings/system-controls" \
  | python3 -m json.tool > "api-system-controls-after-N.json"
```

Replace `N` in the filenames with `0`, `35`, `70`, or `100`.

PASS for each target requires ALL of:

- UI shows the submitted value after refresh;
- authenticated PUT performed by the UI succeeded;
- fresh GET returns `volume_percent = N`;
- one of the actual ALSA `Master`/`Speaker`/`PCM` controls reflects the requested level within the normal ALSA integer/rounding tolerance;
- physical output behaves consistently with the setting.

A UI-only change or API-only change is FAILURE.

---

## 12. Real mute gate

Using the visible Parent UI:

1. enable mute;
2. wait 1 second;
3. record ALSA and fresh API state;
4. confirm sound is physically muted;
5. disable mute;
6. wait 1 second;
7. record ALSA and fresh API state;
8. confirm sound returns without changing the selected volume unexpectedly.

Evidence filenames:

```text
volume/alsa-muted.txt
volume/api-system-controls-muted.json
volume/alsa-unmuted.txt
volume/api-system-controls-unmuted.json
```

PASS requires API `muted` and ALSA on/off state to agree both ways.

---

## 13. Hardware-key convergence gate

Set browser volume to 35% and leave the Parent page open.

On the **physical Acer keyboard**, press the real volume-up key once. Do not inject a synthetic key remotely for this proof.

Then:

1. record ALSA state immediately;
2. perform a fresh authenticated GET of `/api/v1/settings/system-controls`;
3. use the Parent Refresh button once;
4. confirm the browser updates to the hardware-key result.

Repeat with the physical mute key if the Acer exposes one.

Evidence:

```text
volume/hardware-key-alsa.txt
volume/hardware-key-api.json
screenshots/07-hardware-key-converged.png
```

PASS requires physical key -> hardware/shared state -> fresh API/browser convergence. A browser that remains stale after explicit Refresh is FAILURE.

---

## 14. Partial-update stale-form safety gate

This proves the browser does not overwrite a hardware-key change to an untouched field.

1. In Parent UI, open the Speaker output card with mute OFF and do not submit yet.
2. On the physical Acer, press the mute key so mute becomes ON.
3. Verify a fresh API GET now says `muted: true`.
4. In the still-open browser form, change **only volume** to 70% and submit.
5. Fresh GET again.
6. Record ALSA again.

Expected final state:

```text
volume_percent = 70
muted = true
```

If submitting volume restores stale `muted=false`, STOP: this is a production race/clobber bug.

Then restore a normal audible state using the visible Parent UI after evidence is captured.

---

## 15. Real Activity/child controls mutation gate

Choose one harmless reversible Parent control backed by actual child state, for example a daily usage limit or one Activity visibility override.

Before mutation:

- record the real API/state value;
- capture the corresponding Parent page.

Change it through the Parent UI. Then:

- refresh/re-read the API;
- verify the child launcher/effective catalogue or usage policy on the Acer actually changes accordingly;
- restore the original value through the Parent UI;
- verify restoration.

Do not edit the policy JSON directly.

This gate is mandatory because a polished Parent page that cannot affect the child system is not acceptance.

Evidence names should begin:

```text
browser/real-policy-before-
browser/real-policy-after-
screenshots/08-real-policy-
```

---

## 16. Responsive/polish review

### Physical Acer

At the Acer's real 1024x600-class display, review every child-facing Greia screen relevant to the flow and the Parent pairing information if locally shown. For the web Parent UI itself, use a browser viewport of exactly **1024x600** on the paired browser and capture:

```text
screenshots/10-1024x600-home.png
screenshots/11-1024x600-children.png
screenshots/12-1024x600-activities.png
screenshots/13-1024x600-device.png
```

### Narrow/mobile

Use the **same real Acer production URL and same paired API**, not demo mode, at **390x844** and capture:

```text
screenshots/20-390x844-home.png
screenshots/21-390x844-children.png
screenshots/22-390x844-activities.png
screenshots/23-390x844-device.png
```

For both viewport classes verify:

- no horizontal page overflow;
- no clipped primary action;
- readable labels and values;
- no overlapping cards/dialogs;
- pairing/loading/error/unavailable states are visually intentional;
- destructive controls remain clearly separated/confirmed;
- system output controls are understandable without developer terminology;
- Wi-Fi unavailable state is visible when capability is false;
- no demo/sample banner or sample data;
- no persistent spinner after the real API is ready.

Open browser DevTools Console and Network during the ready-state review. Save a screenshot or text note of any errors. Expected: no feature-caused console exception and no failed requests other than an expected authorization transition during initial pairing.

---

## 17. Final service/log check

After all browser mutations:

```bash
systemctl status greia-parent --no-pager > greia-parent-status-final.txt
journalctl -u greia-parent -b --no-pager > greia-parent-journal-final.txt
journalctl -u greia-launcher -b --no-pager > greia-launcher-journal-final.txt
```

Run the integrity verifier again:

```bash
PYTHONPATH=/opt/greia-os/src python3 -m greia_parent.parent_client_integrity \
  --root /usr/share/greia-parent-app \
  --manifest /opt/greia-os/runtime/parent-app-client.manifest.json \
  --pin /opt/greia-os/runtime/parent-app-client.toml \
  > parent-client-integrity-final.txt
```

It must still PASS. No test should have modified the installed browser files.

---

## 18. Evidence bundle

Collect all Acer-generated text files into the corresponding project-local evidence folders. Ensure the bearer credential, pairing token, Wi-Fi password and any private SSH key are NOT present.

Create:

```text
$EVIDENCE/RESULT.md
```

Use exactly this schema:

```text
PARENT_REAL_RUNTIME_FINAL_ACCEPTANCE
candidate_head: <40-char Greia SHA>
required_integration_ancestor: 0f152be9233a311e90d243d7ba4da70ee022b66f
parent_revision: 75ee275771c495dc187efb5275732ea10c10af4b
acer_profile: <exact profile>
installer_sha256: <sha256>
source_gate: PASS|FAIL|INCOMPLETE
installed_integrity: PASS|FAIL|INCOMPLETE
real_pairing: PASS|FAIL|INCOMPLETE
real_data: PASS|FAIL|INCOMPLETE
wifi_truthfulness: PASS|FAIL|INCOMPLETE
volume_real_hardware: PASS|FAIL|INCOMPLETE
mute_real_hardware: PASS|FAIL|INCOMPLETE
hardware_key_convergence: PASS|FAIL|INCOMPLETE
partial_update_safety: PASS|FAIL|INCOMPLETE
real_child_policy_mutation: PASS|FAIL|INCOMPLETE
responsive_1024x600: PASS|FAIL|INCOMPLETE
responsive_390x844: PASS|FAIL|INCOMPLETE
console_and_service_logs: PASS|FAIL|INCOMPLETE
verdict: PASS|FAIL|INCOMPLETE
first_failure: <NONE or exact step/command/observation>
notes: <brief factual notes only>
```

`verdict: PASS` is allowed only if every preceding required line is PASS.

Finally create one return archive from the project root:

```bash
python3 - <<'PY'
from pathlib import Path
import zipfile

root = Path('tmp/PARENT_REAL_RUNTIME_FINAL_2026-09-03')
out = Path('tmp/RETURN_BUNDLE_PARENT_REAL_RUNTIME_FINAL_2026-09-03.zip')
with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(root.rglob('*')):
        if path.is_file():
            archive.write(path, path.relative_to(root.parent))
print(out)
PY
```

Return exactly:

```text
tmp/RETURN_BUNDLE_PARENT_REAL_RUNTIME_FINAL_2026-09-03.zip
```

plus the exact Greia `HEAD` and the final verdict. Do not return secrets separately.

---

## 19. Failure rule

At the first real failure:

1. stop the numbered acceptance;
2. preserve exact command/action, exit code, output, logs and screenshots;
3. write the first failure into `RESULT.md`;
4. set later unexecuted gates to `INCOMPLETE`;
5. create the return bundle anyway;
6. do not patch source or system permissions inside this frozen attempt.

A clean first-failure bundle is more useful than a rerun engineered to look green.
