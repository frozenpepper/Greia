import { el, icon, button, humanBytes, humanUptime, humanActivityTime, dailyLimitLabel, activityName, categoryIcon, activityCategory, challengeName, profileSubtitle } from "./ui.js";
import { tr } from "./localization.js";

const remainingActivityLabel=(seconds)=>{
  if(seconds===0)return tr("common.finished_today");
  if(seconds===null||seconds===undefined)return tr("common.unlimited");
  return tr("children.time.remaining",{time:humanActivityTime(seconds)});
};

const remainingActivitySummary=(seconds)=>{
  if(seconds===0)return tr("common.finished_today");
  if(seconds===null||seconds===undefined)return tr("children.time.unlimited_today");
  return tr("children.time.remaining_today",{time:humanActivityTime(seconds)});
};

const usedActivitySummary=(seconds)=>tr("children.time.used_today",{time:humanActivityTime(seconds,{unlimited:"0 min",zero:"0 min"})});

export function installHomeChildrenViews(proto){
  proto._home=function(snapshot){
    const selected=this._selectedProfile(snapshot),supportsUsage=Boolean(snapshot.index?.capabilities?.["usage_limits.manage"]),visible=snapshot.activityPolicy?.effective_activity_ids?.length??snapshot.activities.length,stars=Number(snapshot.progress?.reward_balances?.star||0),root=el("div","home-workspace");
    const remaining=supportsUsage?snapshot.profileUsageLimit?.effective_remaining_seconds:undefined;
    const timeValue=!supportsUsage?tr("common.unavailable"):snapshot.profileUsageLimit?remainingActivityLabel(remaining):tr("common.unavailable");

    const overview=el("section","overview-panel"),intro=el("div","overview-intro");
    intro.append(el("p","section-kicker",tr("home.intro")),el("h2","",selected?selected.display_name:tr("home.no_child")),el("p","",selected?profileSubtitle(selected):tr("home.add_child_help")));
    const primary=el("div","overview-actions");
    primary.append(button(tr("home.manage_children"),{iconName:"children",className:"button secondary",onClick:()=>this.navigate("children")}),button(tr("home.manage_activities"),{iconName:"sparkles",onClick:()=>this.navigate("activities")}));
    const profileHeading=el("div","overview-profile"),profileCopy=el("div");
    if(selected)profileHeading.append(this._avatar(selected,true));
    profileCopy.append(...Array.from(intro.childNodes));profileHeading.append(profileCopy);intro.append(profileHeading,primary);
    const metrics=el("div","overview-metrics");
    metrics.append(this._metric(tr("home.visible"),visible,"eye"),this._metric(tr("home.time_left"),timeValue,"activity"),this._metric(tr("home.stars"),stars,"star"));
    const art=el("div","overview-art");art.setAttribute("aria-hidden","true");art.append(icon("book"),icon("sparkles"),icon("palette"));
    overview.append(intro,art);root.append(overview,metrics);

    const columns=el("div","home-columns");
    const recent=el("section","section-panel");recent.append(this._sectionHeading(tr("home.recent"),selected?tr("home.recent.child",{name:selected.display_name}):tr("home.recent.generic")));
    if(selected&&snapshot.progress?.recent_sessions?.length){const list=el("div","plain-list");for(const session of snapshot.progress.recent_sessions.slice(0,6)){const activity=snapshot.activities.find(a=>a.activity_id===session.activity_id);const row=el("div","plain-row"),mark=el("div","row-icon");mark.append(icon(categoryIcon(activityCategory(activity))));const copy=el("div","row-copy");copy.append(el("strong","",activity?activityName(activity):session.activity_id),el("span","",session.exit_reason==="normal"?tr("home.session.finished"):tr("home.session.recent")));row.append(mark,copy);list.append(row);}recent.append(list);}else recent.append(this._empty("activity",tr("home.session.empty"),tr("home.session.empty_help")));

    const device=el("section","section-panel");device.append(this._sectionHeading(tr("home.device"),tr("home.device.subtitle")));
    const deviceList=el("div","plain-list");deviceList.append(this._statusRow("device",tr("home.system"),tr("home.uptime",{time:humanUptime(snapshot.system?.uptime_seconds)})),this._statusRow("activity",tr("home.storage"),tr("home.free",{amount:humanBytes(snapshot.system?.disk_free_bytes)})));if(snapshot.language?.selected?.name||snapshot.language?.locale)deviceList.append(this._statusRow("globe",tr("home.language"),snapshot.language.selected?.name||snapshot.language.locale));if(supportsUsage&&snapshot.usageLimits)deviceList.append(this._statusRow("activity",tr("home.shared_limit"),dailyLimitLabel(snapshot.usageLimits.daily_minutes)));device.append(deviceList,button(tr("home.open_device"),{iconName:"settings",className:"button secondary full-width",onClick:()=>this.navigate("device")}));
    columns.append(recent,device);root.append(columns);
    return root;
  };

  proto._metric=function(label,value,iconName){const item=el("div","overview-metric"),mark=el("div","metric-icon");mark.append(icon(iconName));const copy=el("div");copy.append(el("strong","",value),el("span","",label));item.append(mark,copy);return item;};
  proto._sectionHeading=function(title,subtitle){const head=el("div","section-heading");head.append(el("h2","",title),el("p","",subtitle));return head;};

  proto._children=function(snapshot){
    const supportsPresentation=Boolean(snapshot.index?.capabilities?.["profiles.presentation"]),supportsUsage=Boolean(snapshot.index?.capabilities?.["usage_limits.manage"]),canManage=Boolean(snapshot.index?.capabilities?.["profiles.manage"]),action=document.getElementById("page-actions");
    if(canManage)action.append(button(tr("children.add"),{iconName:"plus",onClick:()=>this._openChildEditor(snapshot,null)}));
    const root=el("div","children-manager");
    const intro=el("section","manager-summary"),copy=el("div","manager-summary-copy");copy.append(el("strong","",tr(snapshot.profiles.length===1?"children.count":"children.count_many",{count:snapshot.profiles.length})),el("span","",tr("children.summary")));intro.append(copy);root.append(intro);

    if(supportsUsage){
      const usage=el("section","manager-summary"),usageCopy=el("div","manager-summary-copy"),usageCounts=el("div","summary-counts"),device=snapshot.usageLimits;
      usageCopy.append(el("strong","",tr("children.daily_time")),el("span","",tr("children.daily_time_help")));
      usageCounts.append(this._pill(device?dailyLimitLabel(device.daily_minutes):tr("common.unavailable"),"device",device?.exhausted?"warn":"info"));
      if(device)usageCounts.append(this._pill(usedActivitySummary(device.used_seconds),"activity",""));
      usageCounts.append(button(tr("children.shared_limit"),{iconName:"edit",className:"button small secondary",onClick:()=>this._openUsageLimitEditor(snapshot,null)}));
      usage.append(usageCopy,usageCounts);root.append(usage);
    }

    const list=el("section","children-list");
    for(const profile of snapshot.profiles){
      const row=el("article","child-row"),identity=el("div","child-row-identity"),copy=el("div","child-row-copy");identity.append(this._avatar(profile,true));copy.append(el("h3","",profile.display_name),el("p","",profileSubtitle(profile)));identity.append(copy);
      const facts=el("div","child-row-facts");facts.append(this._pill(profile.approximate_age==null?tr("children.age_not_set"):tr("common.about_age",{age:profile.approximate_age}),"children",profile.approximate_age==null?"":"info"),this._pill(challengeName(profile.challenge_preference),"sparkles","warm"),this._pill(profile.has_secret?tr("children.password_set"):tr("children.password_none"),"lock",profile.has_secret?"ok":""));if(supportsPresentation){const label={boy:tr("children.style.boy"),girl:tr("children.style.girl"),neutral:tr("children.style.neutral")}[profile.presentation]||tr("children.style.neutral");facts.append(this._pill(label,"palette","info"));}if(supportsUsage&&snapshot.selectedProfileId===profile.profile_id&&snapshot.profileUsageLimit){facts.append(this._pill(dailyLimitLabel(snapshot.profileUsageLimit.profile_daily_minutes),"activity",snapshot.profileUsageLimit.exhausted?"warn":"info"),this._pill(remainingActivityLabel(snapshot.profileUsageLimit.effective_remaining_seconds),"activity",snapshot.profileUsageLimit.exhausted?"warn":"ok"));}
      const actions=el("div","child-row-actions");actions.append(button(tr("children.activity"),{iconName:"sparkles",className:"button small secondary",onClick:async()=>{await this.state.selectProfile(profile.profile_id);this.navigate("activities");}}));if(supportsUsage)actions.append(button(tr("children.time_limit"),{iconName:"activity",className:"button small secondary",onClick:()=>this._openUsageLimitEditor(snapshot,profile)}));if(canManage)actions.append(button(tr("children.edit"),{iconName:"edit",className:"button small secondary",onClick:()=>this._openChildEditor(snapshot,profile)}));actions.append(button(snapshot.selectedProfileId===profile.profile_id?tr("children.selected"):tr("children.select"),{iconName:"star",className:"button small ghost",onClick:async()=>{await this.state.selectProfile(profile.profile_id);this.showFlash(tr("children.selected_flash",{name:profile.display_name}));}}));
      row.dataset.selected=String(snapshot.selectedProfileId===profile.profile_id);
      row.append(identity,facts,actions);list.append(row);
    }
    if(!snapshot.profiles.length){const empty=el("div","manager-empty");empty.append(icon("children"),el("strong","",tr("children.empty")),el("span","",tr("children.empty_help")));if(canManage)empty.append(button(tr("children.add"),{iconName:"plus",onClick:()=>this._openChildEditor(snapshot,null)}));list.append(empty);}
    root.append(list);return root;
  };

  proto._openUsageLimitEditor=async function(snapshot,profile){
    const profileMode=Boolean(profile),title=profileMode?tr("children.time.profile_title",{name:profile.display_name}):tr("children.time.shared_title"),subtitle=profileMode?tr("children.time.profile_help"):tr("children.time.shared_help"),d=this._openDialog({title,subtitle,iconName:"activity"}),body=d.querySelector(".dialog-content"),form=el("form","form-grid");
    let status=null;
    try{status=profileMode?await this.api.profileUsageLimit(profile.profile_id):await this.api.usageLimits();}catch(error){d.close();this.showFlash(error?.message||tr("children.time.load_failed"),"error");return;}
    const current=profileMode?status.profile_daily_minutes:status.daily_minutes,limitField=this._textField(tr("children.time.minutes"),"daily_minutes",current==null?"60":String(current)),limitInput=limitField.querySelector("input"),unlimited=this._checkField(tr("children.time.no_limit"),"unlimited",current==null),unlimitedInput=unlimited.querySelector("input");
    limitInput.type="number";limitInput.min="1";limitInput.max="1440";limitInput.step="1";limitInput.inputMode="numeric";
    const sync=()=>{limitInput.disabled=unlimitedInput.checked;};unlimitedInput.addEventListener("change",sync);sync();
    form.append(limitField,unlimited,el("p","help full field",tr("children.time.accounting")));
    const remaining=profileMode?status.effective_remaining_seconds:status.remaining_seconds,used=profileMode?status.profile_used_seconds:status.used_seconds,summary=el("div","field full");summary.append(el("strong","",remainingActivitySummary(remaining)),el("span","help",`${usedActivitySummary(used)}.`));form.append(summary);
    const actions=el("div","form-actions"),save=button(tr("children.time.save"),{iconName:"check",type:"submit"});actions.append(save);form.append(actions);
    form.addEventListener("submit",async event=>{event.preventDefault();const dailyMinutes=unlimitedInput.checked?null:Number(limitInput.value);if(dailyMinutes!==null&&(!Number.isInteger(dailyMinutes)||dailyMinutes<1||dailyMinutes>1440)){this.showFlash(tr("children.time.invalid"),"error");return;}save.disabled=true;try{if(profileMode)await this.api.updateProfileUsageLimit(profile.profile_id,dailyMinutes);else await this.api.updateUsageLimits(dailyMinutes);if(!profileMode||snapshot.selectedProfileId===profile?.profile_id)await this.state.refreshUsageLimits();d.close();this.showFlash(profileMode?tr("children.time.profile_updated",{name:profile.display_name}):tr("children.time.shared_updated"));}catch(error){this.showFlash(error?.message||tr("children.time.update_failed"),"error");}finally{save.disabled=false;}});
    body.append(form);
  };

  proto._openChildEditor=function(snapshot,profile){
    const isNew=!profile,supportsPresentation=Boolean(snapshot.index?.capabilities?.["profiles.presentation"]),d=this._openDialog({title:isNew?tr("children.add"):tr("children.editor.title",{name:profile.display_name}),subtitle:isNew?tr("children.editor.create_help"):tr("children.editor.edit_help"),iconName:"children"}),body=d.querySelector(".dialog-content"),form=el("form","form-grid");
    const name=this._textField(tr("children.editor.name"),"display_name",profile?.display_name||""),avatar=this._selectField(tr("children.editor.avatar"),"avatar_id",(snapshot.system?.profile_policy?.avatars||["unicorn","owl","robot","rabbit","star"]).map(v=>[v,String(v).replaceAll("_"," ")]),profile?.avatar_id||"unicorn"),ages=[["",tr("children.editor.not_specified")],...Array.from({length:18},(_,i)=>[String(i+1),tr("common.about_age",{age:i+1})])],age=this._selectField(tr("children.editor.age"),"approximate_age",ages,profile?.approximate_age==null?"":String(profile.approximate_age)),challenge=this._selectField(tr("children.editor.challenge"),"challenge_preference",[["automatic",tr("common.challenge.automatic")],["easier",tr("common.challenge.easier")],["standard",tr("common.challenge.standard")],["harder",tr("common.challenge.harder")]],profile?.challenge_preference||"automatic");
    form.append(name,avatar,age,challenge);
    if(supportsPresentation){const presentation=this._selectField(tr("children.editor.style"),"presentation",[["neutral",tr("children.editor.neutral")],["boy",tr("children.editor.boy")],["girl",tr("children.editor.girl")]],profile?.presentation||"neutral");form.append(presentation,el("p","help full field",tr("children.editor.style_help")));}
    const pass=this._selectField(tr("children.editor.password"),"secret_action",isNew?[["keep",tr("children.password_none")],["set",tr("children.editor.set_password")]]:[["keep",tr("children.editor.keep_current")],["set",tr("children.editor.set_replace")],["clear",tr("children.editor.remove_password")]],"keep"),secret=this._textField(tr("children.editor.new_password"),"secret","","password"),mask=this._checkField(tr("children.editor.mask_password"),"mask_secret",Boolean(profile?.mask_secret));form.append(pass,secret,mask,el("p","help full field",tr("children.editor.age_help")));
    const actions=el("div","form-actions");
    if(!isNew)actions.append(button(tr("children.editor.delete"),{iconName:"trash",className:"button danger",onClick:async()=>{if(!await this.confirm(tr("children.editor.delete_title",{name:profile.display_name}),tr("children.editor.delete_warn")))return;try{await this.api.deleteProfile(profile.profile_id);d.close();await this.state.refresh();this.showFlash(tr("children.editor.deleted",{name:profile.display_name}));}catch(error){this.showFlash(error?.message||tr("children.editor.delete_failed"),"error");}}}));
    const save=button(isNew?tr("children.add"):tr("children.editor.save"),{iconName:"check",type:"submit"});actions.append(save);form.append(actions);
    form.addEventListener("submit",async event=>{event.preventDefault();save.disabled=true;const data=new FormData(form),rawAge=String(data.get("approximate_age")||""),secretAction=String(data.get("secret_action")||"keep"),presentation=String(data.get("presentation")||profile?.presentation||"neutral"),payload={display_name:String(data.get("display_name")||"").trim(),avatar_id:String(data.get("avatar_id")||"unicorn"),approximate_age:rawAge?Number(rawAge):null,challenge_preference:String(data.get("challenge_preference")||"automatic"),secret_action:secretAction,secret:secretAction==="set"?String(data.get("secret")||""):"",mask_secret:data.get("mask_secret")==="on"};try{let saved;if(isNew){const {secret_action: _ignored, ...createPayload}=payload;saved=await this.api.createProfile(createPayload);}else saved=await this.api.updateProfile(profile.profile_id,payload);const profileId=saved?.profile_id||profile?.profile_id;if(supportsPresentation&&profileId)await this.api.updateProfilePresentation(profileId,{presentation,seedThemeIfUnset:true});d.close();await this.state.refresh();this.showFlash(isNew?tr("children.editor.added",{name:payload.display_name}):tr("children.editor.updated",{name:payload.display_name}));}catch(error){this.showFlash(error?.message||tr("children.editor.save_failed"),"error");}finally{save.disabled=false;}});
    body.append(form);
  };
}
