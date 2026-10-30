import { el, icon, button, activityName, audienceLabel, categoryLabel, categoryIcon, visibilityName, MAX_ACTIVITY_PACKAGE_BYTES } from "./ui.js";
import { tr } from "./localization.js";

const launcherCategories=(activity)=>Array.isArray(activity?.launcher_categories)?activity.launcher_categories:Array.isArray(activity?.presentation_categories)?activity.presentation_categories:[];
const primaryCategory=(activity)=>["create","play","learn","explore"].find(value=>launcherCategories(activity).includes(value))||launcherCategories(activity)[0]||"activity";
const isParentInstalled=(activity)=>activity?.removable===true||activity?.package_trust==="parent_trusted_unsigned";
const difficultyLabel=(activity)=>{const fixed=Number(activity?.difficulty??1);if(activity?.adaptive_difficulty){const low=Number(activity?.difficulty_min??fixed),high=Number(activity?.difficulty_max??fixed);return low===high?tr("activities.difficulty.single",{level:low}):tr("activities.difficulty.adaptive",{low,high});}return tr("activities.difficulty.single",{level:fixed});};
const difficultyOptions=()=>[["",tr("activities.any")],...Array.from({length:10},(_,index)=>[String(index+1),String(index+1)])];
const canonicalPolicyMode=(mode)=>mode==="hide_too_simple"?"age_and_easier":mode||"show_all";
const ageModeOptions=(profile)=>{const age=profile?.approximate_age;return[["show_all",tr("activities.age_all")],["recommended_only",age==null?tr("activities.age_first"):tr("common.age_only",{age})],["age_and_easier",age==null?tr("activities.age_easier_first"):tr("common.age_younger",{age})],["custom",tr("activities.custom_choices")]];};
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
      actionHost.append(button(tr("activities.install"),{iconName:"plus",onClick:()=>this._openActivityInstall(snapshot)}));
    }else{
      const unavailable=button(tr("activities.install_unavailable"),{iconName:"upload",className:"button secondary"});
      unavailable.disabled=true;
      unavailable.title=tr("activities.install_unavailable_title");
      actionHost.append(unavailable);
    }

    const summary=el("section","manager-summary");
    const summaryCopy=el("div","manager-summary-copy");
    summaryCopy.append(el("strong","",tr("activities.count",{count:snapshot.activities.length})),el("span","",selected?tr("activities.managing_child",{name:selected.display_name}):tr("activities.installed_here")));
    const counts=el("div","summary-counts");
    counts.append(this._pill(tr("activities.added_count",{count:snapshot.activities.filter(isParentInstalled).length}),"upload","info"),this._pill(tr("activities.builtin_count",{count:snapshot.activities.length-snapshot.activities.filter(isParentInstalled).length}),"shield",""));
    summary.append(summaryCopy,counts);
    root.append(summary);

    const controls=el("section","manager-controls");
    if(snapshot.profiles.length){
      const selector=this._selectField(tr("activities.child"),"activity_profile",snapshot.profiles.map(p=>[p.profile_id,p.display_name]),selected?.profile_id||"");
      selector.classList.add("compact-field");
      selector.querySelector("select").addEventListener("change",async event=>{await this.state.selectProfile(event.target.value);});
      controls.append(selector);
    }
    if(selected&&capabilities["activities.policy"]){
      const mode=this._selectField(tr("activities.age_guidance"),"visibility_mode",ageModeOptions(selected),policyMode);
      mode.classList.add("compact-field","policy-mode");
      disableUnavailableAgeModes(mode,selected);
      const minimum=this._selectField(tr("activities.minimum_difficulty"),"difficulty_min",difficultyOptions(),policy.difficulty_min==null?"":String(policy.difficulty_min));minimum.classList.add("compact-field","policy-difficulty-min");
      const maximum=this._selectField(tr("activities.maximum_difficulty"),"difficulty_max",difficultyOptions(),policy.difficulty_max==null?"":String(policy.difficulty_max));maximum.classList.add("compact-field","policy-difficulty-max");
      controls.append(mode,minimum,maximum);
    }
    const searchWrap=el("label","manager-search");
    searchWrap.append(icon("search"));
    const search=document.createElement("input");search.type="search";search.placeholder=tr("activities.search");search.setAttribute("aria-label",tr("activities.search"));searchWrap.append(search);controls.append(searchWrap);
    root.append(controls);
    if(selected&&capabilities["activities.policy"]){
      const age=selected.approximate_age;
      const guidance=age==null
        ?tr("activities.guidance.no_age")
        :tr("activities.guidance.age",{age});
      root.append(el("p","help",guidance));
    }

    const filters=el("div","filter-tabs");
    let activeCategory="all";
    for(const category of["all","create","play","learn","explore"]){
      const tab=el("button","filter-tab",category==="all"?tr("activities.filter.all"):categoryLabel(category));tab.type="button";
      tab.dataset.category=category;tab.setAttribute("aria-pressed",String(category==="all"));
      tab.prepend(icon(category==="all"?"activity":categoryIcon(category)));
      if(category==="all")tab.classList.add("active");
      tab.addEventListener("click",()=>{activeCategory=category;for(const item of filters.children){item.classList.toggle("active",item===tab);item.setAttribute("aria-pressed",String(item===tab));}applyFilter();});
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
      titleLine.append(this._pill(isParentInstalled(activity)?tr("activities.installed_parent"):tr("activities.installed_builtin"),isParentInstalled(activity)?"upload":"shield",isParentInstalled(activity)?"info":""));
      identity.append(titleLine,el("p","",`${categoryLabel(category)} · ${audienceLabel(activity)} · ${difficultyLabel(activity)} · v${activity.version||"—"}`));

      const state=el("div","activity-row-state");
      state.append(this._pill(effective.has(activity.activity_id)?tr("activities.visible"):tr("activities.hidden"),"eye",effective.has(activity.activity_id)?"ok":"warn"));
      if(selected&&capabilities["activities.policy"]){
        const select=document.createElement("select");select.className="visibility-select";select.dataset.activityId=activity.activity_id;select.setAttribute("aria-label",tr("activities.visibility_for",{name:activityName(activity)}));
        for(const [value,text] of [["default",tr("common.challenge.automatic")],["always_show",tr("activities.always_show")],["always_hide",tr("activities.hide_child")]]){const option=document.createElement("option");option.value=value;option.textContent=text;option.selected=(overrides[activity.activity_id]||"default")===value;select.append(option);}state.append(select);
      }

      const actions=el("div","activity-row-actions");
      if(isParentInstalled(activity)){
        if(capabilities["activities.remove"]){
          const remove=button(tr("activities.remove"),{iconName:"trash",className:"button small danger-quiet"});
          remove.addEventListener("click",async()=>{
            if(!await this.confirm(tr("activities.remove_title",{name:activityName(activity)}),tr("activities.remove_warning",{child:selected?.display_name||tr("activities.children_generic")})))return;
            remove.disabled=true;
            try{await this.api.removeActivity(activity.activity_id);await this.state.refresh();this.showFlash(tr("activities.removed",{name:activityName(activity)}));}catch(error){this.showFlash(error?.code==="profile_session_active"?tr("activities.profile_picker_required"):error?.message||tr("activities.remove_failed"),"error");}finally{remove.disabled=false;}
          });
          actions.append(remove);
        }else{
          const locked=button(tr("activities.remove_unavailable"),{iconName:"lock",className:"button small ghost"});locked.disabled=true;actions.append(locked);
        }
      }

      row.append(symbol,identity,state,actions);list.append(row);
    }
    root.append(list);

    const empty=el("div","manager-empty");empty.hidden=true;empty.append(icon("search"),el("strong","",tr("activities.empty")),el("span","",tr("activities.empty_help")));root.append(empty);
    const applyFilter=()=>{const term=search.value.trim().toLowerCase();let shown=0;for(const row of list.children){const nameHit=!term||row.dataset.name.includes(term),categoryHit=activeCategory==="all"||row.dataset.categories.split(" ").includes(activeCategory),show=nameHit&&categoryHit;row.hidden=!show;if(show)shown+=1;}empty.hidden=shown!==0;};
    search.addEventListener("input",applyFilter);

    if(selected&&capabilities["activities.policy"]){
      const saveBar=el("div","manager-savebar"),copy=el("div");copy.append(el("strong","",tr("activities.policy_title",{name:selected.display_name})),el("span","",tr("activities.policy_summary",{mode:visibilityName(policyMode,selected.approximate_age),min:policy.difficulty_min??tr("activities.any"),max:policy.difficulty_max??tr("activities.any")})));
      const save=button(tr("activities.policy_save"),{iconName:"check"});
      save.addEventListener("click",async()=>{save.disabled=true;const mode=root.querySelector('.policy-mode select')?.value||policyMode,minRaw=root.querySelector('.policy-difficulty-min select')?.value??"",maxRaw=root.querySelector('.policy-difficulty-max select')?.value??"",difficultyMin=minRaw===""?null:Number(minRaw),difficultyMax=maxRaw===""?null:Number(maxRaw),overridesPayload={};if(difficultyMin!==null&&difficultyMax!==null&&difficultyMin>difficultyMax){this.showFlash(tr("activities.policy_invalid"),"error");save.disabled=false;return;}for(const select of list.querySelectorAll("select[data-activity-id]"))overridesPayload[select.dataset.activityId]=select.value==="default"?null:select.value;try{await this.api.updateActivityPolicy(selected.profile_id,{visibility_mode:mode,difficulty_min:difficultyMin,difficulty_max:difficultyMax,overrides:overridesPayload});await this.state.selectProfile(selected.profile_id);this.showFlash(tr("activities.policy_updated",{name:selected.display_name}));}catch(error){this.showFlash(error?.message||tr("activities.policy_failed"),"error");}finally{save.disabled=false;}});
      saveBar.append(copy,save);root.append(saveBar);
    }
    return root;
  };

  proto._openActivityInstall=function(){
    const dialog=this._openDialog({title:tr("activities.install_title"),subtitle:tr("activities.install_help"),iconName:"upload"});
    const body=dialog.querySelector(".dialog-content"),panel=el("div","install-panel"),drop=el("label","file-picker");
    drop.append(icon("upload"),el("strong","",tr("activities.install_choose")),el("span","",tr("activities.install_max")));
    const input=document.createElement("input");input.type="file";input.accept=".greiaactivity,application/vnd.greia.activity+zip";drop.append(input);panel.append(drop);
    const chosen=el("p","file-name",tr("activities.no_file"));panel.append(chosen);input.addEventListener("change",()=>{chosen.textContent=input.files?.[0]?.name||tr("activities.no_file");});
    const actions=el("div","form-actions"),submit=button(tr("activities.install"),{iconName:"upload"});actions.append(submit);panel.append(actions);
    submit.addEventListener("click",async()=>{const file=input.files?.[0];if(!file)return this.showFlash(tr("activities.choose_first"),"error");if(!file.name.toLowerCase().endsWith(".greiaactivity"))return this.showFlash(tr("activities.bad_extension"),"error");if(file.size<=0||file.size>MAX_ACTIVITY_PACKAGE_BYTES)return this.showFlash(tr("activities.too_large"),"error");submit.disabled=true;try{const result=await this.api.installActivity(file);dialog.close();await this.state.refresh();this.showFlash(tr("activities.installed",{name:result?.installed?.activity_id||tr("category.unknown")}));}catch(error){this.showFlash(error?.code==="profile_session_active"?tr("activities.profile_picker_required"):error?.message||tr("activities.install_failed"),"error");}finally{submit.disabled=false;}});
    body.append(panel);
  };
}
