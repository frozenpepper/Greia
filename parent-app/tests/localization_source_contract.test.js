import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { CHROME_LOCALES, CHROME_TRANSLATIONS } from "../src/localization.js";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const fromSource = (name) => readFileSync(join(root, name), "utf8");
const JS_SOURCES = readdirSync(join(root, "src"))
  .filter((name) => name.endsWith(".js"))
  .map((name) => `src/${name}`);

test("browser source modules parse with the pinned Node toolchain", () => {
  // This uses local Node only. It neither starts a web server nor touches
  // Greia credentials, LAN devices, hosted CI, or live Parent settings.
  for (const path of JS_SOURCES) {
    const checked = spawnSync(process.execPath, ["--check", join(root, path)], {
      encoding: "utf8",
      timeout: 10000,
      windowsHide: true,
    });
    assert.equal(checked.status, 0, `${path}: ${checked.error?.message || checked.stderr}`);
  }
});

test("all referenced static Parent translation IDs resolve in every staged locale", () => {
  const references = new Set();
  for (const path of [...JS_SOURCES, "index.html"]) {
    const source = fromSource(path);
    for (const match of source.matchAll(/\btr\("([^"]+)"/g)) references.add(match[1]);
    for (const match of source.matchAll(/data-i18n(?:-aria|-title)?="([^"]+)"/g)) references.add(match[1]);
    assert.equal(source.includes("innerHTML"), false, `${path}: unsafe HTML assignment`);
  }
  assert.ok(references.size > 200, "expected real Home, Children and Activities integration");
  for (const key of references) {
    assert.ok(CHROME_TRANSLATIONS[key], `unknown source translation key ${key}`);
    for (const locale of CHROME_LOCALES) {
      assert.ok(CHROME_TRANSLATIONS[key][locale], `missing ${locale} translation for ${key}`);
    }
  }
});

test("management operations retain real API routes and never invent client languages", () => {
  const children = fromSource("src/views_home_children.js");
  const activities = fromSource("src/views_activities.js");
  const device = fromSource("src/views_device.js");
  assert.match(children, /updateProfileUsageLimit\(/);
  assert.match(children, /deleteProfile\(/);
  assert.match(children, /createProfile\(/);
  assert.match(activities, /updateActivityPolicy\(/);
  assert.match(activities, /installActivity\(/);
  assert.match(activities, /removeActivity\(/);
  assert.match(device, /snapshot\.language\?\.languages/);
  assert.match(fromSource("src/localization.js"), /Parent API remains the sole/); // Client strings are not capabilities.
  assert.equal(fromSource("src/localization.js").includes("updateLanguage("), false);
});
