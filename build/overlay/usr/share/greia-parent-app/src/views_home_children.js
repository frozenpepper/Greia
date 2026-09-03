import { el, icon, button, humanBytes, humanUptime, humanActivityTime, dailyLimitLabel, activityName, categoryIcon, activityCategory, challengeName, profileSubtitle } from "./ui.js";

const remainingActivityLabel=(seconds)=>{
  if(seconds===0)return"Finished for today";
  if(seconds===null||seconds===undefined)return"Unlimited";
  return`${humanActivityTime(seconds)} left`;
};

const remainingActivitySummary=(seconds)=>{
  if(seconds===0)return"Finished for today";
  if(seconds===null||seconds===undefined)return"Unlimited today";
  return`${humanActivityTime(seconds)} remaining today`;
};

const usedActivitySummary=(seconds)=>`${humanActivityTime(seconds,{unlimited:"0 min",zero:"0 min"})} used today`;

export function installHomeChildrenViews(proto){
  proto._home=function(snapshot){
    const selected=this._selectedProfile(snapshot),supportsUsage=Boolean(snapshot.index?.capabilities?.["usage_limits.manage"]),visible=snapshot.activityPolicy?.effective_activity_ids?.length??snapshot.activities.length,stars=Number(snapshot.progress?.reward_balances?.star||0),root=el("div","home-workspace");
    const remaining=supportsUsage?snapshot.profileUsageLimit?.effective_remaining_seconds:undefined;
    const timeValue=!supportsUsage?"Unavailable":snapshot.profileUsageLimit?remainingActivityLabel(remaining):"Unavailable";

    const overview=el("section","overview-panel"),intro=el("div","overview-intro");
    intro.append(el("p","section-kicker","Current child"),el("h2","",selected?selected.display_name:"No child selected"),el("p","",selected?profileSubtitle(selected):"Add a child profile to start personalising Greia."));
    const primary=el("div","overview-actions");
    primary.append(button("Manage children",{iconName:"children",className:"button secondary",onClick:()=>this.navigate("children")}),button("Manage Activities",{iconName:"sparkles",onClick:()=>this.navigate("activities")}));
    intro.append(primary);
    const metrics=el("div","overview-metrics");
    metrics.append(this._metric("Activities visible",visible,"eye"),this._metric("Activity time left",timeValue,"activity"),this._metric("Stars collected",stars,"star"));
    overview.append(intro,metrics);root.append(overview);

    const columns=el("div","home-columns");
    const recent=el("section","section-panel");recent.append(this._sectionHeading("Recent activity",selected?`What ${selected.display_name} used recently.`:"Recent child sessions."));
    if(selected&&snapshot.progress?.recent_sessions?.length){const list=el("div","plain-list");for(const session of snapshot.progress.recent_sessions.slice(0,6)){const activity=snapshot.activities.find(a=>a.activity_id===session.activity_id);const row=el("div","plain-row"),mark=el("div","row-icon");mark.append(icon(categoryIcon(activityCategory(activity))));const copy=el("div","row-copy");copy.append(el("strong","",activity?activityName(activity):session.activity_id),el("span","",session.exit_reason==="normal"?"Finished":"Recent session"));row.append(mark,copy);list.append(row);}recent.append(list);}else recent.append(this._empty("activity","Nothing recent yet","Recent sessions will appear here."));

    const device=el("section","section-panel");device.append(this._sectionHeading("This Greia","Everyday device status and settings."));
    const deviceList=el("div","plain-list");deviceList.append(this._statusRow("device","System",`Up for ${humanUptime(snapshot.system?.uptime_seconds)}`),this._statusRow("activity","Storage",`${humanBytes(snapshot.system?.disk_free_bytes)} free`));if(snapshot.language?.selected?.name||snapshot.language?.locale)deviceList.append(this._statusRow("globe","Language",snapshot.language.selected?.name||snapshot.language.locale));if(supportsUsage&&snapshot.usageLimits)deviceList.append(this._statusRow("activity","Shared Activity limit",dailyLimitLabel(snapshot.usageLimits.daily_minutes)));device.append(deviceList,button("Open device settings",{iconName:"settings",className:"button secondary full-width",onClick:()=>this.navigate("device")}));
    columns.append(recent,device);root.append(columns);
    return root;
  };

  proto._metric=function(label,value,iconName){const item=el("div","overview-metric"),mark=el("div","metric-icon");mark.append(icon(iconName));const copy=el("div");copy.append(el("strong","",value),el("span","",label));item.append(mark,copy);return item;};
  proto._sectionHeading=function(title,subtitle){const head=el("div","section-heading");head.append(el("h2","",title),el("p","",subtitle));return head;};

  proto._children=function(snapshot){
    const supportsPresentation=Boolean(snapshot.index?.capabilities?.["profiles.presentation"]),supportsUsage=Boolean(snapshot.index?.capabilities?.["usage_limits.manage"]),canManage=Boolean(snapshot.index?.capabilities?.["profiles.manage"]),action=document.getElementById("page-actions");
    if(canManage)action.append(button("Add child",{iconName:"plus",onClick:()=>this._openChildEditor(snapshot,null)}));
    const root=el("div","children-manager");
    const intro=el("section","manager-summary"),copy=el("div","manager-summary-copy");copy.append(el("strong","",`${snapshot.profiles.length} child ${snapshot.profiles.length===1?"profile":"profiles"}`),el("span","","Profiles keep each child's progress, creations, preferences and Activity choices separate."));intro.append(copy);root.append(intro);

    if(supportsUsage){
      const usage=el("section","manager-summary"),usageCopy=el("div","manager-summary-copy"),usageCounts=el("div","summary-counts"),device=snapshot.usageLimits;
      usageCopy.append(el("strong","","Daily Activity time"),el("span","","Only time spent inside Activities counts. Home, profile choice and Parent management do not use the budget."));
      usageCounts.append(this._pill(device?dailyLimitLabel(device.daily_minutes):"Unavailable","device",device?.exhausted?"warn":"info"));
      if(device)usageCounts.append(this._pill(usedActivitySummary(device.used_seconds),"activity",""));
      usageCounts.append(button("Set shared limit",{iconName:"edit",className:"button small secondary",onClick:()=>this._openUsageLimitEditor(snapshot,null)}));
      usage.append(usageCopy,usageCounts);root.append(usage);
    }

    const list=el("section","children-list");
    for(const profile of snapshot.profiles){
      const row=el("article","child-row"),identity=el("div","child-row-identity"),copy=el("div","child-row-copy");identity.append(this._avatar(profile,true));copy.append(el("h3","",profile.display_name),el("p","",profileSubtitle(profile)));identity.append(copy);
      const facts=el("div","child-row-facts");facts.append(this._pill(profile.approximate_age==null?"Age not set":`About ${profile.approximate_age}`,"children",profile.approximate_age==null?"":"info"),this._pill(challengeName(profile.challenge_preference),"sparkles","warm"),this._pill(profile.has_secret?"Password set":"No password","lock",profile.has_secret?"ok":""));if(supportsPresentation){const label={boy:"Boy style",girl:"Girl style",neutral:"Neutral style"}[profile.presentation]||"Neutral style";facts.append(this._pill(label,"palette","info"));}if(supportsUsage&&snapshot.selectedProfileId===profile.profile_id&&snapshot.profileUsageLimit){facts.append(this._pill(dailyLimitLabel(snapshot.profileUsageLimit.profile_daily_minutes),"activity",snapshot.profileUsageLimit.exhausted?"warn":"info"),this._pill(remainingActivityLabel(snapshot.profileUsageLimit.effective_remaining_seconds),"activity",snapshot.profileUsageLimit.exhausted?"warn":"ok"));}
      const actions=el("div","child-row-actions");actions.append(button("Activities",{iconName:"sparkles",className:"button small secondary",onClick:async()=>{await this.state.selectProfile(profile.profile_id);this.navigate("activities");}}));if(supportsUsage)actions.append(button("Time limit",{iconName:"activity",className:"button small secondary",onClick:()=>this._openUsageLimitEditor(snapshot,profile)}));if(canManage)actions.append(button("Edit",{iconName:"edit",className:"button small secondary",onClick:()=>this._openChildEditor(snapshot,profile)}));actions.append(button(snapshot.selectedProfileId===profile.profile_id?"Selected":"Select",{iconName:"star",className:"button small ghost",onClick:async()=>{await this.state.selectProfile(profile.profile_id);this.showFlash(`${profile.display_name} selected for this Parent view.`);}}));
      row.append(identity,facts,actions);list.append(row);
    }
    if(!snapshot.profiles.length){const empty=el("div","manager-empty");empty.append(icon("children"),el("strong","","No children yet"),el("span","","Add the first child profile to begin."));if(canManage)empty.append(button("Add child",{iconName:"plus",onClick:()=>this._openChildEditor(snapshot,null)}));list.append(empty);}
    root.append(list);return root;
  };

  proto._openUsageLimitEditor=async function(snapshot,profile){
    const profileMode=Boolean(profile),title=profileMode?`${profile.display_name}'s Activity time`:"Shared Activity time",subtitle=profileMode?"Set a personal daily limit for this child. The shared Greia limit still applies if it is lower.":"Set the daily Activity-time budget shared by all children on this Greia.",d=this._openDialog({title,subtitle,iconName:"activity"}),body=d.querySelector(".dialog-content"),form=el("form","form-grid");
    let status=null;
    try{status=profileMode?await this.api.profileUsageLimit(profile.profile_id):await this.api.usageLimits();}catch(error){d.close();this.showFlash(error?.message||"Could not load Activity time settings.","error");return;}
    const current=profileMode?status.profile_daily_minutes:status.daily_minutes,limitField=this._textField("Minutes per day","daily_minutes",current==null?"60":String(current)),limitInput=limitField.querySelector("input"),unlimited=this._checkField("No daily limit","unlimited",current==null),unlimitedInput=unlimited.querySelector("input");
    limitInput.type="number";limitInput.min="1";limitInput.max="1440";limitInput.step="1";limitInput.inputMode="numeric";
    const sync=()=>{limitInput.disabled=unlimitedInput.checked;};unlimitedInput.addEventListener("change",sync);sync();
    form.append(limitField,unlimited,el("p","help full field","Greia counts only real Activity runtime. Time on Home, the profile picker and Parent screens is not charged. Limits reset on the next accounting day."));
    const remaining=profileMode?status.effective_remaining_seconds:status.remaining_seconds,used=profileMode?status.profile_used_seconds:status.used_seconds,summary=el("div","field full");summary.append(el("strong","",remainingActivitySummary(remaining)),el("span","help",`${usedActivitySummary(used)}.`));form.append(summary);
    const actions=el("div","form-actions"),save=button("Save time limit",{iconName:"check",type:"submit"});actions.append(save);form.append(actions);
    form.addEventListener("submit",async event=>{event.preventDefault();const dailyMinutes=unlimitedInput.checked?null:Number(limitInput.value);if(dailyMinutes!==null&&(!Number.isInteger(dailyMinutes)||dailyMinutes<1||dailyMinutes>1440)){this.showFlash("Choose between 1 and 1440 minutes, or select no daily limit.","error");return;}save.disabled=true;try{if(profileMode)await this.api.updateProfileUsageLimit(profile.profile_id,dailyMinutes);else await this.api.updateUsageLimits(dailyMinutes);if(!profileMode||snapshot.selectedProfileId===profile?.profile_id)await this.state.refreshUsageLimits();d.close();this.showFlash(profileMode?`${profile.display_name}'s Activity time updated.`:"Shared Activity time updated.");}catch(error){this.showFlash(error?.message||"Could not update Activity time.","error");}finally{save.disabled=false;}});
    body.append(form);
  };

  proto._openChildEditor=function(snapshot,profile){
    const isNew=!profile,supportsPresentation=Boolean(snapshot.index?.capabilities?.["profiles.presentation"]),d=this._openDialog({title:isNew?"Add a child":`Edit ${profile.display_name}`,subtitle:isNew?"Create a separate Greia space for this child.":"Progress and creations stay with this profile.",iconName:"children"}),body=d.querySelector(".dialog-content"),form=el("form","form-grid");
    const name=this._textField("Name","display_name",profile?.display_name||""),avatar=this._selectField("Avatar","avatar_id",(snapshot.system?.profile_policy?.avatars||["unicorn","owl","robot","rabbit","star"]).map(v=>[v,String(v).replaceAll("_"," ")]),profile?.avatar_id||"unicorn"),ages=[["","Not specified"],...Array.from({length:18},(_,i)=>[String(i+1),`About ${i+1}`])],age=this._selectField("Approximate age","approximate_age",ages,profile?.approximate_age==null?"":String(profile.approximate_age)),challenge=this._selectField("Challenge preference","challenge_preference",[["automatic","Automatic"],["easier","Easier"],["standard","Standard"],["harder","More challenging"]],profile?.challenge_preference||"automatic");
    form.append(name,avatar,age,challenge);
    if(supportsPresentation){const presentation=this._selectField("Style & wording","presentation",[["neutral","Neutral"],["boy","Boy"],["girl","Girl"]],profile?.presentation||"neutral");form.append(presentation,el("p","help full field","This only provides a gentle starting colour style and language agreement such as bravo/brava. It never changes Activity access, interests, challenge or rewards."));}
    const pass=this._selectField("Child password","secret_action",isNew?[["keep","No password"],["set","Set a password"]]:[["keep","Keep current"],["set","Set or replace"],["clear","Remove password"]],"keep"),secret=this._textField("New password","secret","","password"),mask=this._checkField("Hide the password while the child types","mask_secret",Boolean(profile?.mask_secret));form.append(pass,secret,mask,el("p","help full field","Approximate age is optional and is used only for Activity discovery guidance. Greia does not need a date of birth."));
    const actions=el("div","form-actions");
    if(!isNew)actions.append(button("Delete child",{iconName:"trash",className:"button danger",onClick:async()=>{if(!await this.confirm(`Delete ${profile.display_name}?`,"This removes this child profile and its profile-scoped data from this Greia."))return;try{await this.api.deleteProfile(profile.profile_id);d.close();await this.state.refresh();this.showFlash(`${profile.display_name} deleted.`);}catch(error){this.showFlash(error?.message||"Could not delete child.","error");}}}));
    const save=button(isNew?"Add child":"Save changes",{iconName:"check",type:"submit"});actions.append(save);form.append(actions);
    form.addEventListener("submit",async event=>{event.preventDefault();save.disabled=true;const data=new FormData(form),rawAge=String(data.get("approximate_age")||""),secretAction=String(data.get("secret_action")||"keep"),presentation=String(data.get("presentation")||profile?.presentation||"neutral"),payload={display_name:String(data.get("display_name")||"").trim(),avatar_id:String(data.get("avatar_id")||"unicorn"),approximate_age:rawAge?Number(rawAge):null,challenge_preference:String(data.get("challenge_preference")||"automatic"),secret_action:secretAction,secret:secretAction==="set"?String(data.get("secret")||""):"",mask_secret:data.get("mask_secret")==="on"};try{let saved;if(isNew){const {secret_action: _ignored, ...createPayload}=payload;saved=await this.api.createProfile(createPayload);}else saved=await this.api.updateProfile(profile.profile_id,payload);const profileId=saved?.profile_id||profile?.profile_id;if(supportsPresentation&&profileId)await this.api.updateProfilePresentation(profileId,{presentation,seedThemeIfUnset:true});d.close();await this.state.refresh();this.showFlash(isNew?`${payload.display_name} added.`:`${payload.display_name} updated.`);}catch(error){this.showFlash(error?.message||"Could not save child profile.","error");}finally{save.disabled=false;}});
    body.append(form);
  };
}
