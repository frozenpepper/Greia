import test from "node:test";
import assert from "node:assert/strict";
import { ParentApiClient } from "../src/api.js";

const jsonResponse=(status,body)=>({ok:status>=200&&status<300,status,headers:{get:()=>"application/json"},json:async()=>body,text:async()=>JSON.stringify(body)});

test("profile presentation update uses typed profile resource",async()=>{
  let seen;
  const api=new ParentApiClient({origin:"http://greia.local:8766",fetchImpl:async(url,options)=>{seen={url,options};return jsonResponse(200,{profile_id:"gaia",presentation:"girl",grammatical_gender:"feminine",theme_seeded:true});}});
  const result=await api.updateProfilePresentation("gaia",{presentation:"girl",seedThemeIfUnset:true});
  assert.equal(seen.url,"http://greia.local:8766/api/v1/profiles/gaia/presentation");
  assert.equal(seen.options.method,"PUT");
  assert.deepEqual(JSON.parse(seen.options.body),{presentation:"girl",seed_theme_if_unset:true});
  assert.equal(result.grammatical_gender,"feminine");
});

test("profile presentation rejects unknown values before network access",async()=>{
  const api=new ParentApiClient({fetchImpl:async()=>{throw new Error("should not run");}});
  await assert.rejects(()=>api.updateProfilePresentation("gaia",{presentation:"purple"}),TypeError);
});

test("Activity install rejects a generic ZIP filename before upload",()=>{
  const api=new ParentApiClient({fetchImpl:async()=>{throw new Error("should not run");}});
  const fakeFile={name:"activity.zip",arrayBuffer:async()=>new ArrayBuffer(0)};
  assert.throws(()=>api.installActivity(fakeFile),/\.greiaactivity/);
});

test("Activity install accepts the custom extension case-insensitively",async()=>{
  let called=false;
  const api=new ParentApiClient({fetchImpl:async()=>{called=true;return jsonResponse(201,{installed:{activity_id:"org.greia.example"}});}});
  const fakeFile={name:"ACTIVITY.GREIAACTIVITY",arrayBuffer:async()=>new ArrayBuffer(0)};
  await api.installActivity(fakeFile);
  assert.equal(called,true);
});
