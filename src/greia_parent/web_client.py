from __future__ import annotations


def render_parent_web_app() -> str:
    """Return the dependency-free Greia Parents HTML client.

    The page contains no privileged implementation knowledge. All state and
    mutations go through the same /api/v1 contract intended for future native
    parent clients.
    """

    return r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Greia Parents</title>
<style>
:root{--cream:#f6ecd1;--paper:#fffaf0;--ink:#3d2c1f;--accent:#f1b923;--muted:#76685d;--danger:#a83434;--ok:#2f7551}
*{box-sizing:border-box}body{margin:0;background:var(--cream);color:var(--ink);font-family:system-ui,-apple-system,sans-serif}
header{padding:1.1rem 1.2rem;background:#07152d;color:white;position:sticky;top:0;z-index:3}
header h1{font-size:1.25rem;margin:0}header p{opacity:.8;margin:.25rem 0 0;font-size:.9rem}
main{max-width:70rem;margin:auto;padding:1rem}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(17rem,1fr));gap:1rem}
section,.card{background:var(--paper);border-radius:1rem;padding:1rem;box-shadow:0 1px 3px #0001}
section{margin-bottom:1rem}h2{margin:.1rem 0 .8rem}h3{margin:.2rem 0}
label{display:block;font-weight:700;margin:.65rem 0 .25rem}input,select{width:100%;padding:.6rem;border:1px solid #0003;border-radius:.6rem;font:inherit;background:white}
input[type=checkbox]{width:auto}button{border:0;border-radius:.7rem;padding:.7rem .9rem;background:var(--accent);color:var(--ink);font:inherit;font-weight:800;cursor:pointer}
button.danger{background:var(--danger);color:white}button:disabled{opacity:.45;cursor:not-allowed}.row{display:flex;gap:.6rem;align-items:center;flex-wrap:wrap}
.muted{color:var(--muted)}.status{font-weight:800}.ok{color:var(--ok)}.error{color:var(--danger)}
code{background:#0001;padding:.1rem .25rem;border-radius:.25rem}.capability{display:flex;justify-content:space-between;gap:1rem;border-top:1px solid #0001;padding:.45rem 0}
ul{padding-left:1.2rem}.hidden{display:none}
</style>
</head>
<body>
<header><h1>Greia Parents</h1><p id="connection">Connecting to this Greia…</p></header>
<main>
<section>
  <h2>System</h2>
  <div id="system" class="grid"><div class="card muted">Loading…</div></div>
</section>

<section>
  <h2>Children</h2>
  <div id="profiles" class="grid"></div>
  <h3>Add child</h3>
  <form id="create-profile">
    <div class="grid">
      <label>Name<input name="display_name" maxlength="24" required></label>
      <label>Avatar<select name="avatar_id" id="new-avatar"></select></label>
      <label>Optional simple password<input name="secret" maxlength="32"></label>
    </div>
    <label><input type="checkbox" name="mask_secret"> Hide password while the child types</label>
    <button type="submit">Add child</button>
  </form>
</section>

<section>
  <h2>Mouse, touchpad and display</h2>
  <form id="hardware">
    <div class="grid">
      <label>Mouse speed<input type="range" name="mouse_speed" min="-1" max="1" step=".25"></label>
      <label>Touchpad speed<input type="range" name="touchpad_speed" min="-1" max="1" step=".25"></label>
      <label>Resolution<select name="resolution" id="resolution"></select></label>
    </div>
    <div class="row">
      <label><input type="checkbox" name="touchpad_tap"> Tap touchpad to click</label>
      <label><input type="checkbox" name="natural_scrolling"> Natural scrolling</label>
    </div>
    <button type="submit">Apply settings</button>
  </form>
</section>

<section>
  <h2>Activities</h2>
  <div id="activities" class="grid"></div>
</section>

<section>
  <h2>Parent devices</h2>
  <p class="muted">Each future parent client receives its own revocable credential. The current browser-pairing bootstrap is transitional.</p>
  <div id="devices" class="grid"></div>
</section>

<section>
  <h2>Coming through the same Parent API</h2>
  <div id="capabilities"></div>
  <p class="muted">Unavailable controls are not emulated with shell commands. They become available only when Greia exposes the corresponding typed platform service.</p>
</section>

<p id="message" class="status"></p>
</main>
<script>
const API="/api/v1";
const message=document.getElementById("message");

async function request(path, options={}) {
  const response=await fetch(API+path,{credentials:"same-origin",headers:{"Accept":"application/json","Content-Type":"application/json",...(options.headers||{})},...options});
  let body={};
  try { body=await response.json(); } catch (_) {}
  if(!response.ok) throw new Error(body?.error?.message || `Request failed (${response.status})`);
  return body;
}
function text(value){ return String(value ?? ""); }
function card(title, body){ const el=document.createElement("article"); el.className="card"; const h=document.createElement("h3"); h.textContent=title; el.append(h,body); return el; }
function lines(items){ const ul=document.createElement("ul"); for(const item of items){const li=document.createElement("li");li.textContent=item;ul.append(li)} return ul; }
function showError(error){ message.className="status error"; message.textContent=error.message; }

async function load() {
  try {
    const [index,system,profiles,activities,hardware,devices]=await Promise.all([
      request(""),request("/system"),request("/profiles"),request("/activities"),request("/settings/hardware"),request("/devices")
    ]);
    document.getElementById("connection").textContent=`Connected · Parent API v${index.api_version}`;

    const systemBox=document.getElementById("system"); systemBox.replaceChildren();
    const systemLines=[
      `Uptime: ${text(system.uptime_seconds)} s`,
      `Memory available: ${Math.round((system.memory_available_bytes||0)/1048576)} MiB`,
      `Disk free: ${Math.round((system.disk_free_bytes||0)/1048576)} MiB`,
      `Runtime API: ${text(system.runtime_api_version)}`
    ];
    systemBox.append(card("This Greia",lines(systemLines)));

    renderProfiles(profiles,system.profile_policy?.avatars || []);
    renderActivities(activities);
    renderHardware(hardware);
    renderDevices(devices);
    renderCapabilities(index.capabilities || {});
    message.textContent="";
  } catch(error) { showError(error); }
}

function renderProfiles(profiles,avatars){
  const box=document.getElementById("profiles"); box.replaceChildren();
  for(const profile of profiles){
    const body=document.createElement("div");
    body.append(lines([
      `Avatar: ${text(profile.avatar_id)}`,
      `Password: ${profile.has_secret ? "set" : "none"}`
    ]));
    const remove=document.createElement("button"); remove.className="danger"; remove.textContent="Delete";
    remove.onclick=async()=>{ if(!confirm(`Delete ${profile.display_name}?`)) return; try{await request(`/profiles/${encodeURIComponent(profile.profile_id)}`,{method:"DELETE"});await load()}catch(e){showError(e)} };
    body.append(remove);
    box.append(card(text(profile.display_name),body));
  }
  const select=document.getElementById("new-avatar"); select.replaceChildren();
  for(const avatar of avatars){const option=document.createElement("option");option.value=avatar;option.textContent=text(avatar).replaceAll("_"," ");select.append(option)}
}

function renderActivities(activities){
  const box=document.getElementById("activities"); box.replaceChildren();
  for(const activity of activities){
    box.append(card(text(activity.activity_id),lines([
      `Version: ${text(activity.version)}`,
      `Input: ${text(activity.input_profile)}`,
      `Languages: ${(activity.languages||[]).join(", ")}`
    ])));
  }
}

function renderHardware(hardware){
  const desired=hardware.desired || {};
  const form=document.getElementById("hardware");
  form.mouse_speed.value=desired.mouse_speed ?? 0;
  form.touchpad_speed.value=desired.touchpad_speed ?? 0;
  form.touchpad_tap.checked=!!desired.touchpad_tap;
  form.natural_scrolling.checked=!!desired.natural_scrolling;
  const select=document.getElementById("resolution"); select.replaceChildren();
  const choices=["auto",...(hardware.display_modes||[]).map(item=>item.id).filter(Boolean)];
  const unique=[...new Set(choices)];
  if(desired.resolution && !unique.includes(desired.resolution)) unique.push(desired.resolution);
  for(const value of unique){const option=document.createElement("option");option.value=value;option.textContent=value==="auto"?"Automatic":value;option.selected=value===desired.resolution;select.append(option)}
}

function renderDevices(devices){
  const box=document.getElementById("devices"); box.replaceChildren();
  if(!devices.length){box.append(card("Current browser",lines(["Using transitional pairing credential"])));return}
  for(const device of devices){
    const body=document.createElement("div"); body.append(lines([`Paired: ${text(device.created_at)}`]));
    const revoke=document.createElement("button"); revoke.className="danger"; revoke.textContent="Revoke";
    revoke.onclick=async()=>{if(!confirm(`Revoke ${device.display_name}?`))return;try{await request(`/devices/${encodeURIComponent(device.device_id)}`,{method:"DELETE"});await load()}catch(e){showError(e)}};
    body.append(revoke); box.append(card(text(device.display_name),body));
  }
}

function renderCapabilities(capabilities){
  const labels={
    "activities.install":"Install / update Activities",
    "backup.manage":"Backup / restore",
    "settings.audio":"Sound settings",
    "network.manage":"Network settings",
    "maintenance.ssh":"SSH maintenance"
  };
  const box=document.getElementById("capabilities");box.replaceChildren();
  for(const [key,label] of Object.entries(labels)){
    const row=document.createElement("div");row.className="capability";
    const name=document.createElement("span");name.textContent=label;
    const state=document.createElement("strong");state.textContent=capabilities[key]?"Available":"Not implemented yet";
    row.append(name,state);box.append(row);
  }
}

document.getElementById("create-profile").addEventListener("submit",async event=>{
  event.preventDefault(); const form=new FormData(event.currentTarget);
  try{
    await request("/profiles",{method:"POST",body:JSON.stringify({
      display_name:form.get("display_name"),avatar_id:form.get("avatar_id"),secret:form.get("secret")||"",mask_secret:form.get("mask_secret")==="on"
    })});
    event.currentTarget.reset(); await load();
  }catch(error){showError(error)}
});
document.getElementById("hardware").addEventListener("submit",async event=>{
  event.preventDefault(); const form=new FormData(event.currentTarget);
  try{
    await request("/settings/hardware",{method:"PUT",body:JSON.stringify({
      mouse_speed:Number(form.get("mouse_speed")),touchpad_speed:Number(form.get("touchpad_speed")),
      resolution:form.get("resolution"),touchpad_tap:form.get("touchpad_tap")==="on",natural_scrolling:form.get("natural_scrolling")==="on"
    })});
    await load();
  }catch(error){showError(error)}
});
load();
</script>
</body>
</html>"""
