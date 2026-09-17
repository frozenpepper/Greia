// Minimal @opencode/plugin/tui mock: Plugin.define passes the definition through.
// usePlugin returns a phase-recording keymap so the smoke test can prove no
// layer is created during render (the "provider is missing" crash class).
const Plugin = {
  define(definition) {
    return definition;
  },
};
function usePlugin() {
  return {
    keymap: {
      layer(input) {
        globalThis.__recordLayer(input);
      },
    },
  };
}
module.exports = { Plugin, usePlugin };
