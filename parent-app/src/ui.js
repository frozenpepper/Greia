import { tr } from "./localization.js";
import { MAX_SOFTWARE_UPDATE_BYTES } from "./api.js";
export { MAX_SOFTWARE_UPDATE_BYTES };
export const NAV_ITEMS = [
  { id: "home", labelKey: "nav.home", icon: "home", subtitleKey: "nav.home.subtitle" },
  { id: "children", labelKey: "nav.children", icon: "children", subtitleKey: "nav.children.subtitle" },
  { id: "activities", labelKey: "nav.activities", icon: "sparkles", subtitleKey: "nav.activities.subtitle" },
  { id: "device", labelKey: "nav.device", icon: "device", subtitleKey: "nav.device.subtitle" },
];
export const ROUTE_ALIASES = { overview: "home", settings: "device", devices: "device" };
export const MAX_ACTIVITY_PACKAGE_BYTES = 32 * 1024 * 1024;
export const MAX_UPDATE_BYTES = 2 * 1024 * 1024 * 1024;
const SVG_NS = "http://www.w3.org/2000/svg";
const ICONS = {
  home:["M3.5 11 12 4l8.5 7","M5.5 10.5V20h13v-9.5","M9.5 20v-6h5v6"],
  children:["M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z","M2.8 20c.7-4.1 3-6.1 6.2-6.1s5.5 2 6.2 6.1","M16.2 4.3a3.2 3.2 0 0 1 0 6.2","M16.2 13.9c2.7.1 4.5 2.1 5 5.2"],
  sparkles:["m12 3 1.3 3.7L17 8l-3.7 1.3L12 13l-1.3-3.7L7 8l3.7-1.3L12 3Z","m5 14 .8 2.2L8 17l-2.2.8L5 20l-.8-2.2L2 17l2.2-.8L5 14Z"],
  device:["M5 3.5h14a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-9a2 2 0 0 1 2-2Z","M8 20.5h8","M12 16.5v4"],
  refresh:["M20 6v5h-5","M19 11a7 7 0 1 0 .2 5.8"], plus:["M12 5v14","M5 12h14"],
  edit:["M4 20h4l11-11-4-4L4 16v4Z","m13.8 6.2 4 4"], trash:["M4 7h16","M9 7V4h6v3","M7 7l1 13h8l1-13","M10 11v5","M14 11v5"],
  lock:["M6 10h12v10H6V10Z","M8.5 10V7.5a3.5 3.5 0 0 1 7 0V10"], shield:["M12 3 19 6v5c0 4.4-2.5 7.5-7 10-4.5-2.5-7-5.6-7-10V6l7-3Z","m9 12 2 2 4-5"],
  star:["m12 3 2.7 5.5 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.8 1-6.1-4.4-4.3 6.1-.9L12 3Z"],
  activity:["M7 4h10a3 3 0 0 1 3 3v10a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V7a3 3 0 0 1 3-3Z","M8 8h8","M8 12h5","M8 16h3"],
  palette:["M12 3a9 9 0 0 0 0 18h1.2a2.1 2.1 0 0 0 1.6-3.5 2.2 2.2 0 0 1 1.6-3.7H19a2 2 0 0 0 2-2A9 9 0 0 0 12 3Z"],
  book:["M4 5.5A2.5 2.5 0 0 1 6.5 3H12v17H6.5A2.5 2.5 0 0 0 4 22V5.5Z","M20 5.5A2.5 2.5 0 0 0 17.5 3H12v17h5.5A2.5 2.5 0 0 1 20 22V5.5Z"],
  compass:["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z","m15.7 8.3-2.1 5.3-5.3 2.1 2.1-5.3 5.3-2.1Z"],
  search:["M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14Z","m16 16 5 5"], eye:["M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z","M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"],
  wifi:["M3 9.5a14 14 0 0 1 18 0","M6.5 13a9 9 0 0 1 11 0","M10 16.5a4 4 0 0 1 4 0","M12 20h.01"],
  globe:["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z","M3.5 12h17","M12 3c2.2 2.5 3.3 5.5 3.3 9S14.2 18.5 12 21","M12 3c-2.2 2.5-3.3 5.5-3.3 9S9.8 18.5 12 21"],
  sliders:["M4 6h10","M18 6h2","M14 3v6","M4 12h3","M11 12h9","M7 9v6","M4 18h8","M16 18h4","M12 15v6"],
  key:["M14 7a5 5 0 1 0-4.5 7.2L12 17h3v3h3v-3h2v-3h-6.5A5 5 0 0 0 14 7Z"], terminal:["M4 5h16v14H4V5Z","m7 9 3 3-3 3","M12 15h5"],
  upload:["M12 16V4","m7 9 5-5 5 5","M5 20h14"], close:["M6 6l12 12","M18 6 6 18"], check:["m5 12 4 4L19 6"],
  settings:["M4 7h16","M7 12h10","M10 17h4","M8 5v4","M16 10v4","M12 15v4"],
};
export const el=(tag,className="",text=null)=>{const n=document.createElement(tag);if(className)n.className=className;if(text!==null)n.textContent=String(text);return n;};
export const icon=(name,label=null)=>{const svg=document.createElementNS(SVG_NS,"svg");svg.setAttribute("viewBox","0 0 24 24");svg.setAttribute("class","ui-icon");svg.setAttribute("fill","none");svg.setAttribute("stroke","currentColor");svg.setAttribute("stroke-width","1.8");svg.setAttribute("stroke-linecap","round");svg.setAttribute("stroke-linejoin","round");if(label){svg.setAttribute("role","img");svg.setAttribute("aria-label",label);}else svg.setAttribute("aria-hidden","true");for(const d of ICONS[name]||ICONS.activity){const p=document.createElementNS(SVG_NS,"path");p.setAttribute("d",d);svg.append(p);}return svg;};
export const button=(label,{iconName=null,className="button",type="button",onClick=null}={})=>{const n=el("button",className);n.type=type;if(iconName)n.append(icon(iconName));n.append(el("span","",label));if(onClick)n.addEventListener("click",onClick);return n;};
export const humanBytes=(v)=>{const n=Math.max(0,Number(v||0));return n>=1073741824?`${(n/1073741824).toFixed(1)} GB`:`${Math.round(n/1048576)} MB`;};
export const humanUptime=(s)=>{const t=Math.max(0,Number(s||0)),h=Math.floor(t/3600);return h>=24?`${Math.floor(h/24)}d ${h%24}h`:`${h}h ${Math.floor((t%3600)/60)}m`;};
export const humanActivityTime=(seconds,{unlimited=tr("common.unlimited"),zero=tr("common.finished_today")}={})=>{if(seconds===null||seconds===undefined)return unlimited;const total=Math.max(0,Math.floor(Number(seconds)||0));if(total===0)return zero;const minutes=Math.max(1,Math.floor(total/60)),hours=Math.floor(minutes/60),rest=minutes%60;if(hours&&rest)return`${hours} h ${rest} min`;if(hours)return`${hours} h`;return`${minutes} min`;};
export const dailyLimitLabel=(minutes)=>{if(minutes===null||minutes===undefined)return tr("common.unlimited");const value=Math.max(1,Math.floor(Number(minutes)||1));const time=value%60===0?`${value/60} h`:value>60?`${Math.floor(value/60)} h ${value%60} min`:`${value} min`;return tr("common.per_day",{time});};
export const percent=(a,b)=>Number(b)>0?Math.max(0,Math.min(100,Math.round((Number(a||0)/Number(b))*100))):0;
export const activityName=(a)=>{const c=a?.title_key;if(c&&!String(c).includes("."))return String(c);const t=String(a?.activity_id||tr("category.unknown")).split(".").pop();return t.replaceAll("-"," ").replace(/\b\w/g,x=>x.toUpperCase());};
export const challengeName=(v)=>tr(`common.challenge.${["automatic","easier","standard","harder"].includes(v)?v:"automatic"}`);
export const visibilityName=(v,age=null)=>{if(v==="recommended_only")return age==null?tr("common.age_fit"):tr("common.age_only",{age});if(v==="age_and_easier"||v==="hide_too_simple")return age==null?tr("common.age_easier"):tr("common.age_younger",{age});return tr(v==="custom"?"common.custom":"common.show_all");};
export const audienceLabel=(a)=>{const lo=a?.recommended_age_min,hi=a?.recommended_age_max;if(lo==null&&hi==null)return tr("common.age_unspecified");if(lo!=null&&hi==null)return tr("common.age_min",{age:lo});if(lo==null)return tr("common.up_to_age",{age:hi});return tr("common.age_range",{min:lo,max:hi});};
export const activityCategory=(a)=>{const c=Array.isArray(a?.launcher_categories)?a.launcher_categories:Array.isArray(a?.presentation_categories)?a.presentation_categories:[];return["create","play","learn","explore"].find(x=>c.includes(x))||c[0]||"activity";};
export const categoryLabel=(c)=>tr(`category.${["create","play","learn","explore","my_greia"].includes(c)?c:"unknown"}`);
export const categoryIcon=(c)=>({create:"palette",play:"sparkles",learn:"book",explore:"compass",my_greia:"settings"}[c]||"activity");
export const avatarTone=(id)=>({unicorn:"lilac",owl:"sun",robot:"sky",rabbit:"coral",star:"sun"}[id]||"forest");
export const avatarIcon=(id)=>({unicorn:"sparkles",owl:"book",robot:"settings",rabbit:"star",star:"star"}[id]||"children");
export const profileSubtitle=(p)=>[p.approximate_age==null?null:tr("common.about_age",{age:p.approximate_age}),challengeName(p.challenge_preference)].filter(Boolean).join(" · ");
export const currentRoute=()=>{const raw=location.hash.replace(/^#/,"")||"home";return ROUTE_ALIASES[raw]||(NAV_ITEMS.some(i=>i.id===raw)?raw:"home");};
