import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { ParentApiClient } from "../src/api.js";

const root=dirname(dirname(fileURLToPath(import.meta.url)));
const read=(path)=>readFileSync(join(root,path),"utf8");
const jsonResponse=(status,body)=>({ok:status>=200&&status<300,status,headers:{get:()=>"application/json"},json:async()=>body,text:async()=>JSON.stringify(body)});

class MemoryCredentials {
  constructor(){this.values=new Map([["http://greia.local:8766","token"]]);}
  get(origin){return this.values.get(origin)||"";}
  set(origin,value){this.values.set(origin,value);}
  remove(origin){this.values.delete(origin);}
}

test("Activity removal uses typed DELETE route",async()=>{
  let seen;
  const api=new ParentApiClient({origin:"http://greia.local:8766",credentialStore:new MemoryCredentials(),fetchImpl:async(url,options)=>{seen={url,options};return jsonResponse(200,{removed:{activity_id:"org.greia.example",profile_data_preserved:true}});}});
  const result=await api.removeActivity("org.greia.example");
  assert.equal(seen.url,"http://greia.local:8766/api/v1/activities/org.greia.example");
  assert.equal(seen.options.method,"DELETE");
  assert.equal(seen.options.headers.Authorization,"Bearer token");
  assert.equal(result.removed.profile_data_preserved,true);
});

test("Activity removal rejects missing identity before network access",()=>{
  const api=new ParentApiClient({fetchImpl:async()=>{throw new Error("network should not run");}});
  assert.throws(()=>api.removeActivity("  "),TypeError);
});

test("Parent shell is a sidebar management workspace, not the old top dashboard",()=>{
  const index=read("index.html"),css=read("styles/app.css");
  assert.match(index,/class="sidebar"/);
  assert.match(index,/class="workspace"/);
  assert.match(index,/id="desktop-nav"/);
  assert.equal(index.includes("app-header"),false);
  assert.match(css,/grid-template-columns:var\(--sidebar\)/);
  assert.match(css,/\.activity-row/);
  assert.match(css,/\.child-row/);
});

test("Activities view exposes install and removable package management",()=>{
  const source=read("src/views_activities.js");
  assert.match(source,/tr\("activities\.install"\)/);
  assert.match(source,/activities\.remove/);
  assert.match(source,/removeActivity\(/);
  assert.match(source,/tr\("activities\.installed_parent"\)/);
  assert.match(source,/tr\("activities\.removed",\{name:/);
});
