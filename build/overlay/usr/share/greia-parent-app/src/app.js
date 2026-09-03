import { ParentApiClient, ParentApiError } from "./api.js";
import { BrowserCredentialStore } from "./credential_store.js";
import { ParentAppState } from "./state.js";
import { NAV_ITEMS, el, icon, button, currentRoute } from "./ui.js";
import { installHomeChildrenViews } from "./views_home_children.js";
import { installActivityViews } from "./views_activities.js";
import { installDeviceViews } from "./views_device.js";
import { installDeviceManagementLayout } from "./views_device_layout.js";
import { installSystemControlViews } from "./views_system_controls.js";
import { installAppHelpers } from "./views_helpers.js";

class GreiaParentApp {
  constructor(api){
    this.api=api;this.state=new ParentAppState(api);this.route=currentRoute();this.view=document.getElementById("view");this.flash=document.getElementById("flash");this.connectionLabel=document.getElementById("connection-label");this.connectionDot=document.getElementById("connection-dot");this.confirmDialog=document.getElementById("confirm-dialog");this.confirmResolver=null;this.flashTimer=null;
    this._buildNavigation();this._bindShell();this.state.subscribe(snapshot=>this.render(snapshot));
  }
  async start(){try{await this.state.initialize();}catch(error){if(!error?.pairingRequired)this.showFlash(error?.message||"Could not load Greia Parents.","error");}}
  _buildNavigation(){for(const id of["desktop-nav","mobile-nav"]){const host=document.getElementById(id);host.replaceChildren();for(const item of NAV_ITEMS){const n=button(item.label,{iconName:item.icon,className:"nav-button"});n.dataset.route=item.id;n.addEventListener("click",()=>this.navigate(item.id));host.append(n);}}const refresh=document.getElementById("refresh-button");refresh.replaceChildren(icon("refresh"),el("span","","Refresh"));}
  _bindShell(){window.addEventListener("hashchange",()=>{this.route=currentRoute();this.render(this.state.snapshot);});document.getElementById("refresh-button").addEventListener("click",async()=>{try{await this.state.refresh();this.showFlash("Greia refreshed.");}catch(error){if(!error?.pairingRequired)this.showFlash(error?.message||"Refresh failed.","error");}});this.confirmDialog.addEventListener("close",()=>{if(!this.confirmResolver)return;const r=this.confirmResolver;this.confirmResolver=null;r(this.confirmDialog.returnValue==="confirm");});}
  navigate(route){location.hash=route;}
  render(snapshot){this._renderConnection(snapshot);for(const n of document.querySelectorAll(".nav-button"))n.setAttribute("aria-current",n.dataset.route===this.route?"page":"false");const info=NAV_ITEMS.find(i=>i.id===this.route)||NAV_ITEMS[0];document.getElementById("page-title").textContent=info.label;document.getElementById("page-subtitle").textContent=info.subtitle;document.getElementById("page-eyebrow").textContent=snapshot.meta?.device_name||"Greia Parents";document.getElementById("page-actions").replaceChildren();if(["booting","loading"].includes(snapshot.phase)){this.view.replaceChildren(this._loadingView());return;}if(snapshot.phase==="pairing"){this.view.replaceChildren(this._pairingView(snapshot));return;}if(snapshot.phase==="error"){this.view.replaceChildren(this._errorView(snapshot.error));return;}const render={home:()=>this._home(snapshot),children:()=>this._children(snapshot),activities:()=>this._activities(snapshot),device:()=>this._device(snapshot)}[this.route]||(()=>this._home(snapshot));this.view.replaceChildren(render());}
  _renderConnection(snapshot){this.connectionDot.className="connection-dot";if(snapshot.phase==="ready"){this.connectionDot.classList.add("online");this.connectionLabel.textContent=snapshot.meta?.device_name||"Connected";}else if(snapshot.phase==="pairing"){this.connectionDot.classList.add("warning");this.connectionLabel.textContent="Pair this browser";}else if(snapshot.phase==="error"){this.connectionDot.classList.add("offline");this.connectionLabel.textContent="Connection problem";}else this.connectionLabel.textContent="Connecting…";}
  _loadingView(){const shell=el("div","pair-screen"),card=el("section","pair-card"),em=el("div","pair-emblem");em.append(icon("refresh"));card.append(em,el("h2","","Opening your Greia"),el("p","","Loading children, Activities and device settings."));shell.append(card);return shell;}
  _errorView(error){const shell=el("div","pair-screen"),card=el("section","pair-card"),em=el("div","pair-emblem");em.append(icon("device"));card.append(em,el("h2","","This Greia isn't reachable right now"),el("p","",error?.message||"The Parent API did not respond."));const actions=el("div","button-row");actions.append(button("Try again",{iconName:"refresh",onClick:()=>this.start()}),button("Forget pairing",{className:"button secondary",onClick:()=>{this.api.forgetCredential?.();this.start();}}));card.append(actions);shell.append(card);return shell;}
  _pairingView(snapshot){const shell=el("div","pair-screen"),card=el("section","pair-card"),em=el("div","pair-emblem");em.append(icon("shield"));card.append(em,el("h2","","Pair this browser"),el("p","",`Connect to ${snapshot.meta?.device_name||"this Greia"} so you can manage it here.`));if(snapshot.meta?.transport_security==="provisional-http")card.append(el("div","security-note","Development pairing is active. Use the pairing token shown by Greia."));const form=el("form","form-grid"),name=this._textField("This device","device_name",navigator.platform?`${navigator.platform} browser`:"Parent browser"),token=this._textField("Pairing token","pairing_token","","password");name.classList.add("full");token.classList.add("full");const actions=el("div","form-actions"),submit=button("Pair browser",{iconName:"key",type:"submit"});actions.append(submit);form.append(name,token,actions);form.addEventListener("submit",async event=>{event.preventDefault();submit.disabled=true;const data=new FormData(form);try{await this.api.pairBootstrap({pairingToken:String(data.get("pairing_token")||""),deviceName:String(data.get("device_name")||"Parent browser")});await this.state.refresh();this.showFlash("This browser is paired with Greia.");}catch(error){this.showFlash(error?.message||"Pairing failed.","error");}finally{submit.disabled=false;}});card.append(form);shell.append(card);return shell;}
  showFlash(message,kind="ok"){this.flash.hidden=false;this.flash.className=`flash ${kind==="ok"?"":kind}`.trim();this.flash.textContent=message;clearTimeout(this.flashTimer);this.flashTimer=setTimeout(()=>{this.flash.hidden=true;},4200);}
  confirm(title,message){document.getElementById("confirm-title").textContent=title;document.getElementById("confirm-message").textContent=message;document.getElementById("confirm-icon").replaceChildren(icon("trash"));this.confirmDialog.returnValue="cancel";this.confirmDialog.showModal();return new Promise(resolve=>{this.confirmResolver=resolve;});}
}
installHomeChildrenViews(GreiaParentApp.prototype);installActivityViews(GreiaParentApp.prototype);installDeviceViews(GreiaParentApp.prototype);installSystemControlViews(GreiaParentApp.prototype);installDeviceManagementLayout(GreiaParentApp.prototype);installAppHelpers(GreiaParentApp.prototype);

const params=new URLSearchParams(location.search);
const demoHost=["127.0.0.1","localhost","::1"].includes(location.hostname);

async function createApi(){
  if(params.get("demo")==="1"&&demoHost){
    const {DemoManagementApiClient}=await import("./demo_management_api.js");
    return new DemoManagementApiClient();
  }
  return new ParentApiClient({credentialStore:new BrowserCredentialStore()});
}

createApi().then(api=>{
  const app=new GreiaParentApp(api);
  return app.start();
}).catch(error=>{if(!(error instanceof ParentApiError)||!error.pairingRequired)console.error(error);});
