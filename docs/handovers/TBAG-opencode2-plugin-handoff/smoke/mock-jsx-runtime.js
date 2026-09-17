// Minimal jsx-runtime mock: invokes function components (For/Show/Dashboard),
// records intrinsics as plain structures.
function build(type, props, key) {
  return { type, props: props ?? {}, key };
}
function jsx(type, props, key) {
  if (typeof type === "function") return type(props ?? {});
  return build(type, props, key);
}
function jsxs(type, props, key) {
  return build(type, props, key);
}
function Fragment(props) {
  return props?.children ?? null;
}
module.exports = { jsx, jsxs, Fragment };
