// Minimal SolidJS mock: just enough to execute slot render paths.
function createSignal(initial) {
  let value = initial;
  const get = () => value;
  get.$signal = true;
  const set = (next) => {
    value = typeof next === "function" ? next(value) : next;
    return value;
  };
  return [get, set];
}
function For(props) {
  const list = props.each ?? [];
  return list.map((item, idx) => props.children(item, () => idx));
}
function Show(props) {
  const cond = typeof props.when === "function" ? props.when() : props.when;
  if (cond) return typeof props.children === "function" ? props.children() : props.children;
  if ("fallback" in props) return typeof props.fallback === "function" ? props.fallback() : props.fallback;
  return null;
}
module.exports = { createSignal, For, Show };
