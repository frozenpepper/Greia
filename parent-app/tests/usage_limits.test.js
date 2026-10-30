import test from "node:test";
import assert from "node:assert/strict";

import { ParentApiClient } from "../src/api.js";
import { DemoManagementApiClient } from "./support/demo_management_api.js";
import { ParentAppState } from "../src/state.js";
import { humanActivityTime, dailyLimitLabel } from "../src/ui.js";

class MemoryCredentials {
  constructor(){ this.values=new Map(); }
  get(origin){ return this.values.get(origin)||""; }
  set(origin,value){ this.values.set(origin,value); }
  remove(origin){ this.values.delete(origin); }
}

const jsonResponse=(status,body)=>({
  ok:status>=200&&status<300,
  status,
  headers:{get:()=>"application/json"},
  json:async()=>body,
  text:async()=>JSON.stringify(body),
});

test("Parent Activity-time formatting distinguishes exhausted from zero usage",()=>{
  assert.equal(humanActivityTime(0),"Finished for today");
  assert.equal(humanActivityTime(0,{zero:"0 min"}),"0 min");
  assert.equal(humanActivityTime(null),"Unlimited");
  assert.equal(humanActivityTime(80*60),"1 h 20 min");
  assert.equal(dailyLimitLabel(60),"1 h / day");
  assert.equal(dailyLimitLabel(null),"Unlimited");
});

test("device usage-limit GET and PUT use the versioned authenticated API",async()=>{
  const credentials=new MemoryCredentials();
  credentials.set("http://greia.local:8766","secret-device-token");
  const calls=[];
  const api=new ParentApiClient({
    origin:"http://greia.local:8766",
    credentialStore:credentials,
    fetchImpl:async(url,options)=>{calls.push({url,options});return jsonResponse(200,{daily_minutes:60,remaining_seconds:2400});},
  });
  await api.usageLimits();
  await api.updateUsageLimits(60);
  assert.equal(calls[0].url,"http://greia.local:8766/api/v1/usage-limits");
  assert.equal(calls[0].options.method,"GET");
  assert.equal(calls[1].url,"http://greia.local:8766/api/v1/usage-limits");
  assert.equal(calls[1].options.method,"PUT");
  assert.deepEqual(JSON.parse(calls[1].options.body),{daily_minutes:60});
  assert.equal(calls[1].options.headers.Authorization,"Bearer secret-device-token");
});

test("profile usage-limit routes encode identity and accept unlimited",async()=>{
  const calls=[];
  const api=new ParentApiClient({
    origin:"http://greia.local:8766",
    fetchImpl:async(url,options)=>{calls.push({url,options});return jsonResponse(200,{profile_id:"child one",profile_daily_minutes:null});},
  });
  await api.profileUsageLimit("child one");
  await api.updateProfileUsageLimit("child one",null);
  assert.equal(calls[0].url,"http://greia.local:8766/api/v1/profiles/child%20one/usage-limit");
  assert.equal(calls[1].options.method,"PUT");
  assert.deepEqual(JSON.parse(calls[1].options.body),{daily_minutes:null});
});

test("usage-limit client rejects invalid minute values before network access",()=>{
  const api=new ParentApiClient({fetchImpl:async()=>{throw new Error("network must not run");}});
  assert.throws(()=>api.updateUsageLimits(0),TypeError);
  assert.throws(()=>api.updateUsageLimits(1441),TypeError);
  assert.throws(()=>api.updateProfileUsageLimit("child",1.5),TypeError);
  assert.throws(()=>api.profileUsageLimit(""),TypeError);
});

test("test fixture usage limits apply the most restrictive device or child budget",async()=>{
  const api=new DemoManagementApiClient();
  const initial=await api.profileUsageLimit("greta");
  assert.equal(initial.device_daily_minutes,120);
  assert.equal(initial.profile_daily_minutes,90);
  assert.equal(initial.effective_remaining_seconds,55*60);

  await api.updateUsageLimits(40);
  const deviceWins=await api.profileUsageLimit("greta");
  assert.equal(deviceWins.device_remaining_seconds,0);
  assert.equal(deviceWins.effective_remaining_seconds,0);
  assert.equal(deviceWins.exhausted,true);

  await api.updateUsageLimits(null);
  await api.updateProfileUsageLimit("greta",30);
  const profileWins=await api.profileUsageLimit("greta");
  assert.equal(profileWins.device_remaining_seconds,null);
  assert.equal(profileWins.profile_remaining_seconds,0);
  assert.equal(profileWins.effective_remaining_seconds,0);
});

test("Parent App state loads and switches selected-child usage status without a full refresh",async()=>{
  const api=new DemoManagementApiClient();
  const state=new ParentAppState(api);
  await state.initialize();
  assert.equal(state.snapshot.usageLimits.daily_minutes,120);
  assert.equal(state.snapshot.profileUsageLimit.profile_id,"greta");

  await state.selectProfile("gaia");
  assert.equal(state.snapshot.selectedProfileId,"gaia");
  assert.equal(state.snapshot.profileUsageLimit.profile_id,"gaia");

  await api.updateProfileUsageLimit("gaia",45);
  await state.refreshUsageLimits();
  assert.equal(state.snapshot.profileUsageLimit.profile_daily_minutes,45);
});
