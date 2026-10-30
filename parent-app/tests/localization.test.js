import test from "node:test";
import assert from "node:assert/strict";
import { CHROME_LOCALES, CHROME_TRANSLATIONS, getChromeLocale, setChromeLocale, tr } from "../src/localization.js";

test("four staged browser catalogues have identical keys and interpolation contracts", () => {
  assert.deepEqual(CHROME_LOCALES, ["en", "it", "es", "fr"]);
  assert.ok(Object.keys(CHROME_TRANSLATIONS).length >= 35);
  for (const [key, messages] of Object.entries(CHROME_TRANSLATIONS)) {
    assert.deepEqual(Object.keys(messages), CHROME_LOCALES, key);
    const tokens = value => [...value.matchAll(/\{([a-z_]+)\}/g)].map(x => x[1]).sort();
    for (const locale of CHROME_LOCALES) {
      assert.ok(messages[locale].trim(), `${key}/${locale}`);
      assert.deepEqual(tokens(messages[locale]), tokens(messages.en), `${key}/${locale}`);
    }
  }
});

test("staged locale switching translates text but does not advertise device languages", () => {
  const original = getChromeLocale();
  try {
    setChromeLocale("fr-FR");
    assert.equal(tr("device.language.title"), "Langue");
    assert.equal(tr("device.language.changed", { language: "Français" }), "Langue de Greia définie sur Français.");
    setChromeLocale("es-ES");
    assert.equal(tr("nav.children"), "Niños");
    setChromeLocale("it-IT");
    assert.equal(tr("nav.children"), "Bambini");
    assert.equal(tr("common.per_day", { time: "1 h" }), "1 h al giorno");
    assert.equal(tr("discovery.title.choose"), "Scegli un Greia");
    assert.equal(tr("auth.password_label"), "Password Greia");
    assert.equal(tr("device.sound.volume", { percent: 75 }), "Altoparlanti al 75%");
    setChromeLocale("zh-CN");
    assert.equal(getChromeLocale(), "en");
    assert.equal(tr("nav.home"), "Home");
    assert.throws(() => tr("device.language.changed"), /parameter/i);
    assert.throws(() => tr("not.a.key"), /Unknown Parent chrome/);
  } finally {
    setChromeLocale(original);
  }
});

test("deep device management messages are complete and preserve variable text", () => {
  assert.ok(Object.keys(CHROME_TRANSLATIONS).length >= 371);
  const dynamicKeys = [
    "device.wifi.connect_to", "device.wifi.connected",
    "device.paired.revoke_confirm", "device.update.received",
  ];
  for (const key of dynamicKeys) {
    for (const locale of CHROME_LOCALES) {
      assert.ok(CHROME_TRANSLATIONS[key][locale].length, `${key}/${locale}`);
    }
  }
  for (const key of ["device.update.package.title", "device.update.package.help", "device.update.package.send", "device.update.package.applying", "device.update.package.ready_to_restart"]) {
    for (const locale of CHROME_LOCALES) assert.ok(CHROME_TRANSLATIONS[key][locale].trim(), `${key}/${locale}`);
  }
  const previous = getChromeLocale();
  try {
    setChromeLocale("fr-FR");
    assert.equal(tr("device.update.received", { version: "5.3" }), "Mise à jour 5.3 reçue.");
    setChromeLocale("es-ES");
    assert.equal(tr("device.wifi.connect_to", { name: "CasaWiFi" }), "Conectar a CasaWiFi");
    setChromeLocale("it-IT");
    assert.equal(tr("device.parentpw.changed"), "Password genitori modificata.");
    assert.equal(tr("device.paired.revoke_confirm", { name: "Tablet" }), "Revocare Tablet?");
    assert.throws(() => tr("device.paired.revoke_confirm"), /parameter/);
  } finally {
    setChromeLocale(previous);
  }
});
