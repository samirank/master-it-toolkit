/* Installation is explicit and available only through the local launcher. */
(() => {
 'use strict';
 const el=(tag,text)=>{const node=document.createElement(tag);if(text)node.textContent=text;return node;};
 const link=(title,url)=>{const a=el('a',title);a.href=url;a.target='_blank';a.rel='noopener noreferrer';return a;};
 document.addEventListener('click',async event=>{
  const trigger=event.target.closest('[data-install]');if(!trigger)return;
  const tool=window.TOOLKIT_DATA.find(t=>t.id===trigger.dataset.install);if(!tool)return;
  const dialog=el('dialog');dialog.className='download-dialog install-dialog';dialog.setAttribute('aria-label','Install '+tool.name);
  const close=el('button','Close');close.className='dialog-close';close.onclick=()=>dialog.close();dialog.append(close,el('h2','Install '+tool.name+' on this PC'));
  document.body.append(dialog);dialog.addEventListener('close',()=>dialog.remove());dialog.showModal();
  dialog.append(el('p','Review the installer and publisher before making changes. Portable tools can run from the SSD without installation.'));
  const guide=el('section');guide.className='install-guidance';guide.append(el('h3','Manage installations and removal'));
  guide.append(el('p','Prefer BCUninstaller: free and open source, with batch removal support. Use a paid option only for a required feature: Revo Uninstaller Pro can trace installations; BCUninstaller does not provide that same tracing workflow. Neither is a prerequisite.'));
  const managerActions=el('div');managerActions.className='actions';
  for(const [id,name] of [['bcu','BCUninstaller (free / open source)'],['revo','Revo Pro (optional paid tracing)']]){
   if(tool.id===id)continue;
   const button=el('button','Get '+name);button.dataset.download=id;button.onclick=()=>dialog.close();managerActions.append(button);
  }
  guide.append(managerActions,link('Revo Pro: official installation tracing instructions','https://www.revouninstaller.com/online-manual/uninstaller/'));
  guide.append(el('p','To use Revo tracing, select “Install with Revo Uninstaller Pro” from the installer’s Windows context menu, or use Revo’s Install Program command. That is a separate workflow; the toolkit’s button below does not claim to create a Revo trace. Create a recovery checkpoint before using that workflow.'));
  dialog.append(guide);
  dialog.append(el('p','Toolkit tracked install: verify the EXE/MSI and review its publisher → record installed programs → create and verify a new Windows restore point → run the visible installer → record the result and program list. If the checkpoint or signature check fails, installation stops. A restore point is not a full disk backup and cannot guarantee reversal of every change.'));
  const status=el('p','Reviewing local installer files…');status.setAttribute('role','status');status.className='is-loading';dialog.append(status);
  if(!window.TOOLKIT_LAUNCHER){status.className='';status.textContent='Open the local launcher on the target computer to review installers. The hosted demo cannot install software.';dialog.append(link('Official setup documentation',tool.documentation||tool.officialWebsite));return;}
  const api=path=>new URL('api/'+path,location.href);
  const send=async body=>{const response=await fetch(api('action'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...body,confirmed:true})});const data=await response.json();if(!response.ok)throw Error(data.error);window.dispatchEvent(new CustomEvent('toolkit-activity',{detail:{busy:true,message:data.message}}));return data;};
  const choices=el('div');choices.className='download-options';dialog.append(choices);
  const records=el('section');dialog.append(records);
  let running=false,polling=false;
  function history(items){
   records.replaceChildren(el('h3','Installation history on this computer'));
   if(!items.length)records.append(el('p','No toolkit installation records for this application yet.'));
   for(const item of items){
    const details=el('details');details.append(el('summary',(item.started||'')+' · '+item.status),el('p',item.message),el('code',item.package));
    if(item.restorePoint)details.append(el('p','Restore point '+item.restorePoint.sequence+': '+item.restorePoint.description));
    const key=p=>[p.PSChildName,p.DisplayName,p.DisplayVersion].join('|');const previous=new Set((item.before||[]).map(key));
    const changed=(item.after||[]).filter(p=>!previous.has(key(p)));
    details.append(el('p','New or changed program entries: '+(changed.map(p=>p.DisplayName+' '+(p.DisplayVersion||'')).join(', ')||'None recorded. Verify the installer result manually.')));
    details.append(el('p','To undo: use the application’s uninstaller or Windows installed programs first. For wider recovery, open System Restore and review the recorded checkpoint. A system restore can affect other programs installed later.'));
    records.append(details);
   }
  }
  async function load(){
   const response=await fetch(api('install-options?tool='+encodeURIComponent(tool.id)));const info=await response.json();if(!response.ok)throw Error(info.error);
   if(!dialog.isConnected)return;
   status.className='';status.textContent=info.reason||'Target computer: '+info.host+'. Choose an installer below. Unsigned files require explicit official-source confirmation. Windows will request administrator permission; review its publisher and installer prompts.';
   dialog.querySelectorAll('[data-recovery]').forEach(button=>button.disabled=info.windows===false);
   if(info.installedOnHost)status.textContent='Already detected on '+info.host+': '+info.hostMatches.map(p=>p.name+' '+p.version).join(', ')+'. Use installed programs to manage it; continue only for an intentional repair, upgrade or reinstall.';
   history(info.history);choices.replaceChildren();
   for(const file of info.files){
    const row=el('div');row.className='download-option';const description=el('div');
    description.append(el('strong',file.name),el('p',file.signature?.publisher||'Publisher unavailable'),el('code',file.path),el('small','SHA256: '+(file.sha256||'Unavailable')));
    const button=el('button',info.installedOnHost?'Create checkpoint & reinstall':'Create checkpoint & install');button.disabled=!!info.reason||file.signature?.status!=='Valid';
    description.append(el('small','Signature: '+(file.signature?.status||'Unavailable')));
    let unsignedApproval=null;
    if(!info.reason&&file.signature?.status==='NotSigned'){
     const label=el('label');unsignedApproval=el('input');unsignedApproval.type='checkbox';
     label.append(unsignedApproval,document.createTextNode(' I verified this unsigned file came from the official publisher. I accept that its publisher cannot be authenticated.'));
     description.append(label);unsignedApproval.onchange=()=>button.disabled=!unsignedApproval.checked;
    }
    button.onclick=async()=>{
     if(!confirm((info.installedOnHost?'Repair, upgrade or reinstall ':'Install ')+file.name+' on '+info.host+'?\nPublisher: '+(file.signature.publisher||'Unsigned — source confirmation required')+'\nA verified new restore point is required. The interactive installer may request a restart. Save your work first.'))return;
     button.disabled=true;status.classList.add('is-loading');status.textContent='Preparing recovery checkpoint. Check Windows UAC and installer prompts…';
     try{await send({action:'install',tool:tool.id,package:file.path,sha256:file.sha256,acceptUnsigned:unsignedApproval?.checked===true});running=true;}catch(error){status.className='';status.textContent=error.message;button.disabled=false;}
    };
    row.append(description,button);choices.append(row);
   }
  }
  const recovery=el('div');recovery.className='actions';
  for(const [action,label] of [['installed-apps','Open installed programs'],['system-restore','Open System Restore wizard']]){
   const button=el('button',label);button.dataset.recovery=action;button.onclick=async()=>{try{await send({action});}catch(error){status.textContent=error.message;}};recovery.append(button);
  }
  const refresh=el('button','Refresh install history');refresh.onclick=()=>load().catch(error=>status.textContent=error.message);recovery.append(refresh);dialog.append(recovery);
  try{await load();}catch(error){status.className='';status.textContent=error.message;}
  const timer=setInterval(async()=>{
   if(polling||!dialog.isConnected)return;polling=true;
   try{
    const response=await fetch(api('status'));if(!response.ok)throw Error('Launcher disconnected; reconnect to check installation status.');const state=await response.json();
    if(state.tool===tool.id&&state.busy){running=true;status.className='is-loading';status.textContent=state.message;}
    else if(running&&!state.busy){running=false;await load();status.className='';status.textContent=state.message;}
   }catch(error){status.className='';status.textContent=error.message;}finally{polling=false;}
  },2000);
  dialog.addEventListener('close',()=>clearInterval(timer));
 });
})();
