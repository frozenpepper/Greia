import { el, icon, button, activityName, audienceLabel, categoryLabel, categoryIcon, visibilityName, MAX_ACTIVITY_PACKAGE_BYTES } from "./ui.js";

const launcherCategories=(activity)=>Array.isArray(activity?.launcher_categories)?activity.launcher_categories:Array.isArray(activity?.presentation_categories)?activity.presentation_categories:[];
const primaryCategory=(activity)=>["create","play","learn","explore"].find(value=>launcherCategories(activity).includes(value))||launcherCategories(activity)[0]||"activity";
const isParentInstalled=(activity)=>activity?.removable===true||activity?.package_trust==="parent_trusted_unsigned";
const difficultyLabel=(activity)=>{const fixed=Number(activity?.difficulty??1);if(activity?.adaptive_difficulty){const low=Number(activity?.difficulty_min??fixed),high=Number(activity?.difficulty_max??fixed);return low===high?`Difficulty ${low}`:`Difficulty ${low}–${high} adaptive`;}return`Difficulty ${fixed}`;};
const difficultyOptions=()=>[["","Any"],...Array.from({length:10},(_,index)=>[String(index+1),String(index+1)])];
const canonicalPolicyMode=(mode)=>mode==="hide_too_simple"?"age_and_easier":mode||"show_all";
const ageModeOptions=(profile)=>{const age=profile?.approximate_age;return[["show_all","All age ranges"],["recommended_only",age==null?"Age fit — set age first":`Age ${age} only`],["age_and_easier",age==null?"Age + easier — set age first":`Age ${age} + easier`],["custom","Custom choices"]];};
const disableUnavailableAgeModes=(field,profile)=>{if(profile?.approximate_age!=null)return;const select=field.querySelector("select");for(const option of select?.options||[]){if(["recommended_only","age_and_easier"].includes(option.value))option.disabled=true;}};

export function installActivityViews(proto){
  proto._activities=function(snapshot){
    const selected=this._selectedProfile(snapshot);
    const capabilities=snapshot.index?.capabilities||{};
    const policy=snapshot.activityPolicy||{visibility_mode:"show_all",difficulty_min:null,difficulty_max:null,overrides:{},effective_activity_ids:snapshot.activities.map(a=>a.activity_id)};
    const policyMode=canonicalPolicyMode(policy.visibility_mode);
    const effective=new Set(policy.effective_activity_ids||[]);
    const overrides=policy.overrides||{};
    const root=el("div","activity-manager");

    const actionHost=document.getElementById("page-actions");
    if(capabilities["activities.install"]){
      actionHost.append(button("Install Activity",{iconName:"plus",onClick:()=>this._openActivityInstall(snapshot)}));
    }else{
      const unavailable=button("Install unavailable",{iconName:"upload",className:"button secondary"});
      unavailable.disabled=true;
      unavailable.title="Activity installation is not enabled by this Greia image.";
      actionHost.append(unavailable);
    }

    const summary=el("section","manager-summary");
    const summaryCopy=el("div","manager-summary-copy");
    summaryCopy.append(el("strong","",`${snapshot.activities.length} Activities installed`),el("span","",selected?`Managing what ${selected.display_name} can see.`:"Installed on this Greia."));
    const counts=el("div","summary-counts");
    counts.append(this._pill(`${snapshot.activities.filter(isParentInstalled).length} added`,"upload","info"),this._pill(`${snapshot.activities.length-snapshot.activities.filter(isParentInstalled).length} built in`,"shield",""));
    summary.append(summaryCopy,counts);
    root.append(summary);

    const controls=el("section","manager-controls");
    if(snapshot.profiles.length){
      const selector=this._selectField("Child","activity_profile",snapshot.profiles.map(p=>[p.profile_id,p.display_name]),selected?.profile_id||"");
      selector.classList.add("compact-field");
      selector.querySelector("select").addEventListener("change",async event=>{await this.state.selectProfile(event.target.value);});
      controls.append(selector);
    }
    if(selected&&capabilities["activities.policy"]){
      const mode=this._selectField("Age guidance","visibility_mode",ageModeOptions(selected),policyMode);
      mode.classList.add("compact-field","policy-mode");
      disableUnavailableAgeModes(mode,selected);
      const minimum=this._selectField("Minimum difficulty","difficulty_min",difficultyOptions(),policy.difficulty_min==null?"":String(policy.difficulty_min));minimum.classList.add("compact-field","policy-difficulty-min");
      const maximum=this._selectField("Maximum difficulty","difficulty_max",difficultyOptions(),policy.difficulty_max==null?"":String(policy.difficulty_max));maximum.classList.add("compact-field","policy-difficulty-max");
      controls.append(mode,minimum,maximum);
    }
    const searchWrap=el("label","manager-search");
    searchWrap.append(icon("search"));
    const search=document.createElement("input");search.type="search";search.placeholder="Search installed Activities";search.setAttribute("aria-label","Search installed Activities");searchWrap.append(search);controls.append(searchWrap);
    root.append(controls);
    if(selected&&capabilities["activities.policy"]){
      const age=selected.approximate_age;
      const guidance=age==null
        ?"Set an approximate age in Children to enable the age presets. Until then age guidance does not hide Activities; difficulty and individual choices still work."
        :`Age ${age} only shows Activities whose declared recommended range contains ${age}. Age ${age} + easier also includes Activities designed to start younger, but never Activities whose declared minimum age is above ${age}. Difficulty remains a separate inclusive 1–10 control.`;
      root.append(el("p","help",guidance));
    }

    const filters=el("div","filter-tabs");
    let activeCategory="all";
    for(const category of["all","create","play","learn","explore"]){
      const tab=el("button","filter-tab",category==="all"?"All":categoryLabel(category));tab.type="button";
      if(category==="all")tab.classList.add("active");
      tab.addEventListener("click",()=>{activeCategory=category;for(const item of filters.children)item.classList.toggle("active",item===tab);applyFilter();});
      filters.append(tab);
    }
    root.append(filters);

    const list=el("section","activity-list");
    for(const activity of snapshot.activities){
      const category=primaryCategory(activity),row=el("article","activity-row");
      row.dataset.name=activityName(activity).toLowerCase();
      row.dataset.categories=launcherCategories(activity).join(" ");

      const symbol=el("div","activity-row-icon");symbol.dataset.tone=category;symbol.append(icon(categoryIcon(category)));
      const identity=el("div","activity-row-identity");
      const titleLine=el("div","activity-title-line");titleLine.append(el("h3","",activityName(activity)));
      titleLine.append(this._pill(isParentInstalled(activity)?"Parent installed":"Built in",isParentInstalled(activity)?"upload":"shield",isParentInstalled(activity)?"info":""));
      identity.append(titleLine,el("p","",`${categoryLabel(category)} · ${audienceLabel(activity)} · ${difficultyLabel(activity)} · v${activity.version||"—"}`));

      const state=el("div","activity-row-state");
      state.append(this._pill(effective.has(activity.activity_id)?"Visible":"Hidden","eye",effective.has(activity.activity_id)?"ok":"warn"));
      if(selected&&capabilities["activities.policy"]){
        const select=document.createElement("select");select.className="visibility-select";select.dataset.activityId=activity.activity_id;select.setAttribute("aria-label",`Visibility for ${activityName(activity)}`);
        for(const [value,text] of [["default","Automatic"],["always_show","Always show"],["always_hide","Hide from child"]]){const option=document.createElement("option");option.value=value;option.textContent=text;option.selected=(overrides[activity.activity_id]||"default")===value;select.append(option);}state.append(select);
      }

      const actions=el("div","activity-row-actions");
      if(isParentInstalled(activity)){
        if(capabilities["activities.remove"]){
          const remove=button("Remove",{iconName:"trash",className:"button small danger-quiet"});
          remove.addEventListener("click",async()=>{
            if(!await this.confirm(`Remove ${activityName(activity)}?`,`The Activity will be removed from this Greia. ${selected?.display_name||"Children"}'s saved work and progress are kept.`))return;
            remove.disabled=true;
            try{await this.api.removeActivity(activity.activity_id);await this.state.refresh();this.showFlash(`${activityName(activity)} removed. Saved child data was kept.`);}catch(error){this.showFlash(error?.message||"Could not remove Activity.","error");}finally{remove.disabled=false;}
          });
          actions.append(remove);
        }else{
          const locked=button("Removal unavailable",{iconName:"lock",className:"button small ghost"});locked.disabled=true;actions.append(locked);
        }
      }

      row.append(symbol,identity,state,actions);list.append(row);
    }
    root.append(list);

    const empty=el("div","manager-empty");empty.hidden=true;empty.append(icon("search"),el("strong","","No matching Activities"),el("span","","Try a different search or category."));root.append(empty);
    const applyFilter=()=>{const term=search.value.trim().toLowerCase();let shown=0;for(const row of list.children){const nameHit=!term||row.dataset.name.includes(term),categoryHit=activeCategory==="all"||row.dataset.categories.split(" ").includes(activeCategory),show=nameHit&&categoryHit;row.hidden=!show;if(show)shown+=1;}empty.hidden=shown!==0;};
    search.addEventListener("input",applyFilter);

    if(selected&&capabilities["activities.policy"]){
      const saveBar=el("div","manager-savebar"),copy=el("div");copy.append(el("strong","",`Activity visibility for ${selected.display_name}`),el("span","",`${visibilityName(policyMode,selected.approximate_age)} · difficulty ${policy.difficulty_min??"any"} to ${policy.difficulty_max??"any"}`));
      const save=button("Save Activity choices",{iconName:"check"});
      save.addEventListener("click",async()=>{save.disabled=true;const mode=root.querySelector('.policy-mode select')?.value||policyMode,minRaw=root.querySelector('.policy-difficulty-min select')?.value??"",maxRaw=root.querySelector('.policy-difficulty-max select')?.value??"",difficultyMin=minRaw===""?null:Number(minRaw),difficultyMax=maxRaw===""?null:Number(maxRaw),overridesPayload={};if(difficultyMin!==null&&difficultyMax!==null&&difficultyMin>difficultyMax){this.showFlash("Minimum difficulty cannot be greater than maximum difficulty.","error");save.disabled=false;return;}for(const select of list.querySelectorAll("select[data-activity-id]"))overridesPayload[select.dataset.activityId]=select.value==="default"?null:select.value;try{await this.api.updateActivityPolicy(selected.profile_id,{visibility_mode:mode,difficulty_min:difficultyMin,difficulty_max:difficultyMax,overrides:overridesPayload});await this.state.selectProfile(selected.profile_id);this.showFlash(`${selected.display_name}'s Activity choices updated.`);}catch(error){this.showFlash(error?.message||"Could not update Activity choices.","error");}finally{save.disabled=false;}});
      saveBar.append(copy,save);root.append(saveBar);
    }
    return root;
  };

  proto._openActivityInstall=function(){
    const dialog=this._openDialog({title:"Install an Activity",subtitle:"Add a Greia Activity package from this device.",iconName:"upload"});
    const body=dialog.querySelector(".dialog-content"),panel=el("div","install-panel"),drop=el("label","file-picker");
    drop.append(icon("upload"),el("strong","","Choose a .greiaactivity file"),el("span","","Maximum package size: 32 MB. Greia validates the package before it becomes available."));
    const input=document.createElement("input");input.type="file";input.accept=".greiaactivity,application/vnd.greia.activity+zip";drop.append(input);panel.append(drop);
    const chosen=el("p","file-name","No file chosen");panel.append(chosen);input.addEventListener("change",()=>{chosen.textContent=input.files?.[0]?.name||"No file chosen";});
    const actions=el("div","form-actions"),submit=button("Install Activity",{iconName:"upload"});actions.append(submit);panel.append(actions);
    submit.addEventListener("click",async()=>{const file=input.files?.[0];if(!file)return this.showFlash("Choose a .greiaactivity file first.","error");if(!file.name.toLowerCase().endsWith(".greiaactivity"))return this.showFlash("Choose a .greiaactivity package, not a generic ZIP file.","error");if(file.size<=0||file.size>MAX_ACTIVITY_PACKAGE_BYTES)return this.showFlash("The Activity package must be smaller than 32 MB.","error");submit.disabled=true;try{const result=await this.api.installActivity(file);dialog.close();await this.state.refresh();this.showFlash(`${result?.installed?.activity_id||"Activity"} installed.`);}catch(error){this.showFlash(error?.message||"Activity installation failed.","error");}finally{submit.disabled=false;}});
    body.append(panel);
  };
}
