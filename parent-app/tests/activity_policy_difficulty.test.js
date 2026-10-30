import test from "node:test";
import assert from "node:assert/strict";

import { DemoManagementApiClient } from "./support/demo_management_api.js";

test("difficulty range persists and filters fixed Activities while keeping adaptive overlaps",async()=>{
  const api=new DemoManagementApiClient();
  const policy=await api.updateActivityPolicy("greta",{
    visibility_mode:"show_all",
    difficulty_min:4,
    difficulty_max:4,
    overrides:{},
  });
  assert.equal(policy.difficulty_min,4);
  assert.equal(policy.difficulty_max,4);
  assert.equal(policy.effective_activity_ids.includes("org.greia.painting"),false);
  assert.equal(policy.effective_activity_ids.includes("org.greia.writing"),false);
  assert.equal(policy.effective_activity_ids.includes("org.greia.teatrino-fiabe"),true);
  assert.equal(policy.effective_activity_ids.includes("org.greia.labirinti"),true);
});

test("explicit per-Activity choices take precedence over automatic difficulty filtering",async()=>{
  const api=new DemoManagementApiClient();
  const policy=await api.updateActivityPolicy("greta",{
    visibility_mode:"recommended_only",
    difficulty_min:8,
    difficulty_max:10,
    overrides:{
      "org.greia.painting":"always_show",
      "org.greia.labirinti":"always_hide",
    },
  });
  assert.equal(policy.effective_activity_ids.includes("org.greia.painting"),true);
  assert.equal(policy.effective_activity_ids.includes("org.greia.labirinti"),false);
});

test("invalid reversed difficulty range is rejected",async()=>{
  const api=new DemoManagementApiClient();
  await assert.rejects(
    api.updateActivityPolicy("greta",{
      visibility_mode:"show_all",
      difficulty_min:7,
      difficulty_max:3,
      overrides:{},
    }),
    /Minimum difficulty/,
  );
});
