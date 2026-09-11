/* Local, resumable onboarding. Never auto-downloads, installs or enables backups. */
(() => {
 'use strict';
 if(!window.TOOLKIT_LAUNCHER)return;
 const el=(tag,text)=>{const n=document.createElement(tag);if(text)n.textContent=text;return n;};
 const button=(text,fn)=>{const b=el('button',text);b.onclick=fn;return b;};
 const field=(label,input)=>{const l=el('label',label);l.className='note-field';input.setAttribute('aria-label',label);l.append(input);return l;};
 const api=async(path,body)=>{const r=await fetch(new URL('api/'+path,location.href),body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{cache:'no-store'});const data=await r.json();if(!r.ok)throw Error(data.error||'Setup unavailable');return data;};
 const launch=button('Setup wizard',()=>open());launch.id='setup-wizard-button';document.querySelector('.header-actions').append(launch);
 let dialog=null;
 async function open(initial){
  if(dialog?.isConnected){dialog.focus();return;}
  const d=el('dialog');dialog=d;d.className='download-dialog setup-wizard';d.setAttribute('aria-label','Set up your toolkit');
  const close=button('Set up later',()=>d.close());close.className='setup-close';d.append(close,el('h2','Set up your toolkit'));
  const body=el('div');d.append(body);d.onclose=()=>{d.replaceChildren();d.remove();};document.body.append(d);d.showModal();
  let state,step=0,vault,recoveryPending=false;
  body.append(el('p','Checking this toolkit drive…'));
  try{state=initial||await api('setup');if(state.locked){body.replaceChildren(el('p','Unlock your private vault to review setup for this drive.'),button('Open vault',()=>{d.close();document.querySelector('#manage-private-vault').click();}));return;}
   step=state.required?state.step:0;vault=await api('vault');await paint();
  }catch(e){body.replaceChildren(el('p',e.message),button('Retry',()=>{d.close();open();}));}
  async function persist(next,completed=false){await api('setup',{step:next,completed});step=next;}
  async function paint(){
   body.replaceChildren();const steps=['Your drive','Protect your data','Backup plan','Ready to go'];
   const progress=el('p','Step '+(step+1)+' of 4 · '+steps[step]);progress.className='setup-step';body.append(progress);
   const meter=el('progress');meter.max=4;meter.value=step+1;meter.setAttribute('aria-label','Setup progress');body.append(meter);
   const content=el('section');content.className='setup-content';body.append(content);
   const status=el('p');status.setAttribute('role','status');const actions=el('div');actions.className='actions';body.append(status,actions);
   const act=(label,fn)=>{const b=button(label,async()=>{const controls=[...body.querySelectorAll('button')].map(n=>[n,n.disabled]);controls.forEach(([n])=>n.disabled=true);close.disabled=true;d.oncancel=e=>e.preventDefault();status.textContent='Working…';try{await fn();}catch(e){status.textContent=e.message;}finally{controls.forEach(([n,disabled])=>{if(n.isConnected)n.disabled=disabled;});if(!recoveryPending){close.disabled=false;d.oncancel=null;}}});actions.append(b);return b;};
   if(step>0)act('Back',async()=>{await persist(step-1);await paint();});
   if(step===0){
    content.append(el('h3',state.changedDrive?'Review setup on this drive':'Welcome to Master IT Toolkit'),el('p','Keep the launcher and toolkit folder together. Downloads and portable tools stay inside this toolkit folder.'),el('code',state.root),el('p',(state.free/1024**3).toFixed(1)+' GB free of '+(state.total/1024**3).toFixed(1)+' GB'));
    if(state.changedDrive)content.append(el('p','The volume identifier has changed. Your existing tools and records are preserved; review the settings before continuing.'));
    if(!state.driveDetection)content.append(el('p','A stable drive identifier is unavailable here. Setup completion will follow this toolkit copy; reopen this wizard if you move it to another drive.'));
    const platforms=await api('platforms');content.append(el('p','This computer: '+platforms.current+'. Bundled platforms: '+(platforms.installed.join(', ')||'legacy or source runtime')+'.')) ;
    content.append(el('p','For one SSD on Windows x64, Linux x64 and Apple Silicon Macs, use the all-platforms standalone package. Runtime-only release ZIPs can add a platform without replacing your shared toolkit data.'),el('p','This setup does not format the drive or install software on this computer.'));
    act('Continue',async()=>{await persist(1);await paint();});
   }else if(step===1){
    content.append(el('h3','Protect your private workspace'),el('p','Do not keep sensitive or long-term notes in the toolkit. Export or copy service records to their permanent home, then remove temporary copies.'),el('p','The private vault encrypts the SQLite workspace: notes, favorites, settings and workflow history. Downloaded tools, exported reports and browser sessions are separate and are not encrypted by the vault.'));
    if(vault.configured){content.append(el('p','Your private vault is configured. Keep its recovery key separate from this drive. You can register multiple master computers in Private vault for automatic unlock on their OS accounts. Other computers need your passphrase.'),button('Manage master computers',()=>document.querySelector('#manage-private-vault').click()));act('Continue',async()=>{await persist(2);await paint();});}
    else{
     const secret=el('input');secret.type='password';secret.autocomplete='new-password';secret.maxLength=1024;
     const confirm=el('input');confirm.type='password';confirm.autocomplete='new-password';confirm.maxLength=1024;
     content.append(el('p','Use a passphrase of at least 14 characters.'),field('New vault passphrase',secret),field('Confirm passphrase',confirm));
     act('Encrypt workspace',async()=>{
      if(secret.value!==confirm.value)throw Error('Passphrases do not match.');
      const result=await api('vault',{operation:'setup',secret:secret.value});secret.value='';confirm.value='';vault=result;recoveryPending=true;
      for(const key of Object.keys(localStorage))if(/^(master-it\.v1\.|neighbor-circuit\.v1\.|ventoy\.v1\.)/.test(key))localStorage.removeItem(key);
      actions.replaceChildren();close.disabled=true;d.oncancel=e=>e.preventDefault();
      status.textContent='Save this recovery key somewhere secure, separate from the toolkit. It is shown only once.';
      const key=el('textarea');key.readOnly=true;key.value=result.recoveryKey;content.append(field('New vault recovery key',key));
      act('I saved the recovery key · Continue',async()=>{await persist(2);key.value='';recoveryPending=false;close.disabled=false;d.oncancel=null;await paint();});
     });
     const ack=el('input');ack.type='checkbox';content.append(field('Continue without encryption for now; I understand this workspace remains unencrypted',ack));
     const skip=act('Set up encryption later',async()=>{await persist(2);await paint();});skip.disabled=true;ack.onchange=()=>skip.disabled=!ack.checked;
    }
   }else if(step===2){
    content.append(el('h3','Choose a backup destination'),el('p','Optional: save a NAS folder, mounted backup drive or cloud-synced folder. No backup or automatic schedule starts during setup. Credentials belong in your operating system, never in these fields.'));
    const dest=el('input');dest.value=state.backup.destination||'';dest.placeholder='An existing absolute folder path';
    const engine=el('select');for(const [value,label] of [['restic','Encrypted incremental backup (restic)'],['zip','Versioned ZIP (not encrypted)']]){const o=el('option',label);o.value=value;engine.append(o);}engine.value=state.backup.engine||'restic';
    content.append(field('Backup destination',dest),field('Backup format',engine),el('p','Encrypted backups also need an unlocked vault and the restic tool. On the Backups page, create and verify a first backup before enabling a schedule. An offline NAS destination can be saved now.'));
    act('Save backup plan',async()=>{if(!dest.value.trim())throw Error('Enter a destination or choose Set up backup later.');if(!/^(?:[A-Za-z]:[\\/]|\\\\|\/)/.test(dest.value.trim()))throw Error('Use an absolute folder path.');const value={...state.backup,destination:dest.value.trim(),scope:state.backup.scope||'full',engine:engine.value,automatic:false,intervalHours:state.backup.intervalHours||24,keepLast:state.backup.keepLast||0};if(value.destination===state.backup.destination&&value.engine===state.backup.engine)value.automatic=!!state.backup.automatic;await api('workspace',{key:'backupSettings',value});state.backup=value;await persist(3);await paint();});
    act('Set up backup later',async()=>{await persist(3);await paint();});
   }else{
    content.append(el('h3','Your toolkit is ready'),el('p','Scan local inventory to find downloaded tools and organize supported archives. Scanning does not install software. Use All tools to filter by availability and download method, or PC builds for guided setup workflows.'),el('p','You can reopen Setup wizard from the header at any time. Setup progress is saved in SQLite and preserved by toolkit updates.'));
    act('Finish setup',async()=>{await persist(3,true);d.close();});
    act('Finish and scan inventory',async()=>{const result=await api('action',{action:'inventory',confirmed:true});await persist(3,true);window.dispatchEvent(new CustomEvent('toolkit-activity',{detail:{busy:true,message:result.message}}));d.close();});
   }
  }
 }
 api('setup').then(state=>{if(state.required)open(state);}).catch(()=>{launch.title='Setup could not load. Click to retry.';});
})();
